import { Link, Outlet } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { FormAlert } from '../components/ui/FormAlert'
import { Logo } from '../components/ui/Logo'
import { useCurrentUser, useLogout } from '../features/auth/hooks'
import { getFallbackErrorMessage } from '../lib/api/errors'

// Minimal signed-in frame; the full navigation shell is FE-US-003.
export default function AppLayout() {
  const { data: user } = useCurrentUser()
  const logout = useLogout()

  return (
    <div className="app-frame">
      <header className="app-header">
        <Link to="/" aria-label="GrocerEase home" className="app-header-home">
          <Logo />
        </Link>
        <div className="app-header-user">
          {user && (
            <span className="app-header-name">
              Signed in as <strong>{user.display_name}</strong>
            </span>
          )}
          <Button
            variant="secondary"
            disabled={logout.isPending}
            onClick={() => logout.mutate()}
          >
            {logout.isPending ? 'Logging out…' : 'Log out'}
          </Button>
        </div>
      </header>
      {logout.isError && (
        <div className="app-layout">
          <FormAlert>
            {`We couldn't log you out. ${getFallbackErrorMessage(logout.error)}`}
          </FormAlert>
        </div>
      )}
      <main className="app-layout">
        <Outlet />
      </main>
    </div>
  )
}
