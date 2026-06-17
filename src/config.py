from dataclasses import dataclass
from typing import List, Tuple
import yaml

REQUIRED = [
    "enabled", "origin", "destinations", "passengers", "currency",
    "price_is_total", "date_pairs", "drop_alert_pct",
    "decision_phase_start_month", "history_path",
]


@dataclass
class Config:
    enabled: bool
    origin: str
    destinations: List[str]
    passengers: int
    currency: str
    price_is_total: bool
    date_pairs: List[Tuple[str, str]]
    drop_alert_pct: float
    decision_phase_start_month: int
    history_path: str


def load_config(path: str) -> Config:
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    for key in REQUIRED:
        if key not in raw:
            raise KeyError(f"config missing required key: {key}")
    date_pairs = [(d["depart"], d["return"]) for d in raw["date_pairs"]]
    return Config(
        enabled=bool(raw["enabled"]),
        origin=raw["origin"],
        destinations=list(raw["destinations"]),
        passengers=int(raw["passengers"]),
        currency=raw["currency"],
        price_is_total=bool(raw["price_is_total"]),
        date_pairs=date_pairs,
        drop_alert_pct=float(raw["drop_alert_pct"]),
        decision_phase_start_month=int(raw["decision_phase_start_month"]),
        history_path=raw["history_path"],
    )
