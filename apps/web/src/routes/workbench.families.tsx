import { createFileRoute } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'

export const Route = createFileRoute('/workbench/families')({
    validateSearch: (s: Record<string, unknown>) => {
        const q = typeof s.q === 'string' ? s.q : ''
        const family = typeof s.family === 'string' ? s.family : ''
        const limit = Number.isFinite(Number(s.limit)) ? Math.max(1, Math.min(20, Number(s.limit))) : 20
        const offset = Number.isFinite(Number(s.offset)) ? Math.max(0, Number(s.offset)) : 0
        return { q, family, limit, offset }
    },
    component: FamiliesPage,
})

function FamiliesPage() {
    const router = Route.useRouter()
    const search = Route.useSearch() as { q: string; family: string; limit: number; offset: number }
    const setSearch = (patch: Partial<typeof search>) =>
        router.navigate({ to: '/workbench/families', search: (s: any) => ({ ...s, ...patch }) })

    const familiesQ = (trpc as any).browse?.getFamilies?.useQuery({
        q: search.q || undefined,
        limit: search.limit,
        offset: search.offset,
    })

    const rows: Array<any> = familiesQ?.data?.rows ?? []
    const total: number = familiesQ?.data?.total ?? rows.length

    const pickFamily = (fam: string) => setSearch({ family: fam, offset: 0 })

    const entitiesQ = (trpc as any).browse?.getFamilyEntities?.useQuery(
        {
            family: search.family || '',
            limit: search.limit,
            offset: search.offset,
        },
        { enabled: !!search.family }
    )
    const ents: any[] = entitiesQ?.data?.rows ?? []
    const entsTotal: number = entitiesQ?.data?.total ?? ents.length

    const gotoTPT = (id: string) =>
        router.navigate({ to: '/workbench/tpt/$id', params: { id } })
    const gotoTP = (taxonId: string, partId: string) =>
        router.navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId } })

    return (
        <div className="p-4 space-y-3">
            <div className="text-lg font-semibold">Families</div>

            {/* Search + selected family */}
            <div className="flex items-center gap-2">
                <Input
                    placeholder="Filter families…"
                    value={search.q}
                    onChange={(e) => setSearch({ q: e.target.value, offset: 0 })}
                />
                <Button variant="outline" onClick={() => setSearch({ q: '', offset: 0 })} disabled={!search.q}>
                    Clear
                </Button>
                <div className="ml-auto text-xs text-muted-foreground">
                    {familiesQ?.isLoading ? 'Loading…' : `Total: ${total}`}
                </div>
            </div>

            {/* Families list */}
            <div className="rounded border divide-y">
                {(rows.length ? rows : []).map((r) => (
                    <div key={r.id || r.family} className="p-2 flex items-center justify-between">
                        <div className="min-w-0">
                            <div className="text-sm font-medium truncate">{r.label || r.family || r.id}</div>
                            <div className="text-[11px] text-muted-foreground">{r.id || r.family}</div>
                        </div>
                        <div className="flex items-center gap-2">
                            <Badge variant="secondary" className="text-[10px] uppercase">{r.count ?? r.tptCount ?? 0}</Badge>
                            <Button size="sm" onClick={() => pickFamily(r.id || r.family)}>Open</Button>
                        </div>
                    </div>
                ))}
                {!rows.length && (
                    <div className="p-3 text-sm text-muted-foreground">No families.</div>
                )}
            </div>

            {/* Selected family → entities */}
            {search.family && (
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <div className="text-sm font-medium">
                            Family: <span className="font-mono">{search.family}</span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                            {entitiesQ?.isLoading ? 'Loading…' : `Results: ${entsTotal}`}
                        </div>
                    </div>
                    <div className="rounded border divide-y">
                        {(ents.length ? ents : []).map((e) => (
                            <div key={e.id} className="p-2 text-sm flex items-center justify-between">
                                <div className="min-w-0">
                                    <div className="truncate">{e.name || e.id}</div>
                                    <div className="text-[11px] text-muted-foreground break-all">{e.id}</div>
                                </div>
                                <div className="flex items-center gap-2">
                                    {e.taxonId && e.partId && (
                                        <Button size="sm" variant="secondary" onClick={() => gotoTP(e.taxonId, e.partId)}>TP</Button>
                                    )}
                                    <Button size="sm" onClick={() => gotoTPT(e.id)}>TPT</Button>
                                </div>
                            </div>
                        ))}
                        {!ents.length && (
                            <div className="p-3 text-sm text-muted-foreground">No entities.</div>
                        )}
                    </div>

                    {/* simple pager */}
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
