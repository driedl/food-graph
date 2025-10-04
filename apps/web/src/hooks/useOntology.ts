import { trpc } from '../lib/trpc'

// Ontological data hooks using TanStack Query
// These are small lookup tables that are fetched once and cached forever

export const useCategories = () => 
  trpc.browse.getCategories.useQuery(undefined, {
    staleTime: Infinity, // Never refetch - ontological data is static
    cacheTime: Infinity, // Keep forever
  })

export const useFamilies = () => 
  trpc.browse.getFamilies.useQuery(undefined, {
    staleTime: Infinity,
    cacheTime: Infinity,
  })

export const useCuisines = () => 
  trpc.browse.getCuisines.useQuery(undefined, {
    staleTime: Infinity,
    cacheTime: Infinity,
  })

// Helper hook to get all ontological data at once
export const useOntologyData = () => {
  const categories = useCategories()
  const families = useFamilies()
  const cuisines = useCuisines()

  return {
    categories: categories.data || [],
    families: families.data || [],
    cuisines: cuisines.data || [],
    isLoading: categories.isLoading || families.isLoading || cuisines.isLoading,
    isError: categories.isError || families.isError || cuisines.isError,
  }
}

// Helper to get category by ID
export const useCategoryById = (id: string) => {
  const { data: categories = [] } = useCategories()
  return categories.find(cat => cat.id === id)
}

// Helper to get category name by ID
export const useCategoryName = (id: string) => {
  const category = useCategoryById(id)
  return category?.name || 'Unknown'
}
