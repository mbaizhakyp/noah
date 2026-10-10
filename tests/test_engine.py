from noah.engine import banned, numbers_ok, raise_to_floor, rules


def test_number_guard_accepts_bundle_numbers_and_911_rejects_invented():
    bundle = '{"detail": "2.85 in of rain in 24 h, 98% chance"}'
    assert numbers_ok("About 2.85 inches of rain, 98% chance. Call 911 in an emergency.", bundle)
    assert not numbers_ok("About 2.9 in of rain.", bundle)  # no rounding allowed
    assert not numbers_ok("About 3.0 inches of rain.", bundle)
    assert not numbers_ok("About 6 inches of rain expected.", bundle)


def test_banned_words_whole_word_only():
    assert banned("The route is safe") and banned("Roads are CLEAR") and banned("passable.")
    assert not banned("This is not a safety guarantee") and not banned("conditions are unclear")


def test_rules_only_raise_never_lower():
    r = rules(
        {"state": "flooded", "segments": []},
        [{"source": "NWS alerts", "severity": "danger", "title": "Flash Flood Warning"}],
    )
    assert r["min_now"] == "severe" and r["min_next_18h"] == "severe"
    a = raise_to_floor({"now": {"level": "low"}, "next_18h": {"level": "severe"}}, r)
    assert a["now"]["level"] == "severe"
    calm = rules({"state": "no_forecast_flooding", "segments": []}, [])
    assert raise_to_floor({"now": {"level": "high"}}, calm)["now"]["level"] == "high"


def test_source_errors_are_isolated(monkeypatch):
    import noah.sources as src
    import noah.sources.adapters
    import noah.sources.more  # noqa: F401

    def boom(ctx):
        raise RuntimeError("down")

    monkeypatch.setattr(
        src,
        "ADAPTERS",
        [("ok", 0, lambda c: [src.signal("ok", "context", "fine")]), ("bad", 0, boom)],
    )
    out = src.run(src.Ctx("area", 33.8, -84.4), budget_s=5)
    assert [s["source"] for s in out["signals"]] == ["ok"]
    assert out["sources_failed"][0]["source"] == "bad"


def test_camera_water_needs_two_agreeing_checks(monkeypatch):
    from noah.api import photo

    answers = iter(
        [{"bucket": "curb", "confidence": "high"}, {"bucket": "none", "confidence": "high"}]
    )
    monkeypatch.setattr(
        photo, "classify_url", lambda url, detail="low", skeptic=False: next(answers)
    )
    r = photo.verified("http://x")
    assert (
        r["verified"] is False and r["bucket"] == "curb"
    )  # adapter downgrades this to possible_water

    answers = iter(
        [{"bucket": "half_tire", "confidence": "med"}, {"bucket": "curb", "confidence": "high"}]
    )
    monkeypatch.setattr(
        photo, "classify_url", lambda url, detail="low", skeptic=False: next(answers)
    )
    r = photo.verified("http://x")
    assert r["verified"] is True and r["bucket"] == "curb"  # agree on the lower depth


def test_blank_camera_feed_is_cant_tell_without_ai(monkeypatch):
    from noah.api import photo

    monkeypatch.setattr(photo, "blank_feed", lambda url: True)
    monkeypatch.setattr(
        photo,
        "classify_url",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("AI must not run")),
    )
    r = photo.verified("http://x")
    assert r["bucket"] == "cant_tell" and r["label"] is None and r["blank"]
