import { db } from '../db'

// Guard functions for optional table handling

export const hasTable = (name: string): boolean => {
    try {
        const result = db.prepare(`SELECT name FROM sqlite_master WHERE type='table' AND name=?`).get(name)
        return !!result
    } catch {
        return false
    }
}

export const optionalJoin = ({ when, sql }: { when: boolean; sql: string }): string => {
    return when ? sql : ''
}

export const requireTablesOrEmpty = ({
    need,
    ifMissing
}: {
    need: string[];
    ifMissing: 'empty' | 'error'
}) => {
    const missing = need.filter(table => !hasTable(table))

    if (missing.length > 0) {
        if (ifMissing === 'error') {
            throw new Error(`Required tables missing: ${missing.join(', ')}`)
        }
        return false
    }

    return true
}
