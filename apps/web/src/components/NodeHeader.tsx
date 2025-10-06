import { Skeleton } from '@ui/skeleton'
import { Separator } from '@ui/separator'
import { useNavigate } from '@tanstack/react-router'

export default function NodeHeader({
  loading,
  lineage,
  node,
  rankColor,
}: {
  loading: boolean
  lineage?: Array<{ id: string; name: string; slug: string; rank: string }>
  node?: { id: string; name: string; slug: string; rank: string }
  rankColor: Record<string, string>
}) {
  const navigate = useNavigate()
  
  const handleJump = (id: string) => {
    navigate({ to: '/workbench/taxon/$id', params: { id } })
  }
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
              <button className="underline" onClick={() => handleJump(p.id)}>{p.name}</button>
              {i < (lineage!.length - 1) && <span>›</span>}
            </span>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-2" />
    </div>
  )
}
