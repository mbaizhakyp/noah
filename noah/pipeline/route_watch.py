"""Spec 017: route watch. About a dozen fixed A->B routes past traffic cameras next to roads the live runs flagged.

For every live run: log each route's forecast status (the "warned N hours ahead" proof) in web/data/route_watch.json.
When the newest run changes a route, or a camera confirms water (BL-22 evidence card), queue a message in
data/interim/outbox.jsonl; the iMessage relay (bot/) sends it to every thread that texted "alerts on". Also ntfy.

  uv run python -m noah.pipeline.route_watch --pick       choose the routes -> web/data/watch_routes.json
  caffeinate -i uv run python -m noah.pipeline.route_watch --every 300
  uv run python -m noah.pipeline.route_watch --report     first warning per route
"""

import argparse
import itertools
import json
import logging
import time
import uuid
from collections import Counter

import pandas as pd

from noah import config

log = logging.getLogger("route_watch")
ROUTES = config.WEB_DATA / "watch_routes.json"
HISTORY = config.WEB_DATA / "route_watch.json"
OUTBOX = config.DATA_INTERIM / "outbox.jsonl"
LATEST = (
    config.DATA_INTERIM / "route_watch_latest.txt"
)  # sent to a thread when it texts "alerts on"
CHECKS = config.DATA_INTERIM / "camera_checks.jsonl"
CAMS_CACHE = config.DATA_INTERIM / "cameras_aoi.json"
ET = "America/New_York"
GUARANTEE = (
    "Never drive into water; call 911 if anyone is in danger. This is not a safety guarantee."
)


def iso(t: pd.Timestamp) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def et(t) -> str:
    return pd.Timestamp(t).tz_convert(ET).strftime("%a %-I:%M %p").replace(":00 ", " ")


def live_cycles() -> list[str]:
    c6 = json.loads((config.WEB_DATA / "cycles.json").read_text())
    return sorted(c["cycle"] for c in c6["cycles"] if c.get("event") == "live")


# ---------- pure logic ----------


def route_status(
    seg_ids: list[str], props: dict, issue: pd.Timestamp, had: pd.Timestamp | None = None
) -> dict:
    """One route in one run. props: seg_id -> C5 properties. The route is cut from its earliest t_uncertain (I5 rule).
    now = already cut by the time Noah had the run (`had`)."""
    hits = sorted((props[s] for s in seg_ids if s in props), key=lambda p: p["t_uncertain"])
    if not hits:
        return {"state": "no_forecast_flooding", "from_utc": None, "street": None, "streets": []}
    at = lambda h: iso(issue + pd.Timedelta(hours=int(h)))
    first = {}
    for p in hits:
        first.setdefault(p["name"] or "unnamed road", p)
    return {
        "state": "flooded" if any(p["t_flood"] is not None for p in hits) else "uncertain",
        "from_utc": at(hits[0]["t_uncertain"]),
        "now": had is not None and issue + pd.Timedelta(hours=int(hits[0]["t_uncertain"])) <= had,
        "street": hits[0]["name"] or "unnamed road",
        "streets": [{"name": n, "from_utc": at(p["t_uncertain"])} for n, p in first.items()],
    }


def change(prev: dict | None, cur: dict) -> str | None:
    """'new' | 'dropped' | 'moved' (>= 1 h or another street) | None. No previous run = first look, no alert."""
    if prev is None or (prev["from_utc"] is None and cur["from_utc"] is None):
        return None
    if prev["from_utc"] is None:
        return "new"
    if cur["from_utc"] is None:
        return "dropped"
    if prev.get("now") and cur.get("now") and cur["street"] == prev["street"]:
        return None  # still cut: its "from" just follows each run's start hour
    shift = abs(pd.Timestamp(cur["from_utc"]) - pd.Timestamp(prev["from_utc"]))
    return "moved" if shift >= pd.Timedelta(hours=1) or cur["street"] != prev["street"] else None


