import { screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { createFakeApi } from '../../../test/fakeApi'
import { renderApp } from '../../../test/renderApp'

async function fillRegistration(
  user: ReturnType<typeof renderApp>['user'],
  values: Partial<Record<'name' | 'email' | 'password' | 'confirm', string>> = {},
) {
  const {
    name = 'Alex',
    email = 'alex@example.com',
    password = 'correct horse battery',
    confirm = password,
  } = values
  if (name) await user.type(screen.getByLabelText('Display name'), name)
  if (email) await user.type(screen.getByLabelText('Email'), email)
  if (password) await user.type(screen.getByLabelText('Password'), password)
  if (confirm) await user.type(screen.getByLabelText('Confirm password'), confirm)
}

describe('registration', () => {
  it('requires every field before contacting the API', async () => {
    const api = createFakeApi()
    const { user } = renderApp('/register')

    await user.click(await screen.findByRole('button', { name: 'Create account' }))

    expect(await screen.findByText('Enter your display name.')).toBeInTheDocument()
    expect(screen.getByText('Enter your email address.')).toBeInTheDocument()
    expect(screen.getByText('Enter a password.')).toBeInTheDocument()
    expect(screen.getByText('Confirm your password.')).toBeInTheDocument()
    expect(screen.getByLabelText('Display name')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Display name')).toHaveFocus()
    expect(api.requests('POST /auth/register/')).toHaveLength(0)
  })

  it('rejects an invalid email and mismatched passwords on the client', async () => {
    const api = createFakeApi()
    const { user } = renderApp('/register')
    await screen.findByRole('heading', { name: 'Create your account' })

    await fillRegistration(user, {
      email: 'alex@example',
      password: 'correct horse battery',
      confirm: 'correct horse staple',
    })
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
    expect(screen.getByText("Passwords don't match.")).toBeInTheDocument()
    expect(screen.getByLabelText('Confirm password')).toHaveAccessibleDescription(
      "Passwords don't match.",
    )
    expect(api.requests('POST /auth/register/')).toHaveLength(0)
  })

  it('registers, loads /api/me/, and enters the application', async () => {
    const api = createFakeApi()
    const { user, location } = renderApp('/register')
    await screen.findByRole('heading', { name: 'Create your account' })

    await fillRegistration(user, { name: '  Alex  ', email: ' Alex@Example.com ' })
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('heading', { name: 'Welcome, Alex.' })).toBeInTheDocument()
    expect(location()).toBe('/')
    expect(screen.getByText(/Signed in as/)).toHaveTextContent('Signed in as Alex')

    const [request] = api.requests('POST /auth/register/')
    expect(request.body).toEqual({
      display_name: 'Alex',
      email: 'Alex@Example.com',
      password: 'correct horse battery',
    })
    expect(request.headers.get('X-CSRFToken')).toBe('csrf-from-bootstrap')
    // The session comes from the server, not from the registration response.
    const registerIndex = api.calls.indexOf(request)
    expect(
      api.calls.slice(registerIndex).some((call) => call.method === 'GET' && call.path === '/me/'),
    ).toBe(true)
  })

  it('shows backend field and form errors and keeps the entered values', async () => {
    const api = createFakeApi()
    api.on('POST /auth/register/', {
      status: 400,
      body: {
        errors: {
          email: ['An account with this email already exists.'],
          password: ['This password is too common.', 'This password is entirely numeric.'],
          non_field_errors: ['Please review the highlighted fields.'],
        },
      },
    })
    const { user, location } = renderApp('/register')
    await screen.findByRole('heading', { name: 'Create your account' })

    await fillRegistration(user, { password: '12345678' })
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(
      await screen.findByText('An account with this email already exists.'),
    ).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toHaveAccessibleDescription(
      'This password is too common. This password is entirely numeric.',
    )
    expect(screen.getByRole('alert')).toHaveTextContent('Please review the highlighted fields.')
    expect(screen.getByLabelText('Email')).toHaveFocus()

    expect(screen.getByLabelText('Display name')).toHaveValue('Alex')
    expect(screen.getByLabelText('Email')).toHaveValue('alex@example.com')
    expect(screen.getByLabelText('Password')).toHaveValue('12345678')
    expect(screen.getByLabelText('Confirm password')).toHaveValue('12345678')
    expect(location()).toBe('/register')
  })

  it('reads DRF default validation bodies', async () => {
    const api = createFakeApi()
    api.on('POST /auth/register/', {
      status: 400,
      body: { password: ['This password is too short. It must contain at least 8 characters.'] },
    })
    const { user } = renderApp('/register')
    await screen.findByRole('heading', { name: 'Create your account' })

    await fillRegistration(user, { password: 'short' })
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByText(/too short/)).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toHaveAccessibleDescription(/too short/)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('keeps the form when the server fails unexpectedly', async () => {
    const api = createFakeApi()
    api.on('POST /auth/register/', { status: 500 })
    const { user } = renderApp('/register')
    await screen.findByRole('heading', { name: 'Create your account' })

    await fillRegistration(user)
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    const alert = await screen.findByRole('alert')
    expect(within(alert).getByText(/something went wrong on our side/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toHaveValue('alex@example.com')
    expect(screen.getByRole('button', { name: 'Create account' })).toBeEnabled()
  })

  it('retries a failed session check after registering', async () => {
    const api = createFakeApi()
    let meFailures = 0
    api.on('POST /auth/register/', ({ body }) => {
      const { display_name, email } = body as Record<string, string>
      const created = { id: 2, display_name, email }
      api.on('GET /me/', () => (meFailures++ === 0 ? { status: 503 } : { body: created }))
      return { status: 201, body: created }
    })
    const { user, location } = renderApp('/register')
    await screen.findByRole('heading', { name: 'Create your account' })

    await fillRegistration(user)
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('heading', { name: 'Welcome, Alex.' })).toBeInTheDocument()
    expect(location()).toBe('/')
    expect(api.requests('POST /auth/register/')).toHaveLength(1)
  })

  it('does not offer to resubmit when the account was created but the session check fails', async () => {
    const api = createFakeApi()
    api.on('POST /auth/register/', () => {
      api.on('GET /me/', { status: 503 })
      return { status: 201, body: { id: 2, display_name: 'Alex', email: 'alex@example.com' } }
    })
    const { user } = renderApp('/register')
    await screen.findByRole('heading', { name: 'Create your account' })

    await fillRegistration(user)
    await user.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByRole('heading', { name: 'Account created' })).toBeInTheDocument()
    expect(screen.getByRole('status')).toHaveTextContent("couldn't finish signing you in")
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login')
    expect(screen.queryByRole('button', { name: 'Create account' })).not.toBeInTheDocument()
    expect(api.requests('GET /me/').length).toBeGreaterThanOrEqual(2)
  })
})
