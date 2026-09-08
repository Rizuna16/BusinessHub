from typing import Optional
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.modules.sales_payment.schemas import (
    SalesPaymentInDB,
    SalesPaymentResponse,
    SalesPaymentListResponse,
    SalesPaymentSummary,
    SalesPaymentCreate,
    PaymentStatus,
)
from app.modules.sales_payment.repository import (
    AbstractSalesPaymentRepository,
    sales_payment_repository,
)
from app.modules.sales.repository import (
    AbstractSalesRepository,
    sales_repository,
)
from app.modules.sales.schemas import SalesStatus
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole


class SalesPaymentService:
    def __init__(
        self,
        payment_repo: AbstractSalesPaymentRepository = sales_payment_repository,
        sales_repo: AbstractSalesRepository = sales_repository,
        membership_service: BusinessMembershipService = business_membership_service,
    ):
        self.payment_repo = payment_repo
        self.sales_repo = sales_repo
        self.membership_service = membership_service

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

    async def _get_validated_sales(self, business_id: str, sales_id: str):
        sales = await self.sales_repo.get_sales_by_id(sales_id, business_id)
        if not sales or sales.business_id != business_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sales not found.",
            )
        return sales

    async def create_payment(
        self,
        business_id: str,
        sales_id: str,
        user_id: str,
        payload: SalesPaymentCreate,
    ) -> SalesPaymentResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        sales = await self._get_validated_sales(business_id, sales_id)

        if sales.status == SalesStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot record payment against DRAFT sales.",
            )
        if sales.status == SalesStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot record payment against CANCELLED sales.",
            )
        if sales.status != SalesStatus.FINALIZED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sales must be FINALIZED to receive payment.",
            )

        if payload.amount <= Decimal("0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount must be greater than 0.",
            )

        active_paid = await self.payment_repo.get_active_payments_total(business_id, sales_id)
        remaining = sales.grand_total - active_paid

        if payload.amount > remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount ({payload.amount}) exceeds remaining balance ({remaining}).",
            )

        payment_date = payload.payment_date or datetime.now(timezone.utc)
        seq = await self.payment_repo.get_next_payment_sequence(business_id)
        payment_number = f"PAY-{seq:06d}"

        payment = await self.payment_repo.create_payment(
            business_id=business_id,
            sales_id=sales_id,
            payment_number=payment_number,
            payment_date=payment_date,
            payment_method=payload.payment_method,
            amount=payload.amount,
            created_by_user_id=user_id,
            reference_number=payload.reference_number,
            notes=payload.notes,
        )

        return SalesPaymentResponse(**payment.model_dump())

    async def list_payments(
        self,
        business_id: str,
        sales_id: str,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> SalesPaymentListResponse:
        await self._validate_access(business_id, user_id)
        sales = await self._get_validated_sales(business_id, sales_id)

        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        payments, total = await self.payment_repo.list_payments_for_sales(
            business_id=business_id,
            sales_id=sales_id,
            page=page,
            page_size=page_size,
        )

        active_paid = await self.payment_repo.get_active_payments_total(business_id, sales_id)
        remaining = sales.grand_total - active_paid

        summary = SalesPaymentSummary(
            total_paid=active_paid,
            remaining_amount=remaining,
            grand_total=sales.grand_total,
        )

        items = [SalesPaymentResponse(**p.model_dump()) for p in payments]
        return SalesPaymentListResponse(
            items=items,
            summary=summary,
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get_payment(
        self,
        business_id: str,
        sales_id: str,
        payment_id: str,
        user_id: str,
    ) -> SalesPaymentResponse:
        await self._validate_access(business_id, user_id)
        await self._get_validated_sales(business_id, sales_id)

        payment = await self.payment_repo.get_payment_by_id(payment_id, business_id)
        if not payment or payment.sales_id != sales_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found.",
            )

        return SalesPaymentResponse(**payment.model_dump())

    async def cancel_payment(
        self,
        business_id: str,
        sales_id: str,
        payment_id: str,
        user_id: str,
    ) -> SalesPaymentResponse:
        await self._validate_access(
            business_id, user_id, required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        )
        await self._get_validated_sales(business_id, sales_id)

        payment = await self.payment_repo.get_payment_by_id(payment_id, business_id)
        if not payment or payment.sales_id != sales_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found.",
            )

        if payment.status == PaymentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment is already CANCELLED.",
            )

        now = datetime.now(timezone.utc)
        cancelled = await self.payment_repo.cancel_payment(
            payment_id=payment_id,
            business_id=business_id,
            cancelled_by_user_id=user_id,
            cancelled_at=now,
        )

        return SalesPaymentResponse(**cancelled.model_dump())


sales_payment_service = SalesPaymentService()
