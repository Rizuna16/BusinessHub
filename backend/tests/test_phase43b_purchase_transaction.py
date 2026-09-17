"""
Phase 4.3B — Purchase Finalization Transaction Tests (PostgreSQL).

Proves:
A. Finalization succeeds and all mutations persist in one transaction.
B. Rollback on failure leaves zero partial state.
C. Idempotency preserved.
D. Persistence survives session close.
"""
import pytest
import time
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, engine
from app.core.container import RepositoryContainer
from app.modules.business.service import BusinessService
from app.modules.business.schemas import BusinessCreate, BusinessType
from app.modules.business_membership.service import BusinessMembershipService
from app.modules.subscription.service import SubscriptionService
from app.modules.purchase.service import PurchaseService
from app.modules.purchase.schemas import PurchaseCreate, PurchaseLineCreate
from app.modules.inventory.service import InventoryService


async def _cleanup(biz_id, purchase_id=None):
    async with async_session_factory() as session:
        if purchase_id:
            await session.execute(text("DELETE FROM inventory_cost_movements WHERE reference_id = :pid"), {"pid": purchase_id})
            await session.execute(text("DELETE FROM stock_movements WHERE reference_id = :pid"), {"pid": purchase_id})
            await session.execute(text("DELETE FROM journal_lines WHERE journal_entry_id IN (SELECT id FROM journal_entries WHERE reference_id = :pid)"), {"pid": purchase_id})
            await session.execute(text("DELETE FROM journal_entries WHERE reference_id = :pid"), {"pid": purchase_id})
            await session.execute(text("DELETE FROM purchase_lines WHERE purchase_id = :pid"), {"pid": purchase_id})
            await session.execute(text("DELETE FROM purchases WHERE id = :pid"), {"pid": purchase_id})
        await session.execute(text("DELETE FROM payment_attempts WHERE billing_period_id IN (SELECT id FROM billing_periods WHERE business_id = :bid)"), {"bid": biz_id})
        await session.execute(text("DELETE FROM billing_periods WHERE business_id = :bid"), {"bid": biz_id})
        await session.execute(text("DELETE FROM subscriptions WHERE business_id = :bid"), {"bid": biz_id})
        await session.execute(text("DELETE FROM business_memberships WHERE business_id = :bid"), {"bid": biz_id})
        await session.execute(text("DELETE FROM businesses WHERE id = :bid"), {"bid": biz_id})
        await session.execute(text("DELETE FROM users WHERE id LIKE 'usr-%'"), {})
        await session.commit()


async def _seed_business():
    """Create a business with all required FK entities via separate sessions."""
    fresh_engine = None
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from app.core.config import settings
        fresh_engine = create_async_engine(settings.database_url, echo=False, pool_size=2, pool_pre_ping=True)
        FS = async_sessionmaker(fresh_engine, class_=AsyncSession, expire_on_commit=False)

        uid = str(uuid.uuid4())
        sup_id = str(uuid.uuid4())
        branch_id = str(uuid.uuid4())
        unit_id = str(uuid.uuid4())
        prod_id = str(uuid.uuid4())
        wh_id = str(uuid.uuid4())
        loc_id = str(uuid.uuid4())

        # User + Business in fresh engine
        async with FS() as s:
            await s.execute(text(
                "INSERT INTO users (id,email,full_name,password_hash,is_active,platform_role) "
                "VALUES (:id,:e,:fn,'hash',true,NULL)"
            ), {"id": uid, "e": f"p43b-{uid[:8]}@test.com", "fn": "Test"})

        async with async_session_factory() as s:
            c = RepositoryContainer(s)
            ms = BusinessMembershipService(repository=c.business_membership)
            ss = SubscriptionService(repository=c.subscription)
            biz_svc = BusinessService(repository=c.business, membership_service=ms, subscription_service_instance=ss, session=s)
            biz = await biz_svc.create_business(
                BusinessCreate(name="P43B Biz", business_type=BusinessType.RETAIL, timezone="UTC", locale="en-US"),
                owner_user_id=uid,
            )
            await s.commit()
            biz_id = biz.id

        # Supplier, branch, product, warehouse, location in fresh engine
        async with FS() as s:
            await s.execute(text(
                "INSERT INTO suppliers (id,business_id,supplier_type,code,name,status,created_at,updated_at) "
                "VALUES (:id,:bid,'ORGANIZATION','SUP','Test','ACTIVE',now(),now())"
            ), {"id": sup_id, "bid": biz_id})
            await s.execute(text(
                "INSERT INTO branches (id,business_id,code,name,timezone,locale,status,is_default,created_at,updated_at) "
                "VALUES (:id,:bid,'BR','Test','UTC','en-US','ACTIVE',false,now(),now())"
            ), {"id": branch_id, "bid": biz_id})
            await s.execute(text(
                "INSERT INTO units (id,business_id,name,code,symbol,unit_type,precision,status,created_at,updated_at) "
                "VALUES (:id,:bid,'Piece','PC','pc','DISCRETE',0,'ACTIVE',now(),now())"
            ), {"id": unit_id, "bid": biz_id})
            await s.execute(text(
                "INSERT INTO products (id,business_id,code,name,product_type,tax_treatment,status,unit_id,created_at,updated_at) "
                "VALUES (:id,:bid,'PROD','Test Product','GOODS','STANDARD_NON_LUXURY','ACTIVE',:uid,now(),now())"
            ), {"id": prod_id, "bid": biz_id, "uid": unit_id})
            await s.execute(text(
                "INSERT INTO warehouses (id,business_id,code,name,status,is_default,created_at,updated_at) "
                "VALUES (:id,:bid,'WH','WH','ACTIVE',true,now(),now())"
            ), {"id": wh_id, "bid": biz_id})
            await s.execute(text(
                "INSERT INTO inventory_locations (id,business_id,warehouse_id,code,name,status,location_type,is_default,created_at,updated_at) "
                "VALUES (:id,:bid,:wid,'LOC','Loc','ACTIVE','STORAGE',true,now(),now())"
            ), {"id": loc_id, "bid": biz_id, "wid": wh_id})
            await s.commit()

        return biz_id, uid, sup_id, branch_id, prod_id
    finally:
        if fresh_engine:
            await fresh_engine.dispose()


