// Utility functions for router modules

export const makeFtsQuery = (q: string) =>
    q.trim().split(/\s+/).filter(Boolean).map(t => `${t}*`).join(' AND ')

export const safeParseJSON = <T = any>(raw: any, fallback: T): T => {
    try {
        if (raw == null) return fallback
        if (typeof raw === 'string') return JSON.parse(raw) as T
        return raw as T
    } catch { return fallback }
}

export const uniq = <T>(arr: T[]) => Array.from(new Set(arr))

export const asString = (v: unknown) => typeof v === 'string' ? v : JSON.stringify(v)

export const inClause = (n: number) => Array(n).fill('?').join(', ')
