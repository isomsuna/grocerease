# GrocerEase — MVP Product Specification

**Status:** Canonical MVP source of truth  
**Stack:** React + Django REST Framework + PostgreSQL  
**Prototype reference:** `GrocerEase.html` informs the interaction and visual direction, but this document and the aligned `FRONTEND.md` / `BACKEND.md` take precedence when there is a conflict.

---

## 1. Product Overview

**GrocerEase** is a personalized grocery shopping planner and budget tracker. It helps a shopper manually record completed grocery trips, build a private history of products and prices paid at specific stores, and reuse that history to plan future shopping trips against a budget.

For the MVP, receipt information is entered **manually**. There is no receipt upload, OCR, barcode scanning, live retailer pricing, or automatic extraction.

### Core product loop

**Enter receipt manually → Save shopping session → Build product and price history → Create shopping plan → Select store → Set budget → Estimate basket → Adjust plan → Shop → Record the next receipt**

### Core product promise

> **GrocerEase remembers what you bought and what you paid, so planning your next grocery trip is easier and more budget-aware.**

### MVP hypothesis

The MVP succeeds if shoppers are willing to record purchases because the resulting history makes their next grocery-planning and budgeting session meaningfully easier.

---

## 2. Source-of-Truth Hierarchy

The project uses three aligned specifications:

1. **`GROCEREASE.md`** — product scope, terminology, shared rules, user flows, and release criteria.
2. **`FRONTEND.md`** — React implementation contract, screens, interactions, responsive behavior, and frontend user stories.
3. **`BACKEND.md`** — Django/PostgreSQL implementation contract, models, APIs, business rules, services, and backend user stories.

`GrocerEase.html` is a prototype/design reference. Good prototype decisions have been incorporated into these specifications, but the markdown documents are authoritative.

---

## 3. Canonical Product Vocabulary

Use these terms consistently in UI, code, APIs, and documentation.

| Term | Meaning |
|---|---|
| **Shopping Session** | A past grocery purchase manually entered from a physical receipt. May be a draft or completed. |
| **Purchase Item** | One unique product row inside a shopping session. |
| **Shopping Plan** | A future intended grocery trip. |
| **Plan Item** | One unique product row inside a shopping plan. |
| **Store** | A user-created retailer branch/location. Different branches may have different price histories. |
| **Product** | A user-owned reusable grocery catalog item. |
| **Known Estimated Total** | Sum of plan items that have a historical price at the selected store. Unknown items are excluded, never treated as zero. |
| **Price History** | Historical unit-price observations derived from completed shopping sessions. |
| **Must-have** | A plan item considered before optional items in budget-fit calculations. |
| **Optional** | A plan item considered after must-have items in budget-fit calculations. |

### Important product principle

GrocerEase provides a **personalized estimate from the shopper's own historical purchases**, not a guarantee of current shelf price or inventory.

---

## 4. Technology Stack

### Frontend

- React
- TypeScript recommended
- Responsive web application
- REST API integration
- React Router recommended
- TanStack Query recommended for server state

### Backend

- Django
- Django REST Framework
- Django authentication
- Service-layer business logic

### Database

- PostgreSQL
- `NUMERIC` / Django `DecimalField` for money
- Timezone-aware timestamps

---

## 5. Canonical Routes

The shorter route structure used by the prototype is adopted as the MVP convention.

### Public/authentication routes

```text
/login
/register
/forgot-password
/reset-password
```

### Authenticated application routes

```text
/
/sessions/new
/sessions/:sessionId/edit
/history
/history/:sessionId
/plans
/plans/new
/plans/:planId
/products
/products/:productId
/stores
/settings
```

### Route semantics

- `/` — dashboard.
- `/sessions/new` — manually enter a receipt/shopping session.
- `/sessions/:sessionId/edit` — continue a draft or explicitly correct an existing session.
- `/history` — completed shopping history, with access to drafts through a dedicated tab/filter.
- `/history/:sessionId` — shopping-session details.
- `/plans` — active/completed/archived shopping plans.
- `/plans/new` — start a plan from empty, previous session, or frequent products.
- `/plans/:planId` — primary shopping planner.

---

## 6. MVP Scope Summary

A complete MVP user journey is:

