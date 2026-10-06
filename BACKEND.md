# GrocerEase — Backend MVP Specification

**Status:** Canonical Django/PostgreSQL implementation contract  
**Aligned with:** `GROCEREASE.md` and `FRONTEND.md`  
**Prototype note:** Browser-side mock calculations in `GrocerEase.html` are prototype-only. All authoritative ownership, persistence, price selection, totals, recommendations, estimates, and budget decisions belong here.

---

## 1. Backend Responsibility

The GrocerEase backend is responsible for:

- authentication and authorization;
- user ownership isolation;
- persistence and data integrity;
- validation;
- authoritative money/quantity calculations;
- shopping-session lifecycle;
- historical price derivation;
- shopping-plan lifecycle;
- frequent-product suggestions;
- store-specific plan estimation;
- budget-status calculation;
- What Fits My Budget calculation;
- dashboard/spending aggregates;
- filtering and pagination.

> **Django decides what is true. PostgreSQL preserves what happened.**

---

## 2. Required Stack & Architecture

### Required

- Django
- Django REST Framework
- PostgreSQL
- Django authentication

### Recommended

- `django-filter`
- Service layer for business rules
- Serializer/request validation for shape-level validation
- Database transactions for multi-record mutations
- Cursor or page-number pagination
- Structured logging
- Environment-based settings/secrets

### Suggested Django apps

```text
apps/
  accounts/
  stores/
  products/
  shopping/
  planning/
```

Suggested ownership:

```text
accounts/
  auth
  profile

stores/
  store CRUD/archive/restore

products/
  product catalog
  product history queries

shopping/
  shopping sessions
  purchase items
  spending history

planning/
  shopping plans
  plan items
  suggestions
  estimation
  budget logic
```

---

# 3. Global Backend Requirements

## 3.1 Authentication

Use Django's authentication/password hashing.

Required flows:

- Register
- Login
- Logout
- Current user
- Forgot password
- Reset password
- Password change

Recommended endpoint shape:

```text
POST /api/auth/register/
POST /api/auth/login/
POST /api/auth/logout/
POST /api/auth/password-reset/
POST /api/auth/password-reset/confirm/
POST /api/auth/password-change/
GET  /api/me/
PATCH /api/me/
```

Deployment may use secure same-site session cookies or a secure token strategy. The concrete mechanism may vary, but API authorization behavior must remain consistent.

### Rules

- Email is the MVP login identifier and is unique.
- Changing the account email or password requires the current password (see §5.1).
- Passwords never appear in responses/logs.
- Password-reset requests enqueue durable email jobs without persisting reset tokens. Run `python manage.py send_password_reset_emails` as a worker process to deliver and retry queued mail.
- Authentication throttles use the PostgreSQL database cache table installed by migrations. Set `DJANGO_NUM_PROXIES` to the trusted ingress proxy count in every deployment; production startup fails if it is missing. Use `0` only when clients connect directly without a trusted proxy. The ingress must remove client-supplied forwarded headers before appending its own.
- Production cookies/tokens use secure configuration.
- CSRF/CORS matches deployment topology.

---

## 3.2 Authorization & Ownership

All domain data is private to one authenticated user.

Every lookup must be scoped through `request.user` or an ownership-safe parent.

Applies to:

- Store
- Product
- ShoppingSession
- PurchaseItem
- ShoppingPlan
- ShoppingPlanItem
- Price-history queries
- Suggestions
- Dashboard aggregates

### Foreign-key validation

Any submitted ID such as `store_id`, `product_id`, `plan_id`, or `session_id` must be resolved within the authenticated user's queryset.

### Safe not-found behavior

Requesting another user's resource should normally behave like a `404` rather than disclosing its existence.

---

## 3.3 Money & Quantity

Use Python `Decimal` and PostgreSQL numeric types.

Recommended fields:

```text
receipt_total  NUMERIC(12,2)
unit_price     NUMERIC(12,2)
line_total     NUMERIC(12,2)
budget         NUMERIC(12,2)
quantity       NUMERIC(10,3)
```

Never use binary floating point for authoritative monetary calculations.

All money is in Philippine pesos (PHP). There is no currency field or conversion.

### Precision and rounding

- Every money amount has exactly 2 decimal places.
- Quantity allows up to 3 decimal places.
- Products of quantity and price are rounded to 2 decimal places with `ROUND_HALF_UP`, per line, before any aggregation.
- Aggregates (items subtotal, known total, budget-fit totals, remaining, over-by, spending) are sums/differences of already-rounded 2-decimal amounts.

Examples:

```text
0.10 + 0.20          = 0.30
1.5 × 95.25 = 142.875 → 142.88
0.5 × 0.25  = 0.125   → 0.13
3 lines of 0.5 × 0.25 → 0.13 + 0.13 + 0.13 = 0.39
```

### Authoritative line total

```text
line_total = round_half_up(quantity × unit_price, 2)
```

Never trust a client-submitted line total as final.

---

## 3.4 Time

- `created_at`, `updated_at` on primary models.
- `completed_at` where relevant.
- Timezone-aware datetimes (`USE_TZ = True`).
- Application time zone is `Asia/Manila` (`TIME_ZONE = 'Asia/Manila'`).
- "Today" and calendar-month boundaries (for example monthly spending) are evaluated in `Asia/Manila`, e.g. via `django.utils.timezone.localdate()`.
- `purchase_date` and `planned_date` are date fields.

