from datetime import date
from src.models import FlightResult
from src.history import HistoryStore


def _result(dest, dep, ret, price):
    return FlightResult(dest, dep, ret, "MXN", price, "typical", 24000, 31000,
                        None, "1次中转(MEX) 32h00m")


def _write(store, checked_at, dest, dep, ret, price):
    # append() stamps the row with checked_at
    store.append(_result(dest, dep, ret, price), checked_at)


def test_stats_all_time_and_last_value(tmp_path):
    store = HistoryStore(str(tmp_path / "h.csv"))
    _write(store, date(2026, 6, 1), "CAN", "2026-12-28", "2027-02-16", 30000)
    _write(store, date(2026, 6, 2), "CAN", "2026-12-28", "2027-02-16", 28000)
    s = store.stats_for("CAN", "2026-12-28", "2027-02-16", date(2026, 6, 3))
    assert s.prior_all_time_low == 28000
    assert s.last_value == 28000
    assert s.days_tracked == 2


def test_stats_excludes_today_and_other_keys(tmp_path):
    store = HistoryStore(str(tmp_path / "h.csv"))
    _write(store, date(2026, 6, 3), "CAN", "2026-12-28", "2027-02-16", 25000)  # today
    _write(store, date(2026, 6, 2), "SZX", "2026-12-28", "2027-02-16", 21000)  # other key
    _write(store, date(2026, 6, 2), "CAN", "2026-12-28", "2027-02-16", 27000)
    s = store.stats_for("CAN", "2026-12-28", "2027-02-16", date(2026, 6, 3))
    assert s.prior_all_time_low == 27000   # today's 25000 excluded
    assert s.days_tracked == 1             # only the 6/2 CAN row


def test_stats_week_and_month_low(tmp_path):
    store = HistoryStore(str(tmp_path / "h.csv"))
    # today = Wed 2026-06-17 (ISO week 25). Same-week prior: Mon 6/15.
    _write(store, date(2026, 6, 15), "CAN", "2026-12-28", "2027-02-16", 26000)  # this week
    _write(store, date(2026, 6, 8),  "CAN", "2026-12-28", "2027-02-16", 24000)  # prev week, this month
    _write(store, date(2026, 5, 20), "CAN", "2026-12-28", "2027-02-16", 23000)  # prev month
    s = store.stats_for("CAN", "2026-12-28", "2027-02-16", date(2026, 6, 17))
    assert s.prior_week_low == 26000
    assert s.prior_month_low == 24000      # min within June (excludes May)
    assert s.prev_week_avg == 24000        # week containing 6/8
    assert s.prev_month_avg == 23000       # May average
