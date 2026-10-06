# GrocerEase GitHub CI Setup Implementation Plan

> **For agentic workers:** Use this plan task by task. Steps use checkbox syntax for tracking.

**Goal:** Add a reliable GitHub pull request and main branch CI workflow and apply the requested repository templates, labels, project board, and main branch protections.

**Architecture:** Keep CI in `.github/workflows/ci.yml`, with independent frontend and backend jobs. Use commands and environment settings already supported by the monorepo; configure GitHub metadata and branch rules through GitHub CLI/API where credentials permit.

**Tech Stack:** GitHub Actions, Node.js/npm, React/TypeScript/Vite, Python/Django, PostgreSQL, GitHub CLI.

**Spec:** User-provided GitHub Setup instructions; canonical product and implementation constraints in `GROCEREASE.md`, `FRONTEND.md`, and `BACKEND.md`.

## Global Constraints

- The Markdown specifications are authoritative; `GrocerEase.html` is a prototype reference.
- Backend money, price selection, estimates, and budget behavior remain Django/PostgreSQL responsibilities.
- Frontend build includes `tsc -b` followed by Vite build.
- Django database configuration reads `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT`.
- Do not report tests as run when no frontend test script exists.
- CI failures must fail the corresponding job so required status checks can block merges.
- Use PostgreSQL 16 to match `docker-compose.yml`.

## Review Focus

- Missing frontend test/typecheck scripts: run build for type checking; make test coverage gap explicit rather than claiming tests ran.
- PostgreSQL credentials and database name: provide all settings Django consumes.
- Frontend lockfile in a subdirectory: pass `frontend/package-lock.json` to dependency caching.
- Branch check naming: make required check names match workflow check runs exactly.
- GitHub project OAuth scope and first-run status checks: defer only the setting that cannot be configured until the workflow has run or scope is available.

---

### Task 1: CI Workflow

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Produces GitHub Actions checks named `frontend` and `backend` for pull requests and pushes to `main`.

- [x] Configure frontend checkout, Node 20, npm cache dependency path, `npm ci`, lint, and production build. The build provides TypeScript checking. Do not invoke missing frontend test scripts.
- [x] Configure PostgreSQL 16 service, Python 3.12, requirements cache/install, migration check, and Django tests with the environment names expected by Django settings.
- [x] Keep failures blocking; run summary reporting with `if: always()`.
- [x] Parse the workflow YAML with PyYAML; run frontend lint and production build locally. Lint exited successfully with an existing `react(only-export-components)` warning in `frontend/src/app/router.tsx`, and the production build succeeded. Backend migration checks and Django tests passed in PR CI run `37419569056`.

### Task 2: Issue and Pull Request Templates

**Files:**
- Create: `.github/ISSUE_TEMPLATE/feature.md`
- Create: `.github/ISSUE_TEMPLATE/bug.md`
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

**Interfaces:**
- GitHub issue forms are Markdown templates with the specified labels and field headings.
- PR template includes specification references, API/database impact, tests, and checklist.

- [x] Add feature and bug templates from the supplied text; use valid blank-title YAML and include FE/BE format guidance.
- [x] Add the supplied PR template sections, including the later Database impact and Checklist additions.
- [x] Review front matter and headings.

### Task 3: Git Workflow Guidance

**Files:**
- Create: `CONTRIBUTING.md`

**Interfaces:**
- Documents the supplied issue-to-merge sequence and `<type>/<issue-id>-<short-desc>` branch format.

- [x] Document Backlog → Ready → branch → implementation → tests → PR → review → CI → merge → Done.
- [x] Include the three branch naming examples.
- [x] Verify the guide does not introduce product scope or prototype behavior.

### Task 4: GitHub Labels and Project Board

**Files:** None (GitHub repository settings).

**Interfaces:**
- Creates/updates the 17 specified labels.
- Creates a Table project named `GrocerEase MVP` with the seven specified status options in order.

- [x] Create/update labels with specified descriptions and colors.
- [x] Create the project and configure its status options in the specified order; link it to `isomsuna/grocerease`.
- [x] Project is user-owned and private by default; no visibility change was requested.

### Task 5: Main Branch Protection

**Files:** None (GitHub repository settings).

**Interfaces:**
- Protects `main` with pull request review, conversation resolution, force-push/deletion restrictions, and required status checks after those checks have run once.

- [x] Apply the protection settings that can be safely enabled now.
- [x] Require one approval and conversation resolution; disable force pushes and deletions.
- [x] Ruling: use GitHub's default administrator bypass for the personal repository — GitHub only supports explicit push restrictions for organization-owned repositories, and the sole collaborator is the owner/admin — cost if wrong: administrators can push directly to `main` without PR review.
- [x] Add `frontend` and `backend` as required checks after GitHub observed both checks in PR CI run `37419569056`.
- [x] Read back the protection rule; both required checks are configured alongside the existing review and conversation-resolution requirements.
