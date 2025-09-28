import { useEffect, useMemo, useRef, useState } from 'react'
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

/** Shared types matching API rows */
interface TaxonNode {
  id: string
  name: string
  slug: string
  rank: string
  parentId: string | null
}

type LayoutMode = 'radial' | 'tree'

/** Small helpers */
const rankColor: Record<string, string> = {
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

export default function App() {
  // API health + root bootstrap
  const health = trpc.health.useQuery()
  const root = trpc.taxonomy.getRoot.useQuery(undefined, { refetchOnWindowFocus: false })

  // Focus / navigation state
  const [currentId, setCurrentId] = useState<string | null>(null)
  const [layout, setLayout] = useState<LayoutMode>('radial')

  // Queries scoped to current node
  const nodeQuery = trpc.taxonomy.getNode.useQuery({ id: currentId! }, { enabled: !!currentId })
  const path = trpc.taxonomy.pathToRoot.useQuery({ id: currentId! }, { enabled: !!currentId })
  const children = trpc.taxonomy.getChildren.useQuery({ id: currentId! }, { enabled: !!currentId })

  // Siblings (fetch parent’s children once)
  const parentId = (nodeQuery.data as TaxonNode | undefined)?.parentId ?? null
  const siblings = trpc.taxonomy.getChildren.useQuery({ id: parentId! }, { enabled: !!parentId })

  // Search (+ debounce + hotkey)
  const [qInput, setQInput] = useState('')
  const [q, setQ] = useState('') // debounced
  const search = trpc.taxonomy.search.useQuery({ q }, { enabled: q.length > 0 })
  const searchRef = useRef<HTMLInputElement>(null)
  const [activeIdx, setActiveIdx] = useState<number>(0)

  useEffect(() => {
    const t = setTimeout(() => setQ(qInput.trim()), 250)
    return () => clearTimeout(t)
  }, [qInput])

  // Bootstrap root
  useEffect(() => {
    if (root.data && !currentId) setCurrentId((root.data as TaxonNode).id)
  }, [root.data, currentId])

  // Cmd/Ctrl+K → focus search
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        searchRef.current?.focus()
      }
      // Quick lineage nav on arrow keys when not typing in an input
      const tag = (e.target as HTMLElement)?.tagName
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable
      if (isTyping) return
      if (e.key === 'ArrowLeft' && parentId) setCurrentId(parentId)
      if (e.key === 'ArrowRight') {
        const cs = (children.data as TaxonNode[] | undefined) ?? []
        if (cs.length) setCurrentId(cs[0].id)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [parentId, children.data])

  // Build a richer node/edge model for the canvas
  const graph = useMemo(() => {
    if (!nodeQuery.data) return { nodes: [] as RFNode[], edges: [] as RFEdge[] }

    const nodeData = nodeQuery.data as TaxonNode
    const kids = (children.data as TaxonNode[] | undefined) ?? []

    const center: RFNode = {
      id: nodeData.id,
      type: 'taxon',
      position: { x: 0, y: 0 },
      data: {
        id: nodeData.id,
        name: nodeData.name,
        slug: nodeData.slug,
        rank: nodeData.rank,
        childCount: kids.length,
        isCenter: true,
      },
    }

    const nodes: RFNode[] = [center]
    const edges: RFEdge[] = []

    kids.forEach((c) => {
      nodes.push({
        id: c.id,
        type: 'taxon',
        position: { x: 0, y: 0 }, // GraphView will lay out
        data: {
          id: c.id,
          name: c.name,
          slug: c.slug,
          rank: c.rank,
          childCount: undefined,
          isCenter: false,
        },
      })
      edges.push({ id: `${nodeData.id}->${c.id}`, source: nodeData.id, target: c.id, type: 'smoothstep' })
    })

    return { nodes, edges }
  }, [nodeQuery.data, children.data])

  // Inspector tabs
  const [tab, setTab] = useState<'overview' | 'lineage' | 'path'>('overview')

  // Search keyboard nav
  useEffect(() => {
    setActiveIdx(0)
  }, [q])

  const results = (search.data as TaxonNode[] | undefined) ?? []

  return (
    <div className="p-6 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="text-xl font-semibold tracking-tight">Nutrition Graph Explorer</div>
        <div className="flex items-center gap-2">
          <div className="hidden sm:flex text-xs text-muted-foreground px-2 py-1 rounded-md border bg-muted/30">
            Press <kbd className="mx-1 rounded border bg-background px-1">⌘</kbd>
            <span>K</span> to search
          </div>
          <div className="text-xs">
            {health.data?.ok ? (
              <Badge className="border-green-600">API: OK</Badge>
            ) : (
              <Badge className="border-red-600">API: down</Badge>
            )}
          </div>
        </div>
      </div>

      {/* 3-pane grid */}
      <div className="grid grid-cols-1 lg:grid-cols-[300px,1fr,360px] gap-4">
        {/* Left: Search */}
        <Card className="h-[72vh] flex flex-col">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between">
              <span>Find</span>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant={layout === 'radial' ? 'default' : 'outline'}
                  onClick={() => setLayout('radial')}
                >
                  Radial
                </Button>
                <Button
                  size="sm"
                  variant={layout === 'tree' ? 'default' : 'outline'}
                  onClick={() => setLayout('tree')}
                >
                  Tree
                </Button>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 overflow-hidden flex flex-col gap-3">
            <div className="flex gap-2">
              <Input
                ref={searchRef}
                placeholder="Search taxa (⌘K)…"
                value={qInput}
                onChange={(e) => setQInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'ArrowDown') setActiveIdx((i) => Math.min(i + 1, Math.max(results.length - 1, 0)))
                  if (e.key === 'ArrowUp') setActiveIdx((i) => Math.max(i - 1, 0))
                  if (e.key === 'Enter' && results[activeIdx]) {
                    setCurrentId(results[activeIdx].id)
                    setQInput('')
                    setQ('')
                  }
                  if (e.key === 'Escape') {
                    setQInput('')
                    setQ('')
                  }
                }}
              />
              {q && (
                <Button variant="outline" onClick={() => { setQInput(''); setQ('') }}>
                  Clear
                </Button>
              )}
            </div>

            {/* Results */}
            {q ? (
              <div className="flex-1 min-h-0 overflow-auto rounded-md border">
                <div className="bg-muted/50 border-b px-3 py-2 text-xs">
                  {search.isLoading ? 'Searching…' : `Results (${results.length})`}
                </div>
                {search.isLoading ? (
                  <div className="p-3 space-y-2">
                    {Array.from({ length: 6 }).map((_, i) => (
                      <div key={i} className="flex items-center gap-2">
                        <Skeleton className="h-4 flex-1" />
                        <Skeleton className="h-4 w-16" />
                      </div>
                    ))}
                  </div>
                ) : results.length === 0 ? (
                  <div className="p-6 text-center text-sm text-muted-foreground">
                    No results for “{q}”
                  </div>
                ) : (
                  <ul className="divide-y">
                    {results.map((n, i) => (
                      <li
                        key={n.id}
                        className={`flex items-center justify-between px-3 py-2 text-sm cursor-pointer hover:bg-muted/40 ${
                          i === activeIdx ? 'bg-muted/50' : ''
                        }`}
                        onMouseEnter={() => setActiveIdx(i)}
                        onClick={() => {
                          setCurrentId(n.id)
                          setQInput('')
                          setQ('')
                        }}
                      >
                        <div className="truncate">
                          <div className="truncate">{n.name}</div>
                          <div className="text-xs text-muted-foreground truncate">/{n.slug}</div>
                        </div>
                        <span
                          className={`ml-2 inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[n.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}
                        >
                          {n.rank}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              <div className="text-xs text-muted-foreground px-1">
                Tip: Use arrow keys to move up/down lineage when the canvas is focused.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Center: Graph */}
        <div className="min-h-[72vh]">
          <Card className="h-full">
            <CardHeader className="pb-2">
              <CardTitle>Browse</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Breadcrumb with sibling hop */}
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
                  {((path.data as TaxonNode[]) ?? []).map((p, i, arr) => {
                    const isLast = i === arr.length - 1
                    return (
                      <div key={p.id} className="flex items-center gap-2">
                        {!isLast ? (
                          <button className="underline" onClick={() => setCurrentId(p.id)}>
                            {p.name}
                          </button>
                        ) : (
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{p.name}</span>
                            {/* Sibling dropdown */}
                            {siblings.data && siblings.data.length > 0 && (
                              <select
                                className="text-xs border rounded px-1 py-0.5 bg-background"
                                value={currentId ?? ''}
                                onChange={(e) => setCurrentId(e.target.value)}
                              >
                                {(siblings.data as TaxonNode[]).map((s) => (
                                  <option key={s.id} value={s.id}>
                                    {s.name}
                                  </option>
                                ))}
                              </select>
                            )}
                          </div>
                        )}
                        {!isLast && <Separator className="w-3 rotate-90" />}
                      </div>
                    )
                  })}
                </div>
              )}

              <ErrorBoundary>
                <GraphView
                  nodes={graph.nodes}
                  edges={graph.edges}
                  layout={layout}
                  onNodeClick={(id) => setCurrentId(id)}
                />
              </ErrorBoundary>
            </CardContent>
          </Card>
        </div>

        {/* Right: Inspector */}
        <Card className="h-[72vh] flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle>Inspector</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 overflow-hidden">
            {/* Tabs */}
            <div className="flex gap-2">
              <Button size="sm" variant={tab === 'overview' ? 'default' : 'outline'} onClick={() => setTab('overview')}>
                Overview
              </Button>
              <Button size="sm" variant={tab === 'lineage' ? 'default' : 'outline'} onClick={() => setTab('lineage')}>
                Lineage
              </Button>
              <Button size="sm" variant={tab === 'path' ? 'default' : 'outline'} onClick={() => setTab('path')}>
                Path Builder
              </Button>
            </div>

            {/* Panels */}
            <div className="flex-1 min-h-0 overflow-auto">
              {tab === 'overview' && (
                <div className="space-y-3 text-sm">
                  {!nodeQuery.data ? (
                    <Skeleton className="h-6 w-40" />
                  ) : (
                    <>
                      <div className="flex items-center justify-between">
                        <div className="text-base font-medium">{(nodeQuery.data as TaxonNode).name}</div>
                        <span
                          className={`ml-2 inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[(nodeQuery.data as TaxonNode).rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}
                        >
                          {(nodeQuery.data as TaxonNode).rank}
                        </span>
                      </div>
                      <div className="text-xs text-muted-foreground">/{(nodeQuery.data as TaxonNode).slug}</div>
                      <Separator />
                      <div className="grid grid-cols-2 gap-2">
                        <div className="text-xs text-muted-foreground">ID</div>
                        <div className="text-xs break-all">{(nodeQuery.data as TaxonNode).id}</div>
                        <div className="text-xs text-muted-foreground">Children</div>
                        <div className="text-xs">{(children.data as TaxonNode[] | undefined)?.length ?? 0}</div>
                        <div className="text-xs text-muted-foreground">Parent</div>
                        <div className="text-xs">
                          {parentId ? (
                            <button className="underline" onClick={() => setCurrentId(parentId)}>
                              {parentId}
                            </button>
                          ) : (
                            '—'
                          )}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              {tab === 'lineage' && (
                <div className="space-y-2 text-sm">
                  {!path.data ? (
                    <div className="space-y-2">
                      {Array.from({ length: 6 }).map((_, i) => (
                        <Skeleton key={i} className="h-4 w-3/4" />
                      ))}
                    </div>
                  ) : (
                    <ul className="space-y-1">
                      {((path.data as TaxonNode[]) ?? []).map((p) => (
                        <li key={p.id} className="flex items-center justify-between">
                          <button className="underline text-left" onClick={() => setCurrentId(p.id)}>
                            {p.name}
                          </button>
                          <span
                            className={`ml-2 inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[p.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}
                          >
                            {p.rank}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {tab === 'path' && (
                <div className="space-y-3 text-sm">
                  <div className="text-muted-foreground">
                    Compose a FoodState identity (client-only preview).
                  </div>
                  <Separator />
                  {/* Tiny local “builder” with a few illustrative choices */}
                  <PathBuilder
                    taxonPath={((path.data as TaxonNode[]) ?? []).map((p) => p.slug)}
                    onCopy={(s) => navigator.clipboard.writeText(s)}
                  />
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

/** Simple client-only builder to preview FoodState identity strings */
function PathBuilder({ taxonPath, onCopy }: { taxonPath: string[]; onCopy: (s: string) => void }) {
  const [part, setPart] = useState<'fruit' | 'seed' | 'leaf' | 'grain' | 'milk' | ''>('')
  const [refinement, setRefinement] = useState<'whole' | 'refined' | '00' | ''>('')
  const [process, setProcess] = useState<'raw' | 'boil' | 'steam' | 'bake' | 'roast' | 'fry' | 'broil' | ''>('')

  const fs = useMemo(() => {
    const segments = [`fs://${taxonPath.join('/')}`]
    if (part) segments.push(`part:${part}`)
    if (refinement) segments.push(`tf:mill{refinement=${refinement}}`)
    if (process) segments.push(`tf:cook{method=${process}}`)
    return segments.join('/')
  }, [taxonPath, part, refinement, process])

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-3 gap-2 items-center">
        <div>Part</div>
        <select className="col-span-2 border rounded px-2 py-1 bg-background" value={part} onChange={(e) => setPart(e.target.value as any)}>
          <option value="">—</option>
          <option value="fruit">fruit</option>
          <option value="seed">seed</option>
          <option value="leaf">leaf</option>
          <option value="grain">grain</option>
          <option value="milk">milk</option>
        </select>

        <div>Mill</div>
        <select className="col-span-2 border rounded px-2 py-1 bg-background" value={refinement} onChange={(e) => setRefinement(e.target.value as any)}>
          <option value="">—</option>
          <option value="whole">whole</option>
          <option value="refined">refined</option>
          <option value="00">00</option>
        </select>

        <div>Cook</div>
        <select className="col-span-2 border rounded px-2 py-1 bg-background" value={process} onChange={(e) => setProcess(e.target.value as any)}>
          <option value="">—</option>
          <option value="raw">raw</option>
          <option value="boil">boil</option>
          <option value="steam">steam</option>
          <option value="bake">bake</option>
          <option value="roast">roast</option>
          <option value="fry">fry</option>
          <option value="broil">broil</option>
        </select>
      </div>

      <div className="text-xs text-muted-foreground">Preview</div>
      <div className="text-xs font-mono border rounded p-2 bg-muted/30 break-all">{fs}</div>
      <div>
        <Button size="sm" onClick={() => onCopy(fs)}>Copy</Button>
      </div>
    </div>
  )
}
