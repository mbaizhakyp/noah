"""Spec 015: Noah engine. All sources -> signals -> hard safety rules -> AI assessment.

The AI (Azure OpenAI) reasons over the bundle; it never invents data. Guards on its output:
every number with a unit must appear in the input, banned words are filtered (02 §5), and if
either check fails twice the reply falls back to a rules-only template.
"""

import json
import logging
import os
import re

import httpx
from shapely.geometry import LineString, shape

from noah import sources
from noah.api import routing

log = logging.getLogger("engine")
BANNED = re.compile(r"\b(safe|safely|clear|passable|you're fine|no risk)\b", re.IGNORECASE)
UNIT_NUM = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:in\b|inch|inches|ft\b|feet|cfs|mph|%|km\b|mi\b|miles|mm\b|kt\b)",
    re.IGNORECASE,
)
ANY_NUM = re.compile(r"\d+(?:\.\d+)?")
LEVELS = ["low", "elevated", "high", "severe"]
SEV_LEVEL = {"info": 0, "watch": 1, "warning": 2, "danger": 3}
ERROR_MESSAGE = (
    "I can't confirm conditions right now, so treat low roads near creeks as impassable. "
    "In an emergency call 911."
)

SYSTEM = """You are Noah's flood-road engine for Georgia. You get a JSON bundle with:
- road_forecast: NOAA National Water Model road flood timing for the user's area or route (state + segments with local times)
- signals: live data from many sources (NWS alerts, river gauges, rain gauges, rain forecasts, flash-flood outlooks, traffic incidents, storm reports, cameras, flood zones, past flood reports, vulnerability), each with a source name
- rules: deterministic safety rules already applied

Write a short assessment as JSON with exactly these keys:
{"now": {"level": "low|elevated|high|severe", "summary": str},
 "next_18h": {"level": ..., "summary": str},
 "next_days": {"level": ..., "summary": str},
 "reasons": [{"text": str, "sources": [source names from the bundle]}],
 "action": str,
 "confidence": "low|medium|high"}

Rules you must follow:
1. Use ONLY facts in the bundle. Every number you write must appear in the bundle. Quote times exactly as given (they are already Atlanta local time).
2. Cite sources by the exact "source" names in the bundle. Give 2-5 reasons, most important first.
3. Never say a road or route is "safe", "clear" or "passable", or "no risk". Say "no flooding is forecast" and add "this is not a safety guarantee" when relevant.
4. Be conservative: if sources disagree, use the more cautious level. A rule result can never be lowered.
5. If anything describes danger, tell people never to drive into water and to call 911 in an emergency.
6. Never infer a cause or fact a signal does not state: a road closure is not flooding unless the signal says flooding; an old incident is not caused by today's rain; a gauge with "no flooding" is not rising unless the data shows it.
7. Plain language, each summary at most 2 sentences. If road_forecast state is "no_road_forecast", say: "Noah's road-by-road forecast covers metro Atlanta; for this location it uses statewide warnings, gauges and rain data."
"""


# ---------------------------------------------------------------- guards (pure, tested)


def numbers_ok(text: str, bundle_text: str) -> bool:
    """Every number written with a unit must exist in the bundle (rounding allowed)."""
    have = [float(x) for x in ANY_NUM.findall(bundle_text)] + [
        911.0
    ]  # "call 911 in an emergency" is not 911 inches
    for n in (float(x) for x in UNIT_NUM.findall(text)):
        if not any(abs(n - h) < 0.051 or round(h) == n for h in have):
            return False
    return True


def banned(text: str) -> bool:
    return bool(BANNED.search(text))


def assessment_text(a: dict) -> str:
    parts = [a.get(k, {}).get("summary", "") for k in ("now", "next_18h", "next_days")]
    parts += [r.get("text", "") for r in a.get("reasons", [])] + [a.get("action", "")]
    return " ".join(parts)


# ---------------------------------------------------------------- rules (deterministic)


