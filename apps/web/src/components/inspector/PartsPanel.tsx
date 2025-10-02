import { memo } from 'react'

export const PartsPanel = memo(function PartsPanel({
  parts,
  selectedPartId,
  onSelect,
}: {
  parts?: Array<{
    id: string;
    name: string;
    kind?: string;
    parentId?: string | null;
    applicable: boolean;
    identityCount: number;
    nonIdentityCount: number;
    synonyms: string[];
  }>
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
          <div className="grid grid-cols-1 gap-2">
            {groups[k].map((p) => (
              <button
                key={p.id}
                className={`px-3 py-2 rounded border text-left hover:bg-muted/40 ${selectedPartId === p.id ? 'bg-muted/50 border-blue-300' : ''} ${!p.applicable ? 'opacity-50' : ''}`}
                onClick={() => onSelect(p.id)}
                disabled={!p.applicable}
              >
                <div className="flex items-center justify-between">
                  <div className="font-medium">{p.name}</div>
                  {p.applicable && (
                    <div className="flex items-center gap-1">
                      {p.identityCount > 0 && (
                        <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                          {p.identityCount}I
                        </span>
                      )}
                      {p.nonIdentityCount > 0 && (
                        <span className="text-xs bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                          {p.nonIdentityCount}T
                        </span>
                      )}
                    </div>
                  )}
                </div>
                <div className="text-[11px] text-muted-foreground break-all">{p.id}</div>
                {p.synonyms.length > 0 && (
                  <div className="text-[10px] text-muted-foreground mt-1">
                    Also: {p.synonyms.slice(0, 2).join(', ')}{p.synonyms.length > 2 && '...'}
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
})
