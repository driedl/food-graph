import { Outlet, createRootRoute } from '@tanstack/react-router'
import React from 'react'

// App-wide shell (header etc.) already lives in App.tsx; keep root minimal for now
export const Route = createRootRoute({
  component: () => {
    console.log('Root route rendering...')
    return <Outlet />
  },
})
