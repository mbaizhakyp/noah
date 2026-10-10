"""Spec 006: flood states near a point (/status) and flood-avoiding routes (/route).

Shares the graph + flood loaders and the blocking rule with spec 014 (dispatch.py), so the
graph is held in memory once (integration items I4/I5).
"""

import itertools
import json
import logging
import os
from dataclasses import dataclass
from functools import lru_cache

import networkx as nx
import numpy as np
import pandas as pd
import shapely
from pyproj import Transformer
from shapely.geometry import LineString, Point, shape
from shapely.ops import transform

from noah import config
from noah.api.dispatch import (
    blocked_weight,
    cycles_meta,
    flood_state,
    graph_state,
    nearest_node,
)

log = logging.getLogger("routing")
_to_metric = Transformer.from_crs("EPSG:4326", config.METRIC_CRS, always_xy=True).transform
SEVERITY = {"flooded": 2, "uncertain": 1, "no_forecast_flooding": 0}


# ---------- which forecast ----------


def latest_live(cycles: list[dict]) -> str | None:
    """Newest cycle tagged event == "live" (everyday app: always the latest forecast)."""
    live = sorted((c for c in cycles if c.get("event") == "live"), key=lambda c: c["issue_time"])
    return live[-1]["cycle"] if live else None


def current_cycle() -> str:
    """Env NOAH_CYCLE pins a cycle (testing); otherwise the newest live cycle in C6."""
    c = os.environ.get("NOAH_CYCLE") or latest_live(cycles_meta()["cycles"])
    if not c:
        raise LookupError("no live forecast published yet")
    return c


# ---------- pure logic ----------


def seg_state(t_uncertain: int | None, t_flood: int | None, h: int) -> str:
    """State of one segment at lead hour h (02-ARCHITECTURE §4 C9)."""
    if t_flood is not None and t_flood <= h:
        return "flooded"
    if t_uncertain is not None and t_uncertain <= h:
        return "uncertain"
    return "no_forecast_flooding"


def worst(states: list[str]) -> str:
    return max(states, key=SEVERITY.get, default="no_forecast_flooding")


def coverage_state(pt: Point, georgia, processed) -> str | None:
    """None if Noah has road-level forecasts at pt, else the reason it doesn't (CC6)."""
    if not georgia.contains(pt):
        return "out_of_coverage"
    if not processed.contains(pt):
        return "no_road_forecast"
    return None


def trip_nodes(ids: np.ndarray, xy: np.ndarray, a: tuple, b: tuple, margin_km: float):
    """Graph nodes inside the bbox of points a, b (lon, lat) expanded by margin_km."""
    lat0 = (a[1] + b[1]) / 2
    dlat = margin_km / 110.54
    dlon = margin_km / (111.32 * np.cos(np.radians(lat0)))
    lo_x, hi_x = min(a[0], b[0]) - dlon, max(a[0], b[0]) + dlon
    lo_y, hi_y = min(a[1], b[1]) - dlat, max(a[1], b[1]) + dlat
    m = (xy[:, 0] >= lo_x) & (xy[:, 0] <= hi_x) & (xy[:, 1] >= lo_y) & (xy[:, 1] <= hi_y)
    return ids[m]


def shortest(G, src, dst, weight):
    """Node path or None. `weight` may be a networkx weight fn that hides edges by returning None."""
    try:
        return nx.shortest_path(G, src, dst, weight=weight)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None


def best_edge(G, u, v, t_uncertain: dict | None, limit: int | None) -> dict:
    """Fastest parallel edge u->v, skipping blocked ones when a limit is given."""
    best = None
    for d in G[u][v].values():
        t = t_uncertain.get(d.get("seg_id")) if t_uncertain is not None else None
        if limit is not None and t is not None and t <= limit:
            continue
        if best is None or d.get("travel_time", 1e9) < best.get("travel_time", 1e9):
            best = d
    return best or next(iter(G[u][v].values()))


def path_edges(G, path, t_uncertain=None, limit=None) -> list[dict]:
    return [best_edge(G, u, v, t_uncertain, limit) for u, v in itertools.pairwise(path)]


def path_line(G, path, edges: list[dict]) -> LineString:
    """Concatenate edge geometries along the path, falling back to node coordinates."""
    coords = []
    for (u, v), d in zip(itertools.pairwise(path), edges, strict=True):
        g = d.get("geometry")
        pts = (
            list(g.coords)
            if g is not None
            else [
                (G.nodes[u]["x"], G.nodes[u]["y"]),
                (G.nodes[v]["x"], G.nodes[v]["y"]),
            ]
        )
        coords.extend(pts if not coords else pts[1:])
    return LineString(coords)


# ---------- loaded state ----------


@dataclass
class FloodIndex:
    """One cycle's C5 segments with a metric STRtree for radius / corridor queries."""

    cycle: str
    issue_time: pd.Timestamp
    props: list[dict]
    geoms_m: np.ndarray
    tree: shapely.STRtree


@lru_cache(maxsize=1)
def coverage():
    """(Georgia polygon, processed-area polygon). Processed area = C7 (HUC8 outlines once CC6 lands)."""
    ga = shape(json.loads(config.GEORGIA_GEOJSON.read_text())["features"][0]["geometry"])
    c7 = json.loads((config.WEB_DATA / "aoi.geojson").read_text())["features"]
    hucs = [shape(f["geometry"]) for f in c7 if "huc8" in f["properties"]]
    processed = shapely.union_all(hucs or [shape(f["geometry"]) for f in c7])  # all basins in C7
    return ga, processed