def rules(road: dict, signals: list[dict]) -> dict:
    """Hard, upgrade-only floor for the AI. Returns minimum levels + the rules that fired."""
    fired, now, next18 = [], 0, 0
    st = road.get("state")
    if st == "flooded":
        next18 = max(next18, 3)
        fired.append(
            "Road forecast: at least one road in the area/route is forecast flooded in the next 18 h."
        )
    elif st == "uncertain":
        next18 = max(next18, 2)
        fired.append(
            "Road forecast: roads in the area/route are forecast uncertain (treat as impassable) in the next 18 h."
        )
    if any(s.get("hour") == 0 for s in road.get("segments", [])):
        now = max(now, 2)
        fired.append("Road forecast: roads are already estimated in the flood band now (hour 0).")
    for s in signals:
        if s["source"] == "NWS alerts" and s["severity"] == "danger":
            now, next18 = max(now, 3), max(next18, 3)
            fired.append(f"NWS alerts: {s['title']} in effect.")
        elif s["source"] == "NWS alerts" and s["severity"] == "watch":
            next18 = max(next18, 1)
            fired.append(f"NWS alerts: {s['title']} in effect.")
        elif s["source"] == "TomTom traffic incidents" and s.get("value") == 11:
            now = max(now, 3)
            fired.append(f"TomTom traffic incidents: flooding reported ({s['title']}).")
        elif s["source"] == "NWPS river gauges" and s["severity"] == "danger":
            now = max(now, 3)
            fired.append(f"NWPS river gauges: {s['title']} at moderate/major flood.")
        elif s["source"] == "Traffic cameras" and s["severity"] == "danger":
            now = max(now, 3)
            fired.append(f"Traffic cameras: {s['title']}.")
    return {"min_now": LEVELS[now], "min_next_18h": LEVELS[next18], "fired": fired}


def raise_to_floor(a: dict, r: dict) -> dict:
    for key, floor in (("now", r["min_now"]), ("next_18h", r["min_next_18h"])):
        cur = a.get(key, {}).get("level", "low")
        if LEVELS.index(cur if cur in LEVELS else "low") < LEVELS.index(floor):
            a.setdefault(key, {})["level"] = floor
    return a


def template(road: dict, signals: list[dict], r: dict) -> dict:
    """Rules-only assessment, used when the AI is unavailable or fails its guards."""
    top = [s for s in signals if s["severity"] in ("danger", "warning")][:4]
    days = max(
        (
            SEV_LEVEL[s["severity"]]
            for s in signals
            if s["source"] in ("WPC Excessive Rainfall Outlook", "NWPS reach flow forecast (NWM)")
        ),
        default=0,
    )
    return {
        "now": {
            "level": r["min_now"],
            "summary": "Based on live warnings, gauges and incidents near you.",
        },
        "next_18h": {
            "level": r["min_next_18h"],
            "summary": "Based on NOAA's road-level flood forecast for the next 18 hours.",
        },
        "next_days": {
            "level": LEVELS[days],
            "summary": "Based on NOAA's rain outlook and 10-day creek forecasts.",
        },
        "reasons": [
            {"text": f"{s['title']}. {s.get('detail', '')}", "sources": [s["source"]]} for s in top
        ]
        + [{"text": f, "sources": ["rules"]} for f in r["fired"][:2]],
        "action": "Check the red and amber roads before you leave. Never drive into water. In an emergency call 911.",
        "confidence": "low",
        "generated_by": "rules",
    }


# ---------------------------------------------------------------- AI call


def ai_call(messages: list[dict]) -> dict:
    ep = os.environ["AZURE_OPENAI_ENDPOINT"].rstrip("/")
    dep = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1-mini")
    r = httpx.post(
        f"{ep}/openai/deployments/{dep}/chat/completions",
        params={"api-version": "2024-10-21"},
        headers={"api-key": os.environ["AZURE_OPENAI_API_KEY"]},
        timeout=30,
        json={
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": 900,
            "response_format": {"type": "json_object"},
        },
    )
    r.raise_for_status()
    return json.loads(r.json()["choices"][0]["message"]["content"])


def compact(signals: list[dict], limit: int = 60) -> list[dict]:
    keep = ("source", "kind", "title", "detail", "severity", "value", "units")
    return [{k: s[k] for k in keep if k in s} for s in signals[:limit]]