def header(run: dict) -> str:
    return f"Noah route watch, NOAA forecast issued {et(run['issued_utc'])} (Noah had it {et(run['had_utc'])})"


def digest(run: dict, prev: dict, routes: list[dict]) -> str | None:
    """One message per run listing the routes whose forecast changed, or None."""
    lines = []
    for r in routes:
        old, cur = prev["routes"].get(r["id"]), run["routes"][r["id"]]
        c = change(old, cur)
        if c == "new":
            lines.append(
                f"• {r['label']}: forecast cut by flooding from ~{et(cur['from_utc'])} at {short(cur['street'])} (new)"
            )
        elif c == "moved":
            lines.append(
                f"• {r['label']}: now cut from ~{et(cur['from_utc'])} at {short(cur['street'])} (was ~{et(old['from_utc'])})"
            )
        elif c == "dropped":
            lines.append(
                f"• {r['label']}: this run no longer flags it (was ~{et(old['from_utc'])})"
            )
    if not lines:
        return None
    more = [f"…and {len(lines) - 6} more"] if len(lines) > 6 else []
    n = sum(run["routes"][r["id"]]["from_utc"] is not None for r in routes)
    tail = f"{n} of {len(routes)} watched routes forecast cut now. {GUARANTEE}"
    return "\n".join([header(run) + ":", *lines[:6], *more, tail])


def summary(run: dict, routes: list[dict]) -> str:
    cut = sorted(
        ((r, run["routes"][r["id"]]) for r in routes if run["routes"][r["id"]]["from_utc"]),
        key=lambda rs: rs[1]["from_utc"],
    )
    if not cut:
        end = et(pd.Timestamp(run["issued_utc"]) + pd.Timedelta(hours=config.MAX_LEAD_H))
        return (
            f"{header(run)}: no flooding is forecast on the {len(routes)} watched routes through {end}. "
            + GUARANTEE
        )
    lines = [
        f"• {r['label']}: from ~{et(s['from_utc'])} at {short(s['street'])}" for r, s in cut[:6]
    ]
    return "\n".join(
        [
            f"{header(run)}: {len(cut)} of {len(routes)} watched routes forecast cut by flooding.",
            *lines,
            GUARANTEE,
        ]
    )


def first_warning(runs: list[dict], route_id: str, before_utc: str) -> dict | None:
    """Earliest run Noah had before `before_utc` that flagged the route."""
    hits = [
        {"cycle": r["cycle"], "had_utc": r["had_utc"], **r["routes"][route_id]}
        for r in runs
        if route_id in r["routes"]
        and r["routes"][route_id]["from_utc"]
        and r["had_utc"] <= before_utc
    ]
    return min(hits, key=lambda h: h["had_utc"], default=None)


def camera_message(row: dict, route: dict | None, first: dict | None) -> str:
    """§5 camera wording + how far ahead Noah's first warning came."""
    where = f"the {route['label']} route" if route else (row.get("title") or "a watched road")
    s = (
        f"Camera on {where} shows water around {(row.get('bucket') or 'some').replace('_', ' ')} level at "
        f"{et(row['ts'])} (AI-checked twice). Treat nearby roads as impassable."
    )
    if first:
        h = (pd.Timestamp(row["ts"]) - pd.Timestamp(first["had_utc"])).total_seconds() / 3600
        s += (
            f" Noah first flagged this route {h:.1f} h earlier, at {et(first['had_utc'])} "
            f"(forecast: cut from ~{et(first['from_utc'])} at {short(first['street'])})."
        )
    elif route:
        s += " Noah had not flagged this route before this."
    return f"{s} Call 911 if anyone is in danger. (Webcams provided by Windy.com)"


# ---------- watch loop ----------