---

## 3.5 API Error Shape

Use a consistent structure.

Field errors:

```json
{
  "errors": {
    "quantity": ["Quantity must be greater than zero."]
  }
}
```

Non-field:

```json
{
  "errors": {
    "non_field_errors": ["Unable to complete this shopping session."]
  }
}
```

Conflict example:

```json
{
  "code": "PRODUCT_ALREADY_IN_PLAN",
  "errors": {
    "product_id": ["This product is already in the plan."]
  },
  "existing_item_id": "..."
}
```

Unexpected exceptions are logged server-side; production responses never expose stack traces.

---

## 3.6 Pagination

Paginate list endpoints from the beginning.

At minimum:

- shopping sessions/history;
- products;
- plans if data grows;
- price history when necessary.

Use stable deterministic ordering.

---

# 4. Domain Models

## 4.1 User Profile

The custom Django user model holds the profile fields. No separate preference model is required for MVP.

```text
id
email            unique, login identifier
display_name
```

### Rules

- API exposes one canonical `display_name`.
- `display_name` is required, and Django's `get_full_name()` and `get_short_name()` return it.
- Email is required and case-insensitively unique; authentication ignores letter case and stores addresses in lowercase.
- There is no per-user currency setting; all money is PHP.

---

## 4.2 Store

```text
id
user_id
name
branch_label
notes
status            ACTIVE | ARCHIVED
created_at
updated_at
```

### Rules

- Store belongs to one user.
- Archived stores remain valid references for historical sessions/plans.
- Normal selectors query only ACTIVE stores.
- An archived store cannot be assigned to a new record. Creating a shopping session or plan, completing a draft session, or changing a session's or plan's `store_id` requires an ACTIVE owned store; otherwise return a `400` field error on `store_id`.
- A record that already references a store keeps it after the store is archived. Updates that leave `store_id` unchanged are not rejected because the store is archived.
- Exact duplicate store name/branch may produce a warning, but need not be hard-blocked because legitimate duplicate labels are possible.

Recommended indexes:

```text
(user_id, status)
(user_id, name)
```

---

## 4.3 Product

```text
id
user_id
name
normalized_name
category
unit_label        nullable
is_active
created_at
updated_at
```

### Category choices

```text
PANTRY
DAIRY_EGGS
MEAT_SEAFOOD
PRODUCE
BAKERY
BEVERAGES
HOUSEHOLD
PERSONAL_CARE
FROZEN
SNACKS
OTHER
```

### Normalization

Recommended normalization:

- trim leading/trailing whitespace;
- collapse repeated internal whitespace;
- case-fold/lowercase for uniqueness key.

### Constraint

```text
UNIQUE(user_id, normalized_name)
```

### Rules

- No fuzzy auto-merging in MVP.
- Deactivating a product preserves historical references.

Recommended indexes:

```text
(user_id, normalized_name)
(user_id, category)
(user_id, is_active)
```

---

## 4.4 ShoppingSession

Represents a manually entered past shopping receipt.

```text
id
user_id
store_id          nullable while DRAFT
purchase_date     nullable while DRAFT
receipt_total     nullable while DRAFT
status            DRAFT | COMPLETED
notes             nullable
created_at
updated_at
completed_at      nullable
```

### Draft rules

A DRAFT may be intentionally incomplete.

Drafts do not participate in:

- price history;
- suggestions;
- monthly spending;
- recent completed session;
- default completed history.

### Completed rules

A COMPLETED session requires:

- owned store, which must be ACTIVE when the session is created as completed, when a draft is completed, or when its store is changed (see §4.2); a correction that keeps the existing store is allowed even if that store has since been archived;
- purchase date;
- receipt total `>= 0`;
- at least one valid PurchaseItem;
- all completion validations passing.

Recommended indexes:

```text
(user_id, status, purchase_date)
(user_id, store_id, purchase_date)
(user_id, updated_at)
```

---

## 4.5 PurchaseItem

```text
id
shopping_session_id
product_id
quantity
unit_price
line_total
created_at
updated_at
```

### Rules

- Product must belong to same user as session.
- Quantity `> 0` for valid persisted item.
- Unit price `>= 0`.
- Line total is backend calculated.
- One product may appear at most once in a session.

Constraint:

```text
UNIQUE(shopping_session_id, product_id)
```

### Historical price meaning

A completed PurchaseItem is a price observation at:

- its parent session's store;
- its parent session's purchase date.

No separate price-history table is required for MVP.

---

## 4.6 ShoppingPlan

```text
id
user_id
store_id          required
name
planned_date      nullable
budget            nullable
status            ACTIVE | COMPLETED | ARCHIVED
created_at
updated_at
completed_at      nullable
```

### Rules

- Store belongs to user.
- Store must be ACTIVE when the plan is created or its store is changed (see §4.2).
- New plan starts ACTIVE.
- Blank/empty name becomes `Untitled plan` server-side.
- `budget = null` means no budget.
- Budget, when present, must be `>= 0`.
- Completed/archived plans remain readable.

Recommended indexes:

```text
(user_id, status, updated_at)
(user_id, store_id)
```

---

## 4.7 ShoppingPlanItem

```text
id
shopping_plan_id
product_id
quantity
priority          MUST_HAVE | OPTIONAL
sort_order
created_at
updated_at
```

### Rules

- Product belongs to same user as plan.
- Quantity `> 0`.
- One product per plan.
- Sort order is deterministic within plan.

