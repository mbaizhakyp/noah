"""J21: Noah Operations API, for the web console used by agencies and businesses (mounted by app.py).

GET /ops/why?seg_id=&cycle=   why a road is flagged: which creek overtops it, how high the road sits above it, the flow at
                              which water reaches it vs the forecast, how often it flagged in past storms, cameras nearby
GET /ops/city?cycle=          what is at stake: facilities cut off by hour, streets to fix first (and why), and how much of
                              the flooding falls in socially vulnerable neighborhoods (CDC SVI)
GET /ops/site?lat=&lon=       how often roads around a candidate site were forecast cut in the recorded storms

Noah models creek and river overflow (NOAA National Water Model + NOAA terrain). Storm drains and sewers are not in public
data for Atlanta, and dam failure is not modeled; the answers say so instead of guessing.
"""

import json
from functools import lru_cache

import networkx as nx
import numpy as np
import pandas as pd
import shapely
from fastapi import APIRouter, HTTPException
from pyproj import Transformer
from shapely.geometry import Point, shape
from shapely.ops import transform

from noah import config
from noah.api import dispatch

router = APIRouter(prefix="/ops")
CFS = 1 / config.CFS_TO_CMS
_m = Transformer.from_crs(4326, 5070, always_xy=True).transform
NOT_MODELED = "Storm drains and sewers are not in public data for Atlanta, so this is creek overflow only; dam failure is not modeled."
SOURCE = {
    "noaa": "NOAA road flood study",
    "noah": "Noah, from NOAA terrain data (residential street)",
}
EVENT = {"helene": "Helene 2024", "live": "Isaias 2026"}
SVI_HIGH = 0.75  # CDC's "high vulnerability" band: the most vulnerable quarter of US census tracts


def iso(t: pd.Timestamp) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------- cached inputs ----------


@lru_cache(maxsize=1)
def thresholds() -> pd.DataFrame:
    """Per segment: the lowest flow at which water reaches it, how high it sits above the creek, and who computed it."""
    t = pd.read_parquet(config.DATA_INTERIM / "seg_thresholds.parquet")
    t = t.sort_values("threshold_q_cms").drop_duplicates("seg_id")
    return t.set_index("seg_id")[["feature_id", "threshold_q_cms", "threshold_hand_m", "source"]]


@lru_cache(maxsize=1)
def waterways():
    feats = json.loads((config.WEB_DATA / "waterways.geojson").read_text())["features"]
    geoms = [transform(_m, shape(f["geometry"])) for f in feats]
    return [f["properties"]["name"] for f in feats], shapely.STRtree(geoms), geoms


def creek_near(geom_4326) -> dict | None:
    names, tree, geoms = waterways()
    g = transform(_m, geom_4326)
    i = tree.nearest(g)
    if i is None or geoms[int(i)].distance(g) > 600:
        return None
    name = names[int(i)]
    return {"name": name, "regulated": "Chattahoochee River" in name}


@lru_cache(maxsize=1)
def runs() -> list[tuple[str, str]]:
    """(cycle, event) for every stored forecast run."""
    c6 = json.loads((config.WEB_DATA / "cycles.json").read_text())
    return [
        (c["cycle"], c.get("event", ""))
        for c in c6["cycles"]
        if (config.WEB_DATA / f"flood_{c['cycle']}.geojson").exists()
    ]


@lru_cache(maxsize=64)
def run_features(cycle: str) -> tuple[list[dict], shapely.STRtree, list]:
    feats = json.loads((config.WEB_DATA / f"flood_{cycle}.geojson").read_text())["features"]
    geoms = [transform(_m, shape(f["geometry"])) for f in feats]
    return feats, shapely.STRtree(geoms), geoms


@lru_cache(maxsize=1)
def history() -> dict:
    """seg_id -> {event: number of runs that flagged it}, plus run totals per event."""
    out, totals = {}, {}
    for cyc, ev in runs():
        totals[ev] = totals.get(ev, 0) + 1
        for f in run_features(cyc)[0]:
            d = out.setdefault(f["properties"]["seg_id"], {})
            d[ev] = d.get(ev, 0) + 1
    return {"by_seg": out, "totals": totals}


@lru_cache(maxsize=16)
def forecast(cycle: str) -> pd.DataFrame:
    return pd.read_parquet(config.DATA_INTERIM / "nwm" / f"{cycle}.parquet")


