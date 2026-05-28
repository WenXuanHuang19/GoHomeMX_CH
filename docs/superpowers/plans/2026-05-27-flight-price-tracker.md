# Flight Price Tracker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python tool that runs daily on GitHub Actions, queries SerpAPI Google Flights for TIJ→CAN/SZX prices across 4 date pairs, judges buy/no-buy using Google price insights + self-built CSV history, and pushes a daily Telegram message.

**Architecture:** Small, single-responsibility modules under `src/`: `models` (dataclasses), `config` (load YAML), `flights` (SerpAPI call + pure normalizer), `history` (CSV store + stats), `recommend` (pure decision function), `notify` (Telegram format + send), `main` (orchestration). History is a CSV committed back to the repo by the Action. Pure functions are unit-tested with fixtures; HTTP layers are thin wrappers.

**Tech Stack:** Python 3.11, `requests`, `PyYAML`, `pytest`. SerpAPI Google Flights API. Telegram Bot API. GitHub Actions cron.

**Reference spec:** `docs/superpowers/specs/2026-05-27-flight-price-tracker-design.md`

---

## File Structure

```
config.yaml                         # all tunables (route, dates, thresholds)
requirements.txt                    # runtime deps
requirements-dev.txt                # pytest
README.md                           # setup guide incl. how to obtain secrets
.gitignore
src/
  __init__.py
  models.py        # SearchParams, FlightResult, HistoryStats, Recommendation
  config.py        # load_config() -> Config
  flights.py       # normalize_response() (pure), search() (HTTP+retry)
  history.py       # HistoryStore: stats_for(), append()
  recommend.py     # recommend() (pure)
  notify.py        # build_message() (pure), send_telegram() (HTTP)
  main.py          # run() orchestration + CLI (--dry-run)
tests/
  __init__.py
  fixtures/serpapi_sample.json
  test_config.py
  test_flights.py
  test_history.py
  test_recommend.py
  test_notify.py
  test_main.py
data/                               # price_history.csv created at runtime
.github/workflows/daily.yml
```

---

## Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `config.yaml`, `src/__init__.py`, `tests/__init__.py`, `README.md` (stub)

- [ ] **Step 1: Create `requirements.txt`**

```
requests==2.32.3
PyYAML==6.0.2
```

- [ ] **Step 2: Create `requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.3
```

- [ ] **Step 3: Create `.gitignore`**

```
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
.env
```

- [ ] **Step 4: Create `config.yaml`**

```yaml
enabled: true
origin: TIJ
destinations: [CAN, SZX]
passengers: 3
currency: MXN
# SerpAPI Google Flights returns the price for the whole party when adults>1.
# If verification shows it returns per-person, set this to false.
price_is_total: true
date_pairs:
  - {depart: "2026-12-28", return: "2027-02-16"}
  - {depart: "2026-12-28", return: "2027-02-17"}
  - {depart: "2026-12-29", return: "2027-02-16"}
  - {depart: "2026-12-29", return: "2027-02-17"}
drop_alert_pct: 8
# Months >= this number are "决策期" (full daily advice); earlier months are
# "观察期" (still daily, just labelled "暂不计划购买"). Oct = 10.
decision_phase_start_month: 10
history_path: data/price_history.csv
```

- [ ] **Step 5: Create empty package markers**

`src/__init__.py` and `tests/__init__.py` — both empty files.

- [ ] **Step 6: Create `README.md` stub**

```markdown
# FlightsTickets — TIJ→CAN/SZX daily price tracker

See `docs/superpowers/specs/2026-05-27-flight-price-tracker-design.md` for the design.
Setup guide (secrets, local dry-run) is filled in by Task 9.
```

- [ ] **Step 7: Commit**

```bash
git add requirements.txt requirements-dev.txt .gitignore config.yaml src/__init__.py tests/__init__.py README.md
git commit -m "chore: project scaffold and config"
```

---

## Task 2: Data models

**Files:**
- Create: `src/models.py`
- Test: `tests/test_main.py` (import smoke — created here, expanded in Task 8)

- [ ] **Step 1: Write `src/models.py`**

```python
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
```

