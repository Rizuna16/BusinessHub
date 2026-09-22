from fastapi import APIRouter, Depends, Request, Response
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.container import RepositoryContainer
from app.modules.authentication.schemas import UserInDB
from app.modules.authentication.router import get_current_user
from app.modules.subscription.schemas import (
    SubscriptionResponse, SubscriptionOverrideInput, SubscriptionStatus,
    PlanCreate, PlanUpdate, PlanResponse,
    BillingPeriodResponse, PaymentAttemptResponse, VerifyPaymentInput,
    PlanEntitlementCreate, PlanEntitlementUpdate,
)
from app.modules.subscription.service import SubscriptionService, subscription_service
from app.shared.utils import create_api_response
from app.modules.platform_admin.service import PlatformAdminService, platform_admin_service


router = APIRouter(prefix="/api/v1/platform/subscriptions", tags=["Platform Subscriptions"])


async def get_scoped_subscription_service(session: AsyncSession = Depends(get_db_session)) -> SubscriptionService:
    """
    Request-scoped SubscriptionService wired to the same AsyncSession for transaction boundary.
    """
    container = RepositoryContainer(session)
    return SubscriptionService(
        repository=container.subscription,
        session=session,
    )


async def get_super_admin(
    current_user: UserInDB = Depends(get_current_user),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
) -> UserInDB:
    return await service.require_superadmin(current_user.id)


@router.get("")
async def list_subscriptions(
    status_filter: Optional[SubscriptionStatus] = None,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    subs = await svc.list_all(status_filter=status_filter)
    return create_api_response(success=True, data=[s.model_dump() for s in subs])


@router.get("/{subscription_id}")
async def get_subscription(
    subscription_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    sub = await svc.get_by_id(subscription_id)
    if not sub:
        return create_api_response(success=False, message="Subscription not found.")
    return create_api_response(success=True, data=SubscriptionResponse.model_validate(sub).model_dump())


@router.get("/{subscription_id}/billing-periods")
async def list_billing_periods(
    subscription_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    bps = await svc.get_billing_periods(subscription_id)
    return create_api_response(success=True, data=[bp.model_dump() for bp in bps])


@router.post("/{subscription_id}/checkout")
async def checkout_subscription(
    subscription_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    pa = await svc.checkout(subscription_id)
    return create_api_response(success=True, data=pa.model_dump())


@router.post("/{subscription_id}/renew")
async def renew_subscription(
    subscription_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    bp = await svc.renew(subscription_id)
    if bp is None:
        return create_api_response(
            success=False,
            data=None,
            message="Renewal blocked: referenced plan is inactive."
        )
    return create_api_response(success=True, data=bp.model_dump())


@router.post("/{subscription_id}/retry")
async def retry_payment(
    subscription_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    bps = await svc.get_billing_periods(subscription_id)
    pending_bp = None
    for bp in bps:
        if bp.payment_status.value in ("PENDING", "PROCESSING", "FAILED"):
            pending_bp = bp
            break
    if not pending_bp:
        return create_api_response(success=False, message="No retryable billing period found.")
    pa = await svc.retry_payment(pending_bp.id)
    return create_api_response(success=True, data=pa.model_dump())


@router.post("/{subscription_id}/reconcile")
async def reconcile_subscription(
    subscription_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    result = await svc.reconcile(subscription_id)
    return create_api_response(success=True, data=result)


@router.post("/{subscription_id}/billing-periods/{billing_period_id}/payment-attempts/{payment_attempt_id}/verify")
async def verify_manual_payment(
    subscription_id: str,
    billing_period_id: str,
    payment_attempt_id: str,
    body: VerifyPaymentInput,
    superadmin: UserInDB = Depends(get_super_admin),
    service: PlatformAdminService = Depends(lambda: platform_admin_service),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    pa_before = await svc.repository.get_payment_attempt(payment_attempt_id)
    before_state = None
    if pa_before:
        before_state = {
            "status": pa_before.status.value,
            "payment_reference": pa_before.payment_reference,
            "verified_by": pa_before.verified_by,
        }

    pa = await svc.verify_manual_payment(
        subscription_id=subscription_id,
        billing_period_id=billing_period_id,
        payment_attempt_id=payment_attempt_id,
        payment_reference=body.payment_reference,
        verification_note=body.verification_note,
        verified_by_user_id=superadmin.id,
    )

    after_state = {
        "status": pa.status.value,
        "payment_reference": pa.payment_reference,
        "verified_by": pa.verified_by,
        "verified_at": pa.verified_at.isoformat() if pa.verified_at else None,
        "verification_note": pa.verification_note,
    }

    await service.log_audit(
        actor=superadmin,
        action="PAYMENT_VERIFIED",
        target_type="PAYMENT_ATTEMPT",
        target_id=payment_attempt_id,
        target_business_id=pa.business_id,
        reason=f"Manual bank transfer verified: {body.payment_reference}",
        before_state=before_state,
        after_state=after_state,
        metadata={
            "subscription_id": subscription_id,
            "billing_period_id": billing_period_id,
            "amount": str(pa.amount),
            "currency": pa.currency,
        },
    )

    return create_api_response(success=True, data=pa.model_dump())


plans_router = APIRouter(prefix="/api/v1/platform/plans", tags=["Platform Plans"])


@plans_router.get("")
async def list_plans(
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    plans = await svc.plan_list()
    return create_api_response(success=True, data=[p.model_dump() for p in plans])


@plans_router.get("/{plan_id}")
async def get_plan(
    plan_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    plan = await svc.plan_get(plan_id)
    return create_api_response(success=True, data=plan.model_dump())


@plans_router.post("")
async def create_plan(
    plan_data: PlanCreate,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    plan = await svc.plan_create(plan_data)
    return create_api_response(success=True, data=plan.model_dump())


@plans_router.put("/{plan_id}")
async def update_plan(
    plan_id: str,
    plan_data: PlanUpdate,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    plan = await svc.plan_update(plan_id, plan_data)
    return create_api_response(success=True, data=plan.model_dump())


@plans_router.post("/{plan_id}/activate")
async def activate_plan(
    plan_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    plan = await svc.plan_update(plan_id, PlanUpdate(is_active=True))
    return create_api_response(success=True, data=plan.model_dump())


@plans_router.post("/{plan_id}/deactivate")
async def deactivate_plan(
    plan_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    plan = await svc.plan_update(plan_id, PlanUpdate(is_active=False))
    return create_api_response(success=True, data=plan.model_dump())


@plans_router.get("/{plan_id}/entitlements")
async def list_plan_entitlements(
    plan_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    ents = await svc.entitlement_list(plan_id)
    return create_api_response(success=True, data=[e.model_dump() for e in ents])


@plans_router.post("/{plan_id}/entitlements")
async def create_plan_entitlement(
    plan_id: str,
    body: PlanEntitlementCreate,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    ent = await svc.entitlement_create(plan_id, body.feature_key, body.limit_value)
    return create_api_response(success=True, data=ent.model_dump())


@plans_router.put("/entitlements/{entitlement_id}")
async def update_plan_entitlement(
    entitlement_id: str,
    body: PlanEntitlementUpdate,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    ent = await svc.entitlement_update(entitlement_id, body.limit_value)
    return create_api_response(success=True, data=ent.model_dump())


@plans_router.delete("/entitlements/{entitlement_id}")
async def delete_plan_entitlement(
    entitlement_id: str,
    superadmin: UserInDB = Depends(get_super_admin),
    svc: SubscriptionService = Depends(get_scoped_subscription_service),
):
    await svc.entitlement_delete(entitlement_id)
    return create_api_response(success=True, data={"deleted": True})
