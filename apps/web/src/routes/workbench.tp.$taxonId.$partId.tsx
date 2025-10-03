import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/workbench/tp/$taxonId/$partId')({
    component: TPPage,
})

function TPPage() {
    return (
        <div className="p-4">
            <div className="text-lg font-semibold">TP Page</div>
            <div className="text-sm text-muted-foreground">TP page implementation coming soon...</div>
        </div>
    )
}
