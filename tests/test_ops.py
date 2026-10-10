from noah.api.ops import fix_score, site_badge, times_over


def test_site_badge_bands():
    assert site_badge(0.0) == "Rarely cut off"
    assert site_badge(0.1) == "Sometimes cut off"
    assert site_badge(0.86) == "Often cut off"


def test_fix_score_puts_repeat_offenders_first():
    totals = {"helene": 25, "live": 16}
    every_storm = fix_score({"helene": 25, "live": 16}, totals, major=False, n_facilities=0)
    once = fix_score({"live": 3}, totals, major=True, n_facilities=1)
    assert every_storm > once
    assert fix_score({"live": 3}, totals, True, 1) > fix_score({"live": 3}, totals, False, 0)


def test_times_over():
    assert times_over(279, 261) == 1.1
    assert times_over(100, 0) is None
