import { createFileRoute, redirect } from '@tanstack/react-router'
import React from 'react'

// Legacy redirect: /workbench/node/<taxonId> → /workbench/taxon/<taxonId>
export const Route = createFileRoute('/workbench/node/$id')({
  beforeLoad: ({ params }) => {
    throw redirect({ to: '/workbench/taxon/$id', params: { id: params.id } })
  },
  component: () => null,
})
