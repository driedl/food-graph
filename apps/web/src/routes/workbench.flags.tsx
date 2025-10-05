import { createFileRoute, useNavigate } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'
import { Input } from '@ui/input'

export const Route = createFileRoute('/workbench/flags')({
    validateSearch: (s: Record<string, unknown>) => {
        const q = typeof s.q === 'string' ? s.q : ''
        const type = typeof s.type === 'string' ? s.type : 'any' // 'safety' | 'dietary' | 'any'
        const flag = typeof s.flag === 'string' ? s.flag : ''
        const limit = Number.isFinite(Number(s.limit)) ? Math.max(1, Math.min(20, Number(s.limit))) : 20
        const offset = Number.isFinite(Number(s.offset)) ? Math.max(0, Number(s.offset)) : 0
        return { q, type, flag, limit, offset }
    },
    component: FlagsPage,
})

function FlagsPage() {
    const navigate = useNavigate()
    const search = Route.useSearch() as { q: string; type: string; flag: string; limit: number; offset: number }
    const setSearch = (patch: Partial<typeof search>) =>
        navigate({ to: '/workbench/flags', search: (s: any) => ({ ...s, ...patch }) })

    const flagsQ = trpc.browse.getFlags.useQuery({ q: search.q || undefined })
    const groups: Array<{ type: string; items: Array<{ flag: string; count: number }> }> = flagsQ?.data ?? []

    const entsQ = trpc.browse.getFlagEntities.useQuery(
        {
            flag: search.flag || '',
            type: search.type === 'any' ? undefined : search.type,
            limit: search.limit,
            offset: search.offset,
        },
        { enabled: !!search.flag }
    )
    const ents: any[] = entsQ?.data?.rows ?? []
    const entsTotal: number = entsQ?.data?.total ?? ents.length

    const gotoTPT = (id: string) => navigate({ to: '/workbench/tpt/$id', params: { id }, search: { tab: 'overview' } })

    return (
        <div className="p-4 space-y-3">
            <div className="flex items-center gap-2">
                <div className="text-lg font-semibold">Flags</div>
                {search.q && (
                    <Badge variant="secondary" className="text-xs">
                        Filtered by: "{search.q}"
                    </Badge>
                )}
            </div>

            <div className="flex items-center gap-2">
                <Input
                    placeholder="Filter flags…"
                    value={search.q}
                    onChange={(e) => setSearch({ q: e.target.value, offset: 0 })}
                />
                <Button variant="outline" onClick={() => setSearch({ q: '', offset: 0 })} disabled={!search.q}>
                    Clear
                </Button>
                <div className="ml-auto text-xs text-muted-foreground">
                    {flagsQ?.isLoading ? 'Loading…' : `Total: ${groups.reduce((sum, g) => sum + g.items.length, 0)}`}
                </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
                {flagsQ?.isLoading ? (
                    <div className="col-span-2 p-4 text-center text-sm text-muted-foreground">Loading flags...</div>
                ) : groups.length > 0 ? (
                    groups.map((g) => (
                        <div key={g.type} className="rounded border">
                            <div className="px-2 py-1 text-[11px] uppercase tracking-wide text-muted-foreground border-b">{g.type}</div>
                            <ul className="divide-y">
                                {g.items.map((it) => (
                                    <li
                                        key={it.flag}
                                        className="p-3 flex items-center justify-between hover:bg-muted/50 cursor-pointer transition-colors group"
                                        onClick={() => setSearch({ flag: it.flag, type: g.type, offset: 0 })}
                                    >
                                        <div className="min-w-0 flex-1">
                                            <div className="text-sm font-medium truncate group-hover:text-primary transition-colors">{it.flag}</div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Badge variant="secondary" className="text-[10px] uppercase">{it.count}</Badge>
                                        </div>
                                    </li>
                                ))}
                                {g.items.length === 0 && <li className="p-3 text-sm text-muted-foreground">None</li>}
                            </ul>
                        </div>
                    ))
                ) : (
                    <div className="col-span-2 p-4 text-center text-sm text-muted-foreground">
                        {search.q ? `No flags found matching "${search.q}"` : 'No flags found.'}
                    </div>
                )}
            </div>

            {search.flag && (
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <div className="text-sm font-medium">
                            <span className="text-muted-foreground">Flag:</span> <span className="font-mono">{search.flag}</span>
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
                                        </div>
                                        <div className="flex items-center gap-2 ml-4">
                                            <Badge variant="outline" className="text-[10px]">{e.family || 'unknown'}</Badge>
                                            <Badge variant="secondary" className="text-[10px]">{e.type || 'unknown'}</Badge>
                                        </div>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="p-4 text-center text-sm text-muted-foreground">
                                No TPTs found for this flag.
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
