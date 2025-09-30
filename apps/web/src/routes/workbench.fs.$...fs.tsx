import { createFileRoute } from '@tanstack/react-router'
import React from 'react'
import App from '@/App'

// Any FS form: /workbench/fs/<slug>/.../part:<partId>/tx:<id>{k=v}/...
export const Route = createFileRoute('/workbench/fs/$/fs')({
  component: () => <App />,
})
