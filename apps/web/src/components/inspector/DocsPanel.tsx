import { Badge } from '@ui/badge'
import { Separator } from '@ui/separator'
import { MarkdownRenderer } from '@ui/markdown-renderer'

export function DocsPanel({
  docs,
  node,
}: {
  docs: any
  node?: { id: string; name: string }
}) {
  if (!node) return <div className="text-sm text-muted-foreground">Select a node</div>
  if (!docs) {
    return (
      <div className="text-center text-muted-foreground py-8">
        <div className="text-sm">No documentation available</div>
        <div className="text-xs mt-1">Documentation is sparse and only available for some taxa</div>
      </div>
    )
  }
  return (
    <div className="space-y-3 text-sm">
      {docs.summary && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Summary</div>
          <div className="text-sm leading-relaxed">{docs.summary}</div>
        </div>
      )}
      {docs.description_md && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Description</div>
          <MarkdownRenderer>{docs.description_md}</MarkdownRenderer>
        </div>
      )}
      {docs.tags && docs.tags.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Tags</div>
          <div className="flex flex-wrap gap-1">
            {docs.tags.map((tag: string, i: number) => (
              <Badge key={i} variant="secondary" className="text-xs">
                {tag}
              </Badge>
            ))}
          </div>
        </div>
      )}
      <Separator />
      <div className="text-xs text-muted-foreground">Last updated: {docs.updated_at}</div>
    </div>
  )
}
