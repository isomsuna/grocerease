import {
  MutationCache,
  QueryCache,
  QueryClient,
  type DefaultOptions,
} from '@tanstack/react-query'
import { clearPrivateState, getCachedUser } from '../features/auth/session'
import { ApiError, isApiError } from './api/client'

const MAX_RETRIES = 1

export function createQueryClient(overrides: DefaultOptions = {}): QueryClient {
  // A 401 from any private request means the server session is gone: drop
  // private data and let the route guards send the shopper back to login.
  const handleError = (error: unknown) => {
    if (isApiError(error, 401) && getCachedUser(queryClient)) {
      clearPrivateState(queryClient)
    }
  }

  const queryClient: QueryClient = new QueryClient({
    queryCache: new QueryCache({ onError: handleError }),
    mutationCache: new MutationCache({ onError: handleError }),
    defaultOptions: {
      ...overrides,
      queries: {
        staleTime: 30_000,
        // Client errors will not succeed on retry; only retry server/network failures.
        retry: (failureCount, error) =>
          failureCount < MAX_RETRIES &&
          !(error instanceof ApiError && error.status < 500),
        refetchOnWindowFocus: false,
        ...overrides.queries,
      },
      mutations: { ...overrides.mutations },
    },
  })

  return queryClient
}

export const queryClient = createQueryClient()
