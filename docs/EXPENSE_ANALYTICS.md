# FEATURE #45 — EXPENSE ANALYTICS WITH CATEGORY BREAKDOWN

**Status:** LOCKED
**Feature:** Expense Analytics with Category Breakdown
**Nature:** Enhancement + Analytics
**Architecture:** Read-Only
**Data Source:** Existing Expense Domain
**Database Change:** None
**Accounting Mutation:** None
**Tax Mutation:** None

---

## Purpose

Provide reliable period-based and category-based expense visibility using the existing Expense source of truth. Business owners can answer:

- "Berapa total expense bulan September?"
- "Berapa biaya Utilities bulan ini?"
- "Kategori expense mana yang paling besar?"

---

## Scope

### In Scope

1. Expense summary with date range filtering
2. Expense summary with optional category filtering
3. Expense total counting only FINALIZED expenses
4. Category breakdown aggregation
5. Optional category filter on breakdown
6. Read-only analytics endpoints
7. Frontend Expense Analytics page

### Out of Scope

- Charts, graphs, trend analysis
- Budget, budget vs actual, targets, forecasting
- Multi-currency analytics, FX conversion
- Tax analytics, cash flow calculations
- Accounting journal changes, P&L changes
- Database, ORM, migrations
- Expense mutations or workflow changes

---

## Business Rules

### Status Rule

Analytics counts only `FINALIZED` expenses:

```
total = SUM(expense.amount) WHERE expense.status == FINALIZED
expense_count = COUNT(expense records) WHERE expense.status == FINALIZED
```

DRAFT and CANCELLED expenses are excluded.

### Date Semantics

API accepts `date_from` and `date_to` as inclusive calendar dates:

```
date_from = 2026-09-01
date_to   = 2026-09-30
```

Internal interval: `[2026-09-01T00:00:00Z, 2026-10-01T00:00:00Z)`

Rules:
- Both parameters must be provided together (422 otherwise)
- `date_from > date_to` returns 422
- Invalid date returns 422

### Date Filter Authority

Filtering uses `Expense.expense_date`, not `created_at`, `updated_at`, or `finalized_at`.

### Business Scoping

Every query is scoped by `business_id` from the URL. Category lookup is business-scoped. Cross-business data is never returned.

---

## Category Aggregation

### Category Breakdown Output

```
category_id, category_code, category_name, total, expense_count
```

Formula:

```
category.total = SUM(expense.amount)
WHERE
  status == FINALIZED
  AND category_id == category
  AND expense_date IN selected range
```

### Category Ordering

Deterministic ordering:
1. `total DESC` (primary)
2. `category_name ASC` (secondary)
3. `category_id ASC` (tertiary)

### Category Filter

Optional. If not provided, all categories with finalized expenses in the period are returned. If provided, only that category is returned.

Foreign category ID (from another business) returns HTTP 404.

---

## Decimal Precision

All financial aggregation uses `Decimal`. No `float` calculations. No frontend financial computation.

Presentation: 2 decimal places for display.

---

## Currency

Single-currency aggregation following existing business convention. No multi-currency, FX conversion, or currency normalization.

---

## Security

### Authentication

All endpoints require JWT authentication with active business membership.

### Roles

All roles (OWNER, ADMIN, MEMBER) can read analytics. No write permissions.

### IDOR Protection

- Business A cannot read Business B expenses
- Business A cannot use Business B category_id
- Foreign category returns 404

---

## API

### Enhanced Summary Endpoint

```
GET /api/v1/businesses/{business_id}/expenses/summary
```

Query parameters (all optional):
- `date_from` (datetime) — start of date range
- `date_to` (datetime) — end of date range
- `category_id` (string) — optional category filter

**Behavior:** When called without date parameters, behaves identically to the pre-Feature-45 endpoint (backward compatible). When date parameters are provided, summary reflects only expenses within that range.

### New Analytics Endpoint

```
GET /api/v1/businesses/{business_id}/expenses/analytics/by-category
```

