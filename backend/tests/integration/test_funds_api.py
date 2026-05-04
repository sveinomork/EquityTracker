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


def test_update_fund_tax_config(client) -> None:
    response = client.post(
        "/api/v1/funds",
        json={"name": "Tax Fund", "ticker": "TXF"},
    )
    assert response.status_code == 201
    fund_id = response.json()["id"]

    update_response = client.patch(
        f"/api/v1/funds/{fund_id}/tax-config",
        json={"is_distributing": True, "manual_taxable_gain_override": 12345.67},
    )
    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["is_distributing"] is True
    assert payload["manual_taxable_gain_override"] == 12345.67

    clear_response = client.patch(
        f"/api/v1/funds/{fund_id}/tax-config",
        json={"manual_taxable_gain_override": None},
    )
    assert clear_response.status_code == 200
    assert clear_response.json()["manual_taxable_gain_override"] is None
