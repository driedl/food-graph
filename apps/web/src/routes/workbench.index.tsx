import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/workbench/')({
  // App is rendered by the parent; nothing to render here.
  component: () => null,
})
