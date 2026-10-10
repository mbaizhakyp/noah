"""Spec 007: Noah's chat agent behind POST /chat (iMessage relay 008, web chat). Azure OpenAI tool calling (J11).

Facts come only from tools: routing.status/route (our road forecast, < 1 s) plus, when it finishes within
ENGINE_BUDGET_S, Priyanshu's engine (33 live sources + AI assessment). Replies follow 02-ARCHITECTURE §5:
never "safe/clear/passable", 911 when describing danger, <= 480 characters, plain text.
Memory: per sender, last 12 messages + named places ("home", "work"), in RAM only.
"""

import json
import logging
import os
import re
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

import httpx
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

from noah import config
from noah.api import routing

log = logging.getLogger("agent")
router = APIRouter()
ET = "America/New_York"
MAX_CHARS = 480
ENGINE_BUDGET_S = 12
GEORGIA_VIEWBOX = "-85.61,35.00,-80.84,30.36"  # left,top,right,bottom
BANNED = re.compile(r"\b(safe|safely|clear|passable|you're fine|no risk)\b", re.IGNORECASE)
ERROR_REPLY = (
    "I can't confirm conditions right now, so treat low roads near creeks as impassable. "
    "In an emergency call 911."
)
_pool = ThreadPoolExecutor(max_workers=4)
_geo_cache: dict[str, dict] = {}
_geo_lock = threading.Lock()
_last_geo = [0.0]
SESSIONS: dict[str, dict] = {}

