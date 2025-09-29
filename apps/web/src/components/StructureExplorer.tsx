import { useMemo } from 'react'
import { trpc } from '../lib/trpc'
import { Separator } from '@ui/separator'
import { Badge } from '@ui/badge'
import { Skeleton } from '@ui/skeleton'

export default function StructureExplorer({
  node,
  childrenRows,
  siblings,
  rankCounts,
  rankColor,
  onPick,
}: {
  node?: { id: string }
  childrenRows: Array<{ id: string; name: string; slug: string; rank: string }>
  siblings: Array<{ id: string; name: string }>
  rankCounts?: Array<{ rank: string; count: number }>
  rankColor: Record<string, string>
  onPick: (id: string) => void
}) {
  const ids = useMemo(() => childrenRows.map((c) => c.id), [childrenRows])
  const hasDocsQ = trpc.docs.hasDocs.useQuery({ taxonIds: ids, lang: 'en' }, { enabled: ids.length > 0 })
  const hasDocMap = useMemo(() => {
    const m = new Map<string, boolean>()
    for (const r of (hasDocsQ.data || [])) m.set(r.id, r.hasDoc)
    return m
  }, [hasDocsQ.data])

  return (
    <div className="grid grid-rows-[auto_auto_1fr] gap-3 h-full">
      {/* Siblings strip */}
      <div className="flex items-center gap-2 overflow-x-auto">
        <div className="text-xs text-muted-foreground">Siblings:</div>
        <div className="flex items-center gap-1">
          {siblings.map((s) => (
            <button
              key={s.id}
              className="text-xs px-2 py-0.5 rounded border hover:bg-muted/40"
              onClick={() => onPick(s.id)}
            >
              {s.name}
            </button>
          ))}
        </div>
      </div>

      {/* Rank distribution */}
      <div>
        <div className="text-xs text-muted-foreground mb-1">Child rank distribution</div>
        <div className="flex items-end gap-1 h-16">
          {(rankCounts ?? []).map((r) => (
            <div key={r.rank} className="flex flex-col items-center">
              <div className="w-6 bg-muted rounded" style={{ height: Math.max(4, Math.min(56, r.count * 4)) }} />
              <div className="text-[10px] mt-1">{r.rank}</div>
            </div>
          ))}
          {(!rankCounts || rankCounts.length === 0) && (
            <div className="text-xs text-muted-foreground">No children</div>
          )}
        </div>
      </div>

      {/* Children table */}
      <div className="min-h-0">
        <div className="min-h-0 overflow-auto rounded border">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted-foreground bg-muted/40 sticky top-0">
              <tr>
                <th className="text-left font-medium px-3 py-2">Name</th>
                <th className="text-left font-medium px-3 py-2">Slug</th>
                <th className="text-left font-medium px-3 py-2">Rank</th>
                <th className="text-left font-medium px-3 py-2">Doc</th>
              </tr>
            </thead>
            <tbody>
              {childrenRows.map((r) => (
                <tr key={r.id} className="border-t hover:bg-muted/30 cursor-pointer" onClick={() => onPick(r.id)}>
                  <td className="px-3 py-2">{r.name}</td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">/{r.slug}</td>
                  <td className="px-3 py-2">
                    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[r.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>{r.rank}</span>
                  </td>
                  <td className="px-3 py-2">
                    {hasDocsQ.isLoading ? (
                      <Skeleton className="h-4 w-8" />
                    ) : hasDocMap.get(r.id) ? (
                      <Badge variant="secondary" className="text-[10px]">yes</Badge>
                    ) : (
                      <span className="text-[10px] text-muted-foreground">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
