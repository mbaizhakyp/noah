"""Spec 019: time-aware trips.

A road is usable only if its forecast uncertain hour is later than the hour the driver actually
reaches it (plus ROUTE_BUFFER_H). Blocking only grows with time and nobody waits at a corner, so
plain label-setting Dijkstra stays exact (earliest arrival at a node is always best).

`trip()` drives origin -> stops -> destination for the order the user typed, skipping stops that
cannot be reached before their roads are cut, then searches every order (<= 9 stops) for the one
that reaches the most stops, and finds the latest departure that still makes them all.
"""

import heapq
import itertools
import logging
import math
import time
from collections import OrderedDict

import numpy as np
import pandas as pd
import shapely
from shapely.geometry import Point
from shapely.ops import transform

from noah import config
from noah.api import routing
from noah.api.dispatch import flood_state

log = logging.getLogger("trip")
BUFFER_H = config.ROUTE_BUFFER_H
CUTOFF_S = 3 * 3600  # no leg longer than this
STEP_MIN = 5  # leave-by resolution (the page's slider step)
MAX_STOPS = 9
ACCESS_M = 250  # a stop counts as reached from any open road within this distance of it
INF = float("inf")
STATS = {"runs": 0, "secs": 0.0}  # td_dijkstra calls, for the log


class Net:
    """Compact adjacency of a trip box: adj[u] = [(v, travel_s, t_block, key)].
    t_block = lead hour the segment is forecast uncertain (None = never flagged)."""

    def __init__(self, G, nodes, t_uncertain: dict):
        self.G = G
        self.adj: dict = {}
        for u, v, k, d in G.subgraph(nodes).edges(keys=True, data=True):
            tb = t_uncertain.get(d.get("seg_id"))
            self.adj.setdefault(u, []).append((v, float(d.get("travel_time", 1e9)), tb, k))


_nets: OrderedDict = OrderedDict()


def net_for(cycle: str, G, ids, xy, pts: list[tuple], margin_km: float) -> Net:
    """One Net per (cycle, rounded box, margin), newest 8 kept."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    key = (
        cycle,
        id(G),
        round(min(xs), 2),
        round(min(ys), 2),
        round(max(xs), 2),
        round(max(ys), 2),
        margin_km,
    )
    net = _nets.get(key)
    if net is None:
        t0 = time.time()
        net = Net(G, routing.box_nodes(ids, xy, pts, margin_km), flood_state(cycle).t_uncertain)
        _nets[key] = net
        while len(_nets) > 8:
            _nets.popitem(last=False)
        log.info("net %d nodes built in %.2f s", len(net.adj), time.time() - t0)
    return net


def td_dijkstra(
    net: Net,
    src,
    depart_h: float,
    targets=None,
    cutoff_s: float = CUTOFF_S,
    buffer_h: float = BUFFER_H,
    ignore_block: bool = False,
):
    """Earliest arrival (seconds after leaving) from src, leaving at lead hour depart_h.
    Returns (dist, pred) with pred[v] = (u, edge key). Stops early once every target is settled."""
    STATS["runs"] += 1
    t0 = time.time()
    dist, pred = {src: 0.0}, {src: None}
    heap = [(0.0, src)]
    want = set(targets or ())
    want.discard(src)
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist.get(u, INF):
            continue
        if u in want:
            want.discard(u)
            if not want and targets is not None:
                break
        if d > cutoff_s:
            break
        reach_h = depart_h + d / 3600 + buffer_h
        for v, tt, tb, k in net.adj.get(u, ()):
            if not ignore_block and tb is not None and tb <= reach_h:
                continue
            nd = d + tt
            if nd < dist.get(v, INF):
                dist[v] = nd
                pred[v] = (u, k)
                heapq.heappush(heap, (nd, v))
    STATS["secs"] += time.time() - t0
    return dist, pred


def path_from(pred: dict, dst) -> tuple[list, list]:
    """(nodes, edge keys) from the source to dst, following pred."""
    nodes, keys = [dst], []
    while pred.get(nodes[-1]) is not None:
        u, k = pred[nodes[-1]]
        keys.append(k)
        nodes.append(u)
    return nodes[::-1], keys[::-1]


def edges_of(G, nodes: list, keys: list) -> list[dict]:
    return [G[u][v][k] for (u, v), k in zip(itertools.pairwise(nodes), keys)]


def blocked_on_path(
    edges: list[dict], t_uncertain: dict, depart_h: float, buffer_h: float = BUFFER_H
) -> list[str]:
    """seg_ids on a path that are forecast cut by the time the path reaches them."""
    out, t = [], 0.0
    for d in edges:
        tb = t_uncertain.get(d.get("seg_id"))
        if tb is not None and tb <= depart_h + t / 3600 + buffer_h:
            out.append(d["seg_id"])
        t += float(d.get("travel_time", 0))
    return sorted(set(out))


def near_nodes(ids, xy, lon: float, lat: float, radius_m: float, cap: int = 12) -> list:
    """Graph nodes within radius_m of a point, nearest first (the nearest is always included).
    A stop is reached when the driver can get to any of these by open roads: the corner, the
    far end of the block, the next street over. Its own street being flagged does not by itself
    make it unreachable (spec 019, Sat 11:20)."""
    kx = 111320 * math.cos(math.radians(lat))
    dx, dy = (xy[:, 0] - lon) * kx, (xy[:, 1] - lat) * 110540
    d2 = dx * dx + dy * dy
    order = np.argsort(d2)[: cap + 1]
    out = [ids[i] for i in order if d2[i] <= radius_m * radius_m][:cap]
    return out or [ids[order[0]]]


def best_order(n: int, cost, user_order: list[int]) -> tuple[list[int], bool]:
    """Exact search over stop subsets (stops 1..n, destination n+1 fixed last, origin 0).
    cost(i, j, t_s) -> seconds i->j leaving t_s seconds after departure, or INF.
    Objective: most stops reached, then destination reached, then least driving time, then fewest
    swaps from the user's order. Returns (order of reached stops, destination_reached)."""
    dest = n + 1
    best: dict[tuple[int, int], tuple[float, tuple]] = {(0, 0): (0.0, (0,))}
    for mask in range(1 << n):
        for last in range(n + 1):
            st = best.get((mask, last))
            if st is None:
                continue
            t, seq = st
            for j in range(1, n + 1):
                bit = 1 << (j - 1)
                if mask & bit:
                    continue
                c = cost(last, j, t)
                if c == INF:
                    continue
                nt = t + c
                cur = best.get((mask | bit, j))
                if cur is None or nt < cur[0]:
                    best[(mask | bit, j)] = (nt, (*seq, j))
    pos = {s: i for i, s in enumerate(user_order)}

    def swaps(seq):
        s = [x for x in seq if x in pos]
        return sum(1 for a, b in itertools.combinations(s, 2) if pos[a] > pos[b])

    ranked = []
    for (mask, last), (t, seq) in best.items():
        to_dest = cost(last, dest, t)
        reached_dest = to_dest != INF
        total = t + (to_dest if reached_dest else 0)
        ranked.append(
            (
                -(
                    mask.bit_count() + (1 if reached_dest else 0)
                ),  # the destination is a location too
                not reached_dest,
                total,
                swaps(seq),
                seq,
                reached_dest,
            )
        )
    ranked.sort(key=lambda r: r[:4])
    _, _, _, _, seq, reached_dest = ranked[0]
    return [s for s in seq if s != 0], reached_dest