1. User registers and logs in.
2. User creates a store, either from Store Management or inline during a workflow.
3. User manually enters a physical receipt as a shopping session.
4. User reuses existing products or creates products inline.
5. User saves the entry as a draft or completes the shopping session.
6. Completed purchases become shopping history and historical price observations.
7. User creates a shopping plan from an empty list, previous session, or frequent products.
8. User selects a store and optionally sets a budget.
9. GrocerEase estimates each plan item from the latest known price for that product at that exact store.
10. Unknown prices are clearly identified.
11. User changes quantities, priorities, ordering, store, planned date, and budget.
12. GrocerEase shows whether the estimate is within budget, over budget, incomplete, or has no budget.
13. User can open **What fits my budget?** to see which full planned item quantities fit deterministically.
14. User completes, archives, reactivates, or deletes the shopping plan as appropriate.
15. After shopping, the user records the actual receipt as a new shopping session, continuing the loop.

---

## 7. MVP Product Decisions

| Decision | Canonical MVP behavior |
|---|---|
| Account model | One account represents one shopper. Household collaboration is deferred. |
| Receipt capture | Manual entry only. No image upload or OCR. |
| Session statuses | `DRAFT`, `COMPLETED`. |
| Plan statuses | `ACTIVE`, `COMPLETED`, `ARCHIVED`. New plans start `ACTIVE`. |
| Store requirement for plan | Required when a plan is created so estimates have a target context. |
| Budget | Optional. Blank means **no budget**, not zero. |
| Currency | One preferred display currency per user. No currency conversion in MVP. |
| Price source | User's own completed purchase history. |
| Store estimate | Latest known unit price for the product at the selected store. |
| Unknown price | `null` / unknown, never zero. |
| Price prediction | None. No forecasting or machine learning. |
| Product duplication | One product row per shopping session and per plan. Duplicate add attempts reuse/focus the existing row. |
| Suggestions | Rules-based from recent completed sessions; explainable, not described as AI. |
| Budget fit | Whole planned quantities only. No partial-quantity optimization in MVP. |
| Plan duplication | Deferred; not required for MVP. |
| Completed session deletion | Not in MVP. Completed sessions can be explicitly corrected. Draft sessions may be discarded. |
| Live retailer pricing | Not in MVP. |
| Inventory availability | Not in MVP. |

---

# 8. Feature Specifications

## 8.1 Authentication & Shopper Profile

### Purpose

Keep each shopper's stores, products, purchase history, plans, and budgets private.

### Required capabilities

- Registration
- Login
- Logout
- Forgot/reset password
- Profile editing
- Preferred currency
- Password change

### Business rules

- Email is the MVP login identifier and must be unique.
- Every user-owned resource is scoped to the authenticated user.
- Client-supplied ownership IDs are never trusted.
- Changing display currency changes formatting only; historical stored money values are not converted.

### Success criteria

- New user can register and enter the application.
- Returning user can log in and resume persisted data.
- Session expiration routes the user back through authentication cleanly.
- User A cannot retrieve, modify, or infer the existence of User B resources by changing IDs.

---

## 8.2 Application Shell & Navigation

### Desktop

- Persistent left sidebar.
- GrocerEase logo/brand.
- Prominent **+ Add Shopping Session** action.
- Navigation: Dashboard, Shopping Plans, Shopping History, Products, Stores, Settings.
- Current-user/profile access at the bottom of the sidebar.

### Mobile

- Compact header.
- Bottom navigation for the primary destinations.
- Touch-friendly controls and safe-area spacing.
- Planner budget summary may become sticky.

### Success criteria

- Primary sections are reachable in one navigation action.
- Current route is visually identifiable.
- Application remains usable at common mobile widths.

---

## 8.3 Dashboard

### Purpose

Help the shopper decide what to do next rather than becoming an analytics-heavy page.

### Required sections

1. **Primary quick actions**
   - Add Shopping Session
   - Create Shopping Plan
2. **Secondary quick action**
   - Check a Price → Products
3. **Active shopping plan**
   - Most recently updated `ACTIVE` plan
   - Store, budget, known estimated total, remaining/over amount, item count, unknown count, status
4. **Recent completed shopping session**
5. **Frequently purchased products**
6. **Lightweight monthly spending summary**
   - Current month
   - Previous month

### Success criteria

- Empty account has a useful first-action state.
- Active plan summary matches authoritative backend estimate.
- Monthly spending comes only from completed shopping sessions.

---

## 8.4 Store Management

