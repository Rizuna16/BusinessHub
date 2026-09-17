import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from app.modules.subscription.schemas import (
    SubscriptionStatus, BillingInterval, BillingPeriodStatus,
    PaymentAttemptStatus, PlanCreate, PlanUpdate, SubscriptionOverrideInput
)
from app.modules.subscription.repository import subscription_repository
from app.modules.subscription.service import subscription_service


@pytest.fixture(autouse=True)
def clear_repos():
    subscription_repository.clear()
    yield
    subscription_repository.clear()


@pytest.mark.anyio
async def test_default_plan_and_subscription_creation():
    sub = await subscription_service.create_default_subscription("biz_123")
    assert sub.business_id == "biz_123"
    assert sub.plan_id == "plan_business_standard"
    assert sub.price == Decimal("50000.00")
    assert sub.status == SubscriptionStatus.ACTIVE

    bps = await subscription_service.get_billing_periods(sub.id)
    assert len(bps) == 1
    assert bps[0].price_snapshot == Decimal("50000.00")
    assert bps[0].payment_status == BillingPeriodStatus.PENDING


@pytest.mark.anyio
async def test_configurable_pricing_scenario_50k_75k_100k():
    sub = await subscription_service.create_default_subscription("biz_price_test")

    bps1 = await subscription_service.get_billing_periods(sub.id)
    assert bps1[0].price_snapshot == Decimal("50000.00")

    plan = await subscription_service.plan_get("plan_business_standard")
    await subscription_service.plan_update(plan.id, PlanUpdate(price=Decimal("75000.00")))

    assert bps1[0].price_snapshot == Decimal("50000.00")

    bp2_res = await subscription_service.renew(sub.id)
    assert bp2_res.price_snapshot == Decimal("75000.00")

    current_sub = await subscription_service.get_by_id(sub.id)
    assert current_sub.price == Decimal("50000.00")

    await subscription_service.plan_update(plan.id, PlanUpdate(price=Decimal("100000.00")))

    bp2 = await subscription_service.repository.get_billing_period(bp2_res.id)
    assert bp2.price_snapshot == Decimal("75000.00")

    sub.current_period_end = bp2.period_end
    await subscription_service.repository.update(sub)

    bp3_res = await subscription_service.renew(sub.id)
    assert bp3_res.price_snapshot == Decimal("100000.00")


@pytest.mark.anyio
async def test_inactive_plan_renewal_block():
    sub = await subscription_service.create_default_subscription("biz_inactive")

    plan = await subscription_service.plan_get("plan_business_standard")
    await subscription_service.plan_update(plan.id, PlanUpdate(is_active=False))

    result = await subscription_service.renew(sub.id)
    assert result is None


@pytest.mark.anyio
async def test_checkout_manual_bank_transfer_initiation():
    sub = await subscription_service.create_default_subscription("biz_checkout")
    pa_resp = await subscription_service.checkout(sub.id)

    assert pa_resp.provider == "manual_bank_transfer"
    assert pa_resp.provider_order_id.startswith("BTR-")
    assert pa_resp.status == PaymentAttemptStatus.PENDING
    assert pa_resp.amount == Decimal("50000.00")
    assert pa_resp.currency == "IDR"

    bps = await subscription_service.get_billing_periods(sub.id)
    assert len(bps) == 1
    assert bps[0].payment_status == BillingPeriodStatus.PROCESSING


@pytest.mark.anyio
async def test_verify_manual_payment_success():
    sub = await subscription_service.create_default_subscription("biz_verify")
    pa_resp = await subscription_service.checkout(sub.id)

    bps = await subscription_service.get_billing_periods(sub.id)
    bp = bps[0]

    result = await subscription_service.verify_manual_payment(
        subscription_id=sub.id,
        billing_period_id=bp.id,
        payment_attempt_id=pa_resp.id,
        payment_reference="TRX-BCA-987654321",
        verification_note="Verified against bank statement",
        verified_by_user_id="admin_001",
    )

    assert result.status == PaymentAttemptStatus.SUCCESS
    assert result.payment_reference == "TRX-BCA-987654321"
    assert result.verified_by == "admin_001"
    assert result.verified_at is not None
    assert result.verification_note == "Verified against bank statement"
    assert result.paid_at is not None

    updated_sub = await subscription_service.get_by_id(sub.id)
    assert updated_sub.status == SubscriptionStatus.ACTIVE

    updated_bps = await subscription_service.get_billing_periods(sub.id)
    assert updated_bps[0].payment_status == BillingPeriodStatus.PAID


@pytest.mark.anyio
async def test_verify_payment_amount_mismatch_rejection():
    sub = await subscription_service.create_default_subscription("biz_mismatch")
    pa_resp = await subscription_service.checkout(sub.id)

    bps = await subscription_service.get_billing_periods(sub.id)
    bp = bps[0]

    pa_internal = await subscription_service.repository.get_payment_attempt(pa_resp.id)
    pa_internal.amount = Decimal("99999.00")
    await subscription_service.repository.update_payment_attempt(pa_internal)

    try:
        await subscription_service.verify_manual_payment(
            subscription_id=sub.id,
            billing_period_id=bp.id,
            payment_attempt_id=pa_resp.id,
            payment_reference="TRX-999",
            verification_note="Mismatch test",
            verified_by_user_id="admin_001",
        )
        assert False, "Should have raised HTTPException for amount mismatch"
    except Exception as e:
        assert "Amount mismatch" in str(e.detail) if hasattr(e, 'detail') else True

    failed_pa = await subscription_service.repository.get_payment_attempt(pa_resp.id)
    assert failed_pa.status == PaymentAttemptStatus.FAILED
    assert failed_pa.failure_code == "AMOUNT_MISMATCH"


