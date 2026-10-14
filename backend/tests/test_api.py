from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from app import main as main_module
from app.main import app
from app.schemas.verification import VerificationRun


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
    assert "public GitHub pull request" in response.json()["detail"]


def test_create_verification_accepts_json_body(monkeypatch) -> None:
    run = VerificationRun(pull_request_url="https://github.com/acme/store/pull/42")
    create = MagicMock(return_value=run)
    verify = AsyncMock()
    monkeypatch.setattr(main_module.orchestrator, "create", create)
    monkeypatch.setattr(main_module.orchestrator, "verify", verify)

    response = client.post(
        "/api/verifications",
        json={"pull_request_url": "https://github.com/acme/store/pull/42"},
    )

    assert response.status_code == 202
    assert response.json()["id"] == run.id
    create.assert_called_once()
    verify.assert_awaited_once()


def test_repair_unknown_verification_returns_not_found() -> None:
    response = client.post("/api/verifications/not-a-run/repair", json={})
    assert response.status_code == 404

