import json
from datetime import date
from pathlib import Path


def test_models_importable():
    from src.models import SearchParams, FlightResult, HistoryStats, Recommendation
    p = SearchParams("TIJ", "CAN", "2026-12-28", "2027-02-16", 3, "MXN")
    assert p.destination == "CAN"


FIXTURE = Path(__file__).parent / "fixtures" / "serpapi_sample.json"


def test_dry_run_uses_fixture_and_returns_message(tmp_path, capsys):
    from src.main import run
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "enabled: true\norigin: TIJ\ndestinations: [CAN, SZX]\npassengers: 3\n"
        "currency: MXN\nprice_is_total: true\n"
        "date_pairs:\n  - {depart: \"2026-12-28\", return: \"2027-02-16\"}\n"
        "drop_alert_pct: 8\ndecision_phase_start_month: 10\n"
        f"history_path: {tmp_path / 'h.csv'}\n"
    )
    fixture = json.loads(FIXTURE.read_text())
    msg = run(config_path=str(cfg), dry_run=True, today=date(2026, 8, 15), fixture=fixture)
    assert "机票日报" in msg
    assert "🏆 今日最优" in msg
    out = capsys.readouterr().out
    assert "机票日报" in out          # dry-run prints the message


def test_disabled_config_returns_none(tmp_path):
    from src.main import run
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "enabled: false\norigin: TIJ\ndestinations: [CAN]\npassengers: 3\n"
        "currency: MXN\nprice_is_total: true\n"
        "date_pairs:\n  - {depart: \"2026-12-28\", return: \"2027-02-16\"}\n"
        "drop_alert_pct: 8\ndecision_phase_start_month: 10\n"
        f"history_path: {tmp_path / 'h.csv'}\n"
    )
    assert run(config_path=str(cfg), dry_run=True, today=date(2026, 8, 15), fixture={}) is None