Constraint:

```text
UNIQUE(shopping_plan_id, product_id)
```

Duplicate add attempts should return a clear conflict containing the existing item ID rather than silently creating another row.

---

# 5. Feature/API Specifications

## 5.1 Current User

### Endpoints

```text
GET   /api/me/
PATCH /api/me/
```

Response should include at minimum:

```json
{
  "id": "...",
  "display_name": "Alex",
  "email": "alex@example.com"
}
```

### Rules

- Email uniqueness enforced when changed.
- Changing `email` requires `current_password` in the same `PATCH` request. A missing or incorrect current password returns `400` with an error on `current_password`, and nothing is updated.
- Re-sending the shopper's existing email (ignoring letter case) is not a change and needs no password.
- Changing only `display_name` does not require the current password.
- `POST /api/auth/password-change/` requires `current_password` and `new_password`; an incorrect current password returns `400` with an error on `current_password`.

Email-change request example:

```json
{
  "email": "new-address@example.com",
  "current_password": "..."
}
```

---

## 5.2 Store Management

### Endpoints

```text
GET   /api/stores/
POST  /api/stores/
GET   /api/stores/:id/
PATCH /api/stores/:id/
POST  /api/stores/:id/archive/
POST  /api/stores/:id/restore/
```

### List behavior

Query:

```text
?status=ACTIVE
?status=ARCHIVED
?search=metro
```

Default can be ACTIVE for selector-oriented calls; management page may explicitly request both states/tabs.

### Archive rules

- Do not hard-delete store if historical data references it.
- Archive simply changes status.
- Existing historical references remain valid.

---

## 5.3 Product Catalog

### Endpoints

```text
GET   /api/products/
POST  /api/products/
GET   /api/products/:id/
PATCH /api/products/:id/
```

### Query support

```text
?search=milk
?category=DAIRY_EGGS
?is_active=true
?page=1
```

### Create rules

- Normalize name.
- Reject same user's exact normalized duplicate with `400` or `409` and existing product identifier when useful.
- No fuzzy matching/merging.

### Summary fields

Product list response may include efficiently-derived:

- times purchased;
- last purchase date;
- latest price paid;
- latest store.

These values use completed sessions only.

---

## 5.4 Shopping Session Create / Draft Save

### Endpoint

```text
POST /api/shopping-sessions/
```

### Recommended request

```json
{
  "status": "DRAFT",
  "store_id": null,
  "purchase_date": null,
  "receipt_total": null,
  "notes": "",
  "items": [
    {
      "product_id": "p1",
      "quantity": "2.000",
      "unit_price": "95.00"
    }
  ]
}
```

`status` may be `DRAFT` or `COMPLETED` on initial create.

### Draft validation

Drafts are permissive, but any provided item should still be structurally valid enough to persist safely.

Recommended:

- If product is present, quantity/unit price must be valid.
- Do not persist blank phantom item rows.
- Enforce no duplicate product rows among persisted items.

### Completed validation

If `status=COMPLETED`, run full completion validation before committing.

### Transaction

Session + items must be written atomically.

---

## 5.5 Shopping Session Update / Correction

### Endpoint

```text
GET   /api/shopping-sessions/:id/
PATCH /api/shopping-sessions/:id/
```

PATCH may contain the full canonical items collection for MVP simplicity.

### Draft update

May remain incomplete.

### Completed correction

If existing status is COMPLETED:

- keep status COMPLETED unless an explicitly supported state transition says otherwise;
- validate complete-state requirements after patch;
- recompute all line totals;
- replace/update item set transactionally;
- update `updated_at`;
- do not create a second shopping session;
- derived price-history/suggestions automatically reflect corrected rows on future queries.

### Important

Because price history is derived rather than duplicated, no stale price-history record needs manual synchronization.

---

## 5.6 Complete Draft Shopping Session

### Endpoint

```text
POST /api/shopping-sessions/:id/complete/
```

### Process

1. Lock/resolve owned draft.
2. Validate store (owned and ACTIVE)/date/receipt total/items.
3. Recalculate line totals.
4. Set `status=COMPLETED`.
5. Set `completed_at=now()`.
6. Commit atomically.

### Idempotency

Calling complete on an already-completed session should return the completed state or a clear validation response; it must not create duplicate history.

---

## 5.7 Discard Draft

### Endpoint

```text
DELETE /api/shopping-sessions/:id/
```

### Rule

Allowed only when `status=DRAFT` in MVP.

Attempting to DELETE a completed session returns a validation/conflict response explaining completed sessions must be corrected instead.

---

## 5.8 Receipt Total Mismatch

Backend calculates:

```text
items_subtotal = Σ line_total
receipt_difference = receipt_total - items_subtotal
```

Mismatch never invalidates an otherwise valid completed session.

Return both values in detail/create/update responses.

---

## 5.9 Shopping History

### Endpoint

```text
GET /api/shopping-sessions/
```

### Query parameters

```text
status=COMPLETED|DRAFT
store_id=<id>
date_from=YYYY-MM-DD
date_to=YYYY-MM-DD
page=<n>
page_size=<n>
```

### Defaults

If status omitted for a normal history query, recommended default is `COMPLETED`.

### Ordering

Completed:

```text
purchase_date DESC, completed_at DESC, created_at DESC
```

Drafts:

```text
updated_at DESC
```

### Row response

