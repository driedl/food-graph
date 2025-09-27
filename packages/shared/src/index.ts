export type NodeRank = 'root' | 'kingdom' | 'phylum' | 'class' | 'order' | 'family' | 'genus' | 'species' | 'variety' | 'form'

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
