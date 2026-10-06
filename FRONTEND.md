# GrocerEase — Frontend MVP Specification

**Status:** Canonical React implementation contract  
**Aligned with:** `GROCEREASE.md` and `BACKEND.md`  
**Prototype reference:** `GrocerEase.html` supplies the baseline interaction/visual direction, but this document is authoritative for frontend behavior.

---

## 1. Frontend Responsibility

The GrocerEase frontend is responsible for:

- interaction and presentation;
- accessible responsive behavior;
- route handling;
- form state and client-side validation;
- immediate local feedback;
- server-state fetching and mutation;
- clearly presenting backend-calculated prices, estimates, and budget states.

The frontend is **not** authoritative for:

- authentication ownership;
- persisted monetary totals;
- latest-price selection;
- price-history derivation;
- shopping suggestions;
- budget status;
- budget-fit decisions.

> **React decides how the experience feels. Django decides what is true.**

The frontend may calculate temporary previews such as line totals while the user types, but saved values and decision states must be reconciled with backend responses.

---

## 2. Recommended Frontend Stack

### Required

- React
- Responsive web UI
- REST API integration
- Route-based pages
- Accessible forms and controls

### Recommended

- TypeScript
- React Router
- TanStack Query
- React Hook Form
- Zod or equivalent client schema validation
- Accessible primitives such as Radix/shadcn or equivalent
- Decimal-safe library/helper for client preview calculations (no binary floating point for money; see §5.3)

### Suggested structure

```text
src/
  api/
  app/
  components/
    ui/
  features/
    auth/
    dashboard/
    stores/
    products/
    sessions/
    plans/
  hooks/
  layouts/
  routes/
  utils/
```

Each feature may contain:

```text
components/
pages/
api/
hooks/
types/
schemas/
```

---

# 3. Canonical Routing

## 3.1 Public routes

```text
/login
/register
/forgot-password
/reset-password
```

## 3.2 Authenticated routes

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

## 3.3 Routing rules

- Unauthenticated access to private routes redirects to `/login`.
- After successful login, return to the originally requested private route when practical.
- Authenticated users visiting login/register should normally be redirected to `/`.
- A missing or unauthorized private object renders a safe Not Found state; never reveal whether another user's resource exists.
- `/sessions/:sessionId/edit` is used both to continue drafts and explicitly correct completed shopping sessions.

### Canonical frontend enum values

The frontend may render human-readable labels, but API/state types use these values exactly:

```text
ShoppingSession.status: DRAFT | COMPLETED
ShoppingPlan.status:    ACTIVE | COMPLETED | ARCHIVED
PlanItem.priority:      MUST_HAVE | OPTIONAL
Budget status:          NO_BUDGET | WITHIN_BUDGET | OVER_BUDGET | INCOMPLETE_ESTIMATE
Budget-fit result:      FIT | NOT_FIT | UNKNOWN
```

---

# 4. Application Shell & Design System

## 4.1 Visual baseline

Adopt the initial prototype's visual direction:

- Primary green: `#2F7D4F`
- Warm page background: `#FAF9F5`
- Font: Plus Jakarta Sans with system fallback
- Rounded cards
- Subtle borders and shadows
- Spacious consumer-product layout
- Limited decorative effects

Semantic intent:

- Green: primary/positive/within budget
- Amber: warning/incomplete/unknown price
- Red: over budget/destructive
- Neutral gray: secondary information

Do not rely on color alone for meaning.

## 4.2 Desktop shell

Persistent left sidebar:

1. GrocerEase brand
2. Prominent **+ Add Shopping Session** button
3. Dashboard
4. Shopping Plans
5. Shopping History
6. Products
7. Stores
8. Settings
9. Current user/profile area

## 4.3 Mobile shell

- Compact top header
- Bottom navigation for primary destinations
- Add Shopping Session remains easily reachable
- Safe-area padding supported
- Planner uses touch-friendly cards and sticky budget summary

## 4.4 Shared UI components

At minimum:

