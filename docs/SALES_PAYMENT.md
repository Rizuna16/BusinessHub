# Feature #23 — Sales Payment Foundation

## 1. Domain Responsibility
Sales Payment Foundation provides internal payment recording against FINALIZED sales transactions within the BusinessHub modular monolith.

Key responsibilities:
- Recording internal payments against finalized sales orders.
- Calculating dynamic payment aggregations (`total_paid`, `remaining_amount`).
- Enforcing payment immutability and overpayment protection.
- Exposing payment summaries for future downstream consumers (#26 Customer Receivable).

Explicit non-responsibilities:
- Payment Engine & Gateway integrations (#32).
- Customer Receivable & AR Ledger (#26).
- Accounting Journals & Accounts (#33).
- Cash Account balance tracking (#28).
- Inventory deduction/mutation (#24).

---

## 2. SalesPayment Entity

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | UUID string | Yes | Primary key |
| `business_id` | UUID string | Yes | Multi-tenant isolation scope |
| `sales_id` | UUID string | Yes | Target finalized Sales order |
| `payment_number` | String | Yes | Server-generated business sequence (`PAY-000001`) |
| `payment_date` | DateTime | Yes | Payment recording date |
| `payment_method` | Enum | Yes | `CASH`, `BANK_TRANSFER`, `DEBIT_CARD`, `CREDIT_CARD`, `QRIS`, `E_WALLET`, `OTHER` |
| `amount` | Decimal | Yes | Payment amount (Decimal > 0) |
| `reference_number` | String | Optional | Generic reference code (e.g. bank slip reference) |
| `notes` | String | Optional | Internal payment notes |
| `status` | Enum | Yes | `RECORDED` or `CANCELLED` |
| `created_by_user_id` | UUID string | Yes | User who created the payment record |
| `cancelled_by_user_id`| UUID string | Optional | User who cancelled the payment |
| `created_at` | DateTime | Yes | Creation timestamp |
| `updated_at` | DateTime | Yes | Last update timestamp |
| `cancelled_at` | DateTime | Optional | Cancellation timestamp |

---

## 3. Core Business & Domain Rules

### 3.1 Eligibility Rules
- Payments can **ONLY** be recorded against sales with status `FINALIZED`.
- Payments against `DRAFT` or `CANCELLED` sales are rejected with HTTP 400.

### 3.2 Overpayment Protection
- `active_total_paid = sum(amount for payments if status == RECORDED)`
- `remaining = sales.grand_total - active_total_paid`
- New payment requires `new_amount <= remaining`. Overpayment attempts are rejected with HTTP 400.

### 3.3 Immutability & Cancellation
- Recorded payments **CANNOT** be updated or hard-deleted.
- The only allowed state change is `RECORDED -> CANCELLED`.
- `CANCELLED` is terminal. Re-cancelling returns HTTP 400.
- Cancelled payments are excluded from `total_paid` calculations.

### 3.4 Multi-tenant & Role-Based Access Control (RBAC)
- Cross-business sales or payment access is strictly forbidden (HTTP 404).
- Permissions:
  - `sales.payment.read`: `OWNER`, `ADMIN`, `MEMBER`
  - `sales.payment.create`: `OWNER`, `ADMIN`
  - `sales.payment.cancel`: `OWNER`, `ADMIN`
- `MEMBER` role is strictly read-only.

---

## 4. API Specification

| Method | Endpoint | Authorization | Description |
|---|---|---|---|
| `POST` | `/api/v1/businesses/{business_id}/sales/{sales_id}/payments` | OWNER, ADMIN | Record a new payment against finalized sales |
| `GET` | `/api/v1/businesses/{business_id}/sales/{sales_id}/payments` | OWNER, ADMIN, MEMBER | List payments and payment summary for sales |
| `GET` | `/api/v1/businesses/{business_id}/sales/{sales_id}/payments/{payment_id}` | OWNER, ADMIN, MEMBER | Get specific payment detail |
| `POST` | `/api/v1/businesses/{business_id}/sales/{sales_id}/payments/{payment_id}/cancel` | OWNER, ADMIN | Cancel a recorded payment |

---

## 5. Architectural Boundaries

- **Inventory Boundary**: 0 inventory changes occur during payment creation or cancellation.
- **Receivable Boundary**: Payment foundation exposes `total_paid` and `remaining_amount` for #26 Customer Receivable without introducing AR ledgers.
- **Payment Engine & Gateway Boundary**: Gateway references, webhooks, and multi-provider state machine belong to Payment Engine #32.
- **Accounting Boundary**: No GL postings or tax postings.

---

## 6. Concurrency & Future Hardening

### 6.1 Current Architecture Note
The current implementation uses an abstracted in-memory repository matching Features #1–#22. Concurrency checks on active remaining balance are executed sequentially per process.

### 6.2 PostgreSQL Hardening Strategy (Deferred)
When migrating to PostgreSQL, remaining balance checks during concurrent payment requests must be guarded via explicit row locking:

```sql
BEGIN;
SELECT grand_total FROM sales WHERE id = :sales_id FOR UPDATE;
SELECT COALESCE(SUM(amount), 0) FROM sales_payment WHERE sales_id = :sales_id AND status = 'RECORDED';
-- Validate amount <= (grand_total - active_total)
INSERT INTO sales_payment (...);
COMMIT;
```