@lru_cache(maxsize=1)
def cameras():
    cams = json.loads((config.DATA_INTERIM / "cameras_aoi.json").read_text())
    last = {}
    path = config.DATA_INTERIM / "camera_checks.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            r = json.loads(line)
            last[r["cam_id"]] = r
    pts = [transform(_m, Point(c["lon"], c["lat"])) for c in cams]
    return cams, shapely.STRtree(pts), pts, last


@lru_cache(maxsize=1)
def facilities():
    feats = json.loads((config.WEB_DATA / "facilities.geojson").read_text())["features"]
    ids, xy = dispatch.graph_state()[1:3]
    node = [dispatch.nearest_node(ids, xy, *f["geometry"]["coordinates"]) for f in feats]
    pts = [transform(_m, Point(*f["geometry"]["coordinates"])) for f in feats]
    return feats, node, pts


@lru_cache(maxsize=1)
def svi():
    """CDC SVI tracts (web/data/svi_tracts.geojson) and, per road segment, the tract its midpoint sits in."""
    feats = json.loads((config.WEB_DATA / "svi_tracts.geojson").read_text())["features"]
    edges = dispatch.graph_state()[4]
    mids = shapely.line_interpolate_point(edges.geometry.values, 0.5, normalized=True)
    seg_i, tract_i = shapely.STRtree([shape(f["geometry"]) for f in feats]).query(
        mids, predicate="within"
    )
    return [f["properties"] for f in feats], dict(zip(edges.seg_id.values[seg_i], tract_i.tolist()))


@lru_cache(maxsize=1)
def undirected():
    """Road network as an undirected graph; each edge remembers the segment ids that make it up (both directions)."""
    G = dispatch.graph_state()[0]
    H = nx.Graph()
    for u, v, d in G.edges(data=True):
        if H.has_edge(u, v):
            H[u][v]["segs"].add(d.get("seg_id"))
        else:
            H.add_edge(u, v, segs={d.get("seg_id")})
    return H


# ---------- pure helpers ----------


def times_over(peak_cfs: float, reach_cfs: float) -> float | None:
    return round(peak_cfs / reach_cfs, 1) if reach_cfs > 0 else None


def site_badge(share: float) -> str:
    """Share of recorded forecast hours with a road near the site forecast cut."""
    return (
        "Rarely cut off"
        if share < 0.05
        else "Sometimes cut off"
        if share < 0.25
        else "Often cut off"
    )


def fix_score(hist: dict, totals: dict, major: bool, n_facilities: int) -> float:
    """Recurring across storms first, then busy roads, then roads that cut off schools, clinics or responders."""
    rec = sum(hist.get(ev, 0) / max(1, totals.get(ev, 1)) for ev in totals)
    return round(rec * 10 + (3 if major else 0) + 2 * min(n_facilities, 3), 2)


def vulnerable(
    t_by_seg: dict, tract_of: dict, tracts: list[dict], h: int
) -> tuple[float | None, int]:
    """Of the segments cut by hour h: share in high-SVI tracts, and the population of those tracts."""
    cut = [tract_of[s] for s, t in t_by_seg.items() if t <= h and s in tract_of]
    hi = {k for k in cut if tracts[k]["rpl"] >= SVI_HIGH}
    share = round(sum(k in hi for k in cut) / len(cut), 2) if cut else None
    return share, sum(tracts[k]["pop"] for k in hi)


# ---------- endpoints ----------


