const AUTH_ONLY_PATHS = ['/login', '/register']

export type ReturnToState = { from?: unknown } | null | undefined

/**
 * Picks where to send a shopper after login: the private route they were
 * bounced from, if it is a same-app path, otherwise the dashboard.
 */
export function getReturnTo(state: unknown): string {
  const from = (state as ReturnToState)?.from
  if (
    typeof from !== 'string' ||
    !from.startsWith('/') ||
    from.startsWith('//') ||
    from.startsWith('/\\')
  ) {
    return '/'
  }

  const pathname = from.split(/[?#]/, 1)[0]
  return AUTH_ONLY_PATHS.includes(pathname) ? '/' : from
}
