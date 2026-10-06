import { Outlet } from 'react-router-dom'
import { Logo } from '../components/ui/Logo'

export default function AuthLayout() {
  return (
    <div className="auth-layout">
      <header className="auth-brand">
        <Logo />
      </header>
      <main className="auth-main">
        <Outlet />
      </main>
      <p className="auth-tagline">
        GrocerEase remembers what you bought and what you paid.
      </p>
    </div>
  )
}
