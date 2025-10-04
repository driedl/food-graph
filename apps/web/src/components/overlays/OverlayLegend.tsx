import React from 'react'
import { OverlayState, OVERLAY_CATALOG } from '@/lib/overlays'
import { Badge } from '@ui/badge'

export function OverlayLegend({
    state,
    className = ''
}: {
    state: OverlayState
    className?: string
}) {
    if (state.on.length === 0) return null

    return (
        <div className={`text-xs text-muted-foreground ${className}`}>
            <div className="mb-1">Active overlays:</div>
            <div className="flex flex-wrap gap-1">
                {state.on.map((id) => {
                    const meta = OVERLAY_CATALOG.find(m => m.id === id)
                    if (!meta) return null

                    const label = id === 'tf' && state.tfId ? `${meta.label}:${state.tfId}` : meta.label
                    return (
                        <Badge key={id} variant="outline" className="text-[10px]">
                            {label}
                        </Badge>
                    )
                })}
            </div>
        </div>
    )
}