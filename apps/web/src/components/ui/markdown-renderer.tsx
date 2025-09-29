import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { cn } from '@lib/utils'

interface MarkdownRendererProps {
  children: string
  className?: string
}

export function MarkdownRenderer({ children, className }: MarkdownRendererProps) {
  return (
    <div className={cn(
      // Typography plugin base styles
      'prose prose-sm max-w-none',
      // Custom theme overrides to match your design system
      'prose-headings:text-foreground',
      'prose-p:text-foreground prose-p:text-sm prose-p:leading-relaxed',
      'prose-strong:text-foreground prose-strong:font-semibold',
      'prose-em:text-foreground prose-em:italic',
      'prose-code:bg-muted prose-code:text-foreground prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-mono',
      'prose-pre:bg-muted prose-pre:text-foreground prose-pre:border prose-pre:border-border',
      'prose-blockquote:border-l-border prose-blockquote:text-muted-foreground prose-blockquote:italic',
      'prose-hr:border-border',
      'prose-ul:text-foreground prose-ol:text-foreground',
      'prose-li:text-sm prose-li:leading-relaxed',
      // Table styling to match your existing components
      'prose-table:border-collapse prose-table:border prose-table:border-border',
      'prose-th:bg-muted prose-th:border prose-th:border-border prose-th:px-2 prose-th:py-1 prose-th:text-left prose-th:font-medium prose-th:text-xs',
      'prose-td:border prose-td:border-border prose-td:px-2 prose-td:py-1 prose-td:text-xs',
      // Dark mode support
      'dark:prose-invert',
      className
    )}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>
        {children}
      </ReactMarkdown>
    </div>
  )
}
