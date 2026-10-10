import numpy as np
import pandas as pd

from noah.pipeline.build_segments import edge_thresholds, truthy_tag


def test_truthy_tag_handles_osmnx_shapes():
    assert truthy_tag("yes") and truthy_tag("viaduct") and truthy_tag(["no", "yes"])
    assert (
        not truthy_tag("no")
        and not truthy_tag(np.nan)
        and not truthy_tag(None)
        and not truthy_tag(["no"])
    )


def test_edge_thresholds_drops_bridges_explodes_and_floors():
    edges = pd.DataFrame(
        {
            "seg_id": ["a", "b", "c"],
            "osmid": [11, [12, 13], 14],
            "bridge": [np.nan, np.nan, "yes"],
        }
    )
    fimpact = pd.DataFrame(
        {
            "osmid": [11, 12, 13, 14],
            "HydroID": [1, 2, 3, 4],
            "feature_id": [100, 200, 300, 400],
            "branch": [0, 0, 7, 0],
            "threshold_hand": [2.0, 0.1, 3.0, 1.0],  # 12 is a crossing artifact (< 0.3 m)
            "threshold_discharge": [50.0, 1.0, 80.0, 20.0],
        }
    )
    out = edge_thresholds(edges, fimpact, min_hand_m=0.3)
    assert sorted(zip(out.seg_id, out.hydro_id)) == [
        ("a", 1),
        ("b", 3),
    ]  # bridge c gone, 12 floored
    assert list(out.columns) == [
        "seg_id",
        "hydro_id",
        "feature_id",
        "branch_id",
        "threshold_hand_m",
        "threshold_q_cms",
    ]


def test_densify_spacing_and_min_hand_floor():
    import shapely
    from shapely.geometry import LineString

    from noah.pipeline.build_segments import densify, min_hand_per_catchment

    idx, pts = densify(
        np.array([LineString([(0, 0), (25, 0)]), LineString([(0, 0), (5, 0)])]), 10.0
    )
    xs = shapely.get_x(pts)
    assert idx.tolist() == [0, 0, 0, 0, 1, 1]  # 25 m -> 4 points (<= 10 m apart), 5 m -> both ends
    assert np.allclose(xs[:4], [0, 25 / 3, 50 / 3, 25]) and np.allclose(xs[4:], [0, 5])

    m = min_hand_per_catchment(
        ["a", "a", "a", "b"], np.array([0.1, 1.2, 2.0, 30.0]), np.array([7, 7, 7, 7]), 0.3, 25.0
    )
    assert m.to_dict("records") == [
        {"seg_id": "a", "hydro_id": 7, "hand": 1.2}
    ]  # 0.1 floored, 30 > max
