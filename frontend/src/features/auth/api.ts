import { apiPost, apiRequest, isApiError } from '../../lib/api/client'
import type { CurrentUser } from './types'

export type RegisterRequest = {
  display_name: string
  email: string
  password: string
}

export type LoginRequest = {
  email: string
  password: string
}

export type PasswordResetRequest = {
  email: string
}

export type PasswordResetConfirmRequest = {
  uid: string
  token: string
  new_password: string
}

/** Returns the signed-in shopper, or `null` when the API reports no session. */
export async function fetchCurrentUser(): Promise<CurrentUser | null> {
  try {
    return await apiRequest<CurrentUser>('/me/')
  } catch (error) {
    if (isApiError(error, 401)) {
      return null
    }
    throw error
  }
}

export function register(data: RegisterRequest): Promise<unknown> {
  return apiPost('/auth/register/', data)
}

export function login(data: LoginRequest): Promise<unknown> {
  return apiPost('/auth/login/', data)
}

export function logout(): Promise<unknown> {
  return apiPost('/auth/logout/')
}

export function requestPasswordReset(data: PasswordResetRequest): Promise<unknown> {
  return apiPost('/auth/password-reset/', data)
}

export function confirmPasswordReset(
  data: PasswordResetConfirmRequest,
): Promise<unknown> {
  return apiPost('/auth/password-reset/confirm/', data)
}
