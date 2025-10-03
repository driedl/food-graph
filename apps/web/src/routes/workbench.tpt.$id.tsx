import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/workbench/tpt/$id')({
    component: TPTPage,
})

function TPTPage() {
    return (
        <div className="p-4">
            <div className="text-lg font-semibold">TPT Page</div>
            <div className="text-sm text-muted-foreground">TPT page implementation coming soon...</div>
        </div>
    )
}
