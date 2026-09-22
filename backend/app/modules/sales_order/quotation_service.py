from typing import List, Optional
from decimal import Decimal
from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sales_order.schemas import (
    QuotationInDB,
    QuotationLineInDB,
    QuotationResponse,
    QuotationLineResponse,
    QuotationListResponse,
    QuotationCreate,
    QuotationUpdate,
    QuotationAction,
    QuotationConvert,
    QuotationLineCreate,
    QuotationLineUpdate,
    QuotationStatus,
)
from app.modules.sales_order.repository import (
    AbstractQuotationRepository,
    quotation_repository,
    AbstractSalesOrderRepository,
    sales_order_repository,
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
from app.modules.warehouse.repository import warehouse_repository
from app.modules.warehouse.schemas import WarehouseStatus
from app.modules.accounting.tax_calculation import tax_calculation_service
from app.modules.accounting.schemas import TaxSnapshot, TaxConfigurationInDB, PricingMode, TaxTreatment
from app.modules.accounting.repository import accounting_repository


QUOTATION_INVALID_STATUS = "QUOTATION_INVALID_STATUS"
QUOTATION_ALREADY_CONVERTED = "QUOTATION_ALREADY_CONVERTED"
QUOTATION_NOT_FOUND = "QUOTATION_NOT_FOUND"


class QuotationService:
    def __init__(
        self,
        quotation_repo: AbstractQuotationRepository = quotation_repository,
        sales_order_repo: AbstractSalesOrderRepository = sales_order_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        session: Optional[AsyncSession] = None,
    ):
        self.quotation_repo = quotation_repo
        self.sales_order_repo = sales_order_repo
        self.membership_service = membership_service
        self.session = session

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

    async def _validate_warehouse(self, business_id: str, warehouse_id: str):
        warehouse = await warehouse_repository.get_by_id(warehouse_id)
        if not warehouse or warehouse.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warehouse not found in this business.",
            )
        if warehouse.status != WarehouseStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Warehouse is not ACTIVE (current: {warehouse.status}).",
            )
        return warehouse

    async def _validate_product_and_variant(
        self, business_id: str, product_id: Optional[str], variant_id: Optional[str]
    ) -> tuple[str, Optional[str]]:
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
                detail="Line must specify product_id or variant_id.",
            )

    def _is_terminal(self, s: QuotationStatus) -> bool:
        return s in (QuotationStatus.REJECTED, QuotationStatus.EXPIRED, QuotationStatus.CANCELLED, QuotationStatus.CONVERTED)

    def _validate_transition(self, current: QuotationStatus, target: QuotationStatus) -> bool:
        transitions = {
            QuotationStatus.DRAFT: {QuotationStatus.SENT, QuotationStatus.CANCELLED},
            QuotationStatus.SENT: {QuotationStatus.ACCEPTED, QuotationStatus.REJECTED, QuotationStatus.EXPIRED, QuotationStatus.CANCELLED},
            QuotationStatus.ACCEPTED: {QuotationStatus.CONVERTED},
        }
        return target in transitions.get(current, set())

    async def _recalculate_totals(self, business_id: str, quotation_id: str):
        lines = await self.quotation_repo.list_lines_for_quotation(quotation_id)
        subtotal = Decimal("0")
        discount_total = Decimal("0")
        tax_total = Decimal("0")
        for l in lines:
            subtotal += l.line_subtotal
            discount_total += l.discount_amount
            tax_total += l.tax_amount
        grand_total = subtotal - discount_total + tax_total
        await self.quotation_repo.update_quotation(
            quotation_id=quotation_id,
            business_id=business_id,
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            grand_total=grand_total,
        )

    async def _build_response(self, business_id: str, q: QuotationInDB) -> QuotationResponse:
        lines = await self.quotation_repo.list_lines_for_quotation(q.id)
        return QuotationResponse(**q.model_dump(), lines=lines)

    async def create_quotation(self, business_id: str, user_id: str, payload: QuotationCreate) -> QuotationResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._create_quotation_with_retry(business_id, user_id, payload)
        else:
            return await self._create_quotation_with_retry(business_id, user_id, payload)

    async def _create_quotation_with_retry(self, business_id: str, user_id: str, payload: QuotationCreate) -> QuotationResponse:
        for attempt in range(3):
            try:
                if self.session is not None:
                    async with self.session.begin_nested():
                        return await self._create_quotation_impl(business_id, user_id, payload)
                else:
                    return await self._create_quotation_impl(business_id, user_id, payload)
            except Exception as e:
                err_str = str(e).lower()
                if ("unique" in err_str and ("quotation_number" in err_str or "uq_quotation" in err_str)) and attempt < 2:
                    continue
                raise
        raise HTTPException(status_code=409, detail="Document number collision; please retry")

    async def _create_quotation_impl(self, business_id: str, user_id: str, payload: QuotationCreate) -> QuotationResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        await self._validate_customer(business_id, payload.customer_id)
        await self._validate_branch(business_id, payload.branch_id)
        await self._validate_warehouse(business_id, payload.warehouse_id)

        seq = await self.quotation_repo.get_next_quotation_sequence(business_id)
        quotation_number = f"QT-{seq:06d}"

        q = await self.quotation_repo.create_quotation(
            business_id=business_id,
            customer_id=payload.customer_id,
            branch_id=payload.branch_id,
            warehouse_id=payload.warehouse_id,
            quotation_number=quotation_number,
            quotation_date=payload.quotation_date,
            validity_date=payload.validity_date,
            created_by_user_id=user_id,
            notes=payload.notes,
        )
        return await self._build_response(business_id, q)

    async def list_quotations(
        self,
        business_id: str,
        user_id: str,
        status: Optional[QuotationStatus] = None,
        customer_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> QuotationListResponse:
        await self._validate_access(business_id, user_id)
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20
        items, total = await self.quotation_repo.list_quotations(
            business_id=business_id, status=status, customer_id=customer_id,
            branch_id=branch_id, search=search, page=page, page_size=page_size,
        )
        responses = [await self._build_response(business_id, q) for q in items]
        return QuotationListResponse(items=responses, page=page, page_size=page_size, total=total)

    async def get_quotation(self, business_id: str, quotation_id: str, user_id: str) -> QuotationResponse:
        await self._validate_access(business_id, user_id)
        q = await self.quotation_repo.get_quotation_by_id(quotation_id, business_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        return await self._build_response(business_id, q)

    async def update_quotation(self, business_id: str, quotation_id: str, user_id: str, payload: QuotationUpdate) -> QuotationResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        q = await self.quotation_repo.get_quotation_by_id(quotation_id, business_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        if self._is_terminal(q.status):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot modify a {q.status.value} quotation.")
        if payload.customer_id is not None:
            await self._validate_customer(business_id, payload.customer_id)
        if payload.branch_id is not None:
            await self._validate_branch(business_id, payload.branch_id)
        if payload.warehouse_id is not None:
            await self._validate_warehouse(business_id, payload.warehouse_id)
        updated = await self.quotation_repo.update_quotation(
            quotation_id=quotation_id, business_id=business_id,
            customer_id=payload.customer_id, branch_id=payload.branch_id,
            warehouse_id=payload.warehouse_id, quotation_date=payload.quotation_date,
            validity_date=payload.validity_date, notes=payload.notes,
        )
        return await self._build_response(business_id, updated)

    async def add_line(self, business_id: str, quotation_id: str, user_id: str, payload: QuotationLineCreate) -> QuotationLineResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        q = await self.quotation_repo.get_quotation_by_id(quotation_id, business_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        if q.status not in (QuotationStatus.DRAFT,):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot add lines to non-DRAFT quotation.")
        resolved_product_id, resolved_variant_id = await self._validate_product_and_variant(business_id, payload.product_id, payload.variant_id)
        # Feature #64: Server-authoritative discount evaluation
        from app.modules.pricing.service import PricingService
        from datetime import datetime, timezone as tz
        from decimal import Decimal as D
        pricing_svc = PricingService()
        auto_discount, rule_id, rule_name = await pricing_svc.evaluate_discount(
            business_id=business_id,
            product_id=resolved_product_id,
            variant_id=resolved_variant_id,
            quantity=payload.quantity,
            unit_price=payload.unit_price,
            transaction_currency="IDR",
            evaluation_time=datetime.now(tz.utc),
        )
        if auto_discount > D("0"):
            final_discount = auto_discount
            final_rule_id = rule_id
            final_rule_name = rule_name
        else:
            final_discount = payload.discount_amount
            final_rule_id = None
            final_rule_name = None
        line_subtotal = payload.quantity * payload.unit_price
        line_total = line_subtotal - final_discount + payload.tax_amount
        line = await self.quotation_repo.create_line(
            quotation_id=quotation_id, product_id=resolved_product_id, variant_id=resolved_variant_id,
            description=payload.description, quantity=payload.quantity, unit_price=payload.unit_price,
            discount_amount=final_discount, tax_amount=payload.tax_amount,
            line_subtotal=line_subtotal, line_total=line_total,
            discount_rule_id=final_rule_id, discount_rule_name_snapshot=final_rule_name,
        )
        await self._recalculate_totals(business_id, quotation_id)
        return QuotationLineResponse(**line.model_dump())

    async def update_line(self, business_id: str, quotation_id: str, line_id: str, user_id: str, payload: QuotationLineUpdate) -> QuotationLineResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        q = await self.quotation_repo.get_quotation_by_id(quotation_id, business_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        if q.status != QuotationStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify lines of non-DRAFT quotation.")
        line = await self.quotation_repo.get_line_by_id(line_id, quotation_id)
        if not line:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation line not found.")
        target_product_id = payload.product_id if payload.product_id is not None else line.product_id
        target_variant_id = payload.variant_id if payload.variant_id is not None else line.variant_id
        if payload.product_id is not None or payload.variant_id is not None:
            resolved_product_id, resolved_variant_id = await self._validate_product_and_variant(business_id, target_product_id, target_variant_id)
        else:
            resolved_product_id, resolved_variant_id = target_product_id, target_variant_id
        target_qty = payload.quantity if payload.quantity is not None else line.quantity
        target_price = payload.unit_price if payload.unit_price is not None else line.unit_price
        target_disc = payload.discount_amount if payload.discount_amount is not None else line.discount_amount
        target_tax = payload.tax_amount if payload.tax_amount is not None else line.tax_amount
        # Feature #64: Server-authoritative discount evaluation on update
        from app.modules.pricing.service import PricingService
        from datetime import datetime, timezone as tz
        from decimal import Decimal as D
        pricing_svc = PricingService()
        auto_discount, rule_id, rule_name = await pricing_svc.evaluate_discount(
            business_id=business_id,
            product_id=resolved_product_id,
            variant_id=resolved_variant_id,
            quantity=target_qty,
            unit_price=target_price,
            transaction_currency="IDR",
            evaluation_time=datetime.now(tz.utc),
        )
        if auto_discount > D("0"):
            final_discount = auto_discount
            final_rule_id = rule_id
            final_rule_name = rule_name
        else:
            final_discount = target_disc
            final_rule_id = None
            final_rule_name = None
        line_subtotal = target_qty * target_price
        line_total = line_subtotal - final_discount + target_tax
        updated_line = await self.quotation_repo.update_line(
            line_id=line_id, quotation_id=quotation_id,
            product_id=resolved_product_id, variant_id=resolved_variant_id,
            description=payload.description, quantity=payload.quantity,
            unit_price=payload.unit_price, discount_amount=final_discount,
            tax_amount=payload.tax_amount, line_subtotal=line_subtotal, line_total=line_total,
            discount_rule_id=final_rule_id, discount_rule_name_snapshot=final_rule_name,
        )
        await self._recalculate_totals(business_id, quotation_id)
        return QuotationLineResponse(**updated_line.model_dump())

    async def delete_line(self, business_id: str, quotation_id: str, line_id: str, user_id: str) -> dict:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        q = await self.quotation_repo.get_quotation_by_id(quotation_id, business_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        if q.status != QuotationStatus.DRAFT:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot modify lines of non-DRAFT quotation.")
        success = await self.quotation_repo.delete_line(line_id, quotation_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation line not found.")
        await self._recalculate_totals(business_id, quotation_id)
        return {"message": "Quotation line successfully deleted."}

    async def send_quotation(self, business_id: str, quotation_id: str, user_id: str) -> QuotationResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._send_quotation_impl(business_id, quotation_id, user_id)
        else:
            return await self._send_quotation_impl(business_id, quotation_id, user_id)

    async def _send_quotation_impl(self, business_id: str, quotation_id: str, user_id: str) -> QuotationResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        q = await self.quotation_repo.get_quotation_by_id(quotation_id, business_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        if not self._validate_transition(q.status, QuotationStatus.SENT):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot send a {q.status.value} quotation.")
        lines = await self.quotation_repo.list_lines_for_quotation(quotation_id)
        if not lines:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot send quotation without lines.")
        await self._recalculate_totals(business_id, quotation_id)
        now = datetime.now(timezone.utc)
        updated = await self.quotation_repo.update_quotation(
            quotation_id=quotation_id, business_id=business_id,
            status=QuotationStatus.SENT, sent_by_user_id=user_id, sent_at=now,
        )
        return await self._build_response(business_id, updated)

    async def accept_quotation(self, business_id: str, quotation_id: str, user_id: str) -> QuotationResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._accept_quotation_impl(business_id, quotation_id, user_id)
        else:
            return await self._accept_quotation_impl(business_id, quotation_id, user_id)

    async def _accept_quotation_impl(self, business_id: str, quotation_id: str, user_id: str) -> QuotationResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        q = await self.quotation_repo.get_quotation_by_id(quotation_id, business_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        if not self._validate_transition(q.status, QuotationStatus.ACCEPTED):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot accept a {q.status.value} quotation.")
        now = datetime.now(timezone.utc)
        updated = await self.quotation_repo.update_quotation(
            quotation_id=quotation_id, business_id=business_id,
            status=QuotationStatus.ACCEPTED, accepted_by_user_id=user_id, accepted_at=now,
        )
        return await self._build_response(business_id, updated)

    async def reject_quotation(self, business_id: str, quotation_id: str, user_id: str) -> QuotationResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._reject_quotation_impl(business_id, quotation_id, user_id)
        else:
            return await self._reject_quotation_impl(business_id, quotation_id, user_id)

    async def _reject_quotation_impl(self, business_id: str, quotation_id: str, user_id: str) -> QuotationResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        q = await self.quotation_repo.get_quotation_by_id(quotation_id, business_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        if not self._validate_transition(q.status, QuotationStatus.REJECTED):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot reject a {q.status.value} quotation.")
        now = datetime.now(timezone.utc)
        updated = await self.quotation_repo.update_quotation(
            quotation_id=quotation_id, business_id=business_id,
            status=QuotationStatus.REJECTED, rejected_by_user_id=user_id, rejected_at=now,
        )
        return await self._build_response(business_id, updated)

    async def cancel_quotation(self, business_id: str, quotation_id: str, user_id: str) -> QuotationResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._cancel_quotation_impl(business_id, quotation_id, user_id)
        else:
            return await self._cancel_quotation_impl(business_id, quotation_id, user_id)

    async def _cancel_quotation_impl(self, business_id: str, quotation_id: str, user_id: str) -> QuotationResponse:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        q = await self.quotation_repo.get_quotation_by_id(quotation_id, business_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        if self._is_terminal(q.status):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot cancel a {q.status.value} quotation.")
        if q.status not in (QuotationStatus.DRAFT, QuotationStatus.SENT):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot cancel a {q.status.value} quotation.")
        now = datetime.now(timezone.utc)
        updated = await self.quotation_repo.update_quotation(
            quotation_id=quotation_id, business_id=business_id,
            status=QuotationStatus.CANCELLED, cancelled_by_user_id=user_id, cancelled_at=now,
        )
        return await self._build_response(business_id, updated)

    async def convert_quotation(self, business_id: str, quotation_id: str, user_id: str, payload: QuotationConvert) -> dict:
        if self.session is not None:
            async with self.session.begin():
                return await self._convert_quotation_impl(business_id, quotation_id, user_id, payload)
        else:
            return await self._convert_quotation_impl(business_id, quotation_id, user_id, payload)

    async def _convert_quotation_impl(self, business_id: str, quotation_id: str, user_id: str, payload: QuotationConvert) -> dict:
        await self._validate_access(business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN))
        q = await self.quotation_repo.get_quotation_by_id(quotation_id, business_id)
        if not q:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found.")
        if q.status == QuotationStatus.CONVERTED:
            if q.converted_sales_order_id:
                return {"sales_order_id": q.converted_sales_order_id, "message": "Quotation already converted."}
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quotation already converted.")
        if q.status != QuotationStatus.ACCEPTED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot convert a {q.status.value} quotation.")

        now = datetime.now(timezone.utc)
        seq = await self.sales_order_repo.get_next_order_sequence(business_id)
        sales_order_number = f"SO-{seq:06d}"

        order = await self.sales_order_repo.create_order(
            business_id=business_id,
            customer_id=q.customer_id,
            branch_id=q.branch_id,
            warehouse_id=q.warehouse_id,
            sales_order_number=sales_order_number,
            order_date=now,
            created_by_user_id=user_id,
            notes=payload.notes,
        )

        quotation_lines = await self.quotation_repo.list_lines_for_quotation(quotation_id)
        for ql in quotation_lines:
            line_subtotal = ql.quantity * ql.unit_price
            line_total = line_subtotal - ql.discount_amount + ql.tax_amount
            await self.sales_order_repo.create_line(
                sales_order_id=order.id,
                product_id=ql.product_id,
                variant_id=ql.variant_id,
                description=ql.description,
                quantity_ordered=ql.quantity,
                unit_price=ql.unit_price,
                discount_amount=ql.discount_amount,
                tax_amount=ql.tax_amount,
                line_subtotal=line_subtotal,
                line_total=line_total,
                discount_rule_id=getattr(ql, 'discount_rule_id', None),
                discount_rule_name_snapshot=getattr(ql, 'discount_rule_name_snapshot', None),
            )

        updated_q = await self.quotation_repo.update_quotation(
            quotation_id=quotation_id, business_id=business_id,
            status=QuotationStatus.CONVERTED, converted_at=now, converted_sales_order_id=order.id,
        )

        return {"sales_order_id": order.id, "sales_order_number": sales_order_number, "message": "Quotation converted to Sales Order."}


quotation_service = QuotationService()
