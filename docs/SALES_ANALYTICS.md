# FEATURE #46 — SALES ANALYTICS WITH CATEGORY & CUSTOMER BREAKDOWN

**Status:** PRODUCTION PASS / LOCKED
**Feature:** Sales Analytics with Category & Customer Breakdown
**Nature:** Enhancement + Analytics
**Architecture:** Read-Only
**Data Source:** Existing Sales & Sales Return domains
**Database Change:** None
**Accounting Mutation:** None
**Tax Mutation:** None
**Inventory Mutation:** None

---

## Purpose

Provide reliable period-based, category-based, and customer-based sales visibility using the existing Sales and Sales Return sources of truth. Complements:
- Feature #43 — Product Profitability
- Feature #44 — Operational Dashboard
- Feature #45 — Expense Analytics

---

## Scope

### In Scope

1. Sales summary with date range filtering
2. Sales summary with optional branch/customer/category filters
3. Gross sales, sales returns, net sales, discount total, tax total
4. Transaction count and average transaction value
5. Category breakdown with deterministic ordering
6. Customer breakdown with walk-in handling
7. Read-only analytics endpoints
8. Frontend Sales Analytics page

### Out of Scope

- Charts, graphs, forecasting, targets, commissions
- Multi-currency, FX conversion
- Tax rule changes, accounting changes
- Inventory changes, COGS recalculation
- Payment analytics, purchase analytics
- Super Admin, database, ORM, migrations

---

## Business Rules

### Status Rule

Analytics counts only `FINALIZED` sales and `FINALIZED` sales returns.

### Date Semantics

- `date_from` and `date_to` are inclusive calendar dates
- Internal interval: `[start_datetime, end_datetime_exclusive)`
- Both must be provided together (422 otherwise)
- `date_from > date_to` returns 400

### Return Semantics

- Returns are anchored by their own return date
- In current domain, `return_date = sales.sales_date` (set by sales return service)
- Returns are always in the same period as the original sale
- Only finalized returns counted

### Category Attribution

- Derived from `Product.category_id` via `SalesLine.product_id`
- Current-state only (no historical snapshot)
- Documented limitation: historical category analytics may reflect current product category

### Customer Attribution

- Derived from `SalesInDB.customer_id`
- Walk-in sales (`customer_id = None`) represented as `WALK_IN`

---

## API Endpoints

### Sales Summary

```
GET /api/v1/businesses/{business_id}/sales/analytics/summary
```

Required: `date_from`, `date_to`
Optional: `branch_id`, `customer_id`, `category_id`

Response: `SalesAnalyticsSummaryResponse`

### Category Breakdown

```
GET /api/v1/businesses/{business_id}/sales/analytics/by-category
```

Required: `date_from`, `date_to`
Optional: `branch_id`, `customer_id`, `category_id`

Response: `SalesAnalyticsByCategoryResponse`

### Customer Breakdown

```
GET /api/v1/businesses/{business_id}/sales/analytics/by-customer
```

Required: `date_from`, `date_to`
Optional: `branch_id`, `category_id`, `customer_id`

Response: `SalesAnalyticsByCustomerResponse`

---

## Financial Formulas

- `gross_sales = SUM(sales.grand_total)` for finalized sales in period
- `sales_returns = SUM(return.grand_total)` for finalized returns in period
- `net_sales = gross_sales - sales_returns`
- `discount_total = SUM(sales.discount_total)` for finalized sales in period
- `tax_total = SUM(sales.tax_total)` for finalized sales in period
- `transaction_count = COUNT(distinct finalized sales in period)`
- `average_transaction_value = gross_sales / transaction_count` (or 0.00)

All calculations use `Decimal`. No float.

---

## Reconciliation Invariants

- `sum(category.net_sales) == summary.net_sales`
- `sum(customer.net_sales) == summary.net_sales`
- `sum(category.gross_sales) == summary.gross_sales`
- `sum(customer.gross_sales) == summary.gross_sales`

Transaction counts in breakdowns may differ from summary transaction count (single sale can span multiple categories).

---

## Security

- JWT authentication required
- Active business membership required
- OWNER / ADMIN / MEMBER can read analytics
- Business-scoped queries
- Foreign branch/customer/category → HTTP 404
- Cross-business access denied

---

## Domain Verification

| Field | Source |
|-------|--------|
| Sales date | `SalesInDB.sales_date` |
| Sales status | `SalesStatus.FINALIZED` |
| Return date | `SalesReturnInDB.return_date` (= `sales.sales_date`) |
| Return status | `SalesReturnStatus.FINALIZED` |
| Category | `Product.category_id` via `SalesLine.product_id` |
| Customer | `SalesInDB.customer_id` |
| Branch | `SalesInDB.branch_id` |
| Currency | Single currency per business (no `SalesInDB.currency` field) |

---

## Known Limitations

1. **Category historical accuracy**: Category derived from current `Product.category_id`, not historical snapshot
2. **Cross-period returns**: Not currently possible; `return_date` always equals original `sales.sales_date`
3. **Single currency**: No multi-currency analytics support

---

## Testing

Dedicated: `backend/tests/test_sales_analytics.py` (35 tests)

Covers:
- Status inclusion/exclusion
- Date boundaries
- Returns
- Category aggregation, filter, ordering, reconciliation
- Customer aggregation, filter, walk-in, ordering, reconciliation
- Branch filter
- Security (401, 404, cross-business)
- Decimal precision
- Empty data

Regression: All existing sales, sales return, accounting integration, and expense analytics tests pass.

---

## Files

### Created
- `backend/tests/test_sales_analytics.py`
- `frontend/src/types/salesAnalytics.ts`
- `frontend/src/pages/SalesAnalytics.tsx`
- `docs/SALES_ANALYTICS.md`

### Modified
- `backend/app/modules/sales/schemas.py` — Added analytics response schemas
- `backend/app/modules/sales/service.py` — Added analytics service methods + entity validation
- `backend/app/modules/sales/router.py` — Added analytics endpoints
- `frontend/src/services/apiClient.ts` — Added analytics API methods
- `frontend/src/app/routes.tsx` — Added analytics route

---

**FEATURE #46 — SALES ANALYTICS**
**STATUS: PRODUCTION PASS / LOCKED**
