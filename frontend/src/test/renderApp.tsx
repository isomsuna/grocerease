import { QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { routes } from '../app/router'
import { createQueryClient } from '../lib/queryClient'

/** Renders the real route tree and query client at `path`. */
export function renderApp(path = '/') {
  const queryClient = createQueryClient({ queries: { retry: false } })
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const user = userEvent.setup()

  render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )

  const location = () => {
    const { pathname, search, hash } = router.state.location
    return `${pathname}${search}${hash}`
  }

  return { queryClient, router, user, location }
}
