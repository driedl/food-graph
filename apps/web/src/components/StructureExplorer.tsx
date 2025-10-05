import { useMemo } from 'react'

export default function StructureExplorer({
  node,
  childrenRows,
  siblings,
  childCount,
  rankColor,
  onPick,
  parent,
  hasMore,
  onShowMore,
}: {
  node?: { id: string; rank?: string }
  childrenRows: Array<{ id: string; name: string; slug: string; rank: string }>
  siblings: Array<{ id: string; name: string }>
  childCount: number
  rankColor: Record<string, string>
  onPick: (id: string) => void
  parent?: { id: string; name: string } | null
  hasMore?: boolean
  onShowMore?: () => void
}) {
  const ranks = useMemo(() => Array.from(new Set(childrenRows.map(c => c.rank))), [childrenRows])
  const childRank = ranks.length === 1 ? ranks[0] : null

  // Filter out current node from siblings
  const actualSiblings = useMemo(() =>
    siblings.filter(s => s.id !== node?.id),
    [siblings, node?.id]
  )

  return (
    <div className="grid grid-rows-[auto_auto_1fr] gap-3 h-full">
      {/* Peers (siblings) */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          {actualSiblings.length > 0 ? (
            <div className="text-sm font-medium">Peers</div>
          ) : (
            <div className="text-sm font-medium text-muted-foreground">No peers</div>
          )}
          {parent ? (
            <button
              className="text-xs px-2 py-0.5 rounded border bg-background hover:bg-muted/40 focus:outline-none focus:ring-2 focus:ring-blue-200"
              onClick={() => onPick(parent.id)}
              title={`Up to ${parent.name}`}
            >
              ↑ {parent.name}
            </button>
          ) : null}
        </div>
        {actualSiblings.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            {actualSiblings.map((s) => (
              <button
                key={s.id}
                title="Jump to peer"
                className="px-2.5 py-1 rounded-md border bg-background hover:bg-muted/40 hover:border-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-200 text-xs shadow-sm"
                onClick={() => onPick(s.id)}
              >
                {s.name}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Children summary */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {childrenRows.length > 0 ? (
            <>
              <div className="text-sm font-medium">Children</div>
              {childRank && (
                <span className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[childRank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>
                  {childRank}
                </span>
              )}
            </>
          ) : (
            <div className="text-sm font-medium text-muted-foreground">No children</div>
          )}
        </div>
        {childrenRows.length > 0 && (
          <div className="text-xs text-muted-foreground">
            Showing {childrenRows.length}{childCount > childrenRows.length ? ` of ${childCount}` : ''}
          </div>
        )}
      </div>

      {/* Children table */}
      <div className="min-h-0">
        {childrenRows.length > 0 ? (
          <>
            <div className="min-h-0 overflow-auto rounded border">
              <table className="w-full text-sm">
                <thead className="text-xs text-muted-foreground bg-muted/40 sticky top-0">
                  <tr>
                    <th className="text-left font-medium px-3 py-2">Name</th>
                    <th className="text-left font-medium px-3 py-2">Slug</th>
                    <th className="w-8">{/* affordance column */}</th>
                  </tr>
                </thead>
                <tbody>
                  {childrenRows.map((r) => (
                    <tr
                      key={r.id}
                      className="group border-t hover:bg-muted/30 cursor-pointer"
                      onClick={() => onPick(r.id)}
                    >
                      <td className="px-3 py-2">{r.name}</td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">/{r.slug}</td>
                      <td className="px-3 py-2 pr-3 text-right">
                        <span className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground">→</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {hasMore && (
              <div className="mt-2 flex justify-center">
                <button
                  className="text-xs px-3 py-1 rounded border bg-background hover:bg-muted/40"
                  onClick={() => onShowMore?.()}
                >
                  Show more
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="flex items-center justify-center h-24 text-sm text-muted-foreground">
            {/* Empty state - no additional content needed since label already says "No children" */}
          </div>
        )}
      </div>
    </div>
  )
}
