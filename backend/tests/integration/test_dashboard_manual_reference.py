from __future__ import annotations

from datetime import date

import pytest


def _post_fund(client, name: str, ticker: str) -> str:
    response = client.post("/api/v1/funds", json={"name": name, "ticker": ticker})
    assert response.status_code == 201
    return response.json()["id"]


def _post_transaction(client, payload: dict) -> str:
    response = client.post("/api/v1/transactions", json=payload)
    assert response.status_code == 201
    return response.json()["id"]


def _post_prices(client, fund_id: str, items: list[dict]) -> None:
    response = client.post(f"/api/v1/funds/{fund_id}/prices", json={"items": items})
    assert response.status_code == 201


def _post_rates(client, fund_id: str, items: list[dict]) -> None:
    response = client.post(f"/api/v1/funds/{fund_id}/rates", json={"items": items})
    assert response.status_code == 201


def _assert_period(metric: dict, expected_gross: float, expected_base: float, expected_after: float) -> None:
    split = metric["return_split"]
    expected_gross_pct = (expected_gross / expected_base) * 100 if expected_base else None
    expected_after_pct = (expected_after / expected_base) * 100 if expected_base else None

    assert metric["period_capital_base_nok"] == pytest.approx(expected_base, abs=0.01)
    assert split["gross_amount_nok"] == pytest.approx(expected_gross, abs=0.01)
    assert split["after_interest_amount_nok"] == pytest.approx(expected_after, abs=0.01)

    if expected_gross_pct is None:
        assert split["gross_pct"] is None
    else:
        assert split["gross_pct"] == pytest.approx(expected_gross_pct, abs=0.01)

    if expected_after_pct is None:
        assert split["after_interest_pct"] is None
    else:
        assert split["after_interest_pct"] == pytest.approx(expected_after_pct, abs=0.01)


def _days_inclusive(start: date, end: date) -> int:
    return (end - start).days + 1


