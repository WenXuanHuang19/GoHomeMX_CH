from typing import Optional

from src.models import FlightResult, HistoryStats, Recommendation

TIER_LABELS = {
    "strong_buy": "🟢🟢 强烈建议买",
    "buy": "🟢 可以买",
    "wait": "🟡 再观望",
    "hold": "🔴 暂不建议",
    "no_data": "⚪ 无数据",
}

MILESTONE_LABELS = {
    "all_time": "🔥 史上新低",
    "month": "🟠 本月新低",
    "week": "🔵 本周新低",
}


def _pct(value: float, base: Optional[float]) -> Optional[float]:
    if base in (None, 0):
        return None
    return round((value / base - 1) * 100, 1)


def recommend(result: FlightResult, stats: HistoryStats, drop_alert_pct: float = 8.0) -> Recommendation:
    price = result.lowest_overall_pp
    if price is None:
        return Recommendation(
            tier="no_data", tier_label=TIER_LABELS["no_data"],
            milestone=None, milestone_label=None, drop_alert=False,
            pct_vs_last_week=None, pct_vs_last_month=None, pct_vs_last_value=None,
            reason="本组合今日查询失败,无价格数据。",
        )

    is_all_time = stats.prior_all_time_low is not None and price <= stats.prior_all_time_low
    is_month = stats.prior_month_low is not None and price <= stats.prior_month_low
    is_week = stats.prior_week_low is not None and price <= stats.prior_week_low

    milestone = "all_time" if is_all_time else "month" if is_month else "week" if is_week else None
    milestone_label = MILESTONE_LABELS.get(milestone)

    level = result.price_level
    if level == "low":
        at_typical_low = result.typical_low is not None and price <= result.typical_low
        tier = "strong_buy" if (is_all_time or at_typical_low) else "buy"
    elif level == "typical":
        tier = "wait"
    elif level == "high":
        tier = "hold"
    else:  # no Google signal
        tier = "buy" if is_all_time else "wait"

    drop_alert = stats.last_value is not None and price <= stats.last_value * (1 - drop_alert_pct / 100)

    pct_week = _pct(price, stats.prev_week_avg)
    pct_month = _pct(price, stats.prev_month_avg)
    pct_last = _pct(price, stats.last_value)

    bits = []
    if level:
        bits.append({"low": "Google 判定偏低", "typical": "Google 判定正常", "high": "Google 判定偏高"}[level])
    else:
        bits.append("Google 暂无价格档位,仅参考历史")
    if milestone_label:
        bits.append(milestone_label)
    if stats.days_tracked < 10:
        bits.append(f"历史仅 {stats.days_tracked} 天,主要参考 Google 信号")
    if drop_alert:
        bits.append("较上次大跌")
    reason = " · ".join(bits)

    return Recommendation(
        tier=tier, tier_label=TIER_LABELS[tier],
        milestone=milestone, milestone_label=milestone_label, drop_alert=drop_alert,
        pct_vs_last_week=pct_week, pct_vs_last_month=pct_month, pct_vs_last_value=pct_last,
        reason=reason,
    )