```text
Button
IconButton
TextInput
CurrencyInput
QuantityInput / QuantityStepper
Select
Autocomplete
DateInput / DatePicker
Textarea
Card
StatCard
Badge
StatusBadge
Tabs
Modal / Dialog
Drawer / Sheet
DataTable
Pagination / LoadMore
EmptyState
Toast
ConfirmationDialog
SearchInput
FilterControl
StoreSelector
ProductAutocomplete
BudgetSummary
BudgetProgressBar
ShoppingSessionCard
ShoppingPlanCard
PlanItemRow
PlanItemCard
ProductSuggestionCard
Skeleton
InlineError
```

All components need default, hover, focus, disabled, loading, and error states where applicable.

---

# 5. Global Frontend Requirements

## 5.1 Server state

Use query/mutation patterns that support:

- caching;
- targeted invalidation;
- background refetching where useful;
- preserving stable UI during small mutations.

Do not blank an entire planner page while changing one quantity.

## 5.2 Error handling

Handle at minimum:

- `400` — validation errors
- `401` — authentication required/expired
- `403` — forbidden
- `404` — unavailable/not found
- `409` — conflict such as duplicate product in a plan
- `500` — unexpected failure

Recoverable failures should not erase unsaved local form state.

## 5.3 Money display

All money is in Philippine pesos (PHP). There is no currency preference or selector. Display `₱` with thousands separators and exactly 2 decimal places.

Client previews use decimal-safe arithmetic, not binary floating point, and follow the backend rounding rule: each line total is rounded half-up to 2 decimal places, then rounded line totals are summed. Example: `0.5 × ₱0.25 = ₱0.13`.

Example formatting:

```text
₱95.00
₱3,000.00
```

Budget input may be blank. Blank means **no budget**; never coerce blank to zero.

## 5.4 Quantity display

Support integer and decimal values up to 3 decimal places.

Examples:

```text
1
2
1.5
0.750
```

If a product has a unit label, surface it next to quantity where useful.

## 5.5 Accessibility

Minimum:

- labels associated with fields;
- keyboard-accessible navigation and dialogs;
- visible focus;
- semantic headings;
- correct table semantics on desktop;
- text/icon meaning in addition to color;
- appropriate touch targets;
- dialogs trap focus and restore it on close;
- screen-reader-friendly loading and error messages.

## 5.6 Dates and time zone

GrocerEase uses the `Asia/Manila` time zone.

- "Today" (for example a default purchase date) and calendar-month labels follow Manila time, not the browser's time zone.
- Date-only API fields such as `purchase_date` and `planned_date` are calendar dates; render them without time-zone shifting.

---

# 6. Feature Specifications

## 6.1 Authentication

### Screens

- Login
- Registration
- Forgot password
- Reset password

### Registration fields

- Display name
- Email
- Password
- Confirm password

### Login fields

- Email
- Password

### Required behavior

- Client validates required fields and email shape.
- Password confirmation must match before submission.
- Backend password-policy errors are rendered next to the password field or in a clear form-level message.
- `401` on a private route clears stale auth state and returns user to login.
- Do not use a client-stored user ID as an authorization mechanism.

### Success criteria

- User can register, log in, log out, request password reset, and reset password.
- Authenticated app shell is never shown with stale private data after logout.

---

## 6.2 Dashboard

### Route

```text
/
```

### Header

Example:

> **Good morning, Alex**  
> Ready to plan your next grocery trip?

### Quick actions

Primary:

- Add Shopping Session → `/sessions/new`
- Create Shopping Plan → `/plans/new`

Secondary:

- Check a Price → `/products`

### Active plan card

Display backend-provided active plan summary:

- Name
- Store
- Item count
- Planned date if present
- Budget if present
- Known estimated total
- Unknown item count
- Remaining or over amount when meaningful
- Budget status
- Progress bar when a budget exists

Canonical status values:

```text
NO_BUDGET
WITHIN_BUDGET
OVER_BUDGET
INCOMPLETE_ESTIMATE
```

For incomplete estimate with known total already above budget, explicitly say so.

### Recent shopping session

Show latest completed session:

- Date
- Store
- Item count
- Receipt total
- View Session

### Frequent products

Each suggestion shows:

- Product name
- `Bought in X of your last Y trips`
- Latest selected-store price only if a relevant target context exists; otherwise omit
- Add-to-plan action only when a specific active plan is the target, otherwise route user to planning

### Monthly spending

Show current and previous calendar month totals. Keep secondary.

### Empty state

