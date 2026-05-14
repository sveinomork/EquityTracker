from datetime import date

import pytest


def _xirr_pct(cashflows: list[tuple[date, float]]) -> float | None:
    if not cashflows:
        return None

    has_positive = any(amount > 0 for _, amount in cashflows)
    has_negative = any(amount < 0 for _, amount in cashflows)
    if not has_positive or not has_negative:
        return None

    ordered = sorted(cashflows, key=lambda item: item[0])
    first_date = ordered[0][0]

    def npv(rate: float) -> float:
        total = 0.0
        for flow_date, amount in ordered:
            years = (flow_date - first_date).days / 365.0
            total += amount / ((1.0 + rate) ** years)
        return total

    low = -0.999999
    high = 1.0
    f_low = npv(low)
    f_high = npv(high)

    for _ in range(40):
        if f_low * f_high < 0:
            break
        high *= 2.0
        if high > 1_000_000:
            return None
        f_high = npv(high)
    else:
        return None

    mid = 0.0
    for _ in range(100):
        mid = (low + high) / 2.0
        f_mid = npv(mid)
        if abs(f_mid) < 1e-8:
            break
        if f_low * f_mid <= 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid

    return mid * 100.0


def test_fund_summary_and_lots_include_analytics(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Fondsfinans High Yield", "ticker": "FHY"},
    )
    fund_id = fund_response.json()["id"]

    buy_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2000-01-01",
            "type": "BUY",
            "units": 100,
            "price_per_unit": 100,
            "total_amount": 10000,
            "borrowed_amount": 4000,
        },
    )
    assert buy_response.status_code == 201
    lot_id = buy_response.json()["id"]

    dividend_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "lot_id": lot_id,
            "date": "2024-02-01",
            "type": "DIVIDEND_REINVEST",
            "units": 2,
            "price_per_unit": 101,
            "total_amount": 202,
            "borrowed_amount": 0,
        },
    )
    assert dividend_response.status_code == 201

    sell_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "lot_id": lot_id,
            "date": "2024-03-15",
            "type": "SELL",
            "units": 20,
            "price_per_unit": 102,
            "total_amount": 2040,
            "borrowed_amount": 0,
        },
    )
    assert sell_response.status_code == 201

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2024-01-01", "price": 100},
                {"date": "2024-03-01", "price": 103},
                {"date": "2024-04-01", "price": 104},
            ]
        },
    )
    assert prices_response.status_code == 201

    rates_response = client.post(
        f"/api/v1/funds/{fund_id}/rates",
        json={"items": [{"effective_date": "2024-01-01", "nominal_rate": 0.05}]},
    )
    assert rates_response.status_code == 201

    summary_response = client.get(
        f"/api/v1/funds/{fund_id}/summary", params={"as_of_date": "2024-04-01"}
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()

    assert summary["fund_name"] == "Fondsfinans High Yield"
    assert summary["capital_split"]["total_cost"] == pytest.approx(8039.21568627451, abs=1e-6)
    assert summary["capital_split"]["total_equity"] == pytest.approx(4823.529411764706, abs=1e-6)
    assert summary["capital_split"]["total_borrowed"] == pytest.approx(3215.686274509804, abs=1e-6)
    assert summary["current_value"] == 8528.0
    assert summary["total_dividend_reinvested"] == 202.0
    assert summary["realized_profit_from_sold_positions"] == pytest.approx(79.21568627451, abs=1e-6)
    assert summary["profit_loss_gross"] == pytest.approx(488.78431372549, abs=1e-6)
    assert summary["profit_loss_gross_including_realized"] == pytest.approx(366.0, abs=1e-6)
    assert summary["performance_windows"]["14d_pct"] is None
    assert summary["performance_windows"]["30d_pct"] > 0
    assert summary["returns"]["return_on_equity_net_pct"] is not None
    assert "annualized_return_on_cost_weighted_pct" in summary["returns"]

    lots_response = client.get(f"/api/v1/funds/{fund_id}/lots", params={"as_of_date": "2024-04-01"})
    assert lots_response.status_code == 200
    lots_payload = lots_response.json()
    assert len(lots_payload["lots"]) == 1
    assert lots_payload["lots"][0]["current_units"] == 82.0

    portfolio_response = client.get(
        "/api/v1/portfolio/summary", params={"as_of_date": "2024-04-01"}
    )
    assert portfolio_response.status_code == 200
    portfolio = portfolio_response.json()
    assert portfolio["totals"]["current_value"] == 8528.0
    assert len(portfolio["funds"]) == 1


def test_sell_without_lot_id_is_fifo_allocated(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Fund A", "ticker": "FNA"},
    )
    fund_id = fund_response.json()["id"]

    buy_lot_1 = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2024-01-01",
            "type": "BUY",
            "units": 10,
            "price_per_unit": 100,
            "total_amount": 1000,
            "borrowed_amount": 0,
        },
    )
    assert buy_lot_1.status_code == 201
    lot_1_id = buy_lot_1.json()["id"]

    buy_lot_2 = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2024-01-02",
            "type": "BUY",
            "units": 10,
            "price_per_unit": 110,
            "total_amount": 1100,
            "borrowed_amount": 0,
        },
    )
    assert buy_lot_2.status_code == 201
    lot_2_id = buy_lot_2.json()["id"]

    response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": str(date(2024, 1, 3)),
            "type": "SELL",
            "units": 12,
            "price_per_unit": 105,
            "total_amount": 1260,
            "borrowed_amount": 0,
        },
    )

    assert response.status_code == 201

    list_response = client.get("/api/v1/transactions", params={"fund_id": fund_id})
    assert list_response.status_code == 200
    payload = list_response.json()

    sells = [item for item in payload if item["type"] == "SELL"]
    assert len(sells) == 2
    assert sells[0]["lot_id"] == lot_1_id
    assert sells[1]["lot_id"] == lot_2_id
    assert sells[0]["units"] == pytest.approx(-10.0, abs=0.0001)
    assert sells[1]["units"] == pytest.approx(-2.0, abs=0.0001)
    assert (sells[0]["total_amount"] + sells[1]["total_amount"]) == pytest.approx(1260.0, abs=0.01)


