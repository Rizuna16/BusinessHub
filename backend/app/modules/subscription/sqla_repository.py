from datetime import datetime, timezone, timedelta
from typing import Optional, List
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.subscription.models import (
    SubscriptionInDB as SubscriptionModel,
    BillingPeriod as BillingPeriodModel,
    PaymentAttempt as PaymentAttemptModel,
)
from app.modules.subscription.repository import AbstractSubscriptionRepository
from app.modules.subscription.schemas import (
    SubscriptionInDB,
    SubscriptionStatus,
    BillingInterval,
    BillingPeriodStatus,
    PaymentAttemptStatus,
    SubscriptionPlan,
    BillingPeriod,
    PaymentAttempt,
)
from app.modules.sqla_base import sa_create


def _to_subscription(obj: SubscriptionModel) -> SubscriptionInDB:
    return SubscriptionInDB(
        id=obj.id,
        business_id=obj.business_id,
        plan_id=obj.plan_id,
        plan_name=obj.plan_name,
        status=SubscriptionStatus(obj.status),
        price=obj.price,
        currency=obj.currency,
        billing_interval=BillingInterval(obj.billing_interval),
        started_at=obj.started_at,
        current_period_start=obj.current_period_start,
        current_period_end=obj.current_period_end,
        cancelled_at=obj.cancelled_at,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_billing_period(obj: BillingPeriodModel) -> BillingPeriod:
    return BillingPeriod(
        id=obj.id,
        subscription_id=obj.subscription_id,
        business_id=obj.business_id,
        plan_id=obj.plan_id,
        plan_name_snapshot=obj.plan_name_snapshot,
        period_start=obj.period_start,
        period_end=obj.period_end,
        price_snapshot=obj.price_snapshot,
        currency_snapshot=obj.currency_snapshot,
        billing_interval_snapshot=BillingInterval(obj.billing_interval_snapshot),
        payment_status=BillingPeriodStatus(obj.payment_status),
        payment_attempt_id=obj.payment_attempt_id,
        paid_at=obj.paid_at,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def _to_payment_attempt(obj: PaymentAttemptModel) -> PaymentAttempt:
    return PaymentAttempt(
        id=obj.id,
        billing_period_id=obj.billing_period_id,
        subscription_id=obj.subscription_id,
        business_id=obj.business_id,
        amount=obj.amount,
        currency=obj.currency,
        provider=obj.provider,
        payment_reference=obj.payment_reference,
        idempotency_key=obj.idempotency_key,
        provider_order_id=obj.provider_order_id,
        provider_transaction_id=obj.provider_transaction_id,
        status=PaymentAttemptStatus(obj.status),
        failure_code=obj.failure_code,
        failure_reason=obj.failure_reason,
        created_at=obj.created_at,
        updated_at=obj.updated_at,
        paid_at=obj.paid_at,
        verification_note=obj.verification_note,
        verified_by=obj.verified_by,
        verified_at=obj.verified_at,
    )


class SQLAlchemySubscriptionRepository(AbstractSubscriptionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_default(self, business_id: str) -> SubscriptionInDB:
        existing = await self.get_by_business_id(business_id)
        if existing and existing.status != SubscriptionStatus.CANCELLED:
            return existing

        now = datetime.now(timezone.utc)
        sub_data = {
            "business_id": business_id,
            "plan_id": "plan_business_standard",
            "plan_name": "Business Plan",
            "status": SubscriptionStatus.ACTIVE.value,
            "price": Decimal("50000.00"),
            "currency": "IDR",
            "billing_interval": BillingInterval.MONTHLY.value,
            "started_at": now,
            "current_period_start": now,
            "current_period_end": now + timedelta(days=30),
        }
        sub_obj = await sa_create(self.session, SubscriptionModel, sub_data)

        bp_data = {
            "subscription_id": sub_obj.id,
            "business_id": business_id,
            "plan_id": "plan_business_standard",
            "plan_name_snapshot": "Business Plan",
            "period_start": now,
            "period_end": now + timedelta(days=30),
            "price_snapshot": Decimal("50000.00"),
            "currency_snapshot": "IDR",
            "billing_interval_snapshot": BillingInterval.MONTHLY.value,
            "payment_status": BillingPeriodStatus.PENDING.value,
        }
        bp_obj = await sa_create(self.session, BillingPeriodModel, bp_data)

        pa_data = {
            "billing_period_id": bp_obj.id,
            "subscription_id": sub_obj.id,
            "business_id": business_id,
            "amount": Decimal("50000.00"),
            "currency": "IDR",
            "provider": "manual_bank_transfer",
            "idempotency_key": f"init_{sub_obj.id}_{bp_obj.id}",
            "provider_order_id": f"ORD-{str(sub_obj.id)[:12].upper()}",
            "status": PaymentAttemptStatus.CREATED.value,
        }
        pa_obj = await sa_create(self.session, PaymentAttemptModel, pa_data)

        bp_obj.payment_attempt_id = pa_obj.id
        await self.session.flush()

        return _to_subscription(sub_obj)

    async def get_by_id(self, subscription_id: str) -> Optional[SubscriptionInDB]:
        stmt = select(SubscriptionModel).where(SubscriptionModel.id == subscription_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_subscription(obj) if obj else None

    async def get_by_business_id(self, business_id: str) -> Optional[SubscriptionInDB]:
        stmt = select(SubscriptionModel).where(SubscriptionModel.business_id == business_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_subscription(obj) if obj else None

    async def list_all(self) -> List[SubscriptionInDB]:
        stmt = select(SubscriptionModel)
        res = await self.session.execute(stmt)
        return [_to_subscription(o) for o in res.scalars().all()]

    async def update(self, subscription: SubscriptionInDB) -> SubscriptionInDB:
        stmt = select(SubscriptionModel).where(SubscriptionModel.id == subscription.id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return subscription
        obj.status = subscription.status.value
        obj.plan_id = subscription.plan_id
        obj.plan_name = subscription.plan_name
        obj.price = subscription.price
        obj.currency = subscription.currency
        obj.billing_interval = subscription.billing_interval.value
        obj.started_at = subscription.started_at
        obj.current_period_start = subscription.current_period_start
        obj.current_period_end = subscription.current_period_end
        obj.cancelled_at = subscription.cancelled_at
        await self.session.flush()
        return _to_subscription(obj)

    async def count(self) -> int:
        stmt = select(func.count()).select_from(SubscriptionModel)
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def create_plan(self, plan: SubscriptionPlan) -> SubscriptionPlan:
        # Plans are managed via SubscriptionPlan model if defined; here we store in memory as fallback
        return plan

    async def get_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        return None

    async def get_plan_by_code(self, code: str) -> Optional[SubscriptionPlan]:
        return None

    async def list_plans(self) -> List[SubscriptionPlan]:
        return []

    async def update_plan(self, plan_id: str, updates: dict) -> Optional[SubscriptionPlan]:
        return None

    async def create_billing_period(self, bp: BillingPeriod) -> BillingPeriod:
        # Check for duplicate by subscription_id + period_start
        existing_stmt = select(BillingPeriodModel).where(
            BillingPeriodModel.subscription_id == bp.subscription_id,
            BillingPeriodModel.period_start == bp.period_start,
        )
        existing_res = await self.session.execute(existing_stmt)
        existing = existing_res.scalar_one_or_none()
        if existing:
            return _to_billing_period(existing)

        data = {
            "subscription_id": bp.subscription_id,
            "business_id": bp.business_id,
            "plan_id": bp.plan_id,
            "plan_name_snapshot": bp.plan_name_snapshot,
            "period_start": bp.period_start,
            "period_end": bp.period_end,
            "price_snapshot": bp.price_snapshot,
            "currency_snapshot": bp.currency_snapshot,
            "billing_interval_snapshot": bp.billing_interval_snapshot.value,
            "payment_status": bp.payment_status.value,
            "payment_attempt_id": bp.payment_attempt_id,
            "paid_at": bp.paid_at,
        }
        obj = await sa_create(self.session, BillingPeriodModel, data)
        return _to_billing_period(obj)

    async def get_billing_period(self, bp_id: str) -> Optional[BillingPeriod]:
        stmt = select(BillingPeriodModel).where(BillingPeriodModel.id == bp_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_billing_period(obj) if obj else None

    async def get_billing_periods_for_subscription(self, subscription_id: str) -> List[BillingPeriod]:
        stmt = select(BillingPeriodModel).where(BillingPeriodModel.subscription_id == subscription_id)
        res = await self.session.execute(stmt)
        return [_to_billing_period(o) for o in res.scalars().all()]

    async def get_billing_period_by_order_id(self, order_id: str) -> Optional[BillingPeriod]:
        pa_stmt = select(PaymentAttemptModel).where(PaymentAttemptModel.provider_order_id == order_id)
        pa_res = await self.session.execute(pa_stmt)
        pa = pa_res.scalar_one_or_none()
        if not pa:
            return None
        return await self.get_billing_period(pa.billing_period_id)

    async def update_billing_period(self, bp: BillingPeriod) -> BillingPeriod:
        stmt = select(BillingPeriodModel).where(BillingPeriodModel.id == bp.id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return bp
        obj.payment_status = bp.payment_status.value
        obj.payment_attempt_id = bp.payment_attempt_id
        obj.paid_at = bp.paid_at
        await self.session.flush()
        return _to_billing_period(obj)

    async def create_payment_attempt(self, pa: PaymentAttempt) -> PaymentAttempt:
        data = {
            "billing_period_id": pa.billing_period_id,
            "subscription_id": pa.subscription_id,
            "business_id": pa.business_id,
            "amount": pa.amount,
            "currency": pa.currency,
            "provider": pa.provider,
            "payment_reference": pa.payment_reference,
            "idempotency_key": pa.idempotency_key,
            "provider_order_id": pa.provider_order_id,
            "provider_transaction_id": pa.provider_transaction_id,
            "status": pa.status.value,
            "failure_code": pa.failure_code,
            "failure_reason": pa.failure_reason,
            "paid_at": pa.paid_at,
            "verification_note": pa.verification_note,
            "verified_by": pa.verified_by,
            "verified_at": pa.verified_at,
        }
        obj = await sa_create(self.session, PaymentAttemptModel, data)
        return _to_payment_attempt(obj)

    async def get_payment_attempt(self, pa_id: str) -> Optional[PaymentAttempt]:
        stmt = select(PaymentAttemptModel).where(PaymentAttemptModel.id == pa_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_payment_attempt(obj) if obj else None

    async def get_payment_attempt_by_order_id(self, order_id: str) -> Optional[PaymentAttempt]:
        stmt = select(PaymentAttemptModel).where(PaymentAttemptModel.provider_order_id == order_id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_payment_attempt(obj) if obj else None

    async def get_payment_attempts_for_billing_period(self, bp_id: str) -> List[PaymentAttempt]:
        stmt = select(PaymentAttemptModel).where(PaymentAttemptModel.billing_period_id == bp_id)
        res = await self.session.execute(stmt)
        return [_to_payment_attempt(o) for o in res.scalars().all()]

    async def get_success_payment_attempt(self, bp_id: str) -> Optional[PaymentAttempt]:
        stmt = select(PaymentAttemptModel).where(
            PaymentAttemptModel.billing_period_id == bp_id,
            PaymentAttemptModel.status == PaymentAttemptStatus.SUCCESS.value,
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        return _to_payment_attempt(obj) if obj else None

    async def update_payment_attempt(self, pa: PaymentAttempt) -> PaymentAttempt:
        stmt = select(PaymentAttemptModel).where(PaymentAttemptModel.id == pa.id)
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if not obj:
            return pa
        obj.status = pa.status.value
        obj.payment_reference = pa.payment_reference
        obj.provider_transaction_id = pa.provider_transaction_id
        obj.failure_code = pa.failure_code
        obj.failure_reason = pa.failure_reason
        obj.paid_at = pa.paid_at
        obj.verification_note = pa.verification_note
        obj.verified_by = pa.verified_by
        obj.verified_at = pa.verified_at
        await self.session.flush()
        return _to_payment_attempt(obj)

    @classmethod
    def clear(cls):
        pass
