import { useQuery } from '@tanstack/react-query'
import { useCurrentUser } from '../features/auth/hooks'
import { apiRequest } from '../lib/api/client'

type HealthResponse = {
  status: string
}

export default function HomePage() {
  const { data: user } = useCurrentUser()
  const health = useQuery({
    queryKey: ['api-health'],
    queryFn: () => apiRequest<HealthResponse>('/health/'),
  })

  return (
    <section aria-labelledby="welcome-title" className="welcome">
      <p className="eyebrow">GrocerEase</p>
      <h1 id="welcome-title">
        {user ? `Welcome, ${user.display_name}.` : 'Welcome.'}
      </h1>
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
