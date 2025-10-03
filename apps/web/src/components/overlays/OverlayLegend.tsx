import React from 'react'
import { OVERLAY_CATALOG } from '@/lib/overlays'

export function OverlayLegend() {
    return (
        <div className="rounded border p-2 text-xs">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">Legend</div>
            <ul className="space-y-1">
                {OVERLAY_CATALOG.map((m) => (
                    <li key={m.id} className="flex items-start gap-2">
                        <span className="font-medium w-24">{m.label}</span>
                        <span className="text-muted-foreground">{m.desc}</span>
                    </li>
                ))}
            </ul>
        </div>
    )
}
export default OverlayLegend
