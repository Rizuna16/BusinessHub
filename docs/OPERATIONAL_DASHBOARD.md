# Feature #44 — Business Operational Dashboard

**Status:** LOCKED

## 1. Purpose & Scope

Feature #44 provides a cross-module, read-only operational dashboard that aggregates key business metrics into a single view. It serves as a presentation/aggregation layer over existing data without modifying any locked features (#35–#43).

## 2. Dependencies

| Dependency | Feature # | Relationship |
|---|---|---|
| Sales Foundation | #22 | Reads finalized sales |
| Sales Return | #25 | Reads finalized returns |
| Sales Receivable | #26/#30 | Reads outstanding AR |
| Purchase Payable | #31 | Reads outstanding AP |
| Cash Account | #28 | Reads cash balances |
| Expense | #29 | Reads finalized expenses |
| Inventory Valuation | #38 | Reads inventory valuation |
| Authentication | #1 | JWT verification |
| Business Membership | #4/#5 | Active membership check |

## 3. Source of Truth

| KPI | Source |
|---|---|
| Revenue | `SalesInDB.grand_total` where `status = FINALIZED` and `sales_date` in range |
| Sales Returns | `SalesReturnInDB.grand_total` where `status = FINALIZED` and `return_date` in range |
| Net Revenue | `revenue.total - revenue.return_total` |
| Expenses | `ExpenseInDB.amount` where `status = FINALIZED` and `expense_date` in range |
| Net Operating Result | `revenue.net - expenses.total` |
| Cash Position | `CashSummaryResponse.total_cash_balance` (current snapshot) |
| AR Outstanding | `SalesReceivableSummaryResponse.total_outstanding_amount` |
| AP Outstanding | `PurchasePayableSummaryResponse.total_outstanding_amount` |
| Inventory Valuation | `ValuationSummaryResponse.total_inventory_value` |

## 4. Date Semantics

- `date_from` and `date_to` are inclusive calendar dates
- Internally converted to half-open UTC interval: `[date_from 00:00 UTC, date_to+1 00:00 UTC)`
- Both parameters are required

## 5. API

```
GET /api/v1/businesses/{business_id}/dashboard/operational
  ?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD&branch_id=optional
```

## 6. Net Operating Result

```
net_operating_result = revenue.net - expenses.total
```

This is NOT net profit. COGS is not subtracted.

## 7. Security

- JWT required
- Active membership required
- OWNER, ADMIN, MEMBER (read-only)
- Business-scoped

## 8. Limitations

- Net Operating Result does not include COGS
- Expense does not have branch_id in current schema
- Recent activity limited to 10 records
- No charts, export, or real-time updates