If no completed sessions:

> **Your shopping history starts here.**  
> Add your first grocery receipt manually to start building price history.

### Success criteria

- Dashboard is useful for both new and returning users.
- All budget numbers/states come from backend response, not local inference.

---

## 6.3 Store Management

### Route

```text
/stores
```

### List behavior

Tabs or filters:

- Active
- Archived

Each store card shows:

- Name
- Branch/location label
- Session count
- Last visit if available
- Status

Actions:

- Edit
- Archive
- Restore

### Store form

Fields:

- Name
- Branch/location label
- Notes

### Inline store creation

`StoreSelector` must support **+ Add Store** from:

- `/sessions/new`
- `/sessions/:id/edit`
- `/plans/new`
- `/plans/:id`

Inline create behavior:

1. Open modal/sheet without leaving current form.
2. Create store via API.
3. Insert returned store into selector cache.
4. Auto-select it.
5. Preserve the rest of the current form.

### Success criteria

- Missing store never forces user to abandon receipt or planner input.
- Archived store is not shown in normal selectors unless current historical record already references it.
- A new shopping session or plan cannot use an archived store. If the backend rejects a store because it is archived, show the error on the store field and preserve the rest of the form.

---

## 6.4 Product Catalog

### Routes

```text
/products
/products/:productId
```

### Product list

Show:

- Name
- Category
- Last price paid
- Store
- Last purchase date
- Purchase frequency

### Controls

- Search by name
- Category filter
- Optional store filter if backend supports it
- Add Product

### Product create/edit

Fields:

- Name
- Category
- Optional unit label

If backend reports duplicate normalized name, offer the existing product rather than creating a second identity.

### Product autocomplete

Used in sessions and plans.

Behavior:

1. Search server-backed personal catalog.
2. Show matches.
3. If exact normalized match exists, reuse it.
4. In session entry, allow **Create “X”** if no match.
5. In a session/plan that already contains the chosen product, focus the existing row instead of creating a duplicate.

### Product details

Show:

- Name/category/unit
- Times purchased
- Last purchased
- Latest price paid + store
- Price-history list
- Historical price chart when at least two observations exist
- Add to Shopping Plan action

The chart is historical only; no prediction line.

### Success criteria

- Search and filters are server-backed or bounded appropriately.
- Repeated purchases reuse product identity.

---

## 6.5 Manual Shopping Session Entry

### Routes

```text
/sessions/new
/sessions/:sessionId/edit
```

### Header language

New:

> **Add Shopping Session**  
> Copy the details from your printed receipt. Prices you enter become your price history for planning.

Edit:

> **Edit Shopping Session**

### Receipt fields

- Store
- Purchase date
- Receipt total
- Optional notes

### Items table/card fields

- Product
- Quantity
- Unit price
- Line total
- Remove

### Required interactions

- Add item
- Remove item
- Product autocomplete
- Inline product creation
- Inline store creation
- Client preview of line total
- Client preview of item subtotal
- Difference from receipt total
- Save Draft
- Save Shopping Session
- Cancel/back

### Preview formulas

```text
line_total_preview = round_half_up(quantity × unit_price, 2)
items_subtotal_preview = Σ line_total_preview
difference_preview = receipt_total - items_subtotal_preview
```

Use decimal-safe preview logic where practical. Backend response replaces preview as authoritative after save.

### Duplicate product behavior

If the user selects a product already present:

- do not add a second row;
- focus/highlight the existing row;
- optionally show toast: `This product is already in the session.`

### Receipt mismatch

Show a neutral/amber callout, not a blocking error.

Example:

> **₱25.00 not itemized**  
> Your item subtotal differs from the receipt total. You can still save this session.

### Save Draft

- May submit incomplete data.
- Show loading only on draft button while request is pending.
- On success, route to History Drafts or remain with a clear `Draft saved` state.

### Save Shopping Session

Client validates obvious completion requirements before submit, but backend is authoritative.

On success:

- show confirmation toast;
- route to `/history/:sessionId`;
- optionally say `X items added to your price history.`

### Edit completed session

- Load persisted values into same form.
- Clearly indicate this is changing historical data.
- On save, route back to session details and refresh price-history/plan estimate queries that may be affected.

### Success criteria

