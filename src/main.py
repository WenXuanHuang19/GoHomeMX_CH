import argparse
import os
import sys
from datetime import date
from typing import Optional

from src.config import load_config
from src.models import SearchParams
from src.flights import search, normalize_response
from src.history import HistoryStore
from src.recommend import recommend
from src.notify import build_message, send_telegram


def run(config_path: str = "config.yaml", dry_run: bool = False,
        today: Optional[date] = None, fixture: Optional[dict] = None) -> Optional[str]:
    cfg = load_config(config_path)
    if not cfg.enabled:
        print("tracker disabled in config; nothing to do.")
        return None

    today = today or date.today()
    store = HistoryStore(cfg.history_path)
    combos = [(dest, dep, ret) for (dep, ret) in cfg.date_pairs for dest in cfg.destinations]

    items = []
    for dest, dep, ret in combos:
        params = SearchParams(cfg.origin, dest, dep, ret, cfg.passengers, cfg.currency)
        if dry_run and fixture is not None:
            result = normalize_response(fixture, params, cfg.price_is_total)
        else:
            result = search(params, api_key=os.environ["SERPAPI_KEY"],
                            price_is_total=cfg.price_is_total)
        stats = store.stats_for(dest, dep, ret, today)
        rec = recommend(result, stats, cfg.drop_alert_pct)
        items.append((result, rec, stats))
        if result.ok and result.lowest_overall_pp is not None and not dry_run:
            store.append(result, today)

    msg = build_message(items, today=today,
                        decision_phase_start_month=cfg.decision_phase_start_month)

    if dry_run:
        print(msg)
    else:
        send_telegram(msg, token=os.environ["TELEGRAM_BOT_TOKEN"],
                      chat_id=os.environ["TELEGRAM_CHAT_ID"])
    return msg


def main(argv=None):
    parser = argparse.ArgumentParser(description="Daily flight price tracker")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--dry-run", action="store_true",
                        help="use bundled fixture, print message, do not send or write history")
    args = parser.parse_args(argv)

    fixture = None
    if args.dry_run:
        import json
        from pathlib import Path
        fixture = json.loads((Path(__file__).parent.parent
                              / "tests" / "fixtures" / "serpapi_sample.json").read_text())
    run(config_path=args.config, dry_run=args.dry_run, fixture=fixture)


if __name__ == "__main__":
    sys.exit(main())
