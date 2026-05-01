from datetime import date


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
            "date": "2024-01-01",
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
    assert summary["capital_split"]["total_cost"] == 10000.0
    assert summary["capital_split"]["total_equity"] == 6000.0
    assert summary["capital_split"]["total_borrowed"] == 4000.0
    assert summary["current_value"] == 8528.0
    assert summary["total_dividend_reinvested"] == 202.0
    assert summary["performance_windows"]["30d_pct"] > 0
    assert summary["returns"]["return_on_equity_net_pct"] is not None

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


def test_sell_without_lot_id_is_rejected(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Fund A", "ticker": "FNA"},
    )
    fund_id = fund_response.json()["id"]

    response = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": fund_id,
            "date": str(date(2024, 1, 1)),
            "type": "SELL",
            "units": 2,
            "price_per_unit": 100,
            "total_amount": 200,
            "borrowed_amount": 0,
        },
    )

    assert response.status_code == 422