### Store fields

- Name
- Branch/location label
- Notes
- Status: `ACTIVE` or `ARCHIVED`

### Required behaviors

- Add store.
- Edit store.
- Archive store.
- Restore archived store.
- Create a store inline from a Store Selector during shopping-session entry or planning.

### Rules

- Different branches can be represented separately.
- Archived stores remain attached to historical data.
- Archived stores do not appear in normal new-session/new-plan selectors unless explicitly restored.

### Success criteria

- Store creation never forces the shopper to abandon the current receipt or planning workflow.
- Store-specific price history remains branch-specific.

---

## 8.5 Personal Product Catalog

### Product fields

- Name
- Category
- Optional unit label/default unit
- Active/deactivated state

### MVP categories

```text
Pantry
Dairy & Eggs
Meat & Seafood
Produce
Bakery
Beverages
Household
Personal Care
Frozen
Snacks
Other
```

### Required behaviors

- Search product catalog.
- Filter by category.
- Create and edit products.
- Reuse products in sessions and plans.
- Product autocomplete in manual entry and planner.
- Inline product creation during shopping-session entry.

### Duplicate policy

- Exact product names are unique per user using normalized case/whitespace comparison.
- Fuzzy or semantic auto-merging is not part of MVP.
- If a duplicate product is selected within the same session or plan, the existing row is reused rather than creating a second row.

### Product details

Show:

- Category
- Purchase count
- Last purchased date
- Latest paid price and store
- Chronological price history
- Lightweight historical price chart after enough observations exist

### Success criteria

- Product history remains connected to one reusable product identity.
- Chart/list never implies price forecasting.

---

## 8.6 Manual Shopping Session Entry

### Purpose

Turn a physical receipt into structured purchase history without OCR.

### Routes

```text
/sessions/new
/sessions/:sessionId/edit
```

### Session fields

- Store
- Purchase date
- Receipt total
- Optional notes

### Purchase item fields

- Product
- Quantity
- Unit price
- Line total, authoritative formula: `quantity × unit_price`

### Required interactions

- Add item row.
- Remove item row.
- Product autocomplete.
- Create product inline.
- Create store inline.
- Quantity and currency controls.
- Automatic line-total preview.
- Running items subtotal.
- Receipt total.
- Difference indicator.
- Save Draft.
- Save Shopping Session.

### Draft rules

A draft may be incomplete. Store, purchase date, receipt total, or items may still be missing.

Drafts:

- do not contribute to price history;
- do not contribute to spending summaries;
- do not generate suggestions;
- can be continued at `/sessions/:sessionId/edit`;
- may be discarded.

### Completion rules

To complete a shopping session:

- store is required;
- purchase date is required;
- receipt total must be `>= 0`;
- at least one purchase item is required;
- each quantity must be `> 0`;
- each unit price must be `>= 0`;
- each product appears at most once in the session.

### Receipt-total mismatch

The item subtotal does **not** need to equal the receipt total.

Show:

```text
Items subtotal: ₱1,245.00
Receipt total:  ₱1,220.00
Difference:        ₱25.00 not itemized
```

The mismatch is a warning, not a blocker, because discounts, coupons, tax, fees, rounding, or omitted receipt lines may explain it.

### Correction behavior

Completed sessions may be explicitly edited through the manual-entry screen. Corrections replace the relevant persisted values and automatically affect future derived price-history and recommendation queries.

### Success criteria

- A user can manually enter a normal grocery receipt without leaving the workflow.
- Drafts are safe and do not pollute historical calculations.
- Completed-session totals are calculated authoritatively by the backend.
- Mismatched receipt totals can still be saved.

---

## 8.7 Shopping History

### Routes

```text
/history
/history/:sessionId
```

### History list

Default view shows completed sessions newest first.

Each card/row shows:

- Purchase date
- Store/branch
- Item count
- Receipt total
- Status where relevant

### Draft access

Provide a separate **Drafts** tab/filter. Draft cards use **Continue draft** and link to `/sessions/:id/edit`.

### Filters

- Store
- Date range
- Status/tab

### Pagination

History uses server-side pagination. UI may use numbered pagination or a **Load more** pattern.

### Session details

Show:

- Store
- Purchase date
- Receipt total
- Items subtotal
- Difference if meaningful
- Purchased products
- Quantities
- Unit prices
- Line totals

