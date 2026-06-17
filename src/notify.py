from datetime import date
from typing import List, Optional, Tuple
import requests

from src.models import FlightResult, HistoryStats, Recommendation

TIER_RANK = {"strong_buy": 0, "buy": 1, "wait": 2, "hold": 3, "no_data": 5}
WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

Item = Tuple[FlightResult, Recommendation, HistoryStats]


def _money(x: Optional[float]) -> str:
    return f"{x:,.0f}" if x is not None else "—"


def _md(d: str) -> str:  # "2026-12-29" -> "12/29"
    _, mm, dd = d.split("-")
    return f"{int(mm)}/{int(dd)}"


def _dest_name(code: str) -> str:
    return {"CAN": "广州(CAN)", "SZX": "深圳(SZX)"}.get(code, code)


def _pct_line(rec: Recommendation) -> Optional[str]:
    parts = []
    if rec.pct_vs_last_week is not None:
        parts.append(f"较上周均价 {rec.pct_vs_last_week:+.1f}%")
    if rec.pct_vs_last_month is not None:
        parts.append(f"较上月均价 {rec.pct_vs_last_month:+.1f}%")
    return " · ".join(parts) if parts else None


def build_message(items: List[Item], today: date, decision_phase_start_month: int) -> str:
    good = [it for it in items if it[0].ok and it[0].lowest_overall_pp is not None]
    phase = "决策期" if today.month >= decision_phase_start_month else "观察期"
    header = (f"✈️ 机票日报 · TIJ → 广州/深圳\n"
              f"{today.isoformat()}({WEEKDAYS[today.weekday()]})· 3人往返 · MXN · {phase}")

    if not good:
        return header + "\n\n⚠️ 今日抓取全部失败,请检查 SerpAPI 配置与额度。"

    # Headline = best tier, then cheapest.
    res, rec, stats = min(good, key=lambda it: (TIER_RANK[it[1].tier], it[0].lowest_overall_pp))
    lines = [header, "", "🏆 今日最优",
             f"  {_md(res.depart_date)} → {_md(res.return_date)} · {_dest_name(res.destination)}",
             f"  全网最低 MXN {_money(res.lowest_overall_pp)} /人   {rec.tier_label}"]
    if rec.milestone_label:
        lines.append(f"  {rec.milestone_label}!")
    pct = _pct_line(rec)
    if pct:
        lines.append(f"  {pct}")
    if res.typical_low is not None and res.typical_high is not None:
        lines.append(f"  典型区间 {_money(res.typical_low)}–{_money(res.typical_high)} · {res.best_itinerary}")
    if res.hainan_lowest_pp is not None:
        lines.append(f"  ✈️ 含海航最低:MXN {_money(res.hainan_lowest_pp)} /人")
    else:
        lines.append("  ✈️ 含海航:暂无可用")
    total = res.lowest_overall_pp * 3
    lines.append(f"  👉 {rec.tier_label.split(' ')[-1]} · 3人合计约 MXN {_money(total)}(不含行李/税)")

    # Other combos
    lines += ["", "📊 其他组合(单人价 · 全网最低)"]
    for r2, rc2, _ in sorted(good, key=lambda it: (it[0].depart_date, it[0].return_date, it[0].destination)):
        if (r2.destination, r2.depart_date, r2.return_date) == (res.destination, res.depart_date, res.return_date):
            continue
        badge = {"strong_buy": "🟢", "buy": "🟢", "wait": "🟡", "hold": "🔴"}.get(rc2.tier, "")
        lines.append(f"  {_md(r2.depart_date)}→{_md(r2.return_date)} {r2.destination} {_money(r2.lowest_overall_pp)} {badge}")

    if any((not it[0].ok) or it[0].lowest_overall_pp is None for it in items):
        lines += ["", "⚠️ 部分组合抓取失败,已跳过。"]

    lines += ["", f"🗓 追踪第 {stats.days_tracked} 天"]
    return "\n".join(lines)


def send_telegram(text: str, token: str, chat_id: str, timeout: int = 30) -> dict:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id, "text": text, "disable_web_page_preview": True,
    }, timeout=timeout)
    resp.raise_for_status()
    return resp.json()
