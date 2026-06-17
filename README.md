# FlightsTickets — TIJ→CAN/SZX daily price tracker

Daily checks TIJ→广州/深圳 round-trip prices across 4 date pairs via SerpAPI
Google Flights, judges buy/no-buy, and sends a Telegram message. Runs on
GitHub Actions; price history is committed to `data/price_history.csv`.

Design: `docs/superpowers/specs/2026-05-27-flight-price-tracker-design.md`

## Local use

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest                 # run tests
python -m src.main --dry-run     # print a sample message, no network/secrets
```

## Secrets you must provide (GitHub → Settings → Secrets and variables → Actions)

| Secret | How to get it |
|--------|---------------|
| `SERPAPI_KEY` | Sign up at serpapi.com → Dashboard → copy "Your Private API Key". Free plan = 250 searches/month. |
| `TELEGRAM_BOT_TOKEN` | In Telegram, message **@BotFather** → `/newbot` → follow prompts → copy the token (`123456:ABC...`). |
| `TELEGRAM_CHAT_ID` | Message your new bot once, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and read `result[].message.chat.id`. (Or message **@userinfobot**.) |

Add each via **New repository secret**.

## Configuration

Edit `config.yaml`: dates, destinations, currency, thresholds. Set
`enabled: false` (or disable the workflow) once you've bought the tickets.

## Schedule

Runs at 17:00 UTC daily (≈ 09:00 Tijuana in winter; ≈ 10:00 in summer DST).
Adjust the `cron` line in `.github/workflows/daily.yml` if you want a
different time. You can also trigger a run anytime from the Actions tab
(**Run workflow**).
