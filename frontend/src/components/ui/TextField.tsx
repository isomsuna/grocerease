import { useId, type InputHTMLAttributes, type Ref } from 'react'

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string
  error?: string
  hint?: string
  ref?: Ref<HTMLInputElement>
}

export function TextField({ label, error, hint, id, ...inputProps }: TextFieldProps) {
  const generatedId = useId()
  const inputId = id ?? generatedId
  const hintId = hint ? `${inputId}-hint` : undefined
  const errorId = error ? `${inputId}-error` : undefined
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className="field">
      <label className="field-label" htmlFor={inputId}>
        {label}
      </label>
      <input
        className="input"
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        {...inputProps}
      />
      {hint && (
        <p className="field-msg" id={hintId}>
          {hint}
        </p>
      )}
      {error && (
        <p className="field-msg field-msg-error" id={errorId}>
          {error}
        </p>
      )}
    </div>
  )
}
