import { useEffect, useMemo, useState } from 'react'
import { trpc } from './lib/trpc'
import ErrorBoundary from './components/ErrorBoundary'
import { DocsPanel } from './components/inspector/DocsPanel'
import { TaxonPanel } from './components/inspector/TaxonPanel'
import { PartsPanel } from './components/inspector/PartsPanel'
import { TransformsPanel } from './components/inspector/TransformsPanel'
import { FoodStatePanel } from './components/inspector/FoodStatePanel'
import { Button } from '@ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'
import { Badge } from '@ui/badge'
import LeftRail from './components/layout/LeftRail'
import NodeHeader from './components/NodeHeader'
import StructureExplorer from './components/StructureExplorer'

/** Shared types matching API rows */
interface TaxonNode {
  id: string
  name: string
  slug: string
  rank: string
  parentId: string | null
}


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

  // Queries scoped to current node - using new neighborhood API
  const neighborhood = trpc.taxonomy.neighborhood.useQuery(
    { id: currentId!, childLimit: 50, orderBy: 'name' }, 
    { enabled: !!currentId }
  )
  const docs = trpc.docs.getByTaxon.useQuery({ taxonId: currentId! }, { enabled: !!currentId })
  const parts = trpc.taxonomy.partTree.useQuery({ id: currentId! }, { enabled: !!currentId })
  const lineageQ = trpc.taxonomy.pathToRoot.useQuery({ id: currentId! }, { enabled: !!currentId })
  const rankCountsQ = trpc.taxonomy.childrenRankCounts.useQuery({ id: currentId! }, { enabled: !!currentId })

  // Extract data from neighborhood response
  const nodeData = neighborhood.data?.node as TaxonNode | undefined
  const parentData = neighborhood.data?.parent as TaxonNode | undefined
  const childrenData = (neighborhood.data?.children || []) as TaxonNode[]
  const siblingsData = (neighborhood.data?.siblings || []) as TaxonNode[]
  const parentId = parentData?.id ?? null


  // Bootstrap root
  useEffect(() => {
    if (root.data && !currentId) setCurrentId((root.data as TaxonNode).id)
  }, [root.data, currentId])



  // Inspector tabs: Taxon is DEFAULT
  const [tab, setTab] = useState<'taxon' | 'parts' | 'transforms' | 'foodstate'>('taxon')

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
    const pathSlugs = (lineageQ.data?.map((n: any) => n.slug) ?? (nodeData ? [nodeData.slug] : []))
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

  return (
    <div className="p-4">
      {/* Top status bar */}
      <div className="mb-3 flex items-center justify-between">
        <div className="text-lg font-semibold tracking-tight">Nutrition Graph Workbench</div>
        <div className="flex items-center gap-2 text-xs">
          <div className="hidden lg:flex text-xs text-muted-foreground px-2 py-1 rounded-md border bg-muted/30">
            Press <kbd className="mx-1 rounded border bg-background px-1">⌘</kbd><span>K</span> to search
          </div>
          {health.data?.ok ? (
            <Badge className="border-green-600">API: OK</Badge>
          ) : (
            <Badge className="border-red-600">API: down</Badge>
          )}
        </div>
      </div>

      {/* Desktop layout: Left rail / Center canvas / Right rail */}
      <div className="grid grid-cols-[280px,1fr,420px] gap-3 h-[calc(100vh-84px)]">
        {/* Left: Search, Filters, Outline */}
        <LeftRail
          rankColor={rankColor}
          rootId={(root.data as any)?.id}
          currentId={currentId ?? ''}
          onPick={(id) => setCurrentId(id)}
        />

        {/* Center: Header + Two-up panels */}
        <div className="min-h-0 flex flex-col">
          <Card className="flex-1 min-h-0 flex flex-col">
            <CardHeader className="border-b">
              <ErrorBoundary>
                <NodeHeader
                  loading={neighborhood.isLoading}
                  lineage={lineageQ.data as any[] | undefined}
                  node={nodeData}
                  siblings={siblingsData}
                  rankColor={rankColor}
                  onJump={(id) => setCurrentId(id)}
                />
              </ErrorBoundary>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 flex gap-3 pt-3">
              {/* LEFT: Docs */}
              <Card className="min-h-0 flex flex-col flex-1">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Documentation</CardTitle>
                </CardHeader>
                <CardContent className="flex-1 min-h-0 overflow-auto">
                  <ErrorBoundary>
                    <DocsPanel docs={docs.data as any} node={nodeData as any} />
                  </ErrorBoundary>
                </CardContent>
              </Card>
              {/* RIGHT: Structure Explorer */}
              <Card className="min-h-0 flex flex-col flex-1">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Structure</CardTitle>
                </CardHeader>
                <CardContent className="flex-1 min-h-0 overflow-hidden">
                  <ErrorBoundary>
                    <StructureExplorer
                      node={nodeData as any}
                      childrenRows={childrenData}
                      siblings={siblingsData}
                      rankCounts={rankCountsQ.data as any[] | undefined}
                      rankColor={rankColor}
                      onPick={(id) => setCurrentId(id)}
                    />
                  </ErrorBoundary>
                </CardContent>
              </Card>
            </CardContent>
          </Card>
        </div>

        {/* Right rail: Parts / Transforms / FoodState composer */}
        <div className="min-h-0 flex flex-col gap-3">
          <Card className="flex-1 min-h-0 flex flex-col">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Parts & Transforms</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-0 overflow-auto space-y-3">
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant={tab === 'taxon' ? 'default' : 'outline'} onClick={() => setTab('taxon')}>Taxon</Button>
                <Button size="sm" variant={tab === 'parts' ? 'default' : 'outline'} onClick={() => setTab('parts')}>Parts</Button>
                <Button size="sm" variant={tab === 'transforms' ? 'default' : 'outline'} onClick={() => setTab('transforms')}>Transforms</Button>
                <Button size="sm" variant={tab === 'foodstate' ? 'default' : 'outline'} onClick={() => setTab('foodstate')}>FoodState</Button>
              </div>

              <div className="min-h-0">
                {tab === 'taxon' && (
                  <TaxonPanel
                    node={nodeData as any}
                    path={(lineageQ.data as any[] | undefined)}
                    children={childrenData as any}
                    parentId={parentId}
                    onJump={(id) => setCurrentId(id)}
                    rankColor={rankColor}
                  />
                )}
                {tab === 'parts' && (
                  <PartsPanel
                    parts={parts.data as any}
                    selectedPartId={selectedPartId}
                    onSelect={setSelectedPartId}
                  />
                )}
                {tab === 'transforms' && (
                  <>
                    {!selectedPartId ? (
                      <div className="text-sm text-muted-foreground">Select a part to view transforms.</div>
                    ) : (
                      <TransformsPanel
                        loading={transforms.isLoading}
                        data={transforms.data as any}
                        chosen={chosen}
                        onToggleTx={onToggleTx}
                        onParamChange={onParamChange}
                      />
                    )}
                  </>
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
    </div>
  )
}
