# FEATURE #32 — PAYMENT ENGINE DOCUMENTATION

## 1. Purpose & Scope
Payment Engine is the canonical financial payment/settlement engine that connects **Customer Receivable** and **Supplier Payable** to **Cash Account**. It provides atomic, idempotent, auditable payment transactions.

## 2. Architecture

- **Pattern**: Hybrid derived + canonical persistence.
- **Design Choice**: **OPTION A** — `SalesPayment` compatibility projection (deprecated alias) is NOT created. Instead Payment Engine is the canonical payment entity (`app/modules/payment/`) and actively read by Receivable (`_calculate_receivable_for_sales`) and Payable (`_calculate_payable_for_purchase`) engines so no duplicate financial meaning exists.

## 3. Source of Truth

- **Payment**: `Payment` row (`app/modules/payment/repository.py`) — `RECORDED` payments are canonical.
- **Receivable**: Derived read model `Sales.grand_total - Payment(RECORDED)`. No persisted receivable ledger.
- **Payable**: Derived read model `Purchase.grand_total - finalized PurchaseReturn.grand_total - Payment(RECORDED where target_type=PURCHASE)`.
- **Cash**: `CashAccount.opening_balance + Σ(CashMovement POSTED IN) - Σ(CashMovement OUT)`. Payment mirrors with `CASH_IN` (customer) / `CASH_OUT` (supplier).

