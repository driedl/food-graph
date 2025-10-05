import { createFileRoute, useNavigate } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'

export const Route = createFileRoute('/workbench/cuisines')({
    validateSearch: (s: Record<string, unknown>) => {
        const q = typeof s.q === 'string' ? s.q : ''
        const cuisine = typeof s.cuisine === 'string' ? s.cuisine : ''
        const limit = Number.isFinite(Number(s.limit)) ? Math.max(1, Math.min(20, Number(s.limit))) : 20
        const offset = Number.isFinite(Number(s.offset)) ? Math.max(0, Number(s.offset)) : 0
        return { q, cuisine, limit, offset }
    },
    component: CuisinesPage,
})

function CuisinesPage() {
    const navigate = useNavigate()
    const search = Route.useSearch() as { q: string; cuisine: string; limit: number; offset: number }
    const setSearch = (patch: Partial<typeof search>) =>
        navigate({ to: '/workbench/cuisines', search: (s: any) => ({ ...s, ...patch }) })

    const cuisQ = trpc.browse.getCuisines.useQuery({
        q: search.q || undefined,
        limit: search.limit,
        offset: search.offset,
    })

    const rows = cuisQ?.data?.rows ?? []
    const total = cuisQ?.data?.total ?? rows.length

    const pickCuisine = (c: string) => setSearch({ cuisine: c, offset: 0 })

    const entsQ = trpc.browse.getCuisineEntities.useQuery(
        {
            cuisine: search.cuisine || '',
            limit: search.limit,
            offset: search.offset,
        },
        { enabled: !!search.cuisine }
    )
    const ents: any[] = entsQ?.data?.rows ?? []
    const entsTotal: number = entsQ?.data?.total ?? ents.length

    const gotoTPT = (id: string) =>
        navigate({ to: '/workbench/tpt/$id', params: { id }, search: { tab: 'overview' } })
    const gotoTP = (taxonId: string, partId: string) =>
        navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId }, search: { tab: 'overview', family: '', limit: 50, offset: 0, compare: '' } })

    return (
        <div className="p-4 space-y-3">
            <div className="flex items-center gap-2">
                <div className="text-lg font-semibold">Cuisines</div>
                {search.q && (
                    <Badge variant="secondary" className="text-xs">
                        Filtered by: "{search.q}"
                    </Badge>
                )}
            </div>

            <div className="flex items-center gap-2">
                <Input
                    placeholder="Filter cuisines…"
                    value={search.q}
                    onChange={(e) => setSearch({ q: e.target.value, offset: 0 })}
                />
                <Button variant="outline" onClick={() => setSearch({ q: '', offset: 0 })} disabled={!search.q}>
                    Clear
                </Button>
                <div className="ml-auto text-xs text-muted-foreground">
                    {cuisQ?.isLoading ? 'Loading…' : `Total: ${total}`}
                </div>
            </div>

            <div className="rounded border divide-y">
                {cuisQ?.isLoading ? (
                    <div className="p-4 text-center text-sm text-muted-foreground">Loading cuisines...</div>
                ) : rows.length > 0 ? (
                    rows.map((r: any) => (
                        <div
                            key={r.cuisine || r.id}
                            className="p-3 flex items-center justify-between hover:bg-muted/50 cursor-pointer transition-colors group"
                            onClick={() => pickCuisine(r.cuisine || r.id)}
                        >
                            <div className="min-w-0 flex-1">
                                <div className="text-sm font-medium truncate group-hover:text-primary transition-colors">
                                    {r.cuisine || r.id}
                                </div>
                            </div>
                            <div className="flex items-center gap-2">
                                <Badge variant="secondary" className="text-[10px] uppercase">{r.count ?? r.tptCount ?? 0}</Badge>
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="p-4 text-center text-sm text-muted-foreground">
                        {search.q ? `No cuisines found matching "${search.q}"` : 'No cuisines found.'}
                    </div>
                )}
            </div>

            {search.cuisine && (
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <div className="text-sm font-medium">
                            <span className="text-muted-foreground">Cuisine:</span> <span className="font-mono">{search.cuisine}</span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                            {entsQ?.isLoading ? 'Loading…' : `Results: ${entsTotal}`}
                        </div>
                    </div>
                    <div className="rounded border divide-y">
                        {entsQ?.isLoading ? (
                            <div className="p-4 text-center text-sm text-muted-foreground">Loading TPTs...</div>
                        ) : ents.length > 0 ? (
                            ents.map((e) => (
                                <div key={e.id} className="p-3 text-sm hover:bg-muted/30 transition-colors">
                                    <div className="flex items-center justify-between">
                                        <div className="min-w-0 flex-1">
                                            <button
                                                className="text-left hover:text-primary transition-colors group"
                                                onClick={() => gotoTPT(e.id)}
                                            >
                                                <div className="font-medium truncate group-hover:underline">{e.name || e.id}</div>
                                            </button>
                                            <div className="text-[11px] text-muted-foreground break-all mt-1">{e.id}</div>
                                            {e.taxonId && e.partId && (
                                                <button
                                                    className="text-xs text-muted-foreground hover:text-primary transition-colors mt-1 hover:underline"
                                                    onClick={() => gotoTP(e.taxonId, e.partId)}
                                                >
                                                    View as TP: {e.taxon_name} + {e.part_name}
                                                </button>
                                            )}
                                        </div>
                                        <div className="flex items-center gap-2 ml-4">
                                            <Badge variant="outline" className="text-[10px]">{e.family || 'unknown'}</Badge>
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="p-4 text-center text-sm text-muted-foreground">
                                No TPTs found for this cuisine.
                            </div>
                        )}
                    </div>

                    <div className="flex justify-between items-center">
                        <Button size="sm" variant="outline" onClick={() => setSearch({ offset: Math.max(0, search.offset - search.limit) })} disabled={search.offset <= 0}>Prev</Button>
                        <div className="text-xs text-muted-foreground">offset {search.offset}</div>
                        <Button size="sm" variant="outline" onClick={() => setSearch({ offset: search.offset + search.limit })} disabled={ents.length < search.limit}>Next</Button>
                    </div>
                </div>
            )}
        </div>
    )
}
