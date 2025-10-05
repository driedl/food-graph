import { createFileRoute, useNavigate } from '@tanstack/react-router'
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
    const navigate = useNavigate()
    const search = Route.useSearch() as { q: string; family: string; limit: number; offset: number }
    const setSearch = (patch: Partial<typeof search>) =>
        navigate({ to: '/workbench/families', search: (s: any) => ({ ...s, ...patch }) })

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
        { enabled: true }
    )
    const ents: any[] = entitiesQ?.data?.rows ?? []
    const entsTotal: number = entitiesQ?.data?.total ?? ents.length

    const gotoTPT = (id: string) =>
        navigate({ to: '/workbench/tpt/$id', params: { id } })
    const gotoTP = (taxonId: string, partId: string) =>
        navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId }, search: { tab: 'overview', family: '', limit: 50, offset: 0, compare: '' } })

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

            {/* Family Filter Bar */}
            <div className="flex flex-wrap gap-2 mb-4">
                <Button
                    variant={!search.family ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSearch({ family: '', offset: 0 })}
                >
                    All Families ({total})
                </Button>
                {rows.map((r) => (
                    <Button
                        key={r.id}
                        variant={search.family === r.id ? "default" : "outline"}
                        size="sm"
                        onClick={() => pickFamily(r.id)}
                    >
                        {r.label} ({r.count})
                    </Button>
                ))}
            </div>

            {/* TPT Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {(ents.length ? ents : []).map((tpt) => (
                    <div key={tpt.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex items-start justify-between mb-2">
                            <h3 className="font-medium text-sm">{tpt.name}</h3>
                            <Badge variant="secondary" className="text-xs">{tpt.family}</Badge>
                        </div>
                        <div className="text-xs text-muted-foreground mb-3">
                            <div>{tpt.taxon_name}</div>
                            <div>{tpt.part_name}</div>
                        </div>
                        <div className="flex gap-2">
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => gotoTPT(tpt.id)}
                            >
                                View TPT
                            </Button>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={() => gotoTP(tpt.taxon_id, tpt.part_id)}
                            >
                                View TP
                            </Button>
                        </div>
                    </div>
                ))}
                {!ents.length && search.family && (
                    <div className="col-span-full p-8 text-center text-muted-foreground">
                        No TPTs found for family "{search.family}"
                    </div>
                )}
                {!ents.length && !search.family && (
                    <div className="col-span-full p-8 text-center text-muted-foreground">
                        No TPTs found. Try selecting a family above.
                    </div>
                )}
            </div>

        </div>
    )
}
