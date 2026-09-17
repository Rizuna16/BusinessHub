# FEATURE #55 — Manual Bank Transfer Subscription / Recurring Billing + Configurable Pricing

## Overview

Feature #55 introduces configurable subscription pricing, billing periods, payment attempts, Manual Bank Transfer payment flow, Super Admin verification workflow, and reconciliation to BusinessHub's platform subscription system.

## Architecture

```
SubscriptionPlan → Subscription → BillingPeriod → PaymentAttempt → Manual Bank Transfer
```

### SubscriptionPlan

- Configurable plan entity with `id`, `code` (immutable), `name`, `price` (Decimal), `currency`, `billing_interval`, `is_active`.
- Price is mutable but only affects future billing periods.
- Currency and billing interval are immutable after plan creation/use.
- Plans are never deleted; soft lifecycle via `is_active = False`.

### Subscription

- Represents a business's subscription contract.
- `price` reflects the **current paid period** price, not the plan price.
- `current_period_start`/`current_period_end` are projections of the last successfully paid `BillingPeriod`.

### BillingPeriod

- Immutable historical financial record per billing cycle.
- Snapshots: `price_snapshot`, `currency_snapshot`, `billing_interval_snapshot`, `plan_name_snapshot`.
- Payment statuses: `PENDING`, `PROCESSING`, `PAID`, `FAILED`, `EXPIRED`, `CANCELLED`.
- **PAID is terminal** — never reverts.

### PaymentAttempt

- Tracks individual payment attempts per billing period.
- Statuses: `CREATED`, `PENDING`, `SUCCESS`, `FAILED`, `EXPIRED`, `CANCELLED`.
- Only one `SUCCESS` attempt per `BillingPeriod`.
- Retries create new attempts using the same immutable `BillingPeriod.price_snapshot`.
- Manual bank transfer fields: `payment_reference`, `verification_note`, `verified_by`, `verified_at`.

## Price Snapshot Chain

```
SubscriptionPlan.price
    ↓
BillingPeriod.price_snapshot (immutable)
    ↓
PaymentAttempt.amount
    ↓
Super Admin Amount & Currency Verification Match
```

**Key rule:** Changing `SubscriptionPlan.price` NEVER mutates existing `BillingPeriod.price_snapshot` or `PaymentAttempt.amount`.

## Initial Payment & Manual Bank Transfer Flow

1. Business creation creates `Subscription`, `BillingPeriod #1` (PENDING), `PaymentAttempt #1` (CREATED).
2. Explicit checkout action initiates manual bank transfer, transitioning `PaymentAttempt` to `PENDING` and `BillingPeriod` to `PROCESSING`.
3. Business provides payment transfer reference.
4. Super Admin verifies payment via endpoint (`POST /api/v1/platform/subscriptions/{sub_id}/billing-periods/{bp_id}/payment-attempts/{pa_id}/verify`) with strict amount and currency verification (`PaymentAttempt.amount == BillingPeriod.price_snapshot` and currency match).
5. Successful verification records `verified_by`, `verified_at`, `verification_note`, transitions payment attempt to `SUCCESS`, billing period to `PAID`, and advances subscription period. Audit log is recorded.

## Renewal Flow

Explicit Super Admin trigger: `POST /api/v1/platform/subscriptions/{id}/renew`

1. Validates subscription lifecycle and plan activity.
2. Fetches latest **ACTIVE** plan price.
3. Creates new `BillingPeriod` with price snapshot.
4. Creates `PaymentAttempt` with snapshot amount.
5. If plan is inactive → renewal blocked, `RENEWAL_BLOCKED` audit logged.

## Retry Flow

1. Retries use existing `BillingPeriod.price_snapshot`.
2. Never recalculate from current plan price.
3. Creates new `PaymentAttempt` with new idempotency key and provider order ID.

## Super Admin Verification Endpoint

- **Endpoint:** `POST /api/v1/platform/subscriptions/{sub_id}/billing-periods/{bp_id}/payment-attempts/{pa_id}/verify`
- **RBAC:** Requires `SUPER_ADMIN` platform authority.
- **Invariants:** Strict check that `PaymentAttempt.amount == BillingPeriod.price_snapshot` and currency matches. Mismatches automatically fail the payment attempt.

## Subscription Status Safety

- `SUSPENDED`: Payment success does NOT silently unsuspend.
- `CANCELLED`: Payment success does NOT silently reactivate.
- `EXPIRED`: Payment success does NOT automatically revive.
- `ACTIVE`/`PAST_DUE`: Payment success transitions to `ACTIVE` with current period advance.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/platform/plans` | List plans |
| GET | `/api/v1/platform/plans/{id}` | Get plan |
| POST | `/api/v1/platform/plans` | Create plan |
| PUT | `/api/v1/platform/plans/{id}` | Update plan |
| POST | `/api/v1/platform/plans/{id}/activate` | Activate plan |
| POST | `/api/v1/platform/plans/{id}/deactivate` | Deactivate plan |
| GET | `/api/v1/platform/subscriptions` | List subscriptions |
| GET | `/api/v1/platform/subscriptions/{id}` | Get subscription |
| POST | `/api/v1/platform/subscriptions/{id}/override` | Override subscription (with audit) |
| GET | `/api/v1/platform/subscriptions/{id}/billing-periods` | List billing periods |
| POST | `/api/v1/platform/subscriptions/{id}/checkout` | Initiate manual checkout |
| POST | `/api/v1/platform/subscriptions/{id}/renew` | Renew subscription |
| POST | `/api/v1/platform/subscriptions/{id}/retry` | Retry failed payment |
| POST | `/api/v1/platform/subscriptions/{sub_id}/billing-periods/{bp_id}/payment-attempts/{pa_id}/verify` | Super Admin verify payment |
