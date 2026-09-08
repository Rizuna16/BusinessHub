from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.modules.authentication.service import auth_service, AuthenticationService
from app.modules.authentication.schemas import (
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    TokenPayload,
)
from app.core.config import settings

router = APIRouter(prefix=settings.api_v1_prefix + "/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=settings.api_v1_prefix + "/auth/login")


def get_auth_service() -> AuthenticationService:
    return auth_service


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