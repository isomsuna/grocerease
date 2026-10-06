import { z } from 'zod'

// Client checks cover required fields, email shape, and confirmation only.
// The password policy belongs to Django; its errors are shown from the API.

const email = z
  .string()
  .trim()
  .min(1, { error: 'Enter your email address.' })
  .pipe(z.email({ error: 'Enter a valid email address.' }))

const requiredPassword = z.string().min(1, { error: 'Enter your password.' })

const newPassword = z.string().min(1, { error: 'Enter a password.' })

const confirmPassword = z.string().min(1, { error: 'Confirm your password.' })

const PASSWORD_MISMATCH = "Passwords don't match."

export const loginSchema = z.object({
  email,
  password: requiredPassword,
})

export const registerSchema = z
  .object({
    display_name: z
      .string()
      .trim()
      .min(1, { error: 'Enter your display name.' })
      .max(150, { error: 'Use 150 characters or fewer.' }),
    email,
    password: newPassword,
    confirm_password: confirmPassword,
  })
  .refine((values) => values.password === values.confirm_password, {
    error: PASSWORD_MISMATCH,
    path: ['confirm_password'],
  })

export const forgotPasswordSchema = z.object({ email })

export const resetPasswordSchema = z
  .object({
    password: newPassword,
    confirm_password: confirmPassword,
  })
  .refine((values) => values.password === values.confirm_password, {
    error: PASSWORD_MISMATCH,
    path: ['confirm_password'],
  })

export type LoginValues = z.infer<typeof loginSchema>
export type RegisterValues = z.infer<typeof registerSchema>
export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>
