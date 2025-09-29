export interface TaxonRow {
  id: string
  name: string
  slug: string
  rank: string
}

export function ChildrenTable({
  rows,
  onPick,
  rankColor,
}: {
  rows: TaxonRow[]
  onPick: (id: string) => void
  rankColor: Record<string, string>
}) {
  return (
    <div className="min-h-[420px] h-[60vh] rounded-lg border overflow-auto">
      <table className="w-full text-sm">
        <thead className="text-xs text-muted-foreground bg-muted/40 sticky top-0">
          <tr>
            <th className="text-left font-medium px-3 py-2">Name</th>
            <th className="text-left font-medium px-3 py-2">Slug</th>
            <th className="text-left font-medium px-3 py-2">Rank</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t hover:bg-muted/30 cursor-pointer" onClick={() => onPick(r.id)}>
              <td className="px-3 py-2">{r.name}</td>
              <td className="px-3 py-2 text-xs text-muted-foreground">/{r.slug}</td>
              <td className="px-3 py-2">
                <span className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[r.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>{r.rank}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
