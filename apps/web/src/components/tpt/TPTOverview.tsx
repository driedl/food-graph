import { trpc } from '@/lib/trpc'
import type { TPTDetail } from '@/lib/types'
import { Badge } from '@ui/badge'

export function TPTOverview({
    id,
    onOpenTP,
    onOpenTPT,
}: {
    id: string
    onOpenTP: (taxonId: string, partId: string) => void
    onOpenTPT: (id: string) => void
}) {
    const getQ = (trpc as any).tpt?.get?.useQuery({
        id,
        includeFlags: true,
        includeCuisines: true,
        includeRelated: true
    })
    const meta = getQ?.data

    const steps = meta?.identity ?? []
    const flags: string[] = meta?.flags ?? []
    const cuisines: string[] = meta?.cuisines ?? []
    const related = meta?.related ?? { siblings: [], variants: [] }

    if (getQ?.isLoading) return <div className="text-sm text-muted-foreground">Loading TPT…</div>
    if (!meta) return <div className="text-sm text-muted-foreground">TPT not found.</div>

    return (
        <div className="space-y-4">
            {/* Top meta */}
            <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                    <div className="text-base font-semibold truncate">{meta.name || meta.id}</div>
                    <div className="text-xs text-muted-foreground break-all">{meta.id}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-1">
                        <Badge variant="secondary" className="text-[10px] uppercase">{meta.family}</Badge>
                        <button
                            className="text-[11px] underline decoration-dotted"
                            onClick={() => onOpenTP(meta.taxonId, meta.partId)}
                            title="Open TP (Taxon+Part)"
                        >
                            {meta.taxonId} · {meta.partId}
                        </button>
                    </div>
                </div>
            </div>

            {/* Flags & cuisines */}
            <div className="grid grid-cols-2 gap-3">
                <div>
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Flags</div>
                    <div className="flex flex-wrap gap-1">
                        {flags.length ? flags.map((f) => (
                            <Badge key={f} variant="secondary" className="text-[10px]">{f}</Badge>
                        )) : <div className="text-sm text-muted-foreground">—</div>}
                    </div>
                </div>
                <div>
                    <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Cuisines</div>
                    <div className="flex flex-wrap gap-1">
                        {cuisines.length ? cuisines.map((c) => (
                            <Badge key={c} variant="secondary" className="text-[10px]">{c}</Badge>
                        )) : <div className="text-sm text-muted-foreground">—</div>}
                    </div>
                </div>
            </div>

            {/* Identity steps */}
            <div>
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Identity steps</div>
                {steps.length === 0 ? (
                    <div className="text-sm text-muted-foreground">None</div>
                ) : (
                    <ol className="text-sm list-decimal ml-4 space-y-1">
                        {steps.map((s, i) => (
                            <li key={i}>
                                <span className="font-mono text-[11px]">{s.id}</span>
                                {s.params && Object.keys(s.params || {}).length > 0 && (
                                    <span className="text-[11px] text-muted-foreground"> — {JSON.stringify(s.params)}</span>
                                )}
                            </li>
                        ))}
                    </ol>
                )}
            </div>

            {/* Related */}
            <div>
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Related</div>
                <div className="grid grid-cols-2 gap-3">
                    <div>
                        <div className="text-[11px] text-muted-foreground mb-1">Siblings</div>
                        <div className="flex flex-wrap gap-1">
                            {(related.siblings ?? []).slice(0, 20).map((r: any) => (
                                <button
                                    key={r.id}
                                    className="text-xs px-2 py-1 rounded border bg-background hover:bg-muted/40"
                                    onClick={() => onOpenTPT(r.id)}
                                >
                                    {r.name || r.id}
                                </button>
                            ))}
                            {(related.siblings ?? []).length === 0 && <div className="text-sm text-muted-foreground">—</div>}
                        </div>
                    </div>
                    <div>
                        <div className="text-[11px] text-muted-foreground mb-1">Variants</div>
                        <div className="flex flex-wrap gap-1">
                            {(related.variants ?? []).slice(0, 20).map((r: any) => (
                                <button
                                    key={r.id}
                                    className="text-xs px-2 py-1 rounded border bg-background hover:bg-muted/40"
                                    onClick={() => onOpenTPT(r.id)}
                                >
                                    {r.name || r.id}
                                </button>
                            ))}
                            {(related.variants ?? []).length === 0 && <div className="text-sm text-muted-foreground">—</div>}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
