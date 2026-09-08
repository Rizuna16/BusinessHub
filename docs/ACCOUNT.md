# BusinessHub — Account & User Profile Documentation

## 1. Account Purpose
The Account layer represents the user's platform profile and identity preferences within BusinessHub. It stores user-specific profile configurations (display name, phone number, avatar URL, timezone, and locale) separate from authentication credentials (email and password).

## 2. User vs Account Distinction
- **User / Authentication Identity**: Manages `id`, `email`, `password_hash`, `is_active`, and auth state. Managed exclusively by the Authentication module.
- **Account / Profile Layer**: Manages profile metadata (`display_name`, `phone`, `avatar_url`, `timezone`, `locale`). Linked 1:1 to a User via `user_id`.

## 3. API Endpoints
- `GET /api/v1/account`: Retrieves the authenticated user's account profile (lazy-creates a default profile on first access if not already present). Requires Bearer token authentication.
- `PATCH /api/v1/account`: Partially updates allowed account fields (`display_name`, `phone`, `avatar_url`, `timezone`, `locale`). Unspecified fields are preserved. Email, password, user_id, and id are immutable.

## 4. Fields & Validation
- `display_name`: Required string (2–100 characters), cannot be whitespace only.
- `phone`: Optional string (max 30 chars), validated with reasonable phone format regex.
- `avatar_url`: Optional string, must be valid HTTP/HTTPS URL.
- `timezone`: IANA timezone identifier (e.g. `Asia/Jakarta`, `UTC`). Offset notation (+07:00) is rejected.
- `locale`: Standard locale identifier (`en-US`, `id-ID`, etc.).

## 5. Security Model & Cross-User Isolation
- Access requires valid authentication (`401` if unauthenticated or invalid token).
- `user_id` is derived strictly from the authenticated JWT context (sub claim) and cannot be overridden or spoofed via request body parameters or query strings.
- Cross-user isolation tests confirm that User A cannot access or modify User B's account profile.
- Sensitive credentials (`password_hash`, tokens) are never returned in responses.

## 6. Persistence Decision
- Currently implemented using robust in-memory persistence abstractions designed to seamlessly swap out for PostgreSQL in production without architectural rewrites.

## 7. Multi-Tenancy Boundary Notice
- **Business is NOT implemented in this feature.**
- Account is a platform identity/profile layer. Business will serve as the multi-tenant boundary in subsequent features.
