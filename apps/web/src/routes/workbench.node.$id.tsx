import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

// ID-first form: /workbench/node/<taxonId> (optionally extend later for /part/tx)
export const Route = createFileRoute('/workbench/node/$id')({
  component: () => null,
})