- [ ] **Step 2: Write import smoke test in `tests/test_main.py`**

```python
def test_models_importable():
    from src.models import SearchParams, FlightResult, HistoryStats, Recommendation
    p = SearchParams("TIJ", "CAN", "2026-12-28", "2027-02-16", 3, "MXN")
    assert p.destination == "CAN"
```

- [ ] **Step 3: Run test**

Run: `python -m pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/models.py tests/test_main.py
git commit -m "feat: add data models"
```

---

## Task 3: Config loader

**Files:**
- Create: `src/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.config'`

- [ ] **Step 3: Write `src/config.py`**

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat: add config loader"
```

---

## Task 4: Flights normalizer + SerpAPI client

**Files:**
- Create: `src/flights.py`, `tests/fixtures/serpapi_sample.json`
- Test: `tests/test_flights.py`

- [ ] **Step 1: Create fixture `tests/fixtures/serpapi_sample.json`**

```json
{
  "best_flights": [
    {
      "flights": [
        {"airline": "Aeromexico"},
        {"airline": "China Southern"}
      ],
      "layovers": [{"name": "Mexico City", "id": "MEX"}],
      "total_duration": 1920,
      "price": 68940
    },
    {
      "flights": [
        {"airline": "Volaris"},
        {"airline": "Hainan Airlines"}
      ],
      "layovers": [{"name": "Xi'an", "id": "XIY"}],
      "total_duration": 2040,
      "price": 73800
    }
  ],
  "other_flights": [
    {
      "flights": [{"airline": "United"}, {"airline": "Air China"}],
      "layovers": [{"name": "Los Angeles", "id": "LAX"}, {"name": "Beijing", "id": "PEK"}],
      "total_duration": 2200,
      "price": 81000
    }
  ],
  "price_insights": {
    "lowest_price": 68940,
    "price_level": "low",
    "typical_price_range": [74400, 93600]
  }
}
```

- [ ] **Step 2: Write the failing test**

```python
import json
from pathlib import Path
from src.models import SearchParams
from src.flights import normalize_response

FIXTURE = Path(__file__).parent / "fixtures" / "serpapi_sample.json"


def _params():
    return SearchParams("TIJ", "CAN", "2026-12-28", "2027-02-16", 3, "MXN")


def test_normalize_extracts_per_person_lowest_and_level():
    data = json.loads(FIXTURE.read_text())
    r = normalize_response(data, _params(), price_is_total=True)
    assert r.destination == "CAN"
    assert r.lowest_overall_pp == 22980.0          # 68940 / 3
    assert r.price_level == "low"
    assert r.typical_low == 24800.0                # 74400 / 3
    assert r.typical_high == 31200.0               # 93600 / 3
    assert r.ok is True


def test_normalize_finds_cheapest_hainan_option():
    data = json.loads(FIXTURE.read_text())
    r = normalize_response(data, _params(), price_is_total=True)
    assert r.hainan_lowest_pp == 24600.0           # 73800 / 3


def test_normalize_summarizes_cheapest_itinerary():
    data = json.loads(FIXTURE.read_text())
    r = normalize_response(data, _params(), price_is_total=True)
    assert "1次中转" in r.best_itinerary
    assert "Mexico City" in r.best_itinerary
    assert "32h00m" in r.best_itinerary


def test_normalize_without_insights_falls_back_to_min_price():
    data = {"best_flights": [{"flights": [{"airline": "X"}], "layovers": [], "total_duration": 60, "price": 30000}]}
    r = normalize_response(data, _params(), price_is_total=True)
    assert r.lowest_overall_pp == 10000.0
    assert r.price_level is None
    assert r.hainan_lowest_pp is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_flights.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.flights'`

- [ ] **Step 4: Write `src/flights.py`**

