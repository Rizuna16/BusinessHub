from typing import Optional
from fastapi import HTTPException, status

from app.modules.authentication.schemas import UserCreate, UserResponse, UserInDB, LoginRequest, TokenResponse
from app.modules.authentication.repository import AbstractUserRepository, user_repository
from app.modules.authentication import security


class AuthenticationService:
    def __init__(self, repository: AbstractUserRepository = user_repository):
        self.repository = repository
        self.security = security

    async def register(self, user_data: UserCreate) -> UserResponse:
        # Check password confirmation match
        if user_data.password != user_data.password_confirmation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password confirmation does not match password."
            )

        # Check duplicate email
        existing_user = await self.repository.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email is already registered."
            )

        user_in_db = await self.repository.create(user_data)
        return UserResponse.model_validate(user_in_db)

    async def login(self, login_data: LoginRequest) -> TokenResponse:
        generic_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        user = await self.repository.get_by_email(login_data.email)
        if not user:
            raise generic_error

        if not self.security.verify_password(login_data.password, user.password_hash):
            raise generic_error

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive."
            )

        access_token = self.security.create_access_token(data={"sub": user.id})
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=60 * 10
        )

    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        user = await self.repository.get_by_id(user_id)
        if not user or not user.is_active:
            return None
        return UserResponse.model_validate(user)


auth_service = AuthenticationService()
