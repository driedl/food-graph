import React from 'react'
import ReactFlow, { Background, Controls, MiniMap, Node, Edge } from 'reactflow'
import 'reactflow/dist/style.css'

export interface GraphViewProps {
  nodes: Node[]
  edges: Edge[]
  onNodeClick?: (id: string) => void
}

export default function GraphView({ nodes, edges, onNodeClick }: GraphViewProps) {
  return (
    <div className="h-[600px] rounded-lg border">
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
    </div>
  )
}
