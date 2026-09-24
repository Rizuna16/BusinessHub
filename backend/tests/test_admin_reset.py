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


API = "/api/v1/auth"
ADMIN_ENDPOINT = f"{API}/admin/reset-password"


async def _clear_pg_users():
    engine = create_async_engine(settings.database_url, echo=False, pool_size=1, pool_pre_ping=True)
    try:
        async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
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


def _register_user(client: TestClient, email: str = "target@test.com", password: str = "TargetPass123") -> dict:
    """Register a user and return response body."""
    r = client.post(f"{API}/register", json={
        "email": email,
        "full_name": "Target User",
        "password": password,
        "password_confirmation": password,
    })
    assert r.status_code == 201, f"Register failed: {r.status_code} {r.text}"
    return r.json()


def _register_superadmin(client: TestClient) -> dict:
    """Register a user and promote to SUPER_ADMIN via direct DB update. Returns user body."""
    user = _register_user(client, email="admin@test.com", password="AdminPass123")
    # Promote to SUPER_ADMIN via direct DB update (test setup)
    asyncio.run(_promote_to_superadmin(user["id"]))
    return user


async def _promote_to_superadmin(user_id: str):
    engine = create_async_engine(settings.database_url, echo=False, pool_size=1, pool_pre_ping=True)
    try:
        async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            await session.execute(
                text("UPDATE users SET platform_role = 'SUPER_ADMIN' WHERE id = :uid"),
                {"uid": user_id}
            )
            await session.commit()
    finally:
        await engine.dispose()