```python
import time
from typing import Optional
import requests

from src.models import SearchParams, FlightResult

SERPAPI_URL = "https://serpapi.com/search"


def _summarize(option: dict) -> str:
    layovers = option.get("layovers") or []
    n = len(layovers)
    names = "/".join(l.get("name", "?") for l in layovers)
    dur = option.get("total_duration") or 0
    h, m = divmod(int(dur), 60)
    airlines = "/".join(dict.fromkeys(
        f.get("airline", "") for f in option.get("flights", []) if f.get("airline")
    ))
    stop_txt = "直飞" if n == 0 else f"{n}次中转({names})"
    return f"{stop_txt} {h}h{m:02d}m · {airlines}"


def _has_hainan(option: dict) -> bool:
    return any(
        "hainan" in (f.get("airline", "").lower())
        for f in option.get("flights", [])
    )


def normalize_response(data: dict, params: SearchParams, price_is_total: bool = True) -> FlightResult:
    passengers = params.passengers

    def pp(x: Optional[float]) -> Optional[float]:
        if x is None:
            return None
        return round(float(x) / passengers, 2) if price_is_total else round(float(x), 2)

    options = (data.get("best_flights") or []) + (data.get("other_flights") or [])
    priced = [o for o in options if o.get("price") is not None]

    insights = data.get("price_insights") or {}
    lowest = insights.get("lowest_price")
    if lowest is None and priced:
        lowest = min(o["price"] for o in priced)

    tr = insights.get("typical_price_range") or [None, None]
    typ_low, typ_high = (list(tr) + [None, None])[:2]

    hainan_prices = [o["price"] for o in priced if _has_hainan(o)]
    hainan_low = min(hainan_prices) if hainan_prices else None

    best_itin = _summarize(min(priced, key=lambda o: o["price"])) if priced else ""

    return FlightResult(
        destination=params.destination,
        depart_date=params.depart_date,
        return_date=params.return_date,
        currency=params.currency,
        lowest_overall_pp=pp(lowest),
        price_level=insights.get("price_level"),
        typical_low=pp(typ_low),
        typical_high=pp(typ_high),
        hainan_lowest_pp=pp(hainan_low),
        best_itinerary=best_itin,
        ok=True,
    )


def search(params: SearchParams, api_key: str, price_is_total: bool = True,
           max_retries: int = 3, timeout: int = 30) -> FlightResult:
    query = {
        "engine": "google_flights",
        "departure_id": params.origin,
        "arrival_id": params.destination,
        "outbound_date": params.depart_date,
        "return_date": params.return_date,
        "currency": params.currency,
        "adults": params.passengers,
        "type": "1",      # 1 = round trip
        "hl": "en",
        "api_key": api_key,
    }
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(SERPAPI_URL, params=query, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(str(data["error"]))
            return normalize_response(data, params, price_is_total)
        except Exception as e:  # noqa: BLE001 - retry any transient failure
            last_err = str(e)
            if attempt < max_retries:
                time.sleep(min(2 ** attempt, 10))
    return FlightResult(
        destination=params.destination,
        depart_date=params.depart_date,
        return_date=params.return_date,
        currency=params.currency,
        lowest_overall_pp=None,
        price_level=None,
        typical_low=None,
        typical_high=None,
        hainan_lowest_pp=None,
        best_itinerary="",
        ok=False,
        error=last_err,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_flights.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add src/flights.py tests/test_flights.py tests/fixtures/serpapi_sample.json
git commit -m "feat: add SerpAPI flights client and normalizer"
```

---

## Task 5: History store + stats

