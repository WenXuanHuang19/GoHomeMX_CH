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
