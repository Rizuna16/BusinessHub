# BusinessHub — Business / Tenant Core Documentation

## 1. Business Purpose
Business is the central tenant data boundary in BusinessHub. It encapsulates a separate business entity owned by an authenticated user. Each Business is isolated from other users' businesses, enforcing data-level multi-tenancy.

## 2. Architecture Layer Position
```
User → Account → Business → (future: BusinessMembership) → (future: Branch)
```
Business is downstream of Account but upstream of membership/authorization. It is NOT coupled 1:1 to an Account — one Account can own multiple Businesses.

## 3. Ownership Model
- `owner_user_id` is assigned exclusively from the authenticated JWT (`sub` claim) at creation time.
- No `owner_user_id`, `created_by`, or `user_id` from request body is accepted as an authority.
- Only the owner can `GET`, `PATCH`, or `ARCHIVE` their own Business. Cross-user access returns 404 (anti-enumeration).

## 4. Business Model Fields
- `id`: UUID, primary key.
- `owner_user_id`: Auth user who owns this Business.
- `name`: Required, 2–100 chars, trimmed.
- `slug`: Auto-generated from `name`, normalized, globally unique. Stable across renames.
- `description`: Optional, max 500 chars.
- `business_type`: Enum (see §5 below).
- `status`: Enum (Active / Suspended / Archived).
- `timezone`: IANA identifier.
- `locale`: Standard locale identifier.
- `created_at`, `updated_at`: Timestamp fields.

## 5. Business Type
Supported extensible types: `hotel`, `retail`, `umkm`, `restaurant`, `service`, `production`, `garment`, `distributor`, `workshop`, `salon`.
Business type is immutable after creation.

## 6. Template Separation
Business type ≠ Template Usaha. No `template_id` or template engine is included. Template Usaha is a future feature.

## 7. Slug Strategy
- Generated server-side from Business name: lowercase, hyphen-separated, ASCII alphanumeric only.
- Globally unique: collisions resolved with incremental suffixes (e.g., `my-biz-2`).
- Slug remains stable when the Business name is updated.

## 8. Status Lifecycle
`ACTIVE` → (archive) → `ARCHIVED`
- Archived businesses are excluded from the default list.
- Archival is soft (no hard delete). Data persists.

## 9. Archive Strategy
- `DELETE /api/v1/businesses/{id}` performs a soft-archive (sets status to ARCHIVED).
- The business record is never permanently deleted.
- Archived businesses are hidden from the active list but remain accessible by ID for the owner.

## 10. API Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/businesses` | Create Business (owner = authenticated user) |
| GET | `/api/v1/businesses` | List own active businesses |
| GET | `/api/v1/businesses/{id}` | Get single Business (owner-only) |
| PATCH | `/api/v1/businesses/{id}` | Update Business (owner-only) |
| DELETE | `/api/v1/businesses/{id}` | Archive Business (soft delete) |

## 11. Security & Isolation
- All endpoints require Bearer token authentication (401 if missing/invalid).
- Tenant isolation enforced at repository/service layer via `owner_user_id` filter.
- `owner_user_id` derived solely from authenticated JWT.
- Cross-user access returns 404 to prevent enumeration.
- Immutable fields: `owner_user_id`, `slug`, `business_type`, `status` (except via archive), `created_at`.
- No password hashes, tokens, or internal details exposed in responses.

## 12. Persistence Strategy
- Currently implemented with in-memory persistence abstraction designed for seamless PostgreSQL migration.
- `AbstractBusinessRepository` + `InMemoryBusinessRepository` pattern mirrors the existing Account/Authentication architecture.

## 13. Business vs Account
- Account stores profile identity (display_name, phone, timezone, locale).
- Business stores tenant identity (name, type, status, slug).
- There is no `business_id` on the Account model — one Account can own many Businesses.

## 14. Current Limitations
- `SUSPENDED` status exists but is not settable via API yet (future status management feature).
- BusinessMembership is NOT implemented — ownership-based access is the interim model.
- Branch is NOT implemented — Business is the tenant boundary.
- Template Usaha is NOT implemented — business_type is configuration only, not a template reference.
