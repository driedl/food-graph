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