def trip(
    origin: tuple,
    stops: list[tuple],
    dest: tuple,
    depart_h: float,
    cycle: str | None = None,
    corridor_m: int | None = None,
) -> dict:
    """origin, stops, dest as (lon, lat). depart_h = lead hours after the cycle's issue time (float).
    Searches the 5 km trip box first; if any stop would be skipped, searches again with the 15 km
    box so a long way around is found before a stop is given up."""
    t_start = time.time()
    cycle = cycle or routing.current_cycle()
    corridor_m = min(5000, max(500, int(corridor_m or config.CORRIDOR_BUFFER_M)))
    stops = stops[:MAX_STOPS]
    pts = [origin, *stops, dest]
    n = len(stops)
    routing.fresh(cycle)
    fi = routing.flood_index(cycle)
    base = {
        "cycle": cycle,
        "issue_time": routing.iso(fi.issue_time),
        "depart_h": round(depart_h, 3),
    }
    reasons = [routing.coverage_state(Point(*p), *routing.coverage()) for p in pts]
    if reasons[0] or reasons[-1]:
        return {"state": reasons[0] or reasons[-1], **base, "stops": [], "legs": [], "route": None}
    if depart_h > config.MAX_LEAD_H:
        return {"state": "beyond_forecast_window", **base, "stops": [], "legs": [], "route": None}
    depart_h = max(0.0, float(depart_h))
    out = _solve(pts, reasons, depart_h, cycle, fi, corridor_m, config.TRIP_BOX_MARGIN_KM)
    covered_stops = [j for j in range(1, n + 1) if not reasons[j]]
    if out["best"]["reached"] < len(covered_stops) or not out["best"]["dest_reached"]:
        wide = _solve(pts, reasons, depart_h, cycle, fi, corridor_m, config.TRIP_BOX_RETRY_KM)
        if (wide["best"]["reached"], wide["best"]["dest_reached"], wide["current"]["reached"]) >= (
            out["best"]["reached"],
            out["best"]["dest_reached"],
            out["current"]["reached"],
        ):
            out = wide
    out["took_s"] = round(time.time() - t_start, 2)
    return {"state": "ok", **base, **out}


