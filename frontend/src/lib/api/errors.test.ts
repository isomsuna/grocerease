import { describe, expect, it } from 'vitest'
import { ApiError } from './client'
import { applyApiErrors, getApiErrorMap, getFallbackErrorMessage } from './errors'

describe('getApiErrorMap', () => {
  it('reads the documented errors envelope', () => {
    const error = new ApiError(409, {
      code: 'PRODUCT_ALREADY_IN_PLAN',
      errors: { product_id: ['This product is already in the plan.'] },
      existing_item_id: 'item-1',
    })

    expect(getApiErrorMap(error)).toEqual({
      product_id: ['This product is already in the plan.'],
    })
  })

  it('reads DRF field bodies and folds detail into non-field errors', () => {
    expect(getApiErrorMap(new ApiError(400, { email: 'Required.' }))).toEqual({
      email: ['Required.'],
    })
    expect(getApiErrorMap(new ApiError(403, { detail: 'CSRF Failed.' }))).toEqual({
      non_field_errors: ['CSRF Failed.'],
    })
  })

  it('ignores bodies without usable messages', () => {
    expect(getApiErrorMap(new ApiError(500, '<html>Server Error</html>'))).toEqual({})
    expect(getApiErrorMap(new TypeError('Failed to fetch'))).toEqual({})
  })
})

describe('getFallbackErrorMessage', () => {
  it('distinguishes network, throttling, and server failures', () => {
    expect(getFallbackErrorMessage(new TypeError('Failed to fetch'))).toMatch(/couldn't reach/)
    expect(getFallbackErrorMessage(new ApiError(429, undefined))).toMatch(/Too many attempts/)
    expect(getFallbackErrorMessage(new ApiError(502, undefined))).toMatch(/on our side/)
  })
})

describe('applyApiErrors', () => {
  const noFields: never[] = []
  const setError = () => {}

  it('replaces DRF throttle text with a friendly message', () => {
    const error = new ApiError(429, {
      detail: 'Request was throttled. Expected available in 42 seconds.',
    })

    expect(applyApiErrors(error, setError, noFields)).toBe(
      'Too many attempts. Please wait a moment and try again.',
    )
    expect(getFallbackErrorMessage(error)).toMatch(/Too many attempts/)
  })

  it('replaces DRF CSRF failure text with a reload prompt', () => {
    const error = new ApiError(403, { detail: 'CSRF Failed: CSRF token missing.' })

    expect(applyApiErrors(error, setError, noFields)).toBe(
      'Your session needs refreshing. Reload the page and try again.',
    )
  })

  it('keeps other 403 detail messages', () => {
    const error = new ApiError(403, { detail: 'You do not have permission.' })

    expect(applyApiErrors(error, setError, noFields)).toBe('You do not have permission.')
  })
})
