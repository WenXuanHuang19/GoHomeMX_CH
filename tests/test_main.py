def test_models_importable():
    from src.models import SearchParams, FlightResult, HistoryStats, Recommendation
    p = SearchParams("TIJ", "CAN", "2026-12-28", "2027-02-16", 3, "MXN")
    assert p.destination == "CAN"
