import { useLocation } from '@tanstack/react-router'
import { pathToNodeId } from '../lib/fs-url'

/**
 * Hook to get the current taxon ID from the router URL.
 * This serves as the single source of truth for the current taxon.
 */
export function useCurrentTaxon(): string | null {
  const location = useLocation()
  
  // Extract taxon ID from various route patterns
  const taxonId = pathToNodeId(location.pathname)
  
  return taxonId
}

/**
 * Hook to get the current taxon ID with fallback to root.
 * Useful for components that always need a taxon ID.
 */
export function useCurrentTaxonWithFallback(rootId?: string): string | null {
    const taxonId = useCurrentTaxon()

    // If no taxon ID in URL and we have a root ID, return root
    if (!taxonId && rootId) {
        return rootId
    }

    return taxonId
}
