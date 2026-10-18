from fastapi.testclient import TestClient

from app import main


def test_production_api_requires_a_private_access_code(monkeypatch):
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "api_access_token", "private-test-access-code")
    with TestClient(main.app) as client:
        for headers in ({}, {"Authorization": "Bearer wrong"}):
            assert client.get("/api/verifications", headers=headers).status_code == 401
        assert client.get("/api/verifications", headers={"Authorization": "Bearer private-test-access-code"}).status_code == 200
        assert client.get("/health").status_code == 200


def test_production_without_access_configuration_fails_closed(monkeypatch):
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "api_access_token", None)
    with TestClient(main.app) as client:
        assert client.post("/api/verifications", json={"pull_request_url": "https://github.com/a/b/pull/1"}).status_code == 503


def test_cors_preflight_still_works_without_credentials(monkeypatch):
    monkeypatch.setattr(main.settings, "app_env", "production")
    monkeypatch.setattr(main.settings, "api_access_token", "private-test-access-code")
    with TestClient(main.app) as client:
        response = client.options("/api/verifications", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization"})
        assert response.status_code == 200


def test_budget_estimate_is_private_and_explicit(monkeypatch):
    monkeypatch.setattr(main.settings, "api_access_token", "private-test-access-code")
    with TestClient(main.app) as client:
        assert client.get("/api/budget").status_code == 401
        response = client.get("/api/budget", headers={"Authorization": "Bearer private-test-access-code"})
        assert response.status_code == 200
        assert response.json()["limit_usd"] == 20
        assert "not provider balance" in response.json()["note"]
