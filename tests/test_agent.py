import pandas as pd

from noah.api.agent import MAX_CHARS, depart_hour, finalize, flagged, is_banned, template_reply


def test_banned_words_whole_word_only():
    assert (
        is_banned("This road is Safe to drive")
        and is_banned("route is CLEAR")
        and is_banned("passable.")
    )
    assert not is_banned("This is not a safety guarantee") and not is_banned(
        "conditions are unclear"
    )


def test_depart_hour_from_now_and_issue():
    issue = pd.Timestamp("2026-10-10T12:00Z")
    now = issue + pd.Timedelta(hours=2, minutes=10)  # NWM lands ~2 h after the cycle hour
    assert depart_hour(issue, now, 0) == 2
    assert depart_hour(issue, now, 8) == 10  # "home at 6 PM" asked at 10 AM
    assert depart_hour(issue, issue, -3) == 0


def test_finalize_strips_markdown_and_caps_length():
    assert finalize("**Do not cross** Elm St.") == "Do not cross Elm St."
    long = ("Do not cross Elm St from about 6 PM. " * 30).strip()
    out = finalize(long)
    assert len(out) <= MAX_CHARS and out.endswith(".")


def test_flagged_dedupes_and_ranks():
    rows = [
        {"name": "Elm St", "state": "uncertain", "eta_utc": "2026-10-10T20:00:00Z"},
        {"name": "Oak Rd", "state": "flooded", "eta_utc": "2026-10-10T22:00:00Z"},
        {"name": "Elm St", "state": "flooded", "eta_utc": "2026-10-10T23:00:00Z"},
        {"name": "Dry Ln", "state": "no_forecast_flooding", "eta_utc": None},
    ]
    out = flagged(rows)
    assert [r["name"] for r in out] == ["Oak Rd", "Elm St"] and out[0]["state"] == "flooded"
    assert out[0]["from"] == "Sat 6 PM"


def test_template_reply_never_says_safe():
    for res in [
        None,
        {"state": "out_of_coverage"},
        {"state": "beyond_forecast_window"},
        {
            "state": "flooded",
            "flagged_roads": [{"name": "Oak Rd", "state": "flooded", "from": "Sat 6 PM"}],
        },
        {"state": "no_forecast_flooding", "flagged_roads": []},
    ]:
        assert not is_banned(template_reply(res))
    assert template_reply(
        {
            "state": "flooded",
            "flagged_roads": [{"name": "Oak Rd", "state": "flooded", "from": "Sat 6 PM"}],
        }
    ).startswith("Do not cross Oak Rd")


def test_street_matching_handles_abbreviations_and_directions():
    from noah.api.agent import street_matches

    assert street_matches("Northside Drive", "Northside Drive Northwest")
    assert street_matches("Northside Dr NW", "Northside Drive Northwest")
    assert not street_matches("Northside Dr NE", "Northside Drive Northwest")
    assert not street_matches("Collier Road", "Northside Drive Northwest")
    assert not street_matches(
        "NW", "Northside Drive Northwest"
    )  # a direction alone is not a street


def test_endpoint_flags_and_guarantee():
    from noah.api.agent import endpoint_flags, needs_guarantee, template_reply

    status = {
        "segments": [
            {
                "name": "Woodward Way Northwest",
                "state": "flooded",
                "eta_utc": "2026-10-10T09:00:00Z",
                "distance_m": 40,
            },
            {
                "name": "Far Rd",
                "state": "flooded",
                "eta_utc": "2026-10-10T08:00:00Z",
                "distance_m": 900,
            },
        ]
    }
    ends = endpoint_flags(status)
    assert [e["name"] for e in ends] == ["Woodward Way Northwest"]
    res = {"state": "endpoint_flooded", "flagged_roads": [], "destination_street_flooding": ends}
    assert template_reply(res).startswith("Do not cross Woodward Way Northwest")
    assert needs_guarantee(
        {"state": "route_found", "flagged_roads": []}, "No flooded roads on your route."
    )
    assert not needs_guarantee(
        {"state": "route_found", "flagged_roads": []},
        "No flooding. This is not a safety guarantee.",
    )
    assert not needs_guarantee(res, "Do not cross Woodward Way.")


def test_at_place_separates_the_asked_street_from_nearby_roads():
    from noah.api.agent import at_place

    status = {
        "segments": [
            {
                "name": "Valley Road Northwest",
                "state": "flooded",
                "eta_utc": "2026-10-10T09:00:00Z",
                "distance_m": 2100,
            },
            {
                "name": "Woodward Way Northwest",
                "state": "uncertain",
                "eta_utc": "2026-10-10T10:00:00Z",
                "distance_m": 900,
            },
            {
                "name": "Unnamed",
                "state": "flooded",
                "eta_utc": "2026-10-10T09:00:00Z",
                "distance_m": 120,
            },
        ]
    }
    names = [r["name"] for r in at_place(status, "Woodward Way NW, Atlanta")]
    assert names == ["Unnamed", "Woodward Way Northwest"]  # 120 m away + same street within 2 km
    assert (
        at_place({"segments": status["segments"][:1]}, "Woodward Way NW") == []
    )  # Valley Rd is only nearby


def test_guarantee_for_calm_place_with_flooded_neighbours():
    from noah.api.agent import needs_guarantee

    area = {
        "state": "flooded",
        "flooding_at_this_place": [],
        "nearby_flagged_roads": [{"name": "Valley Rd"}],
    }
    assert needs_guarantee(area, "Woodward Way itself is not forecast to flood.")
    assert not needs_guarantee(
        {**area, "flooding_at_this_place": [{"name": "Woodward Way"}]}, "Do not cross."
    )
