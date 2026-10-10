import pandas as pd

from noah.api.agent import is_banned
from noah.pipeline.route_watch import (
    camera_message,
    change,
    digest,
    first_warning,
    route_status,
    summary,
)

ISSUE = pd.Timestamp("2026-10-10T12:00Z")
PROPS = {
    "a": {"name": "Elm Street", "t_uncertain": 5, "t_flood": None},
    "b": {"name": "Oak Road", "t_uncertain": 3, "t_flood": 4},
    "c": {"name": "Oak Road", "t_uncertain": 6, "t_flood": 7},
}


def test_route_status_takes_the_earliest_cut():
    s = route_status(["a", "b", "c", "zz"], PROPS, ISSUE)
    assert (
        s["state"] == "flooded"
        and s["street"] == "Oak Road"
        and s["from_utc"] == "2026-10-10T15:00:00Z"
    )
    assert [x["name"] for x in s["streets"]] == ["Oak Road", "Elm Street"]
    assert route_status(["zz"], PROPS, ISSUE)["state"] == "no_forecast_flooding"


def test_change_detection():
    none = {"from_utc": None, "street": None}
    at = lambda t, st="Oak Road": {"from_utc": t, "street": st}
    assert change(None, at("2026-10-10T15:00:00Z")) is None  # first look never alerts
    assert change(none, at("2026-10-10T15:00:00Z")) == "new"
    assert change(at("2026-10-10T15:00:00Z"), none) == "dropped"
    assert change(at("2026-10-10T15:00:00Z"), at("2026-10-10T16:00:00Z")) == "moved"
    assert change(at("2026-10-10T15:00:00Z"), at("2026-10-10T15:00:00Z", "Elm Street")) == "moved"
    assert change(at("2026-10-10T15:00:00Z"), at("2026-10-10T15:00:00Z")) is None
    assert change(none, none) is None
    cut_now = lambda t: {"from_utc": t, "street": "Oak Road", "now": True}
    assert (
        change(cut_now("2026-10-10T15:00:00Z"), cut_now("2026-10-10T16:00:00Z")) is None
    )  # still cut
    assert route_status(["b"], PROPS, ISSUE, had=ISSUE + pd.Timedelta(hours=3))["now"]
    assert not route_status(["b"], PROPS, ISSUE, had=ISSUE + pd.Timedelta(hours=2))["now"]


def test_messages_use_safe_vocabulary_and_lead_time():
    routes = [{"id": "r01", "label": "Brookwood: Peachtree St → Northside Dr", "cams": [{"id": 7}]}]
    cut = route_status(["b"], PROPS, ISSUE)
    prev = {"routes": {"r01": route_status([], PROPS, ISSUE)}}
    run = {
        "cycle": "20261010T12Z",
        "issued_utc": "2026-10-10T12:00:00Z",
        "had_utc": "2026-10-10T13:50:00Z",
        "routes": {"r01": cut},
    }
    d = digest(run, prev, routes)
    assert "(new)" in d and "Oak Rd" in d and not is_banned(d)
    assert digest(run, run, routes) is None
    assert not is_banned(summary(run, routes)) and not is_banned(
        summary(prev | {"issued_utc": run["issued_utc"], "had_utc": run["had_utc"]}, routes)
    )
    first = first_warning([run], "r01", "2026-10-10T16:20:00Z")
    msg = camera_message(
        {"ts": "2026-10-10T16:20:00Z", "bucket": "curb", "title": "Cam"}, routes[0], first
    )
    assert "2.5 h earlier" in msg and "Windy.com" in msg and not is_banned(msg)
    assert first_warning([run], "r01", "2026-10-10T13:00:00Z") is None  # Noah didn't have it yet


def test_texts_use_the_name_people_say():
    from noah.config import road_alias

    assert (
        road_alias("cut from ~7 AM at Horace E Tate Freeway")
        == "cut from ~7 AM at Downtown Connector"
    )


def test_resend_picks_the_latest_real_new_alert():
    from noah.pipeline.route_watch import pick_resend

    items = [
        {"text": "Noah route watch … Graves Rd (new)", "image": None},
        {"text": "Camera on the Smyrna route shows water", "image": "x.png"},
        {"text": "Noah route watch … moved", "image": None},
        {"text": "TEST (not a real alert)", "image": "y.png"},
    ]
    assert pick_resend(items)["text"].endswith("(new)")
    assert pick_resend([]) is None
