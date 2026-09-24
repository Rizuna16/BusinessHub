from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.modules.authentication.schemas import UserCreate, UserResponse, UserInDB, LoginRequest, TokenResponse
from app.modules.authentication.repository import AbstractUserRepository, user_repository
from app.modules.authentication import security


class AuthenticationService:
    def __init__(
        self,
        repository: AbstractUserRepository = user_repository,
        session: Optional[AsyncSession] = None,
    ):
        self.repository = repository
        self.security = security
        self.session = session

    async def register(self, user_data: UserCreate) -> UserResponse:
        if self.session is not None:
            if self.session.in_transaction():
                return await self._register_impl(user_data)
            async with self.session.begin():
                return await self._register_impl(user_data)
        return await self._register_impl(user_data)

    async def _register_impl(self, user_data: UserCreate) -> UserResponse:
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

        access_token = self.security.create_access_token(data={
            "sub": user.id,
            "platform_role": user.platform_role.value if user.platform_role else None
        })
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

    async def reset_password_by_admin(
        self,
        target_user_id: str,
        new_password: str,
        password_confirmation: str,
        audit_logger: Any = None,
    ) -> Dict[str, str]:
        if self.session is not None:
            if self.session.in_transaction():
                return await self._reset_password_impl(target_user_id, new_password, password_confirmation, audit_logger)
            async with self.session.begin():
                return await self._reset_password_impl(target_user_id, new_password, password_confirmation, audit_logger)
        return await self._reset_password_impl(target_user_id, new_password, password_confirmation, audit_logger)

    async def _reset_password_impl(
        self,
        target_user_id: str,
        new_password: str,
        password_confirmation: str,
        audit_logger: Any = None,
    ) -> Dict[str, str]:
        if new_password != password_confirmation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Konfirmasi password tidak cocok."
            )
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password harus minimal 8 karakter."
            )

        target_user = await self.repository.get_by_id(target_user_id)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found."
            )

        hashed = self.security.hash_password(new_password)
        await self.repository.update_password(target_user_id, hashed)

        if audit_logger is not None:
            try:
                await audit_logger(
                    action="PASSWORD_RESET_BY_ADMIN",
                    target_type="USER",
                    target_id=target_user_id,
                    before_state=None,
                    after_state=None,
                    result="SUCCESS",
                )
            except Exception:
                pass

        return {"target_user_id": target_user_id}


auth_service = AuthenticationService()
