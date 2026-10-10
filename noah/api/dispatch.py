"""Spec 014: small-business dispatch board + agency barricade list (Replit Small Business entry).

Reads:  C4 graph (data/interim/graph.graphml, else fixtures/graph.graphml.gz), C5/C6 in web/data, AOI.
Serves: C13 POST /dispatch, GET /barricades (FastAPI `router`; Priyanshu's app.py mounts it, I3).
Standalone test server: uv run python -m noah.api.dispatch --serve   (port 8001, also serves web/)
"""

import argparse
import gzip
import json
import logging
import os
import shutil
from dataclasses import dataclass
from functools import lru_cache

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
import shapely
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from shapely.geometry import Point, shape

from noah import config

log = logging.getLogger("dispatch")
router = APIRouter()
N_LEADS = config.MAX_LEAD_H + 1


# ---------- loading (shared-state candidates for integration item I4) ----------


def load_graph() -> nx.MultiDiGraph:
    """C4 from data/interim, else unzip the committed fixture (I1)."""
    p = config.DATA_INTERIM / "graph.graphml"
    if not p.exists():
        p = config.DATA_INTERIM / "graph_from_fixture.graphml"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(config.ROOT / "fixtures" / "graph.graphml.gz") as f, open(p, "wb") as o:
                shutil.copyfileobj(f, o)
    return ox.load_graphml(p)


def cycles_meta() -> dict:
    return json.loads((config.WEB_DATA / "cycles.json").read_text())


def active_cycle() -> str:
    """I6: env NOAH_CYCLE, else C6 demo_cycle."""
    return os.environ.get("NOAH_CYCLE") or cycles_meta()["demo_cycle"]


@dataclass
class Flood:
    cycle: str
    issue_time: pd.Timestamp
    t_uncertain: dict  # seg_id -> lead hour
    features: list


def load_flood(cycle: str) -> Flood:
    path = config.WEB_DATA / f"flood_{cycle}.geojson"
    if not path.exists():
        raise HTTPException(404, f"no forecast file for cycle {cycle}")
    feats = json.loads(path.read_text())["features"]
    tu = {f["properties"]["seg_id"]: f["properties"]["t_uncertain"] for f in feats}
    return Flood(cycle, pd.Timestamp(config.parse_cycle(cycle)), tu, feats)


@lru_cache(maxsize=1)
def graph_state():
    G = load_graph()
    ids = np.array(list(G.nodes))
    xy = np.array([(G.nodes[n]["x"], G.nodes[n]["y"]) for n in ids])
    aoi = shape(
        json.loads((config.WEB_DATA / "aoi.geojson").read_text())["features"][0]["geometry"]
    )
    edges = ox.graph_to_gdfs(G, nodes=False).reset_index()[["u", "v", "seg_id", "geometry"]]
    tree = shapely.STRtree(edges.geometry.values)
    log.info("graph loaded: %d nodes, %d edges", len(G), G.number_of_edges())
    return G, ids, xy, aoi, edges, tree


def nearest_edge(edges, tree, lon: float, lat: float) -> tuple:
    """(u, v, seg_id, reverse seg_ids) of the road segment closest to the point: a delivery address sits on a street."""
    i = int(tree.nearest(Point(lon, lat)))
    u, v, sid = edges.u.iat[i], edges.v.iat[i], edges.seg_id.iat[i]
    twins = tuple(edges.seg_id[(edges.u == v) & (edges.v == u)])  # same street, other direction
    return u, v, (sid, *twins)


@lru_cache(maxsize=8)
def flood_state(cycle: str) -> Flood:
    return load_flood(cycle)


# ---------- pure logic ----------


def blocked_weight(t_uncertain: dict, depart_h: int, buffer_h: int = config.ROUTE_BUFFER_H):
    """networkx weight fn: travel_time, or None (= edge removed) if forecast uncertain/flooded by depart_h + buffer.
    Same rule as /route (I5)."""
    limit = depart_h + buffer_h

    def w(u, v, keyed):
        best = None
        for d in keyed.values():
            t = t_uncertain.get(d.get("seg_id"))
            if t is not None and t <= limit:
                continue
            tt = float(d.get("travel_time", 1e9))
            best = tt if best is None or tt < best else best
        return best

    return w


