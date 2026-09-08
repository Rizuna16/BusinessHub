from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.account.service import AccountService, account_service
from app.modules.account.schemas import AccountResponse, AccountUpdate
from app.modules.authentication.router import get_current_user
from app.modules.authentication.schemas import UserResponse
from app.core.config import settings

router = APIRouter(prefix=settings.api_v1_prefix + "/account", tags=["Account"])


# Dependency that resolves the current authenticated user's account.
# This is the shared abstraction other features (Business, etc.) can reuse.
async def get_current_account(
    current_user: UserResponse = Depends(get_current_user),
    account_service: AccountService = Depends(lambda: account_service),
) -> tuple[UserResponse, "AccountResponse"]:
    """FastAPI dependency that returns (current_user, account) or raises 401."""
    account = await account_service.get_or_create_account(
        user_id=current_user.id,
        display_name=current_user.full_name,
    )
    return current_user, account


@router.get("", response_model=AccountResponse)
async def get_account(
    current_user: UserResponse = Depends(get_current_user),
    account_service: AccountService = Depends(lambda: account_service),
) -> AccountResponse:
    """
    Get the current authenticated user's account profile.
    Returns the account, creating a default profile lazily on first access.
    """
    account = await account_service.get_or_create_account(
        user_id=current_user.id,
        display_name=current_user.full_name,
    )
    return account


@router.patch("", response_model=AccountResponse)
async def patch_account(
    account_update: AccountUpdate,
    current_user: UserResponse = Depends(get_current_user),
    account_service: AccountService = Depends(lambda: account_service),
) -> AccountResponse:
    """
    Update the current authenticated user's account profile.
    Only display_name, phone, avatar_url, timezone, and locale can be modified.
    Email, password, user_id, id, is_active, and created_at are immutable here.
    If no account exists yet, a default profile is created before applying the update.
    """
    # Security: user_id comes exclusively from the authenticated context (JWT sub).
    # Any user_id in the request body is deliberately ignored.
    # Ensure account exists (lazy creation) before updating
    await account_service.get_or_create_account(
        user_id=current_user.id,
        display_name=current_user.full_name,
    )
    account = await account_service.update_account(current_user.id, account_update)
    return account
