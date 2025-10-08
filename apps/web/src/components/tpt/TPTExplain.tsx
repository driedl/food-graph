import { useState } from 'react'
import { trpc } from '@/lib/trpc'
import { Button } from '@ui/button'

export function TPTExplain({ id }: { id: string }) {
    const explainQ = (trpc as any).tpt?.explain?.useQuery({ id })
    const detailQ = (trpc as any).tpt?.get?.useQuery({ id })
    const [showRaw, setShowRaw] = useState(false)

    if (explainQ?.isLoading || detailQ?.isLoading) {
        return <div className="text-sm text-muted-foreground">Loading…</div>
    }
    const text: string | undefined = explainQ?.data?.summary
    const raw = detailQ?.data

    return (
        <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
                <div className="text-xs text-muted-foreground">Human-readable explanation of identity and naming.</div>
                <Button size="sm" variant="outline" onClick={() => setShowRaw((v) => !v)}>
                    {showRaw ? 'Hide raw' : 'Show raw'}
                </Button>
            </div>
            {text ? (
                <div className="leading-relaxed whitespace-pre-wrap">{text}</div>
            ) : (
                <div className="text-muted-foreground">No explanation available.</div>
            )}
            {showRaw && (
                <pre className="text-xs border rounded p-2 bg-muted/30 overflow-auto">{JSON.stringify(raw, null, 2)}</pre>
            )}
        </div>
    )
}