SYSTEM = """You are Noah, a flood-road assistant for Georgia, texting with someone over iMessage.
Noah forecasts which roads creeks will flood over the next 18 hours (NOAA National Water Model + road
elevations; road-by-road timing covers metro Atlanta) and checks live warnings, closures and cameras.
Current time: {now}. Latest forecast issued {issued}, valid until {until} (all Atlanta time).

How to answer:
- ALWAYS use tools for road conditions; never guess. One tool call per question is usually enough.
- Places: pass the user's words (street, address, landmark, "home", "work"). If they ask about home/work
  and you don't know it, ask for the address once; when they give it, call remember_place.
- Times: convert "tonight at 6", "in 2 hours" to leave_in_hours from the current time (0 = now).
  More than 18 hours out is beyond the forecast window: say so, don't guess.
- Use only these meanings: "flooded" = Do not cross {{road}}, forecast underwater around {{time}};
  "uncertain" = treat {{road}} as impassable from around {{time}}; "no_forecast_flooding" = no flooding
  forecast through {{time}}, this is not a safety guarantee; "out_of_coverage"/"no_road_forecast" =
  outside Noah's road-by-road coverage, check official warnings.
- NEVER call a road or route safe, clear or passable, and never say "no risk". When describing danger,
  add: never drive into water; call 911 in an emergency.
- Use only numbers and times that appear in tool results. Name the main flooded roads and when.
- If a tool returns an error, say so plainly and ask for a street address. Never claim a place was
  saved or checked unless the tool result says so.
- If a route result has a map_url, include it. Plain text, no markdown, at most 480 characters."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_area",
            "description": "Flood forecast + live hazards within 5 km of a place (roads flooding and when).",
            "parameters": {
                "type": "object",
                "properties": {
                    "place": {
                        "type": "string",
                        "description": "address, street, landmark, or 'home'/'work'",
                    }
                },
                "required": ["place"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_route",
            "description": "Drive from origin to destination avoiding forecast flooding; flags flooded roads on the way.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string"},
                    "destination": {"type": "string"},
                    "leave_in_hours": {
                        "type": "number",
                        "description": "hours from now until departure (0 = now)",
                    },
                },
                "required": ["origin", "destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "remember_place",
            "description": "Save a named place for this person, e.g. name='home', place='123 Main St, Atlanta'.",
            "parameters": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "place": {"type": "string"}},
                "required": ["name", "place"],
            },
        },
    },
]


# ---------------------------------------------------------------- pure helpers (tested)


def depart_hour(issue: pd.Timestamp, now: pd.Timestamp, leave_in_hours: float) -> int:
    """Forecast lead hour for a departure `leave_in_hours` after `now` (forecast issued at `issue`)."""
    return max(0, round((now - issue).total_seconds() / 3600 + max(0.0, leave_in_hours)))


def local(ts: pd.Timestamp | str | None) -> str | None:
    if ts is None:
        return None
    return pd.Timestamp(ts).tz_convert(ET).strftime("%a %-I:%M %p").replace(":00 ", " ")


def finalize(text: str) -> str:
    """Plain text, <= MAX_CHARS, cut at a sentence end when possible."""
    t = re.sub(r"[*_`#]+", "", (text or "").strip())
    if len(t) <= MAX_CHARS:
        return t
    cut = t[: MAX_CHARS - 1]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[: end + 1] if end > MAX_CHARS // 2 else cut.rstrip() + "…").strip()


def is_banned(text: str) -> bool:
    return bool(BANNED.search(text or ""))


def template_reply(result: dict | None) -> str:
    """Deterministic §5 reply from the last tool result (used if the model keeps using banned words)."""
    if not result or "state" not in result:
        return ERROR_REPLY
    st, roads = result["state"], result.get("flagged_roads") or []
    if st in ("out_of_coverage", "no_road_forecast"):
        return "That's outside Noah's road-by-road coverage (metro Atlanta). Check local official warnings."
    if st == "beyond_forecast_window":
        return "That's more than 18 hours out, past Noah's forecast window. Ask again closer to the time."
    if roads:
        r = roads[0]
        verb = "Do not cross" if r["state"] == "flooded" else "Treat as impassable:"
        return finalize(
            f"{verb} {r['name']} (from ~{r['from']}). Never drive into water; call 911 in an emergency."
        )
    return "No flooding is forecast there for the next 18 hours. This is not a safety guarantee."


def flagged(rows: list[dict], limit: int = 5) -> list[dict]:
    """Compact, deduplicated named roads (worst first, then earliest)."""
    rank = {"flooded": 0, "uncertain": 1}
    out, seen = [], set()
    for r in sorted(rows, key=lambda r: (rank.get(r.get("state"), 2), r.get("eta_utc") or "")):
        name = r.get("name") or "an unnamed road"
        if r.get("state") not in rank or name in seen:
            continue
        seen.add(name)
        out.append({"name": name, "state": r["state"], "from": local(r.get("eta_utc"))})
        if len(out) == limit:
            break
    return out


# ---------------------------------------------------------------- tools


ABBREV = {
    "dr": "drive",
    "rd": "road",
    "st": "street",
    "ave": "avenue",
    "av": "avenue",
    "blvd": "boulevard",
    "pkwy": "parkway",
    "hwy": "highway",
    "ln": "lane",
    "ct": "court",
    "cir": "circle",
    "pl": "place",
    "nw": "northwest",
    "ne": "northeast",
    "sw": "southwest",
    "se": "southeast",
    "trl": "trail",
    "ter": "terrace",
}
DIRECTIONS = {"northwest", "northeast", "southwest", "southeast", "north", "south", "east", "west"}


def norm_tokens(name: str) -> set[str]:
    """'Northside Dr NW' -> {'northside', 'drive', 'northwest'} (OSM spells suffixes out)."""
    return {ABBREV.get(w, w) for w in re.findall(r"[a-z0-9]+", name.lower())}


def street_matches(query: str, edge_name: str) -> bool:
    q, e = norm_tokens(query), norm_tokens(edge_name)
    core, dirs = q - DIRECTIONS, q & DIRECTIONS
    return bool(core) and core <= e and dirs <= e


_street_index: list[tuple[str, float, float]] = []


def street_near(street: str, lat: float, lon: float) -> dict | None:
    """Closest stretch of `street` (our OSM road graph) to a point: for 'Northside Drive near Peachtree Creek'."""
    if not _street_index:
        from noah.api.dispatch import graph_state

        G, *_ = graph_state()
        for u, v, d in G.edges(data=True):
            nm = d.get("name")
            for n in nm if isinstance(nm, list) else [nm]:
                if isinstance(n, str):
                    y = (G.nodes[u]["y"] + G.nodes[v]["y"]) / 2
                    x = (G.nodes[u]["x"] + G.nodes[v]["x"]) / 2
                    _street_index.append((n, y, x))
    best = min(
        ((n, y, x) for n, y, x in _street_index if street_matches(street, n)),
        key=lambda r: (r[1] - lat) ** 2 + ((r[2] - lon) * 0.83) ** 2,
        default=None,
    )
    return (
        {"lat": best[1], "lon": best[2], "name": f"{best[0]} (near the requested spot)"}
        if best
        else None
    )


def warm() -> None:
    """Build the street index at server start, so the first 'X near Y' question isn't slow."""
    street_near("warm-up", 33.8, -84.4)


