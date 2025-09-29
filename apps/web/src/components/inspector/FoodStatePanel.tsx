import { Button } from '@ui/button'
import { Input } from '@ui/input'
import { Separator } from '@ui/separator'
import { useState } from 'react'

export function FoodStatePanel({
  fsPreview,
  loadingValidate,
  result,
  onCopy,
  onValidate,
  onParse,
}: {
  fsPreview: string
  loadingValidate: boolean
  result?: { id: string | null; errors: string[] } | null
  onCopy: (s: string) => void
  onValidate: () => void
  onParse?: (fs: string) => void
}) {
  const [parseInput, setParseInput] = useState('')

  return (
    <div className="space-y-3 text-sm">
      <div className="text-muted-foreground">Compose a FoodState identity (client-only preview).</div>
      <Separator />
      
      {/* Parse input */}
      {onParse && (
        <div className="space-y-2">
          <div className="text-xs text-muted-foreground">Paste FoodState path to jump to node/part</div>
          <div className="flex gap-2">
            <Input
              placeholder="fs:/path/to/taxon/part:name/tf:transform"
              value={parseInput}
              onChange={(e) => setParseInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && parseInput.trim()) {
                  onParse(parseInput.trim())
                  setParseInput('')
                }
              }}
            />
            <Button 
              size="sm" 
              onClick={() => {
                if (parseInput.trim()) {
                  onParse(parseInput.trim())
                  setParseInput('')
                }
              }}
              disabled={!parseInput.trim()}
            >
              Jump
            </Button>
          </div>
        </div>
      )}

      <div className="text-xs text-muted-foreground">Preview</div>
      <div className="text-xs font-mono border rounded p-2 bg-muted/30 break-all">{fsPreview || '—'}</div>
      <div className="flex gap-2">
        <Button size="sm" onClick={() => fsPreview && onCopy(fsPreview)} disabled={!fsPreview}>Copy</Button>
        <Button size="sm" variant="outline" onClick={() => onValidate()} disabled={!fsPreview || loadingValidate}>
          {loadingValidate ? 'Validating…' : 'Validate'}
        </Button>
      </div>
      {result && (
        <div className="mt-2 text-xs">
          {result.errors && result.errors.length > 0 ? (
            <div className="text-red-600 space-y-1">
              <div className="font-medium">Errors</div>
              <ul className="list-disc ml-4">
                {result.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          ) : (
            <div className="text-green-700">
              ✓ Valid — <span className="font-mono break-all">{result.id}</span>
            </div>
          )}
        </div>
      )}
      <div className="text-[11px] text-muted-foreground">
        Server validation enforces applicability to lineage + part, and that only identity transforms are in the chain.
      </div>
    </div>
  )
}