**Files:**
- Create: `src/history.py`
- Test: `tests/test_history.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
from src.models import FlightResult
from src.history import HistoryStore


def _result(dest, dep, ret, price):
    return FlightResult(dest, dep, ret, "MXN", price, "typical", 24000, 31000,
                        None, "1次中转(MEX) 32h00m")


def _write(store, checked_at, dest, dep, ret, price):
    # append() stamps the row with checked_at
    store.append(_result(dest, dep, ret, price), checked_at)


def test_stats_all_time_and_last_value(tmp_path):
    store = HistoryStore(str(tmp_path / "h.csv"))
    _write(store, date(2026, 6, 1), "CAN", "2026-12-28", "2027-02-16", 30000)
    _write(store, date(2026, 6, 2), "CAN", "2026-12-28", "2027-02-16", 28000)
    s = store.stats_for("CAN", "2026-12-28", "2027-02-16", date(2026, 6, 3))
    assert s.prior_all_time_low == 28000
    assert s.last_value == 28000
    assert s.days_tracked == 2


def test_stats_excludes_today_and_other_keys(tmp_path):
    store = HistoryStore(str(tmp_path / "h.csv"))
    _write(store, date(2026, 6, 3), "CAN", "2026-12-28", "2027-02-16", 25000)  # today
    _write(store, date(2026, 6, 2), "SZX", "2026-12-28", "2027-02-16", 21000)  # other key
    _write(store, date(2026, 6, 2), "CAN", "2026-12-28", "2027-02-16", 27000)
    s = store.stats_for("CAN", "2026-12-28", "2027-02-16", date(2026, 6, 3))
    assert s.prior_all_time_low == 27000   # today's 25000 excluded
    assert s.days_tracked == 1             # only the 6/2 CAN row


def test_stats_week_and_month_low(tmp_path):
    store = HistoryStore(str(tmp_path / "h.csv"))
    # today = Wed 2026-06-17 (ISO week 25). Same-week prior: Mon 6/15.
    _write(store, date(2026, 6, 15), "CAN", "2026-12-28", "2027-02-16", 26000)  # this week
    _write(store, date(2026, 6, 8),  "CAN", "2026-12-28", "2027-02-16", 24000)  # prev week, this month
    _write(store, date(2026, 5, 20), "CAN", "2026-12-28", "2027-02-16", 23000)  # prev month
    s = store.stats_for("CAN", "2026-12-28", "2027-02-16", date(2026, 6, 17))
    assert s.prior_week_low == 26000
    assert s.prior_month_low == 24000      # min within June (excludes May)
    assert s.prev_week_avg == 24000        # week containing 6/8
    assert s.prev_month_avg == 23000       # May average
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_history.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.history'`

- [ ] **Step 3: Write `src/history.py`**

```python
import csv
import os
from datetime import date, timedelta
from typing import List, Optional

from src.models import FlightResult, HistoryStats

FIELDS = [
    "checked_at", "depart_date", "return_date", "destination", "currency",
    "lowest_overall_pp", "price_level", "typical_low", "typical_high",
    "hainan_lowest_pp", "best_itinerary",
]


def _f(x: str) -> Optional[float]:
    return float(x) if x not in (None, "") else None


class HistoryStore:
    def __init__(self, path: str):
        self.path = path

    def _read_rows(self) -> List[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    def append(self, result: FlightResult, checked_at: date) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        exists = os.path.exists(self.path)
        with open(self.path, "a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            if not exists:
                w.writeheader()
            w.writerow({
                "checked_at": checked_at.isoformat(),
                "depart_date": result.depart_date,
                "return_date": result.return_date,
                "destination": result.destination,
                "currency": result.currency,
                "lowest_overall_pp": result.lowest_overall_pp,
                "price_level": result.price_level or "",
                "typical_low": result.typical_low if result.typical_low is not None else "",
                "typical_high": result.typical_high if result.typical_high is not None else "",
                "hainan_lowest_pp": result.hainan_lowest_pp if result.hainan_lowest_pp is not None else "",
                "best_itinerary": result.best_itinerary,
            })

    def stats_for(self, destination: str, depart_date: str, return_date: str,
                  today: date) -> HistoryStats:
        rows = []
        for r in self._read_rows():
            if (r["destination"] == destination
                    and r["depart_date"] == depart_date
                    and r["return_date"] == return_date):
                d = date.fromisoformat(r["checked_at"])
                price = _f(r["lowest_overall_pp"])
                if d < today and price is not None:
                    rows.append((d, price))

        if not rows:
            return HistoryStats(None, None, None, None, None, None, 0)

        rows.sort(key=lambda t: t[0])
        prices = [p for _, p in rows]

        ty, tw, _ = today.isocalendar()
        prev_week_anchor = today - timedelta(days=7)
        py, pw, _ = prev_week_anchor.isocalendar()

        def in_iso_week(d, y, w):
            iy, iw, _ = d.isocalendar()
            return iy == y and iw == w

        prev_month_y = today.year if today.month > 1 else today.year - 1
        prev_month_m = today.month - 1 if today.month > 1 else 12

        week_lows = [p for d, p in rows if in_iso_week(d, ty, tw)]
        month_lows = [p for d, p in rows if d.year == today.year and d.month == today.month]
        prev_week = [p for d, p in rows if in_iso_week(d, py, pw)]
        prev_month = [p for d, p in rows if d.year == prev_month_y and d.month == prev_month_m]

        def avg(xs):
            return round(sum(xs) / len(xs), 2) if xs else None

        return HistoryStats(
            prior_all_time_low=min(prices),
            prior_month_low=min(month_lows) if month_lows else None,
            prior_week_low=min(week_lows) if week_lows else None,
            prev_week_avg=avg(prev_week),
            prev_month_avg=avg(prev_month),
            last_value=rows[-1][1],
            days_tracked=len(rows),
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_history.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/history.py tests/test_history.py
git commit -m "feat: add CSV history store and stats"
```

