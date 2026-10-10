"""Spec 020: the /demo page. A copy of the live map that runs on a frozen Saturday run and recorded
answers, so judging has no live calls and no surprises. Timestamps stay truthful (the run's issue time).

  uv run python -m noah.api.demo build      write web/demo/index.html from web/index.html
  uv run python -m noah.api.demo record     call the running API for every answer the page can ask
                                            for and save them under web/demo/snapshot/
  uv run python -m noah.api.demo all        both
  uv run python -m noah.api.demo ipad       web/demo/snapshot/ipad_plans.json for the iPad app (spec 021; record runs it too)

The page looks up answers by path + parameters; a departure time that was not recorded falls back to
the nearest recorded one (web/index.html, snapLookup).
"""

import argparse
import hashlib
import itertools
import json
import logging
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import httpx

from noah import config

log = logging.getLogger("demo")
WEB = config.ROOT / "web"
OUT = WEB / "demo"
SNAP = OUT / "snapshot"
API = "http://127.0.0.1:8010"

# ---- the demo: Saturday's 1 AM run (the richest: 333 flagged segments, cuts spread over the window),
# a pharmacy run from Dunwoody over the north watched routes (017): all 7 reached leaving at 4 AM,
# leave-by 5:20 AM, leaving at 6 AM the typed order locks in after Northcrest Way and loses four locations
CYCLE = "20240926T22Z"
NOW_MIN = 60  # the page's clock: 7:00 PM ET, one hour after the 6 PM run was issued
STEP_MIN = 5
FINE_H = (
    6  # record every 5 min for this long after "now", then every 30 min to the end of the window
)


def demo_places() -> dict:
    """Home / Work from the live places file; Delivery = the pharmacy run over the Buckhead streets
    that flooded in the chosen run (the 014 sample as of Sat 11:30, pinned here so later edits to
    dispatch_sample.json cannot change what was recorded)."""
    base = json.loads((WEB / "data" / "places.json").read_text())
    pt = lambda label, lat, lon: {"label": label, "lat": lat, "lon": lon}
    return {
        "home": base["home"],
        "work": base["work"],
        "delivery": {
            "label": "Delivery route · Buckhead",
            "depot": pt("Peachtree Rd NE, Buckhead (depot)", 33.83991, -84.3792),
            "stops": [
                pt("Woodward Way NW, Atlanta", 33.8214, -84.41226),
                pt("Hanover West Ct NW, Atlanta", 33.82242, -84.43179),
                pt("Peachtree Battle Cir NW, Atlanta", 33.82259, -84.41893),
                pt("Bohler Rd NW, Atlanta", 33.82133, -84.42926),
                pt("Windsor Pkwy NE, Brookhaven", 33.88506, -84.36256),
                pt("Caldwell Rd NE, Atlanta", 33.86417, -84.33391),
            ],
            "destination": pt("Fairwood Ln NE, Atlanta", 33.84091, -84.30568),
        },
    }


# ---------------------------------------------------------------- build


def build() -> Path:
    """web/demo/index.html = web/index.html + one line that names the snapshot. Nothing else differs."""
    src = (WEB / "index.html").read_text()
    inject = (
        '<base href="/">\n  <script>window.NOAH_SNAPSHOT = "demo/snapshot/index.json";</script>\n'
    )
    assert src.count("<head>") == 1
    out = src.replace("<head>", "<head>\n  " + inject, 1)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(out)
    log.info("built %s (%d bytes)", OUT / "index.html", len(out))
    return OUT / "index.html"


# ---------------------------------------------------------------- record


