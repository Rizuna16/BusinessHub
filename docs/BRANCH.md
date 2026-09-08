# BusinessHub — Feature #6: Branch / Operational Boundary

## Overview
Branch is the **operational boundary** positioned underneath a single `Business` entity in BusinessHub SaaS multi-tenant platform.

### Hierarchy & Security Boundary
```
Account
  ↓
Business (Tenant / Data Boundary)
  ↓
Branch (Operational Boundary)
```

Each Branch belongs strictly to exactly one `Business`. Access to Branch operations is controlled exclusively through an `ACTIVE` `BusinessMembership` on the parent business.

---

## Data Model

Module Location: `backend/app/modules/branch/`

### Branch Entity Fields
| Field | Type | Description |
|---|---|---|
| `id` | `str` (UUID) | System generated unique identifier |
| `business_id` | `str` (UUID) | Authoritative parent Business ID |
| `name` | `str` | Branch name (1-100 chars, case-insensitive unique per business) |
| `code` | `str` | Operational identifier code (1-20 chars, case-insensitive unique per business, e.g., `BDG`) |
| `description` | `str | null` | Optional detailed description |
| `address` | `str | null` | Physical branch location address |
| `phone` | `str | null` | Contact phone number |
| `email` | `str | null` | Contact email address |
| `timezone` | `str` | Timezone identifier (default `UTC`) |
| `locale` | `str` | Locale code (default `en-US`) |
| `status` | `BranchStatus` | Status Enum: `ACTIVE`, `SUSPENDED`, `ARCHIVED` |
| `is_default` | `bool` | Default flag (at most 1 active default per business) |
| `created_at` | `datetime` | UTC creation timestamp |
| `updated_at` | `datetime` | UTC last update timestamp |

---

## Status Lifecycle

- **ACTIVE**: Operational branch available for business activities.
- **SUSPENDED**: Branch temporarily disabled for operations. Cannot act as default branch.
- **ARCHIVED**: Soft-deleted branch retained for audit and historical reference. Excluded from normal active list.

---

## Business & Membership Boundaries

1. **Path-Based Business Context**:
   `business_id` is supplied via path parameter `/api/v1/businesses/{business_id}/branches` and serves as the single source of truth for business ownership.
2. **Membership Enforcement**:
   Requester must have an `ACTIVE` `BusinessMembership` under the exact `business_id`.
   - `SUSPENDED` or `REMOVED` memberships receive HTTP 404 (anti-enumeration protection).
3. **Cross-Business Isolation**:
   Branch endpoints enforce `branch.business_id == path.business_id`. Looking up a branch under a mismatched business ID returns HTTP 404.

---

## Role Access Matrix

| Operation | OWNER | ADMIN | MEMBER | Unauthenticated |
|---|---|---|---|---|
| `POST /branches` (Create) | ALLOW | ALLOW | DENY (403) | DENY (401) |
| `GET /branches` (List) | ALLOW | ALLOW | ALLOW | DENY (401) |
| `GET /branches/{id}` (Get) | ALLOW | ALLOW | ALLOW | DENY (401) |
| `PATCH /branches/{id}` (Update) | ALLOW | ALLOW | DENY (403) | DENY (401) |
| `POST /branches/{id}/suspend` (Suspend) | ALLOW | ALLOW | DENY (403) | DENY (401) |
| `DELETE /branches/{id}` (Archive) | ALLOW | ALLOW | DENY (403) | DENY (401) |
| `POST /branches/{id}/default` (Set Default) | ALLOW | ALLOW | DENY (403) | DENY (401) |

---

## Default Branch Invariants

1. **Rule**: Every Business has **at most 1 default branch** (`is_default = true`).
2. **Auto-Default on Creation**: The first `ACTIVE` branch created for a business automatically becomes `is_default = true`.
3. **Explicit Set Default**: Setting branch B as default resets all other branches in the business to `is_default = false`.
4. **Fallback Mechanism**: When the current default branch is `SUSPENDED` or `ARCHIVED`, the system automatically selects another `ACTIVE` branch as default using a deterministic order (`created_at ASC`, `id ASC`). If no active branches remain, the business temporary has 0 default branches.

---

## Uniqueness Constraints

- `code`: Case-insensitive unique within the same `business_id` (e.g. `BDG` and `bdg` are duplicates in Business A). Different businesses may use identical codes.
- `name`: Case-insensitive unique within the same `business_id`. Different businesses may use identical names.

---

## API Endpoints Summary

- `POST /api/v1/businesses/{business_id}/branches`
- `GET /api/v1/businesses/{business_id}/branches`
- `GET /api/v1/businesses/{business_id}/branches/{branch_id}`
- `PATCH /api/v1/businesses/{business_id}/branches/{branch_id}`
- `DELETE /api/v1/businesses/{business_id}/branches/{branch_id}` (Archive / Soft-delete)
- `POST /api/v1/businesses/{business_id}/branches/{branch_id}/suspend`
- `POST /api/v1/businesses/{business_id}/branches/{branch_id}/default`

---

## Frontend Integration

- **Route**: `/businesses/:businessId/branches`
- **Page Component**: `frontend/src/pages/Branches.tsx`
- **Types**: `frontend/src/types/branch.ts`
- **API Client**: `frontend/src/services/apiClient.ts`
- **UI & UX Features**: Light/Dark mode support, mobile-first responsive table layout, confirmation dialogs for destructive actions, client-side form validation, role-based action visibility, and accessibility attributes.

---

## Verification & Testing

- Backend Unit & Integration Tests: `backend/tests/test_branch.py` (48 test cases PASS)
- Full Regression Suite: 168 test cases PASS across Health, Auth, Account, Business, BusinessMembership, Branch.
- Frontend Checks: TypeScript typecheck PASS (`tsc -b`), Production build PASS (`vite build`), Lint PASS (`oxlint`).
