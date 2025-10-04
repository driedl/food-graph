import { memo, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from '@tanstack/react-router'
import { Outlet } from '@tanstack/react-router'
import { trpc } from '../../lib/trpc'
import ErrorBoundary from '../ErrorBoundary'
import { DocsPanel } from '../inspector/DocsPanel'
import { TaxonPanel } from '../inspector/TaxonPanel'
import { PartsPanel } from '../inspector/PartsPanel'
import { TransformsPanel } from '../inspector/TransformsPanel'
import { FoodStatePanel } from '../inspector/FoodStatePanel'
import { Button } from '@ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'
import { Badge } from '@ui/badge'
import LeftRail from './LeftRail'
import NodeHeader from '../NodeHeader'
import StructureExplorer from '../StructureExplorer'
import { fsToPath, pathToFs, pathToNodeId } from '../../lib/fs-url'
import { RANK_COLOR } from '../../lib/constants'
import { useGlobalHotkeys } from '../../hooks/useGlobalHotkeys'
import { useNavigationHelpers } from '../../lib/nav'

/** Shared types matching API rows */
interface TaxonNode {
    id: string
    name: string
    slug: string
    rank: string
    parentId: string | null
}

const rankColor = RANK_COLOR

export default function AppShell() {
    const router = useRouter()
    const lastFsRef = useRef<string>('') // idempotence for FS derivation
    const nav = useNavigationHelpers()

    // Global hotkeys
    useGlobalHotkeys()

    // API health + root bootstrap
    const health = trpc.health.useQuery()
    const root = trpc.taxonomy.getRoot.useQuery(undefined, { refetchOnWindowFocus: false })

    // Focus / navigation state
    const [currentId, setCurrentId] = useState<string | null>(null)

    // Queries scoped to current node - using new neighborhood API
    const [childLimit, setChildLimit] = useState(50)
    const neighborhood = trpc.taxonomy.neighborhood.useQuery(
        { id: currentId!, childLimit, orderBy: 'name' },
        { enabled: !!currentId, keepPreviousData: true }
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

    // Bootstrap root
    useEffect(() => {
        // Only bootstrap to root if we are NOT already deep-linking via /workbench/node/:id or /workbench/fs/*
        if (root.data && !currentId) {
            const { pathname } = window.location
            if (pathToFs(pathname) || pathToNodeId(pathname)) return
            setCurrentId((root.data as TaxonNode).id)
        }
    }, [root.data, currentId])
    // Reset limit when node changes
    useEffect(() => { setChildLimit(50) }, [currentId])

    // --- URL → State (sync state from URL whenever location changes) ----------
    useEffect(() => {
        const applyFromLocation = async () => {
            const { pathname } = router.state.location
            const currentPath = lastPathRef.current

            // Skip if this is the path we just wrote (prevents loops)
            if (pathname === currentPath && currentPath !== '') {
                return
            }

            // Set flags and update lastPathRef BEFORE setting any state to prevent State→URL from interfering
            isApplyingFromUrl.current = true
            isParsingUrl.current = true // Prevent auto-clear of selectedPartId
            lastPathRef.current = pathname // Update BEFORE state changes to prevent State→URL from overwriting

            const fs = pathToFs(pathname)
            const nodeId = pathToNodeId(pathname)

            if (fs) {
                await handleParse(fs) // will set currentId, selectedPartId
            } else if (nodeId) {
                setCurrentId(nodeId)
                setSelectedPartId('')
                setChosen([])
            }

            isApplyingFromUrl.current = false
            isParsingUrl.current = false
        }
        applyFromLocation()
    }, [router.state.location.pathname])

    // Right-rail tabs
    const [tab, setTab] = useState<'taxon' | 'pt' | 'foodstate'>('taxon')

    // Parts/Transforms builder state
    // Always store WITHOUT the `part:` prefix internally
    const [selectedPartId, setSelectedPartId] = useState<string>('')
    const isParsingUrl = useRef(false) // Track when parsing URL to prevent auto-clear
    useEffect(() => {
        // Don't auto-clear part when we're syncing from URL
        if (!isParsingUrl.current) {
            setSelectedPartId('')
        }
    }, [currentId])
    const transforms = trpc.taxonomy.getTransformsFor.useQuery(
        { taxonId: currentId || '', partId: selectedPartId || '', identityOnly: false },
        { enabled: !!currentId && !!selectedPartId && selectedPartId.startsWith('part:') }
    )

    type ChosenTx = { id: string; params: Record<string, any> }
    const [chosen, setChosen] = useState<ChosenTx[]>([])
    useEffect(() => { setChosen([]) }, [selectedPartId, currentId])
    // When FS parse provided a tentative transform list, stage it here and hydrate after transforms load
    const pendingFromParse = useRef<ChosenTx[] | null>(null)

    // Once transform metadata is available, accept only identity transforms that exist for this part
    useEffect(() => {
        if (!transforms.data || !pendingFromParse.current) return
        const ids = new Map(transforms.data.map((t: any) => [t.id, !!t.identity]))
        const filtered = (pendingFromParse.current || []).filter((t) => ids.has(t.id) && ids.get(t.id))
        setChosen(filtered)
        pendingFromParse.current = null
    }, [transforms.data])

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
        // Wait for lineage to load - don't build partial paths
        if (!lineageQ.data || lineageQ.data.length === 0) return ''
        const pathSlugs = lineageQ.data.map((n: any) => n.slug)
        if (!pathSlugs.length) return ''
        const segs: string[] = [`fs:/${pathSlugs.join('/')}`]
        // FS requires explicit segment tags; we store part ids WITHOUT the prefix
        if (selectedPartId) {
            const partId = `part:${selectedPartId}`
            segs.push(partId)
        }
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
                // Prefix each transform with tx:
                return p ? `tx:${t.id}{${p}}` : `tx:${t.id}`
            }).join('/')
            if (chain) segs.push(chain)
        }
        return segs.join('/')
    }, [lineageQ.data, selectedPartId, chosen, currentId, lineageQ.isLoading])

    // Optional server validation using existing foodstate.compose (query)
    const compose = trpc.foodstate.compose.useQuery(
        { taxonId: currentId || '', partId: selectedPartId || '', transforms: chosen },
        { enabled: false && !!currentId && !!selectedPartId && selectedPartId.startsWith('part:') }
    )

    // tRPC-powered FS parse (typed)
    const [fsToParse, setFsToParse] = useState<string | null>(null)
    const parseQ = trpc.foodstate.parse.useQuery(
        { fs: fsToParse || '' },
        { enabled: !!fsToParse, retry: 0 }
    )
    useEffect(() => {
        const parsed: any = parseQ.data
        if (!fsToParse || !parsed) return
        try {
            if (parsed.taxonPath && parsed.taxonPath.length > 0) {
                const kingdoms = ['plantae', 'animalia', 'fungi']
                const kingdomIndex = parsed.taxonPath.findIndex((slug: string) => kingdoms.includes(slug))
                if (kingdomIndex >= 0) {
                    const taxonomicPath = parsed.taxonPath.slice(kingdomIndex)
                    const taxonId = 'tx:' + taxonomicPath.join(':')
                    setCurrentId(taxonId)
                } else {
                    console.warn('[Parser] No kingdom found in path:', parsed.taxonPath)
                }
            }
            if (parsed.partId) {
                // parsed.partId already includes the part: prefix from the API
                setSelectedPartId(parsed.partId)
            }
            if (parsed.transforms && parsed.transforms.length) {
                pendingFromParse.current = parsed.transforms.map((t: any) => ({
                    id: t.id.replace(/^tx:/, ''),
                    params: t.params ?? {},
                }))
            } else {
                pendingFromParse.current = null
            }
        } finally {
            setFsToParse(null)
        }
    }, [parseQ.data, fsToParse])
    const handleParse = async (fs: string) => {
        setFsToParse(fs)
    }

    // --- State → URL (push new history entries when state changes) ------------
    const lastPathRef = useRef<string>('')
    const isApplyingFromUrl = useRef(false) // Track when we're syncing FROM url to prevent loops

    useEffect(() => {
        if (!currentId || isApplyingFromUrl.current) return
        // Hold only while we are actively applying from URL (not just because we are on an FS route)
        if (isParsingUrl.current && !selectedPartId && !chosen.length) {
            return
        }
        const fs = fsPreview
        // If we intend to write an FS URL (because part/tx is present) but don't
        // have enough data to build it yet, don't downgrade to /node/:id.
        // Wait for lineage to load (it will trigger this effect again when ready).
        if ((selectedPartId || chosen.length) && !fs) {
            return
        }
        // Prefer fs form when part/tx chosen; fallback to node form for "just node"
        const targetPath =
            fs && (selectedPartId || chosen.length)
                ? fsToPath(fs)
                : `/workbench/node/${currentId}`

        // Idempotence: avoid churn if FS string hasn't meaningfully changed
        if (fs) {
            if (fs !== lastFsRef.current) {
                lastFsRef.current = fs
            } else if (targetPath === lastPathRef.current) {
                return
            }
        }

        if (targetPath && targetPath !== lastPathRef.current) {
            const isFirstWrite = !lastPathRef.current
            // Update lastPathRef BEFORE navigation so it's available immediately
            lastPathRef.current = targetPath
            // Use router.navigate to properly update TanStack Router state
            router.navigate({ to: targetPath, replace: isFirstWrite })
        }
    }, [currentId, fsPreview, selectedPartId, chosen, lineageQ.data, router])

    return (
        <div className="p-4">
            {/* Top status bar */}
            <div className="mb-3 flex items-center justify-between">
                <div className="text-lg font-semibold tracking-tight">Food Graph Workbench</div>
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

            {/* Navigation bar */}
            <div className="mb-3 flex items-center gap-1 text-sm">
                <Button variant="ghost" size="sm" onClick={nav.gotoFamilies}>
                    Families
                </Button>
                <Button variant="ghost" size="sm" onClick={nav.gotoCuisines}>
                    Cuisines
                </Button>
                <Button variant="ghost" size="sm" onClick={nav.gotoFlags}>
                    Flags
                </Button>
                <Button variant="ghost" size="sm" onClick={nav.gotoSearch}>
                    Search
                </Button>
                <Button variant="ghost" size="sm" onClick={nav.gotoMeta}>
                    Meta
                </Button>
            </div>

            {/* Desktop layout: Left rail / Center canvas / Right rail */}
            <div className="grid grid-cols-[280px,1fr,420px] gap-3 h-[calc(100vh-84px)]">
                {/* Left: Search, Filters, Outline */}
                <LeftRail
                    rankColor={rankColor}
                    rootId={(root.data as any)?.id}
                    currentId={currentId ?? ''}
                    onPick={(id) => {
                        setSelectedPartId('')   // leaving FS flow → plain taxon view
                        setChosen([])
                        setTab('taxon')
                        setCurrentId(id)
                    }}
                    onPickTP={(taxonId, partId) => {
                        setCurrentId(taxonId)
                        // partId from search results already includes the part: prefix
                        setSelectedPartId(partId)
                        setChosen([])
                        setTab('pt')
                    }}
                />

                {/* Center: Page content via Outlet */}
                <div className="min-h-0 flex flex-col">
                    <ErrorBoundary>
                        <Outlet />
                    </ErrorBoundary>
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
                                <Button size="sm" variant={tab === 'pt' ? 'default' : 'outline'} onClick={() => setTab('pt')}>Parts+Transforms</Button>
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
                                {tab === 'pt' && (
                                    <div className="grid grid-cols-2 gap-3 min-h-0">
                                        <div className="min-h-0 overflow-auto">
                                            <PartsPanel
                                                parts={parts.data as any}
                                                selectedPartId={selectedPartId}
                                                onSelect={(id) => setSelectedPartId(id)}
                                            />
                                        </div>
                                        <div className="min-h-0 overflow-auto">
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
                                        </div>
                                    </div>
                                )}
                                {tab === 'foodstate' && (
                                    <FoodStatePanel
                                        fsPreview={fsPreview}
                                        loadingValidate={compose.isFetching}
                                        result={compose.data as any}
                                        onCopy={(s: string) => navigator.clipboard.writeText(s)}
                                        onValidate={() => compose.refetch()}
                                        onParse={handleParse}
                                        permalink={typeof window !== 'undefined' ? window.location.href : undefined}
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