- Form remains usable on mobile.
- Double submissions are disabled.
- Backend field errors map to the relevant control.

---

## 6.6 Shopping History

### Route

```text
/history
```

### Tabs

- Completed (default)
- Drafts

### Completed card/row

- Purchase date
- Store
- Item count
- Receipt total
- View Details
- Use for Next Shopping Plan

### Draft card/row

- Last updated
- Store if known
- Purchase date if known
- Item count
- Draft badge
- Continue Draft → `/sessions/:id/edit`

### Filters

Completed:

- Store
- Date range

Drafts:

- Optional store filter

### Pagination

Use backend pagination.

Acceptable UI patterns:

- numbered pages;
- Previous/Next;
- Load More.

Do not fetch all history for client-only filtering.

### Empty states

Completed:

> No completed shopping sessions yet.

Drafts:

> No receipt drafts.

### Success criteria

- Changing filters updates query parameters or equivalent state predictably.
- Drafts do not visually look like completed price history.

---

## 6.7 Shopping Session Details

### Route

```text
/history/:sessionId
```

### Display

- Store
- Purchase date
- Receipt total
- Items subtotal
- Difference when non-zero
- Status
- Item count

Items:

- Product
- Quantity
- Unit price
- Line total

### Completed-session CTA

Prominent band:

> **Shopping again soon?**  
> Start a plan with this exact basket. Prices are estimated from your history at the selected store.

Action:

**Use for Next Shopping Plan**

### Correction action

**Edit Shopping Session** → `/sessions/:id/edit`

Do not make historical values directly editable in the details table.

### Success criteria

- Values match backend detail response exactly.
- User understands editing this session may change future estimates.

---

## 6.8 Shopping Plans List

### Route

```text
/plans
```

### Tabs/groups

- Active
- Completed
- Archived

### Plan card

Show:

- Name
- Store
- Planned date
- Item count
- Budget if set
- Known estimated total
- Unknown-price item count
- Budget status

Actions appropriate to status:

Active:

- Continue Planning
- Archive

Completed:

- View
- Reactivate

Archived:

- View
- Reactivate

Page primary action:

**Create Shopping Plan**

### Not included

No Duplicate Plan action in MVP.

### Success criteria

- Status groups match backend state.
- No client-only status assumptions.

---

## 6.9 Create Shopping Plan

### Route

```text
/plans/new
```

### Step 1 — Choose start mode

Cards:

1. **Start Empty**
2. **Use Previous Shopping Session**
3. **Add From Frequent Products**

### Step 2 — Source selection

Previous session mode:

- show recent completed sessions;
- select exactly one;
- default store to source session store; if that store is archived, leave the store unselected and require the user to choose an active store (or add one inline).

Frequent products mode:

- show frequent products with reason;
- allow selecting multiple products;
- default quantity `1` unless backend/source provides a better explicit value.

### Step 3 — Plan details

- Plan name
- Store — required
- Budget — optional

Planned date may be set later on the planner.

Store selector supports inline Add Store.

### Create action

- Do not convert blank budget to zero.
- Disable create while request is pending.
- On success route to `/plans/:planId`.

### Success criteria

- All three creation modes result in the same canonical planner model.
- Copied historical prices are not treated as fixed plan prices.

---

## 6.10 Shopping Planner

### Route

```text
/plans/:planId
```

### Header

- Back to Shopping Plans
- Plan name
- Store / item count subtitle
- Lifecycle actions

Active plan actions:

- Archive
- Mark Completed

Completed/archived:

- Reactivate

All plans:

- Delete Plan in a destructive area with confirmation

### Plan details card

When the plan is `ACTIVE`, these fields are editable:

- Plan name
- Store
- Planned date
- Budget

When the plan is `COMPLETED` or `ARCHIVED`, the planner is read-only until the user chooses **Reactivate**.

Store helper:

> Prices are estimated from your history at this store.

### Planner views

Tabs:

- Items
- What fits my budget

### Items view — desktop

Columns/regions:

- Product
- Quantity
- Priority
- Estimated unit price
- Estimated line total
- Price source
- Remove
- Drag/reorder handle

### Items view — mobile

Each item becomes a card with:

