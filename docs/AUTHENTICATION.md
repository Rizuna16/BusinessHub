# AUTHENTICATION MODULE DOCUMENTATION

## 1. Authentication Endpoints

- `POST /api/v1/auth/register` — Register a new account (returns User identity, no password/hash).
- `POST /api/v1/auth/login` — Authenticate email & password, returns JWT Access Token.
- `GET /api/v1/auth/me` — Protected endpoint returning current user profile.
- `POST /api/v1/auth/logout` — Client-side token clear and logout endpoint.

## 2. Authentication Flow

1. User registers via `/register` UI or API.
2. Email is normalized to lowercase and trimmed; password is hashed using bcrypt.
3. User logs in via `/login`, credentials are verified against stored hash, and a signed JWT token is issued.
4. Protected routes and endpoints pass `Authorization: Bearer <token>`.
5. Reusable `get_current_user` dependency in FastAPI decodes and validates token, rejecting invalid, malformed, inactive, or expired tokens with HTTP 401/403.

## 3. Password Hashing & Security

- Algorithm: `bcrypt` password hashing with random salt.
- Plaintext passwords and hashes are strictly excluded from API responses and log outputs.
- Generic error messages ("Invalid email or password.") prevent account enumeration.

## 4. Token & Session Mechanism

- Short-lived JWT access tokens configured via `JWT_SECRET_KEY`, `JWT_ALGORITHM` (HS256), and `JWT_EXPIRE_MINUTES`.
- Secret key loaded exclusively from environment variables (`.env`).

## 5. Environment Variables

- `JWT_SECRET_KEY`: Secret string used for signing JWTs.
- `JWT_ALGORITHM`: Hashing algorithm (default HS256).
- `JWT_EXPIRE_MINUTES`: Access token validity duration in minutes.

## 6. Limitations & Considerations

- Currently utilizes an abstract repository (`InMemoryUserRepository`) ready for seamless transition to PostgreSQL repository without altering domain/use-case logic.
- Distributed rate limiting is deferred until Redis integration in future phases.
