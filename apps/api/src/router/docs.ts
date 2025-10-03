import { z } from 'zod'
import { db } from '../db'
import { t } from './_t'
import { inClause } from './_util'

export const docsRouter = t.router({
    getByTaxon: t.procedure
        .input(z.object({
            taxonId: z.string(),
            lang: z.string().default('en')
        }))
        .query(({ input }) => {
            const stmt = db.prepare(`
        SELECT td.taxon_id, td.lang, td.summary, td.description_md, td.updated_at,
               n.name, n.slug, n.rank
        FROM taxon_doc td
        JOIN nodes n ON td.taxon_id = n.id
        WHERE td.taxon_id = ? AND td.lang = ?
      `)
            return stmt.get(input.taxonId, input.lang) ?? null
        }),

    overview: t.procedure
        .input(z.object({ taxonId: z.string(), childLimit: z.number().default(25) }))
        .query(({ input }) => {
            const doc = db.prepare(`
        SELECT td.taxon_id, td.summary, td.description_md, td.updated_at,
               n.name, n.slug, n.rank
        FROM taxon_doc td
        JOIN nodes n ON td.taxon_id = n.id
        WHERE td.taxon_id = ? AND td.lang = 'en'
      `).get(input.taxonId) || null

            const lineage = db.prepare(`
        WITH RECURSIVE lineage(id,name,rank,parent_id,depth) AS (
          SELECT id,name,rank,parent_id,0 FROM nodes WHERE id = ?
          UNION ALL
          SELECT n.id,n.name,n.rank,n.parent_id,depth+1
          FROM nodes n JOIN lineage l ON n.id = l.parent_id
        )
        SELECT id,name,rank FROM lineage ORDER BY depth DESC
      `).all(input.taxonId)

            const children = db.prepare(`
        SELECT id,name,rank FROM nodes WHERE parent_id = ?
        ORDER BY name LIMIT ?
      `).all(input.taxonId, input.childLimit)

            // FIXED: Short-circuit when children.length === 0 to avoid IN () clause
            const childDocSummaries = children.length
                ? db.prepare(`
            SELECT taxon_id, summary FROM taxon_doc
            WHERE taxon_id IN (${inClause(children.length)}) AND lang='en'
          `).all(...children.map((c: any) => c.id))
                : []

            const docMap = new Map(childDocSummaries.map((d: any) => [d.taxon_id, d.summary]))
            const childrenWithDoc = children.map((c: any) => ({ ...c, summary: docMap.get(c.id) || null }))

            return { doc, lineage, children: childrenWithDoc }
        }),

    search: t.procedure
        .input(z.object({
            q: z.string().min(1),
            lang: z.string().default('en'),
            limit: z.number().default(20)
        }))
        .query(({ input }) => {
            const stmt = db.prepare(`
        SELECT td.taxon_id, td.lang, td.summary, td.updated_at,
               n.name, n.slug, n.rank, n.parent_id as parentId
        FROM taxon_doc td
        JOIN nodes n ON td.taxon_id = n.id
        WHERE td.lang = ? AND (
          td.summary LIKE ? OR 
          td.description_md LIKE ?
        )
        ORDER BY td.updated_at DESC
        LIMIT ?
      `)
            const searchTerm = `%${input.q}%`
            return stmt.all(input.lang, searchTerm, searchTerm, input.limit)
        }),

    getSummaries: t.procedure
        .input(z.object({
            taxonIds: z.array(z.string()),
            lang: z.string().default('en')
        }))
        .query(({ input }) => {
            if (input.taxonIds.length === 0) return []

            const stmt = db.prepare(`
        SELECT taxon_id, summary, updated_at
        FROM taxon_doc 
        WHERE taxon_id IN (${inClause(input.taxonIds.length)}) AND lang = ?
      `)
            return stmt.all(...input.taxonIds, input.lang)
        }),

    /** Fast boolean doc presence for arbitrary ids (UI table badges) */
    hasDocs: t.procedure
        .input(z.object({
            taxonIds: z.array(z.string()).min(1),
            lang: z.string().default('en'),
        }))
        .query(({ input }) => {
            const sql = `
        SELECT taxon_id
        FROM taxon_doc
        WHERE lang = ? AND taxon_id IN (${inClause(input.taxonIds.length)})
      `
            const rows = db.prepare(sql).all(input.lang, ...input.taxonIds) as Array<{ taxon_id: string }>
            const present = new Set(rows.map(r => r.taxon_id))
            return input.taxonIds.map(id => ({ id, hasDoc: present.has(id) }))
        }),
})
