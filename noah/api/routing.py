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

    @property
    def by_id(self) -> dict:
        if not hasattr(self, "_by_id"):
            self._by_id = {p["seg_id"]: p for p in self.props}
        return self._by_id


def _basins_mtime() -> float:
    p = config.BASINS_GEOJSON
    return p.stat().st_mtime if p.exists() else 0.0


def coverage():
    return _coverage(
        _basins_mtime()
    )  # re-read when a basin finishes building (spec 016), no restart


@lru_cache(maxsize=1)
def _coverage(_mtime: float):
    """(Georgia polygon, processed-area polygon). Processed area = C7 (metro) + every spec-016 basin."""
    ga = shape(json.loads(config.GEORGIA_GEOJSON.read_text())["features"][0]["geometry"])
    c7 = json.loads((config.WEB_DATA / "aoi.geojson").read_text())["features"]
    hucs = [shape(f["geometry"]) for f in c7 if "huc8" in f["properties"]]
    processed = shapely.union_all(hucs or [shape(f["geometry"]) for f in c7])  # all basins in C7
    extra = [poly for _, poly in basins()]
    if extra:
        processed = shapely.union_all([processed, *extra])
    return ga, processed


# ---------- spec 016: neighbouring basins, each with its own graph, loaded when a trip touches it ----------


def basins() -> list[tuple[str, shapely.Geometry]]:
    return _basins(_basins_mtime())


@lru_cache(maxsize=1)
def _basins(_mtime: float) -> list[tuple[str, shapely.Geometry]]:
    """[(basin name, polygon)] from web/data/basins.geojson (written by build_segments --basin)."""
    p = config.BASINS_GEOJSON
    if not p.exists():
        return []
    by = {}
    for f in json.loads(p.read_text())["features"]:
        by.setdefault(f["properties"].get("basin"), []).append(shape(f["geometry"]))
    # Only basins built on this machine (same test as live.load_inputs): basins.geojson is committed, the data
    # isn't, and a basin without data would answer "no forecast flooding" instead of "no road forecast" (I18).
    built = lambda n: (config.basin_dir(n) / "seg_thresholds.parquet").exists()
    return [(name, shapely.union_all(polys)) for name, polys in by.items() if name and built(name)]


def basin_of(pt: Point) -> str | None:
    """Basin name containing pt, or None for metro (C7)."""
    for name, poly in basins():
        if poly.contains(pt):
            return name
    return None


@lru_cache(maxsize=2)
def basin_graph(name: str):
    import osmnx as ox

    G = ox.load_graphml(config.basin_dir(name) / "graph.graphml")
    ids = np.array(list(G.nodes))
    xy = np.array([(G.nodes[n]["x"], G.nodes[n]["y"]) for n in ids])
    log.info("basin graph %s loaded: %d nodes, %d edges", name, len(G), G.number_of_edges())
    return G, ids, xy


@lru_cache(maxsize=1)
def composed_graph(names: frozenset):
    """Areas joined for a trip that crosses between them (their 2 km buffers overlap where they touch)."""
    parts = [basin_graph(n) if n else graph_state()[:3] for n in sorted(names, key=str)]
    G = nx.compose_all([p[0] for p in parts])
    ids = np.array(list(G.nodes))
    xy = np.array([(G.nodes[n]["x"], G.nodes[n]["y"]) for n in ids])
    return G, ids, xy


def graph_for(a: tuple, b: tuple):
    return graph_for_points([a, b])


def graph_for_points(pts: list[tuple]):
    """(G, ids, xy) covering every point: metro alone, one basin alone, or every area the points' box
    touches composed together (areas only connect where their 2 km buffers overlap, so a trip from
    one ring basin to another may need metro and a neighbour in between)."""
    ends = {basin_of(Point(*p)) for p in pts}
    if ends == {None}:
        return graph_state()[:3]
    if len(ends) == 1:
        return basin_graph(next(iter(ends)))
    margin = config.TRIP_BOX_MARGIN_KM / 110.54
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    box = shapely.box(min(xs) - margin, min(ys) - margin, max(xs) + margin, max(ys) + margin)
    names = {name for name, poly in basins() if poly.intersects(box)} | ends | {None}
    return composed_graph(frozenset(names))