- Product
- Quantity stepper/input
- Price each
- Estimated line total
- Priority control
- Price-source text
- Remove
- Reorder affordance where supported

### Priority

```text
Must-have
Optional
```

Maps to:

```text
MUST_HAVE
OPTIONAL
```

### Add product

- Product autocomplete
- Existing products only or catalog creation if product-management UX explicitly permits; MVP baseline can route to Product creation if needed
- If product already exists in plan, focus existing row and do not duplicate

### Reordering

- Persist order to backend.
- Keyboard-accessible alternative to drag-and-drop is required if drag-and-drop is used.

### Suggestions side panel

Desktop:

- Sticky/visible next to planner where space allows.

Mobile:

- Below plan items or in collapsible section.

### Mutation behavior

For quantity/priority/store/budget changes:

1. Show immediate local update when safe.
2. Send mutation.
3. Refetch or consume returned authoritative estimate.
4. Roll back or show recoverable error if mutation fails.

### Success criteria

- User can perform the full planning workflow without leaving the page.
- Unknown prices remain visibly unknown.

---

## 6.11 Budget Summary

Reusable `BudgetSummary` component.

### Data required

- Budget nullable
- Known total
- Unknown count
- Estimate complete
- Budget status
- Remaining amount if valid
- Over-by amount if valid
- Known-total-exceeds-budget boolean

### Status rendering

#### NO_BUDGET

Neutral.

```text
No budget set
Known estimated total: ₱2,650.00
Set a budget to see affordability.
```

#### WITHIN_BUDGET

Green.

```text
Within budget
Budget: ₱3,000.00
Estimated: ₱2,650.00
Remaining: ₱350.00
```

#### OVER_BUDGET

Red.

```text
Over budget
Budget: ₱3,000.00
Estimated: ₱3,420.00
Over by: ₱420.00
```

#### INCOMPLETE_ESTIMATE

Amber.

```text
Incomplete estimate
Known estimated total: ₱2,650.00
2 items have no price history at this store.
```

If known total already exceeds budget:

```text
Known items are already ₱250.00 over budget.
2 additional items have unknown prices.
```

### Progress bar

- Show only when budget exists.
- Use known total as progress numerator.
- In incomplete state, amber styling indicates the total is not complete.
- Clamp visual percentage for rendering but show true numeric amounts.

---

## 6.12 Price Source Display

Known price:

```text
₱95.00 each
Last purchased here Sep 24
```

Unknown:

```text
No price history at this store
```

Optional supporting information may say:

```text
Last purchased for ₱97.00 at Robinsons — Fuente
```

but this value must be visually secondary and never included in selected-store estimate.

---

## 6.13 Store Switching

When user changes store in an active plan:

1. Persist store change.
2. Show subtle recalculating state.
3. Refresh estimate.
4. Refresh suggestions if store-specific context affects their display.
5. Update every item price source.
6. Update budget summary and What Fits results.

Recommended toast:

> Store changed — prices re-estimated.

Do not preserve stale prices from previous store while implying they are current.

---

## 6.14 Suggested From Your History

Display backend suggestions with:

- Product name
- Explanation: `Bought in X of your last Y trips`
- Selected-store latest price if known
- `No price history at this store` if unknown
- Add button

Suggestions already present in the plan should not be displayed as addable suggestions.

Do not label as AI.

---

## 6.15 What Fits My Budget

### Planner tab

Label:

**What fits my budget**

### No budget

Show empty state:

> Set a budget to see what fits.

### Result rows

Backend states:

```text
FIT
NOT_FIT
UNKNOWN
```

Render:

- ✓ FIT
- ✕ NOT_FIT
- ? UNKNOWN

Include:

- Product
- Full planned quantity
- Planned line total if known
- Priority
- Reason/message

### Summary

- Budget
- Affordable known basket
- Remaining budget
- Must-have-exceeds-budget warning when applicable

### Ordering

Display result in the calculation order returned by backend: must-have first, then optional, both respecting plan sort order.

### No partial quantity

Do not show `PARTIAL` state. If a full planned quantity does not fit, user must manually lower quantity in Items view and recalculate.

### Optional convenience action

The prototype's **Remove items that don't fit** action is useful but is **P1**, not required for release. If implemented:

