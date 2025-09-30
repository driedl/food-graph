import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/$')({
  component: () => (
    <div className="p-6 text-sm text-muted-foreground">
      404 · Route not found
    </div>
  ),
})
