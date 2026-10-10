import networkx as nx
import pandas as pd

from noah.api.dispatch import barricade_rows, reach_by_hour, verdict


def _graph():
    # depot 0 -> 1 fast (seg "0-1-0"), 0 -> 2 -> 1 slow detour, 1 -> 3 spur (stop street "1-3-0")
    G = nx.MultiDiGraph()
    for u, v, tt in [(0, 1, 60), (0, 2, 100), (2, 1, 100), (1, 3, 30)]:
        G.add_edge(u, v, key=0, seg_id=f"{u}-{v}-0", travel_time=tt, length=tt * 10)
    return G


def test_verdicts_go_before_hold_open_and_out_of_coverage():
    G = _graph()
    # fast edge uncertain at h=3, detour at h=6; buffer 1 -> fast blocked from depart_h 2, detour from 5
    tu = {"0-1-0": 3, "0-2-0": 6}
    reach = reach_by_hour(G, 0, tu, hours=range(8))
    assert verdict((1, 3, ("1-3-0",)), reach, True, tu) == {
        "state": "go_before",
        "cut_h": 5,
        "minutes": 1.0,
    }
    assert verdict((0, 2, ("0-2-0",)), reach, True, tu)["cut_h"] == 5  # its own street floods
    # stop street itself already flooded at h=0 -> hold
    assert verdict((1, 3, ("1-3-0",)), reach, True, {**tu, "1-3-0": 0})["state"] == "hold"
    # nothing flooded -> open all window
    r2 = reach_by_hour(G, 0, {}, hours=range(8))
    assert verdict((1, 3, ("1-3-0",)), r2, True, {})["state"] == "no_forecast_flooding"
    assert verdict(None, r2, False, {})["state"] == "out_of_coverage"


def test_barricade_rows_group_and_dedupe_directions():
    feats = [
        {
            "properties": {
                "seg_id": "1-2-0",
                "name": "Bohler Road",
                "t_flood": 16,
                "t_uncertain": 15,
            }
        },
        {
            "properties": {
                "seg_id": "2-1-0",
                "name": "Bohler Road",
                "t_flood": 16,
                "t_uncertain": 15,
            }
        },
        {
            "properties": {
                "seg_id": "3-4-0",
                "name": "Collier Road",
                "t_flood": 10,
                "t_uncertain": 9,
            }
        },
        {"properties": {"seg_id": "5-6-0", "name": "Dry Road", "t_flood": None, "t_uncertain": 9}},
    ]
    rows = barricade_rows(
        feats, {"1-2-0": 100.0, "2-1-0": 100.0, "3-4-0": 50.0}, pd.Timestamp("2024-09-26T12:00Z")
    )
    assert [r["street"] for r in rows] == ["Collier Road", "Bohler Road"]  # sorted by first flood
    assert rows[1]["segments"] == 1 and rows[1]["length_m"] == 100  # two directions counted once
    assert rows[0]["first_flood_utc"] == "2024-09-26T22:00:00Z"
