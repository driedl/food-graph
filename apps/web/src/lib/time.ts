export function timeAgo(d: Date) {
    const s = Math.floor((Date.now() - d.getTime()) / 1000)
    if (s < 60) return `${s}s ago`
    const m = Math.floor(s / 60)
    if (m < 60) return `${m}m ago`
    const h = Math.floor(m / 60)
    if (h < 24) return `${h}h ago`
    const days = Math.floor(h / 24)
    if (days < 30) return `${days}d ago`
    const mo = Math.floor(days / 30)
    if (mo < 12) return `${mo}mo ago`
    const y = Math.floor(mo / 12)
    return `${y}y ago`
}

export function isOlderThan(d: Date, days: number) {
    const ms = days * 24 * 60 * 60 * 1000
    return Date.now() - d.getTime() > ms
}
