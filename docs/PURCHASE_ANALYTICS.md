# FEATURE #47 — PURCHASE ANALYTICS WITH CATEGORY & SUPPLIER BREAKDOWN

**Status:** PRODUCTION PASS / LOCKED

---

## Purpose

Provide reliable period-based, category-based, and supplier-based purchase visibility using the existing Purchase and Purchase Return sources of truth.

---

## Source of Truth

- **Purchases**: `PurchaseInDB` — only `PurchaseStatus.FINALIZED` counts
- **Purchase Returns**: `PurchaseReturnInDB` — only `PurchaseReturnStatus.FINALIZED` counts
- **Category**: Derived from `Product.category_id` via `PurchaseLine.product_id` (current-state only)
- **Supplier**: `PurchaseInDB.supplier_id` (mandatory, no walk-in)
- **Branch**: `PurchaseInDB.branch_id`

---

## Date Semantics

- Purchases anchored to `purchase_date`
- Both `date_from` and `date_to` required
- Inclusive on both ends

## Return Date Semantics

**Design Lock originally assumed** `PurchaseReturnInDB` would have a `return_date` field.

**Actual domain verification:** `PurchaseReturnInDB` does **NOT** have a `return_date` field. The only available date fields are `created_at`, `updated_at`, `finalized_at`, and `cancelled_at`.

The accounting integration uses `r_updated.created_at` as the `return_date` parameter for journal entries. Therefore `created_at` is the authoritative economic-effective date for purchase returns in this domain.

**Implementation uses `created_at` as the return activity date for analytics period attribution.**

**Design Lock reconciliation:** The design spec's assumption of `return_date` is reconciled to `created_at` based on actual domain evidence. No new field is added to the domain model.

---

## Metrics

| Metric | Formula |
|--------|---------|
| Gross Purchases | `SUM(purchase.grand_total)` — finalized, in period |
| Purchase Returns | `SUM(return.grand_total)` — finalized, in period |
| Net Purchases | `gross_purchases - purchase_returns` |
| Discount Total | `SUM(purchase.discount_total)` |
| Tax Total | `SUM(purchase.tax_total)` |
| Purchase Count | `COUNT(distinct finalized purchases in period)` |
| Average Purchase Value | `gross_purchases / purchase_count` (or 0.00) |

---

## API Endpoints

| Endpoint | Method | Required | Optional |
|----------|--------|----------|----------|
| `/purchases/analytics/summary` | GET | `date_from`, `date_to` | `supplier_id`, `category_id`, `branch_id` |
| `/purchases/analytics/by-supplier` | GET | `date_from`, `date_to` | `supplier_id`, `category_id`, `branch_id` |
| `/purchases/analytics/by-category` | GET | `date_from`, `date_to` | `supplier_id`, `category_id`, `branch_id` |

---

## Receiving Boundary

Receiving is NOT counted as a purchase. Purchase FINALIZED is the authoritative economic event. Returns require finalized receiving before they can be created (domain constraint).

---

## Known Limitations

1. **Category**: Current-state only (no historical snapshot)
2. **Purchase Return Date**: No explicit `return_date` field; `created_at` used as proxy

---

## Testing

50 dedicated tests covering: finalized/draft/cancelled inclusion, date boundaries, returns, supplier/category aggregation, deterministic ordering, reconciliation, security, Decimal precision, empty data, multi-line purchases, return category/supplier attribution, Decimal precision, large amounts.

---

**FEATURE #47 — PURCHASE ANALYTICS**
**STATUS: PRODUCTION PASS / LOCKED**
