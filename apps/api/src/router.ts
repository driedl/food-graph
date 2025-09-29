import { initTRPC, TRPCError } from '@trpc/server'
import { z } from 'zod'
import { db } from './db'
import { composeFoodState } from './lib/foodstate'

const t = initTRPC.create()

const nullToNotFound = t.middleware(async ({ next }) => {
  const res = await next()
  if (res.ok && res.data === null) {
    throw new TRPCError({ code: 'NOT_FOUND' })
  }
  return res
})

export const appRouter = t.router({
  health: t.procedure.query(() => ({ ok: true })),

  taxonomy: t.router({
    getRoot: t.procedure.query(() => {
      const root = db.prepare('SELECT id, name, slug, rank, parent_id as parentId FROM nodes WHERE parent_id IS NULL LIMIT 1').get()
      return root ?? null
    }),

    getChildren: t.procedure.input(z.object({ id: z.string() })).query(({ input }) => {
      const stmt = db.prepare('SELECT id, name, slug, rank, parent_id as parentId FROM nodes WHERE parent_id = ? ORDER BY name')
      return stmt.all(input.id)
    }),

    getNode: t.procedure.use(nullToNotFound).input(z.object({ id: z.string() })).query(({ input }) => {
      const stmt = db.prepare('SELECT id, name, slug, rank, parent_id as parentId FROM nodes WHERE id = ?')
      const node = stmt.get(input.id)
      return node ?? null
    }),

    pathToRoot: t.procedure.input(z.object({ id: z.string() })).query(({ input }) => {
      const stmt = db.prepare(`
        WITH RECURSIVE lineage(id,name,slug,rank,parent_id,depth) AS (
          SELECT id,name,slug,rank,parent_id,0 FROM nodes WHERE id = ?
          UNION ALL
          SELECT n.id,n.name,n.slug,n.rank,n.parent_id,depth+1 FROM nodes n
          JOIN lineage l ON n.id = l.parent_id
        )
        SELECT id,name,slug,rank,parent_id as parentId FROM lineage ORDER BY depth DESC;
      `)
      return stmt.all(input.id)
    }),

    search: t.procedure.input(z.object({ q: z.string().min(1) })).query(({ input }) => {
      // Use wildcards for partial matching - split query and add * to each term
      const q = input.q.split(/\s+/).map(term => term + '*').join(' AND ')
      const stmt = db.prepare(`
        SELECT n.id, n.name, n.slug, n.rank, n.parent_id as parentId 
        FROM nodes n 
        JOIN nodes_fts fts ON n.rowid = fts.rowid
        WHERE nodes_fts MATCH ?
        ORDER BY bm25(nodes_fts) ASC, n.name
        LIMIT 50
      `)
      return stmt.all(q)
    }),

    getPartsForTaxon: t.procedure
      .input(z.object({ id: z.string() }))
      .query(({ input }) => {
        const stmt = db.prepare(`
          WITH RECURSIVE lineage(id, parent_id) AS (
            SELECT id, parent_id FROM nodes WHERE id = ?
            UNION ALL
            SELECT n.id, n.parent_id FROM nodes n
            JOIN lineage l ON n.id = l.parent_id
          )
          SELECT DISTINCT p.id as id, p.name as name, p.kind as kind
          FROM has_part hp
          JOIN part_def p ON p.id = hp.part_id
          WHERE hp.taxon_id IN (SELECT id FROM lineage)
          ORDER BY p.kind, p.name
        `)
        try {
          return stmt.all(input.id)
        } catch {
          // If compiled DB is older and lacks tables, return empty gracefully
          return []
        }
      }),

    getTransformsFor: t.procedure
      .input(z.object({ taxonId: z.string(), partId: z.string() }))
      .query(({ input }) => {
        const stmt = db.prepare(`
          WITH RECURSIVE lineage(id, parent_id) AS (
            SELECT id, parent_id FROM nodes WHERE id = ?
            UNION ALL
            SELECT n.id, n.parent_id FROM nodes n
            JOIN lineage l ON n.id = l.parent_id
          )
          SELECT DISTINCT td.id, td.name, td.identity, td.schema_json
          FROM transform_applicability ta
          JOIN transform_def td ON td.id = ta.transform_id
          WHERE ta.part_id = ? AND ta.taxon_id IN (SELECT id FROM lineage)
          ORDER BY td.name
        `)
        try {
          const rows = stmt.all(input.taxonId, input.partId) as any[]
          return rows.map(r => ({
            id: r.id,
            name: r.name,
            identity: !!r.identity,
            schema: r.schema_json ? JSON.parse(r.schema_json) : null
          }))
        } catch {
          return []
        }
      }),
  }),

  docs: t.router({
    getByTaxon: t.procedure
      .input(z.object({ 
        taxonId: z.string(),
        lang: z.string().default('en')
      }))
      .query(({ input }) => {
        const stmt = db.prepare(`
          SELECT taxon_id, lang, summary, description_md, updated_at, 
                 rank, latin_name, display_name, tags
          FROM taxon_doc 
          WHERE taxon_id = ? AND lang = ?
        `)
        return stmt.get(input.taxonId, input.lang) ?? null
      }),

    search: t.procedure
      .input(z.object({ 
        q: z.string().min(1),
        lang: z.string().default('en'),
        limit: z.number().default(20)
      }))
      .query(({ input }) => {
        const q = input.q.split(/\s+/).map(term => term + '*').join(' AND ')
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
        
        const placeholders = input.taxonIds.map(() => '?').join(',')
        const stmt = db.prepare(`
          SELECT taxon_id, summary, updated_at
          FROM taxon_doc 
          WHERE taxon_id IN (${placeholders}) AND lang = ?
        `)
        return stmt.all(...input.taxonIds, input.lang)
      }),
  }),

  foodstate: t.router({
    compose: t.procedure
      .input(z.object({
        taxonId: z.string(),
        partId: z.string(),
        transforms: z.array(z.object({
          id: z.string(),
          params: z.record(z.any()).optional()
        })).default([])
      }))
      .query(({ input }) => {
        const res = composeFoodState(db as any, input)
        return res
      }),
  }),
})

export type AppRouter = typeof appRouter
