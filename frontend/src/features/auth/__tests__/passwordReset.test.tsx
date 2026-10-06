import { cleanup, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { alex, createFakeApi } from '../../../test/fakeApi'
import { renderApp } from '../../../test/renderApp'
import { currentUserQueryKey } from '../session'

const RESET_PATH = '/reset-password?uid=MQ&token=c3x0-abc123'

describe('forgot password', () => {
  it('validates the email before sending a reset request', async () => {
    const api = createFakeApi()
    const { user } = renderApp('/forgot-password')

    await user.click(await screen.findByRole('button', { name: 'Send reset link' }))
    expect(await screen.findByText('Enter your email address.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Email'), 'alex@')
    await user.click(screen.getByRole('button', { name: 'Send reset link' }))
    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
    expect(api.requests('POST /auth/password-reset/')).toHaveLength(0)
  })

  it('requests a reset link and shows a neutral confirmation', async () => {
    const api = createFakeApi()
    const { user } = renderApp('/forgot-password')

    await user.type(await screen.findByLabelText('Email'), 'alex@example.com')
    await user.click(screen.getByRole('button', { name: 'Send reset link' }))

    expect(await screen.findByRole('status')).toHaveTextContent(
      "If an account exists for alex@example.com, we'll send a link to reset your password.",
    )
    expect(api.requests('POST /auth/password-reset/')[0].body).toEqual({
      email: 'alex@example.com',
    })
  })

  it('keeps the email and explains when the request is throttled', async () => {
    const api = createFakeApi()
    api.on('POST /auth/password-reset/', { status: 429 })
    const { user } = renderApp('/forgot-password')

    await user.type(await screen.findByLabelText('Email'), 'alex@example.com')
    await user.click(screen.getByRole('button', { name: 'Send reset link' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Too many attempts.')
    expect(screen.getByLabelText('Email')).toHaveValue('alex@example.com')
  })
})

describe('reset password', () => {
  it('explains when the link is missing its uid or token', async () => {
    const api = createFakeApi()
    renderApp('/reset-password?uid=MQ')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This reset link is invalid or has expired.',
    )
    expect(screen.getByRole('link', { name: 'Request a new link' })).toHaveAttribute(
      'href',
      '/forgot-password',
    )
    expect(screen.queryByLabelText('New password')).not.toBeInTheDocument()
    expect(api.calls).toHaveLength(0)
  })

  it('requires matching passwords before submitting', async () => {
    const api = createFakeApi()
    const { user } = renderApp(RESET_PATH)

    await user.type(await screen.findByLabelText('New password'), 'correct horse battery')
    await user.type(screen.getByLabelText('Confirm new password'), 'correct horse')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    expect(await screen.findByText("Passwords don't match.")).toBeInTheDocument()
    expect(api.requests('POST /auth/password-reset/confirm/')).toHaveLength(0)
  })

  it('removes the uid and token from the address bar but still uses them', async () => {
    const api = createFakeApi()
    const { location, router, user } = renderApp(RESET_PATH)

    await waitFor(() => expect(location()).toBe('/reset-password'))
    expect(router.state.historyAction).toBe('REPLACE')

    await user.type(screen.getByLabelText('New password'), 'correct horse battery')
    await user.type(screen.getByLabelText('Confirm new password'), 'correct horse battery')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    await screen.findByRole('status')
    expect(api.requests('POST /auth/password-reset/confirm/')[0].body).toMatchObject({
      uid: 'MQ',
      token: 'c3x0-abc123',
    })
  })

  it('keeps the link for a reload of this tab and forgets it after the reset', async () => {
    const api = createFakeApi()
    const first = renderApp(RESET_PATH)
    await waitFor(() => expect(first.location()).toBe('/reset-password'))
    cleanup()

    const { user } = renderApp('/reset-password')
    await user.type(await screen.findByLabelText('New password'), 'correct horse battery')
    await user.type(screen.getByLabelText('Confirm new password'), 'correct horse battery')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    await screen.findByRole('status')
    expect(api.requests('POST /auth/password-reset/confirm/')[0].body).toMatchObject({
      uid: 'MQ',
      token: 'c3x0-abc123',
    })
    expect(sessionStorage.length).toBe(0)
    cleanup()

    renderApp('/reset-password')
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This reset link is invalid or has expired.',
    )
  })

  it('shows the invalid-link message when the page opens without a link', async () => {
    createFakeApi()
    renderApp('/reset-password')

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This reset link is invalid or has expired.',
    )
    expect(screen.queryByLabelText('New password')).not.toBeInTheDocument()
  })

  it('submits the uid, token, and new password, then points to login', async () => {
    const api = createFakeApi()
    const { user } = renderApp(RESET_PATH)

    await user.type(await screen.findByLabelText('New password'), 'correct horse battery')
    await user.type(screen.getByLabelText('Confirm new password'), 'correct horse battery')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Your password has been reset.')
    expect(screen.getByRole('link', { name: 'Log in' })).toHaveAttribute('href', '/login')
    expect(api.requests('POST /auth/password-reset/confirm/')[0].body).toEqual({
      uid: 'MQ',
      token: 'c3x0-abc123',
      new_password: 'correct horse battery',
    })
  })

  it('shows password-policy errors next to the password field', async () => {
    const api = createFakeApi()
    api.on('POST /auth/password-reset/confirm/', {
      status: 400,
      body: { new_password: ['This password is too common.'] },
    })
    const { user } = renderApp(RESET_PATH)

    await user.type(await screen.findByLabelText('New password'), 'password123')
    await user.type(screen.getByLabelText('Confirm new password'), 'password123')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    expect(await screen.findByText('This password is too common.')).toBeInTheDocument()
    expect(screen.getByLabelText('New password')).toHaveAccessibleDescription(
      'This password is too common.',
    )
    expect(screen.getByLabelText('New password')).toHaveValue('password123')
  })

  it.each([
    ['a token field error', { token: ['This field may not be blank.'] }],
    ['a detail message', { detail: 'The reset link is invalid or expired.' }],
  ])('explains a bad link reported as %s', async (_label, body) => {
    const api = createFakeApi()
    api.on('POST /auth/password-reset/confirm/', { status: 400, body })
    const { user } = renderApp(RESET_PATH)

    await user.type(await screen.findByLabelText('New password'), 'correct horse battery')
    await user.type(screen.getByLabelText('Confirm new password'), 'correct horse battery')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This reset link is invalid or has expired.',
    )
    expect(screen.getByRole('link', { name: 'Request a new link' })).toBeInTheDocument()
  })

  it('drops any cached session after a successful reset', async () => {
    createFakeApi({ signedInAs: alex })
    const { queryClient, user } = renderApp(RESET_PATH)
    queryClient.setQueryData(currentUserQueryKey, alex)
    queryClient.setQueryData(['plans'], [{ id: 'plan-1' }])

    await user.type(await screen.findByLabelText('New password'), 'correct horse battery')
    await user.type(screen.getByLabelText('Confirm new password'), 'correct horse battery')
    await user.click(screen.getByRole('button', { name: 'Reset password' }))

    await screen.findByRole('status')
    expect(queryClient.getQueryData(currentUserQueryKey)).toBeNull()
    expect(queryClient.getQueryData(['plans'])).toBeUndefined()
  })
})
