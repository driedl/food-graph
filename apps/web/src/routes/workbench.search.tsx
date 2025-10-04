import { createFileRoute, useNavigate } from '@tanstack/react-router'
import React, { useMemo } from 'react'
import { trpc } from '@/lib/trpc'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'
import { Separator } from '@ui/separator'

type ResultKind = 'any' | 'taxon' | 'tp' | 'tpt'

export const Route = createFileRoute('/workbench/search')({
    validateSearch: (s: Record<string, unknown>) => {
        const q = typeof s.q === 'string' ? s.q : ''
        const type: ResultKind = (['any', 'taxon', 'tp', 'tpt'] as const).includes(s.type as any) ? (s.type as ResultKind) : 'any'
        const taxonId = typeof s.taxonId === 'string' ? s.taxonId : ''
        const partId = typeof s.partId === 'string' ? s.partId : ''
        const family = typeof s.family === 'string' ? s.family : ''
        const limit = Number.isFinite(Number(s.limit)) ? Math.max(1, Math.min(20, Number(s.limit))) : 20
        const offset = Number.isFinite(Number(s.offset)) ? Math.max(0, Number(s.offset)) : 0
        return { q, type, taxonId, partId, family, limit, offset }
    },
    component: SearchQAPage,
})

function SearchQAPage() {
    const navigate = useNavigate()
    const search = Route.useSearch() as {
        q: string; type: ResultKind; taxonId: string; partId: string; family: string; limit: number; offset: number
    }
    const setSearch = (patch: Partial<typeof search>) =>
        navigate({ to: '/workbench/search', search: (s: any) => ({ ...s, ...patch }) })

    const queryQ = (trpc as any).search?.query?.useQuery({
        q: search.q || '',
        type: search.type === 'any' ? undefined : search.type,
        taxonId: search.taxonId || undefined,
        partId: search.partId || undefined,
        family: search.family || undefined,
        limit: search.limit,
        offset: search.offset,
        withScores: true,
        debug: true,
    }, { enabled: !!search.q })

    const rows: any[] = queryQ?.data?.rows ?? []
    const total: number = queryQ?.data?.total ?? rows.length
    const facets = queryQ?.data?.facets ?? {}

    const gotoTaxon = (id: string) => navigate({ to: '/workbench/taxon/$id', params: { id } })
    const gotoTP = (taxonId: string, partId: string) =>
        navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId } })
    const gotoTPT = (id: string) => navigate({ to: '/workbench/tpt/$id', params: { id } })

    const kindBadge = (k: string) => {
        const label = k === 'tp' ? 'food' : k
        return <Badge variant="secondary" className="text-[10px] uppercase">{label}</Badge>
    }

    const colHint = useMemo(() => {
        return search.type === 'tpt' ? 'family' : search.type === 'tp' ? 'part' : 'rank'
    }, [search.type])

    return (
        <div className="p-4 space-y-3">
            <div className="text-lg font-semibold">Search QA</div>

            {/* query bar */}
            <div className="grid grid-cols-[1fr_auto_auto_auto] gap-2 items-center">
                <Input
                    placeholder='Query (e.g. "buckwheat flour")'
                    value={search.q}
                    onChange={(e) => setSearch({ q: e.target.value, offset: 0 })}
                />
                <select
                    className="border rounded px-2 py-1 bg-background text-sm"
                    value={search.type}
                    onChange={(e) => setSearch({ type: e.target.value as ResultKind, offset: 0 })}
                >
                    <option value="any">any</option>
                    <option value="taxon">taxon</option>
                    <option value="tp">tp</option>
                    <option value="tpt">tpt</option>
                </select>
                <Button variant="outline" onClick={() => setSearch({ q: '', offset: 0 })} disabled={!search.q}>Clear</Button>
                <div className="text-xs text-muted-foreground text-right">{queryQ?.isLoading ? 'Loading…' : `Total: ${total}`}</div>
            </div>

            {/* facets */}
            {!!search.q && (
                <div className="rounded border p-2">
                    <div className="text-xs font-medium mb-2">Facets</div>
                    <div className="flex flex-wrap gap-2">
                        {facets.family?.map((f: any) => (
                            <Button
                                key={f.id}
                                size="sm"
                                variant="outline"
                                className="text-xs"
                                onClick={() => setSearch({ family: f.id, offset: 0 })}
                            >
                                {f.id} ({f.count})
                            </Button>
                        ))}
                        {facets.rank?.map((f: any) => (
                            <Button
                                key={f.id}
                                size="sm"
                                variant="outline"
                                className="text-xs"
                                onClick={() => setSearch({ taxonId: f.id, offset: 0 })}
                            >
                                {f.id} ({f.count})
                            </Button>
                        ))}
                    </div>
                </div>
            )}

            {/* FTS Debug Info */}
            {!!search.q && queryQ?.data?.debug && (
                <div className="rounded border p-3 bg-muted/30">
                    <div className="text-xs font-medium mb-2">FTS5 Debug Info</div>
                    <div className="text-xs space-y-1">
                        <div>Query: <code className="bg-muted px-1 rounded">{queryQ.data.debug.query || search.q}</code></div>
                        <div>Total matches: {queryQ.data.debug.totalMatches || total}</div>
                        <div>Deduplication: {queryQ.data.debug.deduped ? 'Yes' : 'No'}</div>
                        {queryQ.data.debug.ftsVersion && (
                            <div>FTS Version: {queryQ.data.debug.ftsVersion}</div>
                        )}
                    </div>
                </div>
            )}

            {/* results */}
            {!!search.q && (
                <div className="rounded border">
                    <div className="bg-muted/50 border-b px-3 py-2 text-xs">
                        {queryQ?.isLoading ? 'Searching…' : `Results (${rows.length})`}
                    </div>
                    {queryQ?.isLoading ? (
                        <div className="p-3 space-y-2">
                            {Array.from({ length: 6 }).map((_, i) => (
                                <div key={i} className="flex items-center gap-2">
                                    <div className="h-4 bg-muted rounded flex-1" />
                                    <div className="h-4 w-16 bg-muted rounded" />
                                </div>
                            ))}
                        </div>
                    ) : rows.length === 0 ? (
                        <div className="p-6 text-center text-sm text-muted-foreground">No results</div>
                    ) : (
                        <div className="divide-y">
                            {rows.map((r) => (
                                <div key={r.id} className="p-3 flex items-center justify-between">
                                    <div className="min-w-0 flex-1">
                                        <div className="flex items-center gap-2">
                                            <div className="truncate font-medium">{r.name || r.display_name || r.id}</div>
                                            {kindBadge(r.ref_type || r.kind)}
                                            {r.score !== undefined && (
                                                <span className="text-xs text-muted-foreground">score: {r.score.toFixed(3)}</span>
                                            )}
                                        </div>
                                        <div className="text-xs text-muted-foreground mt-1">
                                            {r.ref_type === 'taxon' && `/${r.slug} (${r.rank})`}
                                            {r.ref_type === 'tp' && `TP: ${r.taxon_id}:${r.part_id}`}
                                            {r.ref_type === 'tpt' && `TPT: ${r.family}`}
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {r.ref_type === 'taxon' && (
                                            <Button size="sm" onClick={() => gotoTaxon(r.id)}>View</Button>
                                        )}
                                        {r.ref_type === 'tp' && r.taxon_id && r.part_id && (
                                            <Button size="sm" onClick={() => gotoTP(r.taxon_id, r.part_id)}>View</Button>
                                        )}
                                        {r.ref_type === 'tpt' && (
                                            <Button size="sm" onClick={() => gotoTPT(r.id)}>View</Button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* paging */}
            {!!search.q && rows.length > 0 && (
                <div className="flex justify-between items-center">
                    <Button size="sm" variant="outline" onClick={() => setSearch({ offset: Math.max(0, search.offset - search.limit) })} disabled={search.offset <= 0}>Prev</Button>
                    <div className="text-xs text-muted-foreground">offset {search.offset}</div>
                    <Button size="sm" variant="outline" onClick={() => setSearch({ offset: search.offset + search.limit })} disabled={rows.length < search.limit}>Next</Button>
                </div>
            )}
        </div>
    )
}
