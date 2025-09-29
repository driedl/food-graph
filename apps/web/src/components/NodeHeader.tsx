import { Skeleton } from '@ui/skeleton'
import { Separator } from '@ui/separator'
import { Badge } from '@ui/badge'

export default function NodeHeader({
  loading,
  lineage,
  node,
  siblings,
  rankColor,
  childCount,
  descendants,
  onJump,
}: {
  loading: boolean
  lineage?: Array<{ id: string; name: string; slug: string; rank: string }>
  node?: { id: string; name: string; slug: string; rank: string }
  siblings?: Array<{ id: string; name: string }>
  rankColor: Record<string, string>
  childCount: number
  descendants: number
  onJump: (id: string) => void
}) {
  if (loading) {
    return (
      <div className="flex items-center gap-2">
        <Skeleton className="h-5 w-40" />
        <Separator className="h-5" />
        <Skeleton className="h-4 w-24" />
      </div>
    )
  }
  if (!node) return <div className="text-sm text-muted-foreground">Select a node…</div>

  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <div className="text-base font-semibold truncate">{node.name}</div>
          <span className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[node.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>{node.rank}</span>
        </div>
        {/* Crumbs */}
        <div className="text-xs text-muted-foreground flex items-center gap-1">
          {(lineage ?? []).map((p, i) => (
            <span key={p.id} className="flex items-center gap-1">
              <button className="underline" onClick={() => onJump(p.id)}>{p.name}</button>
              {i < (lineage!.length - 1) && <span>›</span>}
            </span>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="text-[10px]">children {childCount}</Badge>
        <Badge variant="secondary" className="text-[10px]">desc {descendants}</Badge>
        {siblings && siblings.length > 0 && (
          <select
            className="text-xs border rounded px-1.5 py-0.5 bg-background"
            value={node.id}
            onChange={(e) => onJump(e.target.value)}
          >
            {siblings.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
        )}
      </div>
    </div>
  )
}