class Recorder:
    def __init__(self, api: str = API, refresh: set[str] | None = None):
        """refresh: paths to call again even if recorded (e.g. {"/trip"} after a trip change);
        every other recorded answer on disk is kept."""
        self.client = httpx.Client(base_url=api, timeout=180)
        self.entries: list[dict] = []
        self.seen: dict[str, str] = {}
        self.images: dict[str, str] = {}
        (SNAP / "r").mkdir(parents=True, exist_ok=True)
        (SNAP / "img").mkdir(parents=True, exist_ok=True)
        idx = SNAP / "index.json"
        if idx.exists():
            for e in json.loads(idx.read_text()).get("responses", []):
                if e["path"] in (refresh or set()) or not (SNAP / e["file"]).exists():
                    continue
                self.seen[f"{e['path']}?{urlencode(e['p'])}"] = e["file"]
                self.entries.append(e)
            log.info("kept %d recorded answers from disk", len(self.entries))

    def get(self, path: str, params: dict) -> dict:
        q = urlencode(params)
        key = f"{path}?{q}"
        if key in self.seen:
            return json.loads((SNAP / self.seen[key]).read_text())
        t0 = time.time()
        r = self.client.get(path, params=params)
        r.raise_for_status()
        data = r.json()
        data.pop("took_s", None)
        self.localize_images(data)
        blob = json.dumps(data, separators=(",", ":"))
        h = hashlib.sha1(blob.encode()).hexdigest()[:16]
        rel = f"r/{h}.json"
        if not (SNAP / rel).exists():
            (SNAP / rel).write_text(blob)
        self.seen[key] = rel
        self.entries.append(
            {"path": path, "p": {k: str(v) for k, v in params.items()}, "file": rel}
        )
        log.info(
            "%s %s -> %s (%.1f s, %d KB)", path, q[:90], rel, time.time() - t0, len(blob) // 1024
        )
        return data

    def localize_images(self, obj) -> None:
        """Download every camera snapshot once and point the stored answer at the local copy."""
        if isinstance(obj, dict):
            for k, v in list(obj.items()):
                if k == "image_url" and isinstance(v, str) and v.startswith("http"):
                    obj[k] = self.image(v, obj.get("cam_id"))
                else:
                    self.localize_images(v)
        elif isinstance(obj, list):
            for v in obj:
                self.localize_images(v)

    def image(self, url: str, cam_id=None) -> str:
        if url in self.images:
            return self.images[url]
        name = re.sub(
            r"[^A-Za-z0-9_-]", "", str(cam_id or hashlib.sha1(url.encode()).hexdigest()[:12])
        )
        rel = f"img/{name}.jpg"
        try:
            if not (SNAP / rel).exists():
                r = httpx.get(url, timeout=30, follow_redirects=True)
                r.raise_for_status()
                (SNAP / rel).write_bytes(r.content)
            self.images[url] = f"demo/snapshot/{rel}"
        except Exception as e:  # noqa: BLE001 (a missing snapshot must not sink the recording)
            log.warning("image %s failed: %s", url, e)
            self.images[url] = url
        return self.images[url]

    def write_index(self, places: dict) -> None:
        idx = {
            "cycle": CYCLE,
            "now_min": NOW_MIN,
            "recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "places": places,
            "responses": self.entries,
        }
        (SNAP / "index.json").write_text(json.dumps(idx, indent=0))
        log.info("index: %d answers, %d images", len(self.entries), len(self.images))


def depart_steps() -> list[int]:
    fine = list(range(NOW_MIN, min(config.MAX_LEAD_H * 60, NOW_MIN + FINE_H * 60) + 1, STEP_MIN))
    coarse = list(range(fine[-1], config.MAX_LEAD_H * 60 + 1, 30))
    return sorted(set(fine + coarse))


def ll(p: dict) -> str:
    return f"{p['lat']},{p['lon']}"


def leg_pairs(origin: dict, stops: list[dict], dest: dict) -> list[tuple[dict, dict]]:
    pts = [origin, *stops, dest]
    return list(itertools.pairwise(pts))


