# Super Admin & Platform Administration Architecture

## Overview
Feature #52 introduces platform-level administrative governance for BusinessHub. It establishes a strict architectural boundary between Platform Administration (`/api/v1/platform/...`, `/platform/...`) and Tenant Operations (`/api/v1/businesses/{business_id}/...`).

## Core Principles
1. **Separation of Concerns:** Super Admin is **NOT** a business membership role (`OWNER`, `ADMIN`, `MEMBER`). Platform actors operate independently of tenant business memberships.
2. **Server-Side Authorization:** JWT claims are for initial identification; server-side guards always re-verify current `Account.platform_role` and `is_active` state against the in-memory repository.
3. **Audit Immutability:** All platform mutations (suspend, activate, archive, subscription overrides) generate immutable append-only audit records with redaction of sensitive data.

## Platform Identity Model
We use the existing `Account` / `UserInDB` schema extended with a `platform_role` field. A `PlatformRole` enum currently holds only `SUPER_ADMIN`.

**JWT Claims:**
```json
{
  "sub": "account_uuid",
  "platform_role": "SUPER_ADMIN" | null,
  "type": "access",
  "iat": "...",
  "exp": "..."
}
```

## Authorization Pipeline
### Platform Routes (`/api/v1/platform/...`)
1. Validate JWT and extract `sub`.
2. Fetch current `UserInDB` from in-memory repository.
3. Check `account.is_active == True`.
4. Check `account.platform_role == PlatformRole.SUPER_ADMIN`.
5. Process request.

### Tenant Routes (`/api/v1/businesses/{business_id}/...`)
1. Validate JWT.
2. Fetch `BusinessMembership`.
3. **NEW:** Fetch `Business.status`.
4. If `Business.status == SUSPENDED` or `ARCHIVED`, reject request with `403 Forbidden`.

## Business Lifecycle Management
- `ACTIVE`: Normal access.
- `SUSPENDED`: Tenant access blocked immediately.
- `ARCHIVED`: Terminal state in Feature #52.

## Platform API (`/api/v1/platform/...`)
- `GET /dashboard`: Global metrics (active businesses, total accounts, MRR).
- `GET /businesses`: Metadata list with status and subscription summary.
- `POST /businesses/{id}/suspend`, `/activate`, `/archive`: Lifecycle mutations.
- `GET /users`: Read-only global account directory.
- `GET /audit-logs`: Immutable mutation trail.
