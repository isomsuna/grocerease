# GrocerEase frontend

React and TypeScript frontend for GrocerEase, a grocery shopping planner and
budget tracker.

## Development

```sh
npm install
npm run dev
```

Set `VITE_API_BASE_URL` to override the default `/api` base URL for backend
requests. It must stay on the app's own origin, either as a path such as
`/api` or as a URL on the same origin. Authentication depends on same-origin
session and CSRF cookies, so the client refuses to start with an API on
another origin. Serve the API from the same origin, or proxy it.

## Testing

```sh
npm test            # run Vitest once (used by CI)
npm run test:watch  # rerun tests on change
```

Tests use Vitest, React Testing Library, and jsdom. `src/test/fakeApi.ts`
stubs `fetch` at the network boundary, so tests exercise the real API client,
TanStack Query cache, and route tree.

## Authentication

Authentication uses Django session cookies, and `GET /api/me/` is the only
source of truth for the signed-in shopper. The client never stores a user ID
for authorization.

- Before an unsafe request, the API client sends the `csrftoken` cookie as
  `X-CSRFToken`. When the cookie is missing, it first calls
  `GET /api/auth/csrf/`.
- A `401` from any private request clears cached private data, and the route
  guard returns the shopper to `/login`. After the next login, the shopper
  returns to the page they asked for.
- Logout clears the TanStack Query cache before showing `/login`.
- Password-reset emails link to `/reset-password?uid=<uid>&token=<token>`. The
  page moves `uid` and `token` into this tab's `sessionStorage`, removes them
  from the address bar, and posts `{ uid, token, new_password }` to
  `/api/auth/password-reset/confirm/`. The stored link is cleared after a
  successful reset or a rejected link.

## Project specifications

The product, frontend, and backend requirements are documented in
[`../GROCEREASE.md`](../GROCEREASE.md), [`../FRONTEND.md`](../FRONTEND.md), and
[`../BACKEND.md`](../BACKEND.md). `../GrocerEase.html` is a visual prototype
reference.