---

## Task 6: Recommendation engine

**Files:**
- Create: `src/recommend.py`
- Test: `tests/test_recommend.py`

- [ ] **Step 1: Write the failing test**

```python
from src.models import FlightResult, HistoryStats, Recommendation
from src.recommend import recommend


def _result(price, level, typ_low=24800, typ_high=31200):
    return FlightResult("CAN", "2026-12-28", "2027-02-16", "MXN", price, level,
                        typ_low, typ_high, None, "1次中转(MEX) 32h00m")


def _stats(all_low=None, month_low=None, week_low=None, last=None,
           wk_avg=None, mo_avg=None, days=5):
    return HistoryStats(all_low, month_low, week_low, wk_avg, mo_avg, last, days)


def test_strong_buy_on_all_time_low_and_low_level():
    r = recommend(_result(22000, "low"), _stats(all_low=23000, last=23000, days=5))
    assert r.tier == "strong_buy"
    assert r.milestone == "all_time"
    assert "史上新低" in r.milestone_label


def test_buy_when_low_but_not_record():
    r = recommend(_result(26000, "low"), _stats(all_low=22000, week_low=27000, last=27000))
    assert r.tier == "buy"
    assert r.milestone == "week"   # beats week_low 27000


def test_wait_on_typical():
    r = recommend(_result(28000, "typical"), _stats(all_low=22000, last=28500))
    assert r.tier == "wait"


def test_hold_on_high():
    r = recommend(_result(33000, "high"), _stats(all_low=22000, last=32000))
    assert r.tier == "hold"


def test_drop_alert_triggers_on_8pct_fall():
    r = recommend(_result(27600, "typical"), _stats(all_low=22000, last=30000))
    assert r.drop_alert is True   # 27600 <= 30000 * 0.92


def test_no_data_when_price_missing():
    r = recommend(_result(None, None), _stats())
    assert r.tier == "no_data"


def test_first_ever_record_has_no_milestone():
    r = recommend(_result(25000, "low"), _stats(all_low=None, last=None, days=0))
    assert r.milestone is None


def test_pct_vs_last_week_negative_when_cheaper():
    r = recommend(_result(22500, "low"), _stats(all_low=23000, last=23000, wk_avg=25000))
    assert r.pct_vs_last_week == -10.0   # (22500/25000 - 1) * 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_recommend.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.recommend'`

- [ ] **Step 3: Write `src/recommend.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_recommend.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add src/recommend.py tests/test_recommend.py
git commit -m "feat: add recommendation engine"
```

---

## Task 7: Telegram message builder + sender

**Files:**
- Create: `src/notify.py`
- Test: `tests/test_notify.py`

- [ ] **Step 1: Write the failing test**

