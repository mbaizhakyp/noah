from datetime import datetime, timedelta

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

from noah.pipeline.camera_watch import due_alert, segment_state, watch_list


def test_segment_state_over_time():
    issue = pd.Timestamp("2026-10-10T12:00Z")
    p = {"t_flood": 6, "t_uncertain": 4}
    assert segment_state(p, issue, issue + pd.Timedelta(hours=2))[0] == "forecast later"
    assert segment_state(p, issue, issue + pd.Timedelta(hours=5))[0] == "uncertain"
    state, when = segment_state(p, issue, issue + pd.Timedelta(hours=7))
    assert state == "flooded" and when == issue + pd.Timedelta(hours=6)


def test_due_alert_rate_limits_per_camera():
    now = datetime(2026, 10, 10, 16, 0)
    assert due_alert({}, "c1", now)
    assert not due_alert({"c1": now - timedelta(minutes=30)}, "c1", now)
    assert due_alert({"c1": now - timedelta(hours=3)}, "c1", now)


def test_watch_list_keeps_road_and_creek_cameras_only():
    cams = gpd.GeoDataFrame(
        {"id": ["road", "creek", "far"]},
        geometry=[Point(0, 100), Point(5000, 50), Point(9000, 9000)],
        crs=5070,
    )
    c5 = gpd.GeoDataFrame(
        {"seg_id": ["s"], "name": ["Elm St"], "t_flood": [5], "t_uncertain": [4]},
        geometry=[LineString([(0, 0), (100, 0)])],
        crs=5070,
    )
    streams = gpd.GeoDataFrame(geometry=[LineString([(4900, 0), (5100, 0)])], crs=5070)
    w = watch_list(cams, c5, streams)
    assert sorted(w["id"]) == ["creek", "road"]
    assert w.set_index("id").loc["road", "name"] == "Elm St"
