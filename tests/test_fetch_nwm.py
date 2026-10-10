import numpy as np
import pandas as pd
import xarray as xr

from noah.pipeline.fetch_nwm import file_urls, subset


def _fake_file(valid: str) -> xr.Dataset:
    ids = np.array([10, 2047989, 30, 40], dtype="int64")
    return xr.Dataset(
        {"streamflow": (("time", "feature_id"), np.array([[1.0, 161.5, 3.0, 4.0]]))},
        coords={"feature_id": ids, "time": [np.datetime64(valid)]},
    )


def test_subset_shape_and_types():
    df = subset(_fake_file("2024-09-26T20:00"), [2047989, 30, 999], lead_h=2)
    assert list(df.columns) == ["feature_id", "lead_h", "valid_time", "q_cms"]
    assert df.feature_id.tolist() == [30, 2047989]  # missing reach 999 skipped
    assert df.lead_h.dtype == "int8" and (df.lead_h == 2).all()
    assert df.q_cms.dtype == "float32"
    assert df.valid_time.iloc[0] == pd.Timestamp("2024-09-26T20:00", tz="UTC")
    assert np.isclose(df.loc[df.feature_id == 2047989, "q_cms"].item(), 161.5)


def test_file_urls_hour0_is_analysis_and_leads_1_to_18():
    urls = file_urls("20240926T18Z")
    assert sorted(urls) == list(range(19))
    assert "analysis_assim" in urls[0] and urls[0].endswith(
        "t18z.analysis_assim.channel_rt.tm00.conus.nc"
    )
    assert urls[1].endswith("nwm.t18z.short_range.channel_rt.f001.conus.nc")
    assert urls[18].endswith("f018.conus.nc") and "nwm.20240926/" in urls[18]
