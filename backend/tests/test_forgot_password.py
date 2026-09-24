import pytest
import asyncio
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.config import settings
from app.core.database import get_db_session, async_session_factory
from app.modules.authentication.repository import InMemoryUserRepository
from app.modules.authentication.security import verify_password
from app.modules.authentication.models import User, PasswordResetToken


API = "/api/v1/auth"
FORGOT_ENDPOINT = f"{API}/forgot-password"
RESET_ENDPOINT = f"{API}/reset-password"


async def _clear_pg():
    engine = create_async_engine(settings.database_url, echo=False, pool_size=1, pool_pre_ping=True)
    try:
        async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            await session.execute(delete(PasswordResetToken))
            await session.execute(delete(User))
            await session.commit()
    finally:
        await engine.dispose()


async def _committing_get_db_session():
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
def _clear_and_override():
    InMemoryUserRepository.clear()
    asyncio.run(_clear_pg())
    app.dependency_overrides[get_db_session] = _committing_get_db_session
    yield
    app.dependency_overrides.pop(get_db_session, None)
    InMemoryUserRepository.clear()
    asyncio.run(_clear_pg())


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _register_user(client: TestClient, email: str = "user@test.com", password: str = "TestPass123"):
    r = client.post(f"{API}/register", json={
        "email": email, "full_name": "Test User",
        "password": password, "password_confirmation": password,
    })
    assert r.status_code == 201
    return r.json()


def _create_token_directly(user_id: str, raw_token: str, expires_minutes: int = 60):
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    asyncio.run(_create_token_in_db(user_id, token_hash, expires_minutes))


async def _create_token_in_db(user_id: str, token_hash: str, expires_minutes: int = 60):
    engine = create_async_engine(settings.database_url, echo=False, pool_size=1, pool_pre_ping=True)
    try:
        async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
            token = PasswordResetToken(
                user_id=user_id, token_hash=token_hash, expires_at=expires_at,
            )
            session.add(token)
            await session.commit()
    finally:
        await engine.dispose()


def _get_token_hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


# ─── Forgot Password ────────────────────────────────────────────────