def test_distributing_fund_total_period_metrics_use_consistent_formula(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Fondsfinans High Yield", "ticker": "FHY"},
    )
    fund_id = fund_response.json()["id"]

    buy_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2024-01-01",
            "type": "BUY",
            "units": 100,
            "price_per_unit": 100,
            "total_amount": 10000,
            "borrowed_amount": 0,
        },
    )
    assert buy_response.status_code == 201
    lot_id = buy_response.json()["id"]

    dividend_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "lot_id": lot_id,
            "date": "2024-02-01",
            "type": "DIVIDEND_REINVEST",
            "units": 2,
            "price_per_unit": 101,
            "total_amount": 202,
            "borrowed_amount": 0,
        },
    )
    assert dividend_response.status_code == 201

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2024-01-01", "price": 100},
                {"date": "2024-04-01", "price": 104},
            ]
        },
    )
    assert prices_response.status_code == 201

    summary_response = client.get(
        f"/api/v1/funds/{fund_id}/summary",
        params={"as_of_date": "2024-04-01"},
    )
    assert summary_response.status_code == 200

    total = summary_response.json()["period_metrics"]["Total"]

    expected_gross = 608.0
    expected_dividend_tax = 44.44
    expected_return_pct = 6.08
    expected_net_liquidity = -44.44
    expected_net_value = 563.56

    assert total["brutto_value_change_nok"] == pytest.approx(expected_gross, abs=0.01)
    assert total["return_pct_fund"] == pytest.approx(expected_return_pct, abs=0.01)
    assert total["running_dividend_tax_nok"] == pytest.approx(expected_dividend_tax, abs=0.01)
    assert total["net_liquidity_margin_nok"] == pytest.approx(expected_net_liquidity, abs=0.01)
    assert total["net_value_margin_nok"] == pytest.approx(expected_net_value, abs=0.01)


def test_reconciliation_endpoint_exposes_period_formula_components(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Fondsfinans High Yield", "ticker": "FHY"},
    )
    fund_id = fund_response.json()["id"]

    buy_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2024-01-01",
            "type": "BUY",
            "units": 100,
            "price_per_unit": 100,
            "total_amount": 10000,
            "borrowed_amount": 0,
        },
    )
    assert buy_response.status_code == 201
    lot_id = buy_response.json()["id"]

    dividend_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "lot_id": lot_id,
            "date": "2024-02-01",
            "type": "DIVIDEND_REINVEST",
            "units": 2,
            "price_per_unit": 101,
            "total_amount": 202,
            "borrowed_amount": 0,
        },
    )
    assert dividend_response.status_code == 201

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2024-01-01", "price": 100},
                {"date": "2024-04-01", "price": 104},
            ]
        },
    )
    assert prices_response.status_code == 201

    response = client.get(
        "/api/v1/portfolio/reconciliation/fund-period",
        params={"ticker": "FHY", "as_of_date": "2024-04-01"},
    )
    assert response.status_code == 200

    payload = response.json()
    total = next(row for row in payload["rows"] if row["period_key"] == "total")

    assert total["value_t0"] == pytest.approx(10000.0, abs=0.01)
    assert total["value_t1"] == pytest.approx(10608.0, abs=0.01)
    assert total["net_external_cashflow_nok"] == pytest.approx(0.0, abs=0.01)
    assert total["period_capital_base_nok"] == pytest.approx(10000.0, abs=0.01)
    assert total["gross_value_change_nok"] == pytest.approx(608.0, abs=0.01)
    assert total["running_dividend_tax_nok"] == pytest.approx(44.44, abs=0.01)
    assert total["net_liquidity_margin_nok"] == pytest.approx(-44.44, abs=0.01)
    assert total["net_value_margin_nok"] == pytest.approx(563.56, abs=0.01)
    assert total["return_pct_fund"] == pytest.approx(6.08, abs=0.01)


