from typing import List, Optional, Tuple
from fastapi import HTTPException, status

from app.modules.customer.repository import (
    AbstractCustomerRepository,
    customer_repository,
    CustomerInDB,
)
from app.modules.customer.schemas import (
    CustomerCreate,
    CustomerUpdate,
    CustomerStatus,
    CustomerType,
    CustomerResponse,
    CustomerListResponse,
)
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole


class CustomerService:
    def __init__(
        self,
        repository: AbstractCustomerRepository = customer_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.repository = repository
        self.membership_service = membership_service

    async def _require_active_membership(self, business_id: str, user_id: str):
        return await self.membership_service.require_active_membership(business_id, user_id)

    async def _require_admin_or_owner(self, business_id: str, user_id: str):
        membership = await self._require_active_membership(business_id, user_id)
        if membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="OWNER or ADMIN role required.",
            )
        return membership

    async def create_customer(
        self, business_id: str, user_id: str, data: CustomerCreate
    ) -> CustomerResponse:
        await self._require_admin_or_owner(business_id, user_id)

        # Generate unique code server-side
        count = await self.repository.count_by_business(business_id)
        code = f"CUS-{count + 1:06d}"
        
        # Ensure uniqueness in case of race / concurrency / existing counts
        while await self.repository.find_by_code(business_id, code):
            count += 1
            code = f"CUS-{count + 1:06d}"

        customer = await self.repository.create(business_id=business_id, customer_data=data, code=code)
        return self._to_response(customer)

    async def get_customer(self, business_id: str, user_id: str, customer_id: str) -> CustomerResponse:
        await self._require_active_membership(business_id, user_id)
        customer = await self.repository.get_by_id(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )
        return self._to_response(customer)

    async def list_customers(
        self,
        business_id: str,
        user_id: str,
        search: Optional[str] = None,
        status_filter: Optional[CustomerStatus] = None,
        customer_type: Optional[CustomerType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CustomerListResponse:
        await self._require_active_membership(business_id, user_id)

        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page must be >= 1.",
            )
        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size must be between 1 and 100.",
            )

        items, total = await self.repository.list_by_business(
            business_id=business_id,
            search=search,
            status=status_filter,
            customer_type=customer_type,
            page=page,
            page_size=page_size,
        )

        return CustomerListResponse(
            items=[self._to_response(c) for c in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def update_customer(
        self, business_id: str, user_id: str, customer_id: str, data: CustomerUpdate
    ) -> CustomerResponse:
        await self._require_admin_or_owner(business_id, user_id)

        customer = await self.repository.get_by_id(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

        updated = await self.repository.update(customer_id, business_id, data)
        return self._to_response(updated)

    async def archive_customer(self, business_id: str, user_id: str, customer_id: str) -> CustomerResponse:
        await self._require_admin_or_owner(business_id, user_id)

        customer = await self.repository.get_by_id(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

        if customer.status == CustomerStatus.ARCHIVED:
            # Idempotent or validation error? Rule says: "Archive bersifat idempotent sesuai pola existing atau return validation error..."
            # Let's check how Category or Product handles archived / delete.
            return self._to_response(customer)

        updated = await self.repository.update_status(customer_id, business_id, CustomerStatus.ARCHIVED)
        return self._to_response(updated)

    async def activate_customer(self, business_id: str, user_id: str, customer_id: str) -> CustomerResponse:
        await self._require_admin_or_owner(business_id, user_id)

        customer = await self.repository.get_by_id(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

        if customer.status == CustomerStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archived customer cannot be reactivated.",
            )

        if customer.status == CustomerStatus.ACTIVE:
            return self._to_response(customer)

        updated = await self.repository.update_status(customer_id, business_id, CustomerStatus.ACTIVE)
        return self._to_response(updated)

    async def deactivate_customer(self, business_id: str, user_id: str, customer_id: str) -> CustomerResponse:
        await self._require_admin_or_owner(business_id, user_id)

        customer = await self.repository.get_by_id(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

        if customer.status == CustomerStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archived customer cannot be deactivated.",
            )

        if customer.status == CustomerStatus.INACTIVE:
            return self._to_response(customer)

        updated = await self.repository.update_status(customer_id, business_id, CustomerStatus.INACTIVE)
        return self._to_response(updated)

    def _to_response(self, customer: CustomerInDB) -> CustomerResponse:
        return CustomerResponse(
            id=customer.id,
            business_id=customer.business_id,
            customer_type=customer.customer_type,
            code=customer.code,
            name=customer.name,
            legal_name=customer.legal_name,
            phone=customer.phone,
            email=customer.email,
            address=customer.address,
            city=customer.city,
            province=customer.province,
            postal_code=customer.postal_code,
            country=customer.country,
            notes=customer.notes,
            status=customer.status,
            credit_limit=customer.credit_limit,
            store_credit_balance=customer.store_credit_balance,
            created_at=customer.created_at.isoformat(),
            updated_at=customer.updated_at.isoformat(),
        )


customer_service = CustomerService()