- id
- status
- store summary if present
- purchase_date
- receipt_total
- item_count
- created_at
- updated_at

Use annotation/prefetch to avoid per-row count queries.

---

## 5.10 Price History

### Endpoint

```text
GET /api/products/:id/price-history/
```

Optional filters:

```text
store_id=<id>
date_from=<date>
date_to=<date>
```

### Response observation

```json
{
  "shopping_session_id": "...",
  "store": {"id": "...", "name": "Metro Supermarket", "branch_label": "Ayala"},
  "purchase_date": "2026-09-24",
  "quantity": "2.000",
  "unit_price": "95.00"
}
```

Completed sessions only.

---

## 5.11 Latest Store Price Service

### Service

```text
PriceEstimationService.get_latest_price(user, product, store)
```

### Algorithm

Filter PurchaseItem where:

- session.user = user
- product = product
- session.store = store
- session.status = COMPLETED

Order:

```text
session.purchase_date DESC,
session.completed_at DESC,
session.created_at DESC,
purchase_item.id DESC
```

Return:

- unit price;
- purchase date;
- shopping session ID;
- store summary.

If no match, return `None`.

Never silently fall back to another store.

---

## 5.12 Shopping Plans

### Endpoints

```text
GET    /api/plans/
POST   /api/plans/
GET    /api/plans/:id/
PATCH  /api/plans/:id/
DELETE /api/plans/:id/
POST   /api/plans/:id/archive/
POST   /api/plans/:id/reactivate/
POST   /api/plans/:id/complete/
```

### List filters

```text
status=ACTIVE|COMPLETED|ARCHIVED
store_id=<id>
page=<n>
```

### Create validation

- Store is required, owned, and ACTIVE.
- Budget nullable; if provided `>= 0`.
- Name normalized; blank → `Untitled plan`.
- Status is server-controlled and starts ACTIVE.

### Delete

Deleting a plan hard-deletes the plan and plan items only.

It must not delete:

- products;
- stores;
- shopping sessions;
- purchase items;
- historical prices.

### No duplicate endpoint

Plan duplication is explicitly deferred from MVP.

---

## 5.13 Plan Lifecycle State Transitions

### Archive

```text
ACTIVE -> ARCHIVED
```

### Complete

```text
ACTIVE -> COMPLETED
```

Set `completed_at`.

Completion never creates a ShoppingSession.

### Reactivate

```text
ARCHIVED -> ACTIVE
COMPLETED -> ACTIVE
```

Clear `completed_at` when reactivating a completed plan.

### Invalid transitions

Return clear validation errors rather than silently forcing state.

---

## 5.14 Plan Items

### Endpoints

```text
POST   /api/plans/:plan_id/items/
PATCH  /api/plans/:plan_id/items/:item_id/
DELETE /api/plans/:plan_id/items/:item_id/
POST   /api/plans/:plan_id/items/reorder/
```

### Add request

```json
{
  "product_id": "p1",
  "quantity": "1.000",
  "priority": "OPTIONAL"
}
```

### Duplicate behavior

If product already exists:

- return conflict with `existing_item_id`;
- do not auto-increment quantity server-side because that can change intent unexpectedly.

Frontend can focus existing item and let user explicitly change quantity.

### Reorder request

```json
{
  "ordered_item_ids": ["i3", "i1", "i2"]
}
```

Validate all IDs belong to the plan and the set is complete/consistent according to chosen API contract.

### Plan status edits

MVP may allow editing completed/archived plans only after Reactivate. Recommended: reject item mutations unless plan is ACTIVE.

---

## 5.15 Create Plan From Shopping Session

### Endpoint

```text
POST /api/plans/from-session/:session_id/
```

### Preconditions

- Session belongs to user.
- Session status is COMPLETED.

### Optional request fields

```json
{
  "name": "Weekly Groceries",
  "store_id": "optional override",
  "budget": null
}
```

### Behavior

- Create ACTIVE plan.
- Default store to source session store unless valid override provided.
- If the source session's store is archived, an ACTIVE `store_id` override is required; without one, return a `400` field error on `store_id`.
- Copy product references and quantities.
- Set item priority default `OPTIONAL` unless product decision changes later.
- Preserve source item order if available; otherwise stable order.
- Do not copy unit prices as fixed plan prices.
- Estimates are derived normally after creation.

### Historical isolation

Future plan edits never modify the source session.

---

## 5.16 Frequent Product Suggestions

### Service

```text
ShoppingSuggestionService
```

### Endpoint

```text
GET /api/suggestions/products/
```

Optional query:

```text
plan_id=<id>
limit=<n>
```

### Default algorithm

1. Fetch user's latest four COMPLETED sessions.
2. Count distinct sessions containing each product.
3. Keep products appearing in at least two sessions.
4. Rank by:
   - session frequency DESC;
   - most recent purchase DESC;
   - product name ASC.
5. If `plan_id` supplied, exclude products already present in that owned plan.

### Response

```json
{
  "recent_session_count": 4,
  "suggestions": [
    {
      "product": {"id": "p2", "name": "Fresh Milk 1L"},
      "sessions_purchased": 4,
      "reason": "Bought in 4 of your last 4 trips"
    }
  ]
}
```

No machine-learning claims.

---

## 5.17 Plan Estimation

### Service

```text
PlanEstimationService
```

### Endpoint

```text
GET /api/plans/:id/estimate/
```

### Item algorithm

