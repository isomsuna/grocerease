import { zodResolver } from '@hookform/resolvers/zod'
import { useState, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { Button } from '../../../components/ui/Button'
import { FormAlert } from '../../../components/ui/FormAlert'
import { TextField } from '../../../components/ui/TextField'
import { isApiError } from '../../../lib/api/client'
import { applyApiErrors, getApiErrorMap } from '../../../lib/api/errors'
import { AuthCard } from '../components/AuthCard'
import { useConfirmPasswordReset } from '../hooks'
import { clearStoredResetLink, useResetLink } from '../resetLink'
import { resetPasswordSchema, type ResetPasswordValues } from '../schemas'

const invalidLinkMessage = (
  <>
    This reset link is invalid or has expired.{' '}
    <Link to="/forgot-password">Request a new link</Link>.
  </>
)

export default function ResetPasswordPage() {
  const resetLink = useResetLink()
  const confirmReset = useConfirmPasswordReset()
  const [formError, setFormError] = useState<ReactNode>(null)
  const [isComplete, setIsComplete] = useState(false)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: '', confirm_password: '' },
  })

  if (!resetLink) {
    return (
      <AuthCard title="Reset link not valid">
        <FormAlert>{invalidLinkMessage}</FormAlert>
      </AuthCard>
    )
  }

  if (isComplete) {
    return (
      <AuthCard title="Password updated">
        <FormAlert tone="success">
          Your password has been reset. Log in with your new password.
        </FormAlert>
        <Link className="btn btn-primary btn-lg btn-block" to="/login">
          Log in
        </Link>
      </AuthCard>
    )
  }

  const onSubmit = handleSubmit(async ({ password }) => {
    setFormError(null)
    try {
      await confirmReset.mutateAsync({ ...resetLink, new_password: password })
      clearStoredResetLink()
      setIsComplete(true)
    } catch (error) {
      // The API rejects a bad link as a uid/token field error or, once the
      // fields parse, as a 400 with only a non-field message.
      const errorMap = getApiErrorMap(error)
      const isBadLink =
        'uid' in errorMap ||
        'token' in errorMap ||
        (isApiError(error, 400) && 'non_field_errors' in errorMap && !('new_password' in errorMap))
      if (isBadLink) {
        clearStoredResetLink()
        setFormError(invalidLinkMessage)
        return
      }
      setFormError(applyApiErrors(error, setError, ['password'], { new_password: 'password' }))
    }
  })

  return (
    <AuthCard
      title="Choose a new password"
      description="Enter a new password for your GrocerEase account."
      footer={
        <p>
          <Link to="/login">Back to log in</Link>
        </p>
      }
    >
      <form className="auth-form" noValidate onSubmit={onSubmit}>
        {formError && <FormAlert>{formError}</FormAlert>}
        <TextField
          label="New password"
          type="password"
          autoComplete="new-password"
          error={errors.password?.message}
          {...register('password')}
        />
        <TextField
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          error={errors.confirm_password?.message}
          {...register('confirm_password')}
        />
        <Button type="submit" size="lg" block disabled={isSubmitting}>
          {isSubmitting ? 'Saving…' : 'Reset password'}
        </Button>
      </form>
    </AuthCard>
  )
}
