import { z } from 'zod'
import { TRPCError } from '@trpc/server'
import { db } from '../db'
import { t, nullToNotFound } from './_t'
import { safeParseJSON, uniq } from './_util'

// Type definitions for database query results
interface Node {
    id: string
    name: string
    slug: string
    rank: string
    parentId: string | null
}

export const taxonomyRouter = t.router({
    getRoot: t.procedure.query(() => {
        const root = db.prepare('SELECT id, name, slug, rank, parent_id as parentId FROM nodes WHERE parent_id IS NULL LIMIT 1').get()
        return root ?? null
    }),

    getChildren: t.procedure
        .input(z.object({
            id: z.string(),
            orderBy: z.enum(['name', 'rank']).default('name'),
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
            orderBy: z.enum(['name', 'rank']).default('name')
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
        SELECT DISTINCT p.id, p.name, p.kind, p.parent_id AS parentId, p.category,
               c.name as category_name, c.description as category_description, c.kind as category_kind
        FROM has_part hp
        JOIN part_def p ON p.id = hp.part_id
        LEFT JOIN categories c ON p.category = c.id
        WHERE hp.taxon_id IN (SELECT id FROM lineage)
        ORDER BY COALESCE(p.kind,''), p.name
      `).all(input.id)

            // Transform availability per part (counts from TPT data)
            const txCounts = db.prepare(`
        WITH RECURSIVE lineage(id) AS (
          SELECT id FROM nodes WHERE id = ?
          UNION ALL
          SELECT n.parent_id FROM nodes n JOIN lineage l ON n.id = l.id
          WHERE n.parent_id IS NOT NULL
        )
        SELECT 
          tpt.part_id AS partId,
          SUM(CASE WHEN json_extract(step.value, '$.identity') = 1 THEN 1 ELSE 0 END) AS identityCount,
          SUM(CASE WHEN json_extract(step.value, '$.identity') = 0 THEN 1 ELSE 0 END) AS nonIdentityCount
        FROM tpt_nodes tpt,
        json_each(tpt.path_json) as step
        WHERE tpt.taxon_id IN (SELECT id FROM lineage)
        GROUP BY tpt.part_id
      `).all(input.id)

            const countsMap = new Map(txCounts.map((r: any) => [r.partId, r]))

            // Part synonyms (optional legacy table; tolerate absence)
            let syn: Array<{ partId: string; synonym: string }> = []
            try {
                syn = db.prepare(`SELECT part_id AS partId, synonym FROM part_synonym`).all() as any
            } catch {
                syn = []
            }

            const synMap = new Map<string, string[]>()
            for (const s of syn) {
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
                synonyms: synMap.get(p.id) ?? [],
                category: p.category ? {
                    id: p.category,
                    name: p.category_name,
                    description: p.category_description,
                    kind: p.category_kind
                } : null
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
        SELECT DISTINCT 
          td.id,
          td.name,
          td.identity,
          td.param_keys as schema_json,
          td."order" as ordering,
          td.notes,
          MIN(a.depth) AS min_depth
        FROM tpt_identity_steps s
        JOIN taxon_ancestors a ON s.taxon_id = a.ancestor_id
        JOIN transform_def td ON td.id = s.tf_id
        WHERE a.descendant_id = ? AND s.part_id = ?
        ${input.identityOnly ? 'AND td.identity = 1' : ''}
        GROUP BY td.id, td.name, td.identity, td.param_keys, td."order", td.notes
        ORDER BY min_depth ASC, td."order" ASC, td.name ASC
      `)
            const rows = stmt.all(input.taxonId, input.partId) as any[]
            return rows.map(r => {
                const fam = r.id?.split(':').slice(0, 2).join(':') || 'unknown' // e.g. "tf:ferment"
                return {
                    id: r.id || 'unknown',
                    name: r.name || r.id || 'Unknown Transform',
                    identity: !!r.identity,
                    ordering: r.ordering ?? 999,
                    notes: r.notes || null,
                    family: fam,
                    schema: r.schema_json ? JSON.parse(r.schema_json) : null,
                }
            })
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
          tp.id, tp.name, tp.display_name, tp.slug, tp.rank,
          tp.taxon_id, tp.part_id,
          n.name as taxon_name, n.rank as taxon_rank,
          p.name as part_name, p.kind as part_kind
        FROM taxon_part_nodes tp
        JOIN nodes n ON n.id = tp.taxon_id
        JOIN part_def p ON p.id = tp.part_id
        WHERE tp.id = ?
      `).get(input.id)
            if (!row) throw new TRPCError({ code: 'NOT_FOUND' })
            return row
        }),
})