def queue(text: str, image: str | None = None) -> None:
    from noah.pipeline.camera_watch import notify  # desktop + ntfy fallback (spec 017 fallback)

    text = config.road_alias(text)
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTBOX, "a") as fh:
        item = {
            "id": uuid.uuid4().hex,
            "ts": iso(pd.Timestamp.now(tz="UTC")),
            "text": text,
            "image": image,
        }
        fh.write(json.dumps(item) + "\n")
    if image is None:  # camera_watch already pushed its own notification for camera water
        notify("Noah route watch", text[:1000])
    log.info("queued: %s", text.splitlines()[0][:120])


def run_once() -> None:
    routes = json.loads(ROUTES.read_text())["routes"]
    hist = (
        json.loads(HISTORY.read_text()) if HISTORY.exists() else {"runs": [], "camera_alerts": []}
    )
    first_time = not hist["runs"]
    live = live_cycles()
    done = {r["cycle"] for r in hist["runs"]}
    for cyc in (c for c in live if c not in done):
        path = config.WEB_DATA / f"flood_{cyc}.geojson"
        if not path.exists():
            continue
        props = {
            f["properties"]["seg_id"]: f["properties"]
            for f in json.loads(path.read_text())["features"]
        }
        issue = pd.Timestamp(config.parse_cycle(cyc))
        had = pd.Timestamp(path.stat().st_mtime, unit="s", tz="UTC")  # when our live loop wrote it
        run = {
            "cycle": cyc,
            "issued_utc": iso(issue),
            "had_utc": iso(had),
            "routes": {r["id"]: route_status(r["seg_ids"], props, issue, had) for r in routes},
        }
        prev = max(
            (r for r in hist["runs"] if r["cycle"] < cyc), key=lambda r: r["cycle"], default=None
        )
        hist["runs"] = sorted([*hist["runs"], run], key=lambda r: r["cycle"])
        log.info(
            "%s: %d of %d routes flagged",
            cyc,
            sum(s["from_utc"] is not None for s in run["routes"].values()),
            len(routes),
        )
        if not first_time and prev and cyc == live[-1]:  # backfilled / older runs stay silent
            msg = digest(run, prev, routes)
            if msg:
                queue(msg)
    if hist["runs"]:
        LATEST.parent.mkdir(parents=True, exist_ok=True)
        LATEST.write_text(config.road_alias(summary(hist["runs"][-1], routes)))

    seen = {(a["cam_id"], a["ts"]) for a in hist["camera_alerts"]}
    rows = [json.loads(x) for x in CHECKS.read_text().splitlines()] if CHECKS.exists() else []
    for row in rows:
        if not (row.get("verified") and row.get("evidence")) or (row["cam_id"], row["ts"]) in seen:
            continue
        route = next((r for r in routes if row["cam_id"] in {c["id"] for c in r["cams"]}), None)
        first = first_warning(hist["runs"], route["id"], row["ts"]) if route else None
        queue(camera_message(row, route, first), image=row["evidence"])
        hist["camera_alerts"].append(
            {
                "cam_id": row["cam_id"],
                "ts": row["ts"],
                "route": route and route["id"],
                "bucket": row.get("bucket"),
                "first_warning_had_utc": first and first["had_utc"],
            }
        )
    HISTORY.write_text(json.dumps(hist, indent=1))


def report() -> None:
    routes = json.loads(ROUTES.read_text())["routes"]
    hist = json.loads(HISTORY.read_text())
    for r in routes:
        f = first_warning(hist["runs"], r["id"], "9999")
        last = hist["runs"][-1]["routes"][r["id"]] if hist["runs"] else None
        first = (
            f"first flagged {et(f['had_utc'])} (run {f['cycle']}, cut ~{et(f['from_utc'])} at {f['street']})"
            if f
            else "never flagged"
        )
        now = f"now ~{et(last['from_utc'])}" if last and last["from_utc"] else "now not flagged"
        print(f"{r['id']} {r['label']}: {first}; {now}; cams {len(r['cams'])}")
    for a in hist["camera_alerts"]:
        print(
            f"camera {a['cam_id']} water {et(a['ts'])} route {a['route']} first warning {a['first_warning_had_utc'] and et(a['first_warning_had_utc'])}"
        )


