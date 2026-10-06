import { describe, expect, it } from 'vitest'
import { ApiError } from './client'
import { getApiErrorMap, getFallbackErrorMessage } from './errors'

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
