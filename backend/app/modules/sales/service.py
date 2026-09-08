from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status

from app.modules.sales.schemas import (
    SalesInDB,
    SalesLineInDB,
    SalesResponse,
    SalesLineResponse,
    SalesListResponse,
    SalesCreate,
    SalesUpdate,
    SalesFinalize,
    SalesLineCreate,
    SalesLineUpdate,
    SalesStatus,
)
from app.modules.sales.repository import (
    AbstractSalesRepository,
    sales_repository,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.customer.repository import customer_repository
from app.modules.branch.repository import branch_repository
from app.modules.product.repository import product_repository
from app.modules.product_variant.repository import product_variant_repository
from app.modules.customer.schemas import CustomerStatus
from app.modules.branch.schemas import BranchStatus
from app.modules.product.schemas import ProductStatus, ProductType
from app.modules.product_variant.schemas import ProductVariantStatus
from app.modules.pricing.repository import (
    AbstractPriceListRepository,
    price_list_repository,
    AbstractPriceEntryRepository,
    price_entry_repository,
)
from app.modules.pricing.schemas import PriceListStatus, PriceEntryStatus
from app.modules.inventory.service import (
    InventoryService,
    inventory_service,
)
from app.modules.inventory.schemas import InventoryCostMovementType
from app.modules.accounting.integration import accounting_integration_service
from app.modules.accounting.tax_calculation import tax_calculation_service
from app.modules.accounting.schemas import TaxSnapshot, TaxConfigurationInDB, PricingMode, TaxTreatment
from app.modules.accounting.repository import accounting_repository


class SalesService:
    def __init__(
        self,
        sales_repo: AbstractSalesRepository = sales_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        price_list_repo: AbstractPriceListRepository = price_list_repository,
        price_entry_repo: AbstractPriceEntryRepository = price_entry_repository,
        inventory_srv: InventoryService = inventory_service,
    ):
        self.sales_repo = sales_repo
        self.membership_service = membership_service
        self.price_list_repo = price_list_repo
        self.price_entry_repo = price_entry_repo
        self.inventory_srv = inventory_srv

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

    async def _validate_customer(self, business_id: str, customer_id: Optional[str]):
        if customer_id is None:
            return None
        customer = await customer_repository.get_by_id(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Customer not found in this business.",
            )
        if customer.status != CustomerStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Customer is not ACTIVE (current: {customer.status}).",
            )
        return customer

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
        self, business_id: str, product_id: Optional[str], variant_id: Optional[str]
    ) -> tuple[str, Optional[str]]:
        """
        Validates target product XOR variant.
        Returns resolved (product_id, variant_id).
        """
        if variant_id:
            variant = await product_variant_repository.get_by_id(variant_id, business_id)
            if not variant or variant.business_id != business_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product variant not found in this business.",
                )
            if variant.status != ProductVariantStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product variant is not ACTIVE.",
                )

            # Check parent product
            parent_product = await product_repository.get_by_id(variant.product_id, business_id)
            if not parent_product or parent_product.business_id != business_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent product not found in this business.",
                )
            if parent_product.status != ProductStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Parent product is not ACTIVE.",
                )
            if parent_product.product_type != ProductType.GOODS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Variants are only supported for GOODS product type.",
                )

            if product_id and product_id != variant.product_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product variant does not belong to the specified product.",
                )

            return variant.product_id, variant.id

        elif product_id:
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
            return product.id, None

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sales line must specify product_id or variant_id.",
            )

    async def _recalculate_totals(self, business_id: str, sales_id: str):
        lines = await self.sales_repo.list_lines_for_sales(sales_id)
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        tax_total = Decimal("0")

        for l in lines:
            subtotal += l.line_subtotal
            discount_total += l.discount_amount
            tax_total += l.tax_amount

        grand_total = subtotal - discount_total + tax_total

        await self.sales_repo.update_sales(
            sales_id=sales_id,
            business_id=business_id,
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            grand_total=grand_total,
        )

    async def _build_sales_response(self, business_id: str, sales: SalesInDB) -> SalesResponse:
        lines = await self.sales_repo.list_lines_for_sales(sales.id)
        line_responses: List[SalesLineResponse] = []

        for l in lines:
            suggested_price = None
            price_entry = await self._find_active_price_entry(business_id, sales.sales_date, l.product_id, l.variant_id)
            if price_entry:
                suggested_price = str(price_entry.amount)

            line_resp = SalesLineResponse(
                **l.model_dump(),
                suggested_selling_price=suggested_price,
            )
            line_responses.append(line_resp)

        return SalesResponse(**sales.model_dump(), lines=line_responses)

    async def _find_active_price_entry(
        self, business_id: str, sales_date: datetime, product_id: str, variant_id: Optional[str]
    ):
        # Try default price list first
        default_price_list = await self.price_list_repo.get_default(business_id)
        if default_price_list:
            entries = await self.price_entry_repo.list_by_price_list(default_price_list.id, business_id)
            for pe in entries:
                if pe.status != PriceEntryStatus.ACTIVE:
                    continue
                if product_id and pe.product_id != product_id:
                    continue
                if variant_id and pe.variant_id != variant_id:
                    continue
                if pe.effective_from > sales_date:
                    continue
                if pe.effective_to and pe.effective_to < sales_date:
                    continue
                return pe

        # If no default, check all active price lists
        price_lists = await self.price_list_repo.list_by_business(business_id)
        for pl in price_lists:
            if pl.status != PriceListStatus.ACTIVE:
                continue
            entries = await self.price_entry_repo.list_by_price_list(pl.id, business_id)
            for pe in entries:
                if pe.status != PriceEntryStatus.ACTIVE:
                    continue
                if product_id and pe.product_id != product_id:
                    continue
                if variant_id and pe.variant_id != variant_id:
                    continue
                if pe.effective_from > sales_date:
                    continue
                if pe.effective_to and pe.effective_to < sales_date:
                    continue
                return pe
        return None

    async def create_sales(self, business_id: str, user_id: str, payload: SalesCreate) -> SalesResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._validate_customer(business_id, payload.customer_id)
        await self._validate_branch(business_id, payload.branch_id)

        seq = await self.sales_repo.get_next_sales_sequence(business_id)
        sales_number = f"SAL-{seq:06d}"

        sales = await self.sales_repo.create_sales(
            business_id=business_id,
            customer_id=payload.customer_id,
            branch_id=payload.branch_id,
            sales_number=sales_number,
            sales_date=payload.sales_date,
            created_by_user_id=user_id,
            notes=payload.notes,
        )

        return await self._build_sales_response(business_id, sales)

    async def list_sales(
        self,
        business_id: str,
        user_id: str,
        status: Optional[SalesStatus] = None,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> SalesListResponse:
        await self._validate_access(business_id, user_id)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        sales_list, total = await self.sales_repo.list_sales(
            business_id=business_id,
            status=status,
            customer_id=customer_id,
            branch_id=branch_id,
            search=search,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
        )

        items = []
        for s in sales_list:
            items.append(await self._build_sales_response(business_id, s))

        return SalesListResponse(items=items, page=page, page_size=page_size, total=total)

    async def get_sales(self, business_id: str, sales_id: str, user_id: str) -> SalesResponse:
        await self._validate_access(business_id, user_id)
        s = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found.",
            )
        return await self._build_sales_response(business_id, s)

    async def update_sales(
        self,
        business_id: str,
        sales_id: str,
        user_id: str,
        payload: SalesUpdate,
    ) -> SalesResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        s = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found.",
            )

        if s.status != SalesStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT sales can be updated.",
            )

        if payload.customer_id is not None:
            await self._validate_customer(business_id, payload.customer_id)
        if payload.branch_id is not None:
            await self._validate_branch(business_id, payload.branch_id)

        updated = await self.sales_repo.update_sales(
            sales_id=sales_id,
            business_id=business_id,
            customer_id=payload.customer_id,
            branch_id=payload.branch_id,
            sales_date=payload.sales_date,
            notes=payload.notes,
        )

        return await self._build_sales_response(business_id, updated)

    async def delete_sales_draft(self, business_id: str, sales_id: str, user_id: str) -> dict:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        s = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found.",
            )

        if s.status != SalesStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT sales can be deleted.",
            )

        await self.sales_repo.update_sales(
            sales_id=sales_id,
            business_id=business_id,
            is_deleted=True,
        )

        return {"message": "Sales draft successfully deleted."}

    async def add_line(
        self,
        business_id: str,
        sales_id: str,
        user_id: str,
        payload: SalesLineCreate,
    ) -> SalesLineResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        s = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found.",
            )

        if s.status != SalesStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft sales.",
            )

        resolved_product_id, resolved_variant_id = await self._validate_product_and_variant(
            business_id, payload.product_id, payload.variant_id
        )

        # Resolve tax treatment from product and business config
        product = await product_repository.get_by_id(resolved_product_id, business_id)
        tax_treatment = TaxTreatment.STANDARD_NON_LUXURY
        pricing_mode = PricingMode.TAX_EXCLUSIVE
        tax_enabled = False

        if product:
            product_tax = getattr(product, 'tax_treatment', None)
            if product_tax:
                tax_treatment = TaxTreatment(product_tax.value) if hasattr(product_tax, 'value') else TaxTreatment.STANDARD_NON_LUXURY

        tc = await accounting_repository.get_tax_config_by_business(business_id)
        if tc:
            pricing_mode = tc.pricing_mode
            tax_enabled = tc.tax_enabled

        # Server-calculated tax is authoritative if tax_enabled is True;
        # otherwise preserve payload.tax_amount for backward compatibility
        if tax_enabled and tax_treatment != TaxTreatment.NON_TAXABLE:
            tax_result = tax_calculation_service.calculate_line_tax(
                quantity=payload.quantity,
                unit_price=payload.unit_price,
                discount_amount=payload.discount_amount,
                tax_treatment=tax_treatment,
                pricing_mode=pricing_mode,
            )
            calculated_tax = tax_result.tax_amount
        else:
            calculated_tax = payload.tax_amount if payload.tax_amount is not None else Decimal("0.00")

        line_subtotal = payload.quantity * payload.unit_price
        line_total = line_subtotal - payload.discount_amount + calculated_tax

        line = await self.sales_repo.create_line(
            sales_id=sales_id,
            product_id=resolved_product_id,
            variant_id=resolved_variant_id,
            description=payload.description,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            discount_amount=payload.discount_amount,
            tax_amount=calculated_tax,
            line_subtotal=line_subtotal,
            line_total=line_total,
        )

        await self._recalculate_totals(business_id, sales_id)

        # Find suggested price from price list
        suggested_price = None
        price_entry = await self._find_active_price_entry(business_id, s.sales_date, resolved_product_id, resolved_variant_id)
        if price_entry:
            suggested_price = str(price_entry.amount)

        return SalesLineResponse(
            **line.model_dump(),
            suggested_selling_price=suggested_price,
        )

    async def update_line(
        self,
        business_id: str,
        sales_id: str,
        line_id: str,
        user_id: str,
        payload: SalesLineUpdate,
    ) -> SalesLineResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        s = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found.",
            )

        if s.status != SalesStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft sales.",
            )

        line = await self.sales_repo.get_line_by_id(line_id, sales_id)
        if not line:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales line not found.",
            )

        target_product_id = payload.product_id if payload.product_id is not None else line.product_id
        target_variant_id = payload.variant_id if payload.variant_id is not None else line.variant_id

        if payload.product_id is not None or payload.variant_id is not None:
            resolved_product_id, resolved_variant_id = await self._validate_product_and_variant(
                business_id, target_product_id, target_variant_id
            )
        else:
            resolved_product_id, resolved_variant_id = target_product_id, target_variant_id

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

        updated_line = await self.sales_repo.update_line(
            line_id=line_id,
            sales_id=sales_id,
            product_id=resolved_product_id,
            variant_id=resolved_variant_id,
            description=payload.description,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            discount_amount=payload.discount_amount,
            tax_amount=payload.tax_amount,
            line_subtotal=line_subtotal,
            line_total=line_total,
        )

        await self._recalculate_totals(business_id, sales_id)

        suggested_price = None
        price_entry = await self._find_active_price_entry(business_id, s.sales_date, resolved_product_id, resolved_variant_id)
        if price_entry:
            suggested_price = str(price_entry.amount)

        return SalesLineResponse(
            **updated_line.model_dump(),
            suggested_selling_price=suggested_price,
        )

    async def delete_line(self, business_id: str, sales_id: str, line_id: str, user_id: str) -> dict:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        s = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found.",
            )

        if s.status != SalesStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify lines of a non-draft sales.",
            )

        success = await self.sales_repo.delete_line(line_id, sales_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales line not found.",
            )

        await self._recalculate_totals(business_id, sales_id)
        return {"message": "Sales line successfully deleted."}

    async def finalize_sales(
        self,
        business_id: str,
        sales_id: str,
        user_id: str,
        payload: Optional[SalesFinalize] = None,
    ) -> SalesResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        s = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found.",
            )

        if s.status == SalesStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sales is already FINALIZED.",
            )
        if s.status == SalesStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot finalize a CANCELLED sales.",
            )
        if s.status != SalesStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sales is not in DRAFT status.",
            )

        await self._validate_customer(business_id, s.customer_id)
        await self._validate_branch(business_id, s.branch_id)

        lines = await self.sales_repo.list_lines_for_sales(sales_id)
        if not lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot finalize a sales without any lines.",
            )

        goods_lines = []
        for l in lines:
            prod_id, var_id = await self._validate_product_and_variant(business_id, l.product_id, l.variant_id)
            # Check product type to see if it's GOODS
            target_prod_id = var_id and prod_id or l.product_id
            product = await product_repository.get_by_id(target_prod_id, business_id)
            if product and product.product_type == ProductType.GOODS:
                goods_lines.append({
                    "product_id": prod_id,
                    "variant_id": var_id,
                    "quantity": l.quantity,
                    "sales_line_id": l.id,
                })

        # --- Pre-validation (only if cost state exists for any goods line) ---
        has_cost_state = False
        for g in goods_lines:
            cs = await self.inventory_srv.cost_repo.get_cost_state(business_id, g["product_id"], g["variant_id"])
            if cs is not None:
                has_cost_state = True
                break

        if has_cost_state:
            for g in goods_lines:
                physical_qty = await self.inventory_srv.get_physical_quantity(business_id, g["product_id"], g["variant_id"])
                if physical_qty < g["quantity"]:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Insufficient stock for product {g['product_id']}. Available: {physical_qty}, required: {g['quantity']}.",
                    )
                await self.inventory_srv.validate_physical_cost_consistency(business_id, g["product_id"], g["variant_id"])

        await self._recalculate_totals(business_id, sales_id)

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
            await self.sales_repo.update_line_snapshot(l.id, sales_id, snapshot_data)

        # --- Freeze Cost Snapshots for goods lines & Calculate total COGS ---
        total_cogs = Decimal("0")
        # Build a map for quick lookup
        goods_map = {g["sales_line_id"]: g for g in goods_lines}
        for l in lines:
            if l.id in goods_map:
                g = goods_map[l.id]
                mac = await self.inventory_srv.get_current_mac(business_id, g["product_id"], g["variant_id"])
                cost_total = l.quantity * mac
                await self.sales_repo.update_line_cost_snapshots(
                    line_id=l.id,
                    sales_id=sales_id,
                    unit_cost_snapshot=mac,
                    cost_total_snapshot=cost_total,
                )
                total_cogs += cost_total

        # Compute grand_total from freshly saved totals for accounting posting
        s_updated = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        grand_total = s_updated.grand_total if s_updated else Decimal("0")
        tax_total = s_updated.tax_total if s_updated else Decimal("0")

        now = datetime.now(timezone.utc)

        # ── ATOMIC BOUNDARY START ──
        # Accounting posting FIRST (idempotent, safe to retry).
        # If this fails, NO operational state changes occur.
        idem_key = f"SALES:{sales_id}:FINALIZED"
        await accounting_integration_service.safe_post(
            idem_key,
            lambda: accounting_integration_service.post_sales_finalized(
                business_id=business_id,
                user_id=user_id,
                sales_id=sales_id,
                grand_total=grand_total,
                sales_date=s_updated.sales_date if s_updated else now,
                tax_total=tax_total,
                total_cogs=total_cogs,
                branch_id=s_updated.branch_id if s_updated else None,
            )
        )

        # Then inventory deduction + cost pool deduction + status update
        explicit_loc = payload.inventory_location_id if payload else None
        if goods_lines:
            await self.inventory_srv.deduct_sales_stock(
                business_id=business_id,
                user_id=user_id,
                sales_id=sales_id,
                sales_number=s.sales_number,
                explicit_location_id=explicit_loc,
                branch_id=s.branch_id,
                goods_lines=goods_lines,
            )

            for g in goods_lines:
                mac = await self.inventory_srv.get_current_mac(business_id, g["product_id"], g["variant_id"])
                await self.inventory_srv.record_cost_outbound(
                    business_id=business_id,
                    product_id=g["product_id"],
                    variant_id=g["variant_id"],
                    outbound_qty=g["quantity"],
                    unit_cost=mac,
                    movement_type=InventoryCostMovementType.SALE_OUT,
                    reference_type="SALES",
                    reference_id=sales_id,
                )

        now = datetime.now(timezone.utc)
        updated = await self.sales_repo.update_sales(
            sales_id=sales_id,
            business_id=business_id,
            status=SalesStatus.FINALIZED,
            finalized_by_user_id=user_id,
            finalized_at=now,
        )
        # ── ATOMIC BOUNDARY END ──

        return await self._build_sales_response(business_id, updated)

    async def cancel_sales(self, business_id: str, sales_id: str, user_id: str) -> SalesResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        s = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        if not s:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found.",
            )

        if s.status == SalesStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sales is already CANCELLED.",
            )
        if s.status == SalesStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel a FINALIZED sales.",
            )
        if s.status != SalesStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only DRAFT sales can be cancelled.",
            )

        now = datetime.now(timezone.utc)
        updated = await self.sales_repo.update_sales(
            sales_id=sales_id,
            business_id=business_id,
            status=SalesStatus.CANCELLED,
            cancelled_by_user_id=user_id,
            cancelled_at=now,
        )

        return await self._build_sales_response(business_id, updated)


sales_service = SalesService()
