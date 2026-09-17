from typing import List, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid as uuid_mod
from fastapi import HTTPException, status

from app.modules.subscription.schemas import (
    SubscriptionInDB, SubscriptionResponse, SubscriptionStatus,
    SubscriptionOverrideInput, BillingInterval,
    SubscriptionPlan, PlanCreate, PlanUpdate, PlanResponse,
    BillingPeriod, BillingPeriodStatus, BillingPeriodResponse,
    PaymentAttempt, PaymentAttemptStatus, PaymentAttemptResponse,
)
from app.modules.subscription.repository import AbstractSubscriptionRepository, subscription_repository


def _get_notification_service():
    try:
        from app.modules.notification.service import notification_service
        from app.modules.notification.schemas import (
            NotificationScope, NotificationType, NotificationSeverity
        )
        return notification_service, NotificationScope, NotificationType, NotificationSeverity
    except ImportError:
        return None, None, None, None


def _get_super_admin_ids():
    try:
        from app.modules.authentication.repository import user_repository
        from app.modules.authentication.schemas import PlatformRole
        return [
            u.id
            for u in user_repository._users.values()
            if u.is_active and u.platform_role == PlatformRole.SUPER_ADMIN
        ]
    except Exception:
        return []


def _get_owner_admin_ids(business_id: str):
    try:
        from app.modules.business_membership.repository import business_membership_repository
        from app.modules.business_membership.schemas import (
            BusinessMembershipRole, BusinessMembershipStatus
        )
        return [
            m.user_id
            for m in business_membership_repository._memberships.values()
            if m.business_id == business_id
            and m.status == BusinessMembershipStatus.ACTIVE
            and m.role in (BusinessMembershipRole.OWNER, BusinessMembershipRole.ADMIN)
        ]
    except Exception:
        return []


