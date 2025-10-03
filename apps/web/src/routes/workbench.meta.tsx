import { createFileRoute } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'
import { Badge } from '@ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'

export const Route = createFileRoute('/workbench/meta')({
    component: MetaPage,
})

function MetaPage() {
    const metaQ = (trpc as any).meta?.get?.useQuery()

    const meta = metaQ?.data
    const isLoading = metaQ?.isLoading

    // Calculate age in days
    const getAgeInDays = (buildTime?: string) => {
        if (!buildTime) return null
        const buildDate = new Date(buildTime)
        const now = new Date()
        const diffTime = Math.abs(now.getTime() - buildDate.getTime())
        return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
    }

    const ageInDays = getAgeInDays(meta?.build_time)
    const isStale = ageInDays && ageInDays > 14
    const isVeryStale = ageInDays && ageInDays > 30

    return (
        <div className="p-4 space-y-4">
            <div className="text-lg font-semibold">Meta</div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Build Info */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Build Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                        {isLoading ? (
                            <div className="space-y-2">
                                <div className="h-4 bg-muted rounded w-3/4" />
                                <div className="h-4 bg-muted rounded w-1/2" />
                            </div>
                        ) : (
                            <>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm">Schema Version:</span>
                                    <Badge variant="secondary">{meta?.schema_version || 'Unknown'}</Badge>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm">Build Time:</span>
                                    <div className="text-right">
                                        <div className="text-sm">{meta?.build_time ? new Date(meta.build_time).toLocaleString() : 'Unknown'}</div>
                                        {ageInDays && (
                                            <div className="text-xs text-muted-foreground">
                                                Age: {ageInDays} days
                                                {isVeryStale && <Badge variant="destructive" className="ml-2">STALE</Badge>}
                                                {isStale && !isVeryStale && <Badge variant="outline" className="ml-2">WARN</Badge>}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </>
                        )}
                    </CardContent>
                </Card>

                {/* Counts */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-sm">Entity Counts</CardTitle>
                    </CardHeader>
                    <CardContent>
                        {isLoading ? (
                            <div className="space-y-2">
                                {Array.from({ length: 4 }).map((_, i) => (
                                    <div key={i} className="h-4 bg-muted rounded" />
                                ))}
                            </div>
                        ) : (
                            <div className="grid grid-cols-2 gap-2 text-sm">
                                <div className="flex justify-between">
                                    <span>Taxa:</span>
                                    <span className="font-mono">{meta?.taxa_count?.toLocaleString() || '0'}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>Parts:</span>
                                    <span className="font-mono">{meta?.parts_count?.toLocaleString() || '0'}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>Substrates:</span>
                                    <span className="font-mono">{meta?.substrates_count?.toLocaleString() || '0'}</span>
                                </div>
                                <div className="flex justify-between">
                                    <span>TPTs:</span>
                                    <span className="font-mono">{meta?.tpt_count?.toLocaleString() || '0'}</span>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>
            </div>

            {/* Status */}
            <Card>
                <CardHeader>
                    <CardTitle className="text-sm">System Status</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-sm">API Status:</span>
                            <Badge variant="outline" className="border-green-600">OK</Badge>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-sm">Database:</span>
                            <Badge variant="outline" className="border-green-600">Connected</Badge>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-sm">Search Index:</span>
                            <Badge variant="outline" className="border-green-600">Ready</Badge>
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
