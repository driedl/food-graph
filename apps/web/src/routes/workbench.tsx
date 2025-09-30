import { createFileRoute } from '@tanstack/react-router'
import React from 'react'
import App from '@/App'

// Layout for /workbench and its children
export const Route = createFileRoute('/workbench')({
  component: () => <App />,
})
