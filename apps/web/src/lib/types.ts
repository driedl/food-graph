// Shared types for the workbench UI

export type SearchRow = {
    ref_type: 'taxon' | 'tp' | 'tpt'
    ref_id: string
    name?: string
    slug?: string
    family?: string
    rank?: string
    taxon_id?: string
    part_id?: string
    score?: number
    rn?: number // row number for debug/dedup inspection
}

export type SuggestItem =
    | { kind: 'taxon'; id: string; name: string; slug: string; rank: string }
    | { kind: 'tp'; id: string; taxonId: string; partId: string; name: string; displayName?: string; slug?: string }
    | { kind: 'tpt'; id: string; taxonId: string; partId: string; family: string; name?: string }

export type TaxonNode = {
    id: string
    name: string
    slug: string
    rank: string
    parentId?: string | null
}

export type TPTBrief = {
    id: string
    name?: string
    taxonId: string
    partId: string
    family: string
    identityHash: string
}

export type IdentityStep = {
    index: number
    tf_id: string
    params: Record<string, any>
}

export type TPTData = {
    id: string
    taxonId: string
    partId: string
    family: string
    name?: string
    synonyms?: string[]
    identityHash: string
    identity: Array<{ id: string; params?: Record<string, any> }>
    flags?: Array<{ flag: string; flag_type: 'safety' | 'dietary' | 'misc' }>
    cuisines?: string[]
    related?: { variants: string[]; siblings: string[] }
}

export type TPTExplain = {
    steps: Array<{ label: string; details?: string }>
    friendlyName?: string
}

export type FSParseResult = {
    taxonPath?: string[]
    partId?: string
    transforms?: Array<{ id: string; params?: Record<string, any> }>
}
