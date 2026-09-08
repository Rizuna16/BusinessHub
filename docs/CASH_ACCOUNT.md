# Feature #28 — Cash & Cash Account

## Overview
Feature #28 provides operational cash account management for BusinessHub businesses. It enables businesses to create and manage multiple operational money holding accounts like Cash, Bank, E-Wallet, etc.

## Architecture
The module strictly adheres to an operational scope, avoiding Accounting Ledger (General Ledger) and future Payable/Expense behavior.

### Domain Models
- **`CashAccount`**: Represents an individual operational cash account (`CASH`, `BANK`, `E_WALLET`, `OTHER`) with an immutable account code, currency, and starting balance.
- **`CashMovement`**: Represents any inbound or outbound operational money flow (`CASH_IN`, `CASH_OUT`, `TRANSFER_IN`, `TRANSFER_OUT`).

### Balance Calculation
The current operational balance is derived purely from the `opening_balance` plus all `POSTED` `IN` movements, minus all `POSTED` `OUT` movements.
```python
current_balance = opening_balance + SUM(IN) - SUM(OUT)
```

## Transfers
Transfers between two active Cash Accounts of the **same currency** are supported and perform atomic logical transactions (deducting from source, crediting to destination simultaneously).

## Payment Boundary
This feature provides cash infrastructure. It **does not** automatically synchronize with `SalesPayment` to avoid future accounting complexity (#33). `SalesPayment` remains the source of truth for payments, and `SalesReceivable` remains the source of truth for balances. Integrating these will be handled in Payment Engine (#32) and Accounting Foundation (#33).

## API Endpoints
- `GET /api/v1/businesses/{business_id}/cash-accounts`
- `POST /api/v1/businesses/{business_id}/cash-accounts`
- `GET /api/v1/businesses/{business_id}/cash-accounts/summary`
- `GET /api/v1/businesses/{business_id}/cash-accounts/{account_id}`
- `PATCH /api/v1/businesses/{business_id}/cash-accounts/{account_id}`
- `POST /api/v1/businesses/{business_id}/cash-accounts/{account_id}/activate`
- `POST /api/v1/businesses/{business_id}/cash-accounts/{account_id}/deactivate`
- `POST /api/v1/businesses/{business_id}/cash-accounts/{account_id}/movements`
- `GET /api/v1/businesses/{business_id}/cash-accounts/{account_id}/movements`
- `POST /api/v1/businesses/{business_id}/cash-accounts/transfers`

## Security & RBAC
- All endpoints require active business membership (`OWNER`, `ADMIN`, `MEMBER`).
- **Mutations** are restricted to `OWNER` and `ADMIN`.
- **Anti-enumeration**: Cross-tenant access attempts yield `404 Not Found`.

## Postgres Readiness
Future indexes should include:
- `cash_account`: `(business_id, status)`
- `cash_movement`: `(business_id, cash_account_id, created_at)`
- Row-level locks on `cash_account` during balance checks to prevent overdraft in concurrent scenarios.
