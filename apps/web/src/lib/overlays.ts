// Lightweight overlay model with URL helpers

export type OverlayId =
    | 'parts'            // parts availability (# applicable parts)
    | 'identity'         // identity richness (avg identity steps)
    | 'families'         // family diversity (unique families count)
    | 'cuisines'         // cuisine presence (any/ratio)
    | 'flags'            // flags presence (any/ratio)
    | 'docs'             // documentation presence
    | 'tf'               // transform usage (requires tfId)

export type OverlayState = {
    on: OverlayId[]
    tfId?: string       // only used when 'tf' is enabled
}

export type OverlayMeta = {
    id: OverlayId
    label: string
    desc: string
    needsParam?: 'tfId'
}

export const OVERLAY_CATALOG: OverlayMeta[] = [
    { id: 'parts', label: 'Parts', desc: 'Count of applicable parts under node' },
    { id: 'identity', label: 'Identity', desc: 'Avg #identity steps beneath node' },
    { id: 'families', label: 'Families', desc: 'Unique TPT families under node' },
    { id: 'cuisines', label: 'Cuisines', desc: 'Cuisine presence below node' },
    { id: 'flags', label: 'Flags', desc: 'Safety/dietary flags presence' },
    { id: 'docs', label: 'Docs', desc: 'Documentation presence' },
    { id: 'tf', label: 'Transform', desc: 'Usage intensity for a transform', needsParam: 'tfId' },
]

const SEP = ','
/** overlay param encoding: e.g. "parts,identity,tf:tx:milling" */
export function serializeOverlayParam(state: OverlayState): string {
    const base = (state.on || []).map((id) =>
        id === 'tf' && state.tfId ? `tf:${state.tfId}` : id
    )
    return base.join(SEP)
}

export function parseOverlayParam(raw?: string | null): OverlayState {
    const on: OverlayId[] = []
    let tfId: string | undefined
    if (raw && raw.trim()) {
        for (const tok of raw.split(SEP)) {
            const t = tok.trim()
            if (!t) continue
            if (t.startsWith('tf:')) {
                const id = t.slice(3)
                if (id) { on.push('tf'); tfId = id }
            } else if (isOverlayId(t)) {
                on.push(t)
            }
        }
    }
    // de-dupe and preserve order
    const seen = new Set<string>()
    const uniq = on.filter((x) => (seen.has(x) ? false : (seen.add(x), true)))
    return { on: uniq as OverlayId[], tfId }
}

export function toggleOverlay(state: OverlayState, id: OverlayId): OverlayState {
    const on = state.on.includes(id)
        ? state.on.filter((x) => x !== id)
        : [...state.on, id]
    const next: OverlayState = { ...state, on }
    if (!on.includes('tf')) next.tfId = undefined
    return next
}

export function setTfId(state: OverlayState, tfId?: string): OverlayState {
    const next = { ...state, tfId }
    if (tfId && !next.on.includes('tf')) next.on = [...next.on, 'tf']
    return next
}

export function hasOverlay(state: OverlayState, id: OverlayId) {
    return state.on.includes(id)
}

function isOverlayId(s: string): s is OverlayId {
    return (OVERLAY_CATALOG as any[]).some((m) => m.id === s)
}
