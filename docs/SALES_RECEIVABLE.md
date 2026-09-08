# Feature #26 — Sales Receivable (Piutang)

## Overview
Sales Receivable is an operational receivable view domain built on top of:
- Feature #22 Sales Foundation (`Sales` header and lines)
- Feature #23 Sales Payment Foundation (`SalesPayment`)
- Feature #24 Sales → Inventory Integration (`SALE_OUT` movement)
- Feature #25 Sales Return (`SALE_RETURN_IN` movement)

It provides real-time visibility into outstanding customer balances, payment statuses, and business-wide receivable metrics.

## Architectural Principles
1. **Derived Read Model (Option A):** No separate `SalesReceivable` persistent database table is maintained. Receivable state is derived dynamically from `Sales.grand_total` and `SalesPayment` records (`status == RECORDED`).
2. **Single Source of Truth:**
   - `Sales.grand_total` remains the single source of truth for transaction total.
   - `SalesPayment` remains the single source of truth for payment transactions.
3. **Operational Scope:** This module is an **operational view**, NOT a full double-entry accounting engine (no General Ledger, COGS, Tax, or AR Ledger mutation).

## Receivable Calculations
- `gross_receivable` = `Sales.grand_total`
- `paid_amount` = `SUM(SalesPayment.amount)` WHERE `status == RECORDED`
- `outstanding_amount` = `max(0, Sales.grand_total - paid_amount)`

### Receivable Statuses
- **`UNPAID`**: `grand_total > 0` AND `paid_amount == 0`
- **`PARTIALLY_PAID`**: `0 < paid_amount < grand_total`
- **`PAID`**: `paid_amount >= grand_total` (or `grand_total == 0`)

## Boundaries
- **Sales Return Boundary:** `Sales Return` (Feature #25) manages inventory stock returns (`SALE_RETURN_IN`). It does NOT mutate receivable balances or issue financial refunds automatically.
- **Payment Boundary:** Feature #26 provides read-only views of receivables. Payment recording/cancellation is strictly owned by `sales_payment` (Feature #23).
- **Sales Boundary:** Receivable views are available only for `FINALIZED` sales orders. `DRAFT` and `CANCELLED` sales are excluded.

## API Endpoints
- `GET /api/v1/businesses/{business_id}/receivables`: List receivable records for `FINALIZED` sales with filtering (`status`, `customer_id`, `branch_id`, `date_from`, `date_to`, `search`) and pagination.
- `GET /api/v1/businesses/{business_id}/receivables/summary`: Aggregate receivable metrics (`total_sales_amount`, `total_paid_amount`, `total_outstanding_amount`, status counts).
- `GET /api/v1/businesses/{business_id}/receivables/customer-summary`: Outstanding metrics aggregated per customer.
- `GET /api/v1/businesses/{business_id}/receivables/{sales_id}`: Detailed receivable record for a specific sales order including full payment history.

## RBAC & Security
- **Access Control:** Requires active business membership (`OWNER`, `ADMIN`, `MEMBER` read-only). Non-members or removed members receive `404 Not Found`.
- **Tenant Isolation:** All queries are strictly scoped by `business_id`. Cross-tenant lookups fail with `404 Not Found` (anti-enumeration).

## PostgreSQL Future Concurrency & Optimization
- **Concurrent Payment Acceptance:** Payment creation in Feature #23 should acquire a row lock (`SELECT FOR UPDATE` on `Sales`) to prevent concurrent payment race conditions (`SUM(active payments) <= Sales.grand_total`).
- **Recommended Indexes:**
  - `sales`: `(business_id, status, sales_date, customer_id, branch_id)`
  - `sales_payment`: `(business_id, sales_id, status, payment_date)`
