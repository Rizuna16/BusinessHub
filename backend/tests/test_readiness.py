import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_readiness_returns_200_when_db_healthy():
    """Readiness probe returns 200 OK when PostgreSQL is reachable."""
    with patch("app.modules.health.router.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_conn

        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "timestamp" in data


def test_readiness_returns_503_when_db_unavailable():
    """Readiness probe returns 503 Service Unavailable when PostgreSQL is unreachable."""
    with patch("app.modules.health.router.engine") as mock_engine:
        mock_engine.connect.side_effect = Exception("Connection refused")

        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"


def test_readiness_does_not_expose_secrets():
    """Readiness response must not contain database credentials or internal paths."""
    with patch("app.modules.health.router.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_conn

        response = client.get("/api/v1/health/ready")
        body = response.text
        assert "postgres" not in body.lower()
        assert "DATABASE_URL" not in body
        assert "password" not in body.lower()
        assert "secret" not in body.lower()


def test_readiness_does_not_mutate_data():
    """Readiness probe must not modify any application data."""
    with patch("app.modules.health.router.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_conn

        response = client.get("/api/v1/health/ready")
        assert response.status_code in (200, 503)

        call_args = mock_conn.execute.call_args
        assert call_args is not None
        query_str = str(call_args)
        assert "INSERT" not in query_str.upper()
        assert "UPDATE" not in query_str.upper()
        assert "DELETE" not in query_str.upper()
        assert "CREATE" not in query_str.upper()
