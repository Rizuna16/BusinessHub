# Feature #39 — AR/AP Aging & Outstanding Balance Reporting

**Status:** LOCKED

## 1. Purpose & Scope

Feature #39 provides read-only aging and outstanding balance reporting for Accounts Receivable (AR) and Accounts Payable (AP). It calculates aging buckets, outstanding balances, and customer/supplier aggregations based on the existing Sales, Purchase, Payment, and Return engines.

## 2. Dependencies

| Dependency | Feature # | Relationship |
|---|---|---|
| Authentication | #2 | Required |
| Business / Tenant | #4 | Required |
| Business Membership | #5 | Required — RBAC |
| Branch | #6 | Required — branch filtering |
| Customer | #15 | Required — AR customer aggregation |
| Supplier | #16 | Required — AP supplier aggregation |
| Purchase Foundation | #17 | Required — AP source document |
| Purchase Return | #19 | Required — AP return adjustment |
| Sales Foundation | #22 | Required — AR source document |
| Sales Return | #25 | Required — AR return adjustment |
| Sales Receivable | #26 | Required — AR operational context |
| Payment Engine | #32 | Required — payment history |

## 3. Architecture Boundary

Feature #39 is a **read-only reporting/calculation layer**. It:

- Reads from existing Sales, Purchase, Payment, and Return repositories.
- Computes aging buckets and outstanding balances in real-time.
- Does NOT create, modify, or delete any entity.
- Does NOT post journal entries.
- Does NOT alter Account 1200 (AR), Account 2100 (AP), or any account.
- Does NOT interact with inventory, tax, or fiscal period systems.
- Is purely computed on-demand from source-of-truth data.

## 4. Aging Module Structure

```
backend/app/modules/aging/
├── __init__.py
├── utils.py        # AgingBucket enum, compute_aging_days, compute_aging_bucket
├── schemas.py      # AR/AP aging response schemas
└── service.py      # AgingService class
```

## 5. AR Aging

### 5.1 Formulas

For each eligible finalized Sales document:

```
original_amount = sales.grand_total
active_paid = SUM(payment.amount WHERE status == RECORDED AND payment_date <= as_of_date)
sales_return_adjustment = SUM(return.grand_total WHERE status == FINALIZED AND effective_date <= as_of_date)
outstanding = MAX(original_amount - sales_return_adjustment - active_paid, 0)
aging_days = (as_of_date - sales_date).days
```

### 5.2 Inclusion Rules

- Only `FINALIZED` sales are eligible.
- `DRAFT` and `CANCELLED` sales are excluded.
- Sales with `sales_date > as_of_date` are excluded.
- Zero-outstanding documents are excluded from aging rows.

### 5.3 Payment Semantics

- `PaymentStatus.RECORDED` payments count when `payment_date <= as_of_date`.
- `PaymentStatus.VOIDED` payments are excluded (always).

### 5.4 Sales Return Semantics

- Finalized returns count when `(r.finalized_at or r.return_date or r.created_at) <= as_of_date`.
- Returns reduce outstanding by their `grand_total`.

### 5.5 Aging Buckets

| Age (days) | Bucket | Value |
|---|---|---|
| `< 0` | Excluded | N/A (future documents filtered out) |
| `== 0` | `CURRENT` | Documents dated exactly on `as_of_date` |
| `1–30` | `1_30` | |
| `31–60` | `31_60` | |
| `61–90` | `61_90` | |
| `91–120` | `91_120` | |
| `> 120` | `OVER_120` | |

**Source:** `compute_aging_bucket` in `backend/app/modules/aging/utils.py` lines 22–35.

### 5.6 Customer Aggregation

- Customers with `customer_id` are aggregated by customer.
- Walk-in sales (`customer_id == None`) are grouped as `"Walk-in Customer"` with `customer_id = None`.
- No fake Customer entities are created.
- Customer totals reconcile exactly with invoice-level totals.

## 6. AP Aging

### 6.1 Formulas

For each eligible finalized Purchase document:

```
gross_payable = purchase.grand_total
return_adjustment = SUM(return.grand_total WHERE status == FINALIZED AND effective_date <= as_of_date)
active_paid = SUM(payment.amount WHERE status == RECORDED AND payment_date <= as_of_date)
net_payable = MAX(gross_payable - return_adjustment, 0)
outstanding = MAX(net_payable - active_paid, 0)
aging_days = (as_of_date - purchase_date).days
```

