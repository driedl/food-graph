import { z } from 'zod'
import { db } from '../db'
import { t } from './_t'
import { makeFtsQuery, inClause } from './_util'

export const browseRouter = t.router({
    // Existing families endpoint
    families: t.procedure
        .input(z.object({
            family: z.string().min(1),
            q: z.string().optional(),
            taxonPrefix: z.string().optional(),
            taxonId: z.string().optional(),
            partId: z.string().optional(),
            limit: z.number().min(1).max(200).default(50),
            offset: z.number().min(0).default(0)
        }))
        .query(({ input }) => {
            const { family, q, taxonPrefix, taxonId, partId, limit, offset } = input
            const where: string[] = [`sc.ref_type = 'tpt'`, `sc.family = ?`]
            const params: any[] = [family]
            if (taxonId) { where.push(`sc.taxon_id = ?`); params.push(taxonId) }
            if (partId) { where.push(`sc.part_id  = ?`); params.push(partId) }
            if (taxonPrefix) { where.push(`sc.taxon_id LIKE ?`); params.push(`${taxonPrefix}%`) }

            // If q is present, join FTS and order by relevance; else order by name.
            if (q && q.trim()) {
                const fts = makeFtsQuery(q)
                const rows = db.prepare(`
          SELECT sc.ref_id AS id, sc.name, sc.taxon_id AS taxonId, sc.part_id AS partId,
                 sc.family, sc.entity_rank AS rank,
                 bm25(search_fts) AS score
          FROM search_content sc
          JOIN search_fts ON search_fts.rowid = sc.rowid
          WHERE ${where.join(' AND ')} AND search_fts MATCH ?
          ORDER BY bm25(search_fts) ASC, sc.name ASC
          LIMIT ? OFFSET ?
        `).all(...params, fts, limit, offset) as any[]
                return rows
            } else {
                const rows = db.prepare(`
          SELECT sc.ref_id AS id, sc.name, sc.taxon_id AS taxonId, sc.part_id AS partId,
                 sc.family, sc.entity_rank AS rank
          FROM search_content sc
          WHERE ${where.join(' AND ')}
          ORDER BY sc.name ASC
          LIMIT ? OFFSET ?
        `).all(...params, limit, offset) as any[]
                return rows
            }
        }),

    // New: Get all families with metadata
    getFamilies: t.procedure.query(() => {
        try {
            const stmt = db.prepare(`
        SELECT 
          fm.id, fm.label, fm.icon, fm.color, fm.blurb,
          COUNT(tpt.id) as count
        FROM family_meta fm
        LEFT JOIN tpt_nodes tpt ON tpt.family = fm.id
        GROUP BY fm.id, fm.label, fm.icon, fm.color, fm.blurb
        ORDER BY count DESC, fm.label ASC
      `)
            return stmt.all() as any[]
        } catch {
            return []
        }
    }),

    // New: Get all cuisines with counts
    getCuisines: t.procedure.query(() => {
        try {
            const stmt = db.prepare(`
        SELECT 
          cuisine as id,
          cuisine as label,
          COUNT(*) as count
        FROM tpt_cuisines
        GROUP BY cuisine
        ORDER BY count DESC, cuisine ASC
      `)
            return stmt.all() as any[]
        } catch {
            // Return empty array if table doesn't exist
            return []
        }
    }),

    // New: Get TPTs for a specific family
    getFamilyEntities: t.procedure
        .input(z.object({
            familyId: z.string(),
            limit: z.number().min(1).max(200).default(50),
            offset: z.number().min(0).default(0)
        }))
        .query(({ input }) => {
            const stmt = db.prepare(`
        SELECT 
          tpt.id, tpt.name, tpt.family, tpt.synonyms,
          n.name as taxon_name, p.name as part_name
        FROM tpt_nodes tpt
        JOIN nodes n ON n.id = tpt.taxon_id
        JOIN part_def p ON p.id = tpt.part_id
        WHERE tpt.family = ?
        ORDER BY tpt.name ASC
        LIMIT ? OFFSET ?
      `)
            return stmt.all(input.familyId, input.limit, input.offset) as any[]
        }),
})
