from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import uuid
import asyncio

from app.modules.subscription.schemas import (
    SubscriptionInDB, SubscriptionStatus, BillingInterval,
    BillingPeriodStatus, PaymentAttemptStatus,
    SubscriptionPlan, BillingPeriod, PaymentAttempt,
)


class AbstractSubscriptionRepository(ABC):
    @abstractmethod
    async def create_default(self, business_id: str) -> SubscriptionInDB:
        pass

    @abstractmethod
    async def get_by_id(self, subscription_id: str) -> Optional[SubscriptionInDB]:
        pass

    async def get_by_id_for_update(self, subscription_id: str) -> Optional[SubscriptionInDB]:
        return await self.get_by_id(subscription_id)

    async def get_billing_period_for_update(self, bp_id: str) -> Optional[BillingPeriod]:
        return await self.get_billing_period(bp_id)

    async def get_payment_attempt_for_update(self, pa_id: str) -> Optional[PaymentAttempt]:
        return await self.get_payment_attempt(pa_id)

    @abstractmethod
    async def get_by_business_id(self, business_id: str) -> Optional[SubscriptionInDB]:
        pass

    @abstractmethod
    async def list_all(self) -> List[SubscriptionInDB]:
        pass

    @abstractmethod
    async def update(self, subscription: SubscriptionInDB) -> SubscriptionInDB:
        pass

    @abstractmethod
    async def count(self) -> int:
        pass

    @abstractmethod
    async def create_entitlement(self, plan_id: str, feature_key: str, limit_value: int) -> "PlanEntitlementInDB":
        pass

    @abstractmethod
    async def get_entitlement(self, plan_id: str, feature_key: str) -> Optional["PlanEntitlementInDB"]:
        pass

    @abstractmethod
    async def get_entitlement_by_id(self, entitlement_id: str) -> Optional["PlanEntitlementInDB"]:
        pass

    @abstractmethod
    async def list_entitlements(self, plan_id: str) -> List["PlanEntitlementInDB"]:
        pass

    @abstractmethod
    async def update_entitlement(self, entitlement_id: str, limit_value: int) -> Optional["PlanEntitlementInDB"]:
        pass

    @abstractmethod
    async def delete_entitlement(self, entitlement_id: str) -> bool:
        pass

    @classmethod
    @abstractmethod
    def clear(cls):
        pass


