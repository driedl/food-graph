import React, { useMemo } from 'react'
import { trpc } from '@/lib/trpc'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'
import { Badge } from '@ui/badge'
import { Button } from '@ui/button'
import { Input } from '@ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@ui/table'

interface TPTComparePanelProps {
    compare: string
    onSetCompare: (ids: string[]) => void
}

interface TPTData {
    id: string
    name: string
    family: string
    taxonId: string
    partId: string
    identity: Array<{
        id: string
        name: string
        params?: Record<string, any>
    }>
    flags: string[]
    cuisines: string[]
    synonyms: string[]
}

function TPTCard({
    tpt,
    label,
    onClear
}: {
    tpt: TPTData | null
    label: string
    onClear: () => void
}) {
    if (!tpt) {
        return (
            <Card>
                <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-sm">{label}</CardTitle>
                        <div className="text-xs text-muted-foreground">No TPT selected</div>
                    </div>
                </CardHeader>
                <CardContent>
                    <div className="text-sm text-muted-foreground">Select a TPT to compare</div>
                </CardContent>
            </Card>
        )
    }

    return (
        <Card>
            <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                    <CardTitle className="text-sm">{label}</CardTitle>
                    <Button size="sm" variant="outline" onClick={onClear}>
                        Clear
                    </Button>
                </div>
            </CardHeader>
            <CardContent className="space-y-3">
                <div>
                    <div className="font-medium">{tpt.name}</div>
                    <div className="text-xs text-muted-foreground font-mono">{tpt.id}</div>
                    <Badge variant="secondary" className="text-xs mt-1">{tpt.family}</Badge>
                </div>

                <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1">Identity Steps</div>
                    <div className="space-y-1">
                        {tpt.identity.map((step, i) => (
                            <div key={i} className="flex items-center gap-2 text-xs">
                                <Badge variant="outline" className="text-[10px]">{i + 1}</Badge>
                                <span className="font-mono">{step.name || step.id}</span>
                                {step.params && Object.keys(step.params).length > 0 && (
                                    <span className="text-muted-foreground">
                                        {JSON.stringify(step.params)}
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {tpt.flags.length > 0 && (
                    <div>
                        <div className="text-xs font-medium text-muted-foreground mb-1">Flags</div>
                        <div className="flex flex-wrap gap-1">
                            {tpt.flags.map(flag => (
                                <Badge key={flag} variant="secondary" className="text-[10px]">
                                    {flag}
                                </Badge>
                            ))}
                        </div>
                    </div>
                )}

                {tpt.cuisines.length > 0 && (
                    <div>
                        <div className="text-xs font-medium text-muted-foreground mb-1">Cuisines</div>
                        <div className="flex flex-wrap gap-1">
                            {tpt.cuisines.map(cuisine => (
                                <Badge key={cuisine} variant="secondary" className="text-[10px]">
                                    {cuisine}
                                </Badge>
                            ))}
                        </div>
                    </div>
                )}
            </CardContent>
        </Card>
    )
}

function DiffTable({ tptA, tptB }: { tptA: TPTData | null; tptB: TPTData | null }) {
    const diffData = useMemo(() => {
        if (!tptA || !tptB) return []

        const fields = [
            { key: 'name', label: 'Name' },
            { key: 'family', label: 'Family' },
            { key: 'taxonId', label: 'Taxon ID' },
            { key: 'partId', label: 'Part ID' },
        ]

        return fields.map(field => {
            const valueA = tptA[field.key as keyof TPTData]
            const valueB = tptB[field.key as keyof TPTData]
            const isDifferent = valueA !== valueB

            return {
                field: field.label,
                valueA: String(valueA || ''),
                valueB: String(valueB || ''),
                isDifferent
            }
        })
    }, [tptA, tptB])

    if (!tptA || !tptB) return null

    return (
        <Card>
            <CardHeader className="pb-2">
                <CardTitle className="text-sm">Differences</CardTitle>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Field</TableHead>
                            <TableHead>TPT A</TableHead>
                            <TableHead>TPT B</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {diffData.map((row, i) => (
                            <TableRow key={i} className={row.isDifferent ? 'bg-muted/30' : ''}>
                                <TableCell className="font-medium">{row.field}</TableCell>
                                <TableCell className={row.isDifferent ? 'text-destructive' : ''}>
                                    {row.valueA}
                                </TableCell>
                                <TableCell className={row.isDifferent ? 'text-destructive' : ''}>
                                    {row.valueB}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
    )
}

export function TPTComparePanel({ compare, onSetCompare }: TPTComparePanelProps) {
    const [a, b] = compare ? compare.split(',') : ['', '']
    const [inputA, setInputA] = React.useState(a)
    const [inputB, setInputB] = React.useState(b)

    // Fetch TPT data
    const tptAQ = (trpc as any).tpt?.get?.useQuery({ id: a }, { enabled: !!a })
    const tptBQ = (trpc as any).tpt?.get?.useQuery({ id: b }, { enabled: !!b })

    const tptA = tptAQ?.data as TPTData | null
    const tptB = tptBQ?.data as TPTData | null

    const handleSetA = (id: string) => {
        setInputA(id)
        onSetCompare([id, b])
    }

    const handleSetB = (id: string) => {
        setInputB(id)
        onSetCompare([a, id])
    }

    const handleClearA = () => {
        setInputA('')
        onSetCompare(['', b])
    }

    const handleClearB = () => {
        setInputB('')
        onSetCompare([a, ''])
    }

    return (
        <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                    <div className="flex gap-2">
                        <Input
                            placeholder="Paste TPT ID"
                            value={inputA}
                            onChange={(e) => setInputA(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    handleSetA(inputA.trim())
                                }
                            }}
                        />
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleSetA(inputA.trim())}
                        >
                            Load
                        </Button>
                    </div>
                    <TPTCard tpt={tptA} label="TPT A" onClear={handleClearA} />
                </div>

                <div className="space-y-2">
                    <div className="flex gap-2">
                        <Input
                            placeholder="Paste TPT ID"
                            value={inputB}
                            onChange={(e) => setInputB(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    handleSetB(inputB.trim())
                                }
                            }}
                        />
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleSetB(inputB.trim())}
                        >
                            Load
                        </Button>
                    </div>
                    <TPTCard tpt={tptB} label="TPT B" onClear={handleClearB} />
                </div>
            </div>

            <DiffTable tptA={tptA} tptB={tptB} />
        </div>
    )
}
