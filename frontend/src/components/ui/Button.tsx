import type { ButtonHTMLAttributes } from 'react'

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'ghost'
  size?: 'md' | 'lg'
  block?: boolean
}

export function Button({
  variant = 'primary',
  size = 'md',
  block = false,
  className,
  type = 'button',
  ...props
}: ButtonProps) {
  const classes = ['btn', `btn-${variant}`, `btn-${size}`, block && 'btn-block', className]
    .filter(Boolean)
    .join(' ')

  return <button className={classes} type={type} {...props} />
}
