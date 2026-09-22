from typing import List, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid as uuid_mod
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

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
    def __init__(self, repository: AbstractSubscriptionRepository = subscription_repository, session: Optional[AsyncSession] = None):
        self.repository = repository
        self.session = session

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
        if self.session is not None:
            async with self.session.begin():
                return await self._override_subscription_impl(subscription_id, override)
        else:
            return await self._override_subscription_impl(subscription_id, override)

    async def _override_subscription_impl(
        self, subscription_id: str, override: SubscriptionOverrideInput
    ) -> SubscriptionInDB:
        sub = await self.repository.get_by_id_for_update(subscription_id)
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
        sub = await self.repository.get_by_id_for_update(subscription_id)
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
            from app.modules.notification.service import _send_notification
            from app.modules.notification.schemas import (
                NotificationScope, NotificationType, NotificationSeverity,
            )

            super_admin_ids = _get_super_admin_ids()
            if super_admin_ids:
                for admin_id in super_admin_ids:
                    dedup = f"payment-required:{created_pa.id}:{admin_id}"
                    await _send_notification(
                        recipient_id=admin_id,
                        scope=NotificationScope.PLATFORM,
                        notif_type=NotificationType.PAYMENT_VERIFICATION_REQUIRED,
                        severity=NotificationSeverity.INFO,
                        title="Payment Verification Required",
                        message=f"Manual bank transfer payment requires verification for subscription {subscription_id}.",
                        business_id=None,
                        metadata={
                            "subscription_id": subscription_id,
                            "billing_period_id": bp.id,
                            "payment_attempt_id": created_pa.id,
                        },
                        deduplication_key=dedup,
                    )
        except Exception:
            pass

        return PaymentAttemptResponse.model_validate(created_pa)

    async def retry_payment(self, billing_period_id: str) -> PaymentAttemptResponse:
        bp = await self.repository.get_billing_period_for_update(billing_period_id)
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
        if self.session is not None:
            async with self.session.begin():
                return await self._renew_impl(subscription_id)
        else:
            return await self._renew_impl(subscription_id)

    async def _renew_impl(self, subscription_id: str) -> BillingPeriodResponse:
        sub = await self.repository.get_by_id_for_update(subscription_id)
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
        if self.session is not None:
            async with self.session.begin():
                return await self._verify_manual_payment_impl(
                    subscription_id, billing_period_id, payment_attempt_id,
                    payment_reference, verification_note, verified_by_user_id,
                )
        else:
            return await self._verify_manual_payment_impl(
                subscription_id, billing_period_id, payment_attempt_id,
                payment_reference, verification_note, verified_by_user_id,
            )

    async def _verify_manual_payment_impl(
        self,
        subscription_id: str,
        billing_period_id: str,
        payment_attempt_id: str,
        payment_reference: str,
        verification_note: str,
        verified_by_user_id: str,
    ) -> PaymentAttemptResponse:
        pa = await self.repository.get_payment_attempt_for_update(payment_attempt_id)
        if not pa:
            raise HTTPException(status_code=404, detail="Payment attempt not found.")
        if pa.subscription_id != subscription_id:
            raise HTTPException(status_code=400, detail="Payment attempt does not belong to this subscription.")
        if pa.billing_period_id != billing_period_id:
            raise HTTPException(status_code=400, detail="Payment attempt does not belong to this billing period.")
        if pa.status == PaymentAttemptStatus.SUCCESS:
            raise HTTPException(status_code=400, detail="Payment attempt is already verified.")

        bp = await self.repository.get_billing_period_for_update(billing_period_id)
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
            from app.modules.notification.service import _send_notification
            from app.modules.notification.schemas import (
                NotificationScope, NotificationType, NotificationSeverity,
            )

            if sub:
                member_ids = _get_owner_admin_ids(sub.business_id)
                if member_ids:
                    for member_id in member_ids:
                        dedup = f"payment-verified:{payment_attempt_id}:{member_id}"
                        await _send_notification(
                            recipient_id=member_id,
                            scope=NotificationScope.TENANT,
                            notif_type=NotificationType.PAYMENT_VERIFIED,
                            severity=NotificationSeverity.INFO,
                            title="Payment Verified",
                            message=f"Manual bank transfer payment for subscription {subscription_id} has been verified and approved.",
                            business_id=sub.business_id,
                            metadata={
                                "subscription_id": subscription_id,
                                "billing_period_id": billing_period_id,
                                "payment_attempt_id": payment_attempt_id,
                            },
                            deduplication_key=dedup,
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

    # ── Entitlement Management ────────────────────────────────────────

    SUPPORTED_FEATURE_KEYS = frozenset({"max_products", "max_members", "max_branches", "max_warehouses"})

    async def entitlement_create(self, plan_id: str, feature_key: str, limit_value: int) -> "PlanEntitlementResponse":
        from app.modules.subscription.schemas import PlanEntitlementResponse
        if feature_key not in self.SUPPORTED_FEATURE_KEYS:
            raise HTTPException(status_code=400, detail=f"Unsupported feature key: {feature_key}")
        if limit_value < -1:
            raise HTTPException(status_code=400, detail="limit_value must be >= -1")

        plan = await self.repository.get_plan(plan_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found.")

        existing = await self.repository.get_entitlement(plan_id, feature_key)
        if existing:
            raise HTTPException(status_code=409, detail="Entitlement already exists for this plan and feature key.")

        ent = await self.repository.create_entitlement(plan_id, feature_key, limit_value)
        return PlanEntitlementResponse.model_validate(ent)

    async def entitlement_get(self, entitlement_id: str) -> "PlanEntitlementResponse":
        from app.modules.subscription.schemas import PlanEntitlementResponse
        ent = await self.repository.get_entitlement_by_id(entitlement_id)
        if not ent:
            raise HTTPException(status_code=404, detail="Entitlement not found.")
        return PlanEntitlementResponse.model_validate(ent)

    async def entitlement_list(self, plan_id: str) -> List["PlanEntitlementResponse"]:
        from app.modules.subscription.schemas import PlanEntitlementResponse
        ents = await self.repository.list_entitlements(plan_id)
        return [PlanEntitlementResponse.model_validate(e) for e in ents]

    async def entitlement_update(self, entitlement_id: str, limit_value: int) -> "PlanEntitlementResponse":
        from app.modules.subscription.schemas import PlanEntitlementResponse
        if limit_value < -1:
            raise HTTPException(status_code=400, detail="limit_value must be >= -1")
        ent = await self.repository.update_entitlement(entitlement_id, limit_value)
        if not ent:
            raise HTTPException(status_code=404, detail="Entitlement not found.")
        return PlanEntitlementResponse.model_validate(ent)

    async def entitlement_delete(self, entitlement_id: str) -> bool:
        deleted = await self.repository.delete_entitlement(entitlement_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Entitlement not found.")
        return True

    # ── Quota Enforcement ─────────────────────────────────────────────

    async def check_quota(self, business_id: str, feature_key: str) -> None:
        from app.modules.subscription.schemas import SubscriptionStatus, PlanEntitlementInDB, SUPPORTED_ENTITLEMENT_KEYS

        if feature_key not in SUPPORTED_ENTITLEMENT_KEYS:
            raise HTTPException(status_code=400, detail=f"Unsupported quota feature: {feature_key}")

        sub = await self.repository.get_by_business_id(business_id)
        if not sub:
            raise HTTPException(status_code=403, detail="No active subscription found. Subscription required.")

        if sub.status in (SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED, SubscriptionStatus.SUSPENDED):
            raise HTTPException(
                status_code=403,
                detail=f"Subscription is {sub.status.value}. New {feature_key} creation is blocked."
            )

        plan = await self.repository.get_plan(sub.plan_id)
        if not plan:
            raise HTTPException(status_code=403, detail="Referenced subscription plan not found. Quota check failed.")

        if not plan.is_active:
            raise HTTPException(status_code=403, detail="Subscription plan is inactive. Quota check failed.")

        entitlement = await self.repository.get_entitlement(sub.plan_id, feature_key)
        if not entitlement:
            raise HTTPException(
                status_code=403,
                detail=f"No entitlement configured for {feature_key} on plan {sub.plan_id}. Creation blocked."
            )

        limit = entitlement.limit_value

        if limit == -1:
            return

        if limit == 0:
            raise HTTPException(
                status_code=403,
                detail=f"Feature {feature_key} is disabled on plan {sub.plan_id}."
            )

        usage = await self._calculate_usage(business_id, feature_key)

        if usage >= limit:
            raise HTTPException(
                status_code=403,
                detail=f"{feature_key} limit reached. Current: {usage}, Limit: {limit}."
            )

    async def _calculate_usage(self, business_id: str, feature_key: str) -> int:
        if feature_key == "max_products":
            return await self._count_products(business_id)
        elif feature_key == "max_members":
            return await self._count_members(business_id)
        elif feature_key == "max_branches":
            return await self._count_branches(business_id)
        elif feature_key == "max_warehouses":
            return await self._count_warehouses(business_id)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown feature key for usage calculation: {feature_key}")

    async def _count_products(self, business_id: str) -> int:
        try:
            from app.modules.product.repository import product_repository
            products = await product_repository.list_by_business(business_id)
            return sum(1 for p in products if p.status.value != "ARCHIVED")
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to calculate product usage.")

    async def _count_members(self, business_id: str) -> int:
        try:
            from app.modules.business_membership.repository import business_membership_repository
            count = 0
            for m in business_membership_repository._memberships.values():
                if m.business_id == business_id and m.status.value == "ACTIVE":
                    count += 1
            return count
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to calculate membership usage.")

    async def _count_branches(self, business_id: str) -> int:
        try:
            from app.modules.branch.repository import branch_repository
            active = await branch_repository.count_active(business_id)
            return active
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to calculate branch usage.")

    async def _count_warehouses(self, business_id: str) -> int:
        try:
            from app.modules.warehouse.repository import warehouse_repository
            warehouses = await warehouse_repository.list_by_business(business_id)
            return sum(1 for w in warehouses if w.status.value != "ARCHIVED")
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to calculate warehouse usage.")


subscription_service = SubscriptionService()