# ---------- picking the routes (once) ----------


def short(name) -> str:
    """'Hammond Drive Northeast' -> 'Hammond Dr NE' (texts stay readable)."""
    from noah.api.agent import ABBREV, DIRECTIONS

    name = (name[0] if isinstance(name, list) else name) or "unnamed road"
    if name == "unnamed road":
        return name
    full_to_abbr = {v: k for k, v in ABBREV.items() if k != "av"}
    return " ".join(
        (a.upper() if w.lower() in DIRECTIONS else a.capitalize())
        if (a := full_to_abbr.get(w.lower()))
        else w
        for w in name.split()
    )


LONG, NEAR = (120, 360), (20, 120)  # seconds of driving before u / after v
FREEWAY = {"motorway", "motorway_link", "trunk_link"}


def through_route(G, u0, v0, k: int = 10) -> list | None:
    """Node path A..u,v..B whose plain fastest A->B path really drives u-v (either direction). B comes from the
    places whose fastest way from u starts with u->v, A from those whose fastest way to v ends with it (so creek side
    streets that arterials bypass still work); endpoints off freeways, 2-6 min out first, farthest apart first."""
    import networkx as nx

    pos = lambda n: (G.nodes[n]["x"], G.nodes[n]["y"])
    d2 = lambda a, b: (pos(a)[0] - pos(b)[0]) ** 2 + (pos(a)[1] - pos(b)[1]) ** 2
    kinds = lambda h: set(h) if isinstance(h, list) else {h}  # OSMnx merges tags into lists
    street = lambda n: any(
        FREEWAY.isdisjoint(kinds(d.get("highway"))) for _, _, d in G.edges(n, data=True)
    )
    for u, v in [(u0, v0), (v0, u0)] if G.has_edge(v0, u0) else [(u0, v0)]:
        tb, pb = nx.single_source_dijkstra(G, u, cutoff=LONG[1], weight="travel_time")
        ta, pa = nx.single_source_dijkstra(
            G.reverse(copy=False), v, cutoff=LONG[1], weight="travel_time"
        )
        bs_all = {n: t for n, t in tb.items() if len(pb[n]) > 1 and pb[n][1] == v and street(n)}
        as_all = {n: t for n, t in ta.items() if len(pa[n]) > 1 and pa[n][1] == u and street(n)}
        for wa, wb in [(LONG, LONG), (LONG, NEAR), (NEAR, LONG), (NEAR, NEAR)]:
            as_ = sorted(
                (n for n, t in as_all.items() if wa[0] <= t <= wa[1]), key=lambda n: -d2(n, v)
            )
            bs = sorted(
                (n for n, t in bs_all.items() if wb[0] <= t <= wb[1]), key=lambda n: -d2(n, u)
            )
            for a, b in sorted(itertools.product(as_[:k], bs[:k]), key=lambda ab: -d2(*ab)):
                path = nx.shortest_path(G, a, b, weight="travel_time")
                if any((x, y) == (u, v) for x, y in itertools.pairwise(path)):
                    return path
    return None


