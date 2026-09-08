from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.unit.repository import (
    AbstractUnitRepository,
    unit_repository,
    UnitInDB,
)
from app.modules.unit.schemas import (
    UnitCreate,
    UnitUpdate,
    UnitStatus,
    UnitResponse,
    UnitType,
)
from app.modules.business_membership.service import BusinessMembershipService, business_membership_service
from app.modules.business_membership.schemas import BusinessMembershipRole


class UnitService:
    def __init__(
        self,
        repository: AbstractUnitRepository = unit_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.repository = repository
        self.membership_service = membership_service

    async def _require_admin_or_owner(self, business_id: str, user_id: str):
        membership = await self.membership_service.require_active_membership(business_id, user_id)
        if membership.role not in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="OWNER or ADMIN role required.",
            )
        return membership

    async def create_unit(
        self, business_id: str, user_id: str, data: UnitCreate
    ) -> UnitResponse:
        await self._require_admin_or_owner(business_id, user_id)

        # Code uniqueness (case-insensitive) within Business
        existing_code = await self.repository.find_by_code(business_id, data.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Unit code '{data.code.upper()}' already exists in this business.",
            )

        # Name uniqueness (case-insensitive) within Business
        existing_name = await self.repository.find_by_name(business_id, data.name)
        if existing_name:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Unit name '{data.name}' already exists in this business.",
            )

        unit = await self.repository.create(business_id=business_id, unit_data=data)
        return self._to_response(unit)

    async def get_unit(self, business_id: str, user_id: str, unit_id: str) -> UnitResponse:
        await self.membership_service.require_active_membership(business_id, user_id)
        unit = await self.repository.get_by_id(unit_id, business_id)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found.",
            )
        return self._to_response(unit)

    async def list_units(
        self, business_id: str, user_id: str,
        unit_type: Optional[str] = None,
        include_archived: bool = False,
    ) -> List[UnitResponse]:
        await self.membership_service.require_active_membership(business_id, user_id)
        units = await self.repository.list_by_business(
            business_id, unit_type=unit_type, include_archived=include_archived
        )
        return [self._to_response(u) for u in units]

    async def update_unit(
        self, business_id: str, user_id: str, unit_id: str, data: UnitUpdate
    ) -> UnitResponse:
        await self._require_admin_or_owner(business_id, user_id)

        unit = await self.repository.get_by_id(unit_id, business_id)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found.",
            )

        # If changing code, check uniqueness
        if data.code:
            existing = await self.repository.find_by_code(business_id, data.code)
            if existing and existing.id != unit_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Unit code '{data.code.upper()}' already exists.",
                )

        # If changing name, check uniqueness
        if data.name:
            existing = await self.repository.find_by_name(business_id, data.name)
            if existing and existing.id != unit_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Unit name '{data.name}' already exists.",
                )

        updated = await self.repository.update(unit_id, business_id, data)
        return self._to_response(updated)

    async def archive_unit(self, business_id: str, user_id: str, unit_id: str) -> UnitResponse:
        await self._require_admin_or_owner(business_id, user_id)

        unit = await self.repository.get_by_id(unit_id, business_id)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found.",
            )

        archived = await self.repository.archive(unit_id, business_id)
        return self._to_response(archived)

    def _to_response(self, unit: UnitInDB) -> UnitResponse:
        return UnitResponse(
            id=unit.id,
            business_id=unit.business_id,
            name=unit.name,
            code=unit.code,
            symbol=unit.symbol,
            description=unit.description,
            unit_type=unit.unit_type,
            precision=unit.precision,
            status=unit.status,
            created_at=unit.created_at.isoformat(),
            updated_at=unit.updated_at.isoformat(),
        )


unit_service = UnitService()
