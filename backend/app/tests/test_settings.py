from app.tests.conftest import auth_header


def test_settings_api_exposes_only_runtime_controls_with_consumers(
    client, admin_user
):
    headers = auth_header(client, "admin@test.local")

    response = client.get("/api/settings", headers=headers)

    assert response.status_code == 200
    keys = {
        setting["key"]
        for section in response.json()["sections"]
        for setting in section["settings"]
    }
    assert keys == {"data_retention_days"}
