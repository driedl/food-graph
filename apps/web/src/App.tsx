import { useEffect, useMemo, useState } from 'react'
import { trpc } from './lib/trpc'
import GraphView from './components/GraphView'
import type { Node as RFNode, Edge as RFEdge } from 'reactflow'
import { Button } from '@ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'
import { Input } from '@ui/input'
import { Separator } from '@ui/separator'
import { Badge } from '@ui/badge'

export default function App() {
  const health = trpc.health.useQuery()
  const root = trpc.taxonomy.getRoot.useQuery(undefined, { refetchOnWindowFocus: false })
  const [currentId, setCurrentId] = useState<string | null>(null)
  const nodeQuery = trpc.taxonomy.getNode.useQuery({ id: currentId! }, { enabled: !!currentId })
  const path = trpc.taxonomy.pathToRoot.useQuery({ id: currentId! }, { enabled: !!currentId })
  const children = trpc.taxonomy.getChildren.useQuery({ id: currentId! }, { enabled: !!currentId })
  const [q, setQ] = useState('')
  const search = trpc.taxonomy.search.useQuery({ q }, { enabled: q.length > 0 })

  useEffect(() => {
    if (root.data && !currentId) setCurrentId(root.data.id)
  }, [root.data, currentId])

  const graph = useMemo(() => {
    if (!nodeQuery.data) return { nodes: [], edges: [] }
    const center: RFNode = {
      id: nodeQuery.data.id,
      position: { x: 0, y: 0 },
      data: { label: `${nodeQuery.data.name} (${nodeQuery.data.rank})` },
      style: { border: '1px solid #ddd', borderRadius: 8, padding: 8, background: '#fff' }
    }
    const nodes: RFNode[] = [center]
    const edges: RFEdge[] = []

    // children around
    const offsetX = 250
    const offsetY = 100
    children.data?.forEach((c, i) => {
      const angle = (i / Math.max(children.data!.length, 1)) * Math.PI * 2
      const n: RFNode = {
        id: c.id,
        position: { x: Math.cos(angle) * offsetX, y: Math.sin(angle) * offsetY + 120 },
        data: { label: `${c.name} (${c.rank})` },
        style: { border: '1px solid #eee', borderRadius: 8, padding: 6, background: '#fafafa' }
      }
      nodes.push(n)
      edges.push({ id: `${nodeQuery.data!.id}->${c.id}`, source: nodeQuery.data!.id, target: c.id })
    })

    return { nodes, edges }
  }, [nodeQuery.data, children.data])

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="text-xl font-semibold">Nutrition Graph Explorer</div>
        <div className="text-sm">{health.data?.ok ? <Badge className="border-green-600">API: OK</Badge> : <Badge className="border-red-600">API: down</Badge>}</div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Search</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input placeholder="Search nodes..." value={q} onChange={(e) => setQ(e.target.value)} />
            <Button onClick={() => setQ('')}>Clear</Button>
          </div>
          {q && (
            <div className="max-h-60 overflow-auto border rounded-md">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 border-b">
                  <tr><th className="text-left p-2">Name</th><th className="text-left p-2">Rank</th></tr>
                </thead>
                <tbody>
                  {search.data?.map((n) => (
                    <tr key={n.id} className="hover:bg-muted/40 cursor-pointer" onClick={() => { setCurrentId(n.id); setQ('') }}>
                      <td className="p-2">{n.name}</td>
                      <td className="p-2">{n.rank}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Browse</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {path.data?.map((p, i) => (
              <div key={p.id} className="flex items-center gap-2">
                <button className="underline" onClick={() => setCurrentId(p.id)}>{p.name}</button>
                {i < (path.data!.length - 1) && <Separator className="w-3 rotate-90" />}
              </div>
            ))}
          </div>
          <GraphView nodes={graph.nodes} edges={graph.edges} onNodeClick={(id) => setCurrentId(id)} />
        </CardContent>
      </Card>
    </div>
  )
}