def test_period_windows_keep_fixed_start_dates_for_young_fund(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Window Fund", "ticker": "WFD"},
    )
    fund_id = fund_response.json()["id"]

    buy_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2025-09-30",
            "type": "BUY",
            "units": 10,
            "price_per_unit": 100,
            "total_amount": 1000,
            "borrowed_amount": 500,
        },
    )
    assert buy_response.status_code == 201

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2025-09-30", "price": 100},
                {"date": "2026-05-03", "price": 102},
            ]
        },
    )
    assert prices_response.status_code == 201

    rates_response = client.post(
        f"/api/v1/funds/{fund_id}/rates",
        json={"items": [{"effective_date": "2025-09-30", "nominal_rate": 0.05}]},
    )
    assert rates_response.status_code == 201

    summary_response = client.get(
        f"/api/v1/funds/{fund_id}/summary",
        params={"as_of_date": "2026-05-03"},
    )
    assert summary_response.status_code == 200
    payload = summary_response.json()["period_metrics"]

    assert payload["12m"]["start_date"] == "2025-05-03"
    assert payload["24m"]["start_date"] == "2024-05-03"
    assert payload["Total"]["start_date"] == "2025-09-30"
    assert payload["12m"]["return_pct_fund"] is None
    assert payload["24m"]["return_pct_fund"] is None
    assert payload["Total"]["return_pct_fund"] is not None


def test_weighted_annualized_return_on_cost_is_xirr_like(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "XIRR Fund", "ticker": "XIRR"},
    )
    fund_id = fund_response.json()["id"]

    first_buy_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2024-01-01",
            "type": "BUY",
            "units": 100,
            "price_per_unit": 100,
            "total_amount": 10000,
            "borrowed_amount": 0,
        },
    )
    assert first_buy_response.status_code == 201

    second_buy_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2024-07-01",
            "type": "BUY",
            "units": 50,
            "price_per_unit": 110,
            "total_amount": 5500,
            "borrowed_amount": 0,
        },
    )
    assert second_buy_response.status_code == 201

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2024-01-01", "price": 100},
                {"date": "2024-07-01", "price": 110},
                {"date": "2024-12-31", "price": 120},
            ]
        },
    )
    assert prices_response.status_code == 201

    summary_response = client.get(
        f"/api/v1/funds/{fund_id}/summary",
        params={"as_of_date": "2024-12-31"},
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()

    expected = _xirr_pct(
        [
            (date(2024, 1, 1), -10000.0),
            (date(2024, 7, 1), -5500.0),
            (date(2024, 12, 31), 18000.0),
        ]
    )
    assert expected is not None
    assert summary["returns"]["annualized_return_on_cost_weighted_pct"] == pytest.approx(
        expected,
        abs=0.01,
    )


def test_rolling_period_gross_change_excludes_in_period_cashflows(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Rolling Window Fund", "ticker": "RWF"},
    )
    fund_id = fund_response.json()["id"]

    first_buy = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2024-01-01",
            "type": "BUY",
            "units": 100,
            "price_per_unit": 100,
            "total_amount": 10000,
            "borrowed_amount": 0,
        },
    )
    assert first_buy.status_code == 201

    second_buy = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2024-07-01",
            "type": "BUY",
            "units": 50,
            "price_per_unit": 110,
            "total_amount": 5500,
            "borrowed_amount": 0,
        },
    )
    assert second_buy.status_code == 201

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2024-01-01", "price": 100},
                {"date": "2024-07-01", "price": 110},
                {"date": "2024-12-31", "price": 120},
            ]
        },
    )
    assert prices_response.status_code == 201

    summary_response = client.get(
        f"/api/v1/funds/{fund_id}/summary",
        params={"as_of_date": "2024-12-31"},
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()

    total = summary["period_metrics"]["Total"]
    m12 = summary["period_metrics"]["12m"]

    # Total follows markedsverdi - kostpris.
    assert total["brutto_value_change_nok"] == pytest.approx(2500.0, abs=0.01)

    # 12m excludes in-period buy cashflow from gross change.
    # value_t1=18000, value_t0=10000, net_external_cashflow=5500 => gross=2500
    assert m12["brutto_value_change_nok"] == pytest.approx(2500.0, abs=0.01)


def test_rolling_period_gross_change_excludes_reinvested_dividends(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Dividend Window Fund", "ticker": "DWF"},
    )
    fund_id = fund_response.json()["id"]

    first_buy = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2024-01-01",
            "type": "BUY",
            "units": 100,
            "price_per_unit": 100,
            "total_amount": 10000,
            "borrowed_amount": 0,
        },
    )
    assert first_buy.status_code == 201
    lot_id = first_buy.json()["id"]

    dividend_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "lot_id": lot_id,
            "date": "2025-06-01",
            "type": "DIVIDEND_REINVEST",
            "units": 2,
            "price_per_unit": 101,
            "total_amount": 202,
            "borrowed_amount": 0,
        },
    )
    assert dividend_response.status_code == 201

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2024-01-01", "price": 100},
                {"date": "2024-12-31", "price": 100},
                {"date": "2025-06-01", "price": 101},
                {"date": "2025-12-31", "price": 101},
            ]
        },
    )
    assert prices_response.status_code == 201

    summary_response = client.get(
        f"/api/v1/funds/{fund_id}/summary",
        params={"as_of_date": "2025-12-31"},
    )
    assert summary_response.status_code == 200
    summary = summary_response.json()

    m12 = summary["period_metrics"]["12m"]

    # value_t1=10302, value_t0=10000, net_external_cashflow=0 (div not subtracted) => gross=302
    assert m12["brutto_value_change_nok"] == pytest.approx(302.0, abs=0.01)


