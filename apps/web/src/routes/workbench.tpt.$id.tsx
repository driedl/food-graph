import { createFileRoute, useRouter } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'
import { TPTOverview } from '@/components/tpt/TPTOverview'
import { Badge } from '@ui/badge'

export const Route = createFileRoute('/workbench/tpt/$id')({
    component: TPTPage,
})

function TPTPage() {
    const { id } = Route.useParams()
    const router = useRouter()

    // minimal meta for header
    const metaQ = (trpc as any).tpt?.get?.useQuery({ id })
    const meta = metaQ?.data
    const metaError = metaQ?.error

    // Handle case where TPT doesn't exist
    if (metaError) {
        return (
            <div className="p-4">
                <div className="text-lg font-semibold text-red-600">TPT Not Found</div>
                <div className="text-sm text-muted-foreground mt-2">
                    The TPT <code className="bg-muted px-1 rounded">{id}</code> doesn't exist in the current graph.
                </div>
                <div className="text-sm text-muted-foreground mt-2">
                    This TPT may need to be added to the ontology and rebuilt. Check the ETL process or add the required data to make this node available.
                </div>
                <div className="mt-4">
                    <button
                        className="px-3 py-1 text-sm bg-muted hover:bg-muted/80 rounded border"
                        onClick={() => router.navigate({ to: '/workbench' })}
                    >
                        Back to Workbench
                    </button>
                </div>
            </div>
        )
    }



    const openTP = (taxonId: string, partId: string) =>
        router.navigate({
            to: '/workbench/tp/$taxonId/$partId',
            params: { taxonId, partId },
            search: { tab: 'overview', family: '', limit: 50, offset: 0, compare: '' }
        })

    const openTPT = (tid: string) =>
        router.navigate({
            to: '/workbench/tpt/$id',
            params: { id: tid }
        })

    // Suggestions
    const suggestQ = (trpc as any).tptAdvanced?.suggest?.useQuery({ seedId: id }, { enabled: !!id })

    return (
        <div className="rounded-md border p-4 space-y-4">
            {/* Main content */}
            <div className="space-y-4">
                <TPTOverview id={id} onOpenTP={openTP} onOpenTPT={openTPT} />

                {/* Suggestions section */}
                <div className="pt-4 border-t">
                    <div className="flex items-center justify-between mb-3">
                        <div className="text-sm font-medium">Suggestions</div>
                        <Badge variant="secondary" className="text-[10px] uppercase">Dev</Badge>
                    </div>

                    {suggestQ?.isLoading ? (
                        <div className="text-sm text-muted-foreground">Loading…</div>
                    ) : (suggestQ?.data?.suggestions ?? []).length === 0 ? (
                        <div className="text-sm text-muted-foreground">No suggestions.</div>
                    ) : (
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                            {(suggestQ?.data?.suggestions ?? []).map((s: any) => (
                                <button
                                    key={s.id}
                                    className="text-left px-3 py-2 rounded border hover:bg-muted/40"
                                    onClick={() => openTPT(String(s.id))}
                                >
                                    <div className="text-sm truncate">{s.name || s.id}</div>
                                    <div className="text-[11px] text-muted-foreground">{s.family}</div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

            </div>
        </div>
    )
}
