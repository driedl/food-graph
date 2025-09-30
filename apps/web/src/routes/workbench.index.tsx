import { createFileRoute } from '@tanstack/react-router'
import React from 'react'
import App from '@/App'

export const Route = createFileRoute('/workbench/')({
  component: () => <App />,
})
