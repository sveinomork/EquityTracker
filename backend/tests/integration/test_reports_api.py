import pytest


def _seed_basic_fund_with_history(client) -> str:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Report Fund", "ticker": "RPT"},
    )
    assert fund_response.status_code == 201
    fund_id = fund_response.json()["id"]

    buy_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": "2024-01-10",
            "type": "BUY",
            "units": 100,
            "price_per_unit": 100,
            "total_amount": 10000,
            "borrowed_amount": 0,
        },
    )
    assert buy_response.status_code == 201
    lot_id = buy_response.json()["id"]

    reinvest_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "lot_id": lot_id,
            "date": "2024-03-10",
            "type": "DIVIDEND_REINVEST",
            "units": 2,
            "price_per_unit": 102,
            "total_amount": 204,
            "borrowed_amount": 0,
        },
    )
    assert reinvest_response.status_code == 201

    sell_response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "lot_id": lot_id,
            "date": "2024-03-20",
            "type": "SELL",
            "units": 20,
            "price_per_unit": 103,
            "total_amount": 2060,
            "borrowed_amount": 0,
        },
    )
    assert sell_response.status_code == 201

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2024-01-10", "price": 100},
                {"date": "2024-02-29", "price": 101},
                {"date": "2024-03-29", "price": 105},
            ]
        },
    )
    assert prices_response.status_code == 201

    return fund_id


def test_report_period_options_include_historical_months(client) -> None:
    _seed_basic_fund_with_history(client)

    response = client.get(
        "/api/v1/reports/period-options",
        params={"period_type": "monthly", "as_of_date": "2024-03-31"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["period_type"] == "monthly"
    assert payload["data_start_date"] == "2024-01-10"
    assert payload["data_end_date"] == "2024-03-29"

    values = [item["value"] for item in payload["options"]]
    assert "2024-01" in values
    assert "2024-02" in values
    assert "2024-03" in values


def test_period_report_includes_each_fund_and_units(client) -> None:
    _seed_basic_fund_with_history(client)

    response = client.get(
        "/api/v1/reports/period",
        params={"period_type": "monthly", "period_value": "2024-03"},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["period_type"] == "monthly"
    assert payload["period_value"] == "2024-03"
    assert payload["period_start"] == "2024-03-01"
    assert payload["period_end"] == "2024-03-31"
    assert payload["as_of_date"] == "2024-03-29"

    assert payload["portfolio"]["totals"]["current_value"] == pytest.approx(8610.0, abs=0.01)

    assert len(payload["funds"]) == 1
    fund_row = payload["funds"][0]
    assert fund_row["ticker"] == "RPT"
    assert fund_row["units"] == pytest.approx(82.0, abs=1e-6)
    assert fund_row["latest_price_date"] == "2024-03-29"


def test_period_report_rejects_invalid_period_value(client) -> None:
    _seed_basic_fund_with_history(client)

    response = client.get(
        "/api/v1/reports/period",
        params={"period_type": "quarterly", "period_value": "2024-Q9"},
    )

    assert response.status_code == 400
    assert "format YYYY-QN" in response.json()["detail"]
