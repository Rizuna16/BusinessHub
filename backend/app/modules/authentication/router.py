from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.authentication.service import auth_service, AuthenticationService
from app.modules.authentication.schemas import (
    UserCreate,
    UserResponse,
    UserInDB,
    LoginRequest,
    TokenResponse,
    TokenPayload,
    AdminResetPasswordRequest,
)
from app.core.config import settings
from app.shared.utils import create_api_response

router = APIRouter(prefix=settings.api_v1_prefix + "/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.api_v1_prefix + "/auth/login")


async def get_auth_service(session: AsyncSession = Depends(get_db_session)) -> AuthenticationService:
    """Request-scoped AuthenticationService backed by PostgreSQL via SQLAlchemyUserRepository."""
    from app.core.container import RepositoryContainer
    container = RepositoryContainer(session)
    return AuthenticationService(
        repository=container.user,
        session=session,
    )


# Dependency to get the current authenticated user from the token
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> UserResponse:
    """FastAPI dependency that returns the authenticated user or raises 401."""
    payload = auth_service.security.decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await auth_service.get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    user_data: UserCreate,
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> UserResponse:
    """Register a new user account."""
    registered_user = await auth_service.register(user_data)
    return registered_user


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
) -> TokenResponse:
    """Login and receive access token."""
    token = await auth_service.login(login_data)
    return token


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user profile."""
    return current_user


@router.post("/logout")
async def logout(
    current_user: UserResponse = Depends(get_current_user),
) -> dict:
    """Logout the current user."""
    # Stateless JWT: logout is client-side - token remains valid until expiry.
    # Frontend should clear the token from storage.
    # For session/cookie architecture, this would revoke/session_invalidate.
    return {"message": "Successfully logged out. Token has been revoked on client side."}


async def _get_super_admin(
    current_user: UserResponse = Depends(get_current_user),
    auth_svc: AuthenticationService = Depends(get_auth_service),
) -> UserInDB:
    """Verify caller is an active SUPER_ADMIN."""
    from app.modules.authentication.schemas import PlatformRole
    # Re-fetch from DB to get UserInDB (including platform_role)
    user = await auth_svc.repository.get_by_id(current_user.id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform account is inactive or access denied."
        )
    if user.platform_role != PlatformRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform Super Admin authority required."
        )
    return user


@router.post("/admin/reset-password")
async def admin_reset_password(
    payload: AdminResetPasswordRequest,
    superadmin: UserInDB = Depends(_get_super_admin),
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Reset a user's password. Requires authenticated SUPER_ADMIN."""
    # Build a session-scoped audit logger for same-transaction audit
    from app.core.container import RepositoryContainer
    container = RepositoryContainer(auth_service.session)
    audit_repo = container.platform_audit

    async def _audit_log(**kwargs):
        from app.modules.platform_admin.schemas import PlatformAuditLogCreate
        entry = PlatformAuditLogCreate(
            actor_account_id=superadmin.id,
            actor_email=superadmin.email,
            **kwargs,
        )
        await audit_repo.create(entry)

    result = await auth_service.reset_password_by_admin(
        target_user_id=payload.target_user_id,
        new_password=payload.new_password,
        password_confirmation=payload.password_confirmation,
        audit_logger=_audit_log,
    )

    return create_api_response(
        success=True,
        data={"target_user_id": result["target_user_id"]},
        message="Password berhasil direset.",
    )