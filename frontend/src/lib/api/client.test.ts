import { describe, expect, it } from 'vitest'
import { createFakeApi } from '../../test/fakeApi'
import { ApiError, apiPost, apiRequest, resolveApiBaseUrl } from './client'

describe('apiRequest CSRF handling', () => {
  it('does not send a CSRF token on safe requests', async () => {
    const api = createFakeApi()
    document.cookie = 'csrftoken=existing-token; path=/'

    await apiRequest('/health/')

    expect(api.calls[0].headers.has('X-CSRFToken')).toBe(false)
  })

  it('sends the current CSRF cookie on unsafe requests', async () => {
    const api = createFakeApi()
    document.cookie = 'csrftoken=existing-token; path=/'

    await apiPost('/auth/login/', { email: 'alex@example.com', password: 'x' })

    expect(api.requests('GET /auth/csrf/')).toHaveLength(0)
    expect(api.requests('POST /auth/login/')[0].headers.get('X-CSRFToken')).toBe(
      'existing-token',
    )
  })

  it('bootstraps the CSRF cookie once when the browser has none', async () => {
    const api = createFakeApi()

    await Promise.all([apiPost('/auth/login/', {}), apiPost('/auth/logout/')])

    expect(api.requests('GET /auth/csrf/')).toHaveLength(1)
    expect(api.requests('POST /auth/login/')[0].headers.get('X-CSRFToken')).toBe(
      'csrf-from-bootstrap',
    )
  })

  it('fails the request when the CSRF bootstrap fails', async () => {
    const api = createFakeApi()
    api.on('GET /auth/csrf/', { status: 503 })

    await expect(apiPost('/auth/login/', {})).rejects.toMatchObject({ status: 503 })
    expect(api.requests('POST /auth/login/')).toHaveLength(0)
  })

  it('raises ApiError with the parsed body for failed responses', async () => {
    const api = createFakeApi()
    api.on('GET /me/', { status: 401, body: { detail: 'Not authenticated.' } })

    const error = await apiRequest('/me/').catch((caught: unknown) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 401, body: { detail: 'Not authenticated.' } })
  })
})

describe('resolveApiBaseUrl', () => {
  const origin = 'https://app.grocerease.test'

  it('defaults to /api on the page origin', () => {
    expect(resolveApiBaseUrl(undefined, origin)).toBe('/api')
    expect(resolveApiBaseUrl('  ', origin)).toBe('/api')
  })

  it('accepts same-origin paths and absolute URLs', () => {
    expect(resolveApiBaseUrl('/backend/api/', origin)).toBe('/backend/api')
    expect(resolveApiBaseUrl('https://app.grocerease.test/api', origin)).toBe('/api')
  })

  it('rejects another origin, where session cookies would not be sent', () => {
    expect(() => resolveApiBaseUrl('https://api.grocerease.test/api', origin)).toThrow(
      /must be on the app's own origin/,
    )
    expect(() => resolveApiBaseUrl('//api.grocerease.test/api', origin)).toThrow()
    expect(() => resolveApiBaseUrl('http://app.grocerease.test/api', origin)).toThrow()
  })
})
