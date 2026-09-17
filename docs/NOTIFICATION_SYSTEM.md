# # FEATURE #56 — Notification & Alerting System

## Purpose

Feature #56 introduces a notification infrastructure for BusinessHub. It provides a centralized, service-driven notification layer for tenant and platform communication, supporting configurable types, severity levels, scopes, and deduplication without external providers, schedulers, or persistence layers.

## Architecture

**Domain:** Backend `backend/app/modules/notification/` with `schemas.py`, `repository.py`, `service.py`, `router.py`. Frontend `frontend/src/components/Notification*.tsx` and `frontend/src/services/notificationApiClient.ts`.

**Backend Pattern:** Repository → Service → Router (in-memory).

**Frontend Pattern:** NotificationBell, NotificationDropdown, NotificationList components with dedicated API client.

**Scopes:**
- TENANT: `business_id` required, `recipient_id` required
- PLATFORM: `business_id` must be `null`, `recipient_id` required

**Types:**
- SUBSCRIPTION_RENEWAL_REMINDER
- PAYMENT_VERIFICATION_REQUIRED
- PAYMENT_VERIFIED
- STOCK_LOW

**Severity:**
- INFO
- WARNING
- CRITICAL

**State Machine:**
- UNREAD → READ (is_read: false → true, read_at: null → timestamp)
- Idempotent mark-read handled by repository without transition to ARCHIVED/DISMISSED/EXPIRED/DELETED.

## Repository

- In-memory `Dict[str, Notification]` with dedup index.
- Methods: `create`, `get_by_id`, `list_for_recipient`, `count_unread`, `mark_read`, `mark_all_read`, `find_by_deduplication_key`.
- Query filtering explicitly enforces `recipient_id`, `scope`, and `business_id`.

## Service

- Operations: `create_notification`, `create_if_not_exists` (dedup), `list_notifications`, `get_unread_count`, `mark_as_read`, `mark_all_as_read`.
- Helper methods: `notify_super_admins`, `notify_business_members` for bulk fan-out.
- No event bus — synchronous, best-effort service calls (notification failure never rolls back primary business operation).

**Deduplication keys:**
- `renewal:{subscription_id}:{billing_period_id}`
- `payment-required:{payment_attempt_id}`
- `payment-verified:{payment_attempt_id}`
- `stock-low:{business_id}:{product_id}`

## API

- `GET /api/v1/notifications` — tenant list (unread_only, limit)
- `GET /api/v1/notifications/platform` — platform list
- `GET /api/v1/notifications/unread-count` — tenant unread count
- `GET /api/v1/notifications/platform/unread-count` — platform unread count
- `POST /api/v1/notifications/{id}/read` — tenant mark read
- `POST /api/v1/notifications/platform/{id}/read` — platform mark read
- `POST /api/v1/notifications/read-all` — tenant mark all read
- `POST /api/v1/notifications/platform/read-all` — platform mark all read
- No public `POST /notifications` creation.

## Security

- Tenant: `recipient_id == current_user.id` + active membership.
- Platform: active SUPER_ADMIN + `recipient_id == current_account.id`.
- SUPER_ADMIN cannot access tenant notifications across businesses.
- Inaccessible notifications return 404, never leaking existence.
- Client-supplied `recipient_id`/`business_id` never trusted for authorization.

## Triggers

| Type | When | Scope | Recipient Resolution |
|---|---|---|---|
| `PAYMENT_VERIFICATION_REQUIRED` | Checkout creates PENDING payment attempt | PLATFORM | All active SUPER_ADMIN accounts resolved from Account repository (`is_active=True`, `platform_role=SUPER_ADMIN`) |
| `PAYMENT_VERIFIED` | Super Admin verifies payment | TENANT | Active OWNER/ADMIN memberships resolved from BusinessMembership repository (`status=ACTIVE`, `role in {OWNER, ADMIN}`) |
| `SUBSCRIPTION_RENEWAL_REMINDER` | Deterministic renewal check | TENANT | Business members (deferred) |
| `STOCK_LOW` | available_stock ≤ threshold | TENANT | Business members (deferred — no authoritative threshold source) |

**Recipient resolution is synchronous and best-effort.** If no active recipients exist, zero notifications are created without failing the primary business operation.

**Stock-low note:** No authoritative product threshold exists in current inventory domain. Infrastructure is fully implemented; the trigger integration is deferred and documented. MVP uses best-effort service availability without redesigning inventory.

## In-Memory Limitations

- Process restart clears all notifications.
- No cross-instance replication.
- Idempotency and locks are process-local.
- No scheduled/cron delivery.

## No Event Bus / No Scheduler / No External Providers

- Notifications are synchronous service-level calls.
- No WebSocket, message broker, or background job infrastructure.
- No email, SMS, WhatsApp, or push notifications.

## Future / Deferred

- Stock-low trigger when threshold source is defined
- Subscription renewal reminder when scheduler is available
- Email/push delivery
- Notification preferences/UI

## Frontend

- NotificationBell in PlatformTopbar and Topbar (tenant)
- NotificationDropdown with real-time unread badge and mark-read
- NotificationList page at `/app/notifications` and `/platform/notifications`
- Safe array handling (`Array.isArray`), non-blocking error fallback ("Unable to load notifications.")
