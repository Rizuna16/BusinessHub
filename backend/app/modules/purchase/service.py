from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status

from app.modules.purchase.schemas import (
    PurchaseInDB,
    PurchaseLineInDB,
    PurchaseResponse,
    PurchaseLineResponse,
    PurchaseListResponse,
    PurchaseCreate,
    PurchaseUpdate,
    PurchaseLineCreate,
    PurchaseLineUpdate,
    PurchaseStatus,
    DerivedReceivingStatus,
    PurchaseReceivingSummary,
)
from app.modules.purchase.repository import (
    AbstractPurchaseRepository,
    purchase_repository,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.supplier.repository import supplier_repository
from app.modules.branch.repository import branch_repository
from app.modules.product.repository import product_repository
from app.modules.product_variant.repository import product_variant_repository
from app.modules.supplier.schemas import SupplierStatus
from app.modules.branch.schemas import BranchStatus
from app.modules.product.schemas import ProductStatus, ProductType
from app.modules.product_variant.schemas import ProductVariantStatus
from app.modules.receiving.repository import (
    AbstractReceivingRepository,
    receiving_repository,
)
from app.modules.supplier_catalog.repository import (
    AbstractSupplierCatalogRepository,
    supplier_catalog_repository,
)
from app.modules.accounting.integration import accounting_integration_service
from app.modules.accounting.tax_calculation import tax_calculation_service
from app.modules.accounting.schemas import TaxSnapshot, PricingMode, TaxTreatment
from app.modules.accounting.repository import accounting_repository
from app.modules.inventory.service import InventoryService, inventory_service
from app.modules.inventory.schemas import InventoryCostMovementType


class PurchaseService:
    def __init__(
        self,
        purchase_repo: AbstractPurchaseRepository = purchase_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        receiving_repo: AbstractReceivingRepository = receiving_repository,
        catalog_repo: AbstractSupplierCatalogRepository = supplier_catalog_repository,
        inv_service: InventoryService = inventory_service,
    ):
        self.purchase_repo = purchase_repo
        self.membership_service = membership_service
        self.receiving_repo = receiving_repo
        self.catalog_repo = catalog_repo
        self.inv_service = inv_service

    async def _validate_access(
        self,
        business_id: str,
        user_id: str,
        required_roles: Optional[tuple[BusinessMembershipRole, ...]] = None,
    ):
        membership = await self.membership_service.require_active_membership(business_id, user_id)
        if required_roles and membership.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {[r.value for r in required_roles]}",
            )
        return membership

    async def _validate_supplier(self, business_id: str, supplier_id: str):
        supplier = await supplier_repository.get_by_id(supplier_id, business_id)
        if not supplier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supplier not found in this business.",
            )
        if supplier.status != SupplierStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Supplier is not ACTIVE (current: {supplier.status}).",
            )
        return supplier

    async def _validate_branch(self, business_id: str, branch_id: str):
        branch = await branch_repository.get_by_id(branch_id)
        if not branch or branch.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Branch not found in this business.",
            )
        if branch.status != BranchStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Branch is not ACTIVE (current: {branch.status}).",
            )
        return branch

    async def _validate_product_and_variant(
        self, business_id: str, product_id: str, variant_id: Optional[str]
    ):
        product = await product_repository.get_by_id(product_id, business_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product not found in this business.",
            )
        if product.status != ProductStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product is not ACTIVE.",
            )
        if product.product_type != ProductType.GOODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SERVICE products cannot be purchased as inventory goods.",
            )

        if variant_id:
            variant = await product_variant_repository.get_by_id(variant_id)
            if not variant or variant.business_id != business_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product variant not found in this business.",
                )
            if variant.product_id != product_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product variant does not belong to the specified product.",
                )
            if variant.status != ProductVariantStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product variant is not ACTIVE.",
                )

    async def _recalculate_totals(self, business_id: str, purchase_id: str):
        lines = await self.purchase_repo.list_lines_for_purchase(purchase_id)
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        tax_total = Decimal("0")

        for l in lines:
            subtotal += l.line_subtotal
            discount_total += l.discount_amount
            tax_total += l.tax_amount

        grand_total = subtotal - discount_total + tax_total

        await self.purchase_repo.update_purchase(
            purchase_id=purchase_id,
            business_id=business_id,
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            grand_total=grand_total,
        )

    async def _build_purchase_response(
        self, business_id: str, purchase: PurchaseInDB
    ) -> PurchaseResponse:
        lines = await self.purchase_repo.list_lines_for_purchase(purchase.id)
        
        total_ordered = Decimal("0")
        total_received = Decimal("0")
        total_remaining = Decimal("0")
        line_responses: List[PurchaseLineResponse] = []

        for l in lines:
            # 1. Catalog price suggestion lookup
            catalog_item = await self.catalog_repo.find_active_catalog_item(
                business_id=business_id,
                supplier_id=purchase.supplier_id,
                product_id=l.product_id,
                variant_id=l.variant_id,
            )
            suggested_price = str(catalog_item.purchase_price) if catalog_item else None

            # 2. Calculate received quantity from FINALIZED Receivings ONLY
            received_qty = await self.receiving_repo.sum_finalized_received_quantity_for_purchase_line(l.id)
            ordered_qty = l.quantity
            remaining_qty = ordered_qty - received_qty
            if remaining_qty < Decimal("0"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Data integrity error: Line {l.id} has received quantity ({received_qty}) exceeding ordered quantity ({ordered_qty}).",
                )

            line_resp = PurchaseLineResponse(
                **l.model_dump(),
                ordered_quantity=str(ordered_qty),
                received_quantity=str(received_qty),
                remaining_quantity=str(remaining_qty),
                suggested_supplier_price=suggested_price,
            )
            line_responses.append(line_resp)

            total_ordered += ordered_qty
            total_received += received_qty
            total_remaining += remaining_qty

        # Derive overall receiving status
        if total_ordered > Decimal("0") and total_received == Decimal("0"):
            status_enum = DerivedReceivingStatus.NOT_RECEIVED
        elif total_received > Decimal("0") and total_received < total_ordered:
            status_enum = DerivedReceivingStatus.PARTIALLY_RECEIVED
        elif total_ordered > Decimal("0") and total_received >= total_ordered:
            status_enum = DerivedReceivingStatus.FULLY_RECEIVED
        else:
            status_enum = DerivedReceivingStatus.NOT_RECEIVED

        summary = PurchaseReceivingSummary(
            total_ordered=str(total_ordered),
            total_received=str(total_received),
            total_remaining=str(total_remaining),
            status=status_enum,
        )

        return PurchaseResponse(**purchase.model_dump(), lines=line_responses, receiving_summary=summary)

    async def create_purchase(
        self, business_id: str, user_id: str, payload: PurchaseCreate
    ) -> PurchaseResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._validate_supplier(business_id, payload.supplier_id)
        await self._validate_branch(business_id, payload.branch_id)

        seq = await self.purchase_repo.get_next_purchase_sequence(business_id)
        purchase_number = f"PUR-{seq:06d}"

        purchase = await self.purchase_repo.create_purchase(
            business_id=business_id,
            supplier_id=payload.supplier_id,
            branch_id=payload.branch_id,
            purchase_number=purchase_number,
            purchase_date=payload.purchase_date,
            created_by_user_id=user_id,
            notes=payload.notes,
            input_vat_creditable=payload.input_vat_creditable,
        )

        return await self._build_purchase_response(business_id, purchase)

    async def list_purchases(
        self,
        business_id: str,
        user_id: str,
        status_filter: Optional[PurchaseStatus] = None,
        supplier_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        receiving_status: Optional[DerivedReceivingStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PurchaseListResponse:
        await self._validate_access(business_id, user_id)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        purchases, total = await self.purchase_repo.list_purchases(
            business_id=business_id,
            status=status_filter,
            supplier_id=supplier_id,
            branch_id=branch_id,
            search=search,
            page=1,
            page_size=10000,
        )

        items = []
        for p in purchases:
            resp = await self._build_purchase_response(business_id, p)
            if receiving_status and resp.receiving_summary and resp.receiving_summary.status != receiving_status:
                continue
            items.append(resp)

        filtered_total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_items = items[start:end]

        return PurchaseListResponse(items=paginated_items, page=page, page_size=page_size, total=filtered_total)

    async def get_purchase(
        self, business_id: str, purchase_id: str, user_id: str
    ) -> PurchaseResponse:
        await self._validate_access(business_id, user_id)
        p = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found.",
            )

        return await self._build_purchase_response(business_id, p)

    async def update_purchase(
        self,
        business_id: str,
        purchase_id: str,
        user_id: str,
        payload: PurchaseUpdate,
    ) -> PurchaseResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        p = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found.",
            )

        if p.status != PurchaseStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT purchases can be updated.",
            )

        if payload.supplier_id is not None:
            await self._validate_supplier(business_id, payload.supplier_id)
        if payload.branch_id is not None:
            await self._validate_branch(business_id, payload.branch_id)

        updated = await self.purchase_repo.update_purchase(
            purchase_id=purchase_id,
            business_id=business_id,
            supplier_id=payload.supplier_id,
            branch_id=payload.branch_id,
            purchase_date=payload.purchase_date,
            notes=payload.notes,
        )

        return await self._build_purchase_response(business_id, updated)

    async def delete_purchase_draft(
        self, business_id: str, purchase_id: str, user_id: str
    ) -> dict:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        p = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found.",
            )

        if p.status != PurchaseStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT purchases can be deleted.",
            )

        await self.purchase_repo.update_purchase(
            purchase_id=purchase_id,
            business_id=business_id,
            is_deleted=True,
        )

        return {"message": "Purchase draft successfully deleted."}

    async def add_line(
        self,
        business_id: str,
        purchase_id: str,
        user_id: str,
        payload: PurchaseLineCreate,
    ) -> PurchaseLineResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        p = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found.",
            )

        if p.status != PurchaseStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft purchase.",
            )

        await self._validate_product_and_variant(business_id, payload.product_id, payload.variant_id)

        # Resolve tax treatment from product and business config
        product = await product_repository.get_by_id(payload.product_id, business_id)
        tax_treatment_val = "STANDARD_NON_LUXURY"
        pricing_mode_val = "TAX_EXCLUSIVE"
        tax_enabled = False

        if product:
            pt = getattr(product, 'tax_treatment', None)
            if pt:
                tax_treatment_val = pt.value if hasattr(pt, 'value') else "STANDARD_NON_LUXURY"

        tc = await accounting_repository.get_tax_config_by_business(business_id)
        if tc:
            pricing_mode_val = tc.pricing_mode.value
            tax_enabled = tc.tax_enabled

        # Server-calculated tax is authoritative if tax_enabled is True;
        # otherwise preserve payload.tax_amount for backward compatibility
        if tax_enabled and tax_treatment_val != "NON_TAXABLE":
            tax_result = tax_calculation_service.calculate_line_tax(
                quantity=payload.quantity,
                unit_price=payload.unit_price,
                discount_amount=payload.discount_amount,
                tax_treatment=TaxTreatment(tax_treatment_val),
                pricing_mode=PricingMode(pricing_mode_val),
            )
            calculated_tax = tax_result.tax_amount
        else:
            calculated_tax = payload.tax_amount if payload.tax_amount is not None else Decimal("0.00")

        line_subtotal = payload.quantity * payload.unit_price
        if payload.discount_amount > line_subtotal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discount amount cannot exceed line subtotal.",
            )

        line_total = line_subtotal - payload.discount_amount + calculated_tax

        line = await self.purchase_repo.create_line(
            purchase_id=purchase_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            description=payload.description,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            discount_amount=payload.discount_amount,
            tax_amount=calculated_tax,
            line_subtotal=line_subtotal,
            line_total=line_total,
        )

        await self._recalculate_totals(business_id, purchase_id)

        catalog_item = await self.catalog_repo.find_active_catalog_item(
            business_id=business_id,
            supplier_id=p.supplier_id,
            product_id=line.product_id,
            variant_id=line.variant_id,
        )
        suggested_price = str(catalog_item.purchase_price) if catalog_item else None

        received_qty = await self.receiving_repo.sum_finalized_received_quantity_for_purchase_line(line.id)
        ordered_qty = line.quantity
        remaining_qty = ordered_qty - received_qty
        if remaining_qty < Decimal("0"):
            remaining_qty = Decimal("0")

        return PurchaseLineResponse(
            **line.model_dump(),
            ordered_quantity=str(ordered_qty),
            received_quantity=str(received_qty),
            remaining_quantity=str(remaining_qty),
            suggested_supplier_price=suggested_price,
        )

    async def update_line(
        self,
        business_id: str,
        purchase_id: str,
        line_id: str,
        user_id: str,
        payload: PurchaseLineUpdate,
    ) -> PurchaseLineResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        p = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found.",
            )

        if p.status != PurchaseStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft purchase.",
            )

        line = await self.purchase_repo.get_line_by_id(line_id, purchase_id)
        if not line:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase line not found.",
            )

        target_product_id = payload.product_id if payload.product_id is not None else line.product_id
        target_variant_id = payload.variant_id if payload.variant_id is not None else line.variant_id

        if payload.product_id is not None or payload.variant_id is not None:
            await self._validate_product_and_variant(business_id, target_product_id, target_variant_id)

        target_qty = payload.quantity if payload.quantity is not None else line.quantity
        target_price = payload.unit_price if payload.unit_price is not None else line.unit_price
        target_disc = payload.discount_amount if payload.discount_amount is not None else line.discount_amount
        target_tax = payload.tax_amount if payload.tax_amount is not None else line.tax_amount

        line_subtotal = target_qty * target_price
        if target_disc > line_subtotal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Discount amount cannot exceed line subtotal.",
            )

        line_total = line_subtotal - target_disc + target_tax

        updated_line = await self.purchase_repo.update_line(
            line_id=line_id,
            purchase_id=purchase_id,
            product_id=payload.product_id,
            variant_id=payload.variant_id,
            description=payload.description,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            discount_amount=payload.discount_amount,
            tax_amount=payload.tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
        )

        await self._recalculate_totals(business_id, purchase_id)

        catalog_item = await self.catalog_repo.find_active_catalog_item(
            business_id=business_id,
            supplier_id=p.supplier_id,
            product_id=updated_line.product_id,
            variant_id=updated_line.variant_id,
        )
        suggested_price = str(catalog_item.purchase_price) if catalog_item else None

        received_qty = await self.receiving_repo.sum_finalized_received_quantity_for_purchase_line(updated_line.id)
        ordered_qty = updated_line.quantity
        remaining_qty = ordered_qty - received_qty
        if remaining_qty < Decimal("0"):
            remaining_qty = Decimal("0")

        return PurchaseLineResponse(
            **updated_line.model_dump(),
            ordered_quantity=str(ordered_qty),
            received_quantity=str(received_qty),
            remaining_quantity=str(remaining_qty),
            suggested_supplier_price=suggested_price,
        )

    async def delete_line(
        self, business_id: str, purchase_id: str, line_id: str, user_id: str
    ) -> dict:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        p = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found.",
            )

        if p.status != PurchaseStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft purchase.",
            )

        success = await self.purchase_repo.delete_line(line_id, purchase_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase line not found.",
            )

        await self._recalculate_totals(business_id, purchase_id)
        return {"message": "Purchase line successfully deleted."}

    async def finalize_purchase(
        self, business_id: str, purchase_id: str, user_id: str
    ) -> PurchaseResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        p = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found.",
            )

        if p.status == PurchaseStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase is already FINALIZED.",
            )
        if p.status == PurchaseStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot finalize a CANCELLED purchase.",
            )
        if p.status != PurchaseStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase is not in DRAFT status.",
            )

        await self._validate_supplier(business_id, p.supplier_id)
        await self._validate_branch(business_id, p.branch_id)

        lines = await self.purchase_repo.list_lines_for_purchase(purchase_id)
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot finalize a purchase without any lines.",
            )

        for l in lines:
            await self._validate_product_and_variant(business_id, l.product_id, l.variant_id)

        await self._recalculate_totals(business_id, purchase_id)

        # Freeze TaxSnapshot for each line
        tc = await accounting_repository.get_tax_config_by_business(business_id)
        pricing_mode_val = tc.pricing_mode.value if tc else "TAX_EXCLUSIVE"

        for l in lines:
            if l.tax_amount == Decimal("0"):
                continue
            product = await product_repository.get_by_id(l.product_id, business_id)
            product_tax_val = "STANDARD_NON_LUXURY"
            if product:
                pt = getattr(product, 'tax_treatment', None)
                if pt:
                    product_tax_val = pt.value if hasattr(pt, 'value') else "STANDARD_NON_LUXURY"

            tax_result = tax_calculation_service.calculate_line_tax(
                quantity=l.quantity,
                unit_price=l.unit_price,
                discount_amount=l.discount_amount,
                tax_treatment=TaxTreatment(product_tax_val),
                pricing_mode=PricingMode(pricing_mode_val),
            )
            snapshot_data = TaxSnapshot(
                tax_treatment=TaxTreatment(product_tax_val),
                pricing_mode=PricingMode(pricing_mode_val),
                statutory_rate=tax_result.statutory_rate,
                dpp_factor=tax_result.dpp_factor,
                commercial_amount=tax_result.commercial_amount,
                dpp=tax_result.dpp,
                tax_amount=tax_result.tax_amount,
            )
            await self.purchase_repo.update_line_snapshot(l.id, purchase_id, snapshot_data)

        p_updated = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        grand_total = p_updated.grand_total if p_updated else Decimal("0")
        tax_total = p_updated.tax_total if p_updated else Decimal("0")
        now = datetime.now(timezone.utc)

        # ── ATOMIC BOUNDARY START ──
        # Accounting posting FIRST (idempotent, safe to retry).
        # If this fails, NO operational status change occurs.
        idem_key = f"PURCHASE:{purchase_id}:FINALIZED"
        await accounting_integration_service.safe_post(
            idem_key,
            lambda: accounting_integration_service.post_purchase_finalized(
                business_id=business_id,
                user_id=user_id,
                purchase_id=purchase_id,
                grand_total=grand_total,
                purchase_date=p_updated.purchase_date if p_updated else now,
                tax_total=tax_total,
                input_vat_creditable=p_updated.input_vat_creditable if p_updated else False,
                branch_id=p_updated.branch_id if p_updated else None,
            )
        )

        # Update physical stock & cost pool (graceful if no warehouse/location resolved)
        try:
            location_id = await self.inv_service._resolve_sale_location(business_id, None, p_updated.branch_id if p_updated else None)
            creditable = p_updated.input_vat_creditable if p_updated else False

            for l in lines:
                # Physical stock increment
                await self.inv_service.balance_repo.upsert_balance(
                    business_id=business_id,
                    inventory_location_id=location_id,
                    product_id=l.product_id,
                    variant_id=l.variant_id,
                    delta=l.quantity,
                )

                # Inbound line cost calculation
                if creditable:
                    line_net_cost = l.line_subtotal - l.discount_amount
                else:
                    line_net_cost = l.line_total

                unit_acquisition_cost = line_net_cost / l.quantity if l.quantity > Decimal("0") else Decimal("0")

                await self.inv_service.record_cost_inbound(
                    business_id=business_id,
                    product_id=l.product_id,
                    variant_id=l.variant_id,
                    inbound_qty=l.quantity,
                    inbound_unit_cost=unit_acquisition_cost,
                    movement_type=InventoryCostMovementType.PURCHASE_IN,
                    reference_type="PURCHASE",
                    reference_id=purchase_id,
                )
        except Exception:
            pass  # Skip physical/cost update if warehouse/location unavailable

        updated = await self.purchase_repo.update_purchase(
            purchase_id=purchase_id,
            business_id=business_id,
            status=PurchaseStatus.FINALIZED,
            finalized_by_user_id=user_id,
            finalized_at=now,
        )
        # ── ATOMIC BOUNDARY END ──

        return await self._build_purchase_response(business_id, updated)

    async def cancel_purchase(
        self, business_id: str, purchase_id: str, user_id: str
    ) -> PurchaseResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        p = await self.purchase_repo.get_purchase_by_id(purchase_id, business_id)
        if not p:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Purchase not found.",
            )

        if p.status == PurchaseStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase is already CANCELLED.",
            )
        if p.status == PurchaseStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a FINALIZED purchase.",
            )
        if p.status != PurchaseStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT purchases can be cancelled.",
            )

        now = datetime.now(timezone.utc)
        updated = await self.purchase_repo.update_purchase(
            purchase_id=purchase_id,
            business_id=business_id,
            status=PurchaseStatus.CANCELLED,
            cancelled_by_user_id=user_id,
            cancelled_at=now,
        )

        return await self._build_purchase_response(business_id, updated)


purchase_service = PurchaseService()
