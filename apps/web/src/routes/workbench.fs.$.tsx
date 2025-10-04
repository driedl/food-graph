import { createFileRoute, useRouter } from '@tanstack/react-router'
import React, { useEffect } from 'react'
import { trpc } from '@/lib/trpc'

// FS resolver: /workbench/fs/<fsString> → parse and redirect to appropriate entity route
export const Route = createFileRoute('/workbench/fs/$')({
  component: FSResolver,
})

function FSResolver() {
  const router = useRouter()
  const { $: fsString } = Route.useParams()

  const fullFs = fsString ? (fsString.startsWith('fs:/') ? fsString : `fs:/${fsString}`) : ''

  const parse = trpc.foodstate.parse.useQuery({ fs: fullFs }, { enabled: !!fsString })

  // Handle invalid fsString
  useEffect(() => {
    if (!fsString) {
      router.navigate({ to: '/workbench' })
    }
  }, [fsString, router])

  useEffect(() => {
    if (parse.status === 'success' && parse.data) {
      const { taxonPath, partId } = parse.data

      if (taxonPath && taxonPath.length > 0) {
        const kingdoms = ['plantae', 'animalia', 'fungi']
        const kingdomIndex = taxonPath.findIndex((slug: string) => kingdoms.includes(slug))

        if (kingdomIndex >= 0) {
          const taxonomicPath = taxonPath.slice(kingdomIndex)
          const taxonId = 'tx:' + taxonomicPath.join(':')

          if (partId) {
            // Navigate to TP page
            router.navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId } })
          } else {
            // Navigate to taxon page
            router.navigate({ to: '/workbench/taxon/$id', params: { id: taxonId } })
          }
        } else {
          console.warn('[FS Parser] No kingdom found in path:', taxonPath)
          router.navigate({ to: '/workbench' })
        }
      } else {
        router.navigate({ to: '/workbench' })
      }
    } else if (parse.status === 'error') {
      console.error('Failed to parse FS string:', parse.error)
      router.navigate({ to: '/workbench' })
    }
  }, [parse.status, parse.data, parse.error, router])

  if (!fsString) {
    return <div className="p-4 text-sm text-destructive">Invalid FoodState string. Redirecting…</div>
  }

  if (parse.isLoading) {
    return <div className="p-4 text-sm text-muted-foreground">Resolving FoodState…</div>
  }

  if (parse.isError) {
    return <div className="p-4 text-sm text-destructive">Failed to parse FoodState. Redirecting…</div>
  }

  return <div className="p-4 text-sm text-muted-foreground">Redirecting…</div>
}
