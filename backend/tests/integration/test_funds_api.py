def test_create_and_list_fund(client) -> None:
    response = client.post(
        "/api/v1/funds",
        json={"name": "Fondsfinans High Yield", "ticker": "fhy"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["ticker"] == "FHY"

    list_response = client.get("/api/v1/funds")
    assert list_response.status_code == 200
    listed = list_response.json()
    assert len(listed) == 1
    assert listed[0]["name"] == "Fondsfinans High Yield"