def _solve(pts, reasons, depart_h, cycle, fi, corridor_m, margin_km) -> dict:
    n, dest_i = len(pts) - 2, len(pts) - 1
    covered = [i for i, r in enumerate(reasons) if not r]
    cpts = [pts[i] for i in covered]
    G, ids, xy = routing.graph_for_points(cpts)
    tu = flood_state(cycle).t_uncertain
    net = net_for(cycle, G, ids, xy, cpts, margin_km)
    cand = {i: near_nodes(ids, xy, *pts[i], ACCESS_M) for i in covered}  # access points per stop
    src = {i: cand[i][0] for i in covered}  # legs leave from the nearest node
    all_targets = {i: [c for j in covered if j != i for c in cand[j]] for i in covered}
    memo: dict = {}

    def tt(i: int, h: int) -> dict:
        """seconds from point i to every other covered point (best access point), leaving at hour h."""
        key = (i, h)
        if key not in memo:
            dist, _ = td_dijkstra(net, src[i], h, targets=all_targets[i])
            memo[key] = {
                j: min((dist[c] for c in cand[j] if c in dist), default=INF)
                for j in covered
                if j != i
            }
        return memo[key]

    def bucket(tau: float) -> int:
        return int(min(config.MAX_LEAD_H, math.floor(tau + 1e-9)))

    def cost_at(tau0: float):
        def cost(i: int, j: int, t_s: float) -> float:
            if i not in covered or j not in covered:
                return INF
            return tt(i, bucket(tau0 + t_s / 3600)).get(j, INF)

        return cost

    def simulate(order: list[int], tau0: float) -> dict:
        """Drive origin -> order -> dest leaving at lead hour tau0; a stop with no open way in is skipped."""
        cost = cost_at(tau0)
        cur, t, legs, reached, skipped, arrive = 0, 0.0, [], [], [], {}
        for j in [*order, dest_i]:
            c = cost(cur, j, t)
            if c == INF:
                skipped.append(j)
                continue
            t += c
            legs.append((cur, j, t - c))
            arrive[j] = t
            reached.append(j)
            cur = j
        return {
            "legs": legs,
            "reached": reached,
            "skipped": skipped,
            "arrive": arrive,
            "total_s": t,
        }

    def leave_by(order: list[int], want: set[int]) -> float | None:
        """Latest departure (lead minutes, STEP_MIN grid) that still reaches every point in `want`."""
        lo = math.ceil(depart_h * 60 / STEP_MIN)
        if set(simulate(order, lo * STEP_MIN / 60)["reached"]) < want:
            return None
        hi = config.MAX_LEAD_H * 60 // STEP_MIN
        while lo < hi:  # monotone: later never reaches more
            mid = (lo + hi + 1) // 2
            if set(simulate(order, mid * STEP_MIN / 60)["reached"]) >= want:
                lo = mid
            else:
                hi = mid - 1
        return lo * STEP_MIN

    user_order = list(range(1, n + 1))
    cur_sim = simulate(user_order, depart_h)
    order, _dest_ok = best_order(n, cost_at(depart_h), user_order) if n else ([], True)
    best_sim = simulate(order, depart_h)
    want_cur, want_best = set(cur_sim["reached"]), set(best_sim["reached"])

    def cut_hour(j: int) -> int | None:
        """First hour (from 0, so 'cut since 7 AM' is honest) the depot can no longer reach the stop."""
        if j not in covered:
            return None
        for h in range(config.MAX_LEAD_H + 1):
            if tt(0, h).get(j, INF) == INF:
                return h
        return None

    def row(j: int) -> dict:
        cut = cut_hour(j)
        reached = j in want_cur
        return {
            "state": reasons[j]
            or (
                "hold"
                if not reached
                else "go_before"
                if cut is not None
                else "no_forecast_flooding"
            ),
            "cut_h": cut,
            "cut_utc": None
            if cut is None
            else routing.iso(fi.issue_time + pd.Timedelta(hours=int(cut))),
            "arrive_min": round(cur_sim["arrive"][j] / 60, 1) if reached else None,
            "reached": reached,
        }

    stop_rows = [{"i": j - 1, **row(j), "in_best": j in want_best} for j in range(1, n + 1)]
    dest_row = row(dest_i)

    # legs of the current order, each routed at its real departure time from where the last leg ended
    legs_out, at = [], src[0]
    for i, j, t_off in cur_sim["legs"]:
        tau = depart_h + t_off / 3600
        dist, pred = td_dijkstra(net, at, tau, targets=cand[j])
        goal = min((c for c in cand[j] if c in dist), key=dist.get, default=None)
        if goal is None:  # cannot happen when simulate said reachable; keep the answer conservative
            continue
        nodes, keys = path_from(pred, goal)
        edges = edges_of(G, nodes, keys) if len(nodes) > 1 else []
        line = routing.path_line(G, nodes, edges) if len(nodes) > 1 else None
        _, fpred = td_dijkstra(net, at, tau, targets=[goal], ignore_block=True)
        fnodes, fkeys = path_from(fpred, goal) if goal in fpred else ([], [])
        fedges = edges_of(G, fnodes, fkeys) if len(fnodes) > 1 else []
        avoided = blocked_on_path(fedges, tu, tau)
        usual = routing.path_line(G, fnodes, fedges) if avoided and len(fnodes) > 1 else None
        h = bucket(tau)
        corridor = []
        if line is not None:
            near = fi.tree.query(
                transform(routing._to_metric, line), predicate="dwithin", distance=corridor_m
            )
            corridor = sorted(
                (routing.segment_row(fi, fi.props[k], h) for k in near),
                key=lambda r: (-routing.SEVERITY[r["state"]], r["eta_utc"] or ""),
            )
        legs_out.append(
            {
                "from": i,
                "to": j,
                "depart_h": round(tau, 3),
                "minutes": round(dist[goal] / 60, 1),
                "access_m": round(
                    math.hypot(
                        (G.nodes[goal]["x"] - pts[j][0])
                        * 111320
                        * math.cos(math.radians(pts[j][1])),
                        (G.nodes[goal]["y"] - pts[j][1]) * 110540,
                    )
                ),
                "geometry": shapely.geometry.mapping(line) if line is not None else None,
                "usual_geometry": shapely.geometry.mapping(usual) if usual is not None else None,
                "avoided": avoided,
                "corridor": corridor,
            }
        )
        if (
            legs_out[-1]["access_m"] > 60
        ):  # reached from a nearby open road: the map draws the last bit dotted
            legs_out[-1]["access_line"] = [
                [round(G.nodes[goal]["x"], 5), round(G.nodes[goal]["y"], 5)],
                [round(pts[j][0], 5), round(pts[j][1], 5)],
            ]
        at = goal

    def join(parts):
        out = []
        for c in parts:
            out.extend(c[1:] if out and c else c)
        return out

    seen: set = set()
    corridor_all = [
        c
        for leg in legs_out
        for c in leg["corridor"]
        if not (c["seg_id"] in seen or seen.add(c["seg_id"]))
    ]
    geoms = [leg["geometry"]["coordinates"] for leg in legs_out if leg["geometry"]]
    skipped = [j - 1 for j in cur_sim["skipped"] if j != dest_i]
    route = {
        "state": "route_found" if geoms else "no_route",
        "cycle": cycle,
        "corridor_m": corridor_m,
        "geometry": {"type": "LineString", "coordinates": join(geoms)} if geoms else None,
        "usual_geometry": {
            "type": "LineString",
            "coordinates": join(
                [
                    (leg["usual_geometry"] or leg["geometry"])["coordinates"]
                    for leg in legs_out
                    if leg["geometry"]
                ]
            ),
        }
        if geoms and any(leg["usual_geometry"] for leg in legs_out)
        else None,
        "minutes": round(cur_sim["total_s"] / 60, 1) if geoms else None,
        "avoided": sorted({s for leg in legs_out for s in leg["avoided"]}),
        "corridor": corridor_all,
        "live_blocked": [],
        "legs": len(legs_out),
        "skipped": skipped,
        "dest_reached": dest_i in want_cur,
        "map_url": None,
    }
    return {
        "stops": stop_rows,
        "dest": dest_row,
        "order": [j - 1 for j in order],  # best order, as stop indices
        "current": {
            "reached": len([j for j in want_cur if j != dest_i]),
            "of": n,
            "dest_reached": dest_i in want_cur,
            "minutes": round(cur_sim["total_s"] / 60, 1),
        },
        "best": {
            "order": [j - 1 for j in order],
            "reached": len([j for j in want_best if j != dest_i]),
            "dest_reached": dest_i in want_best,
            "minutes": round(best_sim["total_s"] / 60, 1),
            "differs": [j - 1 for j in order] != list(range(n)) or want_best != want_cur,
            "skipped": sorted(
                {j - 1 for j in best_sim["skipped"] if j != dest_i}
                | {j - 1 for j in range(1, n + 1) if j not in want_best}
            ),
        },
        "leave_by_min": {
            "current": leave_by(user_order, want_cur) if want_cur else None,
            "best": leave_by(order, want_best) if want_best else None,
        },
        "route": route,
        "legs": legs_out,
        "box_km": margin_km,
    }
