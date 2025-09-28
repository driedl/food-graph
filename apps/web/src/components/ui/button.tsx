import * as React from 'react'
import { cn } from '@lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline'
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium',
        variant === 'default' && 'bg-black text-white hover:opacity-90',
        variant === 'outline' && 'border border-border bg-background hover:bg-muted',
        'disabled:opacity-50',
        className
      )}
      {...props}
    />
  )
)
Button.displayName = 'Button'
