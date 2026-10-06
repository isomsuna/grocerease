import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation } from 'react-router-dom'
import { Button } from '../../../components/ui/Button'
import { FormAlert } from '../../../components/ui/FormAlert'
import { TextField } from '../../../components/ui/TextField'
import { applyApiErrors } from '../../../lib/api/errors'
import { AuthCard } from '../components/AuthCard'
import { SessionCheckFailedError, SessionNotEstablishedError, useLogin } from '../hooks'
import { loginSchema, type LoginValues } from '../schemas'

const SESSION_CHECK_FAILED =
  "You're logged in, but we couldn't load your account. Check your connection and log in again."
const SESSION_NOT_STARTED =
  "You were signed in, but your browser didn't keep the session. Check that cookies are allowed and try again."

export default function LoginPage() {
  const location = useLocation()
  const login = useLogin()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  })

  // A successful login refreshes the current user; PublicOnlyRoute then
  // redirects to the originally requested page.
  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await login.mutateAsync(values)
    } catch (error) {
      if (error instanceof SessionNotEstablishedError) {
        setFormError(SESSION_NOT_STARTED)
      } else if (error instanceof SessionCheckFailedError) {
        setFormError(SESSION_CHECK_FAILED)
      } else {
        setFormError(applyApiErrors(error, setError, ['email', 'password']))
      }
    }
  })

  return (
    <AuthCard
      title="Welcome back"
      description="Log in to plan your next grocery trip."
      footer={
        <p>
          New to GrocerEase?{' '}
          <Link to="/register" state={location.state}>
            Create an account
          </Link>
        </p>
      }
    >
      <form className="auth-form" noValidate onSubmit={onSubmit}>
        {formError && <FormAlert>{formError}</FormAlert>}
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          error={errors.email?.message}
          {...register('email')}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          error={errors.password?.message}
          {...register('password')}
        />
        <p className="auth-inline-link">
          <Link to="/forgot-password">Forgot password?</Link>
        </p>
        <Button type="submit" size="lg" block disabled={isSubmitting}>
          {isSubmitting ? 'Logging in…' : 'Log in'}
        </Button>
      </form>
    </AuthCard>
  )
}
