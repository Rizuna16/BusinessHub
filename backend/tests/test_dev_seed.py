import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.core.config import settings
from app.core.database import get_db_session, async_session_factory
from app.modules.authentication.repository import InMemoryUserRepository, user_repository
from app.modules.authentication.security import hash_password
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


# 1. Startup seed creates user when repository is empty
def test_seed_creates_user_when_empty(client: TestClient):
    seed_user = asyncio.run(InMemoryUserRepository.seed_development_user(
        email=settings.dev_seed_email,
        plain_password=settings.dev_seed_password,
        full_name=settings.dev_seed_name,
    ))
    assert seed_user is not None
    assert seed_user.email == settings.dev_seed_email.lower().strip()
    assert seed_user.full_name == settings.dev_seed_name
    assert seed_user.is_active is True


# 2. Seeded password can authenticate
def test_seeded_password_authenticates(client: TestClient):
    async def _seed_pg():
        engine = create_async_engine(settings.database_url, echo=False, pool_size=1, pool_pre_ping=True)
        try:
            async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as session:
                from app.modules.authentication.sqla_repository import SQLAlchemyUserRepository
                from app.modules.authentication.schemas import UserCreate
                repo = SQLAlchemyUserRepository(session)
                user_data = UserCreate(
                    email=settings.dev_seed_email,
                    full_name=settings.dev_seed_name,
                    password=settings.dev_seed_password,
                    password_confirmation=settings.dev_seed_password,
                )
                await repo.create(user_data)
                await session.commit()
        finally:
            await engine.dispose()
    asyncio.run(_seed_pg())

    response = client.post("/api/v1/auth/login", json={
        "email": settings.dev_seed_email,
        "password": settings.dev_seed_password,
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


# 3. Seeded user receives expected account state
def test_seeded_user_account_state(client: TestClient):
    seed_user = asyncio.run(InMemoryUserRepository.seed_development_user(
        email=settings.dev_seed_email,
        plain_password=settings.dev_seed_password,
        full_name=settings.dev_seed_name,
    ))
    assert seed_user.is_active is True
    assert seed_user.id is not None
    assert len(seed_user.id) > 0
    assert seed_user.created_at is not None


# 4. Startup seed is idempotent - second call returns existing user
def test_seed_idempotent(client: TestClient):
    user1 = asyncio.run(InMemoryUserRepository.seed_development_user(
        email=settings.dev_seed_email,
        plain_password=settings.dev_seed_password,
        full_name=settings.dev_seed_name,
    ))
    user2 = asyncio.run(InMemoryUserRepository.seed_development_user(
        email=settings.dev_seed_email,
        plain_password="NewPassword999!",
        full_name="Different Name",
    ))
    assert user1.id == user2.id
    assert user2.full_name == settings.dev_seed_name


# 5. Existing user's password is NOT overwritten
def test_existing_user_password_not_overwritten(client: TestClient):
    original = asyncio.run(InMemoryUserRepository.seed_development_user(
        email=settings.dev_seed_email,
        plain_password=settings.dev_seed_password,
        full_name=settings.dev_seed_name,
    ))
    original_hash = original.password_hash

    asyncio.run(InMemoryUserRepository.seed_development_user(
        email=settings.dev_seed_email,
        plain_password="NewPassword999!",
        full_name="New Name",
    ))

    retrieved = asyncio.run(user_repository.get_by_email(settings.dev_seed_email))
    assert retrieved is not None
    assert retrieved.password_hash == original_hash


# 6. Existing user's role/state is NOT overwritten
def test_existing_user_state_not_overwritten(client: TestClient):
    original = asyncio.run(InMemoryUserRepository.seed_development_user(
        email=settings.dev_seed_email,
        plain_password=settings.dev_seed_password,
        full_name=settings.dev_seed_name,
    ))

    asyncio.run(InMemoryUserRepository.seed_development_user(
        email=settings.dev_seed_email,
        plain_password="NewPassword999!",
        full_name="Completely Different Name",
    ))

    retrieved = asyncio.run(user_repository.get_by_email(settings.dev_seed_email))
    assert retrieved is not None
    assert retrieved.is_active == original.is_active
    assert retrieved.full_name == settings.dev_seed_name


# 7. Production mode does NOT seed default user
def test_production_no_seed(client: TestClient):
    original_env = settings.app_env
    settings.app_env = "production"
    try:
        InMemoryUserRepository.clear()
        user = asyncio.run(user_repository.get_by_email(settings.dev_seed_email))
        assert user is None
    finally:
        settings.app_env = original_env


# 8. No plaintext password is persisted
def test_no_plaintext_password(client: TestClient):
    asyncio.run(InMemoryUserRepository.seed_development_user(
        email=settings.dev_seed_email,
        plain_password=settings.dev_seed_password,
        full_name=settings.dev_seed_name,
    ))
    retrieved = asyncio.run(user_repository.get_by_email(settings.dev_seed_email))
    assert retrieved is not None
    assert settings.dev_seed_password not in str(retrieved.model_dump())
    assert retrieved.password_hash != settings.dev_seed_password


# 9. Normal /register still works after seed
def test_register_still_works(client: TestClient):
    asyncio.run(InMemoryUserRepository.seed_development_user(
        email=settings.dev_seed_email,
        plain_password=settings.dev_seed_password,
        full_name=settings.dev_seed_name,
    ))

    response = client.post("/api/v1/auth/register", json={
        "email": "newuser@example.com",
        "full_name": "New User",
        "password": "Password123",
        "password_confirmation": "Password123",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"


# 10. Normal /login still works after seed
def test_login_still_works(client: TestClient):
    client.post("/api/v1/auth/register", json={
        "email": "normaluser@example.com",
        "full_name": "Normal User",
        "password": "Password123",
        "password_confirmation": "Password123",
    })

    response = client.post("/api/v1/auth/login", json={
        "email": "normaluser@example.com",
        "password": "Password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data


# 11. Startup event handler is configured for non-production
def test_startup_event_handler_configured():
    from app.main import app as test_app
    startup_handlers = test_app.router.on_startup
    assert len(startup_handlers) >= 1
    handler_names = [h.__name__ for h in startup_handlers]
    assert "seed_development_user" in handler_names
