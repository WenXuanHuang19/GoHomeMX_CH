# 进度记录 / Progress (resume file)

> 下次对话:让 Claude **先读这个文件**,即可继续作业。

最后更新:2026-06-18(第二天复盘)

## 当前状态:🚀 已上线,全自动运行中

- ✅ 代码全部完成,9 个 commit,已 push 到公开仓库
  https://github.com/WenXuanHuang19/GoHomeMX_CH
- ✅ 23/23 测试通过
- ✅ GitHub Actions cron 已生效;手动触发首跑(2026-06-17 21:21 UTC)成功(52 秒)
- ⏰ 2026-06-18 cron 改为 `37 18 * * *`(18:37 UTC ≈ Tijuana 11:37 夏 / 10:37 冬),错开整点降低被 GitHub 吞掉的概率 → 见下方"事故复盘"
- ✅ Telegram 推送收到(用户确认)
- ✅ 3 人单人价 ~MXN 28,000,与 Google Flights 网页一致 → `price_is_total: true` 假设正确,不动
- ✅ `data/price_history.csv` 已被 GitHub Actions 自动 commit 回仓库(commit `f0e0003`)

后续无需写代码,系统会:
- 每天约 17:00 UTC(≈ Tijuana 冬令 9:00 / 夏令 10:00)自动跑
- Telegram 每天推一条
- 历史每天累积到云端 CSV

## ⚠️ 唯一待观察的问题:`price_insights` 缺失

首跑数据里 `price_level` / `typical_low` / `typical_high` **三列全空**——
SerpAPI 没返回 Google 的"偏低/正常/偏高"信号。

**可能原因**:TIJ→中国是冷门航线,Google 自己就没攒"典型价格"数据。

**当前应对**:`recommend.py` 已有回退逻辑——没 Google 信号时,只看"是不是史/月/周新低 + 趋势百分比"。功能仍可用,只是少了"典型价格"对照。

**用户决定**:**先观察 2–3 天**。如果持续都没信号:
- 接受现状(靠自建历史判断,代码已支持);或
- 尝试改 SerpAPI 参数(如加 `hl=zh`, `gl=mx`)、换路线参数试探,看能不能触发 Google 给信号。

复查时间点:**约 2026-06-20**。届时检查最近 3 天 CSV 是否仍全空,再决定。

## 📋 2026-06-18 事故复盘:cron 被吞 + 改时间

**现象**:第二天中午 Telegram 没收到消息。

**根因**:GitHub Actions 把 17:00 UTC 那次定时跑**直接吞了**(`gh run list` 一条 schedule 类型的运行都没有)。
免费层 + 整点(`XX:00`)是高发场景——全球海量 workflow 同时排队,GitHub 文档承认会丢。

**处理**:
1. 手动 `workflow_dispatch` 触发一次(2026-06-18 19:15 UTC)→ 成功,Telegram 收到,CSV 已补
2. cron 改成 `37 18 * * *`(commit `e58a802`)→ 错开整点。
   - 新触发时间:**每天 18:37 UTC**
   - Tijuana 夏令(PDT,现在)≈ **11:37**
   - Tijuana 冬令(PST,买票期)≈ **10:37** —— 到 11 月入冬时,如果想保持 11:37,改成 `37 19 * * *`

**为什么没加备份触发**:每次跑消耗 8 次 SerpAPI,免费额度 250/月。双触发会变 480/月,直接爆。
真要加备份必须搭配"今天已跑过就跳过 SerpAPI、只补 Telegram"的代码去重逻辑(方案 C),目前不值得做。

## 🔍 2026-06-18 同时发现:milestone 边界 bug(暂不修)

读 `recommend.py:36-40` + `history.py:50-95` 时发现三个"本周/本月/史新低"的边界情况:

| 情况 | 行为 | 严重度 |
|---|---|---|
| 每周一早上 | "本周新低" badge **永远不会触发**(ISO 周刚重置,本周历史为空,`prior_week_low=None`) | 低——通常被更高优先级 milestone 接住 |
| 每月 1 号早上 | "本月新低" badge 同上 | 低 |
| 早期(< 10 天) | "史新低"频繁出现,意义不大 | 已有缓解:`reason` 里追加"历史仅 X 天" |

**用户决定**:**先观察 2 周再说**(到约 2026-07-02)。如果觉得周一/月初漏报"本周新低"碍事,可以把口径改成"滚动 7 天 / 滚动 30 天",代价是"本周"不再指日历周。

**与 `price_insights` 缺失无关**:三个 milestone 完全独立于 Google 信号,即使 `price_insights` 一直为空也能正常工作。

## 本地 CSV 不会自动更新

GitHub 远端 CSV 每天自动 commit;本地这份要 `git pull` 才同步。日常**不需要本地更新**——
Telegram 已经把关键信息推给用户了。要看历史:浏览器开
https://github.com/WenXuanHuang19/GoHomeMX_CH/blob/main/data/price_history.csv

## 想改/想停

- 改日期/阈值:编辑 `config.yaml`,push。
- 改触发时间:编辑 `.github/workflows/daily.yml` 的 cron。
- 临时停:Actions 页面 → "Daily flight price check" → ··· → Disable workflow。
- 永久停(买到票后):`config.yaml` 设 `enabled: false`,push。

## 关键文件 / 链接

- 仓库:https://github.com/WenXuanHuang19/GoHomeMX_CH
- 设计规格:`docs/superpowers/specs/2026-05-27-flight-price-tracker-design.md`
- 实现计划:`docs/superpowers/plans/2026-05-27-flight-price-tracker.md`
- 长期记忆:`~/.claude/projects/-Users-owenhuang-Documents-FlightsTickets/memory/flight-price-tracker.md`
- 本地虚拟环境:`.venv/`(Python 3.14, pytest 8.3.3, requests, PyYAML)

## 本地常用命令

```bash
cd /Users/owenhuang/Documents/FlightsTickets
.venv/bin/python -m pytest                 # 跑测试
.venv/bin/python -m src.main --dry-run     # 本地干跑一次看消息
git pull                                   # 拉远端最新 CSV 数据
```
