from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request, status
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
    ForgotPasswordRequest,
    ResetPasswordRequest,
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
    return {"message": "Successfully logged out. Token has been revoked on client side."}


GENERIC_FORGOT_RESPONSE = "Jika email terdaftar, instruksi reset telah dikirim ke email Anda."


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Request a password reset link. Always returns generic response."""
    from app.core.rate_limit import is_rate_limited
    from app.core.container import RepositoryContainer

    ip_address = request.client.host if request.client else "unknown"

    if is_rate_limited(payload.email, ip_address):
        return create_api_response(
            success=True,
            message=GENERIC_FORGOT_RESPONSE,
        )

    container = RepositoryContainer(auth_service.session)
    audit_repo = container.platform_audit

    async def _audit_log(**kwargs):
        from app.modules.platform_admin.schemas import PlatformAuditLogCreate
        entry = PlatformAuditLogCreate(
            actor_account_id="system",
            actor_email="system@businesshub.local",
            **kwargs,
        )
        await audit_repo.create(entry)

    await auth_service.forgot_password(email=payload.email, ip_address=ip_address, audit_logger=_audit_log)
    return create_api_response(
        success=True,
        message=GENERIC_FORGOT_RESPONSE,
    )


GENERIC_RESET_SUCCESS = "Password berhasil diubah. Silakan login."


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    auth_service: AuthenticationService = Depends(get_auth_service),
):
    """Reset password using a valid reset token."""
    from app.core.container import RepositoryContainer

    container = RepositoryContainer(auth_service.session)
    audit_repo = container.platform_audit

    async def _audit_log(**kwargs):
        from app.modules.platform_admin.schemas import PlatformAuditLogCreate
        entry = PlatformAuditLogCreate(
            actor_account_id="system",
            actor_email="system@businesshub.local",
            **kwargs,
        )
        await audit_repo.create(entry)

    await auth_service.reset_password(
        token=payload.token,
        new_password=payload.new_password,
        password_confirmation=payload.password_confirmation,
        audit_logger=_audit_log,
    )
    return create_api_response(
        success=True,
        message=GENERIC_RESET_SUCCESS,
    )


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