@lru_cache(maxsize=8)
def flood_index(cycle: str) -> FloodIndex:
    fl = flood_state(cycle)
    geoms = np.array([transform(_to_metric, shape(f["geometry"])) for f in fl.features])
    return FloodIndex(
        cycle, fl.issue_time, [f["properties"] for f in fl.features], geoms, shapely.STRtree(geoms)
    )


def iso(t: pd.Timestamp) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def eta(fi: FloodIndex, p: dict, state: str) -> str | None:
    t = p["t_flood"] if state == "flooded" else p["t_uncertain"]
    return None if t is None else iso(fi.issue_time + pd.Timedelta(hours=int(t)))


def segment_row(fi: FloodIndex, p: dict, h: int) -> dict:
    s = seg_state(p["t_uncertain"], p["t_flood"], h)
    return {"seg_id": p["seg_id"], "name": p["name"], "state": s, "eta_utc": eta(fi, p, s)}


# ---------- endpoint logic ----------


def status(lat: float, lon: float, hours: int, cycle: str | None = None) -> dict:
    cycle = cycle or current_cycle()
    pt = Point(lon, lat)
    reason = coverage_state(pt, *coverage())
    if reason:
        return {"state": reason, "segments": [], "cycle": cycle}
    fi = flood_index(cycle)
    hours = max(0, min(int(hours), config.MAX_LEAD_H))
    pm = transform(_to_metric, pt)
    hits = fi.tree.query(pm, predicate="dwithin", distance=config.ALERT_RADIUS_KM * 1000)
    rows = []
    for i in hits:
        p = fi.props[i]
        if p["t_uncertain"] is None or p["t_uncertain"] > hours:
            continue
        rows.append({**segment_row(fi, p, hours), "distance_m": round(fi.geoms_m[i].distance(pm))})
    rows.sort(key=lambda r: r["distance_m"])
    return {"state": worst([r["state"] for r in rows]), "segments": rows, "cycle": cycle}


def map_url(cycle: str, depart_h: int, a: tuple, b: tuple) -> str:
    """C10. Falls back to the API origin, which also serves web/."""
    base = (config.WEB_BASE or config.API_BASE).rstrip("/")
    return (
        f"{base}/?cycle={cycle}&t={depart_h}&from={a[1]:.5f},{a[0]:.5f}"
        f"&to={b[1]:.5f},{b[0]:.5f}&api={config.API_BASE.rstrip('/')}"
    )


def route(
    a_lat,
    a_lon,
    b_lat,
    b_lon,
    depart_h: int,
    cycle: str | None = None,
    extra_blocked: frozenset = frozenset(),
) -> dict:
    """extra_blocked: seg_ids blocked from now by live hazards (TomTom flooding/closure, camera water; spec 015)."""
    cycle = cycle or current_cycle()
    a, b = (a_lon, a_lat), (b_lon, b_lat)
    empty = {"geometry": None, "minutes": None, "avoided": [], "corridor": [], "cycle": cycle}
    if depart_h > config.MAX_LEAD_H:
        return {"state": "beyond_forecast_window", **empty, "map_url": None}
    depart_h = max(0, int(depart_h))
    for pt in (a, b):
        reason = coverage_state(Point(*pt), *coverage())
        if reason:
            return {"state": reason, **empty, "map_url": None}

    G, ids, xy, *_ = graph_state()
    fl = flood_state(cycle)
    limit = depart_h + config.ROUTE_BUFFER_H
    tu = {**fl.t_uncertain, **dict.fromkeys(extra_blocked, -1)}  # live hazards: blocked from now
    weight = blocked_weight(tu, depart_h)
    src, dst = nearest_node(ids, xy, *a), nearest_node(ids, xy, *b)
    path = sub = None
    for margin in (config.TRIP_BOX_MARGIN_KM, config.TRIP_BOX_RETRY_KM):
        sub = G.subgraph(trip_nodes(ids, xy, a, b, margin))
        path = shortest(sub, src, dst, weight)
        if path:
            break
    url = map_url(cycle, depart_h, a, b)
    if not path:
        return {"state": "no_route", **empty, "map_url": url}

    edges = path_edges(sub, path, tu, limit)
    line = path_line(sub, path, edges)
    free = shortest(sub, src, dst, "travel_time") or []
    avoided = sorted(
        {
            d["seg_id"]
            for d in path_edges(sub, free)
            if (t := tu.get(d.get("seg_id"))) is not None and t <= limit
        }
    )
    fi = flood_index(cycle)
    line_m = transform(_to_metric, line)
    near = fi.tree.query(line_m, predicate="dwithin", distance=config.CORRIDOR_BUFFER_M)
    corridor = sorted(
        (segment_row(fi, fi.props[i], depart_h) for i in near),
        key=lambda r: (-SEVERITY[r["state"]], r["eta_utc"] or ""),
    )
    live = sorted(set(avoided) & set(extra_blocked))
    return {
        "live_blocked": live,
        "state": "route_found",
        "geometry": shapely.geometry.mapping(line),
        "minutes": round(sum(float(d.get("travel_time", 0)) for d in edges) / 60, 1),
        "avoided": avoided,
        "corridor": corridor,
        "cycle": cycle,
        "map_url": url,
    }
