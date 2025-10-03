// URL parameter utilities for the workbench

export function parseSearchParams(search: Record<string, unknown>) {
    const q = typeof search.q === 'string' ? search.q : ''
    const tab = typeof search.tab === 'string' ? search.tab : ''
    const limit = Number.isFinite(Number(search.limit)) ? Math.max(10, Math.min(500, Number(search.limit))) : 50
    const offset = Number.isFinite(Number(search.offset)) ? Math.max(0, Number(search.offset)) : 0
    const overlay = typeof search.overlay === 'string' ? search.overlay : ''
    const compare = typeof search.compare === 'string' ? search.compare : ''
    const family = typeof search.family === 'string' ? search.family : ''
    const cuisines = typeof search.cuisines === 'string' ? search.cuisines : ''
    const flags = typeof search.flags === 'string' ? search.flags : ''
    const type = typeof search.type === 'string' ? search.type : 'any'
    const taxonId = typeof search.taxonId === 'string' ? search.taxonId : ''
    const partId = typeof search.partId === 'string' ? search.partId : ''

    return {
        q,
        tab,
        limit,
        offset,
        overlay,
        compare,
        family,
        cuisines,
        flags,
        type,
        taxonId,
        partId,
    }
}

export function serializeSearchParams(params: Record<string, any>): Record<string, string> {
    const result: Record<string, string> = {}

    Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== '') {
            if (Array.isArray(value)) {
                result[key] = value.join(',')
            } else {
                result[key] = String(value)
            }
        }
    })

    return result
}

export function parseCommaList(value: string): string[] {
    if (!value) return []
    return value.split(',').map(s => s.trim()).filter(Boolean)
}

export function serializeCommaList(values: string[]): string {
    return values.filter(Boolean).join(',')
}

// Debounced URL updates
let urlUpdateTimeout: NodeJS.Timeout | null = null

export function debouncedUrlUpdate(updateFn: () => void, delay = 150) {
    if (urlUpdateTimeout) {
        clearTimeout(urlUpdateTimeout)
    }
    urlUpdateTimeout = setTimeout(updateFn, delay)
}
