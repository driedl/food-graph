import { t } from './_t'
import { db } from '../db'

export const metaRouter = t.router({
    get: t.procedure.query(() => {
        try {
            // Get all meta data from the database
            const metaRows = db.prepare("SELECT key, val FROM meta").all() as Array<{ key: string; val: string }>

            // Convert to object format
            const meta: Record<string, any> = {}
            for (const row of metaRows) {
                const { key, val } = row

                // Parse numeric values
                if (['taxa_count', 'parts_count', 'categories_count', 'substrates_count', 'tpt_count', 'schema_version'].includes(key)) {
                    meta[key] = parseInt(val, 10)
                } else {
                    meta[key] = val
                }
            }

            return meta
        } catch (error) {
            console.error('Error fetching meta data:', error)
            throw new Error('Failed to fetch meta data')
        }
    })
})
