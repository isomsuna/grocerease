import { vi } from 'vitest'
import type { CurrentUser } from '../features/auth/types'

export type ApiCall = {
  method: string
  path: string
  body: unknown
  headers: Headers
}

export type FakeResponse = { status?: number; body?: unknown }

type Handler = (call: ApiCall) => FakeResponse | Promise<FakeResponse>

export const alex: CurrentUser = {
  id: 1,
  display_name: 'Alex',
  email: 'alex@example.com',
}

const NOT_AUTHENTICATED: FakeResponse = {
  status: 401,
  body: { detail: 'Authentication credentials were not provided.' },
}

/**
 * Stubs `fetch` with a small in-memory stand-in for the Django API. It keeps a
 * server-side session so `/api/me/` reflects login, registration, and logout;
 * individual routes can be overridden per test with `on()`.
 */
export function createFakeApi({ signedInAs = null }: { signedInAs?: CurrentUser | null } = {}) {
  let sessionUser = signedInAs
  const calls: ApiCall[] = []

  const handlers = new Map<string, Handler>([
    ['GET /auth/csrf/', () => {
      document.cookie = 'csrftoken=csrf-from-bootstrap; path=/'
      return { status: 204 }
    }],
    ['GET /me/', () => (sessionUser ? { body: sessionUser } : NOT_AUTHENTICATED)],
    ['GET /health/', () => ({ body: { status: 'ok' } })],
    ['POST /auth/login/', () => {
      sessionUser = alex
      return { body: alex }
    }],
    ['POST /auth/register/', ({ body }) => {
      const { display_name, email } = body as Record<string, string>
      sessionUser = { id: 2, display_name, email }
      return { status: 201, body: sessionUser }
    }],
    ['POST /auth/logout/', () => {
      sessionUser = null
      return { status: 204 }
    }],
    ['POST /auth/password-reset/', () => ({ body: { detail: 'Check your email.' } })],
    ['POST /auth/password-reset/confirm/', () => ({ body: { detail: 'Password reset.' } })],
  ])

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = new URL(String(input), 'http://localhost')
    const call: ApiCall = {
      method: (init.method ?? 'GET').toUpperCase(),
      path: url.pathname.replace(/^\/api/, '') + url.search,
      body: typeof init.body === 'string' ? JSON.parse(init.body) : undefined,
      headers: new Headers(init.headers),
    }
    calls.push(call)

    const handler = handlers.get(`${call.method} ${call.path}`)
    if (!handler) {
      throw new Error(`Unhandled API request: ${call.method} ${call.path}`)
    }

    const { status = 200, body } = await handler(call)
    return new Response(body === undefined ? null : JSON.stringify(body), {
      status,
      headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
    })
  })

  vi.stubGlobal('fetch', fetchMock)

  return {
    calls,
    on(route: string, handler: Handler | FakeResponse) {
      handlers.set(route, typeof handler === 'function' ? handler : () => handler)
    },
    /** Simulates the server-side session expiring or being revoked. */
    expireSession() {
      sessionUser = null
    },
    requests(route: string) {
      return calls.filter((call) => `${call.method} ${call.path}` === route)
    },
  }
}
