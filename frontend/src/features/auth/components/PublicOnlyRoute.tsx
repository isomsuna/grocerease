import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { StatusScreen } from '../../../components/ui/StatusScreen'
import { useCurrentUser } from '../hooks'
import { getReturnTo } from '../redirect'

/**
 * Login and registration are for signed-out shoppers. Once `/api/me/` reports
 * a session (on arrival or after submitting), continue into the app.
 */
export function PublicOnlyRoute() {
  const location = useLocation()
  const { data: user, isPending } = useCurrentUser()

  if (user) {
    return <Navigate to={getReturnTo(location.state)} replace />
  }

  if (isPending) {
    return (
      <StatusScreen>
        <p role="status">Checking your session…</p>
      </StatusScreen>
    )
  }

  return <Outlet />
}
