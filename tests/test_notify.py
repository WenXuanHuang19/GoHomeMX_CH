from datetime import date
from src.models import FlightResult, HistoryStats, Recommendation
from src.notify import build_message

TIER_RANK = {"strong_buy": 0, "buy": 1, "wait": 2, "hold": 3, "no_data": 4}


def _item(dest, dep, ret, price, tier, milestone_label=None, hainan=None,
          pct_wk=None, pct_mo=None, days=80):
    res = FlightResult(dest, dep, ret, "MXN", price, "low", 24800, 31200,
                       hainan, "1次中转(墨城) 32h00m")
    rec = Recommendation(tier, {"strong_buy": "🟢🟢 强烈建议买", "buy": "🟢 可以买",
                                "wait": "🟡 再观望", "hold": "🔴 暂不建议"}[tier],
                         "all_time" if milestone_label else None, milestone_label,
                         False, pct_wk, pct_mo, None, "reason")
    stats = HistoryStats(20000, 20000, 20000, None, None, price, days)
    return (res, rec, stats)


def test_headline_picks_best_tier_then_cheapest():
    items = [
        _item("SZX", "2026-12-28", "2027-02-16", 25000, "wait"),
        _item("CAN", "2026-12-29", "2027-02-16", 22980, "strong_buy",
              milestone_label="🔥 史上新低", hainan=24600, pct_wk=-5.2, pct_mo=-9.8),
        _item("CAN", "2026-12-28", "2027-02-16", 24100, "buy"),
    ]
    msg = build_message(items, today=date(2026, 8, 15), decision_phase_start_month=10)
    assert "🏆 今日最优" in msg
    assert "12/29 → 2/16" in msg          # headline = strong_buy combo
    assert "广州(CAN)" in msg
    assert "22,980" in msg                 # thousands separator
    assert "🔥 史上新低" in msg
    assert "含海航最低:MXN 24,600" in msg
    assert "较上周均价 -5.2%" in msg
    assert "观察期" in msg                  # Aug < Oct


def test_failed_combos_get_warning():
    bad = FlightResult("CAN", "2026-12-28", "2027-02-16", "MXN", None, None,
                       None, None, None, "", ok=False, error="timeout")
    rec = Recommendation("no_data", "⚪ 无数据", None, None, False, None, None, None, "fail")
    stats = HistoryStats(None, None, None, None, None, None, 0)
    good = _item("SZX", "2026-12-28", "2027-02-16", 25000, "wait")
    msg = build_message([(bad, rec, stats), good], today=date(2026, 11, 1),
                        decision_phase_start_month=10)
    assert "部分组合抓取失败" in msg
    assert "决策期" in msg                  # Nov >= Oct


def test_all_failed_message():
    bad = FlightResult("CAN", "2026-12-28", "2027-02-16", "MXN", None, None,
                       None, None, None, "", ok=False, error="timeout")
    rec = Recommendation("no_data", "⚪ 无数据", None, None, False, None, None, None, "fail")
    stats = HistoryStats(None, None, None, None, None, None, 0)
    msg = build_message([(bad, rec, stats)], today=date(2026, 11, 1),
                        decision_phase_start_month=10)
    assert "今日抓取全部失败" in msg
