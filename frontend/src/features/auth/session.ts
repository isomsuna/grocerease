import { queryOptions, type Query, type QueryClient } from '@tanstack/react-query'
import { fetchCurrentUser } from './api'
import type { CurrentUser } from './types'

export const currentUserQueryKey = ['auth', 'me'] as const

/**
 * `/api/me/` is the only source of truth for who is signed in. `null` data
 * means the server reported no session; nothing else is cached client-side.
 */
export const currentUserQueryOptions = queryOptions({
  queryKey: currentUserQueryKey,
  queryFn: fetchCurrentUser,
  staleTime: 5 * 60_000,
})

function isCurrentUserQuery(query: Query): boolean {
  return (
    query.queryKey.length === currentUserQueryKey.length &&
    currentUserQueryKey.every((part, index) => query.queryKey[index] === part)
  )
}

export function getCachedUser(queryClient: QueryClient): CurrentUser | null | undefined {
  return queryClient.getQueryData(currentUserQueryKey)
}

/**
 * Drops every cached query and mutation, then marks the shopper as signed out
 * so route guards stop rendering private screens.
 */
export function clearPrivateState(queryClient: QueryClient): void {
  queryClient.removeQueries({ predicate: (query) => !isCurrentUserQuery(query) })
  queryClient.getMutationCache().clear()
  queryClient.setQueryData<CurrentUser | null>(currentUserQueryKey, null)
}

/** Loads the session from `/api/me/` after a login or registration request. */
export async function loadSessionUser(queryClient: QueryClient): Promise<CurrentUser | null> {
  return queryClient.fetchQuery({ ...currentUserQueryOptions, staleTime: 0 })
}
