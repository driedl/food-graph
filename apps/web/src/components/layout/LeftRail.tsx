import { useEffect, useMemo, useRef, useState } from 'react'
import { trpc } from '../../lib/trpc'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'
import { Separator } from '@ui/separator'
import { Skeleton } from '@ui/skeleton'

const RANKS = ['domain','kingdom','phylum','class','order','family','genus','species','product','form','cultivar','variety','breed'] as const

export default function LeftRail({
  rankColor,
  rootId,
  currentId,
  onPick
}: {
  rankColor: Record<string, string>
  rootId?: string
  currentId: string
  onPick: (id: string) => void
}) {
  // Search + filters
  const [qInput, setQInput] = useState('')
  const [q, setQ] = useState('')
  const [rankFilter, setRankFilter] = useState<string[]>([])
  const search = trpc.search.unified.useQuery({ q, limit: 25, rankFilter: rankFilter.length ? rankFilter : undefined }, { enabled: q.length > 0 })
  useEffect(() => {
    const t = setTimeout(() => setQ(qInput.trim()), 220)
    return () => clearTimeout(t)
  }, [qInput])

  const toggleRank = (r: string) => {
    setRankFilter((prev) => (prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]))
  }

  // Quick outline: root → kingdoms (lazy)
  const childrenQ = trpc.taxonomy.getChildren.useQuery(
    { id: rootId || '', orderBy: 'name', offset: 0, limit: 100 },
    { enabled: !!rootId }
  )

  const results = (search.data as any[] | undefined) ?? []

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Find</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col gap-3">
        <div className="flex gap-2">
          <Input
            placeholder="Search taxa (⌘K)…"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
          />
          {q && (
            <Button size="sm" variant="outline" onClick={() => { setQInput(''); setQ('') }}>
              Clear
            </Button>
          )}
        </div>

        <div className="flex flex-wrap gap-1">
          {RANKS.map((r) => (
            <button
              key={r}
              className={`text-[11px] rounded border px-1.5 py-0.5 ${rankFilter.includes(r) ? 'bg-muted/70' : 'bg-background'}`}
              onClick={() => toggleRank(r)}
            >
              {r}
            </button>
          ))}
        </div>

        {/* Results */}
        {q ? (
          <div className="flex-1 min-h-0 overflow-auto rounded-md border">
            <div className="bg-muted/50 border-b px-3 py-2 text-xs">
              {search.isLoading ? 'Searching…' : `Results (${results.length})`}
            </div>
            {search.isLoading ? (
              <div className="p-3 space-y-2">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Skeleton className="h-4 flex-1" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                ))}
              </div>
            ) : results.length === 0 ? (
              <div className="p-6 text-center text-sm text-muted-foreground">No results</div>
            ) : (
              <ul className="divide-y">
                {results.map((n: any) => (
                  <li
                    key={n.id}
                    className="flex items-center justify-between px-3 py-2 text-sm cursor-pointer hover:bg-muted/40"
                    onClick={() => onPick(n.id)}
                  >
                    <div className="min-w-0">
                      <div className="truncate">{n.name}</div>
                      <div className="text-xs text-muted-foreground truncate">/{n.slug}</div>
                    </div>
                    <span
                      className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[n.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}
                    >
                      {n.rank}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <>
            <Separator />
            <div className="text-xs font-medium">Outline</div>
            <div className="text-[11px] text-muted-foreground -mt-1">Root → Kingdoms</div>
            <div className="min-h-0 overflow-auto">
              {childrenQ.isLoading ? (
                <div className="space-y-1 mt-2">
                  {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-4" />)}
                </div>
              ) : (
                <ul className="space-y-1 mt-2">
                  {(childrenQ.data as any[] | undefined)?.map((k) => (
                    <li key={k.id}>
                      <button
                        className={`w-full text-left px-2 py-1 rounded hover:bg-muted/40 ${currentId === k.id ? 'bg-muted/60' : ''}`}
                        onClick={() => onPick(k.id)}
                      >
                        <div className="flex items-center justify-between">
                          <span className="truncate">{k.name}</span>
                          <Badge variant="secondary" className="text-[10px] uppercase">{k.rank}</Badge>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
