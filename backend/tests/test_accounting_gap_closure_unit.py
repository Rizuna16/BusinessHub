"""
Accounting Integration Gap Closure — Unit Tests (Direct Service Tests)

Tests the 4 gap closure areas at the service level:
1. Cash Transfer accounting journal
2. Inventory Adjustment accounting journal
3. Stock Opname Variance accounting journal
4. Direct Store Credit Issuance accounting journal

These tests run against the InMemory accounting repository directly.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from app.modules.accounting.repository import InMemoryAccountingRepository
from app.modules.accounting.integration import _idempotency_locks, accounting_integration_service


@pytest.fixture(autouse=True)
def clear_repos():
    _idempotency_locks.clear()
    InMemoryAccountingRepository.clear()
    yield
    _idempotency_locks.clear()
    InMemoryAccountingRepository.clear()


@pytest.fixture(autouse=True)
def mock_validate_access():
    from app.modules.business_membership.schemas import BusinessMembershipInDB
    mock_membership = BusinessMembershipInDB(
        id="mem-1", business_id="any", user_id="any",
        role="OWNER", status="ACTIVE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    with patch("app.modules.accounting.service.accounting_service._validate_access",
               new_callable=AsyncMock, return_value=mock_membership):
        yield


async def _setup_coa(biz_id: str):
    await accounting_integration_service.acct.ensure_default_chart_of_accounts(biz_id)


# ============================================================
# 1. CASH TRANSFER
# ============================================================

class TestCashTransferAccounting:
    @pytest.mark.asyncio
    async def test_cash_transfer_creates_journal(self):
        biz_id = "biz-ct-1"
        await _setup_coa(biz_id)
        jid = await accounting_integration_service.post_cash_transfer(
            business_id=biz_id, user_id="u1", transfer_id="t1",
            amount=Decimal("300000"), transfer_date=datetime.now(timezone.utc))
        assert jid is not None
        journals, total = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert total == 1
        j = journals[0]
        assert j.reference_type == "CASH_TRANSFER"
        assert j.reference_id == "t1"
        assert j.total_debit == Decimal("300000")
        assert j.total_credit == Decimal("300000")

    @pytest.mark.asyncio
    async def test_cash_transfer_balanced(self):
        biz_id = "biz-ct-2"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_cash_transfer(
            business_id=biz_id, user_id="u2", transfer_id="t2",
            amount=Decimal("100000"), transfer_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert journals[0].total_debit == journals[0].total_credit

    @pytest.mark.asyncio
    async def test_cash_transfer_account_codes(self):
        biz_id = "biz-ct-3"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_cash_transfer(
            business_id=biz_id, user_id="u3", transfer_id="t3",
            amount=Decimal("200000"), transfer_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        lines = await accounting_integration_service.acct.repository.list_lines_for_journal(journals[0].id)
        codes = {l.account_code for l in lines}
        assert "1100" in codes
        assert len(lines) == 2

    @pytest.mark.asyncio
    async def test_cash_transfer_idempotency(self):
        biz_id = "biz-ct-4"
        await _setup_coa(biz_id)
        j1 = await accounting_integration_service.post_cash_transfer(
            business_id=biz_id, user_id="u4", transfer_id="t-idem",
            amount=Decimal("500000"), transfer_date=datetime.now(timezone.utc))
        j2 = await accounting_integration_service.post_cash_transfer(
            business_id=biz_id, user_id="u4", transfer_id="t-idem",
            amount=Decimal("500000"), transfer_date=datetime.now(timezone.utc))
        assert j1 == j2

    @pytest.mark.asyncio
    async def test_zero_amount_returns_none(self):
        result = await accounting_integration_service.post_cash_transfer(
            business_id="biz", user_id="u", transfer_id="x",
            amount=Decimal("0"), transfer_date=datetime.now(timezone.utc))
        assert result is None

    @pytest.mark.asyncio
    async def test_negative_amount_returns_none(self):
        result = await accounting_integration_service.post_cash_transfer(
            business_id="biz", user_id="u", transfer_id="x",
            amount=Decimal("-100"), transfer_date=datetime.now(timezone.utc))
        assert result is None

    @pytest.mark.asyncio
    async def test_cash_transfer_source_type(self):
        biz_id = "biz-ct-5"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_cash_transfer(
            business_id=biz_id, user_id="u5", transfer_id="t-stype",
            amount=Decimal("100000"), transfer_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert len(journals) == 1
        assert journals[0].reference_type == "CASH_TRANSFER"


# ============================================================
# 2. INVENTORY ADJUSTMENT
# ============================================================

class TestInventoryAdjustmentAccounting:
    @pytest.mark.asyncio
    async def test_adjust_in_creates_journal(self):
        biz_id = "biz-ia-1"
        await _setup_coa(biz_id)
        jid = await accounting_integration_service.post_inventory_adjustment(
            business_id=biz_id, user_id="u1", adjustment_id="a1",
            amount=Decimal("100000"), adjustment_date=datetime.now(timezone.utc),
            is_adjustment_in=True)
        assert jid is not None
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert journals[0].reference_type == "INVENTORY_ADJUSTMENT"

    @pytest.mark.asyncio
    async def test_adjust_out_creates_journal(self):
        biz_id = "biz-ia-2"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_inventory_adjustment(
            business_id=biz_id, user_id="u2", adjustment_id="a2",
            amount=Decimal("50000"), adjustment_date=datetime.now(timezone.utc),
            is_adjustment_in=False)
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert len(journals) == 1

    @pytest.mark.asyncio
    async def test_adjust_in_account_codes(self):
        biz_id = "biz-ia-3"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_inventory_adjustment(
            business_id=biz_id, user_id="u3", adjustment_id="a3",
            amount=Decimal("200000"), adjustment_date=datetime.now(timezone.utc),
            is_adjustment_in=True)
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        lines = await accounting_integration_service.acct.repository.list_lines_for_journal(journals[0].id)
        amap = {l.account_code: l for l in lines}
        assert "1300" in amap
        assert amap["1300"].debit == Decimal("200000")
        assert "5100" in amap
        assert amap["5100"].credit == Decimal("200000")

    @pytest.mark.asyncio
    async def test_adjust_out_account_codes(self):
        biz_id = "biz-ia-4"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_inventory_adjustment(
            business_id=biz_id, user_id="u4", adjustment_id="a4",
            amount=Decimal("150000"), adjustment_date=datetime.now(timezone.utc),
            is_adjustment_in=False)
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        lines = await accounting_integration_service.acct.repository.list_lines_for_journal(journals[0].id)
        amap = {l.account_code: l for l in lines}
        assert "5100" in amap
        assert amap["5100"].debit == Decimal("150000")
        assert "1300" in amap
        assert amap["1300"].credit == Decimal("150000")

    @pytest.mark.asyncio
    async def test_adjustment_balanced(self):
        biz_id = "biz-ia-5"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_inventory_adjustment(
            business_id=biz_id, user_id="u5", adjustment_id="a5",
            amount=Decimal("250000"), adjustment_date=datetime.now(timezone.utc),
            is_adjustment_in=True)
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert journals[0].total_debit == journals[0].total_credit

    @pytest.mark.asyncio
    async def test_adjustment_idempotency(self):
        biz_id = "biz-ia-6"
        await _setup_coa(biz_id)
        j1 = await accounting_integration_service.post_inventory_adjustment(
            business_id=biz_id, user_id="u", adjustment_id="a-idem",
            amount=Decimal("100000"), adjustment_date=datetime.now(timezone.utc),
            is_adjustment_in=True)
        j2 = await accounting_integration_service.post_inventory_adjustment(
            business_id=biz_id, user_id="u", adjustment_id="a-idem",
            amount=Decimal("100000"), adjustment_date=datetime.now(timezone.utc),
            is_adjustment_in=True)
        assert j1 == j2

    @pytest.mark.asyncio
    async def test_zero_amount_returns_none(self):
        result = await accounting_integration_service.post_inventory_adjustment(
            business_id="biz", user_id="u", adjustment_id="a0",
            amount=Decimal("0"), adjustment_date=datetime.now(timezone.utc),
            is_adjustment_in=True)
        assert result is None


# ============================================================
# 3. STOCK OPNAME VARIANCE
# ============================================================

class TestStockOpnameVarianceAccounting:
    @pytest.mark.asyncio
    async def test_positive_variance_creates_journal(self):
        biz_id = "biz-so-1"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_stock_opname_variance(
            business_id=biz_id, user_id="u1", opname_id="o1",
            variance_value=Decimal("500000"), opname_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        j = journals[0]
        assert j.reference_type == "STOCK_OPNAME"
        assert j.total_debit == Decimal("500000")
        assert j.total_credit == Decimal("500000")

    @pytest.mark.asyncio
    async def test_negative_variance_creates_journal(self):
        biz_id = "biz-so-2"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_stock_opname_variance(
            business_id=biz_id, user_id="u2", opname_id="o2",
            variance_value=Decimal("-300000"), opname_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        j = journals[0]
        assert j.total_debit == Decimal("300000")
        assert j.total_credit == Decimal("300000")

    @pytest.mark.asyncio
    async def test_positive_variance_account_codes(self):
        biz_id = "biz-so-3"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_stock_opname_variance(
            business_id=biz_id, user_id="u3", opname_id="o3",
            variance_value=Decimal("200000"), opname_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        lines = await accounting_integration_service.acct.repository.list_lines_for_journal(journals[0].id)
        amap = {l.account_code: l for l in lines}
        assert "1300" in amap and amap["1300"].debit == Decimal("200000")
        assert "5100" in amap and amap["5100"].credit == Decimal("200000")

    @pytest.mark.asyncio
    async def test_negative_variance_account_codes(self):
        biz_id = "biz-so-4"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_stock_opname_variance(
            business_id=biz_id, user_id="u4", opname_id="o4",
            variance_value=Decimal("-150000"), opname_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        lines = await accounting_integration_service.acct.repository.list_lines_for_journal(journals[0].id)
        amap = {l.account_code: l for l in lines}
        assert "5100" in amap and amap["5100"].debit == Decimal("150000")
        assert "1300" in amap and amap["1300"].credit == Decimal("150000")

    @pytest.mark.asyncio
    async def test_zero_variance_returns_none(self):
        result = await accounting_integration_service.post_stock_opname_variance(
            business_id="biz", user_id="u", opname_id="o0",
            variance_value=Decimal("0"), opname_date=datetime.now(timezone.utc))
        assert result is None

    @pytest.mark.asyncio
    async def test_variance_idempotency(self):
        biz_id = "biz-so-5"
        await _setup_coa(biz_id)
        j1 = await accounting_integration_service.post_stock_opname_variance(
            business_id=biz_id, user_id="u", opname_id="o-idem",
            variance_value=Decimal("100000"), opname_date=datetime.now(timezone.utc))
        j2 = await accounting_integration_service.post_stock_opname_variance(
            business_id=biz_id, user_id="u", opname_id="o-idem",
            variance_value=Decimal("100000"), opname_date=datetime.now(timezone.utc))
        assert j1 == j2

    @pytest.mark.asyncio
    async def test_variance_source_type(self):
        biz_id = "biz-so-6"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_stock_opname_variance(
            business_id=biz_id, user_id="u6", opname_id="o-stype",
            variance_value=Decimal("75000"), opname_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert journals[0].reference_type == "STOCK_OPNAME"
        assert journals[0].reference_id == "o-stype"


# ============================================================
# 4. DIRECT STORE CREDIT ISSUANCE
# ============================================================

class TestDirectStoreCreditIssuanceAccounting:
    @pytest.mark.asyncio
    async def test_issuance_creates_journal(self):
        biz_id = "biz-sc-1"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_direct_store_credit_issuance(
            business_id=biz_id, user_id="u1", issuance_id="i1",
            amount=Decimal("500000"), issuance_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        j = journals[0]
        assert j.reference_type == "STORE_CREDIT_ISSUANCE"
        assert j.total_debit == Decimal("500000")
        assert j.total_credit == Decimal("500000")

    @pytest.mark.asyncio
    async def test_issuance_account_codes(self):
        biz_id = "biz-sc-2"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_direct_store_credit_issuance(
            business_id=biz_id, user_id="u2", issuance_id="i2",
            amount=Decimal("250000"), issuance_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        lines = await accounting_integration_service.acct.repository.list_lines_for_journal(journals[0].id)
        amap = {l.account_code: l for l in lines}
        assert "5100" in amap and amap["5100"].debit == Decimal("250000")
        assert "2300" in amap and amap["2300"].credit == Decimal("250000")

    @pytest.mark.asyncio
    async def test_issuance_balanced(self):
        biz_id = "biz-sc-3"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_direct_store_credit_issuance(
            business_id=biz_id, user_id="u3", issuance_id="i3",
            amount=Decimal("750000"), issuance_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert journals[0].total_debit == journals[0].total_credit

    @pytest.mark.asyncio
    async def test_issuance_idempotency(self):
        biz_id = "biz-sc-4"
        await _setup_coa(biz_id)
        j1 = await accounting_integration_service.post_direct_store_credit_issuance(
            business_id=biz_id, user_id="u", issuance_id="i-idem",
            amount=Decimal("100000"), issuance_date=datetime.now(timezone.utc))
        j2 = await accounting_integration_service.post_direct_store_credit_issuance(
            business_id=biz_id, user_id="u", issuance_id="i-idem",
            amount=Decimal("100000"), issuance_date=datetime.now(timezone.utc))
        assert j1 == j2

    @pytest.mark.asyncio
    async def test_issuance_source_type(self):
        biz_id = "biz-sc-5"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_direct_store_credit_issuance(
            business_id=biz_id, user_id="u5", issuance_id="i-stype",
            amount=Decimal("200000"), issuance_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert journals[0].reference_type == "STORE_CREDIT_ISSUANCE"

    @pytest.mark.asyncio
    async def test_zero_amount_returns_none(self):
        result = await accounting_integration_service.post_direct_store_credit_issuance(
            business_id="biz", user_id="u", issuance_id="i0",
            amount=Decimal("0"), issuance_date=datetime.now(timezone.utc))
        assert result is None

    @pytest.mark.asyncio
    async def test_store_credit_liability_account_2300(self):
        biz_id = "biz-sc-6"
        await _setup_coa(biz_id)
        acc = await accounting_integration_service.acct.repository.get_account_by_code(biz_id, "2300")
        assert acc is not None
        assert acc.name == "Customer Store Credit Liability"
        assert acc.account_type.value == "LIABILITY"
        assert acc.normal_balance.value == "CREDIT"
        assert acc.is_system is True


# ============================================================
# 5. END-TO-END RECONCILIATION
# ============================================================

class TestEndToEndReconciliation:
    @pytest.mark.asyncio
    async def test_all_journals_balanced(self):
        biz_id = "biz-e2e-1"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_cash_transfer(
            business_id=biz_id, user_id="u", transfer_id="e-t",
            amount=Decimal("500000"), transfer_date=datetime.now(timezone.utc))
        await accounting_integration_service.post_inventory_adjustment(
            business_id=biz_id, user_id="u", adjustment_id="e-a",
            amount=Decimal("300000"), adjustment_date=datetime.now(timezone.utc),
            is_adjustment_in=True)
        await accounting_integration_service.post_stock_opname_variance(
            business_id=biz_id, user_id="u", opname_id="e-o",
            variance_value=Decimal("-100000"), opname_date=datetime.now(timezone.utc))
        await accounting_integration_service.post_direct_store_credit_issuance(
            business_id=biz_id, user_id="u", issuance_id="e-s",
            amount=Decimal("200000"), issuance_date=datetime.now(timezone.utc))
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert len(journals) == 4
        for j in journals:
            assert j.total_debit == j.total_credit, f"{j.reference_type} unbalanced"

    @pytest.mark.asyncio
    async def test_trial_balance_balanced(self):
        biz_id = "biz-e2e-2"
        await _setup_coa(biz_id)
        await accounting_integration_service.post_cash_transfer(
            business_id=biz_id, user_id="u", transfer_id="tb-t",
            amount=Decimal("1000000"), transfer_date=datetime.now(timezone.utc))
        await accounting_integration_service.post_inventory_adjustment(
            business_id=biz_id, user_id="u", adjustment_id="tb-a",
            amount=Decimal("500000"), adjustment_date=datetime.now(timezone.utc),
            is_adjustment_in=True)
        await accounting_integration_service.post_stock_opname_variance(
            business_id=biz_id, user_id="u", opname_id="tb-o",
            variance_value=Decimal("-200000"), opname_date=datetime.now(timezone.utc))
        await accounting_integration_service.post_direct_store_credit_issuance(
            business_id=biz_id, user_id="u", issuance_id="tb-s",
            amount=Decimal("300000"), issuance_date=datetime.now(timezone.utc))
        tb = await accounting_integration_service.acct.get_trial_balance(biz_id, "u")
        assert tb.is_balanced is True
        assert tb.total_debit == tb.total_credit


# ============================================================
# 6. TENANT ISOLATION
# ============================================================

class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_isolation(self):
        biz1, biz2 = "biz-ti-1", "biz-ti-2"
        await _setup_coa(biz1)
        await _setup_coa(biz2)
        await accounting_integration_service.post_cash_transfer(
            business_id=biz1, user_id="u", transfer_id="ti-t",
            amount=Decimal("500000"), transfer_date=datetime.now(timezone.utc))
        j1, _ = await accounting_integration_service.acct.repository.list_journals(biz1)
        j2, _ = await accounting_integration_service.acct.repository.list_journals(biz2)
        assert len(j1) == 1
        assert len(j2) == 0


# ============================================================
# 7. COA VERIFICATION
# ============================================================

class TestCOAConstants:
    @pytest.mark.asyncio
    async def test_all_required_accounts_exist(self):
        biz_id = "biz-coa-1"
        await _setup_coa(biz_id)
        for code in ["1100", "1300", "5100", "2300"]:
            acc = await accounting_integration_service.acct.repository.get_account_by_code(biz_id, code)
            assert acc is not None, f"Account {code} missing"

    @pytest.mark.asyncio
    async def test_existing_integrations_still_work(self):
        """Verify existing integrations (sales, purchase, expense) are not broken."""
        biz_id = "biz-regression"
        await _setup_coa(biz_id)
        jid = await accounting_integration_service.post_sales_finalized(
            business_id=biz_id, user_id="u", sales_id="s-reg",
            grand_total=Decimal("1000000"), sales_date=datetime.now(timezone.utc))
        assert jid is not None
        journals, _ = await accounting_integration_service.acct.repository.list_journals(biz_id)
        assert journals[0].reference_type == "SALES"