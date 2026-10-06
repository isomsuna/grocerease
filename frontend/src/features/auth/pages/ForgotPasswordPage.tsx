import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { Button } from '../../../components/ui/Button'
import { FormAlert } from '../../../components/ui/FormAlert'
import { TextField } from '../../../components/ui/TextField'
import { applyApiErrors } from '../../../lib/api/errors'
import { AuthCard } from '../components/AuthCard'
import { useRequestPasswordReset } from '../hooks'
import { forgotPasswordSchema, type ForgotPasswordValues } from '../schemas'

const backToLogin = (
  <p>
    Remembered it? <Link to="/login">Back to log in</Link>
  </p>
)

export default function ForgotPasswordPage() {
  const requestReset = useRequestPasswordReset()
  const [formError, setFormError] = useState<string | null>(null)
  const [sentTo, setSentTo] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  })

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await requestReset.mutateAsync(values)
      setSentTo(values.email)
    } catch (error) {
      setFormError(applyApiErrors(error, setError, ['email']))
    }
  })

  if (sentTo) {
    // The API answers the same way whether or not the account exists.
    return (
      <AuthCard title="Check your email" footer={backToLogin}>
        <FormAlert tone="success">
          If an account exists for <strong>{sentTo}</strong>, we've sent a link to
          reset your password.
        </FormAlert>
      </AuthCard>
    )
  }

  return (
    <AuthCard
      title="Reset your password"
      description="Enter the email you use for GrocerEase and we'll send you a reset link."
      footer={backToLogin}
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
        <Button type="submit" size="lg" block disabled={isSubmitting}>
          {isSubmitting ? 'Sending link…' : 'Send reset link'}
        </Button>
      </form>
    </AuthCard>
  )
}
