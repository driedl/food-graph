// Time utility helpers for UI components

export function timeAgo(date: Date | string | number): string {
    const now = new Date()
    const then = new Date(date)
    const diffMs = now.getTime() - then.getTime()

    const seconds = Math.floor(diffMs / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)
    const weeks = Math.floor(days / 7)
    const months = Math.floor(days / 30)
    const years = Math.floor(days / 365)

    if (years > 0) return `${years}y ago`
    if (months > 0) return `${months}mo ago`
    if (weeks > 0) return `${weeks}w ago`
    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    if (minutes > 0) return `${minutes}m ago`
    return `${seconds}s ago`
}

export function isOlderThan(date: Date | string | number, thresholdDays: number): boolean {
    const now = new Date()
    const then = new Date(date)
    const diffMs = now.getTime() - then.getTime()
    const diffDays = diffMs / (1000 * 60 * 60 * 24)
    return diffDays > thresholdDays
}

export function formatBuildTime(date: Date | string | number): string {
    const d = new Date(date)
    return d.toLocaleDateString() + ' ' + d.toLocaleTimeString()
}

export function getBuildAgeDays(date: Date | string | number): number {
    const now = new Date()
    const then = new Date(date)
    const diffMs = now.getTime() - then.getTime()
    return Math.floor(diffMs / (1000 * 60 * 60 * 24))
}