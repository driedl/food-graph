import React from 'react'
import type { OverlayState } from '@/lib/overlays'
import { hasOverlay } from '@/lib/overlays'
import { Badge } from '@ui/badge'

/**
 * These badge helpers are intentionally UI-only with placeholder heuristics.
 * Wire them to real metrics as API fields land.
 */

export type TaxonLike = {
    id: string
    name?: string
    slug?: string
    rank?: string
    // optional metrics if available
    _partsCount?: number
    _identityAvg?: number
    _familiesCount?: number
    _cuisinesCount?: number
    _flagsCount?: number
    _docs?: boolean
    _tfHits?: number
}

/** Tiny badge pill */
function Pill({ children }: { children: React.ReactNode }) {
    return <Badge variant="secondary" className="text-[10px]">{children}</Badge>
}

/** Render a set of badges for a taxon row given overlay state. */
export function badgesForTaxon(row: TaxonLike, ov: OverlayState) {
    const out: React.ReactNode[] = []
    if (hasOverlay(ov, 'parts')) out.push(<Pill key="parts">{row._partsCount ?? '—'} parts</Pill>)
    if (hasOverlay(ov, 'identity')) out.push(<Pill key="ident">{fmt(row._identityAvg, 1)} id</Pill>)
    if (hasOverlay(ov, 'families')) out.push(<Pill key="fams">{row._familiesCount ?? '—'} fam</Pill>)
    if (hasOverlay(ov, 'cuisines')) out.push(<Pill key="cuis">{row._cuisinesCount ?? '—'} cui</Pill>)
    if (hasOverlay(ov, 'flags')) out.push(<Pill key="flags">{row._flagsCount ?? '—'} flags</Pill>)
    if (hasOverlay(ov, 'docs')) out.push(<Pill key="docs">{row._docs ? 'docs' : '—'}</Pill>)
    if (hasOverlay(ov, 'tf')) out.push(<Pill key="tf">{row._tfHits ?? '—'} × tf</Pill>)
    return out.length ? <div className="flex flex-wrap gap-1">{out}</div> : null
}

/** Same badges but for node data payloads. */
export function badgesForNodeData(data: any, ov: OverlayState) {
    const row: TaxonLike = {
        id: data?.id,
        name: data?.name,
        slug: data?.slug,
        rank: data?.rank,
        _partsCount: data?._partsCount,
        _identityAvg: data?._identityAvg,
        _familiesCount: data?._familiesCount,
        _cuisinesCount: data?._cuisinesCount,
        _flagsCount: data?._flagsCount,
        _docs: data?._docs,
        _tfHits: data?._tfHits,
    }
    return badgesForTaxon(row, ov)
}

function fmt(v: any, d = 0) {
    return typeof v === 'number' ? v.toFixed(d) : '—'
}
