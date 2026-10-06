import type { ReactNode } from 'react'

/** Full-page placeholder for session checks and blocking failures. */
export function StatusScreen({ children }: { children: ReactNode }) {
  return <main className="status-screen">{children}</main>
}
