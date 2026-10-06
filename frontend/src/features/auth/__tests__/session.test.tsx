import { act, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { apiRequest } from '../../../lib/api/client'
import { alex, createFakeApi } from '../../../test/fakeApi'
import { renderApp } from '../../../test/renderApp'
import { currentUserQueryKey } from '../session'

async function logIn(user: ReturnType<typeof renderApp>['user']) {
  await user.type(await screen.findByLabelText('Email'), 'alex@example.com')
  await user.type(screen.getByLabelText('Password'), 'correct horse battery')
  await user.click(screen.getByRole('button', { name: 'Log in' }))
}

describe('login', () => {
  it('validates required fields and email shape on the client', async () => {
    const api = createFakeApi()
    const { user } = renderApp('/login')

    await user.click(await screen.findByRole('button', { name: 'Log in' }))
    expect(await screen.findByText('Enter your email address.')).toBeInTheDocument()
    expect(screen.getByText('Enter your password.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Email'), 'not-an-email')
    await user.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
    expect(api.requests('POST /auth/login/')).toHaveLength(0)
  })

  it('logs in with email and password and confirms the session via /api/me/', async () => {
    const api = createFakeApi()
    const { user, location } = renderApp('/login')

    await logIn(user)

    expect(await screen.findByRole('heading', { name: 'Welcome, Alex.' })).toBeInTheDocument()
    expect(location()).toBe('/')
    const [request] = api.requests('POST /auth/login/')
    expect(request.body).toEqual({ email: 'alex@example.com', password: 'correct horse battery' })
    expect(request.headers.get('X-CSRFToken')).toBe('csrf-from-bootstrap')
    expect(api.requests('GET /auth/csrf/')).toHaveLength(1)
  })

  it('shows the backend error and keeps the entered credentials', async () => {
    const api = createFakeApi()
    api.on('POST /auth/login/', {
      status: 400,
      body: { errors: { non_field_errors: ['Unable to log in with the provided credentials.'] } },
    })
    const { user, location } = renderApp('/login')

    await logIn(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to log in with the provided credentials.',
    )
    expect(screen.getByLabelText('Email')).toHaveValue('alex@example.com')
    expect(screen.getByLabelText('Password')).toHaveValue('correct horse battery')
    expect(location()).toBe('/login')
  })

  it('shows the DRF detail message for rejected credentials', async () => {
    const api = createFakeApi()
    api.on('POST /auth/login/', {
      status: 400,
      body: { detail: 'Unable to log in with the supplied credentials.' },
    })
    const { user } = renderApp('/login')

    await logIn(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to log in with the supplied credentials.',
    )
    expect(screen.getByLabelText('Password')).toHaveValue('correct horse battery')
  })

  it('treats a bare 401 from login as invalid credentials', async () => {
    const api = createFakeApi()
    api.on('POST /auth/login/', { status: 401 })
    const { user } = renderApp('/login')

    await logIn(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Your email or password is incorrect.',
    )
  })

  it('reports a login that did not produce a session instead of entering the app', async () => {
    const api = createFakeApi()
    api.on('POST /auth/login/', { body: alex })
    const { user, location } = renderApp('/login')

    await logIn(user)

    expect(await screen.findByRole('alert')).toHaveTextContent(/didn't keep the session/)
    expect(location()).toBe('/login')
  })
})

describe('route protection', () => {
  it('sends signed-out visitors to /login and returns them to the requested page', async () => {
    createFakeApi()
    const { user, location } = renderApp('/history/42?tab=drafts#top')

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(location()).toBe('/login')
    expect(screen.queryByText(/Signed in as/)).not.toBeInTheDocument()

    await logIn(user)

    await waitFor(() => expect(location()).toBe('/history/42?tab=drafts#top'))
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeInTheDocument()
  })

  it('keeps the return path when switching from login to registration', async () => {
    createFakeApi()
    const { user, location } = renderApp('/plans')

    await user.click(await screen.findByRole('link', { name: 'Create an account' }))
    await user.type(screen.getByLabelText('Display name'), 'Sam')
    await user.type(screen.getByLabelText('Email'), 'sam@example.com')
    await user.type(screen.getByLabelText('Password'), 'correct horse battery')
    await user.type(screen.getByLabelText('Confirm password'), 'correct horse battery')
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    await waitFor(() => expect(location()).toBe('/plans'))
  })

  it.each(['/login', '/register'])('redirects signed-in shoppers from %s to /', async (path) => {
    createFakeApi({ signedInAs: alex })
    const { location } = renderApp(path)

    expect(await screen.findByRole('heading', { name: 'Welcome, Alex.' })).toBeInTheDocument()
    expect(location()).toBe('/')
  })

  it('leaves the password recovery pages public', async () => {
    createFakeApi()
    renderApp('/forgot-password')

    expect(
      await screen.findByRole('heading', { name: 'Reset your password' }),
    ).toBeInTheDocument()
  })

  it('offers a retry instead of a login redirect when the session check fails', async () => {
    const api = createFakeApi({ signedInAs: alex })
    api.on('GET /me/', { status: 503 })
    const { user, location } = renderApp('/')

    expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't check your session")
    expect(location()).toBe('/')

    api.on('GET /me/', { body: alex })
    await user.click(screen.getByRole('button', { name: 'Try again' }))

    expect(await screen.findByRole('heading', { name: 'Welcome, Alex.' })).toBeInTheDocument()
  })
})

describe('expired sessions', () => {
  it('clears private data and returns to login when a private request gets 401', async () => {
    const api = createFakeApi({ signedInAs: alex })
    const { queryClient, location, user } = renderApp('/products')
    await screen.findByRole('heading', { name: 'Page not found' })
    queryClient.setQueryData(['stores'], [{ id: 'store-1', name: 'Alex market' }])

    api.expireSession()
    api.on('GET /stores/', { status: 401, body: { detail: 'Session expired.' } })
    await queryClient
      .fetchQuery({ queryKey: ['stores', 'refresh'], queryFn: () => apiRequest('/stores/') })
      .catch(() => undefined)

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(location()).toBe('/login')
    expect(queryClient.getQueryData(['stores'])).toBeUndefined()
    expect(queryClient.getQueryData(currentUserQueryKey)).toBeNull()

    await logIn(user)
    await waitFor(() => expect(location()).toBe('/products'))
  })

  it('treats a 401 from /api/me/ on load as signed out', async () => {
    createFakeApi()
    const { location } = renderApp('/')

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(location()).toBe('/login')
  })
})

describe('logout', () => {
  it('logs out, clears every private query, and returns to login', async () => {
    const api = createFakeApi({ signedInAs: alex })
    const { queryClient, location, router, user } = renderApp('/')
    await screen.findByRole('heading', { name: 'Welcome, Alex.' })
    queryClient.setQueryData(['plans'], [{ id: 'plan-1', name: 'Weekly groceries' }])

    await user.click(screen.getByRole('button', { name: 'Log out' }))

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(location()).toBe('/login')
    expect(api.requests('POST /auth/logout/')).toHaveLength(1)
    expect(api.requests('POST /auth/logout/')[0].headers.get('X-CSRFToken')).toBeTruthy()

    const remaining = queryClient.getQueryCache().getAll()
    expect(remaining.map((query) => query.queryKey)).toEqual([currentUserQueryKey])
    expect(queryClient.getQueryData(currentUserQueryKey)).toBeNull()
    expect(queryClient.getMutationCache().getAll()).toHaveLength(0)
    expect(screen.queryByText(/Alex/)).not.toBeInTheDocument()

    // Returning to a private route must not render the cached shopper.
    await act(() => router.navigate('/'))
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(location()).toBe('/login')
    expect(screen.queryByText(/Alex/)).not.toBeInTheDocument()
  })

  it('does not return to the previous page on the next login', async () => {
    createFakeApi({ signedInAs: alex })
    const { location, user } = renderApp('/stores')
    await screen.findByRole('heading', { name: 'Page not found' })

    await user.click(screen.getByRole('button', { name: 'Log out' }))
    await screen.findByRole('heading', { name: 'Welcome back' })
    await logIn(user)

    await waitFor(() => expect(location()).toBe('/'))
  })

  it('finishes logging out locally when the server session had already expired', async () => {
    const api = createFakeApi({ signedInAs: alex })
    api.on('POST /auth/logout/', { status: 401 })
    const { location, user } = renderApp('/')
    await screen.findByRole('heading', { name: 'Welcome, Alex.' })

    await user.click(screen.getByRole('button', { name: 'Log out' }))

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(location()).toBe('/login')
  })

  it('stays signed in and explains when logout fails', async () => {
    const api = createFakeApi({ signedInAs: alex })
    api.on('POST /auth/logout/', { status: 500 })
    const { location, user } = renderApp('/')
    await screen.findByRole('heading', { name: 'Welcome, Alex.' })

    await user.click(screen.getByRole('button', { name: 'Log out' }))

    expect(await screen.findByRole('alert')).toHaveTextContent("We couldn't log you out.")
    expect(location()).toBe('/')
  })
})
