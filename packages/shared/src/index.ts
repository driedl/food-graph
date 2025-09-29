export type NodeRank =
  | 'root' | 'domain' | 'kingdom' | 'phylum' | 'class' | 'order'
  | 'family' | 'genus' | 'species' | 'subspecies' | 'cultivar' | 'variety'
  | 'breed' | 'product' | 'form'

export interface TaxNode {
  id: string
  name: string
  slug: string
  rank: NodeRank
  parentId: string | null
}

export interface NodeAttribute {
  nodeId: string
  attr: string
  val: string
}

// Food state composition types and functions
export type KV = Record<string, unknown>
export type TransformInput = { id: string; params?: KV }

export type ComposeInput = {
  taxonId: string
  partId: string
  transforms: TransformInput[]
}

export type ComposeResult = {
  id: string | null
  errors: string[]
  normalized?: {
    taxonId: string
    partId: string
    transforms: { id: string; params: KV }[]
  }
}

// Export the composeFoodState function from the separate implementation file
export { composeFoodState } from './foodstate.js'
