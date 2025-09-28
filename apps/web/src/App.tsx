import { useEffect, useMemo, useState } from 'react'
import { trpc } from './lib/trpc'
import GraphView from './components/GraphView'
import ErrorBoundary from './components/ErrorBoundary'
import type { Node as RFNode, Edge as RFEdge } from 'reactflow'
import { Button } from '@ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'
import { Input } from '@ui/input'
import { Separator } from '@ui/separator'
import { Badge } from '@ui/badge'
import { Skeleton } from '@ui/skeleton'

// Type definitions for the database results
interface TaxonNode {
  id: string
  name: string
  slug: string
  rank: string
  parentId: string | null
}

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
    if (root.data && !currentId) setCurrentId((root.data as TaxonNode).id)
  }, [root.data, currentId])

  const graph = useMemo(() => {
    if (!nodeQuery.data) return { nodes: [], edges: [] }
    const nodeData = nodeQuery.data as TaxonNode
    const center: RFNode = {
      id: nodeData.id,
      position: { x: 0, y: 0 },
      data: { label: `${nodeData.name} (${nodeData.rank})` },
      style: { border: '1px solid #ddd', borderRadius: 8, padding: 8, background: '#fff' }
    }
    const nodes: RFNode[] = [center]
    const edges: RFEdge[] = []

    // children around
    const offsetX = 250
    const offsetY = 100
    const childrenData = children.data as TaxonNode[] | undefined
    childrenData?.forEach((c, i) => {
      const angle = (i / Math.max(childrenData.length, 1)) * Math.PI * 2
      const n: RFNode = {
        id: c.id,
        position: { x: Math.cos(angle) * offsetX, y: Math.sin(angle) * offsetY + 120 },
        data: { label: `${c.name} (${c.rank})` },
        style: { border: '1px solid #eee', borderRadius: 8, padding: 6, background: '#fafafa' }
      }
      nodes.push(n)
      edges.push({ id: `${nodeData.id}->${c.id}`, source: nodeData.id, target: c.id })
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
              <div className="bg-muted/50 border-b px-3 py-2 text-sm font-medium">
                Search Results {search.data && `(${search.data.length})`}
              </div>
              {search.isLoading ? (
                <div className="p-4 space-y-2">
                  {Array.from({ length: 3 }).map((_, i) => (
                    <div key={i} className="flex items-center space-x-2">
                      <Skeleton className="h-4 flex-1" />
                      <Skeleton className="h-4 w-16" />
                    </div>
                  ))}
                </div>
              ) : (
                <table className="w-full text-sm">
                  <thead className="bg-muted/30 border-b">
                    <tr><th className="text-left p-2">Name</th><th className="text-left p-2">Rank</th></tr>
                  </thead>
                  <tbody>
                    {(search.data as TaxonNode[])?.map((n) => (
                      <tr key={n.id} className="hover:bg-muted/40 cursor-pointer" onClick={() => { setCurrentId(n.id); setQ('') }}>
                        <td className="p-2">{n.name}</td>
                        <td className="p-2"><Badge variant="outline" className="text-xs">{n.rank}</Badge></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {search.data?.length === 0 && (
                <div className="p-4 text-center text-muted-foreground">
                  No results found for "{q}"
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Browse</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {path.isLoading ? (
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-16" />
              <Separator className="w-3 rotate-90" />
              <Skeleton className="h-4 w-20" />
              <Separator className="w-3 rotate-90" />
              <Skeleton className="h-4 w-24" />
            </div>
          ) : (
            <div className="flex flex-wrap items-center gap-2 text-sm">
              {(path.data as TaxonNode[])?.map((p, i) => (
                <div key={p.id} className="flex items-center gap-2">
                  <button className="underline" onClick={() => setCurrentId(p.id)}>{p.name}</button>
                  {i < ((path.data as TaxonNode[])!.length - 1) && <Separator className="w-3 rotate-90" />}
                </div>
              ))}
            </div>
          )}
          <ErrorBoundary>
            <GraphView nodes={graph.nodes} edges={graph.edges} onNodeClick={(id) => setCurrentId(id)} />
          </ErrorBoundary>
        </CardContent>
      </Card>
    </div>
  )
}
