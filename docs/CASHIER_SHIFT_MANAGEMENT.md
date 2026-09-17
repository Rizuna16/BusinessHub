# Feature #51 — Cashier Shift Management

## Overview

Cashier Shift Management enables cash drawer accountability by tracking which cashier operates which cash drawer during a shift, reconciling physical cash counts, and attributing CashMovements to specific shifts.

## Domain Model

### CashierShift

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| business_id | UUID | Business tenant |
| branch_id | UUID | Branch location |
| cashier_user_id | UUID | Cashier operating the shift |
| cash_account_id | UUID | Cash account for the drawer |
| opening_balance | Decimal | Cash at shift start |
| actual_cash_count | Decimal (nullable) | Physical count at close |
| discrepancy | Decimal (nullable) | actual_cash_count - expected_cash |
| status | Enum: OPEN, CLOSED | Shift state |
| opened_at | DateTime (UTC) | When shift opened |
| closed_at | DateTime (UTC) | When shift closed |
| closed_by_user_id | UUID (nullable) | Who closed |
| notes | String (nullable) | Operational notes |

### Shift Lifecycle

```
NO ACTIVE SHIFT → OPEN → CLOSED
```

No reopen. CLOSED is immutable.

### Active Shift Invariant

```
UNIQUE(business_id, cash_account_id) WHERE status = OPEN
```

One OPEN shift per cash account per business. Enforced at service layer.

## API Endpoints

### Open Shift
```
POST /api/v1/businesses/{business_id}/shifts
Body: { branch_id, cash_account_id, opening_balance, notes }
```

### List Shifts
```
GET /api/v1/businesses/{business_id}/shifts?status=OPEN&page=1&page_size=20
```

### Get Shift Detail
```
GET /api/v1/businesses/{business_id}/shifts/{shift_id}
```

### Get Shift Transactions
```
GET /api/v1/businesses/{business_id}/shifts/{shift_id}/transactions
```

### Close Shift
```
PATCH /api/v1/businesses/{business_id}/shifts/{shift_id}/close
Body: { actual_cash_count, notes }
```

### Force Close Shift
```
PATCH /api/v1/businesses/{business_id}/shifts/{shift_id}/force-close
Body: { notes } (required)
```

## Cash Movement Attribution

CashMovements gain an optional `shift_id` field. This is metadata only; existing movements without `shift_id` remain valid (UNATTRIBUTED).

### Attribution Rules

| Operation | shift_id Source |
|-----------|----------------|
| Payment (CASH + shift_id provided) | Validated shift_id |
| Payment (CASH + no shift_id) | None (backward compatible) |
| Payment (non-CASH) | None |
| Expense (CASH account) | Open shift if exists |
| Transfer OUT | Open shift on source account |
| Transfer IN | Open shift on destination account |
| Payment Void | Original shift if OPEN, else None |

## Expected Cash Formula

```
Expected Cash =
    shift.opening_balance
    + SUM(amount WHERE shift_id = shift.id AND direction = IN AND status = POSTED)
    - SUM(amount WHERE shift_id = shift.id AND direction = OUT AND status = POSTED)
```

## Reconciliation

At close:
- Cashier enters `actual_cash_count`
- `discrepancy = actual_cash_count - expected_cash`
- Discrepancy types: BALANCED (0), OVERAGE (>0), SHORTAGE (<0)
- No accounting adjustment is created

## Security

- OWNER/ADMIN: view all shifts, force close any shift
- MEMBER: view/close own shifts only
- Business isolation enforced on all endpoints

## Backward Compatibility

- `shift_id` is optional on CashMovement
- Existing payments without shift_id continue to work
- No historical backfill
- No database migration required

## Limitations

- In-memory repository (single-process deployment only)
- No Z-report or thermal printer
- No shift scheduling or attendance
- No accounting adjustment for discrepancies
- Post-close payment reversals create unattributed movements