Primary completed-session action:

**Use for Next Shopping Plan**

Secondary correction action:

**Edit Shopping Session**

### Success criteria

- Completed history is clearly separate from unfinished drafts.
- Copying a session into a plan never mutates the historical session.

---

## 8.8 Personal Price History

### Price source

Historical prices are derived from completed `PurchaseItem` records plus their parent `ShoppingSession` store/date.

### Latest-price rule

For a given user, product, and store:

> **Estimated unit price = unit price from the most recent completed shopping session containing that product at that exact store.**

Order by purchase date descending, with completion/creation time as deterministic tie-breaker.

### Missing store price

If there is no historical price at the selected store:

- estimated unit price = unknown/null;
- estimated line total = unknown/null;
- the item is excluded from known estimated total;
- UI says **No price history at this store**.

The UI may show supporting context such as the latest price at another store, but it must never silently use that other-store price in the selected-store estimate.

### Success criteria

- Every displayed estimate has a traceable historical source.
- Correcting a completed shopping session automatically changes future derived estimates where applicable.

---

## 8.9 Shopping Plans

### Routes

```text
/plans
/plans/new
/plans/:planId
```

### Plan creation modes

1. **Start Empty**
2. **Use Previous Shopping Session**
3. **Add From Frequent Products**

### Plan fields

- Name; blank becomes `Untitled plan`
- Target store; required at creation
- Planned date; optional
- Budget; optional
- Status: `ACTIVE`, `COMPLETED`, `ARCHIVED`

### Plan item fields

- Product
- Quantity
- Priority: `MUST_HAVE` / `OPTIONAL`
- Sort order

Historical estimated price is derived, not manually stored on the plan item.

### Plan list

Group or filter by:

- Active
- Completed
- Archived

Cards show:

- Name
- Store
- Planned date
- Budget if set
- Known estimated total
- Item count
- Unknown-price count
- Budget status

### Lifecycle actions

- Active → Archive
- Active → Complete, with confirmation
- Completed/Archived → Reactivate
- Delete plan, with confirmation

Deleting a shopping plan never deletes shopping history.

### Deferred

Plan duplication is not required for MVP.

### Success criteria

- Plans remain independent from their source history.
- Plan lifecycle state is clear and reversible through reactivation, except deletion.

---

## 8.10 Create Plan From Previous Session

### Behavior

When the user chooses **Use for Next Shopping Plan**:

- create a new plan;
- copy product references and quantities;
- default target store to the session store;
- copy no historical prices as current prices;
- allow the user to change store before or after creation;
- calculate estimates using the normal latest-price rule.

### Success criteria

- Source shopping session remains unchanged.
- New plan is fully editable.

---

## 8.11 Personalized Shopping Suggestions

### Purpose

Provide useful personalization without machine learning.

### Default MVP algorithm

Use the user's last four **completed** shopping sessions.

For each product:

- count distinct recent sessions containing it;
- suggest products appearing in at least two of the recent sessions;
- rank by frequency descending, then most recent purchase, then product name.

Example explanation:

> **Bought in 3 of your last 4 trips**

Suggestions should exclude products already in the plan.

### Success criteria

- Suggestions are deterministic and explainable.
- Users with insufficient history receive a useful empty state.

---

## 8.12 Shopping Planner

### Primary planner responsibilities

The planner is the main GrocerEase working screen.

The user can:

- edit plan name;
- change store;
- set/change planned date;
- set/remove budget;
- add products;
- change quantity;
- change priority;
- reorder items;
- remove items;
- view price source;
- view suggestions;
- open **What fits my budget?**;
- archive, complete, reactivate, or delete the plan.

### Desktop layout

Recommended:

- Main planner column with plan fields and items.
- Contextual side column containing Budget Summary and Suggested From Your History.

### Mobile layout

- Cards instead of wide item tables.
- Sticky compact budget summary.
- Large quantity controls.
- Touch-friendly priority and remove controls.
- Planner tabs such as **Items** and **What fits my budget**.

### Success criteria

- Common edits feel immediate.
- Server response remains authoritative.
- Failed mutations do not silently discard local user input.

---

## 8.13 Store-Specific Plan Estimation

For every plan item:

```text
estimated_unit_price = latest known price(product, selected store)
estimated_line_total = quantity × estimated_unit_price
```

When price is unknown:

```text
estimated_unit_price = null
estimated_line_total = null
```

