/**
 * Resolves the API base path and rejects other origins. Auth relies on the
 * session and CSRF cookies, which are only sent with same-origin requests and
 * only readable from `document.cookie` on the API's own origin.
 */
export function resolveApiBaseUrl(configured: string | undefined, pageOrigin: string): string {
  const url = new URL(configured?.trim() || '/api', pageOrigin)
  if (url.origin !== pageOrigin) {
    throw new Error(
      `VITE_API_BASE_URL must be on the app's own origin (${pageOrigin}), but it points to ${url.origin}. ` +
        'Serve the API from the same origin or proxy it, for example under /api.',
    )
  }
  return url.pathname.replace(/\/+$/, '')
}

const API_BASE_URL = resolveApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL,
  window.location.origin,
)

const CSRF_COOKIE_NAME = 'csrftoken'
const CSRF_HEADER_NAME = 'X-CSRFToken'
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS', 'TRACE'])

export class ApiError extends Error {
  public readonly status: number
  public readonly body: unknown

  constructor(
    status: number,
    body: unknown,
  ) {
    super(`API request failed with status ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

export function isApiError(error: unknown, status?: number): error is ApiError {
  return (
    error instanceof ApiError && (status === undefined || error.status === status)
  )
}

function readCookie(name: string): string | undefined {
  const prefix = `${name}=`
  const cookie = document.cookie
    .split(';')
    .map((part) => part.trim())
    .find((part) => part.startsWith(prefix))

  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : undefined
}

let csrfBootstrap: Promise<unknown> | null = null

/**
 * Returns the CSRF cookie value, asking the API to issue one first when the
 * browser has none (for example before an anonymous login or registration).
 */
async function getCsrfToken(): Promise<string | undefined> {
  const existing = readCookie(CSRF_COOKIE_NAME)
  if (existing) {
    return existing
  }

  csrfBootstrap ??= apiRequest('/auth/csrf/').finally(() => {
    csrfBootstrap = null
  })
  await csrfBootstrap
  return readCookie(CSRF_COOKIE_NAME)
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')

  if (options.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  // Django rotates the CSRF token on login, so read the cookie per request.
  const method = (options.method ?? 'GET').toUpperCase()
  if (!SAFE_METHODS.has(method) && !headers.has(CSRF_HEADER_NAME)) {
    const csrfToken = await getCsrfToken()
    if (csrfToken) {
      headers.set(CSRF_HEADER_NAME, csrfToken)
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: options.credentials ?? 'same-origin',
  })
  const contentType = response.headers.get('Content-Type') ?? ''
  const body = contentType.includes('application/json')
    ? await response.json().catch(() => undefined)
    : await response.text().catch(() => undefined)

  if (!response.ok) {
    throw new ApiError(response.status, body)
  }

  return body as T
}

export function apiPost<T>(path: string, data?: unknown): Promise<T> {
  return apiRequest<T>(path, {
    method: 'POST',
    body: data === undefined ? undefined : JSON.stringify(data),
  })
}
