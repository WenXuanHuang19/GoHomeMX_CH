# 进度记录 / Progress (resume file)

> 下次对话:让 Claude **先读这个文件**,即可继续作业。

最后更新:2026-06-19(第三天:换触发源)

## 当前状态:🚀 已上线,cron-job.org 触发,全自动运行中

- ✅ 代码完成 + 23/23 测试通过 + 公开仓库 https://github.com/WenXuanHuang19/GoHomeMX_CH
- ✅ 3 人单人价 ~MXN 28,000,与 Google Flights 网页一致 → `price_is_total: true` 不动
- ✅ `data/price_history.csv` 由 GitHub Actions 自动 commit 回仓库(commit `f0e0003`、`5d02736`、`845334b`、`c1012e3` 等)

**触发架构(2026-06-19 改)**:
- **cron-job.org** (免费、可靠) 每天 **11:30 America/Tijuana**(DST 稳定,不受夏冬令影响)
  通过 GitHub REST API `POST /repos/.../actions/workflows/daily.yml/dispatches` 触发 `workflow_dispatch`
- GitHub 自家 `schedule:` 已从 yaml 删除(commit `d517a2b`)
- 详细原因见下方"2026-06-19 架构迁移复盘"

**外部依赖**(都有过期日,过期前要续):
- cron-job.org 账户(免费)
- GitHub PAT `GoHomeMX_cron_trigger`(fine-grained, repo=GoHomeMX_CH, Actions=write+Metadata=read)
  **到期 2027-01-12 08:00 UTC** —— 比用户回程 2027-02-12+ 早,但用户买票期在 12 月之前,无影响
- cron-job.org schedule 自身的过期日:2027-01-01(用户当时未改;到期前要么续期要么停用,反正那时票早买完)

⚠️ **PAT 部分泄露**:2026-06-19 配置过程中,cron-job.org 截图把 Authorization header 前段 (`github_pat_11BB3UH5Y02pMjHFscw...`) 露在了对话里。
完整 token 没露,理论上不可用。**保守做法**:近期 revoke 这个 token,在 https://github.com/settings/personal-access-tokens 找 `GoHomeMX_cron_trigger` → Revoke → 重新生成,回 cron-job.org Header 替换 Bearer 后那串即可。

## ⚠️ 唯一待观察的问题:`price_insights` 缺失

首跑数据里 `price_level` / `typical_low` / `typical_high` **三列全空**——
SerpAPI 没返回 Google 的"偏低/正常/偏高"信号。

**可能原因**:TIJ→中国是冷门航线,Google 自己就没攒"典型价格"数据。

**当前应对**:`recommend.py` 已有回退逻辑——没 Google 信号时,只看"是不是史/月/周新低 + 趋势百分比"。功能仍可用,只是少了"典型价格"对照。

**用户决定**:**先观察 2–3 天**。如果持续都没信号:
- 接受现状(靠自建历史判断,代码已支持);或
- 尝试改 SerpAPI 参数(如加 `hl=zh`, `gl=mx`)、换路线参数试探,看能不能触发 Google 给信号。

复查时间点:**约 2026-06-20**。届时检查最近 3 天 CSV 是否仍全空,再决定。

## 🔄 2026-06-19 架构迁移复盘:换触发源到 cron-job.org

**起因**:连续两天观察 GitHub Actions schedule 表现极差。
- 2026-06-18 17:00 UTC cron:**完全没触发**(到 19:55 UTC 查 `gh run list`,0 条 schedule 事件)
- 2026-06-19 18:37 UTC cron:**延迟 1h40min 才跑**(实际 20:17:59 UTC)

诊断过程中一度误判"GitHub 从不触发",但今天 13:18 用户发现 Telegram 收到了消息,
查 `gh run list` 确认是延迟触发。修正结论:**GitHub 免费层 schedule = 时灵时不灵 + 严重延迟**,
跟"消息每天准时到"的需求不兼容。

**决策**:走方案 C —— 用 cron-job.org(免费)外部触发器调 GitHub API。
- 优点:cron-job.org 准时(±数秒)、时区设 America/Tijuana 不受 DST 影响、不占 SerpAPI 额度(还是一天 8 次)
- 代价:多一个外部账户 + 一个 GitHub PAT 要管理

**实施**(2026-06-19):
1. 在 github.com/settings/personal-access-tokens/new 生成 fine-grained PAT(只对 GoHomeMX_CH,Actions: read+write)
2. 在 cron-job.org 建任务: POST `https://api.github.com/repos/WenXuanHuang19/GoHomeMX_CH/actions/workflows/daily.yml/dispatches`
   - Headers: `Accept: application/vnd.github+json` + `Authorization: Bearer <PAT>` + `X-GitHub-Api-Version: 2022-11-28` + `Content-Type: application/json`
   - Body: `{"ref":"main"}`
   - Schedule: every day 11:30 America/Tijuana
3. Test run 成功(HTTP 204 + 新 workflow_dispatch run #27851122252 + Telegram 收到)
4. 删除 yaml 里的 `schedule:` 块,只留 `workflow_dispatch:` (commit `d517a2b`)

**为什么不双触发**:每次 workflow 跑 8 次 SerpAPI。双触发(GitHub schedule + cron-job.org)= 16/天 = 480/月,爆免费额度 250。
要双触发只能加代码侧"今天已有数据就跳过 SerpAPI"的去重,工作量不值。

---

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
