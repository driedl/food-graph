import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react'
import type { Node, Edge, NodeProps, ReactFlowInstance } from 'reactflow'
import 'reactflow/dist/style.css'
import { RANK_COLOR } from '@/lib/constants'

export interface GraphViewProps {
  nodes: Node[]
  edges: Edge[]
  onNodeClick?: (id: string) => void
  /** optional layout, defaults to 'radial' */
  layout?: 'radial' | 'tree'
}

function RankPill({ rank }: { rank?: string }) {
  return (
    <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] uppercase ${RANK_COLOR[rank ?? ''] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>
      {rank}
    </span>
  )
}

const Flow = lazy(async () => {
  const { 
    ReactFlow, 
    MiniMap, 
    Controls, 
    Background, 
    MarkerType
  } = await import('reactflow')

  const TaxonNode: React.FC<NodeProps> = ({ data, selected }) => {
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
  const defaultEdgeOptions = {
    type: 'smoothstep',
    animated: false,
    markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
    style: { strokeWidth: 1.5 },
  }

  const Cmp = ({ nodes, edges, onNodeClick, layout = 'radial' }: GraphViewProps) => {
    const centerId = useMemo(() => {
      const indeg: Record<string, number> = {}
      nodes.forEach((n) => (indeg[n.id] = 0))
      edges.forEach((e) => { indeg[e.target] = (indeg[e.target] ?? 0) + 1 })
      const explicitCenter = nodes.find((n: any) => n.data?.isCenter)?.id
      if (explicitCenter) return explicitCenter
      const id = Object.entries(indeg).find(([, v]) => v === 0)?.[0]
      return id ?? nodes[0]?.id
    }, [nodes, edges])

    const laidOut = useMemo(() => {
      if (!nodes.length) return { nodes, edges }
      const children = edges.filter((e) => e.source === centerId).map((e) => e.target)
      const arranged = nodes.map((n) => ({ ...n }))

      if (layout === 'tree') {
        const gapX = 220, gapY = 140
        arranged.forEach((n) => {
          if (n.id === centerId) n.position = { x: 0, y: 0 }
          else {
            const idx = children.indexOf(n.id)
            const x = (idx - (children.length - 1) / 2) * gapX
            const y = gapY
            n.position = { x, y }
          }
        })
      } else {
        const radiusX = 280, radiusY = 140
        arranged.forEach((n) => {
          if (n.id === centerId) n.position = { x: 0, y: 0 }
          else {
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

    const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null)
    useEffect(() => {
      if (rfInstance) {
        const t = setTimeout(() => rfInstance.fitView({ padding: 0.2, includeHiddenNodes: false }), 0)
        return () => clearTimeout(t)
      }
    }, [rfInstance, laidOut.nodes])

    return (
      <ReactFlow
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
        <MiniMap pannable zoomable />
        <Controls />
        <Background />
      </ReactFlow>
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
