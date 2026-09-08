# Business Membership

## 1. Purpose

Feature #5 — Business Membership — introduces the relationship between a
`User` (authenticated via Authentication module) and a `Business`.

Before this feature the access model was:

```
User → Business (owner only)
```

After this feature the access model is:

```
User
↓
BusinessMembership (ACTIVE)
↓
Business (tenant / data boundary)
```

`Business.owner_user_id` is retained as an ownership reference for backward
compatibility, but **all runtime access** to a Business is determined by an
**active** `BusinessMembership`.

This is **not** a full RBAC/PBAC system. It only establishes:

```
identity ↔ business membership ↔ basic role
```

Granular authorization (permission matrices, attribute-based access) is out
of scope for this feature and will be delivered by the later **Access
Control** feature.

### Out of scope (will be built in other features)

- Branch / BranchMembership
- Invitation system (tokens, email invite, expiry, acceptance flow)
- Onboarding
- Template Usaha
- Subscription
- Billing
- Product / Category / Unit
- Customer / Supplier
- Sales / Purchase / Inventory / Payment / Cash / Expense / Reports
- Notifications
- Hotel / Retail / UMKM operational modules

(For development/testing you may add an existing authenticated user directly by
`user_id`. No email/ invitation lifecycle exists.)

---

## 2. Relationship Model

```
User ──┐
        ├─► BusinessMembership ──► Business
User ──┘  (unique on (business_id, user_id))
```

- A `Business` can have **many** members.
- A `User` can belong to **many** businesses.
- Every `Business` has **exactly one** active `OWNER` membership.
- The `owner_user_id` on `Business` MUST stay consistent with the single active
  `OWNER` membership `user_id`.

```
Business.owner_user_id   ≡  exactly one ACTIVE OWNER membership.user_id
```

---

## 3. Membership Model

### Fields

| Field         | Type                      | Notes                         |
| ------------- | ------------------------- | ----------------------------- |
| id            | uuid                      | Primary key                   |
| business_id   | uuid (FK Business)        | Tenant boundary               |
| user_id       | uuid (FK User)            | Member identity               |
| role          | enum                      | OWNER / ADMIN / MEMBER        |
| status        | enum                      | ACTIVE / SUSPENDED / REMOVED  |
| created_at    | datetime (UTC)            | Record created                |
| updated_at    | datetime (UTC)            | Last mutation                 |

### Roles

| Role    | Level | Description                         |
| ------- | ----- | ----------------------------------- |
| OWNER   | 3     | Full control, can archive business  |
| ADMIN   | 2     | Manage members (non-owner)          |
| MEMBER  | 1     | Read-only member                    |

### Statuses

| Status     | Meaning                                         |
| ---------- | ----------------------------------------------- |
| ACTIVE     | Has access to the business                      |
| SUSPENDED  | Access revoked, record retained for history     |
| REMOVED    | Soft-removed, retained for audit/history        |

### Uniqueness constraint

`UNIQUE (business_id, user_id)` — a user can have only one membership record
per business. Re-adding the same user is rejected with **409 Conflict**.

---

## 4. Owner Membership & Invariant

When a `Business` is created, the `BusinessService.create_business` method
automatically creates a `BusinessMembership`:

```python
BusinessMembership(
    business_id = new_business.id,
    user_id    = authenticated_user.id          # from JWT, never client-supplied
    role       = BusinessMembershipRole.OWNER,
    status     = BusinessMembershipStatus.ACTIVE,
)
```

### Owner protections (MUST be enforced)

- ❌ Cannot create a second OWNER (`add_member` rejects `role=OWNER`)
- ❌ Cannot promote any member to OWNER
- ❌ Cannot demote the OWNER
- ❌ Cannot suspend the OWNER
- ❌ Cannot remove the OWNER
- ❌ Owner cannot remove / suspend / demote **themselves**

The OWNER membership is returned as-is if `create_owner_membership` is called
again for the same `(business_id, user_id)` — no duplicate record is created.

---

## 5. Access Rules (Basic Membership Policy)

Authentication always comes from the JWT (`get_current_user`). Requester
identity is **never** read from the request body.

### Business endpoints (`Business` module — scope #5)

