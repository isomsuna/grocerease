# PR #10 Backend Review Fixes Implementation Plan

**Goal:** Resolve the backend findings from the second PR #10 review.

**Architecture:** Use PostgreSQL for shared DRF throttle counters and a durable, deduplicated password-reset outbox. Outbox rows store only a user reference and retry metadata; a Django management command creates reset tokens immediately before delivery and retries failures.

**Tech Stack:** Django 6.1, Django REST Framework, PostgreSQL, unittest.

**Requirements:** `GROCEREASE.md`, `BACKEND.md`, PR #10 second-pass findings.

## Global Constraints

- Keep the existing email-based `User` foundation and avoid storing or logging passwords/reset tokens.
- Preserve generic reset acknowledgments and require the current password for sensitive account changes.
- Keep registration, login, reset, password-change, and profile behavior covered by backend tests.

## Review Focus

- Spoofed or proxied `X-Forwarded-For` values must not bypass or collapse per-client throttling.
- Throttle counts must be shared across web workers and survive process restarts.
- Reset jobs must survive worker restarts, deduplicate pending work per account, retry failures, and store no reset token.
- Email address comparison must use the same lowercase normalization as `User.save()`.
- Reset links must preserve existing query parameters while replacing `uid` and `token`.

### Task 1: Shared, correctly keyed authentication throttles

**Files:** `backend/config/settings.py`, `backend/accounts/throttles.py`, `backend/accounts/views.py`, `backend/accounts/models.py`, generated account migration, `backend/accounts/tests.py`, `.env.example`.

- [ ] Add failing tests for configured `NUM_PROXIES`, database-backed cache storage, spoofed XFF throttling, registration throttling, and per-user password/profile throttling.
- [ ] Add the throttle cache table and configure Django's database cache; make `DJANGO_NUM_PROXIES` set DRF's proxy count.
- [ ] Add an authenticated scoped throttle keyed by user ID. Apply scopes to registration, password change, and profile update; retain IP-based scopes for login and reset initiation.
- [ ] Run the targeted tests and backend suite.

### Task 2: Durable password-reset outbox and worker

**Files:** `backend/accounts/models.py`, `backend/accounts/services.py`, new management command, generated account migration, `backend/accounts/tests.py`, `BACKEND.md`.

- [ ] Add failing tests for queued API behavior, deduplicated pending jobs, worker delivery, retries, process-restart recovery, no persisted token, and query-string-safe reset URLs.
- [ ] Implement a PostgreSQL outbox with one active job per user, retry metadata, and lease recovery. Generate reset tokens only when a worker sends the email.
- [ ] Add `send_password_reset_emails` with `--once` support and document the worker command.
- [ ] Run targeted reset tests and the backend suite.

### Task 3: Close remaining account and reset findings

**Files:** `backend/accounts/serializers.py`, `backend/accounts/services.py`, `backend/accounts/views.py`, `backend/accounts/tests.py`.

- [ ] Add failing tests for lowercase email-change comparison and generic duplicate-registration errors.
- [ ] Change comparison to `.strip().lower()`, return the generic registration message for duplicates and uniqueness races, and remove the unused unsaved user in registration.
- [ ] Remove redundant display-name validation and CSRF token generation.
- [ ] Run targeted tests, migration checks, and the full backend suite.