### 6.2 Inclusion Rules

- Only `FINALIZED` purchases are eligible.
- `DRAFT` and `CANCELLED` purchases are excluded.
- Purchases with `purchase_date > as_of_date` are excluded.
- Zero-outstanding documents are excluded.

### 6.3 Payment Semantics

Same as AR aging: `RECORDED` counts, `VOIDED` excluded.

### 6.4 Purchase Return Semantics

- Finalized returns count when `(r.finalized_at or r.created_at) <= as_of_date`.
- Returns reduce net payable by their `grand_total`.

### 6.5 Aging Buckets

Identical to AR aging buckets (Section 5.5).

### 6.6 Supplier Aggregation

- All purchases are aggregated by supplier.
- Supplier totals reconcile exactly with purchase-level totals.

## 7. As-of-Date Behavior

- **Parameter:** `as_of_date` (optional `datetime` query parameter).
- **Default:** Current UTC time (`datetime.now(timezone.utc)`).
- **Historical reconstruction:** Only events with economic dates `<= as_of_date` affect the report. Future payments, returns, and documents are excluded.
- **Deterministic:** Same `as_of_date` always produces the same result.

## 8. Walk-in / No Customer Handling

Sales with `customer_id == None` are walk-in sales. They are:
- Filtered when `customer_id == "WALK_IN"` query parameter is used.
- Aggregated under `customer_id = None` with `customer_name = "Walk-in Customer"`.
- No fake Customer records are created.

## 9. Filtering

| Filter | AR Endpoint | AP Endpoint | Behavior |
|---|---|---|---|
| `as_of_date` | Yes | Yes | Historical cutoff |
| `customer_id` | Yes | No | Filter by customer |
| `supplier_id` | No | Yes | Filter by supplier |
| `branch_id` | Yes | Yes | Filter by branch |
| `bucket` | Yes | Yes | Filter by aging bucket |

All filtering occurs server-side. Customer/supplier IDs are validated against the business scope.

## 10. Business Isolation & RBAC

- **Business scoping:** All queries are scoped to `business_id`.
- **Active membership:** `BusinessMembershipService.require_active_membership()` is called for every request.
- **Roles:** OWNER, ADMIN, and MEMBER can all read aging reports (read-only).
- **IDOR protection:** Foreign `customer_id`, `supplier_id`, or `branch_id` values raise HTTP 404 if not found in the business scope.

## 11. API Endpoints

### AR Aging

```
GET /api/v1/businesses/{business_id}/receivables/aging
```

**Query parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `as_of_date` | `datetime` | No | Default: now UTC |
| `customer_id` | `string` | No | Filter by customer |
| `branch_id` | `string` | No | Filter by branch |
| `bucket` | `AgingBucket` | No | Filter by aging bucket |

**Response:** `ARAgingResponse`

### AP Aging

```
GET /api/v1/businesses/{business_id}/purchases/payables/aging
```

**Query parameters:**
| Parameter | Type | Required | Description |
|---|---|---|---|
| `as_of_date` | `datetime` | No | Default: now UTC |
| `supplier_id` | `string` | No | Filter by supplier |
| `branch_id` | `string` | No | Filter by branch |
| `bucket` | `AgingBucket` | No | Filter by aging bucket |

**Response:** `APAgingResponse`

## 12. Response Schemas

### ARAgingResponse

| Field | Type |
|---|---|
| `as_of_date` | `datetime` |
| `summary` | `ARAgingSummary` |
| `customers` | `List[ARCustomerAgingSummaryItem]` |
| `invoices` | `List[ARInvoiceAgingItem]` |

### APAgingResponse

| Field | Type |
|---|---|
| `as_of_date` | `datetime` |
| `summary` | `APAgingSummary` |
| `suppliers` | `List[APSupplierAgingSummaryItem]` |
| `purchases` | `List[APInvoiceAgingItem]` |

### Aging Summary Fields (both AR and AP)

| Field | Description |
|---|---|
| `total_outstanding` | Sum of all outstanding amounts |
| `current` | Bucket: age == 0 |
| `bucket_1_30` | Bucket: 1–30 days |
| `bucket_31_60` | Bucket: 31–60 days |
| `bucket_61_90` | Bucket: 61–90 days |
| `bucket_91_120` | Bucket: 91–120 days |
| `bucket_over_120` | Bucket: >120 days |

**Invariant:** `total_outstanding == current + bucket_1_30 + bucket_31_60 + bucket_61_90 + bucket_91_120 + bucket_over_120`

