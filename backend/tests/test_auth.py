import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.config import settings
from app.core.database import get_db_session, async_session_factory
from app.modules.authentication.repository import InMemoryUserRepository, user_repository
from app.modules.authentication.security import hash_password, verify_password, create_access_token
from app.modules.authentication.models import User


async def _clear_pg_users():
    """Delete all users from PostgreSQL using a fresh engine (avoids event loop conflicts)."""
    engine = create_async_engine(settings.database_url, echo=False, pool_size=1, pool_pre_ping=True)
    try:
        async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            await session.execute(delete(User))
            await session.commit()
    finally:
        await engine.dispose()


async def _committing_get_db_session():
    """Test override: auto-commit session so data persists between HTTP requests."""
    async with async_session_factory() as session:
        try:
            yield session
            if session.is_active:
                await session.commit()
        except Exception:
            if session.is_active:
                await session.rollback()
            raise


@pytest.fixture(autouse=True)
def clear_user_repo():
    InMemoryUserRepository.clear()
    asyncio.run(_clear_pg_users())
    app.dependency_overrides[get_db_session] = _committing_get_db_session
    yield
    app.dependency_overrides.pop(get_db_session, None)
    InMemoryUserRepository.clear()
    asyncio.run(_clear_pg_users())


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# 1. register valid user
def test_register_valid_user(client: TestClient):
    payload = {
        "email": "user@example.com",
        "full_name": "Test User",
        "password": "Password123",
        "password_confirmation": "Password123",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["full_name"] == "Test User"
    assert "id" in data
    assert data["is_active"] is True
    # 17. password/hash never returned
    assert "password" not in data
    assert "password_hash" not in data


# 2. register invalid email
def test_register_invalid_email(client: TestClient):
    payload = {
        "email": "invalid-email-format",
        "full_name": "Test User",
        "password": "Password123",
        "password_confirmation": "Password123",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


# 3. register password terlalu pendek
def test_register_password_too_short(client: TestClient):
    payload = {
        "email": "user@example.com",
        "full_name": "Test User",
        "password": "123",
        "password_confirmation": "123",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


# 4. register password confirmation mismatch
def test_register_password_mismatch(client: TestClient):
    payload = {
        "email": "user@example.com",
        "full_name": "Test User",
        "password": "Password123",
        "password_confirmation": "Password999",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["message"] == "Password confirmation does not match password."


# 5. duplicate email rejected
def test_register_duplicate_email(client: TestClient):
    payload = {
        "email": "user@example.com",
        "full_name": "Test User",
        "password": "Password123",
        "password_confirmation": "Password123",
    }
    client.post("/api/v1/auth/register", json=payload)
    
    # Try registering again with same email (case insensitive check)
    payload["email"] = "USER@example.com"
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert response.json()["message"] == "Email is already registered."


# 6. password stored as hash & 7. correct password verifies & 8. wrong password rejected
def test_password_security():
    plain = "MySecretPass123"
    hashed = hash_password(plain)
    assert plain != hashed
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPass123", hashed) is False


# 9. login valid credentials
def test_login_valid_credentials(client: TestClient):
    reg_payload = {
        "email": "user@example.com",
        "full_name": "Test User",
        "password": "Password123",
        "password_confirmation": "Password123",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "USER@example.com",
        "password": "Password123",
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# 10. login invalid credentials (generic error)
def test_login_invalid_credentials(client: TestClient):
    reg_payload = {
        "email": "user@example.com",
        "full_name": "Test User",
        "password": "Password123",
        "password_confirmation": "Password123",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Wrong email
    res1 = client.post("/api/v1/auth/login", json={"email": "nonexistent@example.com", "password": "Password123"})
    assert res1.status_code == 401
    assert res1.json()["message"] == "Invalid email or password."

    # Wrong password
    res2 = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "WrongPassword"})
    assert res2.status_code == 401
    assert res2.json()["message"] == "Invalid email or password."


# 11. inactive user rejected
def test_login_inactive_user(client: TestClient):
    reg_payload = {
        "email": "user@example.com",
        "full_name": "Test User",
        "password": "Password123",
        "password_confirmation": "Password123",
    }
    res = client.post("/api/v1/auth/register", json=reg_payload)
    user_id = res.json()["id"]

    async def _deactivate_user(uid):
        engine = create_async_engine(settings.database_url, echo=False, pool_size=1, pool_pre_ping=True)
        try:
            async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
                await session.execute(text("UPDATE users SET is_active = false WHERE id = :id"), {"id": uid})
                await session.commit()
        finally:
            await engine.dispose()
    asyncio.run(_deactivate_user(user_id))

    login_res = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "Password123"})
    assert login_res.status_code == 403
    assert login_res.json()["message"] == "User account is inactive."


# 12. /auth/me without credential → 401
def test_me_without_credential(client: TestClient):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


# 13. /auth/me invalid credential → 401
def test_me_invalid_credential(client: TestClient):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token_str"})
    assert response.status_code == 401


# 14. /auth/me valid credential → 200 & 19. protected endpoint behavior
def test_me_valid_credential(client: TestClient):
    reg_payload = {
        "email": "user@example.com",
        "full_name": "Test User",
        "password": "Password123",
        "password_confirmation": "Password123",
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "Password123"})
    token = login_res.json()["access_token"]

    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["email"] == "user@example.com"
    assert "password" not in data
    assert "password_hash" not in data


# 15. expired token rejected
def test_expired_token(client: TestClient):
    expired_token = create_access_token({"sub": "user_id_123"}, expires_delta=timedelta(seconds=-10))
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401


# 16. malformed token rejected
def test_malformed_token(client: TestClient):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.validjwt"})
    assert response.status_code == 401


# 18. logout behavior
def test_logout(client: TestClient):
    reg_payload = {
        "email": "user@example.com",
        "full_name": "Test User",
        "password": "Password123",
        "password_confirmation": "Password123",
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    login_res = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "Password123"})
    token = login_res.json()["access_token"]

    logout_res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_res.status_code == 200
    assert "Successfully logged out" in logout_res.json()["message"]