Aggregate:

```text
known_total = sum(known estimated line totals)
unknown_item_count = number of items with unknown price
estimate_complete = unknown_item_count == 0
```

### Store switching

Changing the selected store:

- persists the new store;
- recalculates all price sources and line estimates;
- recalculates unknown count and budget state;
- never alters purchase history.

### Success criteria

- Store switching can change both prices and which items are unknown.
- No cross-store price is silently substituted.

---

## 8.14 Budget Tracking

### Budget is optional

A blank budget means **no budget has been set**. It is not equivalent to `₱0`.

### Canonical budget status values

```text
NO_BUDGET
WITHIN_BUDGET
OVER_BUDGET
INCOMPLETE_ESTIMATE
```

### Status rules

1. If no budget is set → `NO_BUDGET`.
2. Else if one or more plan items have unknown prices → `INCOMPLETE_ESTIMATE`.
3. Else if known total `<= budget` → `WITHIN_BUDGET`.
4. Else → `OVER_BUDGET`.

For incomplete estimates, also return:

```text
known_total_exceeds_budget = known_total > budget
```

This allows the UI to say:

> **Incomplete estimate**  
> Known items are already ₱250 over budget.  
> 2 additional items have unknown prices.

### Recalculation triggers

- Budget changes
- Product added/removed
- Quantity changes
- Store changes
- Historical data correction that changes the latest applicable price

### Success criteria

- Unknown items never make a basket look falsely within budget.
- No-budget plans never appear over budget simply because the budget input is blank.

---

## 8.15 “What Fits My Budget?”

### Purpose

Give a deterministic view of which **full planned quantities** can fit inside the plan budget.

### Preconditions

- A budget must be set.
- Plan may contain known and unknown prices.

### MVP algorithm

1. Take all `MUST_HAVE` items in plan sort order.
2. Then take all `OPTIONAL` items in plan sort order.
3. For an unknown-price item, return `UNKNOWN`; do not deduct budget.
4. For a known-price item, if the entire planned line total fits in the remaining budget, return `FIT` and deduct it.
5. Otherwise return `NOT_FIT`.

MVP result states:

```text
FIT
NOT_FIT
UNKNOWN
```

### No partial optimization

GrocerEase does not calculate “2 out of 3 units fit” in MVP. The planned quantity is considered as one decision unit. Users can manually reduce quantity and recalculate.

### Must-have warning

Return `must_have_exceeds_budget = true` when the known total of all must-have items is greater than the budget.

### UX example

```text
Budget: ₱1,000

✓ Rice      ₱500  Must-have
✓ Milk      ₱100  Must-have
✓ Eggs      ₱120  Optional
✓ Bread      ₱90  Optional
✕ Coffee    ₱250  Optional
? Shampoo      —  Optional

Affordable known basket: ₱810
Remaining: ₱190
```

### Success criteria

- Same inputs always produce the same result.
- Reordering optional items predictably changes which optional items fit.
- Unknown items are never guessed.

---

## 8.16 Plan Completion

Completing a plan means the shopper is done using that planning record.

### Rules

- UI asks for confirmation.
- Status changes to `COMPLETED`.
- Completion does **not** create purchase history.
- Actual historical prices are created only from a manually entered completed shopping session.
- After completion, UI should encourage **Add Shopping Session**.
- Completed plan can be reactivated if the shopper wants to reuse it.

### Success criteria

- Plan completion cannot accidentally create estimated prices as actual purchases.

---

## 8.17 Settings

### Profile

- Display name
- Email

### Preferences

- Preferred currency

### Account

- Change password
- Log out

### Success criteria

- Currency formatting updates consistently throughout the UI.
- Changing currency does not convert historical values.

---

# 9. Shared Data Model Overview

```text
User
 ├── UserPreference
 ├── Store
 ├── Product
 ├── ShoppingSession
 │    └── PurchaseItem
 └── ShoppingPlan
      └── ShoppingPlanItem
```

### Key ownership rule

Every top-level domain object belongs to one user, directly or through an ownership-safe parent.

### Key uniqueness rules

- User email unique.
- Product normalized name unique per user.
- One product per ShoppingSession.
- One product per ShoppingPlan.

### Money

Use decimal-safe types throughout persistence and backend calculations.

Recommended:

```text
receipt_total NUMERIC(12,2)
unit_price    NUMERIC(12,2)
line_total    NUMERIC(12,2)
budget        NUMERIC(12,2)
quantity      NUMERIC(10,3)
```

---

# 10. Canonical API Surface Summary

Detailed contracts live in `BACKEND.md`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/register/` | Register |
| POST | `/api/auth/login/` | Login |
| POST | `/api/auth/logout/` | Logout |
| GET/PATCH | `/api/me/` | Current profile/preferences |
| GET/POST | `/api/stores/` | List/create stores |
| PATCH | `/api/stores/:id/` | Edit store |
| POST | `/api/stores/:id/archive/` | Archive store |
| POST | `/api/stores/:id/restore/` | Restore store |
| GET/POST | `/api/products/` | List/create products |
| GET/PATCH | `/api/products/:id/` | Product detail/edit |
| GET | `/api/products/:id/price-history/` | Historical prices |
| GET/POST | `/api/shopping-sessions/` | List/create draft or completed session |
| GET/PATCH | `/api/shopping-sessions/:id/` | Session detail/correction |
| POST | `/api/shopping-sessions/:id/complete/` | Complete draft |
| DELETE | `/api/shopping-sessions/:id/` | Discard draft only |
| GET/POST | `/api/plans/` | List/create plans |
| GET/PATCH/DELETE | `/api/plans/:id/` | Plan detail/update/delete |
| POST | `/api/plans/from-session/:id/` | Create plan from historical session |
| POST | `/api/plans/:id/archive/` | Archive plan |
| POST | `/api/plans/:id/reactivate/` | Reactivate plan |
| POST | `/api/plans/:id/complete/` | Complete plan |
| POST | `/api/plans/:id/items/` | Add item |
| PATCH/DELETE | `/api/plans/:id/items/:itemId/` | Update/remove item |
| POST | `/api/plans/:id/items/reorder/` | Persist ordering |
| GET | `/api/plans/:id/estimate/` | Store-specific estimate/budget status |
| GET | `/api/plans/:id/budget-fit/` | What fits budget |
| GET | `/api/suggestions/products/` | Frequent products |
| GET | `/api/dashboard/` | Dashboard aggregate |

---

# 11. Empty, Error, and Edge States

| Situation | Required UX |
|---|---|
| No shopping history | Invite user to add first shopping session. |
| No plans | Invite user to create first shopping plan. |
| No products | Explain products appear as sessions are recorded; allow creation where relevant. |
| No stores | Offer inline Add Store. |
| No price history at selected store | Show unknown state, never zero. |
| No budget | Show `NO_BUDGET` state and invite user to set one. |
| Incomplete estimate | Show known total + unknown item count. |
| Known total already over budget with unknown items | Keep `INCOMPLETE_ESTIMATE` and explicitly say known items already exceed budget. |
| Receipt subtotal differs from receipt total | Non-blocking warning. |
| Expired authentication | Redirect to login without leaking protected content. |
| Server mutation fails | Preserve recoverable form state and show retry/error message. |

---

# 12. Non-Functional MVP Requirements

## Security

- HTTPS in production.
- Django password hashing.
- Strict user ownership checks.
- CSRF/CORS configured for deployment model.
- Secrets in environment/config, not source control.
- No protected resource exposed by predictable IDs.

## Accessibility

- Keyboard-accessible controls.
- Proper labels and semantic headings.
- Visible focus states.
- Status communicated with text/icon, not color alone.
- Sufficient contrast.
- Touch-friendly mobile targets.

## Performance

Targets, not hard guarantees:

- Typical non-heavy API requests: p95 approximately `< 500 ms` under normal MVP load.
- Planner edits should feel immediate through local feedback while server state refreshes.
- History/products/plans use pagination or efficient bounded queries.
- Dashboard aggregation should avoid N+1 query patterns.

## Reliability

- Multi-record shopping-session writes use transactions.
- Duplicate form submissions are guarded.
- Backend remains authoritative for money, estimates, and budget status.

---

# 13. Recommended Visual Direction

The initial prototype's visual direction is adopted as the baseline, not as an immutable pixel-perfect specification.

### Brand baseline

- Primary green: `#2F7D4F`
- Warm background: `#FAF9F5`
- Typography: **Plus Jakarta Sans** or a metrically suitable fallback
- Rounded cards
- Subtle borders
- Restrained shadows
- Clear whitespace
- Green for positive/primary
- Amber for incomplete/unknown warnings
- Red for over-budget/destructive actions