For each plan item:

1. Resolve latest historical price for `plan.store`.
2. If known:

```text
estimated_unit_price = historical unit price
estimated_line_total = round_half_up(quantity × unit price, 2)
```

3. If unknown:

```text
estimated_unit_price = null
estimated_line_total = null
```

### Aggregate

```text
known_total = sum(known line totals)
unknown_item_count = count(unknown items)
estimate_complete = unknown_item_count == 0
```

### Item response example

```json
{
  "plan_item_id": "i1",
  "product": {"id": "p2", "name": "Fresh Milk 1L"},
  "quantity": "2.000",
  "estimated_unit_price": "95.00",
  "estimated_line_total": "190.00",
  "price_source": {
    "shopping_session_id": "ss9",
    "purchase_date": "2026-09-24",
    "store_id": "s1"
  }
}
```

Unknown example:

```json
{
  "estimated_unit_price": null,
  "estimated_line_total": null,
  "price_source": null
}
```

### Optional other-store context

If product UX needs it, backend may additionally return latest known price at another store as `other_store_context`. This field must never affect selected-store totals.

---

## 5.18 Budget Calculation

### Service

```text
BudgetCalculationService
```

### Status choices

```text
NO_BUDGET
WITHIN_BUDGET
OVER_BUDGET
INCOMPLETE_ESTIMATE
```

### Algorithm

Given plan budget, known total, unknown count:

```text
if budget is null:
    status = NO_BUDGET
elif unknown_item_count > 0:
    status = INCOMPLETE_ESTIMATE
elif known_total <= budget:
    status = WITHIN_BUDGET
else:
    status = OVER_BUDGET
```

Always compute when budget exists:

```text
known_total_exceeds_budget = known_total > budget
```

For complete estimate:

```text
remaining = max(budget - known_total, 0)
over_by = max(known_total - budget, 0)
```

For incomplete estimate, `remaining` may be omitted/null because final remaining budget is unknowable. Backend may additionally expose `remaining_after_known_items` if useful, clearly named as provisional.

### Estimate response example

```json
{
  "plan_id": "pl1",
  "budget": "3000.00",
  "known_total": "2650.00",
  "unknown_item_count": 2,
  "estimate_complete": false,
  "budget_status": "INCOMPLETE_ESTIMATE",
  "known_total_exceeds_budget": false,
  "remaining": null,
  "over_by": null,
  "items": []
}
```

### Rules

- Unknown price is never treated as zero.
- A basket with unknown prices is never reported `WITHIN_BUDGET` merely because known items are below budget.
- Blank budget from frontend must deserialize to `null`, not zero.

---

## 5.19 What Fits My Budget

### Service

```text
BudgetFitService
```

### Endpoint

```text
GET /api/plans/:id/budget-fit/
```

### Preconditions

If `budget is null`, return a successful structured state such as:

```json
{
  "available": false,
  "reason": "NO_BUDGET",
  "items": []
}
```

### Item result states

```text
FIT
NOT_FIT
UNKNOWN
```

No `PARTIAL` state exists in MVP.

### Deterministic algorithm

1. Split plan items into MUST_HAVE and OPTIONAL.
2. Within each group, sort by `sort_order`, then ID as tie-breaker.
3. Concatenate MUST_HAVE first, OPTIONAL second.
4. Set `remaining = budget`.
5. For each item:
   - if selected-store price unknown → `UNKNOWN`, do not change remaining;
   - else calculate full planned line total;
   - if line total `<= remaining` → `FIT`, subtract line total;
   - else → `NOT_FIT`, do not subtract.
6. Return totals and flags.

### Summary fields

```text
budget
affordable_known_total
remaining
must_have_known_total
must_have_exceeds_budget
unknown_item_count
```

### Important rule

The service does not solve a knapsack/max-item optimization problem. Order/priority are the shopper's explicit preference model.

---

## 5.20 Dashboard Aggregation

### Endpoint

```text
GET /api/dashboard/
```

### Service

```text
DashboardService
```

### Response should include

- current user summary;
- most recently updated ACTIVE plan + authoritative estimate summary;
- most recent COMPLETED shopping session;
- frequent product suggestions;
- current-month spending;
- previous-month spending.

### Monthly spending rule

```text
SUM(ShoppingSession.receipt_total)
WHERE status = COMPLETED
AND purchase_date in month
```

Use receipt total, not reconstructed item subtotal.

Current and previous month are calendar months determined from today's date in `Asia/Manila`.

### Performance

Avoid N+1 behavior. Use select/prefetch/annotations appropriately.

---

## 5.21 Search & Filtering

Server-side filtering is required for growing datasets.

Examples:

```text
GET /api/products/?search=milk&category=DAIRY_EGGS
GET /api/shopping-sessions/?status=COMPLETED&store_id=s1&date_from=2026-09-01
GET /api/plans/?status=ACTIVE
```

### Rules

- Validate owned filter foreign keys such as store IDs.
- Invalid filter values return clear 400 where ambiguity could hide errors.
- Stable ordering is defined for pagination.

---

## 5.22 Empty Data Behavior

Empty account/data is normal.

Return successful empty collections:

```json
{
  "count": 0,
  "results": []
}
```

Suggestions with insufficient data:

```json
{
  "recent_session_count": 0,
  "suggestions": []
}
```

Dashboard may contain `null` active plan/recent session.

Do not use 404 simply because a collection is empty.

