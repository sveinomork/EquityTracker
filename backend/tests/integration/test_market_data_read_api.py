def test_list_prices_and_rates_with_filters(client) -> None:
    fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Filter Fund", "ticker": "FLR"},
    )
    fund_id = fund_response.json()["id"]

    prices_response = client.post(
        f"/api/v1/funds/{fund_id}/prices",
        json={
            "items": [
                {"date": "2024-01-01", "price": 100},
                {"date": "2024-01-10", "price": 101},
                {"date": "2024-01-20", "price": 102},
            ]
        },
    )
    assert prices_response.status_code == 201

    rates_response = client.post(
        f"/api/v1/funds/{fund_id}/rates",
        json={
            "items": [
                {"effective_date": "2024-01-01", "nominal_rate": 0.05},
                {"effective_date": "2024-02-01", "nominal_rate": 0.06},
            ]
        },
    )
    assert rates_response.status_code == 201

    get_prices_response = client.get(
        f"/api/v1/funds/{fund_id}/prices",
        params={"from_date": "2024-01-05", "to_date": "2024-01-31"},
    )
    assert get_prices_response.status_code == 200
    prices = get_prices_response.json()
    assert len(prices) == 2
    assert prices[0]["date"] == "2024-01-10"
    assert prices[1]["date"] == "2024-01-20"

    get_rates_response = client.get(
        f"/api/v1/funds/{fund_id}/rates",
        params={"to_date": "2024-01-31"},
    )
    assert get_rates_response.status_code == 200
    rates = get_rates_response.json()
    assert len(rates) == 1
    assert rates[0]["effective_date"] == "2024-01-01"


def test_list_transactions_with_optional_fund_filter(client) -> None:
    first_fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Transaction Fund A", "ticker": "TFA"},
    )
    second_fund_response = client.post(
        "/api/v1/funds",
        json={"name": "Transaction Fund B", "ticker": "TFB"},
    )
    first_fund_id = first_fund_response.json()["id"]
    second_fund_id = second_fund_response.json()["id"]

    transaction_a = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": first_fund_id,
            "date": "2026-01-01",
            "type": "BUY",
            "units": 10,
            "price_per_unit": 100,
            "total_amount": 1000,
            "borrowed_amount": 300,
        },
    )
    transaction_b = client.post(
        "/api/v1/transactions",
        json={
            "fund_id": second_fund_id,
            "date": "2026-01-02",
            "type": "BUY",
            "units": 20,
            "price_per_unit": 50,
            "total_amount": 1000,
            "borrowed_amount": 0,
        },
    )
    assert transaction_a.status_code == 201
    assert transaction_b.status_code == 201

    all_transactions_response = client.get("/api/v1/transactions")
    assert all_transactions_response.status_code == 200
    all_transactions = all_transactions_response.json()
    assert len(all_transactions) == 2

    filtered_response = client.get(
        "/api/v1/transactions",
        params={"fund_id": first_fund_id},
    )
    assert filtered_response.status_code == 200
    filtered_transactions = filtered_response.json()
    assert len(filtered_transactions) == 1
    assert filtered_transactions[0]["fund_id"] == first_fund_id