def test_d1_uses_latest_available_price_day_when_as_of_is_stale(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Stale Price Fund", "ticker": "SPF"},
    )
    fund_id = fund_response.json()["id"]

    buy_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2026-04-20",
            "type": "BUY",
            "units": 100,
            "price_per_unit": 100,
            "total_amount": 10000,
            "borrowed_amount": 0,
        },
    )
    assert buy_response.status_code == 201

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2026-04-29", "price": 109},
                {"date": "2026-04-30", "price": 110},
            ]
        },
    )
    assert prices_response.status_code == 201

    summary_response = client.get(
        f"/api/v1/funds/{fund_id}/summary",
        params={"as_of_date": "2026-05-04"},
    )
    assert summary_response.status_code == 200
    d1 = summary_response.json()["period_metrics"]["1d"]

    assert d1["end_date"] == "2026-04-30"
    assert d1["start_date"] == "2026-04-29"
    assert d1["brutto_value_change_nok"] == pytest.approx(100.0, abs=0.01)
    assert d1["return_split"]["gross_pct"] == pytest.approx((100.0 / 10900.0) * 100.0, abs=0.01)


def test_d7_uses_latest_available_price_day_when_as_of_is_stale(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Stale Price Window Fund", "ticker": "SPW"},
    )
    fund_id = fund_response.json()["id"]

    buy_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2026-04-20",
            "type": "BUY",
            "units": 100,
            "price_per_unit": 100,
            "total_amount": 10000,
            "borrowed_amount": 0,
        },
    )
    assert buy_response.status_code == 201

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2026-04-27", "price": 109.63104},
                {"date": "2026-05-05", "price": 110.03269},
            ]
        },
    )
    assert prices_response.status_code == 201

    summary_response = client.get(
        f"/api/v1/funds/{fund_id}/summary",
        params={"as_of_date": "2026-05-20"},
    )
    assert summary_response.status_code == 200
    d7 = summary_response.json()["period_metrics"]["7d"]

    # With stale as_of_date, 7d should still anchor to latest price date (2026-05-05),
    # so start_date becomes 2026-04-28 and falls back to 2026-04-27 for start price.
    expected_gross = (110.03269 - 109.63104) * 100.0
    expected_base = 109.63104 * 100.0

    assert d7["end_date"] == "2026-05-05"
    assert d7["start_date"] == "2026-04-28"
    assert d7["brutto_value_change_nok"] == pytest.approx(expected_gross, abs=0.01)
    assert d7["return_split"]["gross_pct"] == pytest.approx((expected_gross / expected_base) * 100.0, abs=0.01)


