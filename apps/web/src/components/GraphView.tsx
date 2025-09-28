import React, { Suspense, lazy } from 'react'
import { Node, Edge, Background, Controls, MiniMap } from 'reactflow'

export interface GraphViewProps {
  nodes: Node[]
  edges: Edge[]
  onNodeClick?: (id: string) => void
}

// Lazy load React Flow to keep initial bundle smaller
const ReactFlow = lazy(() => import('reactflow').then(module => ({ default: module.default })))

function GraphViewInner({ nodes, edges, onNodeClick }: GraphViewProps) {
  
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodeClick={(_, n) => onNodeClick?.(n.id)}
      fitView
    >
      <MiniMap />
      <Controls />
      <Background />
    </ReactFlow>
  )
}

export default function GraphView(props: GraphViewProps) {
  return (
    <div className="min-h-[400px] h-[60vh] rounded-lg border">
      <Suspense fallback={<div className="h-full flex items-center justify-center text-muted-foreground">Loading graph...</div>}>
        <GraphViewInner {...props} />
      </Suspense>
    </div>
  )
}
