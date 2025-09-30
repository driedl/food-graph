import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

// Catch-all route for FS URLs: /workbench/fs/<slug>/.../part:<partId>/tx:<id>{k=v}/...
// The $ creates a splat route that matches any path after /workbench/fs/
export const Route = createFileRoute('/workbench/fs/$')({
  component: () => null,
})