---

# 6. Recommended Service Layer

```text
CreateShoppingSessionService
UpdateShoppingSessionService
CompleteShoppingSessionService
PriceEstimationService
CreatePlanFromSessionService
ShoppingSuggestionService
PlanEstimationService
BudgetCalculationService
BudgetFitService
DashboardService
```

### Dependency direction

```text
API/View
  ↓
Serializer / Input Validation
  ↓
Domain Service
  ↓
ORM / PostgreSQL
```

Example:

```text
PlanEstimationService
  ├── PriceEstimationService
  └── BudgetCalculationService
```

Keep non-trivial rules out of views and avoid duplicating algorithms in serializers/frontend.

---

# 7. Transaction & Concurrency Requirements

## Shopping session writes

Creating/updating/completing a session with items must be atomic.

## Reorder

Plan item reorder should be atomic.

## Duplicate constraints

Database uniqueness constraints are the final defense against concurrent duplicate product rows.

Handle IntegrityError and convert it to clean API conflict/validation responses.

## Completion

Use appropriate transaction/locking if concurrent completion requests could otherwise cause inconsistent state.

---

# 8. Backend User Stories

## BE-US-001 — Register and authenticate shoppers securely

**Priority:** P0  
**Story:** As the system, I need secure account lifecycle handling so private grocery data belongs to the correct user.

**Acceptance criteria:**

- Unique email registration.
- Django password hashing.
- Login/logout/current-user endpoints.
- Password reset/change supported.
- Email and password changes require the current password.
- Password never serialized.

---

## BE-US-002 — Isolate every user's data

**Priority:** P0  
**Story:** As a shopper, I need confidence that another user cannot access my stores, products, sessions, or plans.

**Acceptance criteria:**

- Every domain lookup is ownership-scoped.
- Foreign-key IDs are ownership-validated.
- Guessed foreign IDs cannot leak existence.

---

## BE-US-003 — Manage active and archived stores

**Priority:** P0  
**Story:** As a shopper, I want reusable store branches with reversible archiving.

**Acceptance criteria:**

- CRUD/edit, archive, restore.
- Archived stores stay referenced historically.
- Active selector query excludes archived by default.

---

## BE-US-004 — Maintain a normalized personal product catalog

**Priority:** P0  
**Story:** As a shopper, I want repeated purchases tied to the same product identity.

**Acceptance criteria:**

- Name normalization is deterministic.
- Unique normalized name per user.
- Search/category filters supported.
- No fuzzy auto-merge.

---

## BE-US-005 — Save incomplete shopping-session drafts

**Priority:** P0  
**Story:** As a shopper, I want to save partial manual receipt entry safely.

**Acceptance criteria:**

- Draft may omit completion-required fields.
- Persisted item rows are still structurally valid.
- Drafts do not affect price history, suggestions, or spending.

---

## BE-US-006 — Complete a shopping session atomically

**Priority:** P0  
**Story:** As a shopper, I want a valid manual receipt saved as authoritative shopping history.

**Acceptance criteria:**

- Store/date/receipt total/items required.
- Quantity/unit price validated.
- Backend calculates line totals.
- Transaction writes session/items atomically.
- `completed_at` set.

---

## BE-US-007 — Allow receipt total and item subtotal to differ

**Priority:** P0  
**Story:** As a shopper, I want real receipts saved even when discounts or fees cause a mismatch.

**Acceptance criteria:**

- Difference is computed and returned.
- Non-zero difference does not block completion.

---

## BE-US-008 — Correct a completed shopping session safely

**Priority:** P0  
**Story:** As a shopper, I want manual-entry mistakes corrected without creating duplicate history.

**Acceptance criteria:**

- PATCH can update completed session and item set.
- Full completed-state validation remains enforced.
- Operation is atomic.
- Future derived prices/suggestions use corrected data automatically.

---

## BE-US-009 — Separate drafts from completed shopping history

**Priority:** P0  
**Story:** As a shopper, I want unfinished entries separated from real purchase history.

**Acceptance criteria:**

- Default history returns completed sessions.
- `status=DRAFT` returns drafts ordered by update time.
- Both queries paginate.

---

## BE-US-010 — Derive complete product price history

**Priority:** P0  
**Story:** As a shopper, I want to see what I actually paid over time.

**Acceptance criteria:**

- Completed PurchaseItems only.
- Store/date filters work.
- Corrections immediately affect query results.

---

## BE-US-011 — Resolve the latest price at an exact store

**Priority:** P0  
**Story:** As a planner, I need a deterministic latest price for a product/store pair.

**Acceptance criteria:**

- Exact store only.
- Deterministic ordering/tie-breaker.
- Missing price returns `None`, never zero/fallback.

---

## BE-US-012 — Create and manage shopping plans

**Priority:** P0  
**Story:** As a shopper, I want persistent future shopping plans.

**Acceptance criteria:**

- Store required.
- Budget nullable.
- New plan ACTIVE.
- Status filters supported.
- Plan deletion affects only plan/items.

---

## BE-US-013 — Enforce plan lifecycle transitions

**Priority:** P0  
**Story:** As a shopper, I want predictable Archive, Complete, Reactivate behavior.

**Acceptance criteria:**

- Only valid transitions accepted.
- Complete sets completed_at.
- Reactivate clears completion timestamp when needed.
- Completion never creates ShoppingSession.

---

## BE-US-014 — Add/update/remove/reorder unique plan items