def test_forgot_password_existing_email(client: TestClient):
    _register_user(client, email="exists@test.com")
    r = client.post(FORGOT_ENDPOINT, json={"email": "exists@test.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "instruksi reset" in body["message"]


def test_forgot_password_unknown_email(client: TestClient):
    r = client.post(FORGOT_ENDPOINT, json={"email": "unknown@test.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "instruksi reset" in body["message"]


def test_forgot_password_inactive_user(client: TestClient):
    user = _register_user(client, email="inactive@test.com")
    asyncio.run(_deactivate_user(user["id"]))
    r = client.post(FORGOT_ENDPOINT, json={"email": "inactive@test.com"})
    assert r.status_code == 200
    assert "instruksi reset" in r.json()["message"]


async def _deactivate_user(user_id: str):
    engine = create_async_engine(settings.database_url, echo=False, pool_size=1, pool_pre_ping=True)
    try:
        async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            await session.execute(text("UPDATE users SET is_active = false WHERE id = :uid"), {"uid": user_id})
            await session.commit()
    finally:
        await engine.dispose()


def test_forgot_password_invalid_email(client: TestClient):
    r = client.post(FORGOT_ENDPOINT, json={"email": "not-an-email"})
    assert r.status_code == 422


# ─── Reset Password ─────────────────────────────────────────────────

def test_reset_password_success(client: TestClient):
    user = _register_user(client, email="reset@test.com")
    raw_token = "test_reset_token_abc123"
    _create_token_directly(user["id"], raw_token)
    r = client.post(RESET_ENDPOINT, json={
        "token": raw_token, "new_password": "NewPass1234", "password_confirmation": "NewPass1234",
    })
    assert r.status_code == 200
    assert "berhasil" in r.json()["message"].lower()


def test_reset_old_password_rejected(client: TestClient):
    user = _register_user(client, email="oldpwd@test.com", password="OldPass123")
    raw_token = "test_old_pwd_token"
    _create_token_directly(user["id"], raw_token)
    client.post(RESET_ENDPOINT, json={
        "token": raw_token, "new_password": "NewPass1234", "password_confirmation": "NewPass1234",
    })
    r = client.post(f"{API}/login", json={"email": "oldpwd@test.com", "password": "OldPass123"})
    assert r.status_code == 401


def test_reset_new_password_accepted(client: TestClient):
    user = _register_user(client, email="newpwd@test.com", password="OldPass123")
    raw_token = "test_new_pwd_token"
    _create_token_directly(user["id"], raw_token)
    client.post(RESET_ENDPOINT, json={
        "token": raw_token, "new_password": "NewPass1234", "password_confirmation": "NewPass1234",
    })
    r = client.post(f"{API}/login", json={"email": "newpwd@test.com", "password": "NewPass1234"})
    assert r.status_code == 200


def test_reset_invalid_token(client: TestClient):
    r = client.post(RESET_ENDPOINT, json={
        "token": "completely-invalid-token", "new_password": "NewPass1234", "password_confirmation": "NewPass1234",
    })
    assert r.status_code == 400


def test_reset_expired_token(client: TestClient):
    user = _register_user(client, email="expired@test.com")
    raw_token = "test_expired_token"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    asyncio.run(_create_token_in_db(user["id"], token_hash, expires_minutes=-60))
    r = client.post(RESET_ENDPOINT, json={
        "token": raw_token, "new_password": "NewPass1234", "password_confirmation": "NewPass1234",
    })
    assert r.status_code == 400


def test_reset_used_token(client: TestClient):
    user = _register_user(client, email="used@test.com")
    raw_token = "test_used_token"
    _create_token_directly(user["id"], raw_token)
    client.post(RESET_ENDPOINT, json={
        "token": raw_token, "new_password": "NewPass1234", "password_confirmation": "NewPass1234",
    })
    r = client.post(RESET_ENDPOINT, json={
        "token": raw_token, "new_password": "NewPass1234", "password_confirmation": "NewPass1234",
    })
    assert r.status_code == 400


def test_reset_password_mismatch(client: TestClient):
    user = _register_user(client, email="mismatch@test.com")
    raw_token = "test_mismatch_token"
    _create_token_directly(user["id"], raw_token)
    r = client.post(RESET_ENDPOINT, json={
        "token": raw_token, "new_password": "PasswordA123", "password_confirmation": "PasswordB123",
    })
    assert r.status_code == 400


def test_reset_password_too_short(client: TestClient):
    user = _register_user(client, email="short@test.com")
    raw_token = "test_short_token"
    _create_token_directly(user["id"], raw_token)
    r = client.post(RESET_ENDPOINT, json={
        "token": raw_token, "new_password": "short", "password_confirmation": "short",
    })
    assert r.status_code in (400, 422)


def test_old_tokens_invalidated_by_new_forgot(client: TestClient):
    user = _register_user(client, email="invalidate@test.com")
    raw_token1 = "old_token_1"
    _create_token_directly(user["id"], raw_token1)
    client.post(FORGOT_ENDPOINT, json={"email": "invalidate@test.com"})
    raw_token2 = "old_token_2"
    _create_token_directly(user["id"], raw_token2)
    r1 = client.post(RESET_ENDPOINT, json={
        "token": raw_token1, "new_password": "NewPass1234", "password_confirmation": "NewPass1234",
    })
    r2 = client.post(RESET_ENDPOINT, json={
        "token": raw_token2, "new_password": "NewPass1234", "password_confirmation": "NewPass1234",
    })
    assert r1.status_code == 400


# ─── Security ───────────────────────────────────────────────────────

def test_token_never_persisted_raw(client: TestClient):
    user = _register_user(client, email="security@test.com")
    raw_token = "test_raw_token_check"
    _create_token_directly(user["id"], raw_token)
    row = asyncio.run(_verify_token_hash(user["id"], raw_token))
    assert row is not None
    assert row[0] != raw_token
    assert row[0] == _get_token_hash(raw_token)


async def _verify_token_hash(user_id: str, raw_token: str):
    engine = create_async_engine(settings.database_url, echo=False, pool_size=1, pool_pre_ping=True)
    try:
        async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            result = await session.execute(
                text("SELECT token_hash FROM password_reset_tokens WHERE user_id = :uid"), {"uid": user_id}
            )
            return result.fetchone()
    finally:
        await engine.dispose()


def test_generic_response_no_enumeration(client: TestClient):
    r1 = client.post(FORGOT_ENDPOINT, json={"email": "exists@test.com"})
    r2 = client.post(FORGOT_ENDPOINT, json={"email": "nonexistent@test.com"})
    assert r1.json()["message"] == r2.json()["message"]


# ─── Regression ─────────────────────────────────────────────────────

def test_register_still_works(client: TestClient):
    r = client.post(f"{API}/register", json={
        "email": "reg@test.com", "full_name": "Reg User",
        "password": "Password123", "password_confirmation": "Password123",
    })
    assert r.status_code == 201


def test_login_still_works(client: TestClient):
    _register_user(client, email="login@test.com", password="Password123")
    r = client.post(f"{API}/login", json={"email": "login@test.com", "password": "Password123"})
    assert r.status_code == 200


def test_me_still_works(client: TestClient):
    _register_user(client, email="me@test.com", password="Password123")
    r = client.get(f"{API}/me", headers={"Authorization": f"Bearer {client.post(f'{API}/login', json={'email': 'me@test.com', 'password': 'Password123'}).json()['access_token']}"})
    assert r.status_code == 200
