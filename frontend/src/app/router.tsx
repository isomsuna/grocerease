import { createBrowserRouter } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppLayout from '../layouts/AppLayout'
import { apiRequest } from '../lib/api/client'
import NotFoundPage from '../pages/NotFoundPage'

type HealthResponse = {
  status: string
}

function HomePage() {
  const health = useQuery({
    queryKey: ['api-health'],
    queryFn: () => apiRequest<HealthResponse>('/health/'),
  })

  return (
    <section aria-labelledby="welcome-title" className="welcome">
      <p className="eyebrow">GrocerEase</p>
      <h1 id="welcome-title">Your grocery planning starts here.</h1>
      <p>
        Record shopping sessions, learn from your price history, and plan your
        next trip around your budget.
      </p>
      <p aria-live="polite" className="api-health">
        Backend API:{' '}
        {health.isPending
          ? 'checking…'
          : health.isError
            ? 'unavailable'
            : health.data.status}
      </p>
    </section>
  )
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
