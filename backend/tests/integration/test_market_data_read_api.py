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
