import { createFileRoute, useNavigate } from '@tanstack/react-router'
import React, { useState } from 'react'
import { trpc } from '@/lib/trpc'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'
import { Badge } from '@ui/badge'
import { Button } from '@ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@ui/table'
import { Input } from '@ui/input'
import { TransformsPanel } from '@/components/inspector/TransformsPanel'
import { FoodStatePanel } from '@/components/inspector/FoodStatePanel'
import { TPCompare } from '@/components/tp/TPCompare'
import { TPTComparePanel } from '@/components/tp/TPTComparePanel'
import ErrorBoundary from '@/components/ErrorBoundary'

export const Route = createFileRoute('/workbench/tp/$taxonId/$partId')({
    validateSearch: (s: Record<string, unknown>) => {
        const tab = typeof s.tab === 'string' ? s.tab : 'overview'
        const family = typeof s.family === 'string' ? s.family : ''
        const limit = Number.isFinite(Number(s.limit)) ? Math.max(10, Math.min(500, Number(s.limit))) : 50
        const offset = Number.isFinite(Number(s.offset)) ? Math.max(0, Number(s.offset)) : 0
        const compare = typeof s.compare === 'string' ? s.compare : ''
        return { tab, family, limit, offset, compare }
    },
    component: TPPage,
})

function TPPage() {
    const { taxonId, partId } = Route.useParams()
    const navigate = useNavigate()
    const search = Route.useSearch() as {
        tab: string;
        family: string;
        limit: number;
        offset: number;
        compare: string
    }
    const setSearch = (patch: Partial<typeof search>) =>
        navigate({
            to: '/workbench/tp/$taxonId/$partId',
            params: { taxonId, partId },
            search: (s: any) => ({ ...s, ...patch })
        })

    // Queries
    const taxonQ = trpc.taxonomy.getById.useQuery({ id: taxonId }, { enabled: !!taxonId })
    const partQ = trpc.taxonomy.getPartById.useQuery({ id: partId }, { enabled: !!partId })
    const familiesQ = (trpc as any).facets?.familiesForTaxonPart?.useQuery(
        { taxonId, partId },
        { enabled: !!taxonId && !!partId }
    )
    const tptListQ = (trpc as any).tpt?.listForTP?.useQuery(
        {
            taxonId,
            partId,
            family: search.family || undefined,
            limit: search.limit,
            offset: search.offset
        },
        { enabled: !!taxonId && !!partId }
    )
    const transformsQ = trpc.taxonomy.getTransformsFor.useQuery(
        { taxonId, partId, identityOnly: false },
        { enabled: !!taxonId && !!partId }
    )

    const handleFamilyFilter = (family: string) => {
        if (search.family === family) {
            setSearch({ family: '', offset: 0 })
        } else {
            setSearch({ family, offset: 0 })
        }
    }

    const handleTPTClick = (tptId: string) => {
        navigate({ to: '/workbench/tpt/$id', params: { id: tptId } })
    }

    const handlePinTPT = (tptId: string) => {
        const currentCompare = search.compare ? search.compare.split(',') : []
        if (currentCompare.includes(tptId)) {
            // Remove from compare
            const newCompare = currentCompare.filter(id => id !== tptId).join(',')
            setSearch({ compare: newCompare })
        } else if (currentCompare.length < 2) {
            // Add to compare
            const newCompare = [...currentCompare, tptId].join(',')
            setSearch({ compare: newCompare })
        }
    }

    const handleShowMore = () => {
        setSearch({ limit: search.limit + 50 })
    }

    const taxon = taxonQ.data
    const part = partQ.data
    const families = familiesQ?.data || []
    const tptRows = tptListQ?.data?.rows || []
    const tptTotal = tptListQ?.data?.total || 0

    if (taxonQ.isLoading || partQ.isLoading) {
        return (
            <div className="p-4">
                <div className="text-lg font-semibold">Loading...</div>
            </div>
        )
    }

    if (!taxon || !part) {
        return (
            <div className="p-4">
                <div className="text-lg font-semibold">Not Found</div>
                <div className="text-sm text-muted-foreground">
                    The requested taxon or part could not be found.
                </div>
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
                    <div className="flex items-center gap-2">
                        <div className="text-lg font-semibold">{taxon.name}</div>
                        <div className="text-muted-foreground">·</div>
                        <div className="text-lg font-semibold">{part.name}</div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                        {taxonId} · {partId}
                    </div>
                </CardHeader>
                <CardContent className="flex-1 min-h-0 p-0">
                    <Tabs value={search.tab} onValueChange={(value) => setSearch({ tab: value })} className="h-full flex flex-col">
                        <TabsList className="mx-4 mt-4">
                            <TabsTrigger value="overview">Overview</TabsTrigger>
                            <TabsTrigger value="transforms">Transforms</TabsTrigger>
                            <TabsTrigger value="compare">Compare</TabsTrigger>
                        </TabsList>

                        <TabsContent value="overview" className="flex-1 min-h-0 p-4">
                            <div className="space-y-4">
                                {/* Family filters */}
                                {families.length > 0 && (
                                    <div className="space-y-2">
                                        <div className="text-sm font-medium">Filter by Family</div>
                                        <div className="flex flex-wrap gap-2">
                                            {families.map((f: any) => (
                                                <Badge
                                                    key={f.family}
                                                    variant={search.family === f.family ? "default" : "secondary"}
                                                    className="cursor-pointer hover:bg-secondary/80"
                                                    onClick={() => handleFamilyFilter(f.family)}
                                                >
                                                    {f.family} ({f.count})
                                                </Badge>
                                            ))}
                                        </div>
                                    </div>
                                )}

                                {/* TPT Table */}
                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <div className="text-sm font-medium">
                                            TPTs ({tptTotal})
                                        </div>
                                        {tptTotal > tptRows.length && (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={handleShowMore}
                                            >
                                                Show More ({tptTotal - tptRows.length} remaining)
                                            </Button>
                                        )}
                                    </div>

                                    <div className="rounded-md border">
                                        <Table>
                                            <TableHeader>
                                                <TableRow>
                                                    <TableHead>Name</TableHead>
                                                    <TableHead>Family</TableHead>
                                                    <TableHead>ID</TableHead>
                                                    <TableHead>Actions</TableHead>
                                                </TableRow>
                                            </TableHeader>
                                            <TableBody>
                                                {tptRows.map((tpt: any) => (
                                                    <TableRow
                                                        key={tpt.id}
                                                        className="cursor-pointer hover:bg-muted/50"
                                                        onClick={() => handleTPTClick(tpt.id)}
                                                    >
                                                        <TableCell className="font-medium">
                                                            {tpt.name || `${taxon.name} ${part.name}`}
                                                        </TableCell>
                                                        <TableCell>
                                                            <Badge variant="secondary" className="text-xs">
                                                                {tpt.family}
                                                            </Badge>
                                                        </TableCell>
                                                        <TableCell className="text-xs text-muted-foreground font-mono">
                                                            {tpt.id}
                                                        </TableCell>
                                                        <TableCell>
                                                            <Button
                                                                size="sm"
                                                                variant="outline"
                                                                onClick={(e) => {
                                                                    e.stopPropagation()
                                                                    handlePinTPT(tpt.id)
                                                                }}
                                                            >
                                                                {search.compare.includes(tpt.id) ? 'Unpin' : 'Pin'}
                                                            </Button>
                                                        </TableCell>
                                                    </TableRow>
                                                ))}
                                            </TableBody>
                                        </Table>
                                    </div>

                                    {tptRows.length === 0 && (
                                        <div className="text-center text-muted-foreground py-8">
                                            {search.family ? 'No TPTs found for this family' : 'No TPTs found'}
                                            {search.family && (
                                                <Button
                                                    className="mt-2"
                                                    size="sm"
                                                    variant="outline"
                                                    onClick={() => setSearch({ family: '', offset: 0 })}
                                                >
                                                    Clear family filter
                                                </Button>
                                            )}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </TabsContent>

                        <TabsContent value="transforms" className="flex-1 min-h-0 p-4">
                            <ErrorBoundary>
                                <TransformsPanel
                                    loading={transformsQ.isLoading}
                                    data={transformsQ.data as any}
                                    chosen={[]}
                                    onToggleTx={() => { }} // Read-only mode
                                    onParamChange={() => { }} // Read-only mode
                                    readOnly={true}
                                />
                            </ErrorBoundary>
                        </TabsContent>

                        <TabsContent value="compare" className="flex-1 min-h-0 p-4">
                            <TPTComparePanel
                                compare={search.compare}
                                onSetCompare={(ids) => setSearch({ compare: ids.join(',') })}
                            />
                        </TabsContent>
                    </Tabs>
                </CardContent>
            </Card>
        </div>
    )
}
