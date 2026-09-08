from app.tests.conftest import auth_header


def test_product_api_rejects_normalized_identifier_collision(
    client, compliance_user
):
    headers = auth_header(client, "compliance@test.local")
    first = client.post(
        "/api/products",
        json={
            "name": "Ações ACME A",
            "product_type": "STOCK",
            "identifier": "ACME3",
        },
        headers=headers,
    )

    duplicate = client.post(
        "/api/products",
        json={
            "name": "Ações ACME B",
            "product_type": "STOCK",
            "identifier": " acme3 ",
        },
        headers=headers,
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert "identifier" in duplicate.json()["detail"].lower()
