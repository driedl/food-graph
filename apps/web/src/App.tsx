import { useEffect, useMemo, useRef, useState } from 'react'
import { trpc } from './lib/trpc'
import GraphView from './components/GraphView'
import ErrorBoundary from './components/ErrorBoundary'
import { ChildrenTable } from './components/ChildrenTable'
import { DocsPanel } from './components/inspector/DocsPanel'
import { TaxonPanel } from './components/inspector/TaxonPanel'
import { PartsPanel } from './components/inspector/PartsPanel'
import { TransformsPanel } from './components/inspector/TransformsPanel'
import { FoodStatePanel } from './components/inspector/FoodStatePanel'
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

/** Compact rank → style map (fallback default if unknown) */
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
  const [centerTab, setCenterTab] = useState<'graph' | 'table'>('graph')

  // Queries scoped to current node - using new neighborhood API
  const neighborhood = trpc.taxonomy.neighborhood.useQuery(
    { id: currentId!, childLimit: 50, orderBy: 'name' }, 
    { enabled: !!currentId }
  )
  const docs = trpc.docs.getByTaxon.useQuery({ taxonId: currentId! }, { enabled: !!currentId })
  const parts = trpc.taxonomy.partTree.useQuery({ id: currentId! }, { enabled: !!currentId })
  const lineageQ = trpc.taxonomy.pathToRoot.useQuery({ id: currentId! }, { enabled: !!currentId })

  // Extract data from neighborhood response
  const nodeData = neighborhood.data?.node as TaxonNode | undefined
  const parentData = neighborhood.data?.parent as TaxonNode | undefined
  const childrenData = (neighborhood.data?.children || []) as TaxonNode[]
  const siblingsData = (neighborhood.data?.siblings || []) as TaxonNode[]
  const parentId = parentData?.id ?? null

  // Search (+ debounce + hotkey) - using new unified search
  const [qInput, setQInput] = useState('')
  const [q, setQ] = useState('') // debounced
  const search = trpc.search.unified.useQuery({ q, limit: 25 }, { enabled: q.length > 0 })
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

  // Cmd/Ctrl+K → focus search & lineage arrow nav
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        searchRef.current?.focus()
      }
      const tag = (e.target as HTMLElement)?.tagName
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || (e.target as HTMLElement)?.isContentEditable
      if (isTyping) return
      if (e.key === 'ArrowLeft' && parentId) setCurrentId(parentId)
      if (e.key === 'ArrowRight') {
        if (childrenData.length) setCurrentId(childrenData[0].id)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [parentId, childrenData])

  // Build a center + children graph model
  const graph = useMemo(() => {
    if (!nodeData) return { nodes: [] as RFNode[], edges: [] as RFEdge[] }
    const kids = childrenData

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

    kids.forEach((c: TaxonNode) => {
      nodes.push({
        id: c.id,
        type: 'taxon',
        position: { x: 0, y: 0 },
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
  }, [nodeData, childrenData])

  // Inspector tabs: Docs is FIRST-CLASS and DEFAULT
  const [tab, setTab] = useState<'docs' | 'taxon' | 'parts' | 'transforms' | 'foodstate'>('docs')

  // Parts/Transforms builder state
  const [selectedPartId, setSelectedPartId] = useState<string>('')
  useEffect(() => { setSelectedPartId('') }, [currentId])
  const transforms = trpc.taxonomy.getTransformsFor.useQuery(
    { taxonId: currentId || '', partId: selectedPartId || '', identityOnly: false },
    { enabled: !!currentId && !!selectedPartId }
  )

  type ChosenTx = { id: string; params: Record<string, any> }
  const [chosen, setChosen] = useState<ChosenTx[]>([])
  useEffect(() => { setChosen([]) }, [selectedPartId, currentId])

  const onToggleTx = (txId: string, isIdentity: boolean) => {
    if (!isIdentity) return // non-identity cannot be in identity chain
    setChosen((prev) => {
      const idx = prev.findIndex((t) => t.id === txId)
      if (idx >= 0) return prev.filter((t) => t.id !== txId)
      return [...prev, { id: txId, params: {} }]
    })
  }
  const onParamChange = (txId: string, key: string, value: any) => {
    setChosen((prev) => prev.map((t) => (t.id === txId ? { ...t, params: { ...t.params, [key]: value } } : t)))
  }

  // Compose local fs:// preview
  const fsPreview = useMemo(() => {
    // Prefer full lineage when available; fall back to current node only.
    const pathSlugs =
      (lineageQ.data?.map((n: any) => n.slug) ??
       (nodeData ? [nodeData.slug] : []))
    if (!pathSlugs.length) return ''
    const segs: string[] = [`fs:/${pathSlugs.join('/')}`]
    if (selectedPartId) segs.push(selectedPartId)
    if (chosen.length) {
      const ordered = [...chosen].sort((a, b) => a.id.localeCompare(b.id))
      const chain = ordered.map((t) => {
        const keys = Object.keys(t.params || {}).sort()
        const p = keys.map((k) => {
          const v: any = (t.params as any)[k]
          if (typeof v === 'number') return `${k}=${Number(v.toFixed(6)).toString()}`
          if (typeof v === 'boolean') return `${k}=${v ? 'true' : 'false'}`
          return `${k}=${String(v)}`
        }).join(',')
        return p ? `${t.id}{${p}}` : `${t.id}`
      }).join('/')
      if (chain) segs.push(chain)
    }
    return segs.join('/')
  }, [lineageQ.data, nodeData, selectedPartId, chosen])

  // Optional server validation using existing foodstate.compose (query)
  const compose = trpc.foodstate.compose.useQuery(
    { taxonId: currentId || '', partId: selectedPartId || '', transforms: chosen },
    { enabled: false }
  )

  // FoodState parser
  const handleParse = async (fs: string) => {
    try {
      // Use direct tRPC HTTP query: /trpc/route?input=...
      const res = await fetch(`/trpc/foodstate.parse?input=${encodeURIComponent(JSON.stringify({ fs }))}`)
      const json = await res.json()
      const parsed = json?.result?.data
      
      if (parsed.taxonPath && parsed.taxonPath.length > 0) {
        // For now, just navigate to the last taxon in the path
        // In a full implementation, you'd navigate through the full path
        const lastTaxon = parsed.taxonPath[parsed.taxonPath.length - 1]
        setCurrentId(lastTaxon)
      }
      if (parsed.partId) {
        setSelectedPartId(parsed.partId)
      }
      // TODO: Handle transforms from parsed.transforms
    } catch (error) {
      console.error('Failed to parse FoodState:', error)
    }
  }

  // Search keyboard nav
  useEffect(() => { setActiveIdx(0) }, [q])
  const results = (search.data as any[] | undefined) ?? []

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
      <div className="grid grid-cols-1 lg:grid-cols-[300px,1fr,380px] gap-4">
        {/* Left: Search */}
        <Card className="h-[74vh] flex flex-col">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between">
              <span>Find</span>
              <div className="flex items-center gap-2">
                <Button size="sm" variant={layout === 'radial' ? 'default' : 'outline'} onClick={() => setLayout('radial')}>
                  Radial
                </Button>
                <Button size="sm" variant={layout === 'tree' ? 'default' : 'outline'} onClick={() => setLayout('tree')}>
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
                    {results.map((n: any, i: number) => (
                      <li
                        key={n.id}
                        className={`flex items-center justify-between px-3 py-2 text-sm cursor-pointer hover:bg-muted/40 ${i === activeIdx ? 'bg-muted/50' : ''}`}
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
                        <div className="flex items-center gap-2">
                          {n.kind && (
                            <span className="text-xs text-muted-foreground bg-muted/50 px-1.5 py-0.5 rounded">
                              {n.kind}
                            </span>
                          )}
                          <span className={`ml-2 inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[n.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>
                            {n.rank}
                          </span>
                        </div>
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

        {/* Center: Graph & Table */}
        <div className="min-h-[74vh]">
          <Card className="h-full">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle>Browse</CardTitle>
                <div className="flex gap-2">
                  <Button size="sm" variant={centerTab === 'graph' ? 'default' : 'outline'} onClick={() => setCenterTab('graph')}>
                    Graph
                  </Button>
                  <Button size="sm" variant={centerTab === 'table' ? 'default' : 'outline'} onClick={() => setCenterTab('table')}>
                    Table
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Breadcrumb with sibling hop */}
              {neighborhood.isLoading ? (
                <div className="flex items-center gap-2">
                  <Skeleton className="h-4 w-16" />
                  <Separator className="w-3 rotate-90" />
                  <Skeleton className="h-4 w-20" />
                  <Separator className="w-3 rotate-90" />
                  <Skeleton className="h-4 w-24" />
                </div>
              ) : (
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  {parentData && (
                    <div className="flex items-center gap-2">
                      <button className="underline" onClick={() => setCurrentId(parentData.id)}>
                        {parentData.name}
                      </button>
                      <Separator className="w-3 rotate-90" />
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{nodeData?.name}</span>
                    {siblingsData && siblingsData.length > 0 && (
                      <select
                        className="text-xs border rounded px-1 py-0.5 bg-background"
                        value={currentId ?? ''}
                        onChange={(e) => setCurrentId(e.target.value)}
                      >
                        {siblingsData.map((s: TaxonNode) => (
                          <option key={s.id} value={s.id}>{s.name}</option>
                        ))}
                      </select>
                    )}
                  </div>
                </div>
              )}

              <ErrorBoundary>
                {centerTab === 'graph' ? (
                  <GraphView
                    nodes={graph.nodes}
                    edges={graph.edges}
                    layout={layout}
                    onNodeClick={(id) => setCurrentId(id)}
                  />
                ) : (
                  <ChildrenTable
                    rows={childrenData}
                    onPick={(id: string) => setCurrentId(id)}
                    rankColor={rankColor}
                  />
                )}
              </ErrorBoundary>
            </CardContent>
          </Card>
        </div>

        {/* Right: Inspector */}
        <Card className="h-[74vh] flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle>Inspector</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 overflow-hidden">
            {/* Tabs - Docs FIRST */}
            <div className="flex flex-wrap gap-2">
              <Button size="sm" variant={tab === 'docs' ? 'default' : 'outline'} onClick={() => setTab('docs')}>Docs</Button>
              <Button size="sm" variant={tab === 'taxon' ? 'default' : 'outline'} onClick={() => setTab('taxon')}>Taxon</Button>
              <Button size="sm" variant={tab === 'parts' ? 'default' : 'outline'} onClick={() => setTab('parts')}>Parts</Button>
              <Button size="sm" variant={tab === 'transforms' ? 'default' : 'outline'} onClick={() => setTab('transforms')}>Transforms</Button>
              <Button size="sm" variant={tab === 'foodstate' ? 'default' : 'outline'} onClick={() => setTab('foodstate')}>FoodState</Button>
            </div>

            <div className="flex-1 min-h-0 overflow-auto">
              {tab === 'docs' && <DocsPanel docs={docs.data as any} node={nodeData as TaxonNode | undefined} rankColor={rankColor} />}
              {tab === 'taxon' && <TaxonPanel node={nodeData as TaxonNode | undefined} path={[parentData, nodeData].filter(Boolean) as TaxonNode[] | undefined} children={childrenData as TaxonNode[] | undefined} parentId={parentId} onJump={setCurrentId} rankColor={rankColor} />}
              {tab === 'parts' && <PartsPanel parts={parts.data as any[] | undefined} selectedPartId={selectedPartId} onSelect={setSelectedPartId} />}
              {tab === 'transforms' && (
                <TransformsPanel
                  loading={transforms.isLoading}
                  data={transforms.data as any[] | undefined}
                  chosen={chosen}
                  onToggleTx={onToggleTx}
                  onParamChange={onParamChange}
                />
              )}
              {tab === 'foodstate' && (
                <FoodStatePanel
                  fsPreview={fsPreview}
                  loadingValidate={compose.isFetching}
                  result={compose.data as any}
                  onCopy={(s: string) => navigator.clipboard.writeText(s)}
                  onValidate={() => compose.refetch()}
                  onParse={handleParse}
                />
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
