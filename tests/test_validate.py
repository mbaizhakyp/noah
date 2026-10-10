import pandas as pd

from noah import config
from noah.pipeline.validate import cycle_table, lead_time, up_crossing


def test_up_crossing_finds_first_rise_not_initial_state():
    t = pd.date_range("2024-09-26T00:00Z", periods=8, freq="15min")
    s = pd.Series([18, 16, 15, 16, 17.2, 19, 16, 18], index=t)  # starts above: not a crossing
    assert up_crossing(s, 17) == t[4]
    assert up_crossing(s, 30) is None


def _cycle(issue: str, flows: list[float]) -> pd.DataFrame:
    t0 = pd.Timestamp(issue, tz="UTC")
    return pd.DataFrame(
        {
            "feature_id": config.GAUGE_FEATURE_ID,
            "lead_h": range(len(flows)),
            "valid_time": [t0 + pd.Timedelta(hours=h) for h in range(len(flows))],
            "q_cms": flows,
        }
    )


def test_first_warning_cycle_and_lead_time():
    nwm = {
        "20240926T16Z": _cycle("2024-09-26T16:00", [5, 10, 50, 90]),  # never crosses
        "20240926T18Z": _cycle("2024-09-26T18:00", [5, 20, 100, 170]),  # crosses at +3h
        "20240926T19Z": _cycle(
            "2024-09-26T19:00", [200, 50, 60, 70]
        ),  # only hour 0 (analysis) high
    }
    table = cycle_table(nwm, threshold_cms=161.4)
    assert table.fcst_minor_cross_utc.notna().tolist() == [False, True, False]
    first, lead = lead_time(table, pd.Timestamp("2024-09-27T01:15Z"))
    assert first == "20240926T18Z"
    assert abs(lead - 7.25) < 1e-9
