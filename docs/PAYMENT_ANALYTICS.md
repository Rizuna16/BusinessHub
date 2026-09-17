# FEATURE #48 — PAYMENT ANALYTICS WITH METHOD & DIRECTION BREAKDOWN

**Status:** PRODUCTION PASS / LOCKED
**Feature:** Payment Analytics with Method & Direction Breakdown
**Nature:** Enhancement + Analytics
**Architecture:** Read-Only
**Data Source:** Existing Payment/InDB (unified payment engine)
**Database Change:** None
**Accounting Mutation:** None
**Inventory Mutation:** None

---

## Purpose

Provide reliable period-based, direction-based, and payment-method-based visibility into payment activity using the existing unified payment engine as the source of truth.

---

## Source-of-Truth

### Authoritative Source: `PaymentInDB` (unified payment engine)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Payment ID |
| `business_id` | `str` | Tenant scoping |
| `branch_id` | `str` | Branch scoping |
| `direction` | `PaymentDirection` | `CUSTOMER_IN` / `SUPPLIER_OUT` |
| `target_type` | `PaymentTargetType` | `SALES` / `PURCHASE` |
| `target_id` | `str` | Reference to sales or purchase |
| `payment_date` | `datetime` | **Authoritative economic date** |
| `payment_method` | `PaymentMethod` | 7 values |
| `amount` | `Decimal` | Payment amount |
| `currency` | `str` | Always IDR in current domain |
| `cash_account_id` | `str` | Links to CashAccount |
| `status` | `PaymentStatus` | `RECORDED` (economic) / `VOIDED` (non-economic) |
| `voided_at` | `Optional[datetime]` | Set when voided |
| `created_at` | `datetime` | Creation timestamp |

### Dual Payment System Reconciliation

| Economic Event | payment/ | sales_payment/ | Duplicate Risk | Authority |
|----------------|----------|-----------------|----------------|-----------|
| Customer payment (SALES collection) | `PaymentInDB` | `SalesPaymentInDB` | Possible if both record | `PaymentInDB` |
| Supplier payment (PURCHASE disbursement) | `PaymentInDB` | Not applicable | No duplicate | `PaymentInDB` |
| Per-sale detail payment | Not created | `SalesPaymentInDB` | Separate system | `SalesPaymentInDB` |

**Payment Analytics uses only `PaymentInDB`.** `sales_payment/` is a detail subsystem and not in scope.

---

## Business Problem

Business owners can view payment transactions but have no analytical layer: no period summaries, no direction breakdown (customer-in vs supplier-out), no payment-method breakdown, no void-adjusted views.

Feature #48 answers:

- Berapa total pembayaran pada periode ini?
- Berapa pemasukan vs pengeluaran?
- Metode pembayaran mana yang paling sering digunakan?
- Bagaimana aliran pembayaran bersih?
- Berapa persentase pembayaran yang dibatalkan?

---

## Status Semantics

- `RECORDED` — economic event, counted in all financial metrics
- `VOIDED` — non-economic state, excluded from financial totals, reported as operational statistics

Voided payments are counted in `voided_count` and `voided_amount` but excluded from `gross_recorded`, `net_payment_flow`, `payment_count`, and all breakdown totals.

---

## Cross-Period Void Behavior

If a payment is recorded on 2026-09-01 and voided on 2026-09-05, analytics for 2026-09-01 will show 0 recorded (because the record is now VOIDED at query time). This is a current-state limitation, not historical reconstruction. `voided_at` is stored but the analytics layer uses current status.

**Known limitation:** Historical analytics may not perfectly reconstruct the state at a past date. Documented limitation, not a silent fix.

---

## Date Semantics

- `date_from` and `date_to` are inclusive calendar dates
- Both REQUIRED: missing → `422`
- `date_from > date_to` → `400`
- Malformed date → `422`
- Internal: `[start_datetime, end_datetime_inclusive]` using `payment_date`

---

## Financial Formulas

| Metric | Formula |
|--------|---------|
| Gross Recorded | `SUM(payment.amount WHERE status=RECORDED in period)` |
| Customer In Total | `SUM(amount WHERE RECORDED AND direction=CUSTOMER_IN)` |
| Supplier Out Total | `SUM(amount WHERE RECORDED AND direction=SUPPLIER_OUT)` |
| Net Payment Flow | `customer_in_total - supplier_out_total` |
| Payment Count | `COUNT(RECORDED payments in period)` |
| Average Payment Value | `gross_recorded / payment_count` (0.00 if count=0) |
| Voided Count | `COUNT(VOIDED in period)` |
| Voided Amount | `SUM(amount WHERE VOIDED in period)` |

