# Backend Foundation Readiness Implementation Plan

> **For agentic workers:** Use this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Align the Django account and timezone foundations with the product contract, add backend smoke coverage, and clean frontend/dependency automation warnings.

**Architecture:** Keep Django's custom user model as the source of account identity and add a migration from the current username-based schema. Test the health endpoint through Django's test client, extract the home page component from the router module, and point Dependabot at each package manifest directory.

**Tech Stack:** Django 5.2, PostgreSQL 16, React, TypeScript, Vite, GitHub Dependabot.

**Spec:** `GROCEREASE.md` and `BACKEND.md`.

## Global Constraints

- Email is the MVP login identifier and must be unique.
- `display_name` is the canonical profile name.
- Application time zone is `Asia/Manila`.
- Money and other product-domain behavior remain unchanged.
- Dependabot manifests are in `frontend/package-lock.json` and `backend/requirements.txt`.

## Review Focus

- Email-only user creation must not depend on a username field; test creation and uniqueness.
- Health checks must return HTTP 200, JSON status `ok`, and `Cache-Control: no-store`.
- Backend migration state must match the custom user model.
- Router module must export the router without defining a React component in that module.
- Dependabot directories must resolve to the two actual project roots.

### Task 1: Email-based custom user

**Files:** `backend/accounts/models.py`, `backend/accounts/managers.py`, `backend/accounts/migrations/`, `backend/accounts/tests.py`.

- [x] Add tests for email as `USERNAME_FIELD`, unique email, creating a user without a username, and email-based superuser creation.
- [x] Run the focused tests and confirm the identity assertions fail against the current model.
- [x] Implement the email manager/model fields and create the migration.
- [x] Run the full backend suite (6 tests) and `makemigrations --check --dry-run`; both pass.

### Task 2: Manila timezone and backend smoke coverage

**Files:** `backend/config/settings.py`, `backend/core/tests.py`.

- [x] Add a health endpoint smoke test for status, JSON body, and no-store header, plus a timezone setting test.
- [x] Confirm the timezone assertion fails before implementation; the health smoke test passes because the endpoint already existed.
- [x] Set `TIME_ZONE = 'Asia/Manila'`; the full backend suite passes.

### Task 3: Frontend router warning

**Files:** `frontend/src/app/router.tsx`, `frontend/src/pages/HomePage.tsx`.

- [x] Move the home component into its own module and import it from the router.
- [x] Run `npm run lint` and `npm run build`; both pass and lint reports no warning.

### Task 4: Dependabot manifest roots

**Files:** `.github/dependabot.yml`.

- [x] Set npm directory to `/frontend` and pip directory to `/backend`.
- [x] Parse the YAML and verify both package manager paths match their manifests.