def test_dashboard_manual_reference_scenario(client) -> None:
    as_of = "2026-01-01"

    # Fund 1 (FHY): buy, extra buy, dividend reinvest, sell, and borrowing with rates.
    fhy_id = _post_fund(client, "Fond A", "FHY")
    fhy_lot_1 = _post_transaction(
        client,
        {
            "fund_id": fhy_id,
            "date": "2024-01-02",
            "type": "BUY",
            "units": 100,
            "price_per_unit": 100,
            "total_amount": 10000,
            "borrowed_amount": 4000,
        },
    )
    _post_transaction(
        client,
        {
            "fund_id": fhy_id,
            "date": "2025-11-01",
            "type": "BUY",
            "units": 50,
            "price_per_unit": 94,
            "total_amount": 4700,
            "borrowed_amount": 0,
        },
    )
    _post_transaction(
        client,
        {
            "fund_id": fhy_id,
            "lot_id": fhy_lot_1,
            "date": "2025-12-15",
            "type": "DIVIDEND_REINVEST",
            "units": 10,
            "price_per_unit": 90,
            "total_amount": 900,
            "borrowed_amount": 0,
        },
    )
    _post_transaction(
        client,
        {
            "fund_id": fhy_id,
            "lot_id": fhy_lot_1,
            "date": "2025-12-20",
            "type": "SELL",
            "units": 20,
            "price_per_unit": 95,
            "total_amount": 1900,
            "borrowed_amount": 0,
        },
    )
    _post_prices(
        client,
        fhy_id,
        [
            {"date": "2024-01-02", "price": 100},
            {"date": "2025-10-03", "price": 92},
            {"date": "2026-01-01", "price": 100},
        ],
    )
    _post_rates(client, fhy_id, [{"effective_date": "2024-01-01", "nominal_rate": 10.0}])

    # Fund 2 (KNB): buy, sell, rebuy without borrowing.
    knb_id = _post_fund(client, "Fond B", "KNB")
    knb_lot_1 = _post_transaction(
        client,
        {
            "fund_id": knb_id,
            "date": "2024-01-02",
            "type": "BUY",
            "units": 200,
            "price_per_unit": 50,
            "total_amount": 10000,
            "borrowed_amount": 0,
        },
    )
    _post_transaction(
        client,
        {
            "fund_id": knb_id,
            "lot_id": knb_lot_1,
            "date": "2025-06-01",
            "type": "SELL",
            "units": 50,
            "price_per_unit": 58,
            "total_amount": 2900,
            "borrowed_amount": 0,
        },
    )
    _post_transaction(
        client,
        {
            "fund_id": knb_id,
            "date": "2025-11-15",
            "type": "BUY",
            "units": 40,
            "price_per_unit": 60,
            "total_amount": 2400,
            "borrowed_amount": 0,
        },
    )
    _post_prices(
        client,
        knb_id,
        [
            {"date": "2024-01-02", "price": 50},
            {"date": "2025-10-03", "price": 59},
            {"date": "2026-01-01", "price": 62},
        ],
    )

    response = client.get("/api/v1/portfolio/summary", params={"as_of_date": as_of})
    assert response.status_code == 200
    payload = response.json()

    funds_by_ticker = {item["ticker"]: item for item in payload["funds"]}
    fhy = funds_by_ticker["FHY"]
    knb = funds_by_ticker["KNB"]

    # 90d window is price-based, used as a simple dashboard reference check.
    expected_fhy_90d = (100.0 / 92.0 - 1.0) * 100.0
    expected_knb_90d = (62.0 / 59.0 - 1.0) * 100.0
    assert fhy["performance_windows"]["90d_pct"] == pytest.approx(expected_fhy_90d, abs=0.01)
    assert knb["performance_windows"]["90d_pct"] == pytest.approx(expected_knb_90d, abs=0.01)

    # FHY manual expectations.
    fhy_24m_gross = 1200.0
    fhy_24m_base = 12800.0
    fhy_total_gross = 1200.0
    fhy_total_base = 14700.0

    days_before_sell = _days_inclusive(date(2024, 1, 3), date(2025, 12, 19))
    days_after_sell = _days_inclusive(date(2025, 12, 20), date(2026, 1, 1))
    fhy_interest = (
        4000.0 * 0.10 / 365.0 * days_before_sell
        + 3200.0 * 0.10 / 365.0 * days_after_sell
    )

    _assert_period(
        fhy["period_metrics"]["24m"],
        expected_gross=fhy_24m_gross,
        expected_base=fhy_24m_base,
        expected_after=fhy_24m_gross - fhy_interest,
    )
    _assert_period(
        fhy["period_metrics"]["Total"],
        expected_gross=fhy_total_gross,
        expected_base=fhy_total_base,
        expected_after=fhy_total_gross - fhy_interest,
    )

    # KNB manual expectations.
    knb_24m_gross = 2280.0
    knb_24m_base = 9500.0
    knb_total_gross = 2280.0
    knb_total_base = 12400.0

    _assert_period(
        knb["period_metrics"]["24m"],
        expected_gross=knb_24m_gross,
        expected_base=knb_24m_base,
        expected_after=knb_24m_gross,
    )
    _assert_period(
        knb["period_metrics"]["Total"],
        expected_gross=knb_total_gross,
        expected_base=knb_total_base,
        expected_after=knb_total_gross,
    )

    # Portfolio manual expectations = sum of fund period entries.
    portfolio_24m_gross = fhy_24m_gross + knb_24m_gross
    portfolio_24m_base = fhy_24m_base + knb_24m_base
    portfolio_total_gross = fhy_total_gross + knb_total_gross
    portfolio_total_base = fhy_total_base + knb_total_base

    _assert_period(
        payload["period_metrics"]["24m"],
        expected_gross=portfolio_24m_gross,
        expected_base=portfolio_24m_base,
        expected_after=portfolio_24m_gross - fhy_interest,
    )
    _assert_period(
        payload["period_metrics"]["Total"],
        expected_gross=portfolio_total_gross,
        expected_base=portfolio_total_base,
        expected_after=portfolio_total_gross - fhy_interest,
    )
