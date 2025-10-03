import { createFileRoute } from '@tanstack/react-router'
import React from 'react'
import AppShell from '@/components/layout/AppShell'

// Layout for /workbench and its children
export const Route = createFileRoute('/workbench')({
  component: () => <AppShell />,
})