| Operation               | Required role | Notes                              |
| ----------------------- | ------------- | ---------------------------------- |
| `GET /businesses`       | active member | List businesses with active membership |
| `GET /businesses/{id}`  | active member | Any active role may read           |
| `PATCH /businesses/{id}`| OWNER / ADMIN | MEMBER → `403 Forbidden`           |
| `DELETE /businesses/{id}` (archive) | OWNER | ADMIN → `403 Forbidden`            |

Access check:
```
User → active BusinessMembership → Business
User without ACTIVE membership → denied
```

Membership requirement (`require_active_membership`):
```
if membership is None or membership.status != ACTIVE → 404 (anti-enumeration)
```

### Membership endpoints (`BusinessMembership` module)

| Operation                                | OWNER | ADMIN | MEMBER |
| ---------------------------------------- | :---: | :---: | :----: |
| `POST .../members` (add member)          |  ✓    |  ✓    |   403  |
| `GET .../members` (list)                 |  ✓    |  ✓    |   403  |
| `GET .../members/{id}`                   |  ✓    |  ✓    |   403  |
| `PATCH .../members/{id}` (role/status)   |  ✓    |  ✓(*) |   403  |
| `DELETE .../members/{id}`                |  ✓    |  ✓(*) |   403  |

`(*)` ADMIN cannot modify / suspend / remove / demote an OWNER.

### Member management rules

- `add_member` requester must be **OWNER** or **ADMIN**.
- Target `user_id` must reference an existing, active user.
- Target user must not already have a membership in this business.
- `role` in add payload cannot be `OWNER`.
- Membership always created with `status = ACTIVE`.
- Owner membership is immutable (role & status).
- ADMIN cannot promote anyone to `OWNER`.

---

## 6. API Contract

Base prefix: `/api/v1`

```
POST   /businesses/{business_id}/members                       Create member
GET    /businesses/{business_id}/members                       List members
GET    /businesses/{business_id}/members/{membership_id}       Get member
PATCH  /businesses/{business_id}/members/{membership_id}       Update role/status
DELETE /businesses/{business_id}/members/{membership_id}       Soft-remove (status=REMOVED)
```

### Add member request

```json
{
  "user_id": "user-uuid",
  "role": "ADMIN"        // OWNER not allowed
}
```

### Update member request (all fields optional)

```json
{
  "role": "ADMIN",
  "status": "SUSPENDED"
}
```

### Member response

```json
{
  "id": "membership-uuid",
  "business_id": "business-uuid",
  "user_id": "user-uuid",
  "role": "ADMIN",
  "status": "ACTIVE",
  "created_at": "2026-01-01T00:00:00Z",
  "updated_at": "2026-01-01T00:00:00Z",
  "email": "user@example.com",
  "display_name": "Display Name"
}
```

`email` / `display_name` are resolved from the existing User (Authentication)
and Account abstractions when available — never duplicated on the membership
record.

### Error codes (summary)

| Scenario                              | Status |
| ------------------------------------- | :----: |
| No JWT / invalid token                |  401   |
| No active membership (business)       |  404   |
| MEMBER attempts member mgmt            |  403   |
| ADMIN / MEMBER attempts business mutation |  403 |
| ADMIN attempts owner modification     |  400   |
| Owner self demote/suspend/remove      |  400   |
| Duplicate membership                  |  409   |
| Add / promote OWNER                   |  400   |
| Target user missing / inactive        |  404   |

---

## 7. Security

- `user_id` (requester) is derived **only** from the authenticated JWT.
- `user_id` in `POST .../members` body is the **target member**, never the
  requester.
- `business_id` is always taken from the **path**, never the body (no spoofing).
- Removed memberships are never hard-deleted.
- No `password` / `password_hash` / `JWT` / secrets are ever returned in any
  membership response.
- No stack traces leak in production.
- Cross-business isolation is enforced both at the service and repository level.
- `require_active_membership` returns `404` (not `403`) for absent / inactive
  membership to reduce enumeration surface — except where a `403` is required
  to communicate a role denial on an otherwise-valid resource.

### Cross-business isolation

A user with an active membership in Business A **cannot**:

