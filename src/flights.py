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