def _scoped_svc(session, user_id, container):
    ms = BusinessMembershipService(repository=container.business_membership, user_repo=container.user, account_repo=container.account, business_repo=container.business)
    inv_svc = InventoryService(
        balance_repo=container.stock_balance,
        movement_repo=container.stock_movement,
        cost_repo=container.inventory_cost,
        business_repo=container.business,
        location_repo=container.inventory_location,
        warehouse_repo=container.warehouse,
        product_repo=container.product,
        variant_repo=container.product_variant,
    )
    from app.modules.accounting.integration import AccountingIntegrationService
    from app.modules.accounting.service import AccountingService
    acct_svc = AccountingService(repository=container.accounting, membership_service=ms, branch_repo=container.branch)
    acct_int = AccountingIntegrationService(accounting_srv=acct_svc)
    return PurchaseService(
        purchase_repo=container.purchase, membership_service=ms,
        receiving_repo=container.receiving, catalog_repo=container.supplier_catalog,
        purchase_return_repo=container.purchase_return, inv_service=inv_svc,
        supplier_repo=container.supplier, branch_repo=container.branch,
        product_repo=container.product, category_repo=container.category,
        accounting_repo=container.accounting, accounting_integration=acct_int,
        session=session,
    )


@pytest.fixture(autouse=True)
async def _reset_engine():
    await engine.dispose()
    yield
    await engine.dispose()


async def _purchase_and_line(biz_id, uid, sup_id, branch_id, prod_id):
    """Create purchase and add line in separate sessions."""
    from app.modules.purchase.schemas import PurchaseCreate, PurchaseLineCreate
    from app.modules.purchase.schemas import PurchaseLineCreate
    async with async_session_factory() as session:
        svc = _scoped_svc(session, uid, RepositoryContainer(session))
        p = await svc.create_purchase(
            biz_id, uid,
            PurchaseCreate(supplier_id=sup_id, branch_id=branch_id, purchase_date="2025-01-01", notes="T"),
        )
        pid = p.id
    async with async_session_factory() as session:
        svc = _scoped_svc(session, uid, RepositoryContainer(session))
        await svc.add_line(
            biz_id, p.id, uid,
            PurchaseLineCreate(product_id=prod_id, quantity=Decimal("10"), unit_price=Decimal("100000"), discount_amount=Decimal("0"), tax_amount=Decimal("0")),
        )
        return pid


@pytest.mark.anyio
async def test_finalize_success():
    biz_id, uid, sup_id, branch_id, prod_id = await _seed_business()
    try:
        pid = await _purchase_and_line(biz_id, uid, sup_id, branch_id, prod_id)
        
        async with async_session_factory() as session:
            svc = _scoped_svc(session, uid, RepositoryContainer(session))
            result = await svc.finalize_purchase(biz_id, pid, uid)
            assert result is not None
        
        async with async_session_factory() as session:
            r = await session.execute(text("SELECT status FROM purchases WHERE id = :pid"), {"pid": pid})
            row = r.first()
            assert row is not None and row[0] == "FINALIZED"
    finally:
        await _cleanup(biz_id)


