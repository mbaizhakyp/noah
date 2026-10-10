import pandas as pd

from noah.pipeline.fetch_hand import clean_rating


def test_clean_rating_branch0_filter_types_and_monotonic():
    ht = pd.DataFrame(
        {
            "HydroID": ["1", "1", "1", "2", "2", "2", "3", "3"],
            "feature_id": ["100", "100", "100", "200", "200", "200", "300", "300"],
            "branch_id": [0, 0, 0, 0, 0, 0, 77, 77],
            "stage": [0.0, 0.3, 0.6, 0.0, 0.3, 0.6, 0.0, 0.3],
            "discharge_cms": [0.0, 5.0, 12.0, 0.0, 9.0, 4.0, 0.0, 1.0],  # HydroID 2 dips
        }
    ).set_index(["HydroID", "feature_id"])
    out = clean_rating(ht)
    assert list(out.columns) == ["hydro_id", "feature_id", "stage_m", "q_cms"]
    assert out.hydro_id.unique().tolist() == [1]  # 2 non-monotonic, 3 not branch 0
    assert str(out.hydro_id.dtype) == "int64" and str(out.stage_m.dtype) == "float32"
    assert clean_rating(ht, hydro_ids=[2, 3]).empty