def _nominatim(q: str):
    """One Nominatim lookup (<= 1 req/s, real User-Agent, R7). Returns "retry" on rate limiting / errors."""
    with _geo_lock:
        wait = 1.0 - (time.time() - _last_geo[0])
        if wait > 0:
            time.sleep(wait)
        try:
            r = httpx.get(
                "https://nominatim.openstreetmap.org/search",
                timeout=10,
                params={
                    "q": q,
                    "format": "jsonv2",
                    "limit": 1,
                    "countrycodes": "us",
                    "viewbox": GEORGIA_VIEWBOX,
                    "bounded": 1,
                },
                headers={"User-Agent": "noah-hacklanta/0.1 (+https://github.com/mbaizhakyp/noah)"},
            )
        except httpx.HTTPError:
            return "retry"
        finally:
            _last_geo[0] = time.time()
    if r.status_code != 200:
        return "retry"
    hits = r.json()
    if not hits:
        return None
    return {
        "lat": float(hits[0]["lat"]),
        "lon": float(hits[0]["lon"]),
        "name": hits[0]["display_name"],
    }


def geocode(place: str) -> dict | None:
    """Place text -> point in Georgia: as written, then '..., Atlanta, GA', then 'STREET near LANDMARK'."""
    key = place.strip().lower()
    if key in _geo_cache:
        return _geo_cache[key]
    out, transient = None, False
    for q in (place, f"{place}, Atlanta, GA"):
        res = _nominatim(q)
        if res == "retry":
            time.sleep(1.5)
            res = _nominatim(q)
        if res == "retry":
            transient = True
        elif res:
            out = res
            break
    m = re.match(r"(.+?)\s+(?:near|by|at|close to)\s+(.+)", place.strip(), re.IGNORECASE)
    if not out and m:  # landmark first, then the nearest stretch of that street
        landmark = geocode(m.group(2))
        out = street_near(m.group(1), landmark["lat"], landmark["lon"]) if landmark else None
    if out or not transient:  # never cache a failure caused by rate limiting / outages
        _geo_cache[key] = out
    return out


def resolve(session: dict, place: str) -> dict | None:
    return session["places"].get(place.strip().lower()) or geocode(place)


def engine_extra(fn, *args) -> dict | None:
    """Priyanshu's engine (live sources + AI assessment) if it answers within the budget."""
    from noah import engine

    fut = _pool.submit(getattr(engine, fn), *args)
    try:
        res = fut.result(timeout=ENGINE_BUDGET_S)
    except FutureTimeout:
        log.info(
            "engine.%s over %ss budget, answering from the road forecast only", fn, ENGINE_BUDGET_S
        )
        return None
    except Exception:
        log.exception("engine.%s failed", fn)
        return None
    a = res.get("assessment") or {}
    return {
        "now": (a.get("now") or {}).get("summary"),
        "next_18h": (a.get("next_18h") or {}).get("summary"),
        "action": a.get("action"),
        "live_hazards_avoided": (res.get("road_forecast") or {})
        .get("route", {})
        .get("avoided_segments"),
    }


def run_tool(name: str, args: dict, session: dict, ctx: dict) -> dict:
    if name == "remember_place":
        geo = geocode(args["place"])
        if not geo:
            return {"error": f"couldn't find '{args['place']}' in Georgia"}
        session["places"][args["name"].strip().lower()] = geo
        return {"saved": args["name"], "as": geo["name"]}
    if name == "check_area":
        geo = resolve(session, args["place"])
        if not geo:
            return {
                "error": f"couldn't find '{args['place']}' in Georgia; ask for a street address"
            }
        st = routing.status(geo["lat"], geo["lon"], config.MAX_LEAD_H, ctx["cycle"])
        out = {
            "place": geo["name"],
            "state": st["state"],
            "flagged_roads": flagged(st.get("segments", [])),
        }
        if st["state"] not in ("out_of_coverage",):
            out["live"] = engine_extra("area", geo["lat"], geo["lon"], ctx["cycle"])
        return out
    if name == "check_route":
        a, b = resolve(session, args["origin"]), resolve(session, args["destination"])
        if not a or not b:
            missing = args["origin"] if not a else args["destination"]
            return {"error": f"couldn't find '{missing}' in Georgia; ask for a street address"}
        h = depart_hour(ctx["issue"], ctx["now"], float(args.get("leave_in_hours") or 0))
        rt = routing.route(a["lat"], a["lon"], b["lat"], b["lon"], h, ctx["cycle"])
        out = {
            "from": a["name"],
            "to": b["name"],
            "state": rt["state"],
            "minutes": rt.get("minutes"),
            "leaving": local(ctx["issue"] + pd.Timedelta(hours=h)),
            "flagged_roads": flagged(rt.get("corridor", [])),
            "avoided_flooded_segments": len(rt.get("avoided", [])),
        }
        if rt.get("map_url") and config.WEB_BASE:
            out["map_url"] = rt["map_url"]
        if rt["state"] == "route_found":
            out["live"] = engine_extra(
                "route", a["lat"], a["lon"], b["lat"], b["lon"], h, ctx["cycle"]
            )
        return out
    return {"error": f"unknown tool {name}"}


