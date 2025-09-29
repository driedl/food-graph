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

    getChildren: t.procedure
      .input(z.object({ 
        id: z.string(),
        orderBy: z.enum(['name','rank']).default('name'),
        offset: z.number().default(0),
        limit: z.number().default(50)
      }))
      .query(({ input }) => {
        const stmt = db.prepare(`
          SELECT id, name, slug, rank, parent_id as parentId 
          FROM nodes 
          WHERE parent_id = ? 
          ORDER BY ${input.orderBy === 'rank' ? 'rank,name' : 'name'}
          LIMIT ? OFFSET ?
        `)
        return stmt.all(input.id, input.limit, input.offset)
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

    search: t.procedure
      .input(z.object({ 
        q: z.string().min(1),
        rankFilter: z.array(z.string()).optional()
      }))
      .query(({ input }) => {
        // Use wildcards for partial matching - split query and add * to each term
        const q = input.q.split(/\s+/).map(term => term + '*').join(' AND ')
        const filter = input.rankFilter && input.rankFilter.length
          ? `AND n.rank IN (${input.rankFilter.map(() => '?').join(',')})` : ''
        const stmt = db.prepare(`
          SELECT n.id, n.name, n.slug, n.rank, n.parent_id as parentId 
          FROM nodes n 
          JOIN nodes_fts fts ON n.name = fts.name AND n.rank = fts.taxon_rank
          WHERE nodes_fts MATCH ?
          ${filter}
          ORDER BY bm25(nodes_fts) ASC, n.name
          LIMIT 50
        `)
        return stmt.all(q, ...(input.rankFilter || []))
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
          SELECT DISTINCT p.id as id, p.name as name, p.kind as kind, p.parent_id as parentId
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

    neighborhood: t.procedure
      .input(z.object({
        id: z.string(),
        childLimit: z.number().min(1).max(200).default(50),
        orderBy: z.enum(['name','rank']).default('name')
      }))
      .query(({ input }) => {
        const { id, childLimit, orderBy } = input
        const node = db.prepare(`
          SELECT id,name,slug,rank,parent_id AS parentId
          FROM nodes WHERE id = ?
        `).get(id)

        if (!node) return null

        const parent = node.parentId ? db.prepare(`
          SELECT id,name,slug,rank,parent_id AS parentId
          FROM nodes WHERE id = ?
        `).get(node.parentId) : null

        const children = db.prepare(`
          SELECT id,name,slug,rank,parent_id AS parentId
          FROM nodes WHERE parent_id = ?
          ORDER BY ${orderBy === 'rank' ? 'rank,name' : 'name'}
          LIMIT ?
        `).all(id, childLimit)

        const childCount = db.prepare(`
          SELECT COUNT(*) AS c FROM nodes WHERE parent_id = ?
        `).get(id).c as number

        const siblings = node.parentId ? db.prepare(`
          SELECT id,name,slug,rank,parent_id AS parentId
          FROM nodes WHERE parent_id = ?
          ORDER BY name
          LIMIT 200
        `).all(node.parentId) : []

        // optional: fast descendant count
        const descendants = db.prepare(`
          WITH RECURSIVE d(id) AS (
            SELECT id FROM nodes WHERE parent_id = ?
            UNION ALL
            SELECT n.id FROM nodes n JOIN d ON n.parent_id = d.id
          ) SELECT COUNT(*) AS c FROM d
        `).get(id).c as number

        return { node, parent, siblings, children, childCount, descendants }
      }),

    partTree: t.procedure
      .input(z.object({ id: z.string() }))
      .query(({ input }) => {
        // All parts (tree structure)
        const parts = db.prepare(`
          SELECT p.id, p.name, p.kind, p.parent_id AS parentId
          FROM part_def p
          ORDER BY COALESCE(p.kind,''), p.name
        `).all()

        // Which parts apply to this taxon (via lineage)
        const applicable = db.prepare(`
          WITH RECURSIVE lineage(id) AS (
            SELECT id FROM nodes WHERE id = ?
            UNION ALL
            SELECT n.parent_id FROM nodes n JOIN lineage l ON n.id = l.id
            WHERE n.parent_id IS NOT NULL
          )
          SELECT DISTINCT part_id FROM has_part
          WHERE taxon_id IN (SELECT id FROM lineage)
        `).all(input.id).map((r: any) => r.part_id)

        // Transform availability per part (counts of identity/non-identity)
        const txCounts = db.prepare(`
          WITH RECURSIVE lineage(id) AS (
            SELECT id FROM nodes WHERE id = ?
            UNION ALL
            SELECT n.parent_id FROM nodes n JOIN lineage l ON n.id = l.id
            WHERE n.parent_id IS NOT NULL
          )
          SELECT ta.part_id AS partId,
                 SUM(CASE WHEN td.identity=1 THEN 1 ELSE 0 END) AS identityCount,
                 SUM(CASE WHEN td.identity=0 THEN 1 ELSE 0 END) AS nonIdentityCount
          FROM transform_applicability ta
          JOIN transform_def td ON td.id = ta.transform_id
          WHERE ta.taxon_id IN (SELECT id FROM lineage)
          GROUP BY ta.part_id
        `).all(input.id)

        const countsMap = new Map(txCounts.map((r: any) => [r.partId, r]))
        const applicableSet = new Set(applicable)

        // Part synonyms
        const syn = db.prepare(`
          SELECT part_id AS partId, synonym FROM part_synonym
        `).all()

        const synMap = new Map<string, string[]>()
        for (const s of syn as any[]) {
          const list = synMap.get(s.partId) || []
          list.push(s.synonym)
          synMap.set(s.partId, list)
        }

        // Build simple tree (flat array is fine; UI can group by parentId)
        return parts.map((p: any) => ({
          ...p,
          applicable: applicableSet.has(p.id),
          identityCount: countsMap.get(p.id)?.identityCount ?? 0,
          nonIdentityCount: countsMap.get(p.id)?.nonIdentityCount ?? 0,
          synonyms: synMap.get(p.id) ?? []
        }))
      }),

    getTransformsFor: t.procedure
      .input(z.object({ 
        taxonId: z.string(), 
        partId: z.string(),
        identityOnly: z.boolean().default(false)
      }))
      .query(({ input }) => {
        const stmt = db.prepare(`
          WITH RECURSIVE lineage(id) AS (
            SELECT id FROM nodes WHERE id = ?
            UNION ALL
            SELECT n.parent_id FROM nodes n JOIN lineage l ON n.id = l.id
          )
          SELECT td.id, td.name, td.identity, td.schema_json, td.ordering, td.notes
          FROM transform_applicability ta
          JOIN transform_def td ON td.id = ta.transform_id
          WHERE ta.part_id = ? AND ta.taxon_id IN (SELECT id FROM lineage)
          ${input.identityOnly ? 'AND td.identity = 1' : ''}
          ORDER BY td.ordering ASC, td.name ASC
        `)
        try {
          const rows = stmt.all(input.taxonId, input.partId) as any[]
          return rows.map(r => {
            const fam = r.id.split(':').slice(0, 2).join(':') // e.g. "tf:ferment"
            return {
              id: r.id,
              name: r.name,
              identity: !!r.identity,
              ordering: r.ordering ?? 999,
              notes: r.notes || null,
              family: fam,
              schema: r.schema_json ? JSON.parse(r.schema_json) : null,
            }
          })
        } catch {
          return []
        }
      }),
  }),

  search: t.router({
    unified: t.procedure
      .input(z.object({
        q: z.string().min(1),
        limit: z.number().min(1).max(100).default(25),
        rankFilter: z.array(z.string()).optional() // e.g. ['species','product']
      }))
      .query(({ input }) => {
        const q = input.q.trim()
        const filter = input.rankFilter && input.rankFilter.length
          ? `AND n.rank IN (${input.rankFilter.map(() => '?').join(',')})` : ''
        const params: any[] = []
        const nodeQ = q.split(/\s+/).map(t => t + '*').join(' AND ')
        const docQ = q // FTS5 default syntax is fine here

        // Nodes FTS
        const nodes = db.prepare(`
          SELECT n.id, n.name, n.slug, n.rank,
                 bm25(nodes_fts, 1.0, 0.5, 0.2, 0.1) AS score, 'taxon' AS kind
          FROM nodes n
          JOIN nodes_fts fts ON n.rowid = fts.rowid
          WHERE nodes_fts MATCH ?
          ${filter}
          ORDER BY score ASC, n.name
          LIMIT ?
        `).all(nodeQ, ...(input.rankFilter || []), input.limit)

        // Docs FTS → mapped to taxon
        const docs = db.prepare(`
          SELECT n.id, n.name, n.slug, n.rank,
                 bm25(taxon_doc_fts, 1.0, 1.0) AS score, 'doc' AS kind
          FROM taxon_doc_fts d
          JOIN nodes n ON n.id = d.taxon_id
          WHERE taxon_doc_fts MATCH ?
          ${filter}
          ORDER BY score ASC, n.name
          LIMIT ?
        `).all(docQ, ...(input.rankFilter || []), input.limit)

        // Merge & re-rank (simple: take best unique per id)
        const byId = new Map<string, any>()
        for (const r of [...nodes, ...docs]) {
          const prev = byId.get(r.id)
          if (!prev || r.score < prev.score) byId.set(r.id, r)
        }
        return Array.from(byId.values())
          .sort((a, b) => a.score - b.score)
          .slice(0, input.limit)
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

    overview: t.procedure
      .input(z.object({ taxonId: z.string(), childLimit: z.number().default(25) }))
      .query(({ input }) => {
        const doc = db.prepare(`
          SELECT taxon_id, summary, description_md, updated_at, rank, latin_name, display_name, tags
          FROM taxon_doc WHERE taxon_id = ? AND lang = 'en'
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

        const childDocSummaries = db.prepare(`
          SELECT taxon_id, summary FROM taxon_doc
          WHERE taxon_id IN (${children.map(() => '?').join(',')}) AND lang='en'
        `).all(...children.map((c: any) => c.id))

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

    parse: t.procedure
      .input(z.object({ fs: z.string().min(1) }))
      .query(({ input }) => {
        // naive parser: fs:/a/b/c/part:.../tf:x{a=1}/tf:y
        const segs = input.fs.replace(/^fs:\/*/, '').split('/').filter(Boolean)
        const partIdx = segs.findIndex(s => s.startsWith('part:'))
        const taxonPath = partIdx >= 0 ? segs.slice(0, partIdx) : segs
        const part = partIdx >= 0 ? segs[partIdx] : null
        const txSegs = partIdx >= 0 ? segs.slice(partIdx + 1) : []

        const parseTx = (s: string) => {
          const m = s.match(/^([^{}]+)(?:\{(.+)\})?$/)
          if (!m) return { id: s, params: {} }
          const id = m[1]; const params: any = {}
          if (m[2]) {
            for (const kv of m[2].split(',')) {
              const [k, raw] = kv.split('=')
              if (!k) continue
              if (raw === 'true' || raw === 'false') params[k] = raw === 'true'
              else if (!Number.isNaN(Number(raw))) params[k] = Number(raw)
              else params[k] = raw
            }
          }
          return { id, params }
        }

        return {
          taxonPath,
          partId: part,
          transforms: txSegs.map(parseTx),
        }
      }),
  }),
})

export type AppRouter = typeof appRouter