def nearest_node(ids: np.ndarray, xy: np.ndarray, lon: float, lat: float):
    """Nearest graph node (equirectangular; fine at city scale, no extra deps)."""
    dx = (xy[:, 0] - lon) * np.cos(np.radians(lat))
    return ids[np.argmin(dx**2 + (xy[:, 1] - lat) ** 2)]


def reach_by_hour(G, src, t_uncertain: dict, hours=range(N_LEADS)) -> dict[int, dict]:
    """depart hour -> {node: seconds} reachable from src. Blocking only grows with h (sticky states),
    so we stop early once nothing changes... but we keep it simple: one Dijkstra per distinct limit."""
    out, cache = {}, {}
    for h in hours:
        limit = h + config.ROUTE_BUFFER_H
        blocked = frozenset(s for s, t in t_uncertain.items() if t <= limit)
        if blocked not in cache:
            cache[blocked] = nx.single_source_dijkstra_path_length(
                G, src, weight=blocked_weight(t_uncertain, h)
            )
        out[h] = cache[blocked]
    return out


def verdict(stop_edge, reach: dict[int, dict], inside: bool, t_uncertain: dict) -> dict:
    """Per stop on edge (u, v, seg_ids): reachable at hour h if its own street isn't blocked and u or v is reachable.
    -> out_of_coverage / no_forecast_flooding / go_before (first cut hour) / hold."""
    if not inside:
        return {"state": "out_of_coverage", "cut_h": None, "minutes": None}
    u, v, sids = stop_edge
    t_own = min((t_uncertain[s] for s in sids if s in t_uncertain), default=None)
    hours = sorted(reach)

    def ok_at(h):
        own_open = t_own is None or t_own > h + config.ROUTE_BUFFER_H
        return own_open and (u in reach[h] or v in reach[h])

    ok = [ok_at(h) for h in hours]
    r0 = reach[hours[0]]
    minutes = round(min(r0.get(u, np.inf), r0.get(v, np.inf)) / 60, 1) if ok[0] else None
    if all(ok):
        return {"state": "no_forecast_flooding", "cut_h": None, "minutes": minutes}
    if ok[0]:
        return {"state": "go_before", "cut_h": hours[ok.index(False)], "minutes": minutes}
    return {"state": "hold", "cut_h": hours[0], "minutes": None}


def barricade_rows(features: list, lengths: dict, issue: pd.Timestamp) -> list[dict]:
    """Forecast-flooded streets grouped by name: first flood hour, segment count, length (both directions counted once)."""
    rows = []
    for f in features:
        p = f["properties"]
        if p["t_flood"] is None or not p["name"]:
            continue
        u, v, k = p["seg_id"].split("-")
        rows.append(
            {
                "street": p["name"],
                "pair": (min(u, v), max(u, v), k),
                "t_flood": p["t_flood"],
                "length_m": lengths.get(p["seg_id"], 0.0),
            }
        )
    if not rows:
        return []
    df = pd.DataFrame(rows).drop_duplicates("pair")
    g = df.groupby("street").agg(
        segments=("pair", "count"), length_m=("length_m", "sum"), t_flood=("t_flood", "min")
    )
    g = g.reset_index().sort_values(["t_flood", "length_m"], ascending=[True, False])
    return [
        {
            "street": r.street,
            "segments": int(r.segments),
            "length_m": round(float(r.length_m)),
            "first_flood_utc": (issue + pd.Timedelta(hours=int(r.t_flood))).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "state": "flooded",
        }
        for r in g.itertuples()
    ]


# ---------- API (C13) ----------


class Place(BaseModel):
    label: str = ""
    lat: float
    lon: float


class Stop(Place):
    id: str


class DispatchRequest(BaseModel):
    cycle: str | None = None
    depot: Place
    stops: list[Stop]