Avoid excessive gradients, glassmorphism, or dense enterprise-dashboard styling.

---

# 14. MVP Analytics

Track only events useful for understanding the product loop.

Recommended events:

```text
account_created
shopping_session_draft_saved
shopping_session_completed
shopping_session_corrected
shopping_plan_created
plan_created_from_session
suggested_item_added
plan_store_changed
budget_set
budget_removed
plan_within_budget
plan_over_budget
plan_incomplete_estimate
budget_fit_viewed
shopping_plan_completed
```

Primary product funnel:

```text
Registered
→ Completed first shopping session
→ Built repeat history
→ Created shopping plan
→ Set/viewed budget estimate
→ Returned and completed another shopping session
```

---

# 15. Explicitly Out of MVP

- Receipt image upload
- OCR
- Barcode scanning
- Live retailer pricing
- Inventory availability
- Coupons/deal discovery
- Loyalty-card integration
- Bank/credit-card integration
- Household collaboration
- Native mobile app
- Meal planning
- Recipes
- Nutrition tracking
- Automatic product substitutions
- ML price forecasting
- AI chat assistant
- Multi-store route optimization
- Automatic cross-store price substitution
- Partial-quantity budget optimization
- Plan duplication

---

# 16. Recommended Build Order

## Phase 1 — Foundation

- Django/React/PostgreSQL setup
- Authentication
- App shell
- Store model/management
- Product model/catalog

**Exit:** authenticated shopper can create stores/products and navigate the application.

## Phase 2 — Manual Shopping Sessions

- Manual entry form
- Inline store/product creation
- Draft saving
- Session completion
- History list/details
- Session correction

**Exit:** shopper can reliably turn a receipt into completed purchase history.

## Phase 3 — Historical Pricing

- Product price history
- Latest store-specific price service
- Product detail history/chart

**Exit:** each known estimate can be traced to a completed historical purchase.

## Phase 4 — Shopping Planning

- Plans list
- Three creation modes
- Planner item CRUD/reorder/priority
- Plan lifecycle

**Exit:** shopper can build and persist an upcoming basket.

## Phase 5 — Budget Intelligence

- Estimate service
- Budget status
- Store switching
- What Fits My Budget

**Exit:** shopper can understand affordability without unknown prices being misrepresented.

## Phase 6 — Personalization & Dashboard

- Frequent-product suggestions
- Dashboard aggregates
- Monthly spending summary

**Exit:** historical data visibly reduces planning effort.

## Phase 7 — MVP Polish

- Responsive mobile planner
- Accessibility
- Error/empty states
- Automated tests
- Analytics events
- Performance/security review

---

# 17. MVP Release Gate

The MVP is release-ready only when this end-to-end scenario works reliably:

1. New user registers and logs in.
2. User starts **Add Shopping Session**.
3. User creates a store inline if necessary.
4. User creates/reuses products and manually enters receipt lines.
5. User saves a draft, returns, and completes it.
6. Completed session appears in history and price history.
7. User records additional sessions.
8. User creates a plan from a previous session or frequent products.
9. User selects a store and optionally a planned date.
10. User sets a budget.
11. GrocerEase returns store-specific estimates with traceable price sources.
12. Unknown store prices remain unknown and are excluded from known total.
13. User changes store, quantities, priorities, and order.
14. Budget status changes correctly among `NO_BUDGET`, `WITHIN_BUDGET`, `OVER_BUDGET`, and `INCOMPLETE_ESTIMATE`.
15. User opens **What fits my budget?** and receives deterministic `FIT`, `NOT_FIT`, and `UNKNOWN` results.
16. User completes the plan and is encouraged to record the actual shopping session.
17. User logs out and back in; all persisted data remains correct and private.

---

# 18. Final MVP Definition

## GrocerEase v1

**Personal grocery memory + shopping planner + store-specific historical cost estimator + budget decision support.**

### Core data flow

```text
Manual Receipt
→ Shopping Session
→ Product & Store Price History
→ Shopping Plan
→ Store-Specific Estimate
→ Budget Decision
→ Next Shopping Session
```

### MVP must prove

> Recording grocery history is worth the effort because GrocerEase makes the shopper's next planning and budgeting session faster, more informed, and easier to control.
