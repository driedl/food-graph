import { memo } from 'react'
import { Badge } from '@ui/badge'

export const PartsPanel = memo(function PartsPanel({
  parts,
  selectedPartId,
  onSelect,
  readOnly = false,
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
    category?: {
      id: string;
      name: string;
      description: string;
      kind: string;
    } | null;
  }>
  selectedPartId: string
  onSelect: (id: string) => void
  readOnly?: boolean
}) {
  console.log('PartsPanel render - parts length:', parts?.length, 'selectedPartId:', selectedPartId)
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
      {!readOnly && <div className="text-xs text-muted-foreground">Select a part to see transforms.</div>}
      {kinds.map((k) => (
        <div key={k} className="space-y-2">
          <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{k}</div>
          <div className="grid grid-cols-1 gap-2">
            {groups[k].map((p) => (
              <button
                key={p.id}
                className={`px-3 py-2 rounded border text-left ${readOnly ? 'cursor-pointer hover:bg-muted/40' : 'hover:bg-muted/40'} ${selectedPartId === p.id ? 'bg-muted/50 border-blue-300' : ''} ${!p.applicable ? 'opacity-50' : ''}`}
                onClick={() => onSelect(p.id)}
                disabled={!p.applicable}
              >
                <div className="flex items-center justify-between">
                  <div className="font-medium">{p.name}</div>
                  {p.applicable && (
                    <div className="flex items-center gap-1">
                      {p.identityCount > 0 && (
                        <Badge variant="secondary" className="text-xs bg-green-100 text-green-700">
                          {p.identityCount}I
                        </Badge>
                      )}
                      {p.nonIdentityCount > 0 && (
                        <Badge variant="secondary" className="text-xs bg-blue-100 text-blue-700">
                          {p.nonIdentityCount}T
                        </Badge>
                      )}
                      {p.category && (
                        <Badge variant="outline" className="text-xs">
                          {p.category.name}
                        </Badge>
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
