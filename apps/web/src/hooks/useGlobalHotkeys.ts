import { useEffect } from 'react'
import { useNavigate } from '@tanstack/react-router'

export function useGlobalHotkeys() {
    const navigate = useNavigate()

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Focus search on ⌘/Ctrl+K
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault()
                const searchInput = document.querySelector('input[placeholder*="Search"]') as HTMLInputElement
                searchInput?.focus()
                return
            }

            // Global navigation (g + letter)
            if (e.key === 'g' && !e.metaKey && !e.ctrlKey && !e.altKey) {
                // Wait for next key
                const handleNextKey = (nextE: KeyboardEvent) => {
                    if (nextE.key === 't') navigate({ to: '/workbench/families' })
                    else if (nextE.key === 'c') navigate({ to: '/workbench/cuisines' })
                    else if (nextE.key === 'f') navigate({ to: '/workbench/flags' })
                    else if (nextE.key === 'm') navigate({ to: '/workbench/meta' })
                    document.removeEventListener('keydown', handleNextKey)
                }
                document.addEventListener('keydown', handleNextKey, { once: true })
                return
            }

            // Tab cycling with [ and ]
            if (e.key === '[' || e.key === ']') {
                const currentPage = window.location.pathname
                const tabs = getTabsForPage(currentPage)
                if (tabs.length > 1) {
                    e.preventDefault()
                    const currentTab = new URLSearchParams(window.location.search).get('tab') || tabs[0]
                    const currentIndex = tabs.indexOf(currentTab)
                    const nextIndex = e.key === '['
                        ? (currentIndex - 1 + tabs.length) % tabs.length
                        : (currentIndex + 1) % tabs.length
                    const nextTab = tabs[nextIndex]
                    navigate({
                        to: currentPage as any,
                        search: (s: any) => ({ ...s, tab: nextTab })
                    })
                }
            }
        }

        document.addEventListener('keydown', handleKeyDown)
        return () => document.removeEventListener('keydown', handleKeyDown)
    }, [navigate])
}

function getTabsForPage(pathname: string): string[] {
    if (pathname.includes('/workbench/taxon/')) return ['overview', 'graph', 'lists']
    if (pathname.includes('/workbench/tp/')) return ['overview', 'transforms', 'compare']
    if (pathname.includes('/workbench/tpt/')) return ['overview', 'explain', 'graph']
    return []
}
