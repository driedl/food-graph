import { z } from 'zod'
import { TRPCError } from '@trpc/server'
import { db } from '../db'
import { t } from './_t'
import { safeParseJSON, uniq } from './_util'

export const tpRouter = t.router({
    /** Get a TP node with useful labels and aggregated synonyms.
     *  Synonyms are aggregated from all TPTs under the same (taxon, part). */
    get: t.procedure
        .input(z.object({ id: z.string() })) // expected form: "tx:...:part:..."
        .query(({ input }) => {
            const row = db.prepare(`
        SELECT 
          tp.id, tp.taxon_id, tp.part_id, tp.name, tp.display_name, tp.slug, tp.rank,
          n.name AS taxon_name, n.rank AS taxon_rank,
          p.name AS part_name
        FROM taxon_part_nodes tp
        JOIN nodes n ON n.id = tp.taxon_id
        JOIN part_def p ON p.id = tp.part_id
        WHERE tp.id = ?
      `).get(input.id) as any
            if (!row) throw new TRPCError({ code: 'NOT_FOUND' })

            // Aggregate TP-level synonyms from TPTs (synonyms JSON on each TPT row)
            const synRows = db.prepare(`
        SELECT t.synonyms FROM tpt_nodes t
        WHERE t.taxon_id = ? AND t.part_id = ?
      `).all(row.taxon_id, row.part_id) as Array<{ synonyms?: string }>
            const syns = uniq(
                synRows.flatMap(r => safeParseJSON<string[]>(r.synonyms ?? '[]', []))
                    .map(s => s.trim().toLowerCase())
                    .filter(Boolean)
            )

            return {
                id: row.id,
                taxonId: row.taxon_id,
                partId: row.part_id,
                name: row.display_name ?? row.name,
                slug: row.slug,
                rank: row.rank,
                taxon: { id: row.taxon_id, name: row.taxon_name, rank: row.taxon_rank },
                part: { id: row.part_id, name: row.part_name },
                synonyms: syns
            }
        }),
})