# ---------------------------------------------------------------- model loop


def llm(messages: list[dict], tools: bool = True) -> dict:
    ep = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    dep = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    body = {"messages": messages, "temperature": 0.2, "max_tokens": 350}
    if tools:
        body |= {"tools": TOOLS, "tool_choice": "auto"}
    r = httpx.post(
        f"{ep}/openai/deployments/{dep}/chat/completions",
        params={"api-version": "2024-10-21"},
        headers={"api-key": os.environ["AZURE_OPENAI_API_KEY"]},
        json=body,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]


def context() -> dict:
    cycle = routing.current_cycle()
    issue = pd.Timestamp(config.parse_cycle(cycle))
    # Demo replay pins a cycle (NOAH_CYCLE): then "now" is that run's issue time, so times line up.
    now = issue if os.environ.get("NOAH_CYCLE") else pd.Timestamp.now(tz="UTC")
    return {"cycle": cycle, "issue": issue, "now": now}


def answer(sender: str, text: str) -> str:
    session = SESSIONS.setdefault(sender, {"history": deque(maxlen=12), "places": {}})
    ctx = context()
    system = SYSTEM.format(
        now=local(ctx["now"]),
        issued=local(ctx["issue"]),
        until=local(ctx["issue"] + pd.Timedelta(hours=config.MAX_LEAD_H)),
    )
    messages = [
        {"role": "system", "content": system},
        *session["history"],
        {"role": "user", "content": text},
    ]
    last_result = None
    for _ in range(3):  # at most 2 rounds of tool calls, then a final answer
        msg = llm(messages)
        calls = msg.get("tool_calls") or []
        if not calls:
            break
        messages.append({"role": "assistant", "content": msg.get("content"), "tool_calls": calls})
        for c in calls:
            t_tool = time.time()
            res = run_tool(
                c["function"]["name"], json.loads(c["function"]["arguments"] or "{}"), session, ctx
            )
            outcome = "error" if "error" in res else res.get("state", "ok")
            log.info("tool %s -> %s %.1fs", c["function"]["name"], outcome, time.time() - t_tool)
            if "state" in res:
                last_result = res
            messages.append(
                {"role": "tool", "tool_call_id": c["id"], "content": json.dumps(res, default=str)}
            )
    else:
        msg = llm(messages, tools=False)
    reply = finalize(msg.get("content") or "")
    if not reply or is_banned(reply):  # one correction round, then the deterministic template
        messages += [
            {"role": "assistant", "content": reply},
            {
                "role": "user",
                "content": "Rewrite without the words safe, safely, clear, passable or 'no risk', same facts, max 480 characters.",
            },
        ]
        reply = finalize(llm(messages, tools=False).get("content") or "")
        if not reply or is_banned(reply):
            reply = template_reply(last_result)
    session["history"].extend(
        [{"role": "user", "content": text}, {"role": "assistant", "content": reply}]
    )
    return reply


class ChatIn(BaseModel):
    sender: str
    text: str
    image_b64: str | None = None  # user photos are out of scope (Fri Oct 9); ignored


@router.post("/chat")
def chat(body: ChatIn) -> dict:
    t0 = time.time()
    try:
        reply = answer(body.sender, body.text.strip()[:1000])
    except Exception:
        log.exception("chat failed")
        reply = ERROR_REPLY
    log.info("chat len=%d out=%d %.1fs", len(body.text), len(reply), time.time() - t0)
    return {"reply": reply}