def iso(t: pd.Timestamp) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def route_and_cut(
    G, paths: dict, dist: dict, stop_edge, stop_pt, t_uncertain, cut_limit, names
) -> tuple:
    """Route line (depot -> stop) along `paths`, and where it gets cut: the first segment on it (or the stop's own
    street) whose t_uncertain <= cut_limit. -> (coords | None, cut dict | None)."""
    from noah.api.routing import path_edges, path_line  # lazy: routing imports this module

    u, v, sids = stop_edge
    ends = [n for n in (u, v) if n in dist]
    if not ends:
        return None, None
    end = min(ends, key=dist.get)
    nodes = paths[end]
    seg_edges = path_edges(G, nodes) if len(nodes) > 1 else []
    coords = (
        [list(c) for c in path_line(G, nodes, seg_edges).coords]
        if len(nodes) > 1
        else [[G.nodes[end]["x"], G.nodes[end]["y"]]]
    )
    coords.append([stop_pt[0], stop_pt[1]])
    cut = None
    if cut_limit is not None:
        candidates = [(e.get("seg_id"), e) for e in seg_edges] + [(s, None) for s in sids]
        for sid, e in candidates:
            tu = t_uncertain.get(sid)
            if tu is not None and tu <= cut_limit:
                if e is not None and e.get("geometry") is not None:
                    mid = e["geometry"].interpolate(0.5, normalized=True)
                    lon, lat = mid.x, mid.y
                else:
                    lon, lat = stop_pt
                cut = {
                    "lon": round(lon, 5),
                    "lat": round(lat, 5),
                    "street": names.get(sid),
                    "t_uncertain": tu,
                }
                break
    return [[round(x, 5), round(y, 5)] for x, y in coords], cut


@router.post("/dispatch")
def dispatch(req: DispatchRequest) -> dict:
    G, ids, xy, aoi, edges, tree = graph_state()
    fl = flood_state(req.cycle or active_cycle())
    if len(req.stops) > 50:
        raise HTTPException(400, "max 50 stops")
    if not aoi.contains(Point(req.depot.lon, req.depot.lat)):
        raise HTTPException(
            400, "depot is outside Noah's coverage (Peachtree Creek watershed, Atlanta)"
        )
    src = nearest_node(ids, xy, req.depot.lon, req.depot.lat)
    reach = reach_by_hour(G, src, fl.t_uncertain)
    dist0, paths0 = nx.single_source_dijkstra(G, src, weight=blocked_weight(fl.t_uncertain, 0))
    free = None  # unconstrained shortest paths, only needed to show where a held route is cut
    names = {f["properties"]["seg_id"]: f["properties"]["name"] for f in fl.features}
    buf = config.ROUTE_BUFFER_H
    out = []
    for s in req.stops:
        inside = aoi.contains(Point(s.lon, s.lat))
        stop_edge = nearest_edge(edges, tree, s.lon, s.lat) if inside else None
        v = verdict(stop_edge, reach, inside, fl.t_uncertain)
        cut = None if v["cut_h"] is None else iso(fl.issue_time + pd.Timedelta(hours=v["cut_h"]))
        route, cut_at = None, None
        if v["state"] in ("go_before", "no_forecast_flooding"):
            limit = v["cut_h"] + buf if v["state"] == "go_before" else None
            route, cut_at = route_and_cut(
                G, paths0, dist0, stop_edge, (s.lon, s.lat), fl.t_uncertain, limit, names
            )
        elif v["state"] == "hold":
            if free is None:
                free = nx.single_source_dijkstra(G, src, weight="travel_time")
            route, cut_at = route_and_cut(
                G, free[1], free[0], stop_edge, (s.lon, s.lat), fl.t_uncertain, buf, names
            )
        if cut_at:
            cut_at["impassable_from_utc"] = iso(
                fl.issue_time + pd.Timedelta(hours=int(cut_at.pop("t_uncertain")))
            )
        out.append(
            {
                "id": s.id,
                "label": s.label,
                "lat": s.lat,
                "lon": s.lon,
                "state": v["state"],
                "go_before_utc": cut if v["state"] == "go_before" else None,
                "cut_from_utc": cut if v["state"] == "hold" else None,
                "minutes": v["minutes"],
                "cut_h": v["cut_h"],
                "route": route,
                "cut_at": cut_at,
            }
        )
    return {
        "cycle": fl.cycle,
        "issue_time": iso(fl.issue_time),
        "valid_until": iso(fl.issue_time + pd.Timedelta(hours=config.MAX_LEAD_H)),
        "depot": req.depot.model_dump(),
        "stops": out,
    }


