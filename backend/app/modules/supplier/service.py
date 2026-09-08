from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.supplier.repository import (
    AbstractSupplierRepository,
    supplier_repository,
    SupplierInDB,
)
from app.modules.supplier.schemas import (
    SupplierCreate,
    SupplierUpdate,
    SupplierStatus,
    SupplierType,
    SupplierResponse,
    SupplierListResponse,
)
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole


class SupplierService:
    def __init__(
        self,
        repository: AbstractSupplierRepository = supplier_repository,
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

    async def create_supplier(
        self, business_id: str, user_id: str, data: SupplierCreate
    ) -> SupplierResponse:
        await self._require_admin_or_owner(business_id, user_id)

        count = await self.repository.count_by_business(business_id)
        code = f"SUP-{count + 1:06d}"
        
        while await self.repository.find_by_code(business_id, code):
            count += 1
            code = f"SUP-{count + 1:06d}"

        supplier = await self.repository.create(business_id=business_id, supplier_data=data, code=code)
        return self._to_response(supplier)

    async def get_supplier(self, business_id: str, user_id: str, supplier_id: str) -> SupplierResponse:
        await self._require_active_membership(business_id, user_id)
        supplier = await self.repository.get_by_id(supplier_id, business_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found.",
            )
        return self._to_response(supplier)

    async def list_suppliers(
        self,
        business_id: str,
        user_id: str,
        search: Optional[str] = None,
        status_filter: Optional[SupplierStatus] = None,
        supplier_type: Optional[SupplierType] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SupplierListResponse:
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
            supplier_type=supplier_type,
            page=page,
            page_size=page_size,
        )

        return SupplierListResponse(
            items=[self._to_response(s) for s in items],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def update_supplier(
        self, business_id: str, user_id: str, supplier_id: str, data: SupplierUpdate
    ) -> SupplierResponse:
        await self._require_admin_or_owner(business_id, user_id)

        supplier = await self.repository.get_by_id(supplier_id, business_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found.",
            )

        updated = await self.repository.update(supplier_id, business_id, data)
        return self._to_response(updated)

    async def archive_supplier(self, business_id: str, user_id: str, supplier_id: str) -> SupplierResponse:
        await self._require_admin_or_owner(business_id, user_id)

        supplier = await self.repository.get_by_id(supplier_id, business_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found.",
            )

        if supplier.status == SupplierStatus.ARCHIVED:
            return self._to_response(supplier)

        updated = await self.repository.update_status(supplier_id, business_id, SupplierStatus.ARCHIVED)
        return self._to_response(updated)

    async def activate_supplier(self, business_id: str, user_id: str, supplier_id: str) -> SupplierResponse:
        await self._require_admin_or_owner(business_id, user_id)

        supplier = await self.repository.get_by_id(supplier_id, business_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found.",
            )

        if supplier.status == SupplierStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archived supplier cannot be reactivated.",
            )

        if supplier.status == SupplierStatus.ACTIVE:
            return self._to_response(supplier)

        updated = await self.repository.update_status(supplier_id, business_id, SupplierStatus.ACTIVE)
        return self._to_response(updated)

    async def deactivate_supplier(self, business_id: str, user_id: str, supplier_id: str) -> SupplierResponse:
        await self._require_admin_or_owner(business_id, user_id)

        supplier = await self.repository.get_by_id(supplier_id, business_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier not found.",
            )

        if supplier.status == SupplierStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archived supplier cannot be deactivated.",
            )

        if supplier.status == SupplierStatus.INACTIVE:
            return self._to_response(supplier)

        updated = await self.repository.update_status(supplier_id, business_id, SupplierStatus.INACTIVE)
        return self._to_response(updated)

    def _to_response(self, supplier: SupplierInDB) -> SupplierResponse:
        return SupplierResponse(
            id=supplier.id,
            business_id=supplier.business_id,
            supplier_type=supplier.supplier_type,
            code=supplier.code,
            name=supplier.name,
            legal_name=supplier.legal_name,
            phone=supplier.phone,
            email=supplier.email,
            address=supplier.address,
            city=supplier.city,
            province=supplier.province,
            postal_code=supplier.postal_code,
            country=supplier.country,
            notes=supplier.notes,
            status=supplier.status,
            created_at=supplier.created_at.isoformat(),
            updated_at=supplier.updated_at.isoformat(),
        )


supplier_service = SupplierService()
