import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import type { Node, Edge } from 'reactflow'
import 'reactflow/dist/style.css'

export interface GraphViewProps {
  nodes: Node[]
  edges: Edge[]
  onNodeClick?: (id: string) => void
  /** optional layout, defaults to 'radial' */
  layout?: 'radial' | 'tree'
}

/** Lightweight presentational helpers */
function RankPill({ rank }: { rank?: string }) {
  const map: Record<string, string> = {
    root: 'bg-slate-100 text-slate-700 border-slate-200',
    domain: 'bg-zinc-100 text-zinc-700 border-zinc-200',
    kingdom: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    phylum: 'bg-teal-100 text-teal-700 border-teal-200',
    class: 'bg-cyan-100 text-cyan-700 border-cyan-200',
    order: 'bg-sky-100 text-sky-700 border-sky-200',
    family: 'bg-teal-100 text-teal-700 border-teal-200',
    genus: 'bg-cyan-100 text-cyan-700 border-cyan-200',
    species: 'bg-blue-100 text-blue-700 border-blue-200',
    cultivar: 'bg-violet-100 text-violet-700 border-violet-200',
    variety: 'bg-violet-100 text-violet-700 border-violet-200',
    breed: 'bg-violet-100 text-violet-700 border-violet-200',
    product: 'bg-amber-100 text-amber-700 border-amber-200',
    form: 'bg-amber-100 text-amber-700 border-amber-200',
  }
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] uppercase ${map[rank ?? ''] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>
      {rank}
    </span>
  )
}

/**
 * We lazy-load reactflow and define nodeTypes inside to keep the main bundle small.
 * We also re-compute simple positions for a center + children graph so we can support
 * 'radial' and 'tree' layouts without external libs.
 */
const Flow = lazy(async () => {
  const m = await import('reactflow')

  const TaxonNode: React.FC<m.NodeProps<any>> = ({ data, selected }) => {
    return (
      <div className={`rounded-lg border bg-white px-3 py-2 shadow-sm ${selected ? 'ring-2 ring-blue-300' : ''}`}>
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <div className="text-sm font-medium truncate">{data?.name ?? data?.label}</div>
            {data?.slug && <div className="text-[11px] text-zinc-500 truncate">/{data.slug}</div>}
          </div>
          <div className="flex items-center gap-2">
            <RankPill rank={data?.rank} />
            {typeof data?.childCount === 'number' && (
              <span className="text-[10px] text-zinc-500">{data.childCount}</span>
            )}
          </div>
        </div>
      </div>
    )
  }

  const nodeTypes = { taxon: TaxonNode }
  const defaultEdgeOptions: m.DefaultEdgeOptions = {
    type: 'smoothstep',
    animated: false,
    markerEnd: { type: m.MarkerType.ArrowClosed, width: 16, height: 16 },
    style: { strokeWidth: 1.5 },
  }

  const Cmp = ({ nodes, edges, onNodeClick, layout = 'radial' }: GraphViewProps) => {
    // find center (node with indegree 0)
    const centerId = useMemo(() => {
      const indeg: Record<string, number> = {}
      nodes.forEach((n) => (indeg[n.id] = 0))
      edges.forEach((e) => { indeg[e.target] = (indeg[e.target] ?? 0) + 1 })
      // prefer provided 'isCenter' flag if present
      const explicitCenter = nodes.find((n: any) => n.data?.isCenter)?.id
      if (explicitCenter) return explicitCenter
      const id = Object.entries(indeg).find(([, v]) => v === 0)?.[0]
      return id ?? nodes[0]?.id
    }, [nodes, edges])

    const laidOut = useMemo(() => {
      if (!nodes.length) return { nodes, edges }

      // derive children of center only (current API returns a star)
      const children = edges.filter((e) => e.source === centerId).map((e) => e.target)

      // shallow clone nodes and assign positions
      const arranged = nodes.map((n) => ({ ...n }))

      if (layout === 'tree') {
        // Center at top, children stacked below
        const gapX = 220
        const gapY = 140
        arranged.forEach((n) => {
          if (n.id === centerId) {
            n.position = { x: 0, y: 0 }
          } else {
            const idx = children.indexOf(n.id)
            const x = (idx - (children.length - 1) / 2) * gapX
            const y = gapY
            n.position = { x, y }
          }
        })
      } else {
        // Radial layout around the center
        const radiusX = 280
        const radiusY = 140
        arranged.forEach((n) => {
          if (n.id === centerId) {
            n.position = { x: 0, y: 0 }
          } else {
            const idx = children.indexOf(n.id)
            const angle = (idx / Math.max(children.length, 1)) * Math.PI * 2
            const x = Math.cos(angle) * radiusX
            const y = Math.sin(angle) * radiusY + 120
            n.position = { x, y }
          }
        })
      }

      return { nodes: arranged, edges }
    }, [nodes, edges, centerId, layout])

    // fitView when the set of nodes changes
    const [rfInstance, setRfInstance] = useState<m.ReactFlowInstance | null>(null)
    useEffect(() => {
      if (rfInstance) {
        const idList = laidOut.nodes.map((n) => n.id).join('|')
        // next tick to allow layout to apply
        const t = setTimeout(() => rfInstance.fitView({ padding: 0.2, includeHiddenNodes: false }), 0)
        return () => clearTimeout(t)
      }
    }, [rfInstance, laidOut.nodes])

    return (
      <m.ReactFlow
        nodes={laidOut.nodes}
        edges={laidOut.edges}
        nodeTypes={nodeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        onNodeClick={(_, n) => onNodeClick?.(n.id)}
        nodesDraggable={false}
        panOnDrag
        zoomOnScroll
        fitView
        proOptions={{ hideAttribution: true }}
        onInit={(inst) => setRfInstance(inst)}
      >
        <m.MiniMap pannable zoomable />
        <m.Controls />
        <m.Background />
      </m.ReactFlow>
    )
  }

  return { default: Cmp }
})

export default function GraphView(props: GraphViewProps) {
  return (
    <div className="min-h-[420px] h-[60vh] rounded-lg border">
      <Suspense fallback={<div className="h-full flex items-center justify-center text-muted-foreground">Loading graph…</div>}>
        <Flow {...props} />
      </Suspense>
    </div>
  )
}
