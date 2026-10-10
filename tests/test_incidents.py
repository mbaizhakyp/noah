from shapely.geometry import box

from noah.pipeline.incidents import keep


def test_keep_filters_category_and_area():
    aoi = box(-84.5, 33.7, -84.0, 34.2)
    incidents = [
        {
            "properties": {"id": "a", "iconCategory": 11, "events": [{"description": "Flooding"}]},
            "geometry": {"type": "Point", "coordinates": [-84.4, 33.82]},
        },
        {
            "properties": {"id": "b", "iconCategory": 6},
            "geometry": {"type": "Point", "coordinates": [-84.4, 33.82]},
        },
        {
            "properties": {"id": "c", "iconCategory": 8},
            "geometry": {"type": "Point", "coordinates": [-85.5, 33.82]},
        },
        {
            "properties": {
                "id": "d",
                "iconCategory": 8,
                "events": [{"description": "Closed"}, {"description": "Flood"}],
            },
            "geometry": {"type": "LineString", "coordinates": [[-84.6, 33.9], [-84.3, 33.9]]},
        },
    ]
    out = keep(incidents, aoi)
    assert [(x["id"], x["category"]) for x in out] == [("a", "flooding"), ("d", "road_closed")]
    assert out[1]["description"] == "Closed; Flood"