def assess(road: dict, signals: list[dict]) -> dict:
    r = rules(road, signals)
    bundle = {"road_forecast": road, "signals": compact(signals), "rules": r}
    bundle_text = json.dumps(bundle)
    if not os.environ.get("AZURE_OPENAI_API_KEY"):
        return template(road, signals, r)
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": bundle_text}]
    for attempt in range(2):
        try:
            a = ai_call(msgs)
        except Exception:
            log.exception("AI call failed")
            return template(road, signals, r)
        text = assessment_text(a)
        problems = []
        if banned(text):
            problems.append("it used a banned word (safe/clear/passable/no risk)")
        if not numbers_ok(text, bundle_text):
            problems.append("it stated a number that is not in the bundle")
        if not problems:
            a = raise_to_floor(a, r)
            a["generated_by"] = "ai"
            return a
        log.warning("AI reply rejected (%s), attempt %d", "; ".join(problems), attempt + 1)
        msgs += [
            {"role": "assistant", "content": json.dumps(a)},
            {
                "role": "user",
                "content": f"Rewrite: {', and '.join(problems)}. Follow the rules exactly.",
            },
        ]
    return template(road, signals, r)


# ---------------------------------------------------------------- road forecast summaries for the bundle


def road_summary(resp: dict, cycle: str) -> dict:
    """006 response -> compact road forecast with Atlanta-local times and lead hours."""
    from noah.sources.adapters import local

    rows = resp.get("segments") or resp.get("corridor") or []
    issue = next(
        (c["issue_time"] for c in routing.cycles_meta()["cycles"] if c["cycle"] == cycle), None
    )
    out = []
    seen = set()
    for s in rows:
        key = (s.get("name"), s.get("state"))
        if key in seen:
            continue
        seen.add(key)
        hour = None
        if issue and s.get("eta_utc"):
            from datetime import datetime

            hour = round(
                (
                    datetime.fromisoformat(s["eta_utc"]) - datetime.fromisoformat(issue)
                ).total_seconds()
                / 3600
            )
        out.append(
            {
                "name": s.get("name") or "unnamed road",
                "state": s.get("state"),
                "from_local": local(s.get("eta_utc")),
                "hour": hour,
                "distance_m": s.get("distance_m"),
            }
        )
    return {
        "state": resp.get("state"),
        "forecast_issued_local": local(issue),
        "flagged_roads": len(seen),
        "segments": out[:25],
    }


def area(lat: float, lon: float, cycle: str | None = None) -> dict:
    cycle = cycle or routing.current_cycle()
    st = routing.status(lat, lon, 18, cycle)
    fids = []  # creeks under the flagged roads -> 10-day reach forecasts
    if st["segments"]:
        ids = {s["seg_id"] for s in st["segments"]}
        fids = list(
            dict.fromkeys(
                p["feature_id"] for p in routing.flood_index(cycle).props if p["seg_id"] in ids
            )
        )
    ctx = sources.Ctx("area", lat, lon, extra={"feature_ids": fids})
    bundle = sources.run(ctx)
    road = road_summary(st, cycle)
    return {
        "state": st["state"],
        "cycle": cycle,
        "assessment": assess(road, bundle["signals"]),
        "road_forecast": road,
        **bundle,
    }


def route(a_lat, a_lon, b_lat, b_lon, depart_h: int = 0, cycle: str | None = None) -> dict:
    cycle = cycle or routing.current_cycle()
    rt = routing.route(a_lat, a_lon, b_lat, b_lon, depart_h, cycle)
    if rt.get("geometry"):
        line = LineString(shape(rt["geometry"]).coords)
    else:
        line = LineString([(a_lon, a_lat), (b_lon, b_lat)])
    mid = line.interpolate(0.5, normalized=True)
    fi = routing.flood_index(cycle)
    ids = {c["seg_id"] for c in rt.get("corridor", [])}
    fids = list(dict.fromkeys(p["feature_id"] for p in fi.props if p["seg_id"] in ids))
    ctx = sources.Ctx("route", mid.y, mid.x, line=line, extra={"feature_ids": fids})
    bundle = sources.run(ctx)
    road = road_summary(rt, cycle)
    road["route"] = {
        "state": rt["state"],
        "minutes": rt.get("minutes"),
        "avoided_segments": len(rt.get("avoided", [])),
    }
    return {
        "state": rt["state"],
        "cycle": cycle,
        "route": rt,
        "assessment": assess(road, bundle["signals"]),
        "road_forecast": road,
        **bundle,
    }