@router.get("/why")
def why(seg_id: str, cycle: str | None = None) -> dict:
    cycle = cycle or dispatch.active_cycle()
    feats = run_features(cycle)[0]
    f = next((x for x in feats if x["properties"]["seg_id"] == seg_id), None)
    if f is None:
        raise HTTPException(404, "that road is not flagged in this forecast")
    p, geom = f["properties"], shape(f["geometry"])
    issue = pd.Timestamp(config.parse_cycle(cycle))
    th = thresholds().loc[seg_id] if seg_id in thresholds().index else None
    fc = forecast(cycle)
    q = fc[fc.feature_id == p["feature_id"]].sort_values("lead_h")
    series = [
        {"t": iso(issue + pd.Timedelta(hours=int(r.lead_h))), "cfs": round(r.q_cms * CFS)}
        for r in q.itertuples()
    ]
    peak = max(series, key=lambda s: s["cfs"]) if series else None
    reach_cfs = round(float(th.threshold_q_cms) * CFS) if th is not None else None
    hist = history()
    h = hist["by_seg"].get(seg_id, {})
    cams, ctree, _, last = cameras()
    near = [int(i) for i in ctree.query(transform(_m, geom), predicate="dwithin", distance=300)]
    return {
        "seg_id": seg_id,
        "name": p["name"] or "Unnamed road",
        "cycle": cycle,
        "uncertain_from_utc": iso(issue + pd.Timedelta(hours=p["t_uncertain"])),
        "flooded_from_utc": iso(issue + pd.Timedelta(hours=p["t_flood"]))
        if p["t_flood"] is not None
        else None,
        "creek": creek_near(geom),
        "road_above_creek_m": round(
            float(th.threshold_hand_m if th is not None else p["hand_min_m"]), 1
        ),
        "water_reaches_road_cfs": reach_cfs,
        "forecast": series,
        "peak": peak,
        "times_over": times_over(peak["cfs"], reach_cfs) if peak and reach_cfs else None,
        "source": SOURCE.get(th.source if th is not None else "", "Noah"),
        "history": [
            {"event": EVENT.get(ev, ev), "runs": h.get(ev, 0), "of": n}
            for ev, n in hist["totals"].items()
        ],
        "cameras": [
            {"title": cams[i]["title"], "last_check": (last.get(cams[i]["id"]) or {}).get("bucket")}
            for i in near
        ][:3],
        "not_modeled": NOT_MODELED,
    }


@lru_cache(maxsize=8)
def city_cached(cycle: str) -> dict:
    fl = dispatch.flood_state(cycle)
    feats = fl.features
    tu = {f["properties"]["seg_id"]: f["properties"]["t_uncertain"] for f in feats}
    H = undirected()
    fac, fac_node, fac_pts = facilities()
    # cut off = no open road connects the facility to the main network (largest component); door = flagged road within 150 m
    cut_from, edges_by_hour, seen = {}, {}, None
    for hr in range(config.MAX_LEAD_H + 1):
        blocked = frozenset(s for s, t in tu.items() if t <= hr)
        if blocked != seen:
            seen = blocked
            open_g = H.edge_subgraph(
                [(u, v) for u, v, d in H.edges(data=True) if not (d["segs"] & blocked)]
            )
            giant = (
                max(nx.connected_components(open_g), key=len) if open_g.number_of_nodes() else set()
            )
        for i, n in enumerate(fac_node):
            if i not in cut_from and n not in giant:
                cut_from[i] = hr
        edges_by_hour[hr] = len(blocked)
    _, ftree, fgeoms = run_features(cycle)
    door_from, door_street = {}, {}
    for i, pt in enumerate(fac_pts):
        near = [int(k) for k in ftree.query(pt, predicate="dwithin", distance=150)]
        if near:
            k = min(near, key=lambda k: feats[k]["properties"]["t_uncertain"])
            door_from[i], door_street[i] = (
                feats[k]["properties"]["t_uncertain"],
                feats[k]["properties"]["name"],
            )
    hit = sorted(
        set(cut_from) | set(door_from), key=lambda i: min(cut_from.get(i, 99), door_from.get(i, 99))
    )
    at = lambda hh: iso(fl.issue_time + pd.Timedelta(hours=int(hh))) if hh is not None else None
    fac_out = [
        {
            "name": fac[i]["properties"]["name"],
            "kind": fac[i]["properties"]["kind"],
            "lon": fac[i]["geometry"]["coordinates"][0],
            "lat": fac[i]["geometry"]["coordinates"][1],
            "cut_off_h": cut_from.get(i),
            "cut_off_utc": at(cut_from.get(i)),
            "door_h": door_from.get(i),
            "door_utc": at(door_from.get(i)),
            "door_street": door_street.get(i),
        }
        for i in hit
    ]

    # streets to fix first: recurring across storms, busy (NOAA road study = major roads), facilities that depend on them
    hist, th = history(), thresholds()
    streets = {}
    for k, f in enumerate(feats):
        p = f["properties"]
        if not p["name"]:
            continue
        s = streets.setdefault(
            p["name"], {"segs": [], "first_h": 99, "major": False, "geoms": [], "first_seg": None}
        )
        s["segs"].append(p["seg_id"])
        s["geoms"].append(fgeoms[k])
        if (
            p["t_uncertain"] < s["first_h"]
        ):  # the stretch that floods first names the creek and opens "why"
            s["first_h"], s["first_seg"], s["first_geom"] = (
                p["t_uncertain"],
                p["seg_id"],
                shape(f["geometry"]),
            )
        s["major"] |= p["seg_id"] in th.index and th.loc[p["seg_id"], "source"] == "noaa"
    fix = []
    for name, s in streets.items():
        hh = {}
        for sid in s["segs"]:
            for ev, n in hist["by_seg"].get(sid, {}).items():
                hh[ev] = max(hh.get(ev, 0), n)
        line = shapely.union_all(s["geoms"])
        deps = [fac[i]["properties"]["name"] for i in hit if fac_pts[i].distance(line) < 400]
        creek = creek_near(s["first_geom"])
        above = [float(th.loc[sid, "threshold_hand_m"]) for sid in s["segs"] if sid in th.index]
        fix.append(
            {
                "street": name,
                "score": fix_score(hh, hist["totals"], s["major"], len(deps)),
                "events": [
                    {"event": EVENT.get(ev, ev), "runs": n, "of": hist["totals"][ev]}
                    for ev, n in hh.items()
                ],
                "first_utc": at(s["first_h"]),
                "major": s["major"],
                "facilities": deps[:4],
                "creek": creek and creek["name"],
                "road_above_creek_m": round(min(above), 1) if above else None,
                "segments": len(set(s["segs"])),
                "seg_id": s["first_seg"],
            }
        )
    fix.sort(key=lambda r: -r["score"])
    first = min((f["properties"]["t_uncertain"] for f in feats), default=None)
    tracts, tract_of = svi()
    vul = [vulnerable(tu, tract_of, tracts, h) for h in range(config.MAX_LEAD_H + 1)]
    all_hi = sum(tracts[k]["rpl"] >= SVI_HIGH for k in tract_of.values()) / max(1, len(tract_of))
    return {
        "cycle": cycle,
        "issue_utc": iso(fl.issue_time),
        "first_closure_utc": at(first),
        "facilities": fac_out,
        "facilities_checked": len(fac),
        "fix_first": fix[:15],
        "segments_by_hour": [edges_by_hour[h] for h in range(config.MAX_LEAD_H + 1)],
        "vulnerability": {
            "share_by_hour": [v[0] for v in vul],
            "people_by_hour": [v[1] for v in vul],
            "share_all_roads": round(all_hi, 2),
            "source": "CDC/ATSDR Social Vulnerability Index 2022, census tracts in the top quarter nationally",
        },
        "not_modeled": NOT_MODELED,
    }