- confirm affected item count;
- remove only `NOT_FIT` optional items by default;
- never auto-remove must-have or unknown items;
- provide Undo when practical.

---

## 6.16 Plan Lifecycle

### Archive

- Active plan only.
- Confirmation is optional because action is reversible.
- On success status becomes Archived.

### Complete

- Active plan only.
- Confirmation dialog required.

Dialog should explicitly state:

> Completing this plan does not record what you actually purchased. Add a Shopping Session after your trip to update price history.

After completion show CTA:

**Add Shopping Session**

### Reactivate

Available for completed and archived plans.

### Delete

Destructive confirmation required.

Copy:

> This removes the plan and its items. Your shopping history and recorded prices will not be deleted.

### Success criteria

- Lifecycle mutations update both plan page and plan list caches.

---

## 6.17 Settings

### Route

```text
/settings
```

### Sections

Profile:

- Display name
- Email — when the email changes, ask for the current password and send it as `current_password`; a display-name-only save does not ask for it

Account:

- Change password — current password, new password, confirm new password
- Log out

A missing or wrong current password is shown as an error on the current-password field, and the other entered values are kept.

### Success criteria

- Email and password changes cannot be saved without the current password.
- Logout clears private query cache.

---

# 7. Frontend API Dependency Map

| UI capability | Backend dependency |
|---|---|
| Auth | `/api/auth/*`, `/api/me/` |
| Dashboard | `/api/dashboard/` |
| Stores | `/api/stores/*` |
| Product search/create | `/api/products/*` |
| Product price history | `/api/products/:id/price-history/` |
| Session draft/completion | `/api/shopping-sessions/*` |
| Shopping history | paginated `/api/shopping-sessions/` |
| Plans | `/api/plans/*` |
| Plan items/reorder | `/api/plans/:id/items/*` |
| Suggestions | `/api/suggestions/products/` |
| Plan estimate | `/api/plans/:id/estimate/` |
| Budget fit | `/api/plans/:id/budget-fit/` |

Frontend should not reimplement backend algorithms merely because mock prototype code did so.

---

# 8. Frontend User Stories

Stories are implementation-oriented and may be used directly as backlog tickets.

## FE-US-001 — Register a shopper

**Priority:** P0  
**Story:** As a new shopper, I want to create an account so my grocery history and plans are private and persistent.

**Acceptance criteria:**

- Registration includes display name, email, password, confirm password.
- Client catches empty/invalid email and password mismatch.
- Backend validation errors render clearly.
- Successful registration routes to authenticated application.

**Backend dependency:** Auth registration + `/api/me/`.

---

## FE-US-002 — Log in, recover access, and log out

**Priority:** P0  
**Story:** As a returning shopper, I want secure account access and recovery.

**Acceptance criteria:**

- Login works with email/password.
- Forgot/reset-password routes are implemented.
- `401` redirects to login.
- Logout clears private client cache and returns to login.

---

## FE-US-003 — Navigate GrocerEase consistently

**Priority:** P0  
**Story:** As a shopper, I want a clear desktop and mobile navigation shell.

**Acceptance criteria:**

- Desktop sidebar and mobile navigation expose canonical destinations.
- Current route is visibly active.
- Add Shopping Session remains prominent.
- Keyboard navigation works.

---

## FE-US-004 — Use the dashboard as a starting point

**Priority:** P0  
**Story:** As a returning shopper, I want to see my current plan, recent shopping, and next useful actions.

**Acceptance criteria:**

- Active plan summary uses backend status/estimate.
- Recent completed session is shown.
- Monthly spending and frequent products render when available.
- Empty account gets first-session CTA.

---

## FE-US-005 — Manage stores

**Priority:** P0  
**Story:** As a shopper, I want to add, edit, archive, and restore store branches.

**Acceptance criteria:**

- Active/Archived states are distinct.
- Edit form preserves existing values.
- Archive/restore updates selectors after success.

---

## FE-US-006 — Create a store without leaving my workflow

**Priority:** P0  
**Story:** As a shopper entering a receipt or plan, I want to create a missing store inline.

**Acceptance criteria:**

- Add Store opens in-place modal/sheet.
- Current form state is preserved.
- New store is selected after creation.

---

## FE-US-007 — Search and manage my product catalog

