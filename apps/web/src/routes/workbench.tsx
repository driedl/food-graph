import { Outlet, createFileRoute } from '@tanstack/react-router'
import React from 'react'

// Layout for /workbench and its children
export const Route = createFileRoute('/workbench')({
  component: () => <Outlet />,
})
