# Feature #29 — Expense (Pengeluaran Operasional)

## Overview
Feature #29 provides operational expense management for BusinessHub businesses. It allows businesses to record, categorize, and track business expenses with proper historical auditability and financial boundary isolation.

## Architecture
The module strictly adheres to an operational expense document layer. It does NOT introduce Accounting LEDGER features such as Journal Entries, COGS, or future Payable behavior.

### Domain Models

**`ExpenseCategory`**
- `id`, `business_id`, `name`, `code`, `description`, `status` (`ACTIVE`, `ARCHIVED`), `created_at`, `updated_at`.

**`Expense`**
- `id`, `business_id`, `expense_number` (`EXP-000001`), `expense_date`, `category_id`, `cash_account_id` (optional), `supplier_id` (optional), `amount`, `currency`, `description`, `status` (`DRAFT`, `FINALIZED`, `CANCELLED`), audit fields (`created_by_user_id`, `finalized_by_user_id`, `cancelled_by_user_id`), timestamps (`created_at`, `updated_at`, `finalized_at`, `cancelled_at`).

### Expense Lifecycle
```
DRAFT
 ├── FINALIZED (terminal historical posting; optionally posts CASH_OUT to CashAccount)
 └── CANCELLED (terminal cancellation of a draft)
```
- `FINALIZED` and `CANCELLED` are strictly terminal.
- Only `DRAFT` supports mutation.
- `FINALIZED → CANCELLED` and `CANCELLED → FINALIZED` are explicitly rejected.

## Cash Account Integration (#28)
- `cash_account_id` is optional.
- If a `FINALIZED` expense includes a valid `CASH`/`E_WALLET`/`OTHER` active cash account, a single `CASH_OUT` movement (`movement_type=EXPENSE`, `direction=OUT`) is posted exactly once using `reference_type=EXPENSE` + `reference_id=expense_id` for idempotent duplicate protection.
- `DRAFT` expenses never post cash movements.
- Insufficient balance in `CASH`/`E_WALLET` prevents expense finalization atomically.
- Transfer atomicity is inherited from Feature #28's atomic movement logic.

## Supplier Boundary
- `supplier_id` is optional. Validated `ACTIVE` supplier within same business.
- Expense does not create Purchase, Receiving, or inventory mutation.

## Payment Engine Boundary
- `Expense` does NOT create `ExpensePayment`; future Payment Engine (#32) owns cross-domain payment behaviors.

## API Endpoints
```http
GET    /api/v1/businesses/{business_id}/expense-categories
POST   /api/v1/businesses/{business_id}/expense-categories
PATCH  /api/v1/businesses/{business_id}/expense-categories/{category_id}
POST   /api/v1/businesses/{business_id}/expense-categories/{category_id}/archive

GET    /api/v1/businesses/{business_id}/expenses
POST   /api/v1/businesses/{business_id}/expenses
GET    /api/v1/businesses/{business_id}/expenses/summary
GET    /api/v1/businesses/{business_id}/expenses/{expense_id}
PATCH  /api/v1/businesses/{business_id}/expenses/{expense_id}
POST   /api/v1/businesses/{business_id}/expenses/{expense_id}/finalize
POST   /api/v1/businesses/{business_id}/expenses/{expense_id}/cancel
```

## Security & RBAC
- All endpoints require active business membership. Nonmembers / removed members receive `404 Not Found`.
- Mutations restricted to `OWNER` / `ADMIN`. `MEMBER` is read-only.

## Data Integrity & Atomicity
- Every mutation affecting money is atomic: `validate → calculate → mutate → persist`.
- `Expense FINALIZED` + `CashMovement EXPENSE` is an all-or-nothing operation.
```python
# Future PostgreSQL:
BEGIN;
SELECT cash_account FOR UPDATE;
validate balance;
insert cash movement (EXPENSE, OUT);
finalize expense;
COMMIT;
```

## PostgreSQL Readiness
Recommended indexes:
- `expense`: `(business_id, status, expense_date)`
- `expense`: `(business_id, expense_number)`
- `expense_category`: `(business_id, code)`
- `cash_movement`: `(business_id, reference_type, reference_id)` for idempotent posting verification
