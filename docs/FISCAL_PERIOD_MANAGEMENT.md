# Feature #35 — Fiscal Period Management Documentation

## 1. Purpose & Scope
Fiscal Period Management establishes period-based financial controls for BusinessHub businesses. It extends the `accounting/` module by allowing business owners and admins to define, view, and close accounting periods (`AccountingPeriod`), making the existing closed-period guard in the journal posting engine fully functional.

## 2. Domain & Security Boundaries
- **Domain Position**: Positioned inside `app/modules/accounting/`.
- **Tenant Isolation**: Every `AccountingPeriod` belongs to a single `Business` via `business_id`. Cross-business period access or modification is strictly prevented.
- **Role-Based Authorization**:
  - **READ** (List, Get): Any active business member (`OWNER`, `ADMIN`, `MEMBER`).
  - **MUTATION** (Create, Close): Only active `OWNER` or `ADMIN`.

## 3. Data Model (`AccountingPeriodInDB`)
- `id`: Unique string identifier (UUID)
- `business_id`: Business tenant scope
- `period_name`: Unique period display name per business (e.g. "2026-01")
- `start_date`: Inclusive start date (`date`)
- `end_date`: Inclusive end date (`date`)
- `status`: Period lifecycle status (`OPEN` | `CLOSED`)
- `created_at`: Creation timestamp (`datetime`)
- `created_by_user_id`: User ID of creator (`str`)
- `updated_at`: Last update timestamp (`datetime`)
- `closed_at`: Closure timestamp (`Optional[datetime]`)
- `closed_by_user_id`: User ID who closed the period (`Optional[str]`)

## 4. Invariants & Business Rules
1. **Date Order**: `start_date` must not exceed `end_date`.
2. **Name Uniqueness**: `period_name` must be unique per business.
3. **No Overlaps**: Period date ranges cannot overlap with any existing period in the same business.
4. **Permanent Closure**: Period status transitions from `OPEN` to `CLOSED`. Reopening is out-of-scope for Feature #35.
5. **Journal Posting Guard**: When a journal entry is posted via `create_and_post_journal()`, the system looks up the matching period for the journal date. If the matching period is `CLOSED`, the posting is rejected with HTTP 400 Bad Request.
6. **Backward Compatibility (Missing Period)**: If no period exists for a journal date, journal posting remains allowed (backward-compatible behavior).

## 5. API Endpoints
- `GET /api/v1/businesses/{business_id}/accounting/periods` — List periods for business (sorted by start_date desc)
- `POST /api/v1/businesses/{business_id}/accounting/periods` — Create new accounting period (OWNER/ADMIN only)
- `GET /api/v1/businesses/{business_id}/accounting/periods/{period_id}` — Get period detail
- `POST /api/v1/businesses/{business_id}/accounting/periods/{period_id}/close` — Close accounting period (OWNER/ADMIN only)

## 6. Frontend Pages & Routes
- Route: `/businesses/:businessId/accounting/periods`
- Component: `AccountingPeriods.tsx`
- Navigation: Period List, Status badges (`OPEN` / `CLOSED`), Create Period Modal, Close Period Confirmation.

## 7. Out of Scope
- Reopening closed periods (`REOPENED` status)
- Year-end closing / retained earnings automation
- Automatic period generation
- Fiscal year configuration
- Opening balance carry-forward
