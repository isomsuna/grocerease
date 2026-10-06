import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { Button } from '../../../components/ui/Button'
import { StatusScreen } from '../../../components/ui/StatusScreen'
import { useCurrentUser } from '../hooks'

/** Renders private routes only after `/api/me/` confirms a session. */
export function RequireAuth() {
  const location = useLocation()
  const { data: user, isPending, isError, isFetching, refetch } = useCurrentUser()

  if (user) {
    return <Outlet />
  }

  if (isPending) {
    return (
      <StatusScreen>
        <p role="status">Checking your session…</p>
      </StatusScreen>
    )
  }

  if (isError) {
    return (
      <StatusScreen>
        <div role="alert">
          <h1>We couldn't check your session</h1>
          <p>GrocerEase is having trouble reaching the server. Please try again.</p>
        </div>
        <Button disabled={isFetching} onClick={() => void refetch()}>
          {isFetching ? 'Trying again…' : 'Try again'}
        </Button>
      </StatusScreen>
    )
  }

  const from = `${location.pathname}${location.search}${location.hash}`
  return <Navigate to="/login" replace state={{ from }} />
}
