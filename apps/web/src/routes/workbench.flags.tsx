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

    const flagsQ = (trpc as any).browse?.getFlags?.useQuery({ q: search.q || undefined })
    const groups: Array<{ type: string; items: Array<{ flag: string; count: number }> }> = flagsQ?.data ?? []

    const entsQ = (trpc as any).browse?.getFlagEntities?.useQuery(
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

    const gotoTPT = (id: string) => router.navigate({ to: '/workbench/tpt/$id', params: { id } })

    return (
        <div className="p-4 space-y-3">
            <div className="text-lg font-semibold">Flags</div>

            <div className="flex items-center gap-2">
                <Input
                    placeholder="Filter flags…"
                    value={search.q}
                    onChange={(e) => setSearch({ q: e.target.value, offset: 0 })}
                />
                <Button variant="outline" onClick={() => setSearch({ q: '', offset: 0 })} disabled={!search.q}>
                    Clear
                </Button>
            </div>

            <div className="grid grid-cols-2 gap-3">
                {groups.map((g) => (
                    <div key={g.type} className="rounded border">
                        <div className="px-2 py-1 text-[11px] uppercase tracking-wide text-muted-foreground border-b">{g.type}</div>
                        <ul className="divide-y">
                            {g.items.map((it) => (
                                <li key={it.flag} className="p-2 flex items-center justify-between">
                                    <div className="min-w-0 truncate">{it.flag}</div>
                                    <div className="flex items-center gap-2">
                                        <Badge variant="secondary" className="text-[10px] uppercase">{it.count}</Badge>
                                        <Button size="sm" onClick={() => setSearch({ flag: it.flag, type: g.type, offset: 0 })}>Open</Button>
                                    </div>
                                </li>
                            ))}
                            {g.items.length === 0 && <li className="p-2 text-sm text-muted-foreground">None</li>}
                        </ul>
                    </div>
                ))}
                {groups.length === 0 && <div className="text-sm text-muted-foreground">No flags.</div>}
            </div>

            {search.flag && (
                <div className="space-y-2">
                    <div className="flex items-center justify-between">
                        <div className="text-sm font-medium">
                            Flag: <span className="font-mono">{search.flag}</span>
                        </div>
                        <div className="text-xs text-muted-foreground">
                            {entsQ?.isLoading ? 'Loading…' : `Results: ${entsTotal}`}
                        </div>
                    </div>
                    <div className="rounded border divide-y">
                        {(ents.length ? ents : []).map((e) => (
                            <div key={e.id} className="p-2 text-sm flex items-center justify-between">
                                <div className="min-w-0">
                                    <div className="truncate">{e.name || e.id}</div>
                                    <div className="text-[11px] text-muted-foreground break-all">{e.id}</div>
                                </div>
                                <Button size="sm" onClick={() => gotoTPT(e.id)}>TPT</Button>
                            </div>
                        ))}
                        {!ents.length && <div className="p-3 text-sm text-muted-foreground">No entities.</div>}
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
