import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'
import { ApiError } from './client'

const NETWORK_ERROR = "We couldn't reach GrocerEase. Check your connection and try again."
const SERVER_ERROR = 'Something went wrong on our side. Please try again.'
const RATE_LIMITED = 'Too many attempts. Please wait a moment and try again.'
const GENERIC_ERROR = "We couldn't complete that request. Please try again."

type ErrorMap = Record<string, string[]>

function toMessages(value: unknown): string[] {
  if (typeof value === 'string') {
    return [value]
  }
  if (Array.isArray(value)) {
    return value.flatMap(toMessages)
  }
  return []
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

// Envelope metadata, not field names.
const NON_FIELD_KEYS = new Set(['errors', 'detail', 'code'])

/**
 * Reads the spec's `{ "errors": { field: [...] } }` envelope, DRF's default
 * `{ field: [...] }` validation body, and DRF's `{ "detail": ... }` errors.
 */
export function getApiErrorMap(error: unknown): ErrorMap {
  if (!(error instanceof ApiError) || !isRecord(error.body)) {
    return {}
  }

  const body = error.body
  const fieldErrors = isRecord(body.errors)
    ? body.errors
    : Object.fromEntries(Object.entries(body).filter(([key]) => !NON_FIELD_KEYS.has(key)))
  const map: ErrorMap = {}

  for (const [key, value] of Object.entries(fieldErrors)) {
    const messages = toMessages(value)
    if (messages.length > 0) {
      map[key] = messages
    }
  }

  const detail = toMessages(body.detail)
  if (detail.length > 0) {
    map.non_field_errors = [...(map.non_field_errors ?? []), ...detail]
  }

  return map
}

/** A user-facing message for failures that carry no usable error payload. */
export function getFallbackErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return NETWORK_ERROR
  }
  if (error.status === 429) {
    return RATE_LIMITED
  }
  if (error.status >= 500) {
    return SERVER_ERROR
  }
  return GENERIC_ERROR
}

/**
 * Puts API field errors on matching form fields (or the field an API key is
 * aliased to) and returns the form-level message for everything else, or
 * `null` when every error belongs to a field.
 */
export function applyApiErrors<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: readonly Path<T>[],
  aliases: Readonly<Record<string, Path<T>>> = {},
): string | null {
  const errorMap = getApiErrorMap(error)
  const formMessages: string[] = []
  let focused = false

  for (const [key, messages] of Object.entries(errorMap)) {
    const field = Object.hasOwn(aliases, key)
      ? aliases[key]
      : fields.find((name) => name === key)
    if (field) {
      setError(field, { type: 'server', message: messages.join(' ') }, { shouldFocus: !focused })
      focused = true
    } else {
      formMessages.push(...messages)
    }
  }

  if (formMessages.length > 0) {
    return formMessages.join(' ')
  }
  return focused ? null : getFallbackErrorMessage(error)
}
