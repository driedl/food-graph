import { Separator } from '@ui/separator'
import { Skeleton } from '@ui/skeleton'

export function TaxonPanel({
  node, path, children, parentId, onJump, rankColor
}: {
  node?: { id: string; name: string; slug: string; rank: string }
  path?: Array<{ id: string; name: string; rank: string }>
  children?: Array<any>
  parentId: string | null
  onJump: (id: string) => void
  rankColor: Record<string, string>
}) {
  if (!node) return <Skeleton className="h-6 w-40" />
  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center justify-between">
        <div className="text-base font-medium">{node.name}</div>
        <span className={`ml-2 inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[node.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>
          {node.rank}
        </span>
      </div>
      <div className="text-xs text-muted-foreground">/{node.slug}</div>
      <Separator />
      <div className="grid grid-cols-2 gap-2">
        <div className="text-xs text-muted-foreground">ID</div>
        <div className="text-xs break-all">{node.id}</div>
        <div className="text-xs text-muted-foreground">Children</div>
        <div className="text-xs">{children?.length ?? 0}</div>
        <div className="text-xs text-muted-foreground">Parent</div>
        <div className="text-xs">
          {parentId ? (
            <button className="underline" onClick={() => onJump(parentId!)}>
              {parentId}
            </button>
          ) : (
            '—'
          )}
        </div>
      </div>
      <Separator />
      <div className="space-y-1">
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Lineage</div>
        <ul className="space-y-1">
          {(path ?? []).map((p) => (
            <li key={p.id} className="flex items-center justify-between">
              <button className="underline text-left" onClick={() => onJump(p.id)}>
                {p.name}
              </button>
              <span className={`ml-2 inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[p.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>
                {p.rank}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