Query parameters:
- `date_from` (datetime, required)
- `date_to` (datetime, required)
- `category_id` (string, optional)

Response:

```json
{
  "date_from": "2026-09-01T00:00:00Z",
  "date_to": "2026-09-30T23:59:59Z",
  "total": "800000",
  "expense_count": 3,
  "categories": [
    {
      "category_id": "...",
      "category_code": "RENT",
      "category_name": "Rent",
      "total": "500000",
      "expense_count": 1
    }
  ]
}
```

### Error Codes

| Code | Condition |
|------|-----------|
| 401 | Invalid/missing authentication |
| 404 | Business not found, unauthorized membership, foreign category |
| 422 | Incomplete date range, reversed dates, invalid date format |

---

## Frontend

### Route

```
/businesses/:businessId/expenses/analytics
```

### Page Features

- Date range picker (from/to)
- Optional category dropdown filter
- Summary cards: Total Expense, Expense Count
- Category breakdown table: Category, Code, Expense Count, Total
- Loading state, error state, empty state
- Mobile-responsive layout

### Frontend Financial Authority

Frontend never calculates totals, counts, or percentages. All values are from the backend response. Frontend only performs formatting and display.

---

## Mathematical Invariants

For an unfiltered category breakdown:

```
sum(category.total) == summary.total
sum(category.expense_count) == summary.expense_count
```

These invariants are validated by tests.

---

## Files

### Created

| File | Purpose |
|------|---------|
| `backend/tests/test_expense_analytics.py` | Dedicated analytics tests |
| `frontend/src/types/expenseAnalytics.ts` | TypeScript types |
| `frontend/src/pages/ExpenseAnalytics.tsx` | Analytics page |
| `docs/EXPENSE_ANALYTICS.md` | This documentation |

### Modified

| File | Change |
|------|--------|
| `backend/app/modules/expense/schemas.py` | Added `CategoryBreakdownItem`, `ExpenseAnalyticsByCategoryResponse` |
| `backend/app/modules/expense/service.py` | Extended `get_summary` with filters, added `get_analytics_by_category` |
| `backend/app/modules/expense/router.py` | Added date/category query params to summary, new analytics endpoint |
| `frontend/src/services/apiClient.ts` | Extended `getExpenseSummary`, added `getExpenseAnalyticsByCategory` |
| `frontend/src/app/routes.tsx` | Added analytics route constant and route definition |

### Not Modified

All locked features (#35-#44) remain unchanged:
- Fiscal Period
- Financial Reporting
- Tax
- Inventory Valuation
- AR/AP Aging
- Cash Flow
- Statements
- Stock Card
- Product Profitability
- Operational Dashboard

---

## Testing

Dedicated test file: `backend/tests/test_expense_analytics.py`

Coverage includes:
- Summary with date/category filters
- Date validation rules (incomplete, reversed, invalid)
- Category breakdown correctness and ordering
- Category filter and IDOR protection
- Unauthenticated access rejection
- Decimal precision verification
- Invariant verification (sum of categories == summary total)
- Cross-business isolation
- Existing expense CRUD regression
- Accounting integration regression

---

## Production Gate

```
FEATURE #45 FINAL PRODUCTION GATE — PASS

STATUS: PRODUCTION PASS
LOCK STATUS: LOCKED
```

Gate checklist:
- [x] Finalized expenses only counted
- [x] Date filtering works correctly
- [x] Inclusive date boundaries work
- [x] Category filtering works
- [x] Category totals are correct
- [x] Category counts are correct
- [x] Summary and category breakdown reconcile
- [x] Decimal used throughout
- [x] No frontend financial calculation
- [x] Business isolation passes
- [x] Category IDOR protection passes
- [x] Existing expense CRUD remains intact
- [x] Existing expense summary backward compatible
- [x] No locked feature modified
- [x] Frontend TypeScript check passes
- [x] Frontend build passes
- [x] Dedicated tests pass
- [x] Regression tests pass
- [x] Documentation complete
