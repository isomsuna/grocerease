# GrocerEase Authentication Vertical Slice Design

## Goal and scope

Implement BE-US-001 from `BACKEND.md`, preserving the existing email-based `accounts.User` foundation. Provide registration, login, logout, password reset start/confirm, password change, and safe current-profile GET/PATCH endpoints. Do not implement later backend stories.

## Design

- Keep account lifecycle orchestration in `accounts/services.py`; keep API input/output validation in DRF serializers and HTTP behavior in `accounts/views.py`.
- Use Django's configured user manager, authentication backend, password validators, password hashing, session framework, and password-reset token generator.
- Register and login establish Django sessions. Logout calls Django logout. `/api/me/` exposes only `id`, `display_name`, and `email`; profile PATCH permits only display name and email, with case-insensitive email uniqueness enforced.
- Use DRF `SessionAuthentication` and Django CSRF middleware. Add a small CSRF bootstrap endpoint so browser clients can fetch a CSRF cookie before anonymous unsafe auth requests. Require CSRF for registration, login, logout, and other unsafe cookie-auth requests. Set session/CSRF cookie `Secure` in production and `SameSite=Lax`.
- Password-reset initiation always returns a generic success response. For an existing active account, send an email containing Django-generated UID/token reset data and a configured frontend reset URL. Confirmation validates the UID/token and Django password validators before setting the password and invalidating existing sessions.
- Password change requires an authenticated session, validates the current password, applies password validators, updates the password, and refreshes the current session hash.
- Authentication failures use generic messages. Responses never include passwords, hashes, or reset tokens. Do not log credentials or reset payloads.

## Endpoints

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/logout/`
- `POST /api/auth/password-reset/`
- `POST /api/auth/password-reset/confirm/`
- `POST /api/auth/password-change/`
- `GET|PATCH /api/me/`
- `GET /api/auth/csrf/` (CSRF cookie bootstrap for browser clients)

Unauthenticated protected requests return 401. Auth endpoints use consistent DRF validation responses and never reveal account existence during login or reset initiation.

## Verification

Add comprehensive account API tests for the requested lifecycle, case-insensitive email uniqueness, safe serialization, CSRF enforcement and session behavior. Run `python manage.py makemigrations --check --dry-run` and the full backend test suite against the configured database.