@pytest.mark.anyio
async def test_finalize_journal_persisted():
    biz_id, uid, sup_id, branch_id, prod_id = await _seed_business()
    try:
        pid = await _purchase_and_line(biz_id, uid, sup_id, branch_id, prod_id)
        
        async with async_session_factory() as session:
            svc = _scoped_svc(session, uid, RepositoryContainer(session))
            await svc.finalize_purchase(biz_id, pid, uid)
        
        async with async_session_factory() as session:
            r = await session.execute(text("SELECT count(*) FROM journal_entries WHERE reference_id = :pid AND reference_type='PURCHASE'"), {"pid": pid})
            assert r.scalar() == 1
    finally:
        await _cleanup(biz_id)


@pytest.mark.anyio
async def test_finalize_idempotent():
    biz_id, uid, sup_id, branch_id, prod_id = await _seed_business()
    try:
        pid = await _purchase_and_line(biz_id, uid, sup_id, branch_id, prod_id)
        
        async with async_session_factory() as session:
            svc = _scoped_svc(session, uid, RepositoryContainer(session))
            await svc.finalize_purchase(biz_id, pid, uid)
        
        async with async_session_factory() as session:
            svc = _scoped_svc(session, uid, RepositoryContainer(session))
            from fastapi import HTTPException
            try:
                await svc.finalize_purchase(biz_id, pid, uid)
                assert False
            except HTTPException:
                pass
        
        async with async_session_factory() as session:
            r = await session.execute(text("SELECT count(*) FROM journal_entries WHERE reference_id = :pid AND reference_type='PURCHASE'"), {"pid": pid})
            assert r.scalar() == 1
    finally:
        await _cleanup(biz_id)


@pytest.mark.anyio
async def test_finalize_across_sessions():
    biz_id, uid, sup_id, branch_id, prod_id = await _seed_business()
    try:
        pid = await _purchase_and_line(biz_id, uid, sup_id, branch_id, prod_id)
        
        async with async_session_factory() as session:
            svc = _scoped_svc(session, uid, RepositoryContainer(session))
            await svc.finalize_purchase(biz_id, pid, uid)
        
        async with async_session_factory() as session:
            r = await session.execute(text("SELECT status FROM purchases WHERE id = :pid"), {"pid": pid})
            assert r.scalar() == "FINALIZED"
    finally:
        await _cleanup(biz_id)


@pytest.mark.anyio
async def test_finalize_rollback():
    biz_id, uid, sup_id, branch_id, prod_id = await _seed_business()
    try:
        pid = await _purchase_and_line(biz_id, uid, sup_id, branch_id, prod_id)
        
        async with async_session_factory() as session:
            svc = _scoped_svc(session, uid, RepositoryContainer(session))
            svc.inv_service.record_cost_inbound = AsyncMock(side_effect=RuntimeError("MAC FAIL"))
            try:
                await svc.finalize_purchase(biz_id, pid, uid)
                assert False
            except RuntimeError:
                pass
        
        async with async_session_factory() as session:
            r = await session.execute(text("SELECT status FROM purchases WHERE id = :pid"), {"pid": pid})
            assert r.scalar() == "DRAFT"
            r2 = await session.execute(text("SELECT count(*) FROM journal_entries WHERE reference_id = :pid"), {"pid": pid})
            assert r2.scalar() == 0
    finally:
        await _cleanup(biz_id)


@pytest.mark.anyio
async def test_purchase_create_persists():
    biz_id, uid, sup_id, branch_id, prod_id = await _seed_business()
    try:
        async with async_session_factory() as session:
            svc = _scoped_svc(session, uid, RepositoryContainer(session))
            p = await svc.create_purchase(
                biz_id, uid,
                PurchaseCreate(supplier_id=sup_id, branch_id=branch_id, purchase_date="2025-01-01", notes="T"),
            )
            pid = p.id
        async with async_session_factory() as session:
            r = await session.execute(text("SELECT status FROM purchases WHERE id = :pid"), {"pid": pid})
            assert r.scalar() == "DRAFT"
    finally:
        await _cleanup(biz_id)


@pytest.mark.anyio
async def test_purchase_cancel_persists():
    biz_id, uid, sup_id, branch_id, prod_id = await _seed_business()
    try:
        async with async_session_factory() as session:
            svc = _scoped_svc(session, uid, RepositoryContainer(session))
            p = await svc.create_purchase(
                biz_id, uid,
                PurchaseCreate(supplier_id=sup_id, branch_id=branch_id, purchase_date="2025-01-01", notes="T"),
            )
            await svc.cancel_purchase(biz_id, p.id, uid)
            pid = p.id
        async with async_session_factory() as session:
            r = await session.execute(text("SELECT status FROM purchases WHERE id = :pid"), {"pid": pid})
            assert r.scalar() == "CANCELLED"
    finally:
        await _cleanup(biz_id)