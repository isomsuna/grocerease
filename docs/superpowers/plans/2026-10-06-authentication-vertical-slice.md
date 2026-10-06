# GrocerEase Authentication Vertical Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Implement BE-US-001 account registration, session authentication, password lifecycle, and safe profile endpoints.

**Architecture:** Keep the existing custom `User` and its migration intact. Use account services for lifecycle operations, DRF serializers for validation/representation, and API views for HTTP/session/CSRF behavior.

**Tech Stack:** Django 6.1, Django REST Framework, Django auth/session/CSRF, PostgreSQL.

**Spec:** `docs/superpowers/specs/2026-10-06-authentication-vertical-slice-design.md`

## Global Constraints

- Email is the case-insensitive unique login identifier and is stored lowercase.
- Use Django authentication and password hashing.
- Passwords and tokens never appear in API responses or logs.
- Login/reset errors do not reveal sensitive account details.
- Protected endpoints return 401 when unauthenticated.
- Do not implement stores, products, or later backend stories.

## Review Focus

- Mixed-case and whitespace email input: canonicalize before lookup/create; assert duplicate registration returns a validation error without a second account.
- Missing/inactive account or incorrect password at login: same generic response; assert no session is established.
- Unknown email at reset initiation: same generic acknowledgment as a known email; assert neither response includes UID/token.
- Invalid/expired reset token and weak new password: reject without changing the account password.
- Cookie-authenticated unsafe request without valid CSRF token: reject; assert bootstrap-issued cookie/token succeeds when supplied.

---

### Task 1: Auth API and session/CSRF foundation

**Files:**
- Modify: `backend/config/settings.py`
- Modify: `backend/config/urls.py`
- Create: `backend/accounts/serializers.py`
- Create: `backend/accounts/services.py`
- Create: `backend/accounts/views.py`
- Modify: `backend/accounts/tests.py`

**Interfaces:**
- `accounts.services.register_user(*, email: str, display_name: str, password: str) -> User`
- `accounts.services.authenticate_user(*, email: str, password: str) -> User | None`
- DRF views for `/api/auth/csrf/`, `/api/auth/register/`, `/api/auth/login/`, `/api/auth/logout/`, and `/api/me/`.

- [x] Add API tests for CSRF bootstrap, registration session establishment, duplicate/case-insensitive registration, login success/failure generic response, logout session invalidation, safe current-user output, profile GET/PATCH, and 401 access.
- [x] Run focused account API tests and confirm new behavior fails before implementation.
- [x] Implement serializers and account service functions; use Django validators and user manager; catch uniqueness races and map them to a clean email field error.
- [x] Implement session views and profile view; explicitly enforce CSRF on anonymous unsafe auth requests, use `SessionAuthentication` on protected endpoints, and configure secure production cookie flags with `SameSite=Lax`.
- [x] Run focused account API tests; confirm response payloads contain only safe profile fields and login errors are generic.

### Task 2: Password reset and change lifecycle

**Files:**
- Modify: `backend/config/settings.py`
- Modify: `backend/config/urls.py`
- Modify: `backend/accounts/serializers.py`
- Modify: `backend/accounts/services.py`
- Modify: `backend/accounts/views.py`
- Modify: `backend/accounts/tests.py`

**Interfaces:**
- `accounts.services.send_password_reset(*, email: str) -> None`
- `accounts.services.reset_password(*, uid: str, token: str, new_password: str) -> bool`
- `accounts.services.change_password(*, user: User, current_password: str, new_password: str) -> bool`

- [x] Add tests for generic reset initiation, email delivery with Django token, valid/invalid reset confirmation, password-validator enforcement, reset invalidating old sessions, password change current-password validation, and refreshing the current session hash.
- [x] Run focused password lifecycle tests and confirm new behavior fails before implementation.
- [x] Implement Django token generation/checking and email delivery; use a configured frontend reset URL; ensure API responses never return reset tokens; invalidate old sessions after successful reset.
- [x] Implement authenticated password change with current-password verification, configured password validators, and current-session hash refresh.
- [x] Run focused password lifecycle tests and inspect API response keys for secret disclosure.

### Task 3: Full backend verification

**Files:**
- No additional implementation files expected; adjust auth files/tests only if verification exposes a defect.

- [x] Run `python manage.py makemigrations --check --dry-run` from `backend/`; expected: no model changes detected.
- [x] Run the full backend test suite with `python manage.py test`; expected: all account, core, and migration tests pass.
- [x] Review git diff to ensure only BE-US-001, its documentation, and tests are included.
