import * as React from 'react'
import { cn } from '@lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'secondary'
  size?: 'sm' | 'default'
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        'inline-flex items-center justify-center rounded-md font-medium',
        size === 'sm' && 'px-2 py-1 text-xs',
        size === 'default' && 'px-3 py-2 text-sm',
        variant === 'default' && 'bg-black text-white hover:opacity-90',
        variant === 'outline' && 'border border-border bg-background hover:bg-muted',
        variant === 'secondary' && 'bg-muted text-muted-foreground hover:bg-muted/80',
        'disabled:opacity-50',
        className
      )}
      {...props}
    />
  )
)
Button.displayName = 'Button'
