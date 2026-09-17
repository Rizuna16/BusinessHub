# Feature #43 — Product Profitability & Gross Margin Analytics

**Status:** LOCKED

## 1. Purpose & Scope

Feature #43 provides a read-only analytics report for Product Profitability and Gross Margin. It derives profitability from existing finalized sales and immutable historical COGS snapshots established by Feature #38 (Perpetual MAC).

**Authoritative Formulas:**
```
Net Revenue     = Grand Total − Tax Total
COGS            = Σ SalesLine.cost_total_snapshot
Gross Profit    = Net Revenue − COGS
Gross Margin %  = (Gross Profit / Net Revenue) × 100
```
When Net Revenue = 0: Gross Margin % = null.

## 2. Dependencies

| Dependency | Feature # | Relationship |
|---|---|---|
| Sales Foundation | #22 | Required — sales orders and lines |
| Sales Return | #25 | Required — return orders and lines |
| Inventory Valuation & COGS | #38 | Required — cost snapshots on sales lines |
| Fiscal Period Management | #35 | Optional — period-based date filtering |
| Product / Variant / Category | #10-#12 | Required — dimensional metadata |
| Customer | #20 | Required — customer dimension |
| Branch | #11 | Required — branch dimension |

## 3. Source of Truth

| Metric | Source |
|---|---|
| Revenue | `SalesLineInDB.line_total − SalesLineInDB.tax_amount` |
| COGS | `SalesLineInDB.cost_total_snapshot` (or `Decimal("0")` if None) |
| Tax | `SalesLineInDB.tax_amount` (excluded from profit) |
| Discount | `SalesLineInDB.discount_amount` |
| Units | `SalesLineInDB.quantity` |

## 4. Return Treatment

- Only `SalesReturnStatus.FINALIZED` returns are included.
- Return attribution follows the **original sale/line** (not the return header).
- Revenue reversals use proportional ratio against original sales line.
- COGS reversals use original `SalesLine.unit_cost_snapshot` (never current MAC).
- `return_count` = unique finalized return header IDs per group.

## 5. Group-by Dimensions

- `product` — by product_id
- `variant` — by variant_id (with "Standard / No Variant" for non-variant sales)
- `category` — by product's current `category_id`
- `customer` — by customer_id (with "Walk-in / Cash Sales" for null)

## 6. Date Semantics

- `date_from` and `date_to` are **inclusive calendar dates**.
- Internally converted to half-open UTC interval: `[date_from 00:00 UTC, date_to+1 00:00 UTC)`.
- Optional `period_id` overrides date range (Feature #35).

## 7. Category Limitation

> "Historical profitability by category uses the product's current category assignment. If a product is reassigned to another category after a historical sale, the historical sale appears under the current category."

## 8. Service Products

Service lines are included with COGS = 0 when `unit_cost_snapshot` is None.

## 9. Security

- JWT required.
- Active business membership required.
- Roles: OWNER, ADMIN, MEMBER (read-only).
- All queries business-scoped.

## 10. API

```
GET /api/v1/businesses/{business_id}/reports/product-profitability
```

Parameters: `period_id`, `date_from`, `date_to`, `group_by`, `branch_id`, `product_id`, `variant_id`, `category_id`, `customer_id`.
