import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "BusinessHub" in data["message"]


def test_health_check_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "environment" in data
    assert "timestamp" in data


def test_404_handling():
    response = client.get("/api/v1/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert "errors" in data


def test_validation_error_handling():
    response = client.get("/api/v1/health", params={"invalid": "param"})
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_cors_preflight_and_origins():
    # Allowed origins
    for origin in [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]:
        response = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == origin
        assert response.headers.get("access-control-allow-credentials") == "true"

    # Disallowed origin
    bad_response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://evil-untrusted-site.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert bad_response.headers.get("access-control-allow-origin") != "http://evil-untrusted-site.com"
