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
})
