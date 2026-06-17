from src.models import FlightResult, HistoryStats, Recommendation
from src.recommend import recommend


def _result(price, level, typ_low=24800, typ_high=31200):
    return FlightResult("CAN", "2026-12-28", "2027-02-16", "MXN", price, level,
                        typ_low, typ_high, None, "1次中转(MEX) 32h00m")


def _stats(all_low=None, month_low=None, week_low=None, last=None,
           wk_avg=None, mo_avg=None, days=5):
    return HistoryStats(all_low, month_low, week_low, wk_avg, mo_avg, last, days)


def test_strong_buy_on_all_time_low_and_low_level():
    r = recommend(_result(22000, "low"), _stats(all_low=23000, last=23000, days=5))
    assert r.tier == "strong_buy"
    assert r.milestone == "all_time"
    assert "史上新低" in r.milestone_label


def test_buy_when_low_but_not_record():
    r = recommend(_result(26000, "low"), _stats(all_low=22000, week_low=27000, last=27000))
    assert r.tier == "buy"
    assert r.milestone == "week"   # beats week_low 27000


def test_wait_on_typical():
    r = recommend(_result(28000, "typical"), _stats(all_low=22000, last=28500))
    assert r.tier == "wait"


def test_hold_on_high():
    r = recommend(_result(33000, "high"), _stats(all_low=22000, last=32000))
    assert r.tier == "hold"


def test_drop_alert_triggers_on_8pct_fall():
    r = recommend(_result(27600, "typical"), _stats(all_low=22000, last=30000))
    assert r.drop_alert is True   # 27600 <= 30000 * 0.92


def test_no_data_when_price_missing():
    r = recommend(_result(None, None), _stats())
    assert r.tier == "no_data"


def test_first_ever_record_has_no_milestone():
    r = recommend(_result(25000, "low"), _stats(all_low=None, last=None, days=0))
    assert r.milestone is None


def test_pct_vs_last_week_negative_when_cheaper():
    r = recommend(_result(22500, "low"), _stats(all_low=23000, last=23000, wk_avg=25000))
    assert r.pct_vs_last_week == -10.0   # (22500/25000 - 1) * 100
