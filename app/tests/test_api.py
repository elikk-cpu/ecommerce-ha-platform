from decimal import Decimal

from fastapi.testclient import TestClient

from src import main

client = TestClient(main.app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["service"] == "ecommerce-api"
    assert response.json()["status"] == "running"


def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_when_all_dependencies_are_healthy(monkeypatch):
    monkeypatch.setattr(main, "check_postgresql", lambda: True)
    monkeypatch.setattr(main, "check_redis", lambda: True)
    monkeypatch.setattr(main, "check_rabbitmq", lambda: True)
    monkeypatch.setattr(main, "check_minio", lambda: True)

    response = client.get("/ready")

    assert response.status_code == 200

    payload = response.json()

    assert payload["status"] == "ready"
    assert all(payload["checks"].values())


def test_ready_when_dependency_is_down(monkeypatch):
    monkeypatch.setattr(main, "check_postgresql", lambda: True)
    monkeypatch.setattr(main, "check_redis", lambda: True)
    monkeypatch.setattr(main, "check_rabbitmq", lambda: True)
    monkeypatch.setattr(main, "check_minio", lambda: False)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"
    assert response.json()["checks"]["minio"] is False


def test_checkout_success(monkeypatch):
    def fake_checkout(customer: str, amount: Decimal):
        return {
            "order_id": "test-order",
            "customer": customer,
            "amount": f"{amount:.2f}",
            "status": "created",
            "created_at": "2026-09-15T00:00:00+00:00",
        }

    monkeypatch.setattr(main, "process_checkout", fake_checkout)

    response = client.post(
        "/checkout",
        json={
            "customer": "ci-test",
            "amount": 10.50,
        },
    )

    assert response.status_code == 201
    assert response.json()["order_id"] == "test-order"
    assert response.json()["status"] == "created"


def test_checkout_dependency_failure(monkeypatch):
    def failed_checkout(*args, **kwargs):
        raise RuntimeError("dependency unavailable")

    monkeypatch.setattr(main, "process_checkout", failed_checkout)

    response = client.post(
        "/checkout",
        json={
            "customer": "ci-test",
            "amount": 10.50,
        },
    )

    assert response.status_code == 503
