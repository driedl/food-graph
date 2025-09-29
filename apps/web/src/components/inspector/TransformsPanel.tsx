import { Badge } from '@ui/badge'

export function TransformsPanel({
  loading,
  data,
  chosen,
  onToggleTx,
  onParamChange,
}: {
  loading: boolean
  data?: Array<{ 
    id: string; 
    name: string; 
    identity: boolean; 
    ordering: number;
    notes: string | null;
    family: string;
    schema: Array<{ key: string; kind: 'boolean' | 'number' | 'string' | 'enum'; enum?: string[] }> | null 
  }>
  chosen: Array<{ id: string; params: Record<string, any> }>
  onToggleTx: (id: string, identity: boolean) => void
  onParamChange: (id: string, key: string, value: any) => void
}) {
  if (loading) return <div className="text-sm text-muted-foreground">Loading transforms…</div>
  if (!data || data.length === 0) return <div className="text-sm text-muted-foreground">No transforms for this part.</div>

  const isChosen = (id: string) => chosen.some((t) => t.id === id)
  const currentParams = (id: string) => chosen.find((t) => t.id === id)?.params || {}

  // Group by family
  const families = data.reduce((acc: Record<string, any[]>, t) => {
    const fam = t.family || 'other'
    acc[fam] ||= []
    acc[fam].push(t)
    return acc
  }, {})

  return (
    <div className="space-y-3 text-sm">
      <div className="text-xs text-muted-foreground">Toggle identity transforms and set parameters.</div>
      <div className="space-y-4">
        {Object.entries(families).map(([family, transforms]) => (
          <div key={family} className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground border-b pb-1">
              {family}
            </div>
            {transforms.map((t) => (
              <div key={t.id} className="rounded border p-2">
                <div className="flex items-center justify-between">
                  <div className="font-medium">{t.name}</div>
                  <div className="flex items-center gap-2">
                    <Badge variant={t.identity ? 'default' : 'secondary'} className="text-[10px] uppercase">
                      {t.identity ? 'identity' : 'non-identity'}
                    </Badge>
                    <label className={`text-xs ${t.identity ? '' : 'opacity-50'}`}>
                      <input
                        type="checkbox"
                        className="mr-1"
                        checked={isChosen(t.id)}
                        onChange={() => onToggleTx(t.id, !!t.identity)}
                        disabled={!t.identity}
                      />
                      include
                    </label>
                  </div>
                </div>
                {t.notes && (
                  <div className="text-[10px] text-muted-foreground mt-1 italic">
                    {t.notes}
                  </div>
                )}
                {t.schema && t.schema.length > 0 && isChosen(t.id) && (
                  <div className="mt-2 grid grid-cols-2 gap-2">
                    {t.schema.map((p: any) => (
                      <div key={p.key} className="space-y-1">
                        <div className="text-[11px] text-muted-foreground">{p.key}</div>
                        {p.kind === 'boolean' && (
                          <select
                            className="border rounded px-2 py-1 bg-background"
                            value={String(currentParams(t.id)[p.key] ?? '')}
                            onChange={(e) => onParamChange(t.id, p.key, e.target.value === 'true')}
                          >
                            <option value="">—</option>
                            <option value="true">true</option>
                            <option value="false">false</option>
                          </select>
                        )}
                        {p.kind === 'number' && (
                          <input
                            type="number"
                            className="border rounded px-2 py-1 bg-background"
                            value={currentParams(t.id)[p.key] ?? ''}
                            onChange={(e) => onParamChange(t.id, p.key, Number(e.target.value))}
                          />
                        )}
                        {p.kind === 'string' && (
                          <input
                            type="text"
                            className="border rounded px-2 py-1 bg-background"
                            value={currentParams(t.id)[p.key] ?? ''}
                            onChange={(e) => onParamChange(t.id, p.key, e.target.value)}
                          />
                        )}
                        {p.kind === 'enum' && (
                          <select
                            className="border rounded px-2 py-1 bg-background"
                            value={currentParams(t.id)[p.key] ?? ''}
                            onChange={(e) => onParamChange(t.id, p.key, e.target.value)}
                          >
                            <option value="">—</option>
                            {(p.enum || []).map((v: any) => (
                              <option key={v} value={v}>{v}</option>
                            ))}
                          </select>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
