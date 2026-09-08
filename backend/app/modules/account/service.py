from app.modules.account.repository import AbstractAccountRepository, account_repository
from app.modules.account.schemas import AccountInDB, AccountUpdate


class AccountService:
    def __init__(self, repository: AbstractAccountRepository = account_repository):
        self.repository = repository

    async def get_or_create_account(self, user_id: str, display_name: str) -> AccountInDB:
        """
        Get the account for a user, creating a default profile if it doesn't exist.
        This implements approach B: create profile on first access (lazy/default-on-read).
        Ensures every authenticated user has exactly one account profile.
        """
        account = await self.repository.get_by_user_id(user_id)
        if not account:
            account = await self.repository.create_for_user(user_id, display_name)
        return account

    async def update_account(self, user_id: str, update_data: AccountUpdate) -> AccountInDB:
        """
        Update the account for a user. Raises KeyError if account doesn't exist.
        Security: user_id comes from authenticated context only - never from request body.
        """
        account = await self.repository.update(user_id, update_data)
        if not account:
            raise KeyError(f"Account not found for user_id: {user_id}")
        return account


account_service = AccountService()
