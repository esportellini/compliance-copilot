from app.tests.conftest import auth_header


def _payload(condition):
    return {
        "name": "Regra validada",
        "product_type": "OPEN_FUND",
        "condition": condition,
        "decision": "ALLOWED",
        "risk": "LOW",
        "priority": 10,
        "is_active": True,
    }


def test_rule_api_rejects_unknown_condition_key(client, compliance_user):
    headers = auth_header(client, "compliance@test.local")

    response = client.post(
        "/api/rules",
        json=_payload({"amount_gr": 100_000}),
        headers=headers,
    )

    assert response.status_code == 422


def test_rule_api_rejects_invalid_condition_value_type(client, compliance_user):
    headers = auth_header(client, "compliance@test.local")

    response = client.post(
        "/api/rules",
        json=_payload({"amount_gt": "100000"}),
        headers=headers,
    )

    assert response.status_code == 422


def test_rule_api_accepts_supported_condition_combination(client, compliance_user):
    headers = auth_header(client, "compliance@test.local")

    response = client.post(
        "/api/rules",
        json=_payload(
            {
                "status": "ALLOWED",
                "product_type": "OPEN_FUND",
                "amount_gt": 10,
                "amount_gte": 20,
            }
        ),
        headers=headers,
    )

    assert response.status_code == 201
