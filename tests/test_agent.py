import pandas as pd

from noah.api.agent import (
    MAX_CHARS,
    bottom_line,
    cam_verdict,
    compass,
    depart_hour,
    finalize,
    flagged,
    is_banned,
    km_between,
    risk_checklist,
    spread,
    template_reply,
)


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


def test_reassurance_phrases_force_rewrite():
    for s in [
        "so do not expect it underwater",
        "It won't flood tonight",
        "You should be fine",
        "no need to worry",
    ]:
        assert is_banned(s), s
    assert not is_banned(
        "Northside Drive itself is not forecast to flood. This is not a safety guarantee."
    )


def test_camera_bundle_spreads_near_to_far():
    assert spread([1, 2, 3], 6) == [1, 2, 3]
    picked = spread(list(range(20)), 6)
    assert picked[0] == 0 and picked[-1] == 19 and len(picked) == 6 and picked == sorted(picked)


def test_camera_verdict_counts_water_only_when_seen_twice():
    assert "twice" in cam_verdict({"bucket": "curb", "verified": True})
    assert "not confirmed" in cam_verdict({"bucket": "curb", "verified": False})
    assert cam_verdict({"bucket": "none"}) == "no water on the road seen"
    assert cam_verdict({"bucket": "cant_tell", "blank": True}) == "camera feed unavailable"
    assert not any(is_banned(cam_verdict({"bucket": b})) for b in ("none", "cant_tell", "curb"))


def test_km_between_gsu_and_midtown():
    assert 2.0 < km_between(33.7531, -84.3853, 33.7816, -84.3830) < 3.5


def test_compass_and_low_risk_wording():
    assert compass(33.75, -84.39, 33.80, -84.39) == "N"
    assert compass(33.75, -84.39, 33.70, -84.30) == "SE"
    assert is_banned("Flood risk is low based on these facts.")
    assert is_banned("This is a low risk area.")
    assert not is_banned("No camera shows water and no warning is in effect.")


def test_risk_checklist_four_items_from_data():
    checks = [{"title": "Cam A", "wet": False, "ai": "no water on the road seen"}] * 6
    bundle = {
        "sources_ok": [
            {"source": n} for n in ("NWS alerts", "NHC tropical storms", "TomTom traffic incidents")
        ],
        "signals": [
            {
                "source": "NHC tropical storms",
                "severity": "warning",
                "title": "PTC Isaias is 235 km away",
            },
            {
                "source": "Synoptic rain gauges",
                "severity": "watch",
                "title": "Rain measured by 7 nearby gauges",
                "detail": "Wettest last hour: 0.01 in (X). Wettest last 24 h / since midnight: 2.61 in (Y).",
            },
            {
                "source": "NWPS river gauges",
                "severity": "info",
                "title": "Peachtree Creek at Atlanta (AANG1)",
                "detail": "Now 4.9 ft (no flooding)",
            },
            {
                "source": "NWPS river gauges",
                "severity": "warning",
                "title": "Proctor Creek Tributary (PCSG1)",
                "detail": "Now -999  (out of service) at .",
            },
            {
                "source": "TomTom traffic incidents",
                "severity": "warning",
                "value": 8,
                "title": "Road closed: Peachtree St",
            },
            {
                "source": "Bluesky posts",
                "severity": "info",
                "title": "7 public posts about flooding nearby in the last 24 h",
            },
        ],
    }
    text = risk_checklist(
        "Georgia State University", 5, 149, checks, bundle, {"until": "Sun 11:00 AM"}
    )
    lines = text.split("\n")
    assert lines[0] == "Risk checklist · Georgia State University · 5 mi" and len(lines) == 5
    assert lines[1].startswith("🟩 Photos: 6 of 149 cameras")
    assert lines[2].startswith(
        "🟨 Official warnings: no NWS warnings in effect; NHC: PTC Isaias"
    )  # distant storm = watch
    assert lines[3].startswith(
        "🟨 Rain and water levels: rain 0.01 in last hour, 2.61 in last 24 h"
    )
    assert "1 creek gauges below flood stage" in lines[3]  # the out-of-service gauge is ignored
    assert lines[4].startswith(
        "🟩 Public flood reports: no flooded roads reported"
    )  # a closure (8) is not a flood (11)
    assert "7 public posts (unverified)" in lines[4]
    assert not is_banned(text)
    wet = [{"title": "Cam B", "wet": True, "ai": "water on the road"}]
    flooded = {"flooded": ["Peachtree Rd (~9 PM)"], "until": "x"}
    red = risk_checklist("X", 5, 3, wet, {"sources_ok": [], "signals": []}, flooded)
    assert (
        "🟥 Photos" in red and "🟥 Rain and water levels" in red and "⬜ Official warnings" in red
    )


def test_bottom_line_follows_the_squares():
    head = "Risk checklist · X · 5 mi\n"
    calm = (
        head
        + "🟩 Photos: a\n🟩 Official warnings: b\n🟩 Rain and water levels: c\n🟩 Public flood reports: d"
    )
    assert bottom_line(calm).startswith(
        "Bottom line: no flooding is seen or forecast here right now."
    )
    watch = calm.replace("🟩 Official", "🟨 Official").replace("🟩 Rain", "🟨 Rain")
    assert "official warnings and rain and water levels need watching" in bottom_line(watch)
    flood = calm.replace("🟩 Photos", "🟥 Photos")
    assert bottom_line(flood).startswith(
        "Bottom line: photos point to flooding here now"
    ) and "911" in bottom_line(flood)
    assert "Couldn't check public flood reports" in bottom_line(
        calm.replace("🟩 Public", "⬜ Public")
    )
    assert not any(is_banned(bottom_line(t)) for t in (calm, watch, flood))


def test_my_location_defaults_to_gsu_until_saved(monkeypatch):
    from noah.api import agent

    monkeypatch.setattr(agent, "geocode", lambda q: {"name": q, "lat": 33.75, "lon": -84.39})
    session = {"places": {}}
    assert (
        agent.resolve(session, "Near me")["name"] == "Georgia State University (default location)"
    )
    agent.run_tool("remember_place", {"name": "here", "place": "Piedmont Park"}, session, {})
    assert agent.resolve(session, "my location")["name"] == "Piedmont Park"
    assert agent.resolve(session, "Midtown")["name"] == "Midtown"
    agent.note_here(session, "I’m at Atlantic Station, any flooding?")
    assert agent.resolve(session, "here")["name"] == "Atlantic Station"
    agent.note_here(session, "I'm in a hurry")  # not a place: unchanged
    assert agent.resolve(session, "here")["name"] == "Atlantic Station"
    out = agent.run_tool(
        "remember_place", {"name": "my location", "place": "my location"}, {"places": {}}, {}
    )
    assert out["saved"] is False and "default location" in out["my_location"]["name"]
