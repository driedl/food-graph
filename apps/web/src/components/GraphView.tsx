import React, { Suspense, lazy } from 'react'
import type { Node, Edge } from 'reactflow'
import 'reactflow/dist/style.css' // add this

export interface GraphViewProps {
  nodes: Node[]
  edges: Edge[]
  onNodeClick?: (id: string) => void
}

// lazy-load the entire module and pluck what we need inside
const Flow = lazy(async () => {
  const m = await import('reactflow')
  const Cmp = ({ nodes, edges, onNodeClick }: GraphViewProps) => (
    <m.ReactFlow
      nodes={nodes}
      edges={edges}
      onNodeClick={(_, n) => onNodeClick?.(n.id)}
      fitView
    >
      <m.MiniMap />
      <m.Controls />
      <m.Background />
    </m.ReactFlow>
  )
  return { default: Cmp }
})

export default function GraphView(props: GraphViewProps) {
  return (
    <div className="min-h-[400px] h-[60vh] rounded-lg border">
      <Suspense fallback={<div className="h-full flex items-center justify-center text-muted-foreground">Loading graph...</div>}>
        <Flow {...props} />
      </Suspense>
    </div>
  )
}