## 13. Frontend

- **AR Aging Page:** `frontend/src/pages/ARAging.tsx`
  - Route: `/businesses/:businessId/receivables/aging`
  - Features: As-of-date picker, bucket filter, summary cards, customer aggregation tab, invoice detail tab.
- **AP Aging Page:** `frontend/src/pages/APAging.tsx`
  - Route: `/businesses/:businessId/purchases/payables/aging`
  - Features: As-of-date picker, bucket filter, summary cards, supplier aggregation tab, purchase detail tab.
- **Types:** `frontend/src/types/aging.ts`
- **API Methods:**
  - `apiClient.getARAging(businessId, params?)`
  - `apiClient.getAPAging(businessId, params?)`

## 14. Tests

**File:** `backend/tests/test_aging.py`

### AR Aging Tests (Class `TestARAgingFeature`)

| # | Test Name | Coverage |
|---|---|---|
| 1 | `test_unpaid_ar_aging` | Unpaid invoice in CURRENT bucket |
| 2 | `test_fully_paid_ar_aging_excluded` | Fully paid excluded |
| 3 | `test_partially_paid_ar_aging` | Partial payment reduces outstanding |
| 4 | `test_voided_payment_excluded_from_ar_aging` | Voided payment not counted |
| 5 | `test_sales_return_reduces_ar_aging` | Return adjustment reduces outstanding |
| 6 | `test_future_events_excluded_from_historical_ar_report` | As-of-date reconstruction |
| 7 | `test_draft_and_cancelled_sales_excluded_from_ar_aging` | DRAFT/CANCELLED excluded |
| 8 | `test_walkin_and_customer_aggregation` | Walk-in grouping |
| 9 | `test_ar_aging_bucket_boundaries` | All 10 boundary values (parametrized) |
| 10 | `test_ar_aging_filters_rbac_and_cross_business` | Customer filter, IDOR, RBAC |

### AP Aging Tests (Class `TestAPAgingFeature`)

| # | Test Name | Coverage |
|---|---|---|
| 1 | `test_unpaid_ap_aging` | Unpaid purchase |
| 2 | `test_fully_paid_ap_aging_excluded` | Fully paid excluded |
| 3 | `test_partially_paid_ap_aging` | Partial payment |
| 4 | `test_voided_payment_excluded_from_ap_aging` | Voided payment excluded |
| 5 | `test_purchase_return_reduces_ap_aging` | Return adjustment |
| 6 | `test_ap_aging_bucket_boundaries` | All 10 boundary values (parametrized) |
| 7 | `test_aging_summary_and_aggregation_invariants` | Summary invariants |

**Total:** 17 test methods (35 test executions via parameterization)

## 15. Limitations

- No explicit `due_date` or payment terms. Aging is anchored to document dates (`sales_date` / `purchase_date`).
- No persistent aging tables. All calculations are derived on-demand.
- No export-to-CSV/PDF.
- No notification/alert for overdue items.
- PostgreSQL runtime not verified (in-memory execution).

## 16. Source References

| Component | File | Lines |
|---|---|---|
| AgingBucket enum | `backend/app/modules/aging/utils.py` | 6–12 |
| compute_aging_days | `backend/app/modules/aging/utils.py` | 15–19 |
| compute_aging_bucket | `backend/app/modules/aging/utils.py` | 22–35 |
| AgingService (AR) | `backend/app/modules/aging/service.py` | 59–276 |
| AgingService (AP) | `backend/app/modules/aging/service.py` | 278–496 |
| AR Aging schemas | `backend/app/modules/aging/schemas.py` | 9–63 |
| AP Aging schemas | `backend/app/modules/aging/schemas.py` | 65–121 |
| AR Aging endpoint | `backend/app/modules/sales_receivable/router.py` | 79–96 |
| AP Aging endpoint | `backend/app/modules/purchase_payable/router.py` | 92–109 |
| Tests | `backend/tests/test_aging.py` | 1–881 |
| Frontend AR Aging | `frontend/src/pages/ARAging.tsx` | 1–249 |
| Frontend AP Aging | `frontend/src/pages/APAging.tsx` | 1–249 |
| Frontend types | `frontend/src/types/aging.ts` | 1–107 |
| API methods | `frontend/src/services/apiClient.ts` | 1756–1790 |
| Frontend routes | `frontend/src/app/routes.tsx` | 119–120, 562–577 |
