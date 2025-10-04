import React, { useMemo } from 'react'
import { OVERLAY_CATALOG, OverlayId, OverlayState, toggleOverlay, setTfId } from '@/lib/overlays'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'

export function OverlaysBar({
    value,
    onChange,
    disabledIds = [],
    compact = false,
    rightSlot,
}: {
    value: OverlayState
    onChange: (next: OverlayState) => void
    disabledIds?: OverlayId[]
    compact?: boolean
    rightSlot?: React.ReactNode
}) {
    const meta = useMemo(
        () => OVERLAY_CATALOG.filter((m) => !disabledIds.includes(m.id)),
        [disabledIds]
    )

    return (
        <div className={`flex flex-wrap items-center gap-2 ${compact ? '' : 'mb-2'}`}>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">Overlays</div>
            {meta.map((m) => {
                const active = value.on.includes(m.id)
                return (
                    <button
                        key={m.id}
                        title={m.desc}
                        className={`text-xs rounded border px-2 py-1 ${active ? 'bg-muted/70' : 'bg-background hover:bg-muted/40'}`}
                        onClick={() => onChange(toggleOverlay(value, m.id))}
                    >
                        {m.label}
                    </button>
                )
            })}

            {/* Transform ID input when tf overlay is active */}
            {value.on.includes('tf') && (
                <div className="flex items-center gap-1">
                    <Input
                        placeholder="Transform ID"
                        value={value.tfId || ''}
                        onChange={(e) => onChange(setTfId(value, e.target.value || undefined))}
                        className="w-32 h-6 text-xs"
                    />
                </div>
            )}

            {rightSlot}
        </div>
    )
}

export function OverlayBadge({
    overlay,
    value,
    className = ''
}: {
    overlay: OverlayId
    value: string | number
    className?: string
}) {
    return (
        <Badge
            variant="secondary"
            className={`text-[10px] px-1 py-0 ${className}`}
        >
            {value}
        </Badge>
    )
}