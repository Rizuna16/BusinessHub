# Feature #27 — Sales Enhancement

## Overview
Feature #27 provides operational enhancements to the Sales module (`#22`), integrating seamlessly with Payment (`#23`), Inventory (`#24`), Sales Return (`#25`), and Customer Receivable (`#26`).

## Enhancements Included
1. **Date Range Filtering:** Added `date_from` and `date_to` query parameters to list sales for flexible reporting and operational auditing.
2. **Repository Consistency:** Corrected schema attributes and model mappings (`is_deleted` alignment) across backend schemas and frontend types.
3. **Frontend Integration:** Linked Sales Detail with Receivable view and Sales Return history, enhancing overall visibility into transaction lifecycles.
4. **Dead Parameter Clean-up:** Removed unused `receiving_status` query parameter from the sales list endpoint.

## Architectural Boundaries
- **Sales Foundation Ownership:** Sales remains owned by `#22` (`Sales`, `SalesLine`, totals calculation).
- **Payment & Receivable Separation:** Payment records (`#23`) and Receivables (`#26`) are referenced via derived/read models without duplicating state.
- **No Accounting Engine:** Feature #27 remains strictly operational and non-accounting.

## API Additions
- `GET /api/v1/businesses/{business_id}/sales` now accepts optional `date_from` and `date_to` query parameters.

## Security & RBAC
- All endpoints remain protected under business active membership (`OWNER`, `ADMIN`, `MEMBER`). Tenant isolation is strictly enforced via `business_id` scoping.
