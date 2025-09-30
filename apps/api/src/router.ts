import { initTRPC, TRPCError } from '@trpc/server'
import { z } from 'zod'
import { db } from './db'
import { composeFoodState } from './lib/foodstate'

// Type definitions for database query results
interface Node {
  id: string
  name: string
  slug: string
  rank: string
  parentId: string | null
}

interface SearchResult {
  id: string
  score: number
  [key: string]: any
}

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
          JOIN taxa_fts ON taxa_fts.rowid = n.rowid
          WHERE taxa_fts MATCH ?
          ${filter}
          ORDER BY bm25(taxa_fts) ASC, n.name
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
        `).get(id) as Node | undefined

        if (!node) return null

        const parent = node.parentId ? db.prepare(`
          SELECT id,name,slug,rank,parent_id AS parentId
          FROM nodes WHERE id = ?
        `).get(node.parentId) as Node : null

        const children = db.prepare(`
          SELECT id,name,slug,rank,parent_id AS parentId
          FROM nodes WHERE parent_id = ?
          ORDER BY ${orderBy === 'rank' ? 'rank,name' : 'name'}
          LIMIT ?
        `).all(id, childLimit) as Node[]

        const childCount = (db.prepare(`
          SELECT COUNT(*) AS c FROM nodes WHERE parent_id = ?
        `).get(id) as { c: number }).c

        const siblings = node.parentId ? db.prepare(`
          SELECT id,name,slug,rank,parent_id AS parentId
          FROM nodes WHERE parent_id = ?
          ORDER BY name
          LIMIT 200
        `).all(node.parentId) as Node[] : []

        // optional: fast descendant count
        const descendants = (db.prepare(`
          WITH RECURSIVE d(id) AS (
            SELECT id FROM nodes WHERE parent_id = ?
            UNION ALL
            SELECT n.id FROM nodes n JOIN d ON n.parent_id = d.id
          ) SELECT COUNT(*) AS c FROM d
        `).get(id) as { c: number }).c

        return { node, parent, siblings, children, childCount, descendants }
      }),

    partTree: t.procedure
      .input(z.object({ id: z.string() }))
      .query(({ input }) => {
        // Only get parts that apply to this taxon (via lineage)
        const parts = db.prepare(`
          WITH RECURSIVE lineage(id) AS (
            SELECT id FROM nodes WHERE id = ?
            UNION ALL
            SELECT n.parent_id FROM nodes n JOIN lineage l ON n.id = l.id
            WHERE n.parent_id IS NOT NULL
          )
          SELECT DISTINCT p.id, p.name, p.kind, p.parent_id AS parentId
          FROM has_part hp
          JOIN part_def p ON p.id = hp.part_id
          WHERE hp.taxon_id IN (SELECT id FROM lineage)
          ORDER BY COALESCE(p.kind,''), p.name
        `).all(input.id)

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
          applicable: true, // All returned parts are applicable by definition
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
          WITH RECURSIVE lineage(id, depth) AS (
            SELECT id, 0 FROM nodes WHERE id = ?
            UNION ALL
            SELECT n.parent_id, l.depth + 1 FROM nodes n JOIN lineage l ON n.id = l.id
            WHERE n.parent_id IS NOT NULL
          ),
          transform_priority AS (
            SELECT ta.transform_id, MIN(l.depth) as min_depth
            FROM transform_applicability ta
            JOIN lineage l ON ta.taxon_id = l.id
            WHERE ta.part_id = ?
            GROUP BY ta.transform_id
          )
          SELECT DISTINCT td.id, td.name, td.identity, td.schema_json, td.ordering, td.notes
          FROM transform_applicability ta
          JOIN transform_def td ON td.id = ta.transform_id
          JOIN lineage l ON ta.taxon_id = l.id
          JOIN transform_priority tp ON ta.transform_id = tp.transform_id AND l.depth = tp.min_depth
          WHERE ta.part_id = ?
          ${input.identityOnly ? 'AND td.identity = 1' : ''}
          ORDER BY td.ordering ASC, td.name ASC
        `)
        try {
          const rows = stmt.all(input.taxonId, input.partId, input.partId) as any[]
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

    /** Distribution of child ranks for a given node (for compact histograms) */
    childrenRankCounts: t.procedure
      .input(z.object({ id: z.string() }))
      .query(({ input }) => {
        const stmt = db.prepare(`
          SELECT rank, COUNT(*) AS count
          FROM nodes
          WHERE parent_id = ?
          GROUP BY rank
          ORDER BY count DESC, rank ASC
        `)
        const rows = stmt.all(input.id) as Array<{ rank: string; count: number }>
        return rows
      }),

    getTaxonPart: t.procedure
      .input(z.object({ id: z.string() })) // "tp:tx:...:part:milk"
      .query(({ input }) => {
        const row = db.prepare(`
          SELECT 
            tp.id, tp.name, tp.display_name, tp.slug, tp.rank, tp.kind,
            tp.taxon_id, tp.part_id,
            n.name as taxon_name, n.rank as taxon_rank,
            p.name as part_name
          FROM taxon_part_nodes tp
          JOIN nodes n ON n.id = tp.taxon_id
          JOIN part_def p ON p.id = tp.part_id
          WHERE tp.id = ?
        `).get(input.id)
        if (!row) throw new TRPCError({ code: 'NOT_FOUND' })
        return row
      }),

  }),

  search: t.router({
    combined: t.procedure
      .input(
        z.object({
          q: z.string().min(1),
          limit: z.number().min(1).max(100).default(20),
          kinds: z.array(z.enum(['taxon', 'taxon_part'])).optional(),
          rankFilter: z.array(z.string()).optional()  // applies to taxa only
        })
      )
      .query(({ input }) => {
        const { limit, kinds, rankFilter } = input
        // AND-join tokens with wildcard for FTS prefix matches
        const q = input.q.split(/\s+/).map(t => t + '*').join(' AND ')

        const results: any[] = []

        const wantTaxa = !kinds || kinds.includes('taxon')
        const wantTP = !kinds || kinds.includes('taxon_part')

        if (wantTaxa) {
          const filter = rankFilter && rankFilter.length
            ? `AND n.rank IN (${rankFilter.map(() => '?').join(',')})` : ''
          const taxa = db.prepare(`
            SELECT n.id, n.name, n.slug, n.rank, n.parent_id as parentId,
                   bm25(taxa_fts) AS score, 'taxon' AS kind,
                   n.id AS taxonId, NULL AS partId
            FROM nodes n
            JOIN taxa_fts ON taxa_fts.rowid = n.rowid
            WHERE taxa_fts MATCH ?
            ${filter}
            ORDER BY bm25(taxa_fts) ASC, n.name
            LIMIT ?
          `).all(q, ...(rankFilter || []), limit) as any[]
          results.push(...taxa)
        }

        if (wantTP) {
          try {
            const tps = db.prepare(`
              SELECT tp.id, tp.name, tp.slug, tp.rank, tp.taxon_id as parentId,
                     bm25(tp_fts) AS score,
                     'taxon_part' AS kind,
                     tp.taxon_id AS taxonId,
                     tp.part_id  AS partId,
                     tp.kind     AS partKind
              FROM taxon_part_nodes tp
              JOIN tp_fts ON tp_fts.rowid = tp.rowid
              WHERE tp_fts MATCH ?
              ORDER BY bm25(tp_fts) ASC, tp.name
              LIMIT ?
            `).all(q, limit) as any[]
            results.push(...tps)
          } catch {
            // If this compiled DB predates TP, just skip TP results
          }
        }

        // De-dupe by id (names can legitimately collide)
        const seen = new Set<string>()
        const deduped = []
        for (const r of results.sort((a,b)=>a.score-b.score)) {
          if (seen.has(r.id)) continue
          seen.add(r.id)
          deduped.push(r)
          if (deduped.length >= limit) break
        }

        // Attach a client-ready nav object to each row
        return deduped.map((r: any) => {
          const nav =
            r.kind === 'taxon'
              ? { target: 'taxon', taxonId: r.taxonId }
              : r.kind === 'taxon_part'
              ? { target: 'taxon_part', taxonId: r.taxonId, partId: r.partId }
              : null
          return { ...r, nav }
        })
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

    /** Fast boolean doc presence for arbitrary ids (UI table badges) */
    hasDocs: t.procedure
      .input(z.object({
        taxonIds: z.array(z.string()).min(1),
        lang: z.string().default('en'),
      }))
      .query(({ input }) => {
        const placeholders = input.taxonIds.map(() => '?').join(',')
        const sql = `
          SELECT taxon_id
          FROM taxon_doc
          WHERE lang = ? AND taxon_id IN (${placeholders})
        `
        const rows = placeholders
          ? (db.prepare(sql).all(input.lang, ...input.taxonIds) as Array<{ taxon_id: string }>)
          : []
        const present = new Set(rows.map(r => r.taxon_id))
        return input.taxonIds.map(id => ({ id, hasDoc: present.has(id) }))
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

  /** Evidence endpoints (stubbed for now; returns safe, zeroed shape) */
  evidence: t.router({
    summaryByTaxon: t.procedure
      .input(z.object({ taxonId: z.string() }))
      .query(({ input }) => {
        // Placeholder structure for future integration.
        // Keep the shape stable so the UI can render badges/empty states today.
        return {
          taxonId: input.taxonId,
          hasDirect: false,
          directCount: 0,
          rollupCount: 0,
          lastUpdated: null as string | null,
        }
      }),
  }),
})

export type AppRouter = typeof appRouter
