import type { ReactNode } from 'react'

type AuthCardProps = {
  title: string
  description?: ReactNode
  footer?: ReactNode
  children: ReactNode
}

export function AuthCard({ title, description, footer, children }: AuthCardProps) {
  return (
    <section className="card auth-card" aria-labelledby="auth-title">
      <h1 className="auth-title" id="auth-title">
        {title}
      </h1>
      {description && <p className="auth-description">{description}</p>}
      {children}
      {footer && <div className="auth-footer">{footer}</div>}
    </section>
  )
}
