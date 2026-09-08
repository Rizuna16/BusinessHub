# FEATURE #33 — ACCOUNTING FOUNDATION DOCUMENTATION

## 1. Purpose & Scope
Accounting Foundation establishes the foundational financial event ledger for BusinessHub. It provides business-scoped Chart of Accounts (COA), double-entry Journal Entry posting, immutable financial history, General Ledger read models, and Trial Balance verification.

## 2. Source-of-Truth Boundaries
- **Operational Source of Truth**: Sales (#17), Purchase (#17), PurchaseReturn (#19), SalesReturn (#20), Expense (#29), Payment (#32), and CashAccount (#28) remain the sole operational sources of truth.
- **Accounting Source of Truth**: `JournalEntry` and `JournalLine` entities (`app/modules/accounting/repository.py`) represent the accounting financial event ledger. Accounting does NOT mutate operational balances directly.
- **Reconciliation**:
  - CashAccount: `CashAccount.opening_balance + Σ(CashMovement)`. Accounting Cash Account Ledger (`1100`) mirrors posted movements.
  - Receivable: Driven by `Sales.grand_total - Payment(CUSTOMER_IN)`. Accounting AR Ledger (`1200`) mirrors postings.
  - Payable: Driven by `Purchase.grand_total - PurchaseReturn.grand_total - Payment(SUPPLIER_OUT)`. Accounting AP Ledger (`2100`) mirrors postings.

## 3. Chart of Accounts (COA)
Default system accounts provisioned automatically per business:
- **ASSET (Normal Balance: DEBIT)**: `1000 ASSETS`, `1100 Cash & Bank`, `1200 Accounts Receivable`, `1300 Inventory Assets`.
- **LIABILITY (Normal Balance: CREDIT)**: `2000 LIABILITIES`, `2100 Accounts Payable`.
- **EQUITY (Normal Balance: CREDIT)**: `3000 EQUITY`, `3100 Owner Equity`.
- **REVENUE (Normal Balance: CREDIT)**: `4000 REVENUE`, `4100 Sales Revenue`.
- **EXPENSE (Normal Balance: DEBIT)**: `5000 EXPENSES`, `5100 General & Operational Expense`, `5200 Cost of Goods Sold`.

System accounts (`is_system=True`) cannot be deleted or archived. Custom accounts support code uniqueness per business and parent-child hierarchy validation.

## 4. Financial Invariants & Double-Entry Accounting
- **Double-Entry Invariant**: `SUM(debit) == SUM(credit)` for every posted journal entry. Unbalanced journal creation requests are strictly rejected with HTTP 400.
- **Line Non-Negativity Invariant**: `debit >= 0` and `credit >= 0`. Negative amounts are rejected.
- **Line XOR Invariant**: A single line cannot have both `debit > 0` and `credit > 0`. Each line represents either debit or credit.

## 5. Journal Entry Lifecycle & Immutability
- **POSTED**: Journal entries created via `create_and_post_journal` are immediately posted and immutable.
- **VOIDED**: Reversal retains auditability; historical posted lines are excluded from ledger balance calculation upon voiding (`voided_by_user_id`, `voided_at`). Posted journals are never hard-deleted.

## 6. Accounting Period & Date Guards
- Accounting period check verifies if the check date falls in a `CLOSED` period. Postings in closed periods are rejected with HTTP 400.

## 7. Security & Multi-Tenancy
- **Authentication**: `get_current_user` OAuth2 Bearer enforced across all endpoints.
- **Authorization**: Journal posting and account modification require `OWNER` or `ADMIN` role.
- **Tenant & IDOR Protection**: Accounts and journals are strictly scoped to `business_id`. Cross-tenant references (e.g. Business A trying to post using Business B's account) are rejected with HTTP 404 / 400 anti-enumeration protection.

## 8. API Endpoints
- `GET /api/v1/businesses/{business_id}/accounting/accounts`: List Chart of Accounts.
- `POST /api/v1/businesses/{business_id}/accounting/accounts`: Create custom account.
- `GET /api/v1/businesses/{business_id}/accounting/accounts/{account_id}`: Account detail.
- `PATCH /api/v1/businesses/{business_id}/accounting/accounts/{account_id}`: Update account.
- `DELETE /api/v1/businesses/{business_id}/accounting/accounts/{account_id}`: Archive custom account.
- `GET /api/v1/businesses/{business_id}/accounting/journals`: List journal entries.
- `POST /api/v1/businesses/{business_id}/accounting/journals`: Create & post journal entry.
- `GET /api/v1/businesses/{business_id}/accounting/journals/{journal_id}`: Journal detail.
- `POST /api/v1/businesses/{business_id}/accounting/journals/{journal_id}/void`: Void journal entry.
- `GET /api/v1/businesses/{business_id}/accounting/ledger/{account_id}`: General Ledger per account.
- `GET /api/v1/businesses/{business_id}/accounting/trial-balance`: Trial Balance.

## 9. Limitations
- **PostgreSQL Runtime**: DOCUMENTED — NOT RUNTIME VERIFIED (In-Memory execution environment).
- **Concurrency**: DOCUMENTED — NOT RUNTIME VERIFIED (In-Memory execution environment).
- **Future Integration (#34+)**: Automated event listeners connecting Sales/Purchase/Payment to automatic Journal Entry creation deferred to Feature #34 Accounting Integration.
