import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/workbench/taxon/$id')({
    component: TaxonPage,
})

function TaxonPage() {
    return (
        <div className="p-4">
            <div className="text-lg font-semibold">Taxon Page</div>
            <div className="text-sm text-muted-foreground">Taxon page implementation coming soon...</div>
        </div>
    )
}
