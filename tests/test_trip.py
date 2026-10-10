"""Spec 019: time-aware blocking and the stop order on a hand-built graph. Offline, no files."""

import networkx as nx

from noah.api import trip


def line_graph():
    """A -> B -> C -> D, 30 min per link; the B->C road (seg s1) is forecast uncertain at hour 2."""
    G = nx.MultiDiGraph()
    for u, v, seg in (("A", "B", "s0"), ("B", "C", "s1"), ("C", "D", "s2")):
        G.add_edge(u, v, key=0, seg_id=seg, travel_time=1800.0)
    for n in G.nodes:
        G.nodes[n]["x"] = G.nodes[n]["y"] = 0.0
    return G


def test_road_is_blocked_by_the_hour_you_reach_it_not_the_hour_you_leave():
    G = line_graph()
    net = trip.Net(G, list(G.nodes), {"s1": 2})
    # leave at hour 0: reach B at 0.5 h, 0.5 + 1 h buffer < 2 -> allowed, D at 1.5 h
    dist, pred = trip.td_dijkstra(net, "A", 0.0, targets=["D"])
    assert dist["D"] == 5400.0
    assert trip.path_from(pred, "D")[0] == ["A", "B", "C", "D"]
    # leave at hour 0.6: reach B at 1.1 h, 1.1 + 1 >= 2 -> blocked, no way to D
    dist, _ = trip.td_dijkstra(net, "A", 0.6, targets=["D"])
    assert "D" not in dist
    # the old rule (departure + buffer) would have allowed both; the fastest way still lists the road as avoided
    edges = trip.edges_of(G, ["A", "B", "C", "D"], [0, 0, 0])
    assert trip.blocked_on_path(edges, {"s1": 2}, 0.6) == ["s1"]
    assert trip.blocked_on_path(edges, {"s1": 2}, 0.0) == []


def test_best_order_visits_the_early_cut_stop_first_and_holds_the_unreachable_one():
    # origin 0, stops 1 (cut at 1 h), 2 (never cut), 3 (never reachable), dest 4; 20 min between any pair
    def cost(i, j, t_s):
        if j == 3 or i == 3:
            return trip.INF
        if (
            j == 1 and t_s / 3600 + 1 >= 1
        ):  # stop 1's road is cut at hour 1 (with the 1 h buffer: must arrive at t=0)
            return trip.INF if t_s > 0 else 1200.0
        return 1200.0

    order, dest_ok = trip.best_order(3, cost, [1, 2, 3])
    assert order == [1, 2] and dest_ok  # 1 first (only reachable right away), 3 held


def test_own_street_blocked_at_arrival_counts_as_unreachable():
    G = line_graph()
    net = trip.Net(G, list(G.nodes), {"s2": 1})  # the destination's own road floods at hour 1
    dist, _ = trip.td_dijkstra(net, "A", 0.0, targets=["C"])
    assert trip.own_open(net, "C", 0.0, dist["C"]) is False  # arrive 1 h, +1 buffer >= 1
    assert trip.own_open(net, "B", 0.0, dist["B"]) is True
