import { createFileRoute, redirect } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'

// FS resolver: /workbench/fs/<fsString> → parse and redirect to appropriate entity route
export const Route = createFileRoute('/workbench/fs/$')({
  beforeLoad: async ({ params }) => {
    const fsString = decodeURIComponent(params._splat)
    const fullFs = fsString.startsWith('fs:/') ? fsString : `fs:/${fsString}`

    try {
      // Parse the FS string using the API
      const parseResult = await trpc.foodstate.parse.query({ fs: fullFs })

      if (parseResult.taxonPath && parseResult.taxonPath.length > 0) {
        const kingdoms = ['plantae', 'animalia', 'fungi']
        const kingdomIndex = parseResult.taxonPath.findIndex((slug: string) => kingdoms.includes(slug))

        if (kingdomIndex >= 0) {
          const taxonomicPath = parseResult.taxonPath.slice(kingdomIndex)
          const taxonId = 'tx:' + taxonomicPath.join(':')

          if (parseResult.partId) {
            // Navigate to TP page
            throw redirect({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId: parseResult.partId } })
          } else {
            // Navigate to taxon page
            throw redirect({ to: '/workbench/taxon/$id', params: { id: taxonId } })
          }
        } else {
          console.warn('[FS Parser] No kingdom found in path:', parseResult.taxonPath)
        }
      }

      // If parsing fails or no taxon path, redirect to root
      throw redirect({ to: '/workbench' })
    } catch (error) {
      console.error('Failed to parse FS string:', error)
      // If parsing fails, redirect to root
      throw redirect({ to: '/workbench' })
    }
  },
  component: () => null,
})