def box_nodes(ids: np.ndarray, xy: np.ndarray, pts: list[tuple], margin_km: float):
    """Graph nodes inside the bbox of all points expanded by margin_km (trip_nodes for N points)."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    lat0 = sum(ys) / len(ys)
    dlat = margin_km / 110.54
    dlon = margin_km / (111.32 * np.cos(np.radians(lat0)))
    m = (
        (xy[:, 0] >= min(xs) - dlon)
        & (xy[:, 0] <= max(xs) + dlon)
        & (xy[:, 1] >= min(ys) - dlat)
        & (xy[:, 1] <= max(ys) + dlat)
    )
    return ids[m]


def plan(depot: tuple, stops: list[tuple], cycle: str | None = None) -> dict:
    """Spec 009/014 for the map's stops: from one depot, when does each stop get cut off by forecast
    flooding? Per stop: no_forecast_flooding / go_before (cut_h = first hour it is unreachable) / hold.
    Same rule as the dispatch board (dispatch.reach_by_hour + verdict), on whatever areas the points touch."""
    from noah.api.dispatch import verdict

    cycle = cycle or current_cycle()
    pts = [depot, *stops]
    reasons = [coverage_state(Point(*p), *coverage()) for p in pts]
    fresh(cycle)
    fi = flood_index(cycle)
    base = {"cycle": cycle, "issue_time": iso(fi.issue_time)}
    if reasons[0]:
        return {"state": reasons[0], "stops": [], **base}
    G, ids, xy = graph_for_points([p for p, r in zip(pts, reasons) if not r])
    tu = flood_state(cycle).t_uncertain
    sub = G.subgraph(box_nodes(ids, xy, pts, config.TRIP_BOX_MARGIN_KM))
    src = nearest_node(ids, xy, *depot)
    # only the flagged roads inside the box matter: one Dijkstra per distinct blocked set, 3 h travel cutoff
    in_box = {d.get("seg_id") for _, _, d in sub.edges(data=True)}
    tu_box = {s: t for s, t in tu.items() if s in in_box}
    reach, cache = {}, {}
    for h in range(config.MAX_LEAD_H + 1):
        key = frozenset(s for s, t in tu_box.items() if t <= h + config.ROUTE_BUFFER_H)
        if key not in cache:
            cache[key] = nx.single_source_dijkstra_path_length(
                sub, src, cutoff=3 * 3600, weight=blocked_weight(tu_box, h)
            )
        reach[h] = cache[key]
    out = []
    for i, (p, reason) in enumerate(zip(stops, reasons[1:])):
        if reason:
            out.append({"i": i, "state": reason, "cut_h": None, "cut_utc": None, "minutes": None})
            continue
        n = nearest_node(ids, xy, *p)
        sids = tuple(
            d.get("seg_id")
            for _, _, d in list(sub.out_edges(n, data=True)) + list(sub.in_edges(n, data=True))
            if d.get("seg_id")
        )
        v = verdict((n, n, sids), reach, True, tu)
        cut = v["cut_h"]
        out.append(
            {
                "i": i,
                **v,
                "cut_utc": None
                if cut is None
                else iso(fi.issue_time + pd.Timedelta(hours=int(cut))),
            }
        )
    # earliest-cut-first is the order that loses the fewest stops to the water
    order = sorted(
        range(len(out)),
        key=lambda i: (
            out[i]["state"] == "out_of_coverage",
            out[i]["cut_h"] if out[i]["cut_h"] is not None else 99,
            out[i]["minutes"] or 0,
        ),
    )
    return {"state": "ok", "stops": out, "order": order, **base}


@lru_cache(maxsize=8)
def flood_index(cycle: str) -> FloodIndex:
    fl = flood_state(cycle)
    geoms = np.array([transform(_to_metric, shape(f["geometry"])) for f in fl.features])
    return FloodIndex(
        cycle, fl.issue_time, [f["properties"] for f in fl.features], geoms, shapely.STRtree(geoms)
    )


_c5_mtimes: dict[str, float] = {}


def fresh(cycle: str) -> None:
    """Drop the cached C5 for a cycle whose file was rewritten (live --refresh after a basin is built)."""
    p = config.WEB_DATA / f"flood_{cycle}.geojson"
    m = p.stat().st_mtime if p.exists() else 0.0
    if _c5_mtimes.get(cycle) not in (None, m):
        flood_state.cache_clear()
        flood_index.cache_clear()
        log.info("C5 %s changed on disk, caches cleared", cycle)
    _c5_mtimes[cycle] = m


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
    fresh(cycle)
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
    corridor_m: int | None = None,
) -> dict:
    """extra_blocked: seg_ids blocked from now by live hazards (TomTom flooding/closure, camera water; spec 015).
    corridor_m: how far around the route to list flagged roads (default CC6's 1 km; the map asks for more)."""
    cycle = cycle or current_cycle()
    corridor_m = min(5000, max(500, int(corridor_m or config.CORRIDOR_BUFFER_M)))
    a, b = (a_lon, a_lat), (b_lon, b_lat)
    empty = {"geometry": None, "minutes": None, "avoided": [], "corridor": [], "cycle": cycle}
    if depart_h > config.MAX_LEAD_H:
        return {"state": "beyond_forecast_window", **empty, "map_url": None}
    depart_h = max(0, int(depart_h))
    for pt in (a, b):
        reason = coverage_state(Point(*pt), *coverage())
        if reason:
            return {"state": reason, **empty, "map_url": None}

    from noah.api import trip  # lazy: trip imports routing

    G, ids, xy = graph_for(a, b)
    fresh(cycle)
    fl = flood_state(cycle)
    tu = {**fl.t_uncertain, **dict.fromkeys(extra_blocked, -1)}  # live hazards: blocked from now
    src, dst = nearest_node(ids, xy, *a), nearest_node(ids, xy, *b)
    # spec 019: a road is blocked by the hour the driver reaches it, not the hour they leave
    path = edges = net = None
    for margin in (config.TRIP_BOX_MARGIN_KM, config.TRIP_BOX_RETRY_KM):
        net = (
            trip.Net(G, trip_nodes(ids, xy, a, b, margin), tu)
            if extra_blocked
            else trip.net_for(cycle, G, ids, xy, [a, b], margin)
        )
        dist, pred = trip.td_dijkstra(net, src, depart_h, targets=[dst])
        if dst in dist:
            path, keys = trip.path_from(pred, dst)
            edges = trip.edges_of(G, path, keys)
            break
    url = map_url(cycle, depart_h, a, b)
    fi = flood_index(cycle)
    _, fpred = trip.td_dijkstra(net, src, depart_h, targets=[dst], ignore_block=True)
    free, fkeys = trip.path_from(fpred, dst) if dst in fpred else ([], [])
    fedges = trip.edges_of(G, free, fkeys) if len(free) > 1 else []
    if not path:
        # no way around: still return the usual way and every flagged road it crosses, so the map can
        # show *why* instead of nothing (the state stays no_route; fields are additive, CC8)
        if len(free) < 2:
            return {"state": "no_route", **empty, "map_url": url}
        uline = path_line(G, free, fedges)
        cut_ids = set(trip.blocked_on_path(fedges, tu, depart_h))
        crosses = [
            segment_row(fi, p, depart_h)
            for d in fedges
            if d.get("seg_id") in cut_ids and (p := fi.by_id.get(d.get("seg_id"))) is not None
        ]
        near = fi.tree.query(transform(_to_metric, uline), predicate="dwithin", distance=corridor_m)
        corridor = sorted(
            (segment_row(fi, fi.props[i], depart_h) for i in near),
            key=lambda r: (-SEVERITY[r["state"]], r["eta_utc"] or ""),
        )
        return {
            "state": "no_route",
            **empty,
            "corridor": corridor,
            "corridor_m": corridor_m,
            "usual_geometry": shapely.geometry.mapping(uline),
            "usual_minutes": round(sum(float(d.get("travel_time", 0)) for d in fedges) / 60, 1),
            "crosses": sorted(crosses, key=lambda r: r["eta_utc"] or ""),
            "map_url": url,
        }

    line = path_line(G, path, edges)
    avoided = trip.blocked_on_path(
        fedges, tu, depart_h
    )  # fastest way, cut where it reaches each road
    line_m = transform(_to_metric, line)
    near = fi.tree.query(line_m, predicate="dwithin", distance=corridor_m)
    corridor = sorted(
        (segment_row(fi, fi.props[i], depart_h) for i in near),
        key=lambda r: (-SEVERITY[r["state"]], r["eta_utc"] or ""),
    )
    live = sorted(set(avoided) & set(extra_blocked))
    # the usual (fastest) way when it differs: the map draws it dashed so the detour reads as a choice
    usual = path_line(G, free, fedges) if avoided and len(free) > 1 else None
    return {
        "live_blocked": live,
        "state": "route_found",
        "geometry": shapely.geometry.mapping(line),
        "usual_geometry": shapely.geometry.mapping(usual) if usual is not None else None,
        "corridor_m": corridor_m,
        "minutes": round(sum(float(d.get("travel_time", 0)) for d in edges) / 60, 1),
        "avoided": avoided,
        "corridor": corridor,
        "cycle": cycle,
        "map_url": url,
    }
