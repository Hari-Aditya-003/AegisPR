from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_is_explicit_about_optional_dependencies() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"ok", "degraded"}
    assert "nebius" in payload["checks"]
    assert "gpu_worker" in payload["checks"]


def test_create_verification_rejects_invalid_pull_request_url() -> None:
    response = client.post("/api/verifications", json={"pull_request_url": "https://example.com/pr/1"})
    assert response.status_code == 422

