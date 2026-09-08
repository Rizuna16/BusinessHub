# FEATURE #31 — PAYABLE ENGINE DOCUMENTATION

## 1. Architecture & Domain Ownership
- **Architecture**: Hybrid derived domain engine.
- **Authoritative Sources**:
  - `Purchase.grand_total` (Feature #17) is the authoritative source for `gross_payable`.
  - `PurchaseReturn.grand_total` (Feature #19) for `FINALIZED` non-deleted returns is the authoritative source for `return_adjustment`.
  - `paid_amount` defaults to `0` and is non-negative. Supplier payment settlement is owned by #32 Payment Engine.
- **Domain Boundaries**:
  - Read-only integration with Purchase (#17), Receiving (#18), Purchase Return (#19), Supplier (#16), and Branch (#3).
  - DOES NOT mutate StockBalance, StockMovement, InventoryLocation, CashAccount balance, CashMovement, Expense, Sales, SalesPayment, or General Ledger.

## 2. Financial Formulas & Calculations
- `gross_payable = max(0, Purchase.grand_total)`
- `return_adjustment = sum(PurchaseReturn.grand_total)` for all `FINALIZED` non-deleted returns belonging to the purchase.
- `net_payable = max(0, gross_payable - return_adjustment)`
- `paid_amount = 0` (non-negative Decimal)
- `outstanding_amount = max(0, net_payable - paid_amount)`

## 3. Payable Status Logic
- `UNPAID`: `paid_amount == 0` and `net_payable > 0`
- `PARTIALLY_PAID`: `paid_amount > 0` and `paid_amount < net_payable`
- `PAID`: `net_payable == 0` or `paid_amount >= net_payable`

## 4. Purchasing & Receiving Lifecycle Rules
- Only `FINALIZED` purchases generate payables. `DRAFT` and `CANCELLED` purchases are excluded.
- `Receiving` records (#18) affect physical stock balance and physical receiving status, but DO NOT create separate payables or alter payable calculation (invoice/purchase based financial model).
- Only `FINALIZED` `PurchaseReturn` records (#19) adjust payable balance. `DRAFT` and `CANCELLED` returns do not reduce payable amount.

## 5. Multi-Currency Handling
- Currency normalization defaults to `IDR`.
- No mixed-currency numeric aggregation is performed. Currency filtering is supported on all endpoints.

## 6. Security & Multi-Tenancy
- All endpoints enforce active business membership via `BusinessMembershipService`.
- Multi-tenant data isolation strictly enforced by `business_id`.
- Supplier and Branch access validated within business scope; cross-tenant requests return 404 anti-enumeration or 403 denial.

## 7. API Endpoints
- `GET /api/v1/businesses/{business_id}/purchases/payables`: List payables with status/supplier/branch/currency/search filtering and pagination.
- `GET /api/v1/businesses/{business_id}/purchases/payables/summary`: Business-level payable metrics.
- `GET /api/v1/businesses/{business_id}/purchases/payables/suppliers/summary`: Supplier-aggregated payable metrics.
- `GET /api/v1/businesses/{business_id}/purchases/payables/{purchase_id}`: Payable detail per purchase.

## 8. Limitations
- PostgreSQL Runtime: DOCUMENTED — NOT RUNTIME VERIFIED (In-Memory execution context).
- Concurrency: DOCUMENTED — NOT RUNTIME VERIFIED (In-Memory execution context).
- Future #32 Payment Engine Integration: Ready for payment record aggregation when #32 is implemented.