**Priority:** P0  
**Story:** As a shopper, I want reusable product identities so my history stays organized.

**Acceptance criteria:**

- Product list supports search and category filter.
- Product create/edit works.
- Duplicate-name backend error points user to existing product.

---

## FE-US-008 — View a product's historical prices

**Priority:** P1  
**Story:** As a shopper, I want to see what I previously paid for a product across stores.

**Acceptance criteria:**

- Detail page lists dated store price observations.
- Chart appears when at least two observations exist.
- No forecasting language appears.

---

## FE-US-009 — Add products quickly with autocomplete

**Priority:** P0  
**Story:** As a shopper, I want autocomplete so manual entry is faster.

**Acceptance criteria:**

- Search existing products while typing.
- Create product inline from session entry when no match exists.
- Selecting a product already in the same session/plan focuses existing row rather than duplicating it.

---

## FE-US-010 — Manually enter a shopping session

**Priority:** P0  
**Story:** As a shopper, I want to copy my physical receipt into GrocerEase.

**Acceptance criteria:**

- Store/date/receipt total and item rows are editable.
- Quantity × unit price preview updates line total.
- Subtotal and receipt difference update immediately.
- Mobile form is usable without horizontal scrolling for core actions.

---

## FE-US-011 — Save an incomplete receipt as a draft

**Priority:** P0  
**Story:** As a shopper, I want to stop receipt entry and continue later.

**Acceptance criteria:**

- Incomplete form can be saved as draft.
- Success state confirms draft saved.
- Draft can be opened from History → Drafts.

---

## FE-US-012 — Complete a shopping session despite receipt mismatch

**Priority:** P0  
**Story:** As a shopper, I want to save actual receipt data even when line items do not exactly equal receipt total.

**Acceptance criteria:**

- Mismatch is an amber warning, not blocker.
- Completion requires backend-required fields.
- On success route to history detail.

---

## FE-US-013 — Browse completed history and drafts

**Priority:** P0  
**Story:** As a shopper, I want completed purchases and unfinished entries clearly separated.

**Acceptance criteria:**

- Completed is default tab.
- Drafts tab has Continue Draft action.
- Completed supports store/date filters.
- Results use backend pagination.

---

## FE-US-014 — Inspect and correct a completed shopping session

**Priority:** P0  
**Story:** As a shopper, I want to fix manual-entry mistakes in my historical purchase.

**Acceptance criteria:**

- Details page is read-only by default.
- Edit Shopping Session opens explicit edit route.
- Save refreshes dependent history/estimate queries.
- UI warns that corrections may change future estimates.

---

## FE-US-015 — Create a plan from one of three starting modes

**Priority:** P0  
**Story:** As a shopper, I want to start empty, reuse a previous trip, or start from frequent products.

**Acceptance criteria:**

- Three mode cards are visible.
- Previous-session mode shows completed sessions only.
- Frequent-product mode shows explanation text.
- Store is required before Create.
- Blank budget remains blank/null.

---

## FE-US-016 — Manage shopping plans by lifecycle

**Priority:** P0  
**Story:** As a shopper, I want Active, Completed, and Archived plans separated.

**Acceptance criteria:**

- Plan list groups/filters by status.
- Relevant actions appear for each state.
- No Duplicate action is required.

---

## FE-US-017 — Edit plan details in the planner

**Priority:** P0  
**Story:** As a shopper, I want to update plan name, store, date, and budget from one place.

**Acceptance criteria:**

- Fields persist via API.
- Store change triggers re-estimation.
- Clearing budget produces NO_BUDGET state rather than zero budget.

---

## FE-US-018 — Add, change, remove, and reorder plan items

**Priority:** P0  
**Story:** As a shopper, I want to shape my planned basket interactively.

**Acceptance criteria:**

- Add product, edit quantity, priority, remove item, reorder.
- Duplicate product selection focuses existing row.
- Reordering persists.
- Mutations do not unnecessarily blank the whole planner.

---

## FE-US-019 — Understand each store-specific price estimate

**Priority:** P0  
**Story:** As a shopper, I want to know where each estimated price came from.

**Acceptance criteria:**

- Known item shows latest historical price and date/source.
- Unknown item says No price history at this store.
- Other-store price, if shown, is clearly secondary and excluded from total.

---

