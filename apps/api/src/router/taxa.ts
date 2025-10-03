import { z } from 'zod'
import { db } from '../db'
import { t } from './_t'
import { inClause } from './_util'
import { hasTable } from './_guards'

export const taxaRouter = t.router({
    // Get parts for a taxon with popularity ranking
    getParts: t.procedure
        .input(z.object({
            taxonId: z.string(),
            limit: z.number().min(1).max(100).default(20)
        }))
        .query(({ input }) => {
            const stmt = db.prepare(`
        SELECT 
          tp.id, tp.name, tp.display_name, tp.slug,
          p.name as part_name,
          COUNT(tpt.id) as derivedCount
        FROM taxon_part_nodes tp
        JOIN part_def p ON p.id = tp.part_id
        LEFT JOIN tpt_nodes tpt ON tpt.taxon_id = tp.taxon_id AND tpt.part_id = tp.part_id
        WHERE tp.taxon_id = ?
        GROUP BY tp.id, tp.name, tp.display_name, tp.slug, p.name
        ORDER BY derivedCount DESC, tp.name ASC
        LIMIT ?
      `)
            return stmt.all(input.taxonId, input.limit) as any[]
        }),

    // Get derived foods (TPTs) for a taxon
    getDerived: t.procedure
        .input(z.object({
            taxonId: z.string(),
            partId: z.string().optional(),
            families: z.array(z.string()).optional(),
            flags: z.array(z.string()).optional(),
            limit: z.number().min(1).max(100).default(50),
            offset: z.number().min(0).default(0)
        }))
        .query(({ input }) => {
            const where: string[] = ['tpt.taxon_id = ?']
            const params: any[] = [input.taxonId]

            if (input.partId) {
                where.push('tpt.part_id = ?')
                params.push(input.partId)
            }

            if (input.families && input.families.length > 0) {
                where.push(`tpt.family IN (${inClause(input.families.length)})`)
                params.push(...input.families)
            }

            if (input.flags && input.flags.length > 0) {
                if (!hasTable('tpt_flags')) return []
                where.push(`EXISTS (
          SELECT 1 FROM tpt_flags tf 
          WHERE tf.tpt_id = tpt.id AND tf.flag IN (${inClause(input.flags.length)})
        )`)
                params.push(...input.flags)
            }

            const stmt = db.prepare(`
        SELECT 
          tpt.id, tpt.name, tpt.family, tpt.synonyms,
          p.name as part_name
        FROM tpt_nodes tpt
        JOIN part_def p ON p.id = tpt.part_id
        WHERE ${where.join(' AND ')}
        ORDER BY tpt.name ASC
        LIMIT ? OFFSET ?
      `)

            return stmt.all(...params, input.limit, input.offset) as any[]
        }),
})