@router.get("/city")
def city(cycle: str | None = None) -> dict:
    return city_cached(cycle or dispatch.active_cycle())


@router.get("/site")
def site(lat: float, lon: float, radius_m: int = 500) -> dict:
    pt = transform(_m, Point(lon, lat))
    per_event, hours_cut, hours_all, nearest = {}, 0, 0, None
    for cyc, ev in runs():
        feats, tree, geoms = run_features(cyc)
        near = [int(k) for k in tree.query(pt, predicate="dwithin", distance=radius_m)]
        e = per_event.setdefault(
            ev, {"event": EVENT.get(ev, ev), "runs": 0, "cut_runs": 0, "first_hours": []}
        )
        e["runs"] += 1
        hours_all += config.MAX_LEAD_H + 1
        if near:
            first = min(feats[k]["properties"]["t_uncertain"] for k in near)
            e["cut_runs"] += 1
            e["first_hours"].append(first)
            hours_cut += config.MAX_LEAD_H + 1 - first
            k = min(near, key=lambda k: geoms[k].distance(pt))
            d = geoms[k].distance(pt)
            if nearest is None or d < nearest[1]:
                nearest = (feats[k]["properties"]["name"] or "an unnamed road", d)
    share = hours_cut / hours_all if hours_all else 0.0
    events = [
        {
            "event": e["event"],
            "runs": e["runs"],
            "cut_runs": e["cut_runs"],
            "typical_first_hour": int(np.median(e["first_hours"])) if e["first_hours"] else None,
        }
        for e in per_event.values()
    ]
    return {
        "lat": lat,
        "lon": lon,
        "radius_m": radius_m,
        "share_hours_cut": round(share, 3),
        "badge": site_badge(share),
        "events": events,
        "nearest_flagged": nearest and {"street": nearest[0], "m": round(nearest[1])},
        "note": "Based on the storms Noah recorded (forecast runs), not a flood-insurance rating. "
        + NOT_MODELED,
    }