class SubscriptionService:
    def __init__(self, repository: AbstractSubscriptionRepository = subscription_repository):
        self.repository = repository

    async def create_default_subscription(self, business_id: str) -> SubscriptionInDB:
        return await self.repository.create_default(business_id)

    async def get_by_id(self, subscription_id: str) -> Optional[SubscriptionInDB]:
        return await self.repository.get_by_id(subscription_id)

    async def get_by_business_id(self, business_id: str) -> Optional[SubscriptionInDB]:
        return await self.repository.get_by_business_id(business_id)

    async def list_all(self, status_filter: Optional[SubscriptionStatus] = None) -> List[SubscriptionResponse]:
        subs = await self.repository.list_all()
        if status_filter:
            subs = [s for s in subs if s.status == status_filter]
        return [SubscriptionResponse.model_validate(s) for s in subs]

    async def count(self) -> int:
        return await self.repository.count()

    async def override_subscription(
        self, subscription_id: str, override: SubscriptionOverrideInput
    ) -> SubscriptionInDB:
        sub = await self.repository.get_by_id(subscription_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found."
            )

        if override.action == "EXTEND":
            if override.extend_days is None or override.extend_days <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="extend_days must be a positive integer for EXTEND action."
                )
            sub.current_period_end = sub.current_period_end + timedelta(days=override.extend_days)
            if sub.status in (SubscriptionStatus.EXPIRED, SubscriptionStatus.PAST_DUE, SubscriptionStatus.SUSPENDED):
                sub.status = SubscriptionStatus.ACTIVE
        elif override.action == "SET_STATUS":
            if override.status is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="status is required for SET_STATUS action."
                )
            if not self._is_valid_transition(sub.status, override.status):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid subscription status transition: {sub.status.value} -> {override.status.value}"
                )
            sub.status = override.status
            if override.status == SubscriptionStatus.CANCELLED:
                sub.cancelled_at = datetime.now(timezone.utc)

        return await self.repository.update(sub)

    def _is_valid_transition(self, from_status: SubscriptionStatus, to_status: SubscriptionStatus) -> bool:
        valid_transitions = {
            SubscriptionStatus.ACTIVE: {
                SubscriptionStatus.PAST_DUE, SubscriptionStatus.EXPIRED,
                SubscriptionStatus.CANCELLED, SubscriptionStatus.SUSPENDED,
            },
            SubscriptionStatus.PAST_DUE: {
                SubscriptionStatus.ACTIVE, SubscriptionStatus.EXPIRED,
                SubscriptionStatus.CANCELLED, SubscriptionStatus.SUSPENDED,
            },
            SubscriptionStatus.EXPIRED: {
                SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE,
                SubscriptionStatus.CANCELLED, SubscriptionStatus.SUSPENDED,
            },
            SubscriptionStatus.CANCELLED: {SubscriptionStatus.ACTIVE},
            SubscriptionStatus.SUSPENDED: {
                SubscriptionStatus.ACTIVE, SubscriptionStatus.CANCELLED,
            },
        }
        return to_status in valid_transitions.get(from_status, set())

    async def plan_list(self) -> List[PlanResponse]:
        plans = await self.repository.list_plans()
        return [PlanResponse.model_validate(p) for p in plans]

    async def plan_get(self, plan_id: str) -> PlanResponse:
        plan = await self.repository.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found.")
        return PlanResponse.model_validate(plan)

    async def plan_create(self, plan_data: PlanCreate) -> PlanResponse:
        plan_id = f"plan_{plan_data.name.lower().replace(' ', '_').replace('-', '_')[:30]}"
        now = datetime.now(timezone.utc)
        existing = await self.repository.get_plan(plan_id)
        if existing:
            raise HTTPException(status_code=409, detail="Plan with this ID already exists.")

        plan = SubscriptionPlan(
            id=plan_id,
            code=plan_id,
            name=plan_data.name,
            description=plan_data.description,
            price=plan_data.price,
            currency=plan_data.currency,
            billing_interval=plan_data.billing_interval,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        created = await self.repository.create_plan(plan)
        return PlanResponse.model_validate(created)

    async def plan_update(self, plan_id: str, plan_data: PlanUpdate) -> PlanResponse:
        plan = await self.repository.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found.")

        updates = {}
        if plan_data.name is not None:
            updates["name"] = plan_data.name
        if plan_data.description is not None:
            updates["description"] = plan_data.description
        if plan_data.price is not None:
            updates["price"] = plan_data.price
        if plan_data.is_active is not None:
            updates["is_active"] = plan_data.is_active

        updated = await self.repository.update_plan(plan_id, updates)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update plan.")
        return PlanResponse.model_validate(updated)

    async def checkout(self, subscription_id: str) -> PaymentAttemptResponse:
        sub = await self.repository.get_by_id(subscription_id)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found.")

        bp = await self._get_current_pending_billing_period(subscription_id)
        if not bp:
            raise HTTPException(status_code=400, detail="No pending billing period for checkout.")

        attempts = await self.repository.get_payment_attempts_for_billing_period(bp.id)
        for a in attempts:
            if a.status in (PaymentAttemptStatus.PENDING, PaymentAttemptStatus.SUCCESS):
                return PaymentAttemptResponse.model_validate(a)

        now = datetime.now(timezone.utc)
        pa = PaymentAttempt(
            id=str(uuid_mod.uuid4()),
            billing_period_id=bp.id,
            subscription_id=subscription_id,
            business_id=sub.business_id,
            amount=bp.price_snapshot,
            currency=bp.currency_snapshot,
            provider="manual_bank_transfer",
            idempotency_key=f"checkout_{subscription_id}_{bp.id}",
            provider_order_id=f"BTR-{uuid_mod.uuid4().hex[:12].upper()}",
            status=PaymentAttemptStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        created_pa = await self.repository.create_payment_attempt(pa)

        bp.payment_status = BillingPeriodStatus.PROCESSING
        bp.payment_attempt_id = created_pa.id
        bp.updated_at = now
        await self.repository.update_billing_period(bp)

        try:
            svc, NScope, NType, NSev = _get_notification_service()
            if svc and NType:
                super_admin_ids = _get_super_admin_ids()
                if super_admin_ids:
                    await svc.notify_super_admins(
                        super_admin_ids=super_admin_ids,
                        type=NType.PAYMENT_VERIFICATION_REQUIRED,
                        severity=NSev.INFO,
                        title="Payment Verification Required",
                        message=f"Manual bank transfer payment requires verification for subscription {subscription_id}.",
                        metadata={
                            "subscription_id": subscription_id,
                            "billing_period_id": bp.id,
                            "payment_attempt_id": created_pa.id,
                        },
                        deduplication_key=f"payment-required:{created_pa.id}",
                    )
        except Exception:
            pass

        return PaymentAttemptResponse.model_validate(created_pa)

    async def retry_payment(self, billing_period_id: str) -> PaymentAttemptResponse:
        bp = await self.repository.get_billing_period(billing_period_id)
        if not bp:
            raise HTTPException(status_code=404, detail="Billing period not found.")

        if bp.payment_status in (BillingPeriodStatus.PAID, BillingPeriodStatus.CANCELLED):
            raise HTTPException(status_code=400, detail="Cannot retry a terminal billing period.")

        success = await self.repository.get_success_payment_attempt(bp.id)
        if success:
            raise HTTPException(status_code=400, detail="Billing period already has a successful payment attempt.")

        now = datetime.now(timezone.utc)
        pa = PaymentAttempt(
            id=str(uuid_mod.uuid4()),
            billing_period_id=bp.id,
            subscription_id=bp.subscription_id,
            business_id=bp.business_id,
            amount=bp.price_snapshot,
            currency=bp.currency_snapshot,
            provider="manual_bank_transfer",
            idempotency_key=f"retry_{bp.id}_{now.isoformat()}",
            provider_order_id=f"BTR-{uuid_mod.uuid4().hex[:12].upper()}",
            status=PaymentAttemptStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        created_pa = await self.repository.create_payment_attempt(pa)

        bp.payment_status = BillingPeriodStatus.PROCESSING
        bp.payment_attempt_id = created_pa.id
        bp.updated_at = now
        await self.repository.update_billing_period(bp)

        return PaymentAttemptResponse.model_validate(created_pa)

    async def renew(self, subscription_id: str) -> BillingPeriodResponse:
        sub = await self.repository.get_by_id(subscription_id)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found.")

        if sub.status not in (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot renew subscription in {sub.status.value} state."
            )

        plan = await self.repository.get_plan(sub.plan_id)
        if not plan:
            raise HTTPException(status_code=400, detail="Referenced plan not found.")

        if not plan.is_active:
            return None

        now = datetime.now(timezone.utc)
        next_start = sub.current_period_end
        if plan.billing_interval == BillingInterval.MONTHLY:
            next_end = next_start + timedelta(days=30)
        else:
            next_end = next_start + timedelta(days=365)

        existing_bps = await self.repository.get_billing_periods_for_subscription(subscription_id)
        for ebp in existing_bps:
            if ebp.period_start == next_start:
                return BillingPeriodResponse.model_validate(ebp)

        bp = BillingPeriod(
            id=str(uuid_mod.uuid4()),
            subscription_id=subscription_id,
            business_id=sub.business_id,
            plan_id=plan.id,
            plan_name_snapshot=plan.name,
            period_start=next_start,
            period_end=next_end,
            price_snapshot=plan.price,
            currency_snapshot=plan.currency,
            billing_interval_snapshot=plan.billing_interval,
            payment_status=BillingPeriodStatus.PENDING,
            created_at=now,
            updated_at=now,
        )
        created_bp = await self.repository.create_billing_period(bp)

        pa = PaymentAttempt(
            id=str(uuid_mod.uuid4()),
            billing_period_id=created_bp.id,
            subscription_id=subscription_id,
            business_id=sub.business_id,
            amount=created_bp.price_snapshot,
            currency=created_bp.currency_snapshot,
            provider="manual_bank_transfer",
            idempotency_key=f"renewal_{subscription_id}_{created_bp.id}",
            provider_order_id=f"BTR-{uuid_mod.uuid4().hex[:12].upper()}",
            status=PaymentAttemptStatus.CREATED,
            created_at=now,
            updated_at=now,
        )
        created_pa = await self.repository.create_payment_attempt(pa)

        created_bp.payment_attempt_id = created_pa.id
        created_bp.updated_at = now
        await self.repository.update_billing_period(created_bp)

        return BillingPeriodResponse.model_validate(created_bp)

    async def verify_manual_payment(
        self,
        subscription_id: str,
        billing_period_id: str,
        payment_attempt_id: str,
        payment_reference: str,
        verification_note: str,
        verified_by_user_id: str,
    ) -> PaymentAttemptResponse:
        pa = await self.repository.get_payment_attempt(payment_attempt_id)
        if not pa:
            raise HTTPException(status_code=404, detail="Payment attempt not found.")
        if pa.subscription_id != subscription_id:
            raise HTTPException(status_code=400, detail="Payment attempt does not belong to this subscription.")
        if pa.billing_period_id != billing_period_id:
            raise HTTPException(status_code=400, detail="Payment attempt does not belong to this billing period.")
        if pa.status == PaymentAttemptStatus.SUCCESS:
            raise HTTPException(status_code=400, detail="Payment attempt is already verified.")

        bp = await self.repository.get_billing_period(billing_period_id)
        if not bp:
            raise HTTPException(status_code=404, detail="Billing period not found.")

        if pa.amount != bp.price_snapshot:
            pa.status = PaymentAttemptStatus.FAILED
            pa.failure_code = "AMOUNT_MISMATCH"
            pa.failure_reason = f"Payment attempt amount {pa.amount} does not match billing period price snapshot {bp.price_snapshot}"
            pa.updated_at = datetime.now(timezone.utc)
            await self.repository.update_payment_attempt(pa)
            raise HTTPException(status_code=400, detail="Amount mismatch between payment attempt and billing period price snapshot.")

        if pa.currency != bp.currency_snapshot:
            pa.status = PaymentAttemptStatus.FAILED
            pa.failure_code = "CURRENCY_MISMATCH"
            pa.failure_reason = f"Payment attempt currency {pa.currency} does not match billing period currency snapshot {bp.currency_snapshot}"
            pa.updated_at = datetime.now(timezone.utc)
            await self.repository.update_payment_attempt(pa)
            raise HTTPException(status_code=400, detail="Currency mismatch between payment attempt and billing period price snapshot.")

        now = datetime.now(timezone.utc)
        pa.status = PaymentAttemptStatus.SUCCESS
        pa.payment_reference = payment_reference
        pa.verification_note = verification_note
        pa.verified_by = verified_by_user_id
        pa.verified_at = now
        pa.paid_at = now
        pa.updated_at = now
        await self.repository.update_payment_attempt(pa)

        bp.payment_status = BillingPeriodStatus.PAID
        bp.payment_attempt_id = pa.id
        bp.paid_at = now
        bp.updated_at = now
        await self.repository.update_billing_period(bp)

        sub = await self.repository.get_by_id(pa.subscription_id)
        if sub and sub.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.PAST_DUE):
            sub.price = bp.price_snapshot
            sub.currency = bp.currency_snapshot
            sub.billing_interval = bp.billing_interval_snapshot
            sub.current_period_start = bp.period_start
            sub.current_period_end = bp.period_end
            sub.status = SubscriptionStatus.ACTIVE
            await self.repository.update(sub)

        try:
            svc, NScope, NType, NSev = _get_notification_service()
            if svc and NType and sub:
                member_ids = _get_owner_admin_ids(sub.business_id)
                if member_ids:
                    await svc.notify_business_members(
                        member_ids=member_ids,
                        business_id=sub.business_id,
                        type=NType.PAYMENT_VERIFIED,
                        severity=NSev.INFO,
                        title="Payment Verified",
                        message=f"Manual bank transfer payment for subscription {subscription_id} has been verified and approved.",
                        metadata={
                            "subscription_id": subscription_id,
                            "billing_period_id": billing_period_id,
                            "payment_attempt_id": payment_attempt_id,
                        },
                        deduplication_key=f"payment-verified:{payment_attempt_id}",
                    )
        except Exception:
            pass

        return PaymentAttemptResponse.model_validate(pa)

    async def reconcile(self, subscription_id: str) -> dict:
        sub = await self.repository.get_by_id(subscription_id)
        if not sub:
            raise HTTPException(status_code=404, detail="Subscription not found.")

        bps = await self.repository.get_billing_periods_for_subscription(subscription_id)
        result = {"subscription_id": subscription_id, "billing_periods": []}

        for bp in bps:
            bp_info = {
                "billing_period_id": bp.id,
                "status": bp.payment_status.value,
                "price": str(bp.price_snapshot),
            }
            if bp.payment_status in (BillingPeriodStatus.PENDING, BillingPeriodStatus.PROCESSING):
                bp_info["reconciliation"] = "pending_manual_verification"
            else:
                bp_info["reconciliation"] = "no_action_required"
            result["billing_periods"].append(bp_info)

        return result

    async def get_billing_periods(self, subscription_id: str) -> List[BillingPeriodResponse]:
        bps = await self.repository.get_billing_periods_for_subscription(subscription_id)
        return [BillingPeriodResponse.model_validate(bp) for bp in bps]

    async def get_payment_attempts(self, billing_period_id: str) -> List[PaymentAttemptResponse]:
        pas = await self.repository.get_payment_attempts_for_billing_period(billing_period_id)
        return [PaymentAttemptResponse.model_validate(pa) for pa in pas]

    async def get_current_pending_billing_period(self, subscription_id: str) -> Optional[BillingPeriodResponse]:
        bp = await self._get_current_pending_billing_period(subscription_id)
        if bp:
            return BillingPeriodResponse.model_validate(bp)
        return None

    async def _get_current_pending_billing_period(self, subscription_id: str) -> Optional[BillingPeriod]:
        bps = await self.repository.get_billing_periods_for_subscription(subscription_id)
        for bp in bps:
            if bp.payment_status in (BillingPeriodStatus.PENDING, BillingPeriodStatus.PROCESSING):
                return bp
        return None


subscription_service = SubscriptionService()
