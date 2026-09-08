from typing import List, Optional
from fastapi import HTTPException, status

from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.pricing.repository import (
    AbstractPriceEntryRepository,
    AbstractPriceListRepository,
    price_entry_repository,
    price_list_repository,
)
from app.modules.pricing.schemas import (
    PriceEntryCreate,
    PriceEntryListResponse,
    PriceEntryResponse,
    PriceEntryStatus,
    PriceEntryUpdate,
    PriceListCreate,
    PriceListListResponse,
    PriceListResponse,
    PriceListStatus,
    PriceListUpdate,
)
from app.modules.product.repository import (
    AbstractProductRepository,
    product_repository,
)
from app.modules.product.schemas import ProductStatus, ProductType
from app.modules.product_variant.repository import (
    AbstractProductVariantRepository,
    product_variant_repository,
)
from app.modules.product_variant.schemas import ProductVariantStatus


class PricingService:
    def __init__(
        self,
        price_list_repo: AbstractPriceListRepository = price_list_repository,
        price_entry_repo: AbstractPriceEntryRepository = price_entry_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        product_repo: AbstractProductRepository = product_repository,
        variant_repo: AbstractProductVariantRepository = product_variant_repository,
    ):
        self.price_list_repo = price_list_repo
        self.price_entry_repo = price_entry_repo
        self.membership_service = membership_service
        self.product_repo = product_repo
        self.variant_repo = variant_repo

    async def _require_active_membership(self, business_id: str, user_id: str):
        return await self.membership_service.require_active_membership(
            business_id, user_id
        )

    async def _require_admin_or_owner(self, business_id: str, user_id: str):
        membership = await self._require_active_membership(business_id, user_id)
        if membership.role not in (
            BusinessMembershipRole.OWNER,
            BusinessMembershipRole.ADMIN,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="OWNER or ADMIN role required.",
            )
        return membership

    # Price List Operations

    async def create_price_list(
        self, business_id: str, user_id: str, data: PriceListCreate
    ) -> PriceListResponse:
        await self._require_admin_or_owner(business_id, user_id)

        existing = await self.price_list_repo.find_by_code(business_id, data.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Price list code '{data.code}' already exists in this business.",
            )

        price_list = await self.price_list_repo.create(business_id, data)
        return PriceListResponse.from_db(price_list)

    async def get_price_list(
        self, business_id: str, user_id: str, price_list_id: str
    ) -> PriceListResponse:
        await self._require_active_membership(business_id, user_id)

        price_list = await self.price_list_repo.get_by_id(price_list_id, business_id)
        if not price_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price list not found.",
            )
        return PriceListResponse.from_db(price_list)

    async def list_price_lists(
        self, business_id: str, user_id: str, include_archived: bool = False
    ) -> PriceListListResponse:
        await self._require_active_membership(business_id, user_id)

        items = await self.price_list_repo.list_by_business(
            business_id, include_archived=include_archived
        )
        return PriceListListResponse(
            items=[PriceListResponse.from_db(item) for item in items],
            total=len(items),
        )

    async def update_price_list(
        self,
        business_id: str,
        user_id: str,
        price_list_id: str,
        data: PriceListUpdate,
    ) -> PriceListResponse:
        await self._require_admin_or_owner(business_id, user_id)

        price_list = await self.price_list_repo.get_by_id(price_list_id, business_id)
        if not price_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price list not found.",
            )

        if data.currency is not None and data.currency != price_list.currency:
            entries = await self.price_entry_repo.list_by_price_list(
                price_list_id, business_id, include_archived=True
            )
            if len(entries) > 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot change currency of a price list with existing entries.",
                )

        updated = await self.price_list_repo.update(price_list_id, business_id, data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price list not found.",
            )
        return PriceListResponse.from_db(updated)

    async def archive_price_list(
        self, business_id: str, user_id: str, price_list_id: str
    ) -> PriceListResponse:
        await self._require_admin_or_owner(business_id, user_id)

        price_list = await self.price_list_repo.get_by_id(price_list_id, business_id)
        if not price_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price list not found.",
            )

        archived = await self.price_list_repo.archive(price_list_id, business_id)
        return PriceListResponse.from_db(archived)

    # Price Entry Operations

    async def create_price_entry(
        self,
        business_id: str,
        price_list_id: str,
        user_id: str,
        data: PriceEntryCreate,
    ) -> PriceEntryResponse:
        await self._require_admin_or_owner(business_id, user_id)

        price_list = await self.price_list_repo.get_by_id(price_list_id, business_id)
        if not price_list or price_list.status != PriceListStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active price list not found.",
            )

        # Target validation
        if data.product_id:
            product = await self.product_repo.get_by_id(data.product_id, business_id)
            if not product or product.status == ProductStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Active product not found.",
                )
        elif data.variant_id:
            variant = await self.variant_repo.get_by_id(data.variant_id, business_id)
            if not variant or variant.status == ProductVariantStatus.ARCHIVED:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Active variant not found.",
                )
            parent_product = await self.product_repo.get_by_id(
                variant.product_id, business_id
            )
            if (
                not parent_product
                or parent_product.status == ProductStatus.ARCHIVED
                or parent_product.product_type != ProductType.GOODS
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent product must exist, be active, and be of type GOODS.",
                )

        # Overlap validation
        overlapping = await self.price_entry_repo.find_overlapping_active(
            business_id=business_id,
            price_list_id=price_list_id,
            product_id=data.product_id,
            variant_id=data.variant_id,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
        )
        if overlapping:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Overlapping active price entry exists for this target in this price list.",
            )

        entry = await self.price_entry_repo.create(
            business_id=business_id,
            price_list_id=price_list_id,
            currency=price_list.currency,
            data=data,
        )
        return PriceEntryResponse.from_db(entry)

    async def get_price_entry(
        self,
        business_id: str,
        price_list_id: str,
        price_id: str,
        user_id: str,
    ) -> PriceEntryResponse:
        await self._require_active_membership(business_id, user_id)

        entry = await self.price_entry_repo.get_by_id(price_id, business_id)
        if not entry or entry.price_list_id != price_list_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price entry not found.",
            )
        return PriceEntryResponse.from_db(entry)

    async def list_price_entries(
        self,
        business_id: str,
        price_list_id: str,
        user_id: str,
        include_archived: bool = False,
    ) -> PriceEntryListResponse:
        await self._require_active_membership(business_id, user_id)

        price_list = await self.price_list_repo.get_by_id(price_list_id, business_id)
        if not price_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price list not found.",
            )

        items = await self.price_entry_repo.list_by_price_list(
            price_list_id, business_id, include_archived=include_archived
        )
        return PriceEntryListResponse(
            items=[PriceEntryResponse.from_db(item) for item in items],
            total=len(items),
        )

    async def update_price_entry(
        self,
        business_id: str,
        price_list_id: str,
        price_id: str,
        user_id: str,
        data: PriceEntryUpdate,
    ) -> PriceEntryResponse:
        await self._require_admin_or_owner(business_id, user_id)

        entry = await self.price_entry_repo.get_by_id(price_id, business_id)
        if not entry or entry.price_list_id != price_list_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price entry not found.",
            )

        new_effective_from = (
            data.effective_from
            if data.effective_from is not None
            else entry.effective_from
        )
        new_effective_to = (
            data.effective_to
            if "effective_to" in data.model_dump(exclude_unset=True)
            else entry.effective_to
        )

        if new_effective_to is not None and new_effective_to < new_effective_from:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="effective_to must be greater than or equal to effective_from.",
            )

        if (
            data.effective_from is not None
            or "effective_to" in data.model_dump(exclude_unset=True)
        ):
            overlapping = await self.price_entry_repo.find_overlapping_active(
                business_id=business_id,
                price_list_id=price_list_id,
                product_id=entry.product_id,
                variant_id=entry.variant_id,
                effective_from=new_effective_from,
                effective_to=new_effective_to,
                exclude_id=price_id,
            )
            if overlapping:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Overlapping active price entry exists for this target in this price list.",
                )

        updated = await self.price_entry_repo.update(price_id, business_id, data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price entry not found.",
            )
        return PriceEntryResponse.from_db(updated)

    async def archive_price_entry(
        self,
        business_id: str,
        price_list_id: str,
        price_id: str,
        user_id: str,
    ) -> PriceEntryResponse:
        await self._require_admin_or_owner(business_id, user_id)

        entry = await self.price_entry_repo.get_by_id(price_id, business_id)
        if not entry or entry.price_list_id != price_list_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Price entry not found.",
            )

        archived = await self.price_entry_repo.archive(price_id, business_id)
        return PriceEntryResponse.from_db(archived)


pricing_service = PricingService()
