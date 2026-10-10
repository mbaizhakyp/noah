import numpy as np
import pandas as pd

from noah.pipeline.flood_times import flood_times


def _flows() -> pd.DataFrame:
    leads = range(19)
    a = [10.0 * h for h in leads]  # reach 1 rises 10 m3/s per hour
    b = [5.0] * 19  # reach 2 flat
    return pd.DataFrame(
        {
            "feature_id": [1] * 19 + [2] * 19,
            "lead_h": list(leads) * 2,
            "q_cms": a + b,
        }
    )


def _c3() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "seg_id": ["s1", "s1", "s2", "s3", "s4"],
            "feature_id": [1, 1, 2, 1, 2],
            "threshold_hand_m": [2.0, 3.0, 4.0, 9.0, 0.5],
            "threshold_q_cms": [50.0, 120.0, 100.0, 1000.0, 4.0],
            "uncertain_q": [30.0, 90.0, 80.0, 900.0, 3.0],
        }
    )


def test_threshold_band_min_and_absent():
    out = flood_times(_c3(), _flows()).set_index("seg_id")
    assert out.loc["s1", "t_flood"] == 5  # min over rows: 50 m3/s reached at hour 5
    assert out.loc["s1", "t_uncertain"] == 3  # 30 m3/s at hour 3, before t_flood
    assert np.isclose(out.loc["s1", "hand_min_m"], 2.0)
    assert "s2" not in out.index and "s3" not in out.index  # never reached
    assert out.loc["s4", "t_flood"] == 0  # flat 5 >= 4 from hour 0, without a baseline guard


def test_baseline_guard_drops_rows_wet_at_low_flow():
    base_q = pd.Series({1: 0.0, 2: 5.0})  # reach 2 already at 5 m3/s at low flow
    out = flood_times(_c3(), _flows(), base_q)
    assert "s4" not in set(out.seg_id)
    assert "s1" in set(out.seg_id)
