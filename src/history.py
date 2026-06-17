import csv
import os
from datetime import date, timedelta
from typing import List, Optional

from src.models import FlightResult, HistoryStats

FIELDS = [
    "checked_at", "depart_date", "return_date", "destination", "currency",
    "lowest_overall_pp", "price_level", "typical_low", "typical_high",
    "hainan_lowest_pp", "best_itinerary",
]


def _f(x: str) -> Optional[float]:
    return float(x) if x not in (None, "") else None


class HistoryStore:
    def __init__(self, path: str):
        self.path = path

    def _read_rows(self) -> List[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def append(self, result: FlightResult, checked_at: date) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        exists = os.path.exists(self.path)
        with open(self.path, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if not exists:
                w.writeheader()
            w.writerow({
                "checked_at": checked_at.isoformat(),
                "depart_date": result.depart_date,
                "return_date": result.return_date,
                "destination": result.destination,
                "currency": result.currency,
                "lowest_overall_pp": result.lowest_overall_pp,
                "price_level": result.price_level or "",
                "typical_low": result.typical_low if result.typical_low is not None else "",
                "typical_high": result.typical_high if result.typical_high is not None else "",
                "hainan_lowest_pp": result.hainan_lowest_pp if result.hainan_lowest_pp is not None else "",
                "best_itinerary": result.best_itinerary,
            })

    def stats_for(self, destination: str, depart_date: str, return_date: str,
                  today: date) -> HistoryStats:
        rows = []
        for r in self._read_rows():
            if (r["destination"] == destination
                    and r["depart_date"] == depart_date
                    and r["return_date"] == return_date):
                d = date.fromisoformat(r["checked_at"])
                price = _f(r["lowest_overall_pp"])
                if d < today and price is not None:
                    rows.append((d, price))

        if not rows:
            return HistoryStats(None, None, None, None, None, None, 0)

        rows.sort(key=lambda t: t[0])
        prices = [p for _, p in rows]

        ty, tw, _ = today.isocalendar()
        prev_week_anchor = today - timedelta(days=7)
        py, pw, _ = prev_week_anchor.isocalendar()

        def in_iso_week(d, y, w):
            iy, iw, _ = d.isocalendar()
            return iy == y and iw == w

        prev_month_y = today.year if today.month > 1 else today.year - 1
        prev_month_m = today.month - 1 if today.month > 1 else 12

        week_lows = [p for d, p in rows if in_iso_week(d, ty, tw)]
        month_lows = [p for d, p in rows if d.year == today.year and d.month == today.month]
        prev_week = [p for d, p in rows if in_iso_week(d, py, pw)]
        prev_month = [p for d, p in rows if d.year == prev_month_y and d.month == prev_month_m]

        def avg(xs):
            return round(sum(xs) / len(xs), 2) if xs else None

        return HistoryStats(
            prior_all_time_low=min(prices),
            prior_month_low=min(month_lows) if month_lows else None,
            prior_week_low=min(week_lows) if week_lows else None,
            prev_week_avg=avg(prev_week),
            prev_month_avg=avg(prev_month),
            last_value=rows[-1][1],
            days_tracked=len(rows),
        )
