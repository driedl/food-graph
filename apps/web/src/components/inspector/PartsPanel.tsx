export function PartsPanel({
  parts,
  selectedPartId,
  onSelect,
}: {
  parts?: Array<{ id: string; name: string; kind?: string; parentId?: string | null }>
  selectedPartId: string
  onSelect: (id: string) => void
}) {
  if (!parts) return <div className="text-sm text-muted-foreground">No parts available</div>

  const groups = (parts || []).reduce((acc: Record<string, Array<any>>, p) => {
    const k = p.kind || 'other'
    acc[k] ||= []
    acc[k].push(p)
    return acc
  }, {})

  const kinds = Object.keys(groups).sort()

  return (
    <div className="space-y-3 text-sm">
      <div className="text-xs text-muted-foreground">Select a part to see transforms.</div>
      {kinds.map((k) => (
        <div key={k} className="space-y-2">
          <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{k}</div>
          <div className="grid grid-cols-2 gap-2">
            {groups[k].map((p) => (
              <button
                key={p.id}
                className={`px-2 py-1 rounded border text-left hover:bg-muted/40 ${selectedPartId === p.id ? 'bg-muted/50 border-blue-300' : ''}`}
                onClick={() => onSelect(p.id)}
              >
                <div className="font-medium">{p.name}</div>
                <div className="text-[11px] text-muted-foreground break-all">{p.id}</div>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
