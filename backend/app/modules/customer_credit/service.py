from typing import Optional
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.customer_credit.schemas import (
    CreditLimitUpdate,
    StoreCreditAdjust,
    CustomerCreditSummaryResponse,
    CreditExposureResponse,
    StoreCreditLedgerResponse,
    StoreCreditLedgerEntry,
)
from app.modules.customer_credit.repository import (
    AbstractStoreCreditLedgerRepository,
    store_credit_ledger_repository,
)
from app.modules.customer.repository import (
    AbstractCustomerRepository,
    customer_repository,
    CustomerInDB,
)
from app.modules.business_membership.service import (
    BusinessMembershipService,
    business_membership_service,
)
from app.modules.business_membership.schemas import BusinessMembershipRole
from app.modules.sales.repository import sales_repository
from app.modules.sales.schemas import SalesStatus
from app.modules.payment.repository import payment_repository
from app.modules.payment.schemas import PaymentTargetType, PaymentStatus
from app.modules.sales_return.repository import sales_return_repository
from app.modules.sales_return.schemas import SalesReturnStatus


class CustomerCreditService:
    def __init__(
        self,
        customer_repo: AbstractCustomerRepository = customer_repository,
        ledger_repo: AbstractStoreCreditLedgerRepository = store_credit_ledger_repository,
        membership_service: BusinessMembershipService = business_membership_service,
        session: Optional[AsyncSession] = None,
    ):
        self.customer_repo = customer_repo
        self.ledger_repo = ledger_repo
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

    async def _verify_ledger_reconciliation(
        self,
        customer_id: str,
        business_id: str,
        cached_balance: Decimal,
    ) -> None:
        """
        Feature #61: Verify that customer.store_credit_balance matches
        sum(issued_not_voided) - sum(redeemed_not_voided).

        Fail closed without mutating history if they diverge.
        Called both pre-mutation (before any mutation) and post-mutation
        (after mutation + ledger append).
        """
        issued = await self.ledger_repo.sum_issued_not_voided(customer_id, business_id)
        redeemed = await self.ledger_repo.sum_redeemed_not_voided(customer_id, business_id)
        derived = issued - redeemed
        if cached_balance != derived:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Store credit ledger integrity violation. "
                    f"Cached balance: {cached_balance}, "
                    f"Ledger-derived balance (issued={issued} - redeemed={redeemed}): {derived}. "
                    f"Operation aborted. No state was modified."
                ),
            )

    async def _get_customer_or_404(self, customer_id: str, business_id: str) -> CustomerInDB:
        customer = await self.customer_repo.get_by_id(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )
        return customer

    async def set_credit_limit(
        self,
        business_id: str,
        user_id: str,
        customer_id: str,
        payload: CreditLimitUpdate,
    ) -> CustomerCreditSummaryResponse:
        await self._validate_access(
            business_id, user_id,
            required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN),
        )
        customer = await self._get_customer_or_404(customer_id, business_id)

        updated = await self.customer_repo.update_credit_fields(
            customer_id=customer_id,
            business_id=business_id,
            credit_limit=payload.credit_limit,
        )

        return await self._build_summary(business_id, updated)

    async def issue_store_credit(
        self,
        business_id: str,
        user_id: str,
        customer_id: str,
        payload: StoreCreditAdjust,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> CustomerCreditSummaryResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._issue_store_credit_impl(business_id, user_id, customer_id, payload, reference_type, reference_id)
        else:
            return await self._issue_store_credit_impl(business_id, user_id, customer_id, payload, reference_type, reference_id)

    async def _issue_store_credit_impl(
        self,
        business_id: str,
        user_id: str,
        customer_id: str,
        payload: StoreCreditAdjust,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> CustomerCreditSummaryResponse:
        await self._validate_access(
            business_id, user_id,
            required_roles=(BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN),
        )
        customer = await self.customer_repo.get_by_id_for_update(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

        # PRE-MUTATION RECONCILIATION — fail closed if cached balance diverges from ledger
        await self._verify_ledger_reconciliation(customer_id, business_id, customer.store_credit_balance)

        new_balance = customer.store_credit_balance + payload.amount
        updated = await self.customer_repo.update_credit_fields(
            customer_id=customer_id,
            business_id=business_id,
            store_credit_balance=new_balance,
        )

        await self.ledger_repo.append(
            customer_id=customer_id,
            business_id=business_id,
            amount=payload.amount,
            balance_after=new_balance,
            direction="ISSUED",
            reference_type=reference_type,
            reference_id=reference_id,
            reason=payload.reason,
            created_by_user_id=user_id,
        )

        # POST-MUTATION RECONCILIATION — let snapshot/restore handle failure
        updated_customer = await self.customer_repo.get_by_id(customer_id, business_id)
        await self._verify_ledger_reconciliation(customer_id, business_id, updated_customer.store_credit_balance)

        return await self._build_summary(business_id, updated)

    async def redeem_store_credit(
        self,
        business_id: str,
        user_id: str,
        customer_id: str,
        amount: Decimal,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> CustomerCreditSummaryResponse:
        if self.session is not None:
            async with self.session.begin():
                return await self._redeem_store_credit_impl(business_id, user_id, customer_id, amount, reference_type, reference_id)
        else:
            return await self._redeem_store_credit_impl(business_id, user_id, customer_id, amount, reference_type, reference_id)

    async def _redeem_store_credit_impl(
        self,
        business_id: str,
        user_id: str,
        customer_id: str,
        amount: Decimal,
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
    ) -> CustomerCreditSummaryResponse:
        customer = await self.customer_repo.get_by_id_for_update(customer_id, business_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

        # PRE-MUTATION RECONCILIATION — fail closed if cached balance diverges from ledger
        await self._verify_ledger_reconciliation(customer_id, business_id, customer.store_credit_balance)

        if customer.store_credit_balance < amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient store credit balance. Available: {customer.store_credit_balance}, requested: {amount}.",
            )

        new_balance = customer.store_credit_balance - amount
        updated = await self.customer_repo.update_credit_fields(
            customer_id=customer_id,
            business_id=business_id,
            store_credit_balance=new_balance,
        )

        await self.ledger_repo.append(
            customer_id=customer_id,
            business_id=business_id,
            amount=amount,
            balance_after=new_balance,
            direction="REDEEMED",
            reference_type=reference_type,
            reference_id=reference_id,
            reason=None,
            created_by_user_id=user_id,
        )

        # POST-MUTATION RECONCILIATION — let snapshot/restore handle failure
        updated_customer = await self.customer_repo.get_by_id(customer_id, business_id)
        await self._verify_ledger_reconciliation(customer_id, business_id, updated_customer.store_credit_balance)

        return await self._build_summary(business_id, updated)

    async def get_credit_exposure(
        self,
        business_id: str,
        user_id: str,
        customer_id: str,
    ) -> CreditExposureResponse:
        await self._validate_access(business_id, user_id)
        customer = await self._get_customer_or_404(customer_id, business_id)

        receivable = await self._compute_receivable_exposure(business_id, customer_id)
        exposure = receivable - customer.store_credit_balance
        if exposure < Decimal("0"):
            exposure = Decimal("0")
        available = customer.credit_limit - exposure
        if available < Decimal("0"):
            available = Decimal("0")

        return CreditExposureResponse(
            customer_id=customer_id,
            business_id=business_id,
            credit_limit=customer.credit_limit,
            total_receivable=receivable,
            exposure=exposure,
            available_credit=available,
        )

    async def get_credit_summary(
        self,
        business_id: str,
        user_id: str,
        customer_id: str,
    ) -> CustomerCreditSummaryResponse:
        await self._validate_access(business_id, user_id)
        customer = await self._get_customer_or_404(customer_id, business_id)
        return await self._build_summary(business_id, customer)

    async def get_store_credit_ledger(
        self,
        business_id: str,
        user_id: str,
        customer_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> StoreCreditLedgerResponse:
        await self._validate_access(business_id, user_id)
        await self._get_customer_or_404(customer_id, business_id)

        items, total = await self.ledger_repo.list_by_customer(
            customer_id=customer_id,
            business_id=business_id,
            page=page,
            page_size=page_size,
        )

        return StoreCreditLedgerResponse(items=items, total=total)

    async def check_credit_limit_for_sales(
        self,
        business_id: str,
        customer_id: str,
        sales_grand_total: Decimal,
        sales_id: Optional[str] = None,
    ) -> None:
        """Called during sales finalization to enforce credit limit."""
        if not customer_id:
            return

        customer = await self.customer_repo.get_by_id(customer_id, business_id)
        if not customer:
            return

        receivable = await self._compute_receivable_exposure(business_id, customer_id)
        current_exposure = receivable - customer.store_credit_balance
        if current_exposure < Decimal("0"):
            current_exposure = Decimal("0")

        # Account for payments already made against THIS sale (if any)
        this_sale_outstanding = sales_grand_total
        if sales_id:
            active_paid = await payment_repository.get_active_payments_total_for_target(
                business_id=business_id,
                target_type=PaymentTargetType.SALES,
                target_id=sales_id,
            )
            this_sale_outstanding = sales_grand_total - active_paid
            if this_sale_outstanding < Decimal("0"):
                this_sale_outstanding = Decimal("0")

        projected_receivable = receivable + this_sale_outstanding
        projected_exposure = projected_receivable - customer.store_credit_balance
        if projected_exposure < Decimal("0"):
            projected_exposure = Decimal("0")

        if customer.credit_limit <= Decimal("0"):
            if projected_exposure > Decimal("0"):
                # Send warning notification before rejection
                try:
                    from app.modules.notification.service import _send_notification
                    from app.modules.notification.schemas import (
                        NotificationScope, NotificationType, NotificationSeverity,
                    )
                    from app.modules.business_membership.repository import (
                        business_membership_repository,
                    )
                    from app.modules.business_membership.schemas import (
                        BusinessMembershipRole, BusinessMembershipStatus,
                    )

                    owner_admin_ids = [
                        m.user_id
                        for m in business_membership_repository._memberships.values()
                        if m.business_id == business_id
                        and m.status == BusinessMembershipStatus.ACTIVE
                        and m.role in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
                    ]
                    for member_id in owner_admin_ids:
                        await _send_notification(
                            recipient_id=member_id,
                            scope=NotificationScope.TENANT,
                            notif_type=NotificationType.CUSTOMER_CREDIT_LIMIT_WARNING,
                            severity=NotificationSeverity.WARNING,
                            title="Credit Limit Warning",
                            message=f"Customer {customer.name} is near credit limit.",
                            business_id=business_id,
                            metadata={
                                "customer_id": customer_id,
                                "customer_name": customer.name,
                                "credit_limit": str(customer.credit_limit),
                                "exposure": str(projected_exposure),
                                "sale_id": sales_id,
                            },
                            deduplication_key=f"CREDIT_WARNING:{customer_id}:{sales_id}:{member_id}",
                        )
                except Exception:
                    pass

                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Credit limit exceeded. Limit: {customer.credit_limit}, "
                        f"current exposure: {current_exposure}, this sale: {sales_grand_total}, "
                        f"projected: {projected_exposure}."
                    ),
                )
            return

        if projected_exposure > customer.credit_limit:
            # Send warning notification before rejection
            try:
                from app.modules.notification.service import _send_notification
                from app.modules.notification.schemas import (
                    NotificationScope, NotificationType, NotificationSeverity,
                )
                from app.modules.business_membership.repository import (
                    business_membership_repository,
                )
                from app.modules.business_membership.schemas import (
                    BusinessMembershipRole, BusinessMembershipStatus,
                )

                owner_admin_ids = [
                    m.user_id
                    for m in business_membership_repository._memberships.values()
                    if m.business_id == business_id
                    and m.status == BusinessMembershipStatus.ACTIVE
                    and m.role in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
                ]
                for member_id in owner_admin_ids:
                    await _send_notification(
                        recipient_id=member_id,
                        scope=NotificationScope.TENANT,
                        notif_type=NotificationType.CUSTOMER_CREDIT_LIMIT_WARNING,
                        severity=NotificationSeverity.WARNING,
                        title="Credit Limit Warning",
                        message=f"Customer {customer.name} is near credit limit.",
                        business_id=business_id,
                        metadata={
                            "customer_id": customer_id,
                            "customer_name": customer.name,
                            "credit_limit": str(customer.credit_limit),
                            "exposure": str(projected_exposure),
                            "sale_id": sales_id,
                        },
                        deduplication_key=f"CREDIT_WARNING:{customer_id}:{sales_id}:{member_id}",
                    )
            except Exception:
                pass

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Credit limit exceeded. Limit: {customer.credit_limit}, "
                    f"current exposure: {current_exposure}, this sale: {sales_grand_total}, "
                    f"projected: {projected_exposure}."
                ),
            )

    async def _compute_receivable_exposure(
        self, business_id: str, customer_id: str
    ) -> Decimal:
        """Sum of outstanding amounts across all finalized sales for this customer."""
        all_sales, _ = await sales_repository.list_sales(
            business_id=business_id,
            customer_id=customer_id,
            status=SalesStatus.FINALIZED,
            page=1,
            page_size=10000,
        )

        total_outstanding = Decimal("0")
        for s in all_sales:
            active_paid = await payment_repository.get_active_payments_total_for_target(
                business_id=business_id,
                target_type=PaymentTargetType.SALES,
                target_id=s.id,
            )
            outstanding = s.grand_total - active_paid
            if outstanding > Decimal("0"):
                total_outstanding += outstanding

        return total_outstanding

    async def _build_summary(
        self, business_id: str, customer: CustomerInDB
    ) -> CustomerCreditSummaryResponse:
        receivable = await self._compute_receivable_exposure(business_id, customer.id)
        exposure = receivable - customer.store_credit_balance
        if exposure < Decimal("0"):
            exposure = Decimal("0")
        available = customer.credit_limit - exposure
        if available < Decimal("0"):
            available = Decimal("0")

        return CustomerCreditSummaryResponse(
            customer_id=customer.id,
            business_id=business_id,
            credit_limit=customer.credit_limit,
            total_receivable=receivable,
            exposure=exposure,
            available_credit=available,
            store_credit_balance=customer.store_credit_balance,
        )


customer_credit_service = CustomerCreditService()
