import { useMemo } from 'react'

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
  const mixedRanks = useMemo(() => {
    const set = new Set(childrenRows.map((c) => c.rank))
    return set.size > 1
  }, [childrenRows])

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
        {!mixedRanks && childrenRows.length > 0 && (
          <div className="text-xs text-muted-foreground mb-2">
            Children · {childrenRows[0]?.rank} · {childrenRows.length}
          </div>
        )}
        <div className="min-h-0 overflow-auto rounded border">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted-foreground bg-muted/40 sticky top-0">
              <tr>
                <th className="text-left font-medium px-3 py-2">Name</th>
                <th className="text-left font-medium px-3 py-2">Slug</th>
                {mixedRanks && <th className="text-left font-medium px-3 py-2">Rank</th>}
              </tr>
            </thead>
            <tbody>
              {childrenRows.map((r) => (
                <tr key={r.id} className="border-t hover:bg-muted/30 cursor-pointer" onClick={() => onPick(r.id)}>
                  <td className="px-3 py-2">{r.name}</td>
                  <td className="px-3 py-2 text-xs text-muted-foreground">/{r.slug}</td>
                  {mixedRanks && (
                    <td className="px-3 py-2">
                      <span className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[r.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>{r.rank}</span>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
