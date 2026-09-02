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