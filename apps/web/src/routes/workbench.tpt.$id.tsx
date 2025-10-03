import { createFileRoute } from '@tanstack/react-router'
import React, { useMemo } from 'react'
import { trpc } from '@/lib/trpc'
import { TPTOverview } from '@/components/tpt/TPTOverview'
import { TPTExplain } from '@/components/tpt/TPTExplain'
import { Badge } from '@ui/badge'
import { Button } from '@ui/button'
import { FoodStatePanel } from '@/components/inspector/FoodStatePanel'

export const Route = createFileRoute('/workbench/tpt/$id')({
    validateSearch: (s: Record<string, unknown>) => {
        const tab = (['overview', 'explain'] as const).includes(s.tab as any) ? (s.tab as any) : 'overview'
        return { tab }
    },
    component: TPTPage,
})

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
    return (
        <button
            className={`text-xs px-2 py-1 rounded border ${active ? 'bg-muted/60' : 'bg-background hover:bg-muted/40'}`}
            onClick={onClick}
        >
            {children}
        </button>
    )
}

function TPTPage() {
    const { id } = Route.useParams()
    const router = Route.useRouter()
    const search = Route.useSearch() as { tab: 'overview' | 'explain' }

    // minimal meta for header + FS
    const metaQ = (trpc as any).tpt?.get?.useQuery({ id })
    const meta = metaQ?.data

    const lineageQ = trpc.taxonomy.pathToRoot.useQuery({ id: meta?.taxonId ?? '' }, { enabled: !!meta?.taxonId })

    // Basic FS preview (taxon path + part only; identity omitted for readability)
    const fsPreview = useMemo(() => {
        const slugs = (lineageQ.data ?? []).map((n: any) => n.slug)
        if (!slugs.length || !meta?.partId) return ''
        const pid = meta.partId.startsWith('part:') ? meta.partId : `part:${meta.partId}`
        return `fs:/${slugs.join('/')}/${pid}`
    }, [lineageQ.data, meta?.partId])

    const setTab = (t: typeof search.tab) => {
        router.navigate({ to: '/workbench/tpt/$id', params: { id }, search: (s: any) => ({ ...s, tab: t }) })
    }

    const openTP = (taxonId: string, partId: string) =>
        router.navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId } })

    const openTPT = (tid: string) =>
        router.navigate({ to: '/workbench/tpt/$id', params: { id: tid } })

    // Suggestions (right inspector)
    const suggestQ = (trpc as any).tptAdvanced?.suggest?.useQuery({ id }, { enabled: !!id })

    return (
        <div className="grid grid-cols-[1fr,360px] gap-3 min-h-0">
            {/* Center */}
            <div className="min-h-0 flex flex-col">
                <div className="rounded-md border p-3">
                    <div className="flex items-center justify-between gap-2">
                        <div className="min-w-0">
                            <div className="text-base font-semibold truncate">{meta?.name || id}</div>
                            <div className="text-xs text-muted-foreground break-all">{id}</div>
                            {meta?.family && (
                                <div className="mt-1 flex items-center gap-2">
                                    <Badge variant="secondary" className="text-[10px] uppercase">{meta.family}</Badge>
                                    <button
                                        className="text-[11px] underline decoration-dotted"
                                        onClick={() => meta && openTP(meta.taxonId, meta.partId)}
                                        title="Open TP (Taxon+Part)"
                                    >
                                        {meta?.taxonId} · {meta?.partId}
                                    </button>
                                </div>
                            )}
                        </div>
                        <div className="flex gap-1">
                            <TabButton active={search.tab === 'overview'} onClick={() => setTab('overview')}>Overview</TabButton>
                            <TabButton active={search.tab === 'explain'} onClick={() => setTab('explain')}>Explain</TabButton>
                        </div>
                    </div>
                </div>

                <div className="mt-3 flex-1 min-h-0 rounded-md border p-3 overflow-auto">
                    {search.tab === 'overview' && (
                        <TPTOverview id={id} onOpenTP={openTP} onOpenTPT={openTPT} />
                    )}
                    {search.tab === 'explain' && (
                        <TPTExplain id={id} />
                    )}
                </div>
            </div>

            {/* Inspector */}
            <div className="min-h-0 rounded-md border p-3 space-y-3">
                <div className="flex items-center justify-between">
                    <div className="text-sm font-medium">Suggestions</div>
                    <Badge variant="secondary" className="text-[10px] uppercase">Dev</Badge>
                </div>

                {suggestQ?.isLoading ? (
                    <div className="text-sm text-muted-foreground">Loading…</div>
                ) : (suggestQ?.data ?? []).length === 0 ? (
                    <div className="text-sm text-muted-foreground">No suggestions.</div>
                ) : (
                    <ul className="space-y-1">
                        {(suggestQ?.data ?? []).map((s: any) => (
                            <li key={s.id}>
                                <button
                                    className="w-full text-left px-2 py-1 rounded border hover:bg-muted/40"
                                    onClick={() => openTPT(String(s.id))}
                                >
                                    <div className="text-sm truncate">{s.name || s.id}</div>
                                    <div className="text-[11px] text-muted-foreground">{s.family}</div>
                                </button>
                            </li>
                        ))}
                    </ul>
                )}

                <div className="pt-2 border-t">
                    <div className="text-xs font-medium mb-1">FoodState</div>
                    <FoodStatePanel
                        fsPreview={fsPreview}
                        loadingValidate={false}
                        result={undefined}
                        onCopy={(s) => navigator.clipboard.writeText(s)}
                        onValidate={() => { }}
                        onParse={(fs) => {
                            const parseQ = (trpc as any).foodstate?.parse?.useQuery({ fs }, { enabled: false })
                                ; (async () => {
                                    const r = await parseQ.refetch()
                                    const taxonPath: string[] = r.data?.taxonPath ?? []
                                    const part = r.data?.partId
                                    if (taxonPath.length >= 1) {
                                        const txid = 'tx:' + taxonPath.join(':')
                                        const pid = (part ?? '').replace(/^part:/, '')
                                        if (pid) router.navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId: txid, partId: pid } })
                                        else router.navigate({ to: '/workbench/taxon/$id', params: { id: txid } })
                                    }
                                })()
                        }}
                    />
                </div>
            </div>
        </div>
    )
}
