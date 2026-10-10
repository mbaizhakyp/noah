"""Past mode: the last ~18 hours for a searched area or route.

Roads: each hourly NWM run's hour-0 analysis = NOAA's model estimate of conditions at that hour
(t_uncertain == 0 / t_flood == 0 in that run's C5). Evidence next to it: USGS gauge readings
(every 15 min) and NWS Local Storm Reports. Cameras and TomTom have no history and are not shown.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

from pyproj import Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform

from noah import config, sources
from noah.api import routing
from noah.sources import adapters

_to_metric = Transformer.from_crs("EPSG:4326", config.METRIC_CRS, always_xy=True).transform
USGS = "https://api.waterdata.usgs.gov/ogcapi/v0/collections"


def past_cycles(now_cycle: str, hours: int = 18) -> list[dict]:
    """Live cycles from (now - hours) up to now, oldest first, each with its offset h (<= 0)."""
    t0 = config.parse_cycle(now_cycle)
    out = []
    for c in routing.cycles_meta()["cycles"]:
        if c.get("event") != "live":
            continue
        h = round((config.parse_cycle(c["cycle"]) - t0).total_seconds() / 3600)
        if -hours <= h <= 0:
            out.append({"h": h, "cycle": c["cycle"], "valid_time": c["issue_time"]})
    return sorted(out, key=lambda x: x["h"])


def hour0_segments(cycle: str, geom_m, limit_m: float) -> list[dict]:
    """Segments in the area/corridor already in the flood band at that run's hour 0."""
    fi = routing.flood_index(cycle)
    feats = routing.flood_state(cycle).features
    out = []
    for i in fi.tree.query(geom_m, predicate="dwithin", distance=limit_m):
        p = fi.props[i]
        if p["t_uncertain"] != 0:
            continue
        out.append(
            {
                "seg_id": p["seg_id"],
                "name": p["name"],
                "state": "flooded" if p["t_flood"] == 0 else "uncertain",
                "geometry": feats[i]["geometry"],
            }
        )
    return out


def gauge_history(ctx: sources.Ctx, hours: int = 18) -> list[dict]:
    """Stage readings for USGS gauges in the area/corridor over the last `hours`."""
    x0, y0, x1, y1 = ctx.bbox
    r = sources.http.get(
        f"{USGS}/latest-continuous/items",
        params={
            "bbox": f"{x0},{y0},{x1},{y1}",
            "parameter_code": "00065",
            "f": "json",
            "limit": 50,
        },
    )
    r.raise_for_status()
    sites = {
        f["properties"]["monitoring_location_id"]: f.get("geometry", {}).get("coordinates")
        for f in r.json().get("features", [])
    }
    start = (datetime.now(UTC) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def one(site):
        rr = sources.http.get(
            f"{USGS}/continuous/items",
            params={
                "monitoring_location_id": site,
                "parameter_code": "00065",
                "time": f"{start}/..",
                "f": "json",
                "limit": 500,
            },
        )
        rr.raise_for_status()
        pts = sorted(
            (f["properties"]["time"], float(f["properties"]["value"]))
            for f in rr.json().get("features", [])
            if f["properties"]["value"] not in (None, "")
        )
        return site, pts

    out = []
    with ThreadPoolExecutor(8) as pool:
        for site, pts in pool.map(one, list(sites)[:12]):
            if len(pts) < 2:
                continue
            lo = min(pts, key=lambda p: p[1])
            hi = max(pts, key=lambda p: p[1])
            xy = sites[site] or [None, None]
            out.append(
                {
                    "site": site,
                    "lat": xy[1],
                    "lon": xy[0],
                    "units": "ft",
                    "first": pts[0][1],
                    "last": pts[-1][1],
                    "min": lo[1],
                    "max": hi[1],
                    "max_time_local": adapters.local(hi[0]),
                    "change_ft": round(pts[-1][1] - pts[0][1], 2),
                    "series": [
                        [t, v] for t, v in pts[::2]
                    ],  # every 30 min is plenty for a sparkline
                    "url": f"https://waterdata.usgs.gov/monitoring-location/{site.split('-')[-1]}/",
                }
            )
    out.sort(key=lambda g: -abs(g["change_ft"]))
    return out


def build(ctx: sources.Ctx, cycle: str, hours: int = 18) -> dict:
    geom = ctx.line if ctx.line is not None else Point(ctx.lon, ctx.lat)
    geom_m = transform(_to_metric, geom)
    limit_m = ctx.radius_km * 1000 if ctx.kind == "area" else ctx.buffer_m
    hrs = []
    for c in past_cycles(cycle, hours):
        segs = hour0_segments(c["cycle"], geom_m, limit_m)
        hrs.append(
            {
                **c,
                "valid_local": adapters.local(c["valid_time"]),
                "segments": segs,
                "flooded": sum(s["state"] == "flooded" for s in segs),
                "uncertain": sum(s["state"] == "uncertain" for s in segs),
            }
        )
    with ThreadPoolExecutor(2) as pool:
        g = pool.submit(gauge_history, ctx, hours)
        rep = pool.submit(adapters.lsr_recent, ctx)
        try:
            gauges = g.result(timeout=15)
        except Exception:  # noqa: BLE001 (evidence is optional; the road estimate still returns)
            gauges = []
        try:
            reports = rep.result(timeout=15)
        except Exception:  # noqa: BLE001
            reports = []
    have = {h["h"] for h in hrs}
    return {
        "cycle": cycle,
        "hours_back": hours,
        "hours": hrs,
        "missing_hours": [h for h in range(-hours, 1) if h not in have],
        "gauges": gauges,
        "reports": reports,
        "note": "Past roads are NOAA's model estimate for each hour (the analysis at the start of each hourly run), "
        "not confirmed flooding. Gauge readings and storm reports are observations.",
    }


def area(lat: float, lon: float, cycle: str | None = None) -> dict:
    cycle = cycle or routing.current_cycle()
    if reason := routing.coverage_state(Point(lon, lat), *routing.coverage()):
        return {"state": reason, "cycle": cycle, "hours": [], "gauges": [], "reports": []}
    return {"state": "ok", **build(sources.Ctx("area", lat, lon), cycle)}


def route(a_lat, a_lon, b_lat, b_lon, cycle: str | None = None) -> dict:
    cycle = cycle or routing.current_cycle()
    rt = routing.route(a_lat, a_lon, b_lat, b_lon, 0, cycle)
    if not rt.get("geometry"):
        return {"state": rt["state"], "cycle": cycle, "hours": [], "gauges": [], "reports": []}
    line = LineString(shape(rt["geometry"]).coords)
    mid = line.interpolate(0.5, normalized=True)
    return {"state": "ok", **build(sources.Ctx("route", mid.y, mid.x, line=line), cycle)}