All monetary aggregation uses `Decimal`. No `float` calculations.

---

## Filters

All filters applied server-side. Frontend never aggregates.

| Filter | Type | Behavior |
|--------|------|----------|
| `date_from` | `datetime` | Required, inclusive |
| `date_to` | `datetime` | Required, inclusive |
| `branch_id` | `Optional[str]` | Foreign → `404` |
| `direction` | `Optional[PaymentDirection]` | Filters by payment direction |
| `payment_method` | `Optional[PaymentMethod]` | Filters by payment method |

---

## Breakdown Endpoints

### By Direction

`GET /api/v1/businesses/{business_id}/payments/analytics/by-direction`

Breakdown by `CUSTOMER_IN` vs `SUPPLIER_OUT`. Ordering: `amount DESC`, `direction ASC`.

### By Method

`GET /api/v1/businesses/{business_id}/payments/analytics/by-method`

Breakdown by 7 payment methods. Ordering: `amount DESC`, `payment_method ASC`.

---

## Reconciliation Invariants

- `SUM(by-direction.amount) == summary.gross_recorded`
- `SUM(by-direction.payment_count) == summary.payment_count`
- `SUM(by-method.amount) == summary.gross_recorded`
- `SUM(by-method.payment_count) == summary.payment_count`

All invariants hold within the same filtered dataset. VOIDED records excluded from reconciliation.

---

## Security

- JWT + active business membership required
- OWNER / ADMIN / MEMBER can read analytics (read-only)
- Business-scoped: all queries filtered by `business_id`
- Branch IDOR: foreign branch → `404`
- Cross-business access: `404` (anti-enumeration)
- No mutation endpoints

---

## Frontend

- Route: `/businesses/:businessId/payments/analytics`
- Page: `frontend/src/pages/PaymentAnalytics.tsx`
- Types: `frontend/src/types/paymentAnalytics.ts`
- API Client: `frontend/src/services/apiClient.ts`

### Layout

```
Header: Payment Analytics
Filters: [Date From] [Date To] [Direction] [Payment Method]
Cards:  Recorded Payments | Customer In | Supplier Out | Net Payment Flow | Payment Count | Average
Tables: Direction Breakdown | Method Breakdown
States: loading / error / empty / success
```

Frontend performs no financial calculation. Backend response is authoritative.

---

## Accounting / Cash Flow Boundaries

- Feature #48 is read-only — no journal mutations, no cash balance changes, no inventory impact
- Cash Flow (#40) and Accounting (#33/#34) remain authoritative for their domains
- Payment analytics only reads `PaymentInDB` and does not recalculate AR/AP

---

## File Impact

### Created
- `backend/tests/test_payment_analytics.py` — 50 dedicated tests
- `frontend/src/types/paymentAnalytics.ts` — analytics type definitions
- `frontend/src/pages/PaymentAnalytics.tsx` — analytics page
- `docs/PAYMENT_ANALYTICS.md` — this document

### Modified
- `backend/app/modules/payment/schemas.py` — added 3 analytics response schemas
- `backend/app/modules/payment/service.py` — added 3 analytics service methods + branch validation helper
- `backend/app/modules/payment/router.py` — added 3 GET analytics endpoints
- `frontend/src/services/apiClient.ts` — added 3 payment analytics API methods
- `frontend/src/app/routes.tsx` — added `BUSINESS_PAYMENT_ANALYTICS` route constant, import, and route component

---

## Testing

- Dedicated suite: `backend/tests/test_payment_analytics.py` — 50 tests
- Relevant regression: payment engine (11), cash account (10), sales payments (11), inventory valuation (16), product profitability (29), dashboard (20), sales analytics (35), expense analytics (4), purchase analytics (50) — all green
- Full backend regression: 1127 passed / 0 failed
- Frontend: TypeScript (`tsc -b`) PASS, build (`vite build`) PASS

---

## Status

**FEATURE #48 — PAYMENT ANALYTICS**
**STATUS: PRODUCTION PASS / LOCKED**

---

`FEATURE #48 — DISCOVERY COMPLETE`
