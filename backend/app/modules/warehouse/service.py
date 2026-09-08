from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.warehouse.schemas import (
    WarehouseInDB,
    WarehouseCreate,
    WarehouseUpdate,
    WarehouseStatus,
    InventoryLocationInDB,
    InventoryLocationCreate,
    InventoryLocationUpdate,
    InventoryLocationStatus,
)
from app.modules.warehouse.repository import (
    AbstractWarehouseRepository,
    warehouse_repository,
    AbstractInventoryLocationRepository,
    inventory_location_repository,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import (
    BusinessMembershipRole,
    BusinessMembershipInDB,
)
from app.modules.business.repository import (
    AbstractBusinessRepository,
    business_repository,
)
from app.modules.business.schemas import BusinessStatus
from app.modules.branch.repository import (
    AbstractBranchRepository,
    branch_repository,
)
from app.modules.branch.schemas import BranchStatus


class WarehouseService:
    def __init__(
        self,
        warehouse_repo: AbstractWarehouseRepository = warehouse_repository,
        location_repo: AbstractInventoryLocationRepository = inventory_location_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        business_repo: AbstractBusinessRepository = business_repository,
        branch_repo: AbstractBranchRepository = branch_repository,
    ):
        self.warehouse_repo = warehouse_repo
        self.location_repo = location_repo
        self.membership_service = membership_service
        self.business_repo = business_repo
        self.branch_repo = branch_repo

    async def _validate_access(
        self, business_id: str, user_id: str, required_roles: Optional[tuple[BusinessMembershipRole, ...]] = None
    ) -> BusinessMembershipInDB:
        """
        Validate that:
        1. The business exists and is active (not archived).
        2. The user has an ACTIVE membership in this business.
        3. The membership role is in required_roles (if specified).
        """
        business = await self.business_repo.get_by_id(business_id)
        if not business or business.status == BusinessStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found or access denied.",
            )

        membership = await self.membership_service.require_active_membership(business_id, user_id)

        if required_roles and membership.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied for this warehouse operation.",
            )

        return membership

    async def _validate_branch(self, business_id: str, branch_id: str) -> None:
        branch = await self.branch_repo.get_by_id(branch_id)
        if not branch or branch.business_id != business_id or branch.status != BranchStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid branch specified or branch is not active in this business.",
            )

    async def _pick_next_default_warehouse(self, business_id: str, exclude_warehouse_id: str) -> None:
        warehouses = await self.warehouse_repo.list_by_business(business_id)
        active_candidates = [
            w for w in warehouses
            if w.id != exclude_warehouse_id and w.status == WarehouseStatus.ACTIVE
        ]
        if active_candidates:
            active_candidates.sort(key=lambda x: (x.created_at, x.id))
            next_default = active_candidates[0]
            await self.warehouse_repo.set_default(business_id, next_default.id)

    async def _pick_next_default_location(self, warehouse_id: str, exclude_location_id: str) -> None:
        locations = await self.location_repo.list_by_warehouse(warehouse_id, include_archived=False)
        active_candidates = [
            l for l in locations
            if l.id != exclude_location_id and l.status == InventoryLocationStatus.ACTIVE
        ]
        if active_candidates:
            active_candidates.sort(key=lambda x: (x.created_at, x.id))
            next_default = active_candidates[0]
            await self.location_repo.set_default(warehouse_id, next_default.id)

    # --- Warehouse API ---

    async def create_warehouse(
        self, business_id: str, user_id: str, payload: WarehouseCreate
    ) -> WarehouseInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        if payload.branch_id:
            await self._validate_branch(business_id, payload.branch_id)

        # Code uniqueness within business
        existing_code = await self.warehouse_repo.find_by_code(business_id, payload.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A warehouse with code '{payload.code}' already exists in this business.",
            )

        active_count = await self.warehouse_repo.count_active(business_id)
        is_default = (active_count == 0)

        return await self.warehouse_repo.create(business_id, payload, is_default=is_default)

    async def list_warehouses(self, business_id: str, user_id: str) -> List[WarehouseInDB]:
        await self._validate_access(business_id, user_id)
        return await self.warehouse_repo.list_by_business(business_id)

    async def get_warehouse(
        self, business_id: str, warehouse_id: str, user_id: str
    ) -> WarehouseInDB:
        await self._validate_access(business_id, user_id)

        warehouse = await self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found.",
            )

        return warehouse

    async def update_warehouse(
        self, business_id: str, warehouse_id: str, user_id: str, payload: WarehouseUpdate
    ) -> WarehouseInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        warehouse = await self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found.",
            )

        if warehouse.status == WarehouseStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update an archived warehouse.",
            )

        if payload.branch_id is not None:
            await self._validate_branch(business_id, payload.branch_id)

        return await self.warehouse_repo.update(warehouse_id, payload)

    async def suspend_warehouse(
        self, business_id: str, warehouse_id: str, user_id: str
    ) -> WarehouseInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        warehouse = await self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found.",
            )

        if warehouse.status == WarehouseStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot suspend an archived warehouse.",
            )

        if warehouse.status == WarehouseStatus.SUSPENDED:
            return warehouse

        was_default = warehouse.is_default
        suspended = await self.warehouse_repo.suspend(warehouse_id)

        if was_default:
            await self._pick_next_default_warehouse(business_id, warehouse_id)

        return suspended

    async def activate_warehouse(
        self, business_id: str, warehouse_id: str, user_id: str
    ) -> WarehouseInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        warehouse = await self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found.",
            )

        if warehouse.status == WarehouseStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot activate an archived warehouse.",
            )

        if warehouse.status == WarehouseStatus.ACTIVE:
            return warehouse

        active_count = await self.warehouse_repo.count_active(business_id)
        activated = await self.warehouse_repo.activate(warehouse_id)

        if active_count == 0:
            await self.warehouse_repo.set_default(business_id, warehouse_id)
            activated = await self.warehouse_repo.get_by_id(warehouse_id)

        return activated

    async def archive_warehouse(
        self, business_id: str, warehouse_id: str, user_id: str
    ) -> WarehouseInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        warehouse = await self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found.",
            )

        if warehouse.status == WarehouseStatus.ARCHIVED:
            return warehouse

        was_default = warehouse.is_default
        archived = await self.warehouse_repo.archive(warehouse_id)

        if was_default:
            await self._pick_next_default_warehouse(business_id, warehouse_id)

        return archived

    # --- Inventory Location API ---

    async def create_location(
        self, business_id: str, warehouse_id: str, user_id: str, payload: InventoryLocationCreate
    ) -> InventoryLocationInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        warehouse = await self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found.",
            )

        if warehouse.status == WarehouseStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create location under an archived warehouse.",
            )

        existing_code = await self.location_repo.find_by_code(warehouse_id, payload.code)
        if existing_code:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A location with code '{payload.code}' already exists in this warehouse.",
            )

        active_count = await self.location_repo.count_active(warehouse_id)
        is_default = (active_count == 0)

        return await self.location_repo.create(business_id, warehouse_id, payload, is_default=is_default)

    async def list_locations(
        self, business_id: str, warehouse_id: str, user_id: str
    ) -> List[InventoryLocationInDB]:
        await self._validate_access(business_id, user_id)

        warehouse = await self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found.",
            )

        return await self.location_repo.list_by_warehouse(warehouse_id, include_archived=False)

    async def get_location(
        self, business_id: str, warehouse_id: str, location_id: str, user_id: str
    ) -> InventoryLocationInDB:
        await self._validate_access(business_id, user_id)

        warehouse = await self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found.",
            )

        location = await self.location_repo.get_by_id(location_id)
        if not location or location.warehouse_id != warehouse_id or location.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found.",
            )

        return location

    async def update_location(
        self, business_id: str, warehouse_id: str, location_id: str, user_id: str, payload: InventoryLocationUpdate
    ) -> InventoryLocationInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        warehouse = await self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found.",
            )

        if warehouse.status == WarehouseStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update location under an archived warehouse.",
            )

        location = await self.location_repo.get_by_id(location_id)
        if not location or location.warehouse_id != warehouse_id or location.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found.",
            )

        if location.status == InventoryLocationStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update an archived location.",
            )

        return await self.location_repo.update(location_id, payload)

    async def archive_location(
        self, business_id: str, warehouse_id: str, location_id: str, user_id: str
    ) -> InventoryLocationInDB:
        await self._validate_access(
            business_id, user_id, (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )

        warehouse = await self.warehouse_repo.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse not found.",
            )

        location = await self.location_repo.get_by_id(location_id)
        if not location or location.warehouse_id != warehouse_id or location.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found.",
            )

        if location.status == InventoryLocationStatus.ARCHIVED:
            return location

        was_default = location.is_default
        archived = await self.location_repo.archive(location_id)

        if was_default:
            await self._pick_next_default_location(warehouse_id, location_id)

        return archived


warehouse_service = WarehouseService()
