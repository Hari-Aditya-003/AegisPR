from fastapi.testclient import TestClient

from app import main


def test_health_remains_available_for_container_orchestration(monkeypatch) -> None:
    monkeypatch.setattr(main, "token", "secret")
    response = TestClient(main.app).get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_rank_requires_the_configured_bearer_token(monkeypatch) -> None:
    monkeypatch.setattr(main, "token", "secret")
    response = TestClient(main.app).post(
        "/rank",
        json={"query": "coupon", "documents": [], "limit": 1},
    )
    assert response.status_code == 401
