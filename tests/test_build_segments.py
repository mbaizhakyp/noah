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
