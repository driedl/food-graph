import { useNavigate } from '@tanstack/react-router'
import { trpc } from './trpc'

// Navigation utilities for the workbench

export function useNavigateFs() {
    const navigate = useNavigate()

    return async (fs: string) => {
        try {
            // Parse the FS string using the API
            const parseResult = await trpc.foodstate.parse.query({ fs })

            if (parseResult.taxonPath && parseResult.taxonPath.length > 0) {
                const kingdoms = ['plantae', 'animalia', 'fungi']
                const kingdomIndex = parseResult.taxonPath.findIndex((slug: string) => kingdoms.includes(slug))

                if (kingdomIndex >= 0) {
                    const taxonomicPath = parseResult.taxonPath.slice(kingdomIndex)
                    const taxonId = 'tx:' + taxonomicPath.join(':')

                    if (parseResult.partId) {
                        // Navigate to TP page
                        navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId: parseResult.partId } })
                    } else {
                        // Navigate to taxon page
                        navigate({ to: '/workbench/taxon/$id', params: { id: taxonId } })
                    }
                } else {
                    console.warn('[FS Parser] No kingdom found in path:', parseResult.taxonPath)
                }
            }

            // Show toast for transforms being ignored
            if (parseResult.transforms && parseResult.transforms.length > 0) {
                // TODO: Implement toast notification
                console.log('Transforms ignored for routing:', parseResult.transforms)
            }
        } catch (error) {
            console.error('Failed to parse FS string:', error)
            // TODO: Show error toast
        }
    }
}

export function useNavigationHelpers() {
    const navigate = useNavigate()

    return {
        gotoTaxon: (id: string) => navigate({ to: '/workbench/taxon/$id', params: { id } }),
        gotoTP: (taxonId: string, partId: string) =>
            navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId } }),
        gotoTPT: (id: string) => navigate({ to: '/workbench/tpt/$id', params: { id } }),
        gotoFamilies: () => navigate({ to: '/workbench/families' }),
        gotoCuisines: () => navigate({ to: '/workbench/cuisines' }),
        gotoFlags: () => navigate({ to: '/workbench/flags' }),
        gotoSearch: () => navigate({ to: '/workbench/search' }),
        gotoMeta: () => navigate({ to: '/workbench/meta' }),
    }
}
