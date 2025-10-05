import { createFileRoute, useNavigate } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'
import { Badge } from '@ui/badge'
import { Button } from '@ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@ui/table'
import { DocsPanel } from '@/components/inspector/DocsPanel'
import StructureExplorer from '@/components/StructureExplorer'
import NodeHeader from '@/components/NodeHeader'
import { RANK_COLOR } from '@/lib/constants'
import ErrorBoundary from '@/components/ErrorBoundary'

export const Route = createFileRoute('/workbench/taxon/$id')({
    validateSearch: (s: Record<string, unknown>) => {
        const tab = typeof s.tab === 'string' && ['overview', 'lists'].includes(s.tab) ? s.tab : 'overview'
        const limit = Number.isFinite(Number(s.limit)) ? Math.max(10, Math.min(500, Number(s.limit))) : 50
        return { tab, limit }
    },
    component: TaxonPage,
})

function TaxonPage() {
    const { id } = Route.useParams()
    const navigate = useNavigate()
    const search = Route.useSearch() as { tab: string; limit: number }

    const setSearch = (patch: Partial<typeof search>) => {
        const newSearch = { ...search, ...patch }

        navigate({
            to: '/workbench/taxon/$id',
            params: { id },
            search: newSearch
        })
    }

    // Queries
    const neighborhood = trpc.taxonomy.neighborhood.useQuery(
        { id, childLimit: search.limit, orderBy: 'name' },
        { enabled: !!id, keepPreviousData: true }
    )
    const lineageQ = trpc.taxonomy.pathToRoot.useQuery({ id }, { enabled: !!id })
    const docs = trpc.docs.getByTaxon.useQuery({ taxonId: id }, { enabled: !!id })
    const familiesQ = trpc.facets.familiesForTaxon.useQuery(
        { taxonId: id, limit: 20 },
        { enabled: !!id }
    )

    // Overlay data query - always fetch all overlay data
    const overlayDataQ = trpc.facets.overlayDataForTaxon.useQuery(
        {
            taxonId: id
        },
        { enabled: !!id }
    )

    // Extract data
    const nodeData = neighborhood.data?.node
    const parentData = neighborhood.data?.parent
    const childrenData = (neighborhood.data?.children || []) as any[]
    const siblingsData = (neighborhood.data?.siblings || []) as any[]
    const childCount = (neighborhood.data as any)?.childCount ?? childrenData.length
    const parentId = parentData?.id ?? null

    const handleShowMore = () => {
        setSearch({ limit: search.limit + 50 })
    }

    const handleJump = (targetId: string) => {
        navigate({ to: '/workbench/taxon/$id', params: { id: targetId } })
    }

    const handleFamilyClick = (family: string) => {
        navigate({
            to: '/workbench/families',
            search: { family, taxonId: id }
        })
    }


    if (neighborhood.isLoading) {
        return (
            <div className="p-4">
                <div className="text-lg font-semibold">Loading...</div>
            </div>
        )
    }

    if (!nodeData) {
        return (
            <div className="p-4">
                <div className="text-lg font-semibold">Taxon Not Found</div>
                <div className="text-sm text-muted-foreground">The requested taxon could not be found.</div>
                <Button
                    className="mt-2"
                    onClick={() => navigate({ to: '/workbench' })}
                >
                    Back to Workbench
                </Button>
            </div>
        )
    }

    return (
        <div className="min-h-0 flex flex-col">
            <Card className="flex-1 min-h-0 flex flex-col">
                <CardHeader className="border-b">
                    <ErrorBoundary>
                        <NodeHeader
                            loading={neighborhood.isLoading}
                            lineage={lineageQ.data as any[] | undefined}
                            node={nodeData}
                            rankColor={RANK_COLOR}
                            onJump={handleJump}
                        />
                    </ErrorBoundary>
                </CardHeader>
                <CardContent className="flex-1 min-h-0 p-0">
                    <Tabs value={search.tab} onValueChange={(value) => setSearch({ tab: value })} className="h-full flex flex-col">
                        <TabsList className="mx-4 mt-4">
                            <TabsTrigger value="overview">Overview</TabsTrigger>
                            <TabsTrigger value="lists">Lists</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="flex-1 min-h-0 p-4 overflow-hidden">
                            <div className="grid grid-cols-2 gap-4 h-full">
                                {/* Left: Docs */}
                                <Card className="flex flex-col h-full min-h-0">
                                    <CardHeader className="pb-2 flex-shrink-0">
                                        <CardTitle className="text-sm">Documentation</CardTitle>
                                    </CardHeader>
                                    <div className="flex-1 min-h-0 overflow-auto p-4">
                                        <ErrorBoundary>
                                            <DocsPanel docs={docs.data as any} node={nodeData as any} />
                                        </ErrorBoundary>
                                    </div>
                                </Card>

                                {/* Right: Structure and Families */}
                                <div className="flex flex-col h-full min-h-0 gap-4">
                                    {/* Structure - takes remaining space */}
                                    <Card className="flex flex-col flex-1 min-h-0">
                                        <CardHeader className="pb-2 flex-shrink-0">
                                            <CardTitle className="text-sm">Structure</CardTitle>
                                        </CardHeader>
                                        <div className="flex-1 min-h-0 overflow-auto p-4">
                                            <ErrorBoundary>
                                                <StructureExplorer
                                                    node={nodeData as any}
                                                    childrenRows={childrenData}
                                                    siblings={siblingsData}
                                                    childCount={childCount}
                                                    rankColor={RANK_COLOR}
                                                    onPick={handleJump}
                                                    parent={parentData ? { id: parentData.id, name: parentData.name } : null}
                                                    hasMore={childCount > childrenData.length}
                                                    onShowMore={handleShowMore}
                                                />
                                            </ErrorBoundary>
                                        </div>
                                    </Card>

                                    {/* Families - only if data exists, takes minimal space */}
                                    {familiesQ?.data && familiesQ.data.length > 0 && (
                                        <Card className="flex-shrink-0">
                                            <CardHeader className="pb-2">
                                                <CardTitle className="text-sm">Families under this taxon</CardTitle>
                                            </CardHeader>
                                            <CardContent className="max-h-32 overflow-auto">
                                                <div className="flex flex-wrap gap-2">
                                                    {familiesQ.data.map((f: any) => (
                                                        <Badge
                                                            key={f.family}
                                                            variant="secondary"
                                                            className="cursor-pointer hover:bg-secondary/80"
                                                            onClick={() => handleFamilyClick(f.family)}
                                                        >
                                                            {f.family} ({f.count})
                                                        </Badge>
                                                    ))}
                                                </div>
                                            </CardContent>
                                        </Card>
                                    )}
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="lists" className="flex-1 min-h-0 p-4 overflow-hidden">
                            <div className="space-y-4">
                                <div className="flex items-center justify-between">
                                    <div className="flex items-center gap-2">
                                        <span className="text-sm font-medium">
                                            Children ({childCount})
                                        </span>
                                        {childrenData.length > 0 && (
                                            <Badge variant="secondary" className="text-xs">
                                                {childrenData[0].rank}
                                            </Badge>
                                        )}
                                    </div>
                                    {childCount > childrenData.length && (
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            onClick={handleShowMore}
                                        >
                                            Show More ({childCount - childrenData.length} remaining)
                                        </Button>
                                    )}
                                </div>

                                <div className="space-y-3">
                                    {childrenData.map((child) => {
                                        const overlayData = overlayDataQ.data?.[child.id] || {}
                                        return (
                                            <Card
                                                key={child.id}
                                                className="cursor-pointer hover:bg-muted/50 transition-colors"
                                                onClick={() => handleJump(child.id)}
                                            >
                                                <CardContent className="p-4">
                                                    <div className="space-y-3">
                                                        {/* Header: Name and basic info */}
                                                        <div className="flex items-start justify-between">
                                                            <div>
                                                                <h3 className="font-semibold text-lg">{child.name}</h3>
                                                                <p className="text-sm text-muted-foreground">/{child.slug}</p>
                                                            </div>
                                                            {overlayData._docs && (
                                                                <Badge variant="default" className="text-xs">
                                                                    Docs Available
                                                                </Badge>
                                                            )}
                                                        </div>

                                                        {/* Overlay data in organized sections */}
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                                                            {/* Left column */}
                                                            <div className="space-y-2">
                                                                {overlayData._parts && overlayData._parts.length > 0 && (
                                                                    <div>
                                                                        <span className="text-muted-foreground font-medium text-xs uppercase tracking-wide">Parts</span>
                                                                        <div className="flex flex-wrap gap-1 mt-1">
                                                                            {overlayData._parts.map((part: string, i: number) => (
                                                                                <Badge key={i} variant="outline" className="text-xs">
                                                                                    {part}
                                                                                </Badge>
                                                                            ))}
                                                                        </div>
                                                                    </div>
                                                                )}

                                                                {overlayData._families && overlayData._families.length > 0 && (
                                                                    <div>
                                                                        <span className="text-muted-foreground font-medium text-xs uppercase tracking-wide">Families</span>
                                                                        <div className="flex flex-wrap gap-1 mt-1">
                                                                            {overlayData._families.map((family: string, i: number) => (
                                                                                <Badge key={i} variant="secondary" className="text-xs">
                                                                                    {family.replace(/_/g, ' ').toLowerCase()}
                                                                                </Badge>
                                                                            ))}
                                                                        </div>
                                                                    </div>
                                                                )}
                                                            </div>

                                                            {/* Right column */}
                                                            <div className="space-y-2">
                                                                {overlayData._cuisines && overlayData._cuisines.length > 0 && (
                                                                    <div>
                                                                        <span className="text-muted-foreground font-medium text-xs uppercase tracking-wide">Cuisines</span>
                                                                        <div className="flex flex-wrap gap-1 mt-1">
                                                                            {overlayData._cuisines.map((cuisine: string, i: number) => (
                                                                                <Badge key={i} variant="default" className="text-xs">
                                                                                    {cuisine}
                                                                                </Badge>
                                                                            ))}
                                                                        </div>
                                                                    </div>
                                                                )}

                                                                {overlayData._flags && overlayData._flags.length > 0 && (
                                                                    <div>
                                                                        <span className="text-muted-foreground font-medium text-xs uppercase tracking-wide">Flags</span>
                                                                        <div className="flex flex-wrap gap-1 mt-1">
                                                                            {overlayData._flags.map((flag: string, i: number) => (
                                                                                <Badge key={i} variant="destructive" className="text-xs">
                                                                                    {flag.replace(/_/g, ' ')}
                                                                                </Badge>
                                                                            ))}
                                                                        </div>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        </div>

                                                        {/* Footer: ID */}
                                                        <div className="pt-2 border-t border-muted">
                                                            <p className="text-xs text-muted-foreground font-mono">{child.id}</p>
                                                        </div>
                                                    </div>
                                                </CardContent>
                                            </Card>
                                        )
                                    })}
                                </div>

                                {childrenData.length === 0 && (
                                    <div className="text-center text-muted-foreground py-8">
                                        No children found
                                    </div>
                                )}
                            </div>
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>
        </div>
    )
}
