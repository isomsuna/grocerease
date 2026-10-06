import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation } from 'react-router-dom'
import { Button } from '../../../components/ui/Button'
import { FormAlert } from '../../../components/ui/FormAlert'
import { TextField } from '../../../components/ui/TextField'
import { applyApiErrors } from '../../../lib/api/errors'
import { AuthCard } from '../components/AuthCard'
import { SessionCheckFailedError, SessionNotEstablishedError, useRegister } from '../hooks'
import { registerSchema, type RegisterValues } from '../schemas'

export default function RegisterPage() {
  const location = useLocation()
  const registerAccount = useRegister()
  const [formError, setFormError] = useState<string | null>(null)
  const [accountCreated, setAccountCreated] = useState(false)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { display_name: '', email: '', password: '', confirm_password: '' },
  })

  // Registration starts a session; PublicOnlyRoute then enters the app.
  const onSubmit = handleSubmit(async ({ display_name, email, password }) => {
    setFormError(null)
    try {
      await registerAccount.mutateAsync({ display_name, email, password })
    } catch (error) {
      // The account exists now, so resubmitting would only report a
      // duplicate email; send the shopper to log in instead.
      if (
        error instanceof SessionNotEstablishedError ||
        error instanceof SessionCheckFailedError
      ) {
        setAccountCreated(true)
      } else {
        setFormError(
          applyApiErrors(error, setError, ['display_name', 'email', 'password']),
        )
      }
    }
  })

  if (accountCreated) {
    return (
      <AuthCard title="Account created">
        <FormAlert tone="success">
          Your account is ready, but we couldn't finish signing you in. Log in to
          continue.
        </FormAlert>
        <Link className="btn btn-primary btn-lg btn-block" to="/login" state={location.state}>
          Log in
        </Link>
      </AuthCard>
    )
  }

  return (
    <AuthCard
      title="Create your account"
      description="Keep your grocery history, prices, and plans private to you."
      footer={
        <p>
          Already have an account?{' '}
          <Link to="/login" state={location.state}>
            Log in
          </Link>
        </p>
      }
    >
      <form className="auth-form" noValidate onSubmit={onSubmit}>
        {formError && <FormAlert>{formError}</FormAlert>}
        <TextField
          label="Display name"
          autoComplete="nickname"
          error={errors.display_name?.message}
          {...register('display_name')}
        />
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
          autoComplete="new-password"
          error={errors.password?.message}
          {...register('password')}
        />
        <TextField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          error={errors.confirm_password?.message}
          {...register('confirm_password')}
        />
        <Button type="submit" size="lg" block disabled={isSubmitting}>
          {isSubmitting ? 'Creating account…' : 'Create account'}
        </Button>
      </form>
    </AuthCard>
  )
}