class InMemorySubscriptionRepository(AbstractSubscriptionRepository):
    _subscriptions: Dict[str, SubscriptionInDB] = {}
    _business_index: Dict[str, str] = {}
    _plans: Dict[str, SubscriptionPlan] = {}
    _plan_code_index: Dict[str, str] = {}
    _billing_periods: Dict[str, BillingPeriod] = {}
    _bp_sub_index: Dict[str, List[str]] = {}
    _bp_order_index: Dict[str, str] = {}
    _payment_attempts: Dict[str, PaymentAttempt] = {}
    _pa_order_index: Dict[str, str] = {}
    _pa_billing_period_index: Dict[str, List[str]] = {}
    _entitlements: Dict[str, "PlanEntitlementInDB"] = {}
    _plan_key_index: Dict[str, str] = {}  # "plan_id:feature_key" -> id
    _lock = asyncio.Lock()
    _initialized = False

    @classmethod
    def _ensure_default_plan(cls):
        if cls._initialized:
            return
        now = datetime.now(timezone.utc)
        default_plan = SubscriptionPlan(
            id="plan_business_standard",
            code="plan_business_standard",
            name="Business Plan",
            description="Standard business monthly plan",
            price=Decimal("50000.00"),
            currency="IDR",
            billing_interval=BillingInterval.MONTHLY,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        cls._plans[default_plan.id] = default_plan
        cls._plan_code_index[default_plan.code] = default_plan.id
        cls._initialized = True

    async def create_default(self, business_id: str) -> SubscriptionInDB:
        self._ensure_default_plan()
        async with self._lock:
            if business_id in self._business_index:
                existing_id = self._business_index[business_id]
                existing = self._subscriptions.get(existing_id)
                if existing and existing.status != SubscriptionStatus.CANCELLED:
                    return existing

            now = datetime.now(timezone.utc)
            subscription_id = str(uuid.uuid4())

            sub = SubscriptionInDB(
                id=subscription_id,
                business_id=business_id,
                plan_id="plan_business_standard",
                plan_name="Business Plan",
                status=SubscriptionStatus.ACTIVE,
                price=Decimal("50000.00"),
                currency="IDR",
                billing_interval=BillingInterval.MONTHLY,
                started_at=now,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                created_at=now,
                updated_at=now,
            )
            self._subscriptions[subscription_id] = sub
            self._business_index[business_id] = subscription_id

            bp_id = str(uuid.uuid4())
            billing_period = BillingPeriod(
                id=bp_id,
                subscription_id=subscription_id,
                business_id=business_id,
                plan_id="plan_business_standard",
                plan_name_snapshot="Business Plan",
                period_start=now,
                period_end=now + timedelta(days=30),
                price_snapshot=Decimal("50000.00"),
                currency_snapshot="IDR",
                billing_interval_snapshot=BillingInterval.MONTHLY,
                payment_status=BillingPeriodStatus.PENDING,
                created_at=now,
                updated_at=now,
            )
            self._billing_periods[bp_id] = billing_period
            self._bp_sub_index.setdefault(subscription_id, []).append(bp_id)

            pa_id = str(uuid.uuid4())
            payment_attempt = PaymentAttempt(
                id=pa_id,
                billing_period_id=bp_id,
                subscription_id=subscription_id,
                business_id=business_id,
                amount=Decimal("50000.00"),
                currency="IDR",
                provider="manual_bank_transfer",
                idempotency_key=f"init_{subscription_id}_{bp_id}",
                provider_order_id=f"ORD-{uuid.uuid4().hex[:12].upper()}",
                status=PaymentAttemptStatus.CREATED,
                created_at=now,
                updated_at=now,
            )
            self._payment_attempts[pa_id] = payment_attempt
            self._pa_order_index[payment_attempt.provider_order_id] = pa_id
            self._pa_billing_period_index.setdefault(bp_id, []).append(pa_id)
            billing_period.payment_attempt_id = pa_id
            billing_period.updated_at = now

            return sub

    async def get_by_id(self, subscription_id: str) -> Optional[SubscriptionInDB]:
        return self._subscriptions.get(subscription_id)

    async def get_by_id_for_update(self, subscription_id: str) -> Optional[SubscriptionInDB]:
        return self._subscriptions.get(subscription_id)

    async def get_by_business_id(self, business_id: str) -> Optional[SubscriptionInDB]:
        sub_id = self._business_index.get(business_id)
        if not sub_id:
            return None
        return self._subscriptions.get(sub_id)

    async def list_all(self) -> List[SubscriptionInDB]:
        return list(self._subscriptions.values())

    async def update(self, subscription: SubscriptionInDB) -> SubscriptionInDB:
        async with self._lock:
            subscription.updated_at = datetime.now(timezone.utc)
            self._subscriptions[subscription.id] = subscription
            return subscription

    async def count(self) -> int:
        return len(self._subscriptions)

    @classmethod
    def clear(cls):
        cls._subscriptions.clear()
        cls._business_index.clear()
        cls._plans.clear()
        cls._plan_code_index.clear()
        cls._billing_periods.clear()
        cls._bp_sub_index.clear()
        cls._bp_order_index.clear()
        cls._payment_attempts.clear()
        cls._pa_order_index.clear()
        cls._pa_billing_period_index.clear()
        cls._entitlements.clear()
        cls._plan_key_index.clear()
        cls._initialized = False

    async def create_plan(self, plan: SubscriptionPlan) -> SubscriptionPlan:
        async with self._lock:
            self._plans[plan.id] = plan
            self._plan_code_index[plan.code] = plan.id
            return plan

    async def get_plan(self, plan_id: str) -> Optional[SubscriptionPlan]:
        return self._plans.get(plan_id)

    async def get_plan_by_code(self, code: str) -> Optional[SubscriptionPlan]:
        plan_id = self._plan_code_index.get(code)
        if plan_id:
            return self._plans.get(plan_id)
        return None

    async def list_plans(self) -> List[SubscriptionPlan]:
        return list(self._plans.values())

    async def update_plan(self, plan_id: str, updates: dict) -> Optional[SubscriptionPlan]:
        async with self._lock:
            plan = self._plans.get(plan_id)
            if not plan:
                return None
            for k, v in updates.items():
                if v is not None and hasattr(plan, k):
                    setattr(plan, k, v)
            plan.updated_at = datetime.now(timezone.utc)
            self._plans[plan_id] = plan
            return plan

    async def create_billing_period(self, bp: BillingPeriod) -> BillingPeriod:
        async with self._lock:
            existing = self._bp_sub_index.get(bp.subscription_id, [])
            for bp_id in existing:
                existing_bp = self._billing_periods.get(bp_id)
                if (existing_bp and
                        existing_bp.period_start == bp.period_start and
                        existing_bp.subscription_id == bp.subscription_id):
                    return existing_bp

            self._billing_periods[bp.id] = bp
            self._bp_sub_index.setdefault(bp.subscription_id, []).append(bp.id)
            return bp

    async def get_billing_period(self, bp_id: str) -> Optional[BillingPeriod]:
        return self._billing_periods.get(bp_id)

    async def get_billing_periods_for_subscription(self, subscription_id: str) -> List[BillingPeriod]:
        bp_ids = self._bp_sub_index.get(subscription_id, [])
        return [self._billing_periods[bid] for bid in bp_ids if bid in self._billing_periods]

    async def get_billing_period_by_order_id(self, order_id: str) -> Optional[BillingPeriod]:
        pa_id = self._pa_order_index.get(order_id)
        if not pa_id:
            return None
        pa = self._payment_attempts.get(pa_id)
        if not pa:
            return None
        return self._billing_periods.get(pa.billing_period_id)

    async def update_billing_period(self, bp: BillingPeriod) -> BillingPeriod:
        async with self._lock:
            bp.updated_at = datetime.now(timezone.utc)
            self._billing_periods[bp.id] = bp
            return bp

    async def create_payment_attempt(self, pa: PaymentAttempt) -> PaymentAttempt:
        async with self._lock:
            self._payment_attempts[pa.id] = pa
            self._pa_order_index[pa.provider_order_id] = pa.id
            self._pa_billing_period_index.setdefault(pa.billing_period_id, []).append(pa.id)
            return pa

    async def get_payment_attempt(self, pa_id: str) -> Optional[PaymentAttempt]:
        return self._payment_attempts.get(pa_id)

    async def get_payment_attempt_by_order_id(self, order_id: str) -> Optional[PaymentAttempt]:
        pa_id = self._pa_order_index.get(order_id)
        if pa_id:
            return self._payment_attempts.get(pa_id)
        return None

    async def get_payment_attempts_for_billing_period(self, bp_id: str) -> List[PaymentAttempt]:
        pa_ids = self._pa_billing_period_index.get(bp_id, [])
        return [self._payment_attempts[paid] for paid in pa_ids if paid in self._payment_attempts]

    async def get_success_payment_attempt(self, bp_id: str) -> Optional[PaymentAttempt]:
        attempts = await self.get_payment_attempts_for_billing_period(bp_id)
        for a in attempts:
            if a.status == PaymentAttemptStatus.SUCCESS:
                return a
        return None

    async def update_payment_attempt(self, pa: PaymentAttempt) -> PaymentAttempt:
        async with self._lock:
            pa.updated_at = datetime.now(timezone.utc)
            self._payment_attempts[pa.id] = pa
            return pa

    async def create_entitlement(self, plan_id: str, feature_key: str, limit_value: int) -> "PlanEntitlementInDB":
        from app.modules.subscription.schemas import PlanEntitlementInDB
        async with self._lock:
            composite_key = f"{plan_id}:{feature_key}"
            if composite_key in self._plan_key_index:
                raise ValueError(f"Entitlement already exists for plan {plan_id}, key {feature_key}")
            now = datetime.now(timezone.utc)
            ent = PlanEntitlementInDB(
                id=str(uuid.uuid4()),
                plan_id=plan_id,
                feature_key=feature_key,
                limit_value=limit_value,
                created_at=now,
                updated_at=now,
            )
            self._entitlements[ent.id] = ent
            self._plan_key_index[composite_key] = ent.id
            return ent

    async def get_entitlement(self, plan_id: str, feature_key: str) -> Optional["PlanEntitlementInDB"]:
        composite_key = f"{plan_id}:{feature_key}"
        ent_id = self._plan_key_index.get(composite_key)
        if ent_id:
            return self._entitlements.get(ent_id)
        return None

    async def get_entitlement_by_id(self, entitlement_id: str) -> Optional["PlanEntitlementInDB"]:
        return self._entitlements.get(entitlement_id)

    async def list_entitlements(self, plan_id: str) -> List["PlanEntitlementInDB"]:
        return [e for e in self._entitlements.values() if e.plan_id == plan_id]

    async def update_entitlement(self, entitlement_id: str, limit_value: int) -> Optional["PlanEntitlementInDB"]:
        from app.modules.subscription.schemas import PlanEntitlementInDB
        async with self._lock:
            ent = self._entitlements.get(entitlement_id)
            if not ent:
                return None
            updated = PlanEntitlementInDB(
                id=ent.id,
                plan_id=ent.plan_id,
                feature_key=ent.feature_key,
                limit_value=limit_value,
                created_at=ent.created_at,
                updated_at=datetime.now(timezone.utc),
            )
            self._entitlements[entitlement_id] = updated
            return updated

    async def delete_entitlement(self, entitlement_id: str) -> bool:
        async with self._lock:
            ent = self._entitlements.pop(entitlement_id, None)
            if ent:
                composite_key = f"{ent.plan_id}:{ent.feature_key}"
                self._plan_key_index.pop(composite_key, None)
                return True
            return False


subscription_repository = InMemorySubscriptionRepository()
