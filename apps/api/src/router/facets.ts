import { z } from 'zod'
import { db } from '../db'
import { t } from './_t'

export const facetsRouter = t.router({
    /** Families available for a Taxon+Part (with counts) */
    familiesForTaxonPart: t.procedure
        .input(z.object({
            taxonId: z.string(),
            partId: z.string(),
            limit: z.number().min(1).max(100).default(20)
        }))
        .query(({ input }) => {
            const rows = db.prepare(`
        SELECT family, COUNT(*) AS count
        FROM tpt_nodes
        WHERE taxon_id = ? AND part_id = ?
        GROUP BY family
        ORDER BY count DESC, family ASC
        LIMIT ?
      `).all(input.taxonId, input.partId, input.limit) as Array<{ family: string; count: number }>
            return rows
        }),

    /** Parts ranked by # of TPT identities under a taxon (desc) */
    partsForTaxonByTPT: t.procedure
        .input(z.object({
            taxonId: z.string(),
            limit: z.number().min(1).max(200).default(50)
        }))
        .query(({ input }) => {
            const rows = db.prepare(`
        SELECT p.id AS partId, p.name AS partName, COUNT(t.id) AS count
        FROM tpt_nodes t
        JOIN part_def p ON p.id = t.part_id
        WHERE t.taxon_id = ?
        GROUP BY p.id, p.name
        ORDER BY count DESC, p.name ASC
        LIMIT ?
      `).all(input.taxonId, input.limit) as Array<{ partId: string; partName: string; count: number }>
            return rows
        }),

    /** Families rolled up at a taxon (across parts) */
    familiesForTaxon: t.procedure
        .input(z.object({
            taxonId: z.string(),
            limit: z.number().min(1).max(200).default(50)
        }))
        .query(({ input }) => {
            const rows = db.prepare(`
        SELECT family, COUNT(*) AS count
        FROM tpt_nodes
        WHERE taxon_id = ?
        GROUP BY family
        ORDER BY count DESC, family ASC
        LIMIT ?
      `).all(input.taxonId, input.limit) as Array<{ family: string; count: number }>
            return rows
        }),

    /** Overlay data for taxon children - provides metrics for overlay badges */
    overlayDataForTaxon: t.procedure
        .input(z.object({
            taxonId: z.string(),
            overlayTypes: z.array(z.enum(['parts', 'identity', 'families', 'cuisines', 'flags', 'docs', 'tf'])).default(['parts', 'families', 'cuisines', 'flags', 'docs']),
            tfId: z.string().optional()
        }))
        .query(({ input }) => {
            const results: Record<string, any> = {}

            // Parts count overlay
            if (input.overlayTypes.includes('parts')) {
                const partsData = db.prepare(`
                    SELECT 
                        n.id,
                        COUNT(DISTINCT p.id) as partsCount,
                        GROUP_CONCAT(DISTINCT p.name) as partsList
                    FROM nodes n
                    LEFT JOIN tpt_nodes tpt ON tpt.taxon_id = n.id
                    LEFT JOIN part_def p ON p.id = tpt.part_id
                    WHERE n.parent_id = ?
                    GROUP BY n.id
                `).all(input.taxonId) as Array<{ id: string; partsCount: number; partsList: string }>

                partsData.forEach(row => {
                    if (!results[row.id]) results[row.id] = {}
                    results[row.id]._partsCount = row.partsCount
                    results[row.id]._parts = row.partsList?.split(',').filter(Boolean) || []
                })
            }

            // Identity richness overlay (average identity steps)
            if (input.overlayTypes.includes('identity')) {
                const identityData = db.prepare(`
                    SELECT 
                        n.id,
                        AVG(CAST(JSON_ARRAY_LENGTH(tpt.path_json) AS REAL)) as identityAvg
                    FROM nodes n
                    LEFT JOIN tpt_nodes tpt ON tpt.taxon_id = n.id
                    WHERE n.parent_id = ? AND tpt.path_json IS NOT NULL
                    GROUP BY n.id
                `).all(input.taxonId) as Array<{ id: string; identityAvg: number }>

                identityData.forEach(row => {
                    if (!results[row.id]) results[row.id] = {}
                    results[row.id]._identityAvg = row.identityAvg
                })
            }

            // Families count overlay
            if (input.overlayTypes.includes('families')) {
                const familiesData = db.prepare(`
                    SELECT 
                        n.id,
                        COUNT(DISTINCT tpt.family) as familiesCount,
                        GROUP_CONCAT(DISTINCT tpt.family) as familiesList
                    FROM nodes n
                    LEFT JOIN tpt_nodes tpt ON tpt.taxon_id = n.id
                    WHERE n.parent_id = ? AND tpt.family IS NOT NULL
                    GROUP BY n.id
                `).all(input.taxonId) as Array<{ id: string; familiesCount: number; familiesList: string }>

                familiesData.forEach(row => {
                    if (!results[row.id]) results[row.id] = {}
                    results[row.id]._familiesCount = row.familiesCount
                    results[row.id]._families = row.familiesList?.split(',').filter(Boolean) || []
                })
            }

            // Cuisines count overlay
            if (input.overlayTypes.includes('cuisines')) {
                const cuisinesData = db.prepare(`
                    SELECT 
                        n.id,
                        COUNT(DISTINCT tc.cuisine) as cuisinesCount,
                        GROUP_CONCAT(DISTINCT tc.cuisine) as cuisinesList
                    FROM nodes n
                    LEFT JOIN tpt_nodes tpt ON tpt.taxon_id = n.id
                    LEFT JOIN tpt_cuisines tc ON tc.tpt_id = tpt.id
                    WHERE n.parent_id = ?
                    GROUP BY n.id
                `).all(input.taxonId) as Array<{ id: string; cuisinesCount: number; cuisinesList: string }>

                cuisinesData.forEach(row => {
                    if (!results[row.id]) results[row.id] = {}
                    results[row.id]._cuisinesCount = row.cuisinesCount
                    results[row.id]._cuisines = row.cuisinesList?.split(',').filter(Boolean) || []
                })
            }

            // Flags count overlay
            if (input.overlayTypes.includes('flags')) {
                const flagsData = db.prepare(`
                    SELECT 
                        n.id,
                        COUNT(DISTINCT tf.flag) as flagsCount,
                        GROUP_CONCAT(DISTINCT tf.flag) as flagsList
                    FROM nodes n
                    LEFT JOIN tpt_nodes tpt ON tpt.taxon_id = n.id
                    LEFT JOIN tpt_flags tf ON tf.tpt_id = tpt.id
                    WHERE n.parent_id = ?
                    GROUP BY n.id
                `).all(input.taxonId) as Array<{ id: string; flagsCount: number; flagsList: string }>

                flagsData.forEach(row => {
                    if (!results[row.id]) results[row.id] = {}
                    results[row.id]._flagsCount = row.flagsCount
                    results[row.id]._flags = row.flagsList?.split(',').filter(Boolean) || []
                })
            }

            // Docs presence overlay
            if (input.overlayTypes.includes('docs')) {
                const docsData = db.prepare(`
                    SELECT 
                        n.id,
                        CASE WHEN td.taxon_id IS NOT NULL THEN 1 ELSE 0 END as hasDocs
                    FROM nodes n
                    LEFT JOIN taxon_doc td ON td.taxon_id = n.id
                    WHERE n.parent_id = ?
                `).all(input.taxonId) as Array<{ id: string; hasDocs: number }>

                docsData.forEach(row => {
                    if (!results[row.id]) results[row.id] = {}
                    results[row.id]._docs = !!row.hasDocs
                })
            }

            // Transform usage overlay
            if (input.overlayTypes.includes('tf') && input.tfId) {
                const tfData = db.prepare(`
                    SELECT 
                        n.id,
                        COUNT(tis.tf_id) as tfHits
                    FROM nodes n
                    LEFT JOIN tpt_nodes tpt ON tpt.taxon_id = n.id
                    LEFT JOIN tpt_identity_steps tis ON tis.tpt_id = tpt.id AND tis.tf_id = ?
                    WHERE n.parent_id = ?
                    GROUP BY n.id
                `).all(input.tfId, input.taxonId) as Array<{ id: string; tfHits: number }>

                tfData.forEach(row => {
                    if (!results[row.id]) results[row.id] = {}
                    results[row.id]._tfHits = row.tfHits
                })
            }

            return results
        }),
})