@router.get("/barricades")
def barricades(cycle: str | None = None) -> list[dict]:
    G, *_ = graph_state()
    fl = flood_state(cycle or active_cycle())
    lengths = {d["seg_id"]: float(d.get("length", 0)) for _, _, d in G.edges(data=True)}
    return barricade_rows(fl.features, lengths, fl.issue_time)


# ---------- sample data + standalone server ----------


def node_label(G, n) -> str:
    names = []
    for _, _, d in list(G.out_edges(n, data=True)) + list(G.in_edges(n, data=True)):
        nm = d.get("name")
        nm = nm[0] if isinstance(nm, list) else nm
        if isinstance(nm, str) and nm not in names:
            names.append(nm)
    return " at ".join(names[:2]) if names else "unnamed street"


def make_sample() -> None:
    """Depot + stops on street segments (labelled by street, no homes/businesses): flagged and dry streets."""
    G, ids, xy, *_ = graph_state()
    fl = load_flood("20240926T22Z")  # evening run, so the sample shows every verdict
    flagged = {}
    for f in sorted(fl.features, key=lambda f: f["properties"]["t_flood"] or 99):
        p = f["properties"]
        if p["name"] and p["t_flood"] is not None:
            line = shapely.geometry.shape(f["geometry"])
            flagged.setdefault(p["name"], line.interpolate(0.5, normalized=True))
    want = [
        "Woodward Way",
        "Windsor Parkway",
        "Hanover West",
        "Peachtree Battle",
        "Bohler Road",
        "Collier Road",
    ]
    stops = []
    for w in want:
        hit = next(((k, pt) for k, pt in flagged.items() if w.lower() in k.lower()), None)
        if hit:
            stops.append({"label": hit[0], "lat": round(hit[1].y, 5), "lon": round(hit[1].x, 5)})
    for lon, lat in [
        (-84.3340, 33.8650),
        (-84.3720, 33.8000),
        (-84.3050, 33.8400),
    ]:  # upland streets
        n = nearest_node(ids, xy, lon, lat)
        stops.append(
            {
                "label": node_label(G, n),
                "lat": round(G.nodes[n]["y"], 5),
                "lon": round(G.nodes[n]["x"], 5),
            }
        )
    stops = [{"id": f"S{i + 1}", **s} for i, s in enumerate(stops)]
    depot_n = nearest_node(ids, xy, -84.3790, 33.8400)  # Peachtree Rd corridor, Buckhead
    stops.append(
        {
            "id": f"S{len(stops) + 1}",
            "label": "Airport cargo area (outside coverage)",
            "lat": 33.6407,
            "lon": -84.4277,
        }
    )
    sample = {
        "business": "Peachtree Corner Pharmacy (sample)",
        "depot": {
            "label": node_label(G, depot_n),
            "lat": round(G.nodes[depot_n]["y"], 5),
            "lon": round(G.nodes[depot_n]["x"], 5),
        },
        "stops": stops,
    }
    (config.WEB_DATA / "dispatch_sample.json").write_text(json.dumps(sample, indent=1))
    log.info("wrote dispatch_sample.json with %d stops", len(stops))


def serve(port: int) -> None:
    import uvicorn
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(title="Noah dispatch (standalone)")
    app.include_router(router)
    app.mount("/", StaticFiles(directory=config.ROOT / "web", html=True), name="web")
    uvicorn.run(app, host="127.0.0.1", port=port)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--make-sample", action="store_true")
    p.add_argument("--serve", action="store_true")
    p.add_argument("--port", type=int, default=8001)
    a = p.parse_args()
    if a.make_sample:
        make_sample()
    if a.serve:
        serve(a.port)


if __name__ == "__main__":
    main()