def record_trip_family(
    rec: Recorder, origin: dict, stops: list[dict], dest: dict, corridor_m: int
) -> None:
    """The trip at every departure step, the live checks and the past replay per leg at every hour,
    then the same for what the plan button would produce (best order, dropped stops), twice over."""
    seen_orders: set = set()
    queue = [stops]
    while queue:
        cur = queue.pop(0)
        key = tuple((s["lat"], s["lon"]) for s in cur)
        if key in seen_orders:
            continue
        seen_orders.add(key)
        stops_q = ";".join(ll(s) for s in cur)
        first = None
        for m in depart_steps():
            t = rec.get(
                "/trip",
                {
                    "from": ll(origin),
                    "to": ll(dest),
                    "stops": stops_q,
                    "depart_h": f"{m / 60:.3f}",
                    "cycle": CYCLE,
                    "corridor_m": corridor_m,
                },
            )
            if first is None:
                first = t
            if t.get("state") == "ok" and t["best"].get("differs") and len(seen_orders) < 4:
                # what the plan button does: best order, minus the stops the best plan leaves out
                dropped = set(t["best"].get("skipped", []))
                order = [i for i in t["order"] if i < len(cur)]
                rest = [i for i in range(len(cur)) if i not in order and i not in dropped]
                nxt = [cur[i] for i in [*order, *rest]]
                if tuple((s["lat"], s["lon"]) for s in nxt) not in seen_orders and nxt not in queue:
                    queue.append(nxt)
        rec.get(
            "/past/route", {"from": ll(origin), "to": ll(dest), "cycle": CYCLE}
        )  # the page's past tab: start to end
        if cur:
            for a, b in leg_pairs(origin, cur, dest):
                for h in range(NOW_MIN // 60, config.MAX_LEAD_H + 1):
                    rec.get(
                        "/assess/route", {"from": ll(a), "to": ll(b), "depart_h": h, "cycle": CYCLE}
                    )
                rec.get("/past/route", {"from": ll(a), "to": ll(b), "cycle": CYCLE})
        else:  # no stops: the page draws /route per hour and asks /trip for the leave-by
            for h in range(NOW_MIN // 60, config.MAX_LEAD_H + 1):
                rec.get(
                    "/route",
                    {
                        "from": ll(origin),
                        "to": ll(dest),
                        "depart_h": h,
                        "cycle": CYCLE,
                        "corridor_m": corridor_m,
                    },
                )
                rec.get(
                    "/assess/route",
                    {"from": ll(origin), "to": ll(dest), "depart_h": h, "cycle": CYCLE},
                )
            rec.get("/past/route", {"from": ll(origin), "to": ll(dest), "cycle": CYCLE})


def record(api: str = API, corridor_m: int = 3000, refresh: set[str] | None = None) -> None:
    places = demo_places()
    rec = Recorder(api, refresh)
    d = places["delivery"]
    record_trip_family(rec, d["depot"], d["stops"], d["destination"], corridor_m)
    # Home chip: the 5 km area check; Work chip: the commute
    home, work = places["home"], places["work"]
    rec.get(
        "/status",
        {"lat": home["lat"], "lon": home["lon"], "hours": config.MAX_LEAD_H, "cycle": CYCLE},
    )
    rec.get("/assess", {"lat": home["lat"], "lon": home["lon"], "cycle": CYCLE})
    rec.get("/past", {"lat": home["lat"], "lon": home["lon"], "cycle": CYCLE})
    record_trip_family(rec, home, [], work, corridor_m)
    rec.write_index(places)


def ipad_plans() -> Path:
    """Spec 021: every recorded /trip, per stop order, reduced to what the iPad needs to compute leave-by and each stop's
    'Go before' (stops, destination, best order) without loading ~30 MB of route geometry per order."""
    idx = json.loads((SNAP / "index.json").read_text())
    keep_stop = ("i", "state", "reached", "arrive_min", "cut_h", "in_best")
    out: dict[str, list] = {}
    for e in idx["responses"]:
        if e["path"] != "/trip":
            continue
        r = json.loads((SNAP / e["file"]).read_text())
        if r.get("state") != "ok":
            continue
        p = e["p"]
        stops = [
            {**{k: s.get(k) for k in keep_stop}, "street": s.get("street")}
            for s in r.get("stops", [])
        ]
        dest = r.get("dest") or {}
        out.setdefault(f"{p['from']}|{p['to']}|{p.get('stops', '')}", []).append(
            {
                "m": round(float(p["depart_h"]) * 60),
                "stops": stops,
                "dest": {
                    k: dest.get(k) for k in ("state", "reached", "arrive_min", "cut_h", "street")
                },
                "current": r.get("current"),
                "best": {
                    k: (r.get("best") or {}).get(k)
                    for k in ("order", "reached", "dest_reached", "minutes", "differs", "skipped")
                },
                "leave_by_min": r.get("leave_by_min"),
            }
        )
    for v in out.values():
        v.sort(key=lambda x: x["m"])
    path = SNAP / "ipad_plans.json"
    path.write_text(json.dumps(out, separators=(",", ":")))
    log.info("wrote %s (%d stop orders, %d KB)", path, len(out), path.stat().st_size // 1024)
    return path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("what", choices=["build", "record", "ipad", "all"])
    p.add_argument("--api", default=API)
    p.add_argument("--refresh", default="", help="comma-separated paths to call again, e.g. /trip")
    a = p.parse_args()
    if a.what in ("build", "all"):
        build()
    if a.what in ("record", "all"):
        record(a.api, refresh={x for x in a.refresh.split(",") if x})
    if a.what in ("ipad", "record", "all"):
        ipad_plans()


if __name__ == "__main__":
    sys.exit(main())
