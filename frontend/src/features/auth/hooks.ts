import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { isApiError } from '../../lib/api/client'
import * as authApi from './api'
import {
  clearPrivateState,
  currentUserQueryOptions,
  loadSessionUser,
} from './session'
import type { CurrentUser } from './types'

export class SessionNotEstablishedError extends Error {
  constructor() {
    super('The API accepted the request but did not start a session.')
    this.name = 'SessionNotEstablishedError'
  }
}

/** The login/registration succeeded, but `/api/me/` could not be loaded. */
export class SessionCheckFailedError extends Error {
  constructor(cause: unknown) {
    super('The request succeeded but the session check failed.', { cause })
    this.name = 'SessionCheckFailedError'
  }
}

async function confirmSession(queryClient: QueryClient): Promise<CurrentUser> {
  let user: CurrentUser | null
  try {
    user = await loadSessionUser(queryClient)
  } catch (error) {
    throw new SessionCheckFailedError(error)
  }
  if (!user) {
    throw new SessionNotEstablishedError()
  }
  return user
}

export function useCurrentUser() {
  return useQuery(currentUserQueryOptions)
}

/**
 * Logs in, then confirms the session through `/api/me/`. Route guards react
 * to the refreshed current user, so this hook never navigates on its own.
 */
export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: authApi.LoginRequest) => {
      await authApi.login(data)
      return confirmSession(queryClient)
    },
  })
}

export function useRegister() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: authApi.RegisterRequest) => {
      await authApi.register(data)
      return confirmSession(queryClient)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  return useMutation({
    mutationFn: async () => {
      try {
        await authApi.logout()
      } catch (error) {
        // An expired session is already logged out on the server.
        if (!isApiError(error, 401)) {
          throw error
        }
      }
    },
    onSuccess: () => {
      // Commit the navigation synchronously (not as a transition) so private
      // routes unmount before the cleared session reaches RequireAuth, which
      // would otherwise redirect with a "return to" location.
      void navigate('/login', { replace: true, flushSync: true })
      clearPrivateState(queryClient)
    },
  })
}

export function useRequestPasswordReset() {
  return useMutation({ mutationFn: authApi.requestPasswordReset })
}

export function useConfirmPasswordReset() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: authApi.confirmPasswordReset,
    // Django invalidates existing sessions when the password changes.
    onSuccess: () => clearPrivateState(queryClient),
  })
}