```python
from datetime import date
from src.models import FlightResult, HistoryStats, Recommendation
from src.notify import build_message

TIER_RANK = {"strong_buy": 0, "buy": 1, "wait": 2, "hold": 3, "no_data": 4}


def _item(dest, dep, ret, price, tier, milestone_label=None, hainan=None,
          pct_wk=None, pct_mo=None, days=80):
    res = FlightResult(dest, dep, ret, "MXN", price, "low", 24800, 31200,
                       hainan, "1次中转(墨城) 32h00m")
    rec = Recommendation(tier, {"strong_buy": "🟢🟢 强烈建议买", "buy": "🟢 可以买",
                                "wait": "🟡 再观望", "hold": "🔴 暂不建议"}[tier],
                         "all_time" if milestone_label else None, milestone_label,
                         False, pct_wk, pct_mo, None, "reason")
    stats = HistoryStats(20000, 20000, 20000, None, None, price, days)
    return (res, rec, stats)


def test_headline_picks_best_tier_then_cheapest():
    items = [
        _item("SZX", "2026-12-28", "2027-02-16", 25000, "wait"),
        _item("CAN", "2026-12-29", "2027-02-16", 22980, "strong_buy",
              milestone_label="🔥 史上新低", hainan=24600, pct_wk=-5.2, pct_mo=-9.8),
        _item("CAN", "2026-12-28", "2027-02-16", 24100, "buy"),
    ]
    msg = build_message(items, today=date(2026, 8, 15), decision_phase_start_month=10)
    assert "🏆 今日最优" in msg
    assert "12/29 → 2/16" in msg          # headline = strong_buy combo
    assert "广州(CAN)" in msg
    assert "22,980" in msg                 # thousands separator
    assert "🔥 史上新低" in msg
    assert "含海航最低:MXN 24,600" in msg
    assert "较上周均价 -5.2%" in msg
    assert "观察期" in msg                  # Aug < Oct


def test_failed_combos_get_warning():
    bad = FlightResult("CAN", "2026-12-28", "2027-02-16", "MXN", None, None,
                       None, None, None, "", ok=False, error="timeout")
    rec = Recommendation("no_data", "⚪ 无数据", None, None, False, None, None, None, "fail")
    stats = HistoryStats(None, None, None, None, None, None, 0)
    good = _item("SZX", "2026-12-28", "2027-02-16", 25000, "wait")
    msg = build_message([(bad, rec, stats), good], today=date(2026, 11, 1),
                        decision_phase_start_month=10)
    assert "部分组合抓取失败" in msg
    assert "决策期" in msg                  # Nov >= Oct


def test_all_failed_message():
    bad = FlightResult("CAN", "2026-12-28", "2027-02-16", "MXN", None, None,
                       None, None, None, "", ok=False, error="timeout")
    rec = Recommendation("no_data", "⚪ 无数据", None, None, False, None, None, None, "fail")
    stats = HistoryStats(None, None, None, None, None, None, 0)
    msg = build_message([(bad, rec, stats)], today=date(2026, 11, 1),
                        decision_phase_start_month=10)
    assert "今日抓取全部失败" in msg
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_notify.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'src.notify'`

- [ ] **Step 3: Write `src/notify.py`**

```python
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
    others = [it for it in good if it is not (res, rec, stats)]
    # group by date pair for compact display
    seen = set()
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_notify.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/notify.py tests/test_notify.py
git commit -m "feat: add Telegram message builder and sender"
```

---

## Task 8: Orchestration + CLI

**Files:**
- Create: `src/main.py`
- Modify: `tests/test_main.py` (add run smoke test)

- [ ] **Step 1: Write the failing test (append to `tests/test_main.py`)**

```python
import json
from datetime import date
from pathlib import Path
from src.main import run

FIXTURE = Path(__file__).parent / "fixtures" / "serpapi_sample.json"


def test_dry_run_uses_fixture_and_returns_message(tmp_path, capsys):
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
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "enabled: false\norigin: TIJ\ndestinations: [CAN]\npassengers: 3\n"
        "currency: MXN\nprice_is_total: true\n"
        "date_pairs:\n  - {depart: \"2026-12-28\", return: \"2027-02-16\"}\n"
        "drop_alert_pct: 8\ndecision_phase_start_month: 10\n"
        f"history_path: {tmp_path / 'h.csv'}\n"
    )
    assert run(config_path=str(cfg), dry_run=True, today=date(2026, 8, 15), fixture={}) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL with `ImportError: cannot import name 'run'`

- [ ] **Step 3: Write `src/main.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_main.py -v`
Expected: PASS (3 tests total in file)

- [ ] **Step 5: Run the full suite + real dry-run**

Run: `python -m pytest -v`
Expected: PASS (all tests)

Run: `python -m src.main --dry-run`
Expected: prints a `机票日报` message to stdout, no network calls.

- [ ] **Step 6: Commit**

```bash
git add src/main.py tests/test_main.py
git commit -m "feat: add orchestration and CLI with dry-run"
```

---

## Task 9: GitHub Actions workflow + README setup guide

**Files:**
- Create: `.github/workflows/daily.yml`
- Modify: `README.md`

- [ ] **Step 1: Create `.github/workflows/daily.yml`**

```yaml
name: Daily flight price check

