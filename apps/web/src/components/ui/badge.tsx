import * as React from 'react'
import { cn } from '@lib/utils'

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'outline' | 'secondary'
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span 
      className={cn(
        'inline-flex items-center rounded-md border px-2 py-0.5 text-xs',
        variant === 'outline' && 'border-border',
        variant === 'secondary' && 'bg-muted text-muted-foreground border-muted',
        className
      )} 
      {...props} 
    />
  )
}
