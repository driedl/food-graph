import GraphView from './GraphView'
import type { Node as RFNode, Edge as RFEdge } from 'reactflow'

export default function MiniMapGraph({
  lineage,
  children,
  onPick,
}: {
  lineage: Array<{ id: string; name: string; slug: string; rank: string }>
  children: Array<{ id: string; name: string; slug: string; rank: string }>
  onPick: (id: string) => void
}) {
  // Build a tiny graph: last lineage node as center, show lineage chain as edges to center,
  // and fan-out of current children.
  const center = lineage[lineage.length - 1]
  if (!center) return <div className="text-xs text-muted-foreground">No context</div>

  const nodes: RFNode[] = [
    {
      id: center.id,
      type: 'taxon',
      position: { x: 0, y: 0 },
      data: { ...center, isCenter: true, childCount: children.length },
    },
  ]
  const edges: RFEdge[] = []

  // Add previous lineage nodes as a chain above
  const above = lineage.slice(0, -1)
  above.forEach((n, idx) => {
    nodes.push({
      id: n.id,
      type: 'taxon',
      position: { x: (idx - (above.length - 1) / 2) * 120, y: -100 },
      data: { ...n, isCenter: false },
    })
    if (idx === above.length - 1) {
      edges.push({ id: `${n.id}->${center.id}`, source: n.id, target: center.id, type: 'smoothstep' })
    } else {
      const next = above[idx + 1]
      edges.push({ id: `${n.id}->${next.id}`, source: n.id, target: next.id, type: 'smoothstep' })
    }
  })

  // Fan-out children
  children.forEach((c, i) => {
    nodes.push({
      id: c.id,
      type: 'taxon',
      position: { x: (i - (children.length - 1) / 2) * 100, y: 120 },
      data: { ...c, isCenter: false },
    })
    edges.push({ id: `${center.id}->${c.id}`, source: center.id, target: c.id, type: 'smoothstep' })
  })

  return (
    <div className="h-40 rounded-md border">
      <GraphView
        nodes={nodes}
        edges={edges}
        onNodeClick={(id) => onPick(id)}
        layout="tree"
      />
    </div>
  )
}
