import textwrap
from src.config import load_config


def test_load_config_parses_date_pairs(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent("""
        enabled: true
        origin: TIJ
        destinations: [CAN, SZX]
        passengers: 3
        currency: MXN
        price_is_total: true
        date_pairs:
          - {depart: "2026-12-28", return: "2027-02-16"}
          - {depart: "2026-12-29", return: "2027-02-17"}
        drop_alert_pct: 8
        decision_phase_start_month: 10
        history_path: data/price_history.csv
    """))
    cfg = load_config(str(p))
    assert cfg.origin == "TIJ"
    assert cfg.destinations == ["CAN", "SZX"]
    assert cfg.date_pairs == [("2026-12-28", "2027-02-16"), ("2026-12-29", "2027-02-17")]
    assert cfg.passengers == 3
    assert cfg.drop_alert_pct == 8


def test_load_config_missing_key_raises(tmp_path):
    p = tmp_path / "config.yaml"
    p.write_text("origin: TIJ\n")
    try:
        load_config(str(p))
        assert False, "expected KeyError"
    except KeyError:
        pass