## FE-US-020 — Switch stores and see the plan re-estimated

**Priority:** P0  
**Story:** As a shopper, I want to compare my plan using my history at another store.

**Acceptance criteria:**

- Store change is persisted.
- All estimates refresh.
- Unknown count/status refresh.
- Toast or inline feedback confirms recalculation.

---

## FE-US-021 — Understand budget status correctly

**Priority:** P0  
**Story:** As a shopper, I want an accurate budget summary including unknown-price cases.

**Acceptance criteria:**

- Supports NO_BUDGET, WITHIN_BUDGET, OVER_BUDGET, INCOMPLETE_ESTIMATE.
- Incomplete state never appears as within-budget.
- If known items already exceed budget, message explicitly says so.

---

## FE-US-022 — See what full planned items fit my budget

**Priority:** P0  
**Story:** As a shopper, I want a deterministic affordability view.

**Acceptance criteria:**

- No-budget state asks user to set a budget.
- Render FIT, NOT_FIT, UNKNOWN only.
- Must-have items are shown first.
- No partial quantity state exists.
- Reordering optional items can change outcome after backend recalculation.

---

## FE-US-023 — Add frequent products from explainable suggestions

**Priority:** P0  
**Story:** As a shopper, I want quick suggestions based on my own recent history.

**Acceptance criteria:**

- Reason uses `Bought in X of your last Y trips`.
- Already-planned products are not addable suggestions.
- No AI label is used.

---

## FE-US-024 — Complete, archive, reactivate, or delete a plan safely

**Priority:** P0  
**Story:** As a shopper, I want to manage a plan's lifecycle without affecting actual purchase history.

**Acceptance criteria:**

- Complete requires confirmation and explains it does not create purchase history.
- Archive is reversible through Reactivate.
- Completed is reversible through Reactivate.
- Delete requires destructive confirmation and explicitly says history is unaffected.
- Completion offers Add Shopping Session CTA.

---

## FE-US-025 — Preserve usability under loading, errors, and mobile constraints

**Priority:** P0  
**Story:** As a shopper, I want the application to remain understandable when data is loading, empty, invalid, or temporarily unavailable.

**Acceptance criteria:**

- Major pages have skeleton/empty/error states.
- Recoverable errors preserve entered data.
- Field errors are announced/accessibly associated.
- Mobile planner has sticky compact summary and touch-friendly controls.

---

# 9. Frontend Testing Requirements

## Unit/component tests

At minimum:

- currency/quantity formatting;
- BudgetSummary rendering for all four statuses;
- receipt subtotal/difference preview;
- duplicate-product UI handling;
- ProductAutocomplete behavior;
- StoreSelector inline creation behavior;
- plan item priority rendering;
- What Fits state rendering.

## Integration tests

- registration/login route protection;
- save draft then resume;
- complete session with mismatch;
- history pagination/filtering;
- edit completed session;
- create plan from previous session;
- create plan from frequent products;
- switch store and refresh estimate;
- clear budget → NO_BUDGET;
- incomplete estimate with known-total-over-budget message;
- plan completion confirmation;
- delete-plan confirmation.

## End-to-end smoke flow

1. Register/login.
2. Create store inline.
3. Enter receipt and save draft.
4. Resume and complete.
5. Open history details.
6. Create plan from session.
7. Add budget and edit items.
8. View What Fits.
9. Complete plan.
10. Log out and back in.

---

# 10. Frontend Definition of Done

Frontend MVP is done when:

- all canonical routes exist;
- authentication screens are real, not prototype placeholders;
- desktop and mobile shells are usable;
- manual shopping-session entry supports drafts, completion, inline store/product creation, and correction;
- completed history and drafts are clearly separated;
- product catalog and price-history detail work;
- three plan creation modes work;
- planner supports item CRUD, ordering, priority, store/date/budget editing;
- backend-authoritative estimates render with traceable sources;
- all four budget statuses render correctly;
- What Fits uses only FIT / NOT_FIT / UNKNOWN;
- lifecycle confirmation flows are implemented;
- protected data is cleared on logout;
- required empty/error/loading/accessibility states exist;
- frontend behavior matches `GROCEREASE.md` and `BACKEND.md` without relying on mock-only algorithms from the prototype.
