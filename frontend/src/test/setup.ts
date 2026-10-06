import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterEach } from 'vitest'

// The default 1s for findBy*/waitFor is too tight for full-app flows (CSRF
// bootstrap, login, /api/me/, redirect) when the whole suite runs in parallel.
configure({ asyncUtilTimeout: 3000 })

afterEach(() => {
  cleanup()
  sessionStorage.clear()
  document.cookie = 'csrftoken=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/'
})