- read / list members of Business B (returns 404)
- manage memberships of Business B (returns 404)
- spoof `business_id` (path is authoritative)

---

## 8. Persistence Strategy

- Architecture is a **modular monolith** using the repository abstraction
  pattern (`AbstractBusinessMembershipRepository`).
- The default implementation is `InMemoryBusinessMembershipRepository` keyed
  in-process — consistent with the existing Account / Business / User repos.
- The data model maps cleanly to **PostgreSQL** without architectural change:
  - `business_membership` table
  - `UNIQUE(business_id, user_id)` index
  - `role` / `status` as `VARCHAR` enums (or native `ENUM` type)
  - `created_at` / `updated_at` timestamps
- No Docker is used.
- No migration framework is introduced. The owner membership is created
  in-process during `create_business`; retro-fitting existing businesses is a
  compatibility concern handled by the test fixture clearing repos per test.

---

## 9. Business Access Integration

The `Business` module (scope #5) was updated backward-compatibly:

- **Business creation** now also creates the OWNER membership.
- **`list_my_businesses`** now returns businesses where the user has an
  **active** membership (not just `owner_user_id` matches).
- **`get_business`** requires an active membership (`404` otherwise).
- **`update_business`** requires active membership + role OWNER/ADMIN
  (`403` for MEMBER); MEMBER is read-only.
- **`archive_business`** requires active membership + role OWNER (`403` for
  ADMIN).

`Business.owner_user_id` is preserved for compatibility/reference only.

---

## 10. Reusable Role Guards

Located in `app.modules.business_membership.router`:

| Guard                       | Allows                |
| --------------------------- | --------------------- |
| `require_business_membership` | any active member    |
| `require_business_member`   | OWNER / ADMIN / MEMBER |
| `require_business_admin`    | OWNER / ADMIN         |
| `require_business_owner`    | OWNER                 |

These are thin FastAPI dependencies that resolve the requester's active
membership. They are **not** an RBAC / PBAC engine — no permission tables or
attribute evaluation exist yet.

---

## 11. Frontend

- `src/types/businessMembership.ts` — strict (no `any`) types.
- `src/services/apiClient.ts` — `listBusinessMembers`, `getBusinessMember`,
  `addBusinessMember`, `updateBusinessMember`, `removeBusinessMember`.
- `src/pages/BusinessMembers.tsx` — member management at
  `/businesses/:businessId/members`.
  - Role + status badges (dark mode themed via Foundation dark classes).
  - Add Member dialog (Target User ID + Role; OWNER not selectable).
  - Role editor (OWNER role disabled / non-editable).
  - Confirm dialogs for Suspend / Remove (removal keeps history).
  - Loading & error states; responsive table with horizontal scroll for
    mobile, status badges, and accessible controls.
- `BusinessDetail` links to the members page.

Role-based UI is **not** a security boundary — the backend remains
authoritative. Frontend hiding of actions degrades gracefully: a denied
request returns `403`/`404` which is surfaced as an error message.

---

## 12. Limitations / Current State

- RBAC / PBAC full **not implemented**.
- Branch / BranchMembership **not implemented**.
- Invitation system **not implemented** (only direct `user_id` add).
- Onboarding **not implemented**.
- Template Usaha **not implemented**.
- Subscription / Billing **not implemented**.
- No ownership transfer (would be a separate feature).

---

## 13. Testing Strategy (backend)

`tests/test_business_membership.py` covers:

- owner membership auto-created on business creation
- owner membership uniqueness / single owner invariant
- duplicate membership rejected (409)
- multiple members / multiple businesses per user
- list / get membership
- add member as OWNER / ADMIN (allowed), as MEMBER (403)
- admin cannot create OWNER / cannot modify OWNER
- owner cannot demote/suspend/remove self
- suspend (role change) & remove (soft-delete / REMOVED)
- suspended / removed members denied business access & excluded from list
- cross-business access & management isolation
- business list reflects active/suspended/removed membership states
- member read access allowed; member cannot mutate business
- admin/membership business mutation rules; admin cannot archive
- 401 / invalid token handling
- no sensitive-field leakage in membership responses
- regression: Authentication, Account, Business, Health

All backend tests pass (health, auth, account, business, membership).
