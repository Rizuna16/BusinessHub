"""
Accounting Integration Service — Feature #34

Connects operational transactions to Accounting Foundation (#33) via the Posting Engine.

Source-of-truth matrix:
- Sales → Sales source of truth
- Payment → Payment source of truth
- Cash → CashMovement source of truth
- Purchase → Purchase source of truth
- Expense → Expense source of truth
- Sales Return → SalesReturn source of truth
- Purchase Return → PurchaseReturn source of truth
- Accounting Journal → GL source of truth

This service performs accounting projection/posting ONLY for validated operational events.
It does NOT duplicate, replace, or override any existing source of truth.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Callable, Awaitable, Any
from fastapi import HTTPException
import asyncio

from app.modules.accounting.schemas import JournalEntryCreate, JournalLineInput
from app.modules.accounting.service import AccountingService, accounting_service


# ============================================================
# COA Account Code Constants
# ============================================================
ACCOUNT_CASH_BANK = "1100"
ACCOUNT_ACCOUNTS_RECEIVABLE = "1200"
ACCOUNT_INVENTORY_ASSETS = "1300"
ACCOUNT_INPUT_VAT = "1400"
ACCOUNT_ACCOUNTS_PAYABLE = "2100"
ACCOUNT_OUTPUT_VAT = "2200"
ACCOUNT_STORE_CREDIT_LIABILITY = "2300"
ACCOUNT_SALES_REVENUE = "4100"
ACCOUNT_GENERAL_EXPENSE = "5100"
ACCOUNT_COGS = "5200"


# ============================================================
# Idempotency Lock Registry
# ============================================================
# In-memory lock registry simulating PostgreSQL UNIQUE constraint.
# For concurrent duplicate requests, only the first request acquires
# the lock and executes; subsequent requests wait and return the
# idempotent result.
_idempotency_locks: dict[str, asyncio.Lock] = {}
_lock_registry_lock = asyncio.Lock()


def _get_lock(key: str) -> asyncio.Lock:
    """Get or create a lock for a given idempotency key."""
    return _idempotency_locks.setdefault(key, asyncio.Lock())


class AccountingIntegrationService:
    """
    Service that posts accounting journals for operational transactions.
    All methods are idempotent: retrying the same event returns the existing journal.
    """

    def __init__(
        self,
        accounting_srv: AccountingService = accounting_service,
    ):
        self.acct = accounting_srv

    def _idempotency_key(self, business_id: str, source_type: str, source_id: str, event: str) -> str:
        """
        Deterministic idempotency key: source_type + source_id + event.
        Uses source_id (UUID) as primary uniqueness; business isolation
        is enforced by business_id on the journal entry itself.
        Max 100 chars per schema constraint.
        """
        raw = f"{source_type}:{source_id}:{event}"
        if len(raw) > 100:
            raw = raw[:100]
        return raw

    async def _resolve_account_id(self, business_id: str, code: str) -> str:
        """Resolve an account code to its ID for the given business."""
        await self.acct.ensure_default_chart_of_accounts(business_id)
        accounts = await self.acct.repository.list_accounts(business_id)
        for acc in accounts:
            if acc.code == code and acc.is_active:
                return acc.id
        raise HTTPException(
            status_code=500,
            detail=f"Required accounting account {code} not found for business.",
        )

    async def safe_post(
        self,
        idem_key: str,
        post_fn: Callable[[], Awaitable[Any]],
    ) -> Any:
        """
        Execute accounting posting within an idempotency lock.

        This ensures concurrent identical requests are serialized:
        - Request A acquires lock, executes posting, releases lock.
        - Request B waits for lock, then finds existing journal (idempotent),
          returns it without creating a duplicate.

        For PostgreSQL production:
        - UNIQUE(business_id, idempotency_key) on journal_entries provides
          the same guarantee at the database level.
        - This in-memory lock simulates that behavior for testing.
        """
        lock = _get_lock(idem_key)
        async with lock:
            return await post_fn()

    async def _post_journal(
        self,
        business_id: str,
        user_id: str,
        source_type: str,
        source_id: str,
        event: str,
        description: str,
        journal_date: datetime,
        lines: list[tuple[str, Decimal, Decimal]],
        branch_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Core posting method. Posts a double-entry journal via the existing Posting Engine.

        Args:
            business_id: Business scope
            user_id: User performing the operation
            source_type: e.g. "SALES", "PAYMENT", "PURCHASE", "EXPENSE"
            source_id: ID of the source transaction
            event: e.g. "FINALIZED", "PAYMENT_RECORDED", "VOIDED"
            description: Journal description
            journal_date: Date of the journal
            lines: List of (account_code, debit, credit) tuples
            branch_id: Optional branch attribution

        Returns:
            Journal entry ID or None if already posted (idempotent)
        """
        idem_key = self._idempotency_key(business_id, source_type, source_id, event)

        # Resolve account codes to IDs
        journal_lines = []
        for code, debit, credit in lines:
            acc_id = await self._resolve_account_id(business_id, code)
            journal_lines.append(
                JournalLineInput(
                    account_id=acc_id,
                    debit=debit,
                    credit=credit,
                )
            )

        payload = JournalEntryCreate(
            branch_id=branch_id,
            journal_date=journal_date,
            description=description,
            reference_type=source_type,
            reference_id=source_id,
            lines=journal_lines,
            idempotency_key=idem_key,
        )

        result = await self.acct.create_and_post_journal(
            business_id=business_id,
            user_id=user_id,
            payload=payload,
        )
        return result.id

    # ============================================================
    # SALES INTEGRATION
    # ============================================================

    async def post_sales_finalized(
        self,
        business_id: str,
        user_id: str,
        sales_id: str,
        grand_total: Decimal,
        sales_date: datetime,
        tax_total: Decimal = Decimal("0"),
        total_cogs: Decimal = Decimal("0"),
        branch_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Journal: Debit AR / Debit COGS / Credit Sales Revenue / Credit Output VAT / Credit Inventory Assets.
        Triggered when Sales status changes to FINALIZED.
        Idempotent: same sales_id → same journal.
        """
        if grand_total <= Decimal("0"):
            return None

        lines = [(ACCOUNT_ACCOUNTS_RECEIVABLE, grand_total, Decimal("0"))]

        if tax_total > Decimal("0"):
            net_revenue = grand_total - tax_total
            if net_revenue > Decimal("0"):
                lines.append((ACCOUNT_SALES_REVENUE, Decimal("0"), net_revenue))
            lines.append((ACCOUNT_OUTPUT_VAT, Decimal("0"), tax_total))
        else:
            lines.append((ACCOUNT_SALES_REVENUE, Decimal("0"), grand_total))

        if total_cogs > Decimal("0"):
            lines.append((ACCOUNT_COGS, total_cogs, Decimal("0")))
            lines.append((ACCOUNT_INVENTORY_ASSETS, Decimal("0"), total_cogs))

        return await self._post_journal(
            business_id=business_id,
            user_id=user_id,
            source_type="SALES",
            source_id=sales_id,
            event="FINALIZED",
            description="Sales revenue and COGS from finalized sale",
            journal_date=sales_date,
            lines=lines,
            branch_id=branch_id,
        )

    async def post_sales_return_finalized(
        self,
        business_id: str,
        user_id: str,
        sales_return_id: str,
        grand_total: Decimal,
        return_date: datetime,
        tax_total: Decimal = Decimal("0"),
        reversal_cogs: Decimal = Decimal("0"),
        branch_id: Optional[str] = None,
        refund_destination: str = "CASH",
    ) -> Optional[str]:
        """
        Journal: Reverses sales revenue and COGS.

        For CASH refunds:        DR Revenue / CR AR          (original behavior)
        For STORE_CREDIT refunds: DR Revenue / CR Store Credit Liability

        Idempotent: same sales_return_id → same journal.
        """
        if grand_total <= Decimal("0") and reversal_cogs <= Decimal("0"):
            return None

        lines = []
        if grand_total > Decimal("0"):
            if tax_total > Decimal("0"):
                net_revenue = grand_total - tax_total
                if net_revenue > Decimal("0"):
                    lines.append((ACCOUNT_SALES_REVENUE, net_revenue, Decimal("0")))
                lines.append((ACCOUNT_OUTPUT_VAT, tax_total, Decimal("0")))
            else:
                lines.append((ACCOUNT_SALES_REVENUE, grand_total, Decimal("0")))

            # Feature #61: STORE_CREDIT → CR Store Credit Liability instead of CR AR
            if refund_destination == "STORE_CREDIT":
                lines.append((ACCOUNT_STORE_CREDIT_LIABILITY, Decimal("0"), grand_total))
            else:
                lines.append((ACCOUNT_ACCOUNTS_RECEIVABLE, Decimal("0"), grand_total))

        if reversal_cogs > Decimal("0"):
            lines.append((ACCOUNT_INVENTORY_ASSETS, reversal_cogs, Decimal("0")))
            lines.append((ACCOUNT_COGS, Decimal("0"), reversal_cogs))

        return await self._post_journal(
            business_id=business_id,
            user_id=user_id,
            source_type="SALES_RETURN",
            source_id=sales_return_id,
            event="FINALIZED",
            description="Sales return reversal and COGS restoration",
            journal_date=return_date,
            lines=lines,
            branch_id=branch_id,
        )

    # ============================================================
    # PAYMENT INTEGRATION
    # ============================================================

    async def post_payment_recorded(
        self,
        business_id: str,
        user_id: str,
        payment_id: str,
        amount: Decimal,
        direction: str,
        payment_date: datetime,
        branch_id: Optional[str] = None,
        payment_method: Optional[str] = None,
    ) -> Optional[str]:
        """
        Customer Payment (CUSTOMER_IN):
            - CASH/BANK:       Debit Cash (1100) / Credit Accounts Receivable (1200)
            - STORE_CREDIT:    Debit Store Credit Liability (2300) / Credit Accounts Receivable (1200)
        Supplier Payment (SUPPLIER_OUT):
            Debit Accounts Payable (2100) / Credit Cash (1100).
        Idempotent: same payment_id → same journal.
        """
        if amount <= Decimal("0"):
            return None

        if direction == "CUSTOMER_IN":
            # Feature #61: STORE_CREDIT uses liability account instead of cash
            if payment_method == "STORE_CREDIT":
                return await self._post_journal(
                    business_id=business_id,
                    user_id=user_id,
                    source_type="PAYMENT",
                    source_id=payment_id,
                    event="RECORDED",
                    description="Store credit payment received",
                    journal_date=payment_date,
                    lines=[
                        (ACCOUNT_STORE_CREDIT_LIABILITY, amount, Decimal("0")),
                        (ACCOUNT_ACCOUNTS_RECEIVABLE, Decimal("0"), amount),
                    ],
                    branch_id=branch_id,
                )
            else:
                return await self._post_journal(
                    business_id=business_id,
                    user_id=user_id,
                    source_type="PAYMENT",
                    source_id=payment_id,
                    event="RECORDED",
                    description=f"Customer payment received",
                    journal_date=payment_date,
                    lines=[
                        (ACCOUNT_CASH_BANK, amount, Decimal("0")),
                        (ACCOUNT_ACCOUNTS_RECEIVABLE, Decimal("0"), amount),
                    ],
                    branch_id=branch_id,
                )
        elif direction == "SUPPLIER_OUT":
            return await self._post_journal(
                business_id=business_id,
                user_id=user_id,
                source_type="PAYMENT",
                source_id=payment_id,
                event="RECORDED",
                description=f"Supplier payment issued",
                journal_date=payment_date,
                lines=[
                    (ACCOUNT_ACCOUNTS_PAYABLE, amount, Decimal("0")),
                    (ACCOUNT_CASH_BANK, Decimal("0"), amount),
                ],
                branch_id=branch_id,
            )
        return None

    async def post_payment_voided(
        self,
        business_id: str,
        user_id: str,
        payment_id: str,
        amount: Decimal,
        direction: str,
        voided_date: datetime,
        branch_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Reverses the payment journal.
        Customer Payment Void: Debit AR (1200) / Credit Cash (1100).
        Supplier Payment Void: Debit Cash (1100) / Credit AP (2100).
        Idempotent: same payment_id + VOIDED event → same journal.
        """
        if amount <= Decimal("0"):
            return None

        if direction == "CUSTOMER_IN":
            return await self._post_journal(
                business_id=business_id,
                user_id=user_id,
                source_type="PAYMENT",
                source_id=payment_id,
                event="VOIDED",
                description=f"Reversal for voided customer payment",
                journal_date=voided_date,
                lines=[
                    (ACCOUNT_ACCOUNTS_RECEIVABLE, amount, Decimal("0")),
                    (ACCOUNT_CASH_BANK, Decimal("0"), amount),
                ],
                branch_id=branch_id,
            )
        elif direction == "SUPPLIER_OUT":
            return await self._post_journal(
                business_id=business_id,
                user_id=user_id,
                source_type="PAYMENT",
                source_id=payment_id,
                event="VOIDED",
                description=f"Reversal for voided supplier payment",
                journal_date=voided_date,
                lines=[
                    (ACCOUNT_CASH_BANK, amount, Decimal("0")),
                    (ACCOUNT_ACCOUNTS_PAYABLE, Decimal("0"), amount),
                ],
                branch_id=branch_id,
            )
        return None

    # ============================================================
    # PURCHASE INTEGRATION
    # ============================================================

    async def post_purchase_finalized(
        self,
        business_id: str,
        user_id: str,
        purchase_id: str,
        grand_total: Decimal,
        purchase_date: datetime,
        tax_total: Decimal = Decimal("0"),
        input_vat_creditable: bool = False,
        branch_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Journal: Debit Inventory Assets (1300) / Debit Input VAT (1400) / Credit Accounts Payable (2100).
        Triggered when Purchase status changes to FINALIZED.
        Idempotent: same purchase_id → same journal.
        """
        if grand_total <= Decimal("0"):
            return None

        lines = []
        if tax_total > Decimal("0") and input_vat_creditable:
            net_amount = grand_total - tax_total
            if net_amount > Decimal("0"):
                lines.append((ACCOUNT_INVENTORY_ASSETS, net_amount, Decimal("0")))
            lines.append((ACCOUNT_INPUT_VAT, tax_total, Decimal("0")))
        else:
            lines.append((ACCOUNT_INVENTORY_ASSETS, grand_total, Decimal("0")))

        lines.append((ACCOUNT_ACCOUNTS_PAYABLE, Decimal("0"), grand_total))

        return await self._post_journal(
            business_id=business_id,
            user_id=user_id,
            source_type="PURCHASE",
            source_id=purchase_id,
            event="FINALIZED",
            description="Purchase payable from finalized order",
            journal_date=purchase_date,
            lines=lines,
            branch_id=branch_id,
        )

    async def post_purchase_return_finalized(
        self,
        business_id: str,
        user_id: str,
        purchase_return_id: str,
        grand_total: Decimal,
        return_date: datetime,
        tax_total: Decimal = Decimal("0"),
        input_vat_creditable: bool = False,
        branch_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Journal: Debit Accounts Payable (2100) / Credit Inventory Assets (1300) / Credit Input VAT (1400).
        Reverses the original purchase payable posting.
        Idempotent: same purchase_return_id → same journal.
        """
        if grand_total <= Decimal("0"):
            return None

        lines = [(ACCOUNT_ACCOUNTS_PAYABLE, grand_total, Decimal("0"))]

        if tax_total > Decimal("0") and input_vat_creditable:
            net_amount = grand_total - tax_total
            if net_amount > Decimal("0"):
                lines.append((ACCOUNT_INVENTORY_ASSETS, Decimal("0"), net_amount))
            lines.append((ACCOUNT_INPUT_VAT, Decimal("0"), tax_total))
        else:
            lines.append((ACCOUNT_INVENTORY_ASSETS, Decimal("0"), grand_total))

        return await self._post_journal(
            business_id=business_id,
            user_id=user_id,
            source_type="PURCHASE_RETURN",
            source_id=purchase_return_id,
            event="FINALIZED",
            description="Purchase return reversal",
            journal_date=return_date,
            lines=lines,
            branch_id=branch_id,
        )

    # ============================================================
    # EXPENSE INTEGRATION
    # ============================================================

    async def post_expense_finalized(
        self,
        business_id: str,
        user_id: str,
        expense_id: str,
        amount: Decimal,
        expense_date: datetime,
        branch_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Journal: Debit General & Operational Expense (5100) / Credit Cash (1100).
        Triggered when Expense status changes to FINALIZED.
        Idempotent: same expense_id → same journal.
        """
        if amount <= Decimal("0"):
            return None

        return await self._post_journal(
            business_id=business_id,
            user_id=user_id,
            source_type="EXPENSE",
            source_id=expense_id,
            event="FINALIZED",
            description=f"Expense recorded",
            journal_date=expense_date,
            lines=[
                (ACCOUNT_GENERAL_EXPENSE, amount, Decimal("0")),
                (ACCOUNT_CASH_BANK, Decimal("0"), amount),
            ],
            branch_id=branch_id,
        )


accounting_integration_service = AccountingIntegrationService()