on:
  schedule:
    - cron: "0 17 * * *"   # 17:00 UTC ≈ 09:00 Tijuana in winter (PST)
  workflow_dispatch:        # allow manual run from the Actions tab

permissions:
  contents: write           # needed to commit price_history.csv back

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - name: Run tracker
        env:
          SERPAPI_KEY: ${{ secrets.SERPAPI_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python -m src.main
      - name: Commit updated history
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/price_history.csv
          git diff --staged --quiet || git commit -m "data: price history $(date -u +%F)"
          git push
```

- [ ] **Step 2: Replace `README.md` with the full setup guide**

```markdown
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
```

- [ ] **Step 3: Verify workflow YAML is valid**

Run: `python -c "import yaml; yaml.safe_load(open('.github/workflows/daily.yml')); print('workflow yaml ok')"`
Expected: `workflow yaml ok`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/daily.yml README.md
git commit -m "ci: add daily GitHub Actions workflow and setup guide"
```

---

## Post-implementation: live verification (with user)

These need the user's real secrets, so they happen after the code is merged:

1. User obtains the three secrets (README table) and adds them to the repo.
2. User triggers the workflow manually (Actions tab → **Run workflow**).
3. Confirm a Telegram message arrives and `data/price_history.csv` gets a commit.
4. **Verify the price normalization assumption** (spec §13): compare the per-person
   figure in the Telegram message against what Google Flights shows for the same
   search. If it's off by ~3×, flip `price_is_total` in `config.yaml`.

---

## Self-Review

**Spec coverage:**
- §2 SerpAPI Google Flights + price_insights → Task 4. ✅
- §2 GitHub Actions / Telegram / Python / CSV → Tasks 9, 7, all, 5. ✅
- §2 budget 8/day (4 pairs × 2 cities) → `combos` in Task 8. ✅
- §4 CSV schema → Task 5 `FIELDS`. ✅
- §5 five tiers + three milestone badges + week/month % → Task 6. ✅
- §6 Hainan: cheapest-overall + surface cheapest Hainan, no extra query → Task 4 `_has_hainan`/`hainan_lowest_pp`, shown in Task 7. ✅
- §7 daily, no silent days; 观察期/决策期 label → Task 7 `phase`. ✅
- §8 errors: per-combo skip + warning, all-failed message, no-insights fallback, no-Hainan text → Tasks 4 (`ok`/`error`), 7 (warnings/all-failed), 6 (no-data + no-signal fallback). ✅
- §9 cron 17:00 UTC + workflow_dispatch → Task 9. ✅
- §10 unit tests for pure parts + dry-run + manual trigger → Tasks 4–8, 9. ✅
- §11 secrets guide → Task 9 README. ✅
- §13 normalization verification → Post-implementation step 4. ✅

**Placeholder scan:** No TBD/TODO; every code step has complete code.

**Type consistency:** `SearchParams`, `FlightResult`, `HistoryStats`, `Recommendation` defined in Task 2 and used unchanged in Tasks 3–8. `normalize_response(data, params, price_is_total)`, `search(params, api_key, price_is_total, ...)`, `HistoryStore.stats_for(destination, depart_date, return_date, today)`, `HistoryStore.append(result, checked_at)`, `recommend(result, stats, drop_alert_pct)`, `build_message(items, today, decision_phase_start_month)`, `send_telegram(text, token, chat_id)`, `run(config_path, dry_run, today, fixture)` — signatures consistent across tasks. ✅