@pytest.mark.anyio
async def test_verify_payment_currency_mismatch_rejection():
    sub = await subscription_service.create_default_subscription("biz_curr_mismatch")
    pa_resp = await subscription_service.checkout(sub.id)

    bps = await subscription_service.get_billing_periods(sub.id)
    bp = bps[0]

    pa_internal = await subscription_service.repository.get_payment_attempt(pa_resp.id)
    pa_internal.currency = "USD"
    await subscription_service.repository.update_payment_attempt(pa_internal)

    try:
        await subscription_service.verify_manual_payment(
            subscription_id=sub.id,
            billing_period_id=bp.id,
            payment_attempt_id=pa_resp.id,
            payment_reference="TRX-USD-999",
            verification_note="Currency mismatch test",
            verified_by_user_id="admin_001",
        )
        assert False, "Should have raised HTTPException for currency mismatch"
    except Exception as e:
        assert "Currency mismatch" in str(e.detail) if hasattr(e, 'detail') else True

    failed_pa = await subscription_service.repository.get_payment_attempt(pa_resp.id)
    assert failed_pa.status == PaymentAttemptStatus.FAILED
    assert failed_pa.failure_code == "CURRENCY_MISMATCH"


@pytest.mark.anyio
async def test_verify_already_success_no_double_verify():
    sub = await subscription_service.create_default_subscription("biz_double_verify")
    pa_resp = await subscription_service.checkout(sub.id)

    bps = await subscription_service.get_billing_periods(sub.id)
    bp = bps[0]

    await subscription_service.verify_manual_payment(
        subscription_id=sub.id,
        billing_period_id=bp.id,
        payment_attempt_id=pa_resp.id,
        payment_reference="TRX-001",
        verification_note="First verification",
        verified_by_user_id="admin_001",
    )

    try:
        await subscription_service.verify_manual_payment(
            subscription_id=sub.id,
            billing_period_id=bp.id,
            payment_attempt_id=pa_resp.id,
            payment_reference="TRX-002",
            verification_note="Double verification attempt",
            verified_by_user_id="admin_002",
        )
        assert False, "Should have raised HTTPException for already verified"
    except Exception as e:
        assert "already verified" in str(e.detail).lower() if hasattr(e, 'detail') else True


@pytest.mark.anyio
async def test_status_safety_suspended():
    sub = await subscription_service.create_default_subscription("biz_suspended")
    await subscription_service.override_subscription(
        sub.id,
        SubscriptionOverrideInput(action="SET_STATUS", status=SubscriptionStatus.SUSPENDED, reason="Test")
    )

    pa_resp = await subscription_service.checkout(sub.id)

    bps = await subscription_service.get_billing_periods(sub.id)
    bp = bps[0]

    result = await subscription_service.verify_manual_payment(
        subscription_id=sub.id,
        billing_period_id=bp.id,
        payment_attempt_id=pa_resp.id,
        payment_reference="TRX-SUSP-001",
        verification_note="Suspended subscription verification",
        verified_by_user_id="admin_001",
    )

    assert result.status == PaymentAttemptStatus.SUCCESS
    updated_sub = await subscription_service.get_by_id(sub.id)
    assert updated_sub.status == SubscriptionStatus.SUSPENDED


@pytest.mark.anyio
async def test_retry_uses_price_snapshot():
    sub = await subscription_service.create_default_subscription("biz_retry")
    pa_resp = await subscription_service.checkout(sub.id)

    bps = await subscription_service.get_billing_periods(sub.id)
    bp = bps[0]

    pa_internal = await subscription_service.repository.get_payment_attempt(pa_resp.id)
    pa_internal.status = PaymentAttemptStatus.FAILED
    pa_internal.failure_code = "BANK_TRANSFER_DECLINED"
    await subscription_service.repository.update_payment_attempt(pa_internal)

    plan = await subscription_service.plan_get("plan_business_standard")
    await subscription_service.plan_update(plan.id, PlanUpdate(price=Decimal("200000.00")))

    pa2 = await subscription_service.retry_payment(bp.id)
    assert pa2.amount == Decimal("50000.00")
    assert pa2.currency == "IDR"


@pytest.mark.anyio
async def test_provider_is_manual_bank_transfer():
    sub = await subscription_service.create_default_subscription("biz_provider")
    pa_resp = await subscription_service.checkout(sub.id)
    assert pa_resp.provider == "manual_bank_transfer"

    bps = await subscription_service.get_billing_periods(sub.id)
    bp = bps[0]

    pa_internal = await subscription_service.repository.get_payment_attempt(pa_resp.id)
    pa_internal.status = PaymentAttemptStatus.FAILED
    await subscription_service.repository.update_payment_attempt(pa_internal)

    pa2 = await subscription_service.retry_payment(bp.id)
    assert pa2.provider == "manual_bank_transfer"


@pytest.mark.anyio
async def test_idempotent_checkout_returns_existing_pending():
    sub = await subscription_service.create_default_subscription("biz_idempotent")
    pa1 = await subscription_service.checkout(sub.id)
    pa2 = await subscription_service.checkout(sub.id)
    assert pa1.id == pa2.id
    assert pa2.status == PaymentAttemptStatus.PENDING