def pick(n: int = 12, near_m: int = 300, cluster_m: int = 1200, cam_m: int = 150) -> None:
    import geopandas as gpd

    from noah.api.dispatch import graph_state
    from noah.api.routing import path_edges, path_line

    G = graph_state()[0]
    live = live_cycles()
    feats = [
        f
        for c in live
        for f in json.loads((config.WEB_DATA / f"flood_{c}.geojson").read_text())["features"]
    ]
    runs = Counter(f["properties"]["seg_id"] for f in feats)
    flag = gpd.GeoDataFrame.from_features(feats, crs=4326).drop_duplicates("seg_id").to_crs(5070)
    flag["runs"] = flag.seg_id.map(runs)
    cams = json.loads(CAMS_CACHE.read_text())
    cg = gpd.GeoDataFrame(
        cams,
        geometry=gpd.points_from_xy([c["lon"] for c in cams], [c["lat"] for c in cams]),
        crs=4326,
    ).to_crs(5070)
    pairs = gpd.sjoin_nearest(
        cg, flag[["seg_id", "name", "runs", "geometry"]], max_distance=near_m, distance_col="m"
    )
    pairs = pairs[~pairs.index.duplicated()].sort_values(["runs", "m"], ascending=[False, True])
    seg_geom = flag.set_index("seg_id").geometry
    anchors, routes = [], []
    for p in pairs.itertuples():
        if len(routes) >= n:
            break
        if any(p.geometry.distance(a) < cluster_m for a in anchors):
            continue
        u, v, _ = (int(x) for x in p.seg_id.split("-"))
        path = through_route(G, u, v)
        if not path:
            log.info("no through route for %s (%s)", p.seg_id, p.title)
            continue
        pe = path_edges(G, path)
        line = path_line(G, path, pe)
        twins = [
            d["seg_id"]
            for x, y in itertools.pairwise(path)
            if G.has_edge(y, x)
            for d in G[y][x].values()
        ]
        line_m = gpd.GeoSeries([line], crs=4326).to_crs(5070).iloc[0]
        near = cg[cg.distance(line_m) <= cam_m].copy()
        near["m"] = near.distance(seg_geom[p.seg_id])
        near = near.sort_values("m").head(4)
        if near.empty:  # the point is camera proof
            log.info("no camera within %d m of the route for %s (%s)", cam_m, p.seg_id, p.title)
            continue
        anchors.append(p.geometry)
        area = (p.title or "Atlanta").split("›")[0].split(":")[0].strip()
        named = [short(d.get("name")) for d in pe if d.get("name")] or ["unnamed road"]
        rid = f"r{len(routes) + 1:02d}"
        routes.append(
            {
                "id": rid,
                "label": f"{area}: {named[0]} → {named[-1]}",
                "via": short(p.name) if isinstance(p.name, str) else "unnamed road",
                "minutes": round(sum(float(d.get("travel_time", 0)) for d in pe) / 60, 1),
                "from": {"lat": G.nodes[path[0]]["y"], "lon": G.nodes[path[0]]["x"]},
                "to": {"lat": G.nodes[path[-1]]["y"], "lon": G.nodes[path[-1]]["x"]},
                "anchor_seg": p.seg_id,
                "anchor_runs_flagged": int(p.runs),
                "seg_ids": sorted({d["seg_id"] for d in pe} | set(twins)),
                "line": [[round(x, 5), round(y, 5)] for x, y in line.coords],
                "cams": [
                    {
                        "id": c.id,
                        "title": c.title,
                        "lat": c.lat,
                        "lon": c.lon,
                        "m_from_anchor": round(c.m),
                    }
                    for c in near.itertuples()
                ],
            }
        )
        log.info(
            "%s %s via %s, %.0f min, %d cams",
            rid,
            routes[-1]["label"],
            routes[-1]["via"],
            routes[-1]["minutes"],
            len(near),
        )
    ROUTES.write_text(
        json.dumps(
            {"picked_utc": iso(pd.Timestamp.now(tz="UTC")), "from_cycles": live, "routes": routes},
            indent=1,
        )
    )
    print(f"{len(routes)} routes -> {ROUTES}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--pick", action="store_true")
    g.add_argument("--once", action="store_true")
    g.add_argument("--every", type=int, help="seconds between checks (e.g. 300)")
    g.add_argument("--report", action="store_true")
    a = p.parse_args()
    if a.pick:
        return pick()
    if a.report:
        return report()
    from dotenv import load_dotenv

    load_dotenv(config.ROOT / ".env")  # NTFY_TOPIC
    while True:
        try:
            run_once()
        except Exception:
            log.exception("route watch pass failed")
        if a.once:
            return
        time.sleep(a.every)


if __name__ == "__main__":
    main()
