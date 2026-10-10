import networkx as nx
import numpy as np
from shapely.geometry import Point, box

from noah.api.dispatch import blocked_weight
from noah.api.routing import coverage_state, seg_state, shortest, trip_nodes, worst


def _graph():
    # 0 -> 1 -> 4 fast (seg "1-4-0" floods), 0 -> 2 -> 3 -> 4 slow detour
    G = nx.MultiDiGraph()
    for u, v, tt in [(0, 1, 10), (1, 4, 10), (0, 2, 30), (2, 3, 30), (3, 4, 30)]:
        G.add_edge(u, v, key=0, seg_id=f"{u}-{v}-0", travel_time=tt)
    return G


def test_route_avoids_edges_flagged_by_depart_plus_buffer():
    G = _graph()
    tu = {"1-4-0": 2}  # fast edge uncertain from hour 2; ROUTE_BUFFER_H = 1
    assert shortest(G, 0, 4, blocked_weight(tu, depart_h=0, buffer_h=1)) == [0, 1, 4]  # 2 > 0+1
    assert shortest(G, 0, 4, blocked_weight(tu, depart_h=1, buffer_h=1)) == [0, 2, 3, 4]  # 2 <= 1+1


def test_no_route_when_every_path_is_cut():
    G = _graph()
    tu = {"1-4-0": 2, "3-4-0": 0}
    assert shortest(G, 0, 4, blocked_weight(tu, depart_h=1, buffer_h=1)) is None


def test_coverage_outside_georgia_and_unprocessed_basin():
    georgia, processed = box(0, 0, 10, 10), box(0, 0, 2, 2)
    assert coverage_state(Point(20, 20), georgia, processed) == "out_of_coverage"
    assert coverage_state(Point(5, 5), georgia, processed) == "no_road_forecast"
    assert coverage_state(Point(1, 1), georgia, processed) is None


def test_segment_states_and_worst():
    assert seg_state(3, 5, 2) == "no_forecast_flooding"
    assert seg_state(3, 5, 3) == "uncertain"
    assert seg_state(3, 5, 5) == "flooded"
    assert seg_state(0, None, 0) == "uncertain"
    assert worst(["uncertain", "flooded", "no_forecast_flooding"]) == "flooded"
    assert worst([]) == "no_forecast_flooding"


def test_trip_box_keeps_nodes_near_the_trip_only():
    ids = np.array([1, 2, 3])
    xy = np.array([[-84.40, 33.80], [-84.39, 33.81], [-84.00, 34.50]])  # node 3 is ~80 km away
    kept = trip_nodes(ids, xy, (-84.40, 33.80), (-84.39, 33.81), margin_km=5)
    assert set(kept) == {1, 2}


def test_latest_live_cycle_ignores_historic_runs():
    from noah.api.routing import latest_live

    cycles = [
        {"cycle": "20240926T12Z", "event": "helene", "issue_time": "2024-09-26T12:00:00Z"},
        {"cycle": "20261010T02Z", "event": "live", "issue_time": "2026-10-10T02:00:00Z"},
        {"cycle": "20261010T03Z", "event": "live", "issue_time": "2026-10-10T03:00:00Z"},
    ]
    assert latest_live(cycles) == "20261010T03Z"
    assert latest_live(cycles[:1]) is None


def test_live_hazard_blocks_road_from_now():
    """extra_blocked (TomTom flooding / camera water) blocks a segment even with no forecast flag."""
    G = _graph()
    tu = dict.fromkeys({"1-4-0"}, -1)
    assert shortest(G, 0, 4, blocked_weight(tu, depart_h=0, buffer_h=1)) == [0, 2, 3, 4]


def test_past_cycles_offsets(monkeypatch):
    from noah.api import past, routing

    meta = {
        "cycles": [
            {"cycle": "20261010T00Z", "event": "live", "issue_time": "2026-10-10T00:00:00Z"},
            {"cycle": "20261010T03Z", "event": "live", "issue_time": "2026-10-10T03:00:00Z"},
            {
                "cycle": "20261009T05Z",
                "event": "live",
                "issue_time": "2026-10-09T05:00:00Z",
            },  # 22 h back: outside
            {"cycle": "20240926T12Z", "event": "helene", "issue_time": "2024-09-26T12:00:00Z"},
        ]
    }
    monkeypatch.setattr(routing, "cycles_meta", lambda: meta)
    got = past.past_cycles("20261010T03Z", hours=18)
    assert [(c["h"], c["cycle"]) for c in got] == [(-3, "20261010T00Z"), (0, "20261010T03Z")]