**Priority:** P0  
**Story:** As a shopper, I want a deterministic plan basket with priorities and order.

**Acceptance criteria:**

- Quantity > 0.
- Product owned.
- One row per product.
- Duplicate add returns conflict with existing item ID.
- Reorder persists atomically.

---

## BE-US-015 — Create a plan from completed shopping history

**Priority:** P0  
**Story:** As a shopper, I want a previous basket to become a new editable plan.

**Acceptance criteria:**

- Completed source only.
- Copy products/quantities.
- Default source store.
- Do not copy historical prices as fixed estimates.
- Source history remains unchanged.

---

## BE-US-016 — Generate explainable frequent-product suggestions

**Priority:** P0  
**Story:** As a shopper, I want useful suggestions derived from my recent completed trips.

**Acceptance criteria:**

- Last four completed sessions.
- At least two-session frequency threshold.
- Deterministic ranking.
- Optional plan exclusion.
- Human-readable reason returned.

---

## BE-US-017 — Estimate a plan using store-specific history

**Priority:** P0  
**Story:** As a shopper, I want each planned item's estimated cost based on my latest purchase at that store.

**Acceptance criteria:**

- Known item returns unit price, line total, source.
- Unknown item returns null price/line/source.
- Known total excludes unknown items.
- Estimate completeness returned.

---

## BE-US-018 — Calculate all four budget states correctly

**Priority:** P0  
**Story:** As a shopper, I want budget status that never hides uncertainty.

**Acceptance criteria:**

- Null budget → NO_BUDGET.
- Any unknown with budget → INCOMPLETE_ESTIMATE.
- Complete <= budget → WITHIN_BUDGET.
- Complete > budget → OVER_BUDGET.
- `known_total_exceeds_budget` returned when budget exists.

---

## BE-US-019 — Determine what full planned quantities fit

**Priority:** P0  
**Story:** As a shopper, I want deterministic FIT/NOT_FIT/UNKNOWN results using my priorities and order.

**Acceptance criteria:**

- Requires budget or returns NO_BUDGET availability state.
- Must-have processed before optional.
- Sort order respected.
- Only FIT/NOT_FIT/UNKNOWN returned.
- No partial quantity optimization.
- Unknown price never deducts budget.

---

## BE-US-020 — Re-estimate after store switching

**Priority:** P0  
**Story:** As a shopper, I want a plan's estimates to reflect its newly selected store.

**Acceptance criteria:**

- When PATCH sets or changes `store_id`, it validates that the store is owned and ACTIVE. A PATCH that leaves `store_id` unchanged is not rejected because the existing store has since been archived (see §4.2).
- Next estimate uses only new store history.
- Purchase history remains untouched.

---

## BE-US-021 — Return dashboard aggregates efficiently

**Priority:** P0  
**Story:** As a shopper, I want a useful dashboard without many client-side joins.

**Acceptance criteria:**

- Most recently updated active plan + estimate.
- Latest completed session.
- Frequent products.
- Current/previous month spending.
- Empty states represented with null/empty collections.

---

## BE-US-022 — Support server-side search, filtering, and pagination

**Priority:** P0  
**Story:** As the dataset grows, I want list screens to stay efficient.

**Acceptance criteria:**

- Product search/category.
- Session status/store/date range.
- Plan status/store.
- Stable pagination ordering.

---

## BE-US-023 — Preserve monetary/data integrity

**Priority:** P0  
**Story:** As the system owner, I want database constraints to prevent invalid state even if client validation is bypassed.

**Acceptance criteria:**

- Decimal types for money.
- Check/service validation for non-negative money and positive quantities.
- Unique product rows per session/plan.
- Transactional multi-row writes.

---

## BE-US-024 — Return consistent actionable errors

**Priority:** P0  
**Story:** As a frontend developer, I want predictable errors that can map to forms and interactions.

**Acceptance criteria:**

- Standard error envelope.
- Duplicate/conflict errors include stable code.
- Production 500 hides internals.

---

## BE-US-025 — Treat empty accounts as valid state

**Priority:** P0  
**Story:** As a new shopper, I want the API to return usable empty data rather than errors.

**Acceptance criteria:**

- Empty stores/products/sessions/plans return successful empty collections.
- Dashboard supports null recent/active records.
- Suggestions return empty list with session count.

---

