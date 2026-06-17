from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SearchParams:
    origin: str
    destination: str
    depart_date: str   # YYYY-MM-DD
    return_date: str   # YYYY-MM-DD
    passengers: int
    currency: str


@dataclass
class FlightResult:
    destination: str
    depart_date: str
    return_date: str
    currency: str
    lowest_overall_pp: Optional[float]   # per person
    price_level: Optional[str]           # "low" | "typical" | "high" | None
    typical_low: Optional[float]         # per person
    typical_high: Optional[float]        # per person
    hainan_lowest_pp: Optional[float]    # per person; None if no Hainan option
    best_itinerary: str                  # human summary, "" if unknown
    ok: bool = True
    error: Optional[str] = None


@dataclass
class HistoryStats:
    prior_all_time_low: Optional[float]
    prior_month_low: Optional[float]
    prior_week_low: Optional[float]
    prev_week_avg: Optional[float]
    prev_month_avg: Optional[float]
    last_value: Optional[float]
    days_tracked: int


@dataclass
class Recommendation:
    tier: str           # strong_buy | buy | wait | hold | no_data
    tier_label: str     # e.g. "🟢🟢 强烈建议买"
    milestone: Optional[str]        # all_time | month | week | None
    milestone_label: Optional[str]  # e.g. "🔥 史上新低"
    drop_alert: bool
    pct_vs_last_week: Optional[float]   # negative = cheaper than avg
    pct_vs_last_month: Optional[float]
    pct_vs_last_value: Optional[float]
    reason: str
