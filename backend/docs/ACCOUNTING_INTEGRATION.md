# BusinessHub Accounting Integration (Feature #34)

## Overview
The Accounting Integration module connects operational transactions in BusinessHub (Sales, Purchases, Payments, Expenses, and Returns) to the Accounting Foundation (#33) via the canonical Posting Engine.

## Source-of-Truth Matrix
| Domain | Operational Source of Truth | Accounting Projection / GL |
|---|---|---|
| Sales | `Sales` | `JournalEntry` (Debit AR / Credit Revenue) |
| Customer Payment | `Payment` | `JournalEntry` (Debit Cash / Credit AR) |
| Supplier Payment | `Payment` | `JournalEntry` (Debit AP / Credit Cash) |
| Cash Movement | `CashMovement` | `JournalEntry` (Mapped via Payment/Expense) |
| Purchase | `Purchase` | `JournalEntry` (Debit Inventory / Credit AP) |
| Expense | `Expense` | `JournalEntry` (Debit Expense / Credit Cash) |
| Sales Return | `SalesReturn` | `JournalEntry` (Debit Revenue / Credit AR) |
| Purchase Return | `PurchaseReturn` | `JournalEntry` (Debit AP / Credit Inventory) |

## COA Mapping
- `1100`: Cash & Bank (Asset, Debit)
- `1200`: Accounts Receivable (Asset, Debit)
- `1300`: Inventory Assets (Asset, Debit)
- `2100`: Accounts Payable (Liability, Credit)
- `4100`: Sales Revenue (Revenue, Credit)
- `5100`: General & Operational Expense (Expense, Debit)

## Transaction Boundary & Atomicity Architecture
1. **Accounting-First Pattern**: Accounting posting is initiated FIRST inside an `accounting_integration_service.safe_post` execution block. If accounting fails, no operational status mutation or inventory/cash movement occurs.
2. **Application-Level Compensation**: If any subsequent step fails after accounting posting, compensating rollback handlers revert operational entity status and delete created cash movements or payments.
3. **PostgreSQL Production Transaction**: For PostgreSQL, all operations (operational entity mutation + cash movement + journal entry) must execute inside a single ACID `BEGIN...COMMIT` database transaction boundary to guarantee atomicity at the storage level.

## Idempotency & Concurrency Strategy
1. **Deterministic Keys**: Idempotency keys are formatted as `{source_type}:{source_id}:{event}` (e.g. `SALES:uuid:FINALIZED`, `PAYMENT:uuid:VOIDED`).
2. **In-Memory Concurrency Lock**: `AccountingIntegrationService.safe_post` uses an `asyncio.Lock` per idempotency key to serialize concurrent identical requests in application memory. The first request acquires the lock and posts; concurrent duplicate requests wait and receive the idempotent existing journal entry.
3. **PostgreSQL Constraint**: Production PostgreSQL database schema requires `UNIQUE(business_id, idempotency_key)` on the `journal_entries` table to enforce database-level duplicate prevention under multi-process concurrent loads.

## PostgreSQL Runtime Verification Status
`FEATURE #34 — PASS — POSTGRESQL RUNTIME VERIFICATION PENDING`

- **Application-Level Atomicity**: RUNTIME VERIFIED (19/19 dedicated integration tests passed)
- **Application-Level Idempotency**: RUNTIME VERIFIED (Sequential + Concurrent tests passed)
- **Full Regression**: RUNTIME VERIFIED (698/698 tests passed)
- **PostgreSQL Database Transactions**: NOT RUNTIME VERIFIED (No active PostgreSQL environment in test runner)
- **PostgreSQL Database UNIQUE Constraints**: NOT RUNTIME VERIFIED (No active PostgreSQL environment in test runner)