def _login(client: TestClient, email: str, password: str) -> str:
    """Login and return access_token."""
    r = client.post(f"{API}/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["access_token"]


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─── Authorization ──────────────────────────────────────────────────

def test_unauthenticated_rejected(client: TestClient):
    target = _register_user(client, email="a@test.com")
    r = client.post(ADMIN_ENDPOINT, json={
        "target_user_id": target["id"],
        "new_password": "NewPass123",
        "password_confirmation": "NewPass123",
    })
    assert r.status_code == 401


def test_regular_user_rejected(client: TestClient):
    user = _register_user(client, email="regular@test.com")
    token = _login(client, "regular@test.com", "TargetPass123")
    r = client.post(ADMIN_ENDPOINT, json={
        "target_user_id": user["id"],
        "new_password": "NewPass123",
        "password_confirmation": "NewPass123",
    }, headers=_auth_header(token))
    assert r.status_code == 403


def test_super_admin_allowed(client: TestClient):
    admin = _register_superadmin(client)
    target = _register_user(client, email="target@test.com")
    admin_token = _login(client, "admin@test.com", "AdminPass123")
    r = client.post(ADMIN_ENDPOINT, json={
        "target_user_id": target["id"],
        "new_password": "ResetPass123",
        "password_confirmation": "ResetPass123",
    }, headers=_auth_header(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["target_user_id"] == target["id"]


# ─── Target ─────────────────────────────────────────────────────────

def test_unknown_user_404(client: TestClient):
    admin = _register_superadmin(client)
    token = _login(client, "admin@test.com", "AdminPass123")
    r = client.post(ADMIN_ENDPOINT, json={
        "target_user_id": "00000000-0000-0000-0000-000000000000",
        "new_password": "NewPass123",
        "password_confirmation": "NewPass123",
    }, headers=_auth_header(token))
    assert r.status_code == 404


def test_inactive_user_can_be_reset(client: TestClient):
    admin = _register_superadmin(client)
    target = _register_user(client, email="inactive@test.com")
    # Deactivate target
    asyncio.run(_set_user_active(target["id"], False))
    admin_token = _login(client, "admin@test.com", "AdminPass123")
    r = client.post(ADMIN_ENDPOINT, json={
        "target_user_id": target["id"],
        "new_password": "NewPass123",
        "password_confirmation": "NewPass123",
    }, headers=_auth_header(admin_token))
    assert r.status_code == 200


async def _set_user_active(user_id: str, active: bool):
    engine = create_async_engine(settings.database_url, echo=False, pool_size=1, pool_pre_ping=True)
    try:
        async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
            await session.execute(
                text("UPDATE users SET is_active = :active WHERE id = :uid"),
                {"active": active, "uid": user_id}
            )
            await session.commit()
    finally:
        await engine.dispose()


# ─── Password ───────────────────────────────────────────────────────

def test_valid_password_success(client: TestClient):
    admin = _register_superadmin(client)
    target = _register_user(client, email="pwd@test.com")
    token = _login(client, "admin@test.com", "AdminPass123")
    r = client.post(ADMIN_ENDPOINT, json={
        "target_user_id": target["id"],
        "new_password": "ValidPass123",
        "password_confirmation": "ValidPass123",
    }, headers=_auth_header(token))
    assert r.status_code == 200


def test_password_too_short_rejected(client: TestClient):
    admin = _register_superadmin(client)
    target = _register_user(client, email="short@test.com")
    token = _login(client, "admin@test.com", "AdminPass123")
    r = client.post(ADMIN_ENDPOINT, json={
        "target_user_id": target["id"],
        "new_password": "short",
        "password_confirmation": "short",
    }, headers=_auth_header(token))
    assert r.status_code in (400, 422)


def test_password_mismatch_rejected(client: TestClient):
    admin = _register_superadmin(client)
    target = _register_user(client, email="mismatch@test.com")
    token = _login(client, "admin@test.com", "AdminPass123")
    r = client.post(ADMIN_ENDPOINT, json={
        "target_user_id": target["id"],
        "new_password": "PasswordA123",
        "password_confirmation": "PasswordB123",
    }, headers=_auth_header(token))
    assert r.status_code == 400
    body = r.json()
    msg = body.get("message", body.get("detail", ""))
    assert "tidak cocok" in msg


# ─── Post-Reset Authentication ──────────────────────────────────────

def test_new_password_enables_login(client: TestClient):
    admin = _register_superadmin(client)
    target = _register_user(client, email="login_new@test.com", password="OldPass123")
    token = _login(client, "admin@test.com", "AdminPass123")
    r = client.post(ADMIN_ENDPOINT, json={
        "target_user_id": target["id"],
        "new_password": "FreshPass123",
        "password_confirmation": "FreshPass123",
    }, headers=_auth_header(token))
    assert r.status_code == 200
    # Login with new password
    r2 = client.post(f"{API}/login", json={"email": "login_new@test.com", "password": "FreshPass123"})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_old_password_rejected_after_reset(client: TestClient):
    admin = _register_superadmin(client)
    target = _register_user(client, email="old_pwd@test.com", password="OldPass123")
    token = _login(client, "admin@test.com", "AdminPass123")
    client.post(ADMIN_ENDPOINT, json={
        "target_user_id": target["id"],
        "new_password": "FreshPass123",
        "password_confirmation": "FreshPass123",
    }, headers=_auth_header(token))
    # Old password should fail
    r = client.post(f"{API}/login", json={"email": "old_pwd@test.com", "password": "OldPass123"})
    assert r.status_code == 401


def test_me_works_after_new_login(client: TestClient):
    admin = _register_superadmin(client)
    target = _register_user(client, email="me_after@test.com", password="OldPass123")
    token = _login(client, "admin@test.com", "AdminPass123")
    client.post(ADMIN_ENDPOINT, json={
        "target_user_id": target["id"],
        "new_password": "NewPass123",
        "password_confirmation": "NewPass123",
    }, headers=_auth_header(token))
    new_token = _login(client, "me_after@test.com", "NewPass123")
    r = client.get(f"{API}/me", headers=_auth_header(new_token))
    assert r.status_code == 200
    assert r.json()["email"] == "me_after@test.com"


# ─── Security ───────────────────────────────────────────────────────

def test_password_absent_from_response(client: TestClient):
    admin = _register_superadmin(client)
    target = _register_user(client, email="sec@test.com")
    token = _login(client, "admin@test.com", "AdminPass123")
    r = client.post(ADMIN_ENDPOINT, json={
        "target_user_id": target["id"],
        "new_password": "SecurePass123",
        "password_confirmation": "SecurePass123",
    }, headers=_auth_header(token))
    body = r.json()
    body_str = str(body)
    assert "SecurePass123" not in body_str
    assert "password_hash" not in body_str
    assert "password" not in body_str


# ─── Regression ─────────────────────────────────────────────────────

def test_register_still_works(client: TestClient):
    r = client.post(f"{API}/register", json={
        "email": "reg@test.com",
        "full_name": "Reg User",
        "password": "Password123",
        "password_confirmation": "Password123",
    })
    assert r.status_code == 201


def test_login_still_works(client: TestClient):
    _register_user(client, email="login@test.com", password="Password123")
    r = client.post(f"{API}/login", json={"email": "login@test.com", "password": "Password123"})
    assert r.status_code == 200


def test_logout_still_works(client: TestClient):
    _register_user(client, email="logout@test.com", password="Password123")
    token = _login(client, "logout@test.com", "Password123")
    r = client.post(f"{API}/logout", headers=_auth_header(token))
    assert r.status_code == 200


def test_me_still_works(client: TestClient):
    _register_user(client, email="me@test.com", password="Password123")
    token = _login(client, "me@test.com", "Password123")
    r = client.get(f"{API}/me", headers=_auth_header(token))
    assert r.status_code == 200
    assert r.json()["email"] == "me@test.com"
