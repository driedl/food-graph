import { useMemo } from 'react'
import { trpc } from '@/lib/trpc'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'

function Steps({
    id,
    label,
}: {
    id?: string
    label: string
}) {
    const getQ = id ? (trpc as any).tpt?.get?.useQuery({ id }) : null
    const steps: Array<any> = getQ?.data?.identity ?? getQ?.data?.path ?? []
    const meta = getQ?.data

    return (
        <div className="space-y-2">
            <div className="text-sm font-medium">{label}</div>
            {getQ?.isLoading ? (
                <div className="text-sm text-muted-foreground">Loading...</div>
            ) : !id ? (
                <div className="text-sm text-muted-foreground">No TPT selected</div>
            ) : !getQ?.data ? (
                <div className="text-sm text-destructive">TPT not found</div>
            ) : (
                <div className="space-y-1">
                    {steps.map((step: any, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                            <Badge variant="outline" className="text-[10px]">
                                {i + 1}
                            </Badge>
                            <span className="font-mono">{step.name || step.type || 'Unknown'}</span>
                        </div>
                    ))}
                    {meta?.name && (
                        <div className="mt-2 text-xs text-muted-foreground">
                            <div className="font-medium">{meta.name}</div>
                            <div className="font-mono">{id}</div>
                        </div>
                    )}
                </div>
            )}
        </div>
    )
}

export function TPCompare({
    compare,
    onSetCompare,
}: {
    compare?: string
    onSetCompare: (ids: string[]) => void
}) {
    const [a, b] = compare ? compare.split(',') : ['', '']
    const aVal = useMemo(() => a ?? '', [a])
    const bVal = useMemo(() => b ?? '', [b])

    return (
        <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
                <div className="flex gap-2">
                    <Input
                        placeholder="Paste TPT id"
                        defaultValue={aVal}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                const newA = (e.target as HTMLInputElement).value.trim()
                                onSetCompare([newA, bVal])
                            }
                        }}
                    />
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onSetCompare(['', bVal])}
                    >
                        Clear
                    </Button>
                </div>
                <Steps id={aVal} label="TPT A" />
            </div>

            <div className="space-y-2">
                <div className="flex gap-2">
                    <Input
                        placeholder="Paste TPT id"
                        defaultValue={bVal}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                                const newB = (e.target as HTMLInputElement).value.trim()
                                onSetCompare([aVal, newB])
                            }
                        }}
                    />
                    <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onSetCompare([aVal, ''])}
                    >
                        Clear
                    </Button>
                </div>
                <Steps id={bVal} label="TPT B" />
            </div>
        </div>
    )
}