# 9. Canonical API Surface

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register/` | Register |
| POST | `/api/auth/login/` | Login |
| POST | `/api/auth/logout/` | Logout |
| POST | `/api/auth/password-reset/` | Start reset |
| POST | `/api/auth/password-reset/confirm/` | Confirm reset |
| POST | `/api/auth/password-change/` | Change password |
| GET/PATCH | `/api/me/` | Current profile |
| GET/POST | `/api/stores/` | List/create stores |
| GET/PATCH | `/api/stores/:id/` | Store detail/edit |
| POST | `/api/stores/:id/archive/` | Archive store |
| POST | `/api/stores/:id/restore/` | Restore store |
| GET/POST | `/api/products/` | List/create products |
| GET/PATCH | `/api/products/:id/` | Product detail/edit |
| GET | `/api/products/:id/price-history/` | Product price history |
| GET/POST | `/api/shopping-sessions/` | List/create session |
| GET/PATCH | `/api/shopping-sessions/:id/` | Detail/correct session |
| POST | `/api/shopping-sessions/:id/complete/` | Complete draft |
| DELETE | `/api/shopping-sessions/:id/` | Discard draft only |
| GET/POST | `/api/plans/` | List/create plans |
| GET/PATCH/DELETE | `/api/plans/:id/` | Plan detail/update/delete |
| POST | `/api/plans/:id/archive/` | Archive |
| POST | `/api/plans/:id/reactivate/` | Reactivate |
| POST | `/api/plans/:id/complete/` | Complete |
| POST | `/api/plans/from-session/:id/` | Create from history |
| POST | `/api/plans/:id/items/` | Add item |
| PATCH/DELETE | `/api/plans/:id/items/:itemId/` | Update/remove item |
| POST | `/api/plans/:id/items/reorder/` | Reorder |
| GET | `/api/plans/:id/estimate/` | Estimate/budget summary |
| GET | `/api/plans/:id/budget-fit/` | What Fits calculation |
| GET | `/api/suggestions/products/` | Frequent products |
| GET | `/api/dashboard/` | Dashboard aggregate |

No plan-duplicate endpoint exists in MVP.

---

# 10. Automated Testing Requirements

## Authentication & authorization

- Registration uniqueness.
- Login/logout.
- Email change and password change reject a missing or incorrect current password and leave the account unchanged; display-name-only profile updates need no password.
- User A cannot access User B store/product/session/plan/item.
- Foreign-key injection blocked.

## Stores/products

- Archive/restore.
- Archived store rejected for new session/plan, draft completion, and store change; existing references kept.
- Product normalized-name uniqueness.
- Search/category filters.

## Shopping sessions

- Save incomplete draft.
- Complete valid draft.
- Reject invalid completed session.
- Atomic session/items write.
- Authoritative line totals, rounded half-up to 2 decimal places.
- Receipt mismatch allowed.
- Unique product per session.
- Correct completed session.
- Draft deletion allowed.
- Completed deletion rejected.

## Price history

- Draft excluded.
- Completed included.
- Latest exact-store price selected.
- Tie-breaker deterministic.
- Missing store returns None.
- Correction affects history.

## Plans

- Store required.
- Null budget accepted.
- Product uniqueness.
- Item reorder.
- Create from completed session.
- Reject create-from-draft.
- Archive/complete/reactivate transitions.
- Delete plan does not affect history.

## Estimation

- Correct line estimate.
- Unknown returns null.
- Known total excludes unknown.
- Estimate completeness.
- Store switching changes source.

## Budget

- NO_BUDGET.
- WITHIN_BUDGET.
- OVER_BUDGET.
- INCOMPLETE_ESTIMATE.
- Incomplete + known total already over budget.

## Budget fit

- Must-have before optional.
- Sort order respected.
- FIT/NOT_FIT/UNKNOWN only.
- Unknown does not deduct.
- No partial result.
- No-budget availability response.

## Suggestions

- Last four completed sessions only.
- Two-session threshold.
- Deterministic ranking.
- Exclude already planned product with plan_id.

## Dashboard

- Latest active plan selection.
- Latest completed session.
- Current/previous month receipt-total sums, with month boundaries in `Asia/Manila`.
- Empty user response.

---

# 11. Performance Expectations

### Avoid N+1

Use `select_related`, `prefetch_related`, annotations, and bounded queries.

Particularly review:

- history list item counts;
- product list summary fields;
- plan detail + products;
- plan estimate price lookups;
- dashboard aggregate.

### Latest-price optimization

MVP can query PurchaseItem history directly with appropriate indexes. If usage grows, consider materialized/latest-price tables later; do not prematurely duplicate price state.

### Target

Typical non-heavy API requests should aim for p95 around `< 500 ms` under normal MVP conditions.

---

# 12. Security Requirements

- HTTPS production.
- Secure auth cookie/token handling.
- CSRF protection when cookie auth used.
- Restrictive CORS configuration.
- Ownership filtering on every private endpoint.
- No secrets in source.
- Rate limiting considered for auth endpoints.
- Password reset tokens follow Django security primitives.
- Logs avoid raw passwords/tokens and unnecessary sensitive payloads.
- Validation prevents mass assignment of `user_id`, `status` fields that should be server-controlled, and foreign ownership.

---

# 13. Backend Definition of Done

Backend MVP is done when:

- authentication and user profile work securely;
- store archive/restore and product normalized uniqueness work;
- session drafts can be incomplete without polluting historical calculations;
- completed sessions validate and persist atomically;
- completed sessions can be corrected but not hard-deleted in MVP;
- shopping history is filtered/paginated;
- price history and exact-store latest price are deterministic;
- plans use ACTIVE/COMPLETED/ARCHIVED lifecycle with archive/reactivate/complete/delete;
- no plan duplication API exists;
- plan items are unique per product and reorderable;
- plans can be created from completed sessions;
- suggestions use last four completed sessions and are explainable;
- plan estimation returns null unknown prices and traceable known price sources;
- budget calculation supports NO_BUDGET / WITHIN_BUDGET / OVER_BUDGET / INCOMPLETE_ESTIMATE;
- budget fit returns only FIT / NOT_FIT / UNKNOWN and performs no partial optimization;
- dashboard aggregates are efficient and correct;
- API errors are consistent;
- money uses Decimal/NUMERIC;
- authorization tests prove cross-user isolation;
- automated tests cover the critical rules above;
- behavior is aligned with `GROCEREASE.md` and `FRONTEND.md`.