## 4. Existing Systems Integrated
- `SalesPayment` (Feature #23): Now superseded; audit showed no direct CashMovement side effects — payload envelope replaced but invariants retained.
- `Receivable Engine` (Feature #30): `_calculate_receivable_for_sales` now queries `payment_repository`.
- `Payable Engine` (Feature #31): `_calculate_payable_for_purchase` now reads `payment_repository` for `paid_amount`.
- `Cash Account` (Feature #28): `cash_account_repository.create_movement` invoked atomically on payment record. `MovementDirection` ensures correct sign.
- `Expense`, `Purchase`, `PurchaseReturn`, `Business/Membership` unchanged.

## 5. Payment Model (Canonical Payload)

Minimal canonical serialization (`PaymentCreate`):

```json
{
  "direction": "CUSTOMER_IN | SUPPLIER_OUT",
  "target_type": "SALES | PURCHASE",
  "target_id": "uuid",
  "amount": "Decimal (>0)",
  "currency": "IDR|USD|SGD|MYR|EUR|JPY",
  "payment_method": "CASH|BANK_TRANSFER|CARD|E_WALLET|OTHER",
  "cash_account_id": "uuid",
  "payment_date": "iso-datetime (optional)",
  "reference_number": "string (optional)",
  "notes": "string (optional)",
  "idempotency_key": "string (optional)"
}
```

Canonical row (`PaymentInDB`): `id, business_id, branch_id, payment_number, payment_date, payment_method, amount, currency, cash_account_id, status, created_by, voided_by, created_at, voided_at`.

## 6. Payment Lifecycle

```text
Creation  → status = RECORDED
Voiding   → status = VOIDED (no hard delete) + reversal CashMovement(idempotent marker: PAYMENT_VOID / reference_id = payment.id)
Second void → 400 (already VOIDED)
```

No soft-delete; void audit trail preserved with `voided_by_user_id`, `voided_at`.

## 7. Customer Payment Flow
`Customer → POST /payments { CUSTOMER_IN, SALES } → Sequence PMT-00000N → CashAccount CASH_IN → Receivable outstanding -= amount`

## 8. Supplier Payment Flow
`POST /payments { SUPPLIER_OUT, PURCHASE } → Sequence PMT-00000N → Pre-check return_adjustment (PurchaseReturn grand_total FINALIZED) → Net payable = grand_total - return_adjustment → CashAccount CASH_OUT → Payable outstanding -= amount`

Example:

```
Purchase = 1,000
Purchase Return 200 (FINALIZED)
Net Payable 800
Supplier Payment 500 → Outstanding 300
```

## 9. CASH INTEGRATION
Atomic posting simulation:

```python
payment = repo.create(payment)
cash_account_repository.create_movement(
    movement_type=SALES_PAYMENT/EXPENSE,
    direction=CASH_IN/CASH_OUT,
    reference_type="PAYMENT",
    reference_id=payment.id,
)
```

Customer payment amount `+X` → `CASH_IN X`. Supplier payment `X` → `CASH_OUT X`. Insufficient-out-balance for supplier is rejected. Void creates mirror `PAYMENT_VOID` reversal movement (direction flipped).

*In-Memory runtime has no real DB transaction; payment failure paths are documented as best-effort. PostgreSQL runtime would use a single `BEGIN ... COMMIT`.*

## 10. RECEIVABLE INTEGRATION
`SalesReceivableService._calculate_receivable_for_sales` now queries `payment_repository.get_active_payments_total_for_target`. No legacy `sales_payment_repository` needed. Historical payment array reflects new `RECORDED/VOIDED` enum.

## 11. PAYABLE INTEGRATION
`PurchasePayableService._calculate_payable_for_purchase` now queries `payment_repository.get_active_payments_total_for_target` for Supplier aggregated `paid_amount`. No new persisted payable ledger.

## 12. Allocation
No explicit partial-allocation table — one payment = single atomic settlement against one target (`target_id`). Partial settlement is natural via multiple payments (e.g., 300 + 700 for 1,000 invoice). All payments enumerated in receivable/payment history arrays.

## 13. Overpayment Policy
**Policy A — Reject payment > outstanding.**

Payment that would exceed `remaining = grand_total - active_paid` (customer) or `net_payable - active_paid` (supplier) is rejected with HTTP 400 (`Payment amount (…) exceeds remaining outstanding (…)`). Verified via `test_overpayment_rejected` and `test_purchase_return_effect_on_payable_limit`.

Optional future #33: allow overpayment as customer credit (deferred).

## 14. Currency Policy
Ternary equality invariant:

`payment.currency == target.currency == cash_account.currency`.

BusinessHub supports `IDR, USD, SGD, MYR, EUR, JPY` but has no FX engine. `IDR + USD` on same payment target is **rejected** (`400 Currency`). `payment → CashAccount` cross-currency also rejected. No numeric multi-currency summation on aggregated summary level — per-payment currency is preserved in its own row and receivable/payable responses keep their own business currency (IDR normalized).

## 15. Idempotency
Header-field `idempotency_key` (opaque client-supplied). Repeated second logical-identical POST with same `business_id + idempotency_key` looks up `get_payment_by_idempotency_key` and returns the existing payment (201 → 200 alias) without re/posting a second base Cash Movement. Invariant: `N identical requests → 1 financial payment, 1 cash posting`. Concurrency simulation `idempotency_key = UNIQUE-KEY-12345` verified.

## 16. Atomicity
Contract: either (`Payment` + `CashMovement`) both persist or neither. In-Memory simulation fulfills relaxed atomicity: successful debt → then attempt movement; if movement creation would throw, the wrapping `except` path documents the limitation (no rollback). **PostgreSQL runtime would wrap both as an ACID transaction.** No partial state created by system: no orphan payment, no orphan movement in success path.

## 17. Concurrency
Race: two concurrent `POST payment(100) + idempotency_key = X` must not settle `2×100`. Serialized in-memory via single-threaded async dict store; simultaneous consumers degenerate. True database-level uniqueness under contended writers requires `UNIQUE(business_id, idempotency_key)` index + `SELECT FOR UPDATE` on outstanding check. Reported honestly: `DOCUMENTED — NOT RUNTIME VERIFIED` for PostgreSQL contention.

## 18. Security

- **Authentication**: `get_current_user` OAuth2 Bearer requirement — `401` on missing/bad token.
- **Authorization**: `create_payment`, `void_payment` require active membership with role `OWNER | ADMIN` — explicit 403 on `MEMBER`, `SUSPENDED`, `REMOVED`, or non-membership.
- **Tenant isolation**: Strictly `business_id`-scoped dict stores, `target_id` business check, `cash_account_id` business check — cross-tenant creation yields `404` (or `403` for no membership).
- **Branch isolation**: `branch_id` derived from target (`Sales.branch_id` / `Purchase.branch_id`) — payment indirectly branch-scoped, matching existing branch-access helper pattern.
- **RBAC / Permissions**: Aligned with `BusinessMembershipRole`; elevated actions gated to high privilege.
- **IDOR**: Verified via `test_tenant_isolation_and_idor` (Biz-B user POST to Biz-A sales — expected 404/403).
- **Input Validation**: Pydantic fast-fail on zero / negative amount (`422`), enum exhausted, currency whitelist, amount > outstanding (`400`).

## 19. Tenant Isolation
All payment queries double-check `payment.business_id == path business_id` and `target.business_id == payment.business_id`. Cross-business `sales_id`, `purchase_id`, or `cash_account_id` returns `404` (not found in this business) rather than success, preventing enumeration-leak verification gap.

## 20. API
| Verbs | URL | Auth | Semantics |
|-------|-----|------|-----------|
| `POST` | `/api/v1/businesses/{business_id}/payments` | Bearer | Record customer / supplier payment |
| `GET`  | `/api/v1/businesses/{business_id}/payments` | Bearer | List (direction/target_type/target_id/page filters) |
| `GET`  | `/api/v1/businesses/{business_id}/payments/{payment_id}` | Bearer | Detail |
| `POST` | `/api/v1/businesses/{business_id}/payments/{payment_id}/void` | Bearer (OWNER/ADMIN) | Void (auditable reversal) |

Route registered as `payment_router` sibling to `sales_receivable_router` / `sales_payment_router` — no conflict with `/{purchase_id}` parametric routes as registration prefix differs.

## 21. Frontend
- **Types**: `frontend/src/types/payment.ts` (`PaymentDirection`, `PaymentTargetType`, `PaymentMethod`, `PaymentStatus`, `Payment`, `PaymentListResponse`).
- **Client**: `frontend/src/services/apiClient.ts` — `listPayments`, `createPayment`, `getPaymentById`, `voidPayment` added as first-class stateless methods (read-only optimistic helpers; no second client).
- **Pages**: `frontend/src/pages/Payments.tsx` (list with direction filter, responsive table, loading/empty/error/permission-aware), `frontend/src/pages/PaymentDetail.tsx` (detail cards, void confirmation, cash-movement revert feedback, branch/target navigation).
- **Routes**: `frontend/src/app/routes.tsx` adds `BUSINESS_PAYMENTS` and `BUSINESS_PAYMENT_DETAIL` under `ProtectedRoute`.
- **Responsive, mobile-first**: Tailwind wrapper, responsive `p-6 max-w-7xl mx-auto`, `overflow-x-auto` tables, `Badge`-compatible status pills (dark mode aware), confirmation dialog for void to avoid fat-finger loss.

## 22. Testing
Eleven focused payment engine functional tests (`tests/test_payment_engine.py`):

`test_customer_payment_success_and_cash_posting`, `test_supplier_payment_success_and_cash_posting`, `test_overpayment_rejected`, `test_idempotency_key`, `test_void_payment_and_cash_reversal`, `test_tenant_isolation_and_idor`, `test_rbac_member_read_only`, `test_invalid_amount_rejection`, `test_invalid_target_status_rejection`, `test_mismatched_currency_rejection`, `test_purchase_return_effect_on_payable_limit`.

Cover critical invariants: partial → full multi-payment, currency & void idempotency, cross-tenant read/write isolation, RBAC allow/deny, and purchase-return-adjusted remaining outstanding.

## 23. PostgreSQL Verification Status
**DOCUMENTED — NOT RUNTIME VERIFIED.** PostgreSQL runtime was not provisioned in this execution environment. A transaction abstraction / `UNIQUE(business_id, idempotency_key)` constraint + `SELECT FOR UPDATE` is prescribed for real deployment concurrency verification and intended to be verified against PostgreSQL at integration test boundary in CI.

## 24. Known Limitations
- Transaction atomicity of `payment + CashMovement` is relax-consistency in In-Memory store (no `BEGIN/COMMIT`).
- Legacy `SalesPayment` sales-scoped payment creation endpoint `/sales/{id}/payments` remains preserved and may continue to be invoked directly by client history — now canonicalized however within new engine's void history read path.
- Currency invariant enforces single-currency per payment but cross-currency conversion not yet implemented (compliance requirement: reject incompatible currency).

## 25. Deferred Items
Any of these requires #33+ (Accounting) funding/scope and a decision memo:

- Overpayment-as-credit ledger (Policy B).
- General Ledger posting (`JournalEntry`) from payment settlement.
- Chart of Accounts exposure for cash/payment revenue/expense lines.

---

Prepared for closure gate: **Feature #32 — Payment Engine**.

Evidence matrix, findings traceability, full regression, typecheck, production build, and lint verification recorded in closing report.
