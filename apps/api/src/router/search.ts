import { z } from 'zod'
import { db } from '../db'
import { t } from './_t'
import { makeFtsQuery, inClause } from './_util'
import { hasTable } from './_guards'

export const searchRouter = t.router({
    query: t.procedure
        .input(z.object({
            q: z.string().min(1),
            type: z.enum(['any', 'taxon', 'tp', 'tpt']).default('any'),
            limit: z.number().min(1).max(100).default(20),
            offset: z.number().min(0).default(0),
            taxonPrefix: z.string().optional(),
            taxonId: z.string().optional(),
            partId: z.string().optional(),
            family: z.string().optional(),
            families: z.array(z.string()).optional(),
            cuisines: z.array(z.string()).optional(),
            flags: z.array(z.string()).optional()
        }))
        .query(({ input }) => {
            const qfts = makeFtsQuery(input.q)

            // Guard optional tables before building main query
            const needCuisines = !!(input.cuisines?.length)
            const needFlags = !!(input.flags?.length)

            if ((needCuisines && !hasTable('tpt_cuisines')) ||
                (needFlags && !hasTable('tpt_flags'))) {
                return {
                    results: [],
                    facets: { families: [], cuisines: [], flags: [] },
                    total: 0,
                    limit: input.limit,
                    offset: input.offset
                }
            }

            // Build WHERE conditions
            const whereConditions = ['search_fts MATCH ?']
            const params: any[] = [qfts]

            // Type filter
            if (input.type !== 'any') {
                whereConditions.push('sc.ref_type = ?')
                params.push(input.type)
            }

            // Taxon prefix filter
            if (input.taxonPrefix) {
                whereConditions.push('sc.taxon_id LIKE ?')
                params.push(`${input.taxonPrefix}%`)
            }

            // Exact taxon filter
            if (input.taxonId) {
                whereConditions.push('sc.taxon_id = ?')
                params.push(input.taxonId)
            }

            // Part filter
            if (input.partId) {
                whereConditions.push('sc.part_id = ?')
                params.push(input.partId)
            }

            // Family filter (single)
            if (input.family) {
                whereConditions.push('sc.family = ?')
                params.push(input.family)
            }

            // Multiple families filter
            if (input.families && input.families.length > 0) {
                whereConditions.push(`sc.family IN (${inClause(input.families.length)})`)
                params.push(...input.families)
            }

            // Cuisines/Flags filters: use EXISTS to avoid fan-out/duplication
            if (needCuisines) {
                whereConditions.push(`EXISTS (
                  SELECT 1 FROM tpt_cuisines tc
                  WHERE tc.tpt_id = sc.ref_id
                    AND tc.cuisine IN (${inClause(input.cuisines!.length)})
                )`)
                params.push(...input.cuisines!)
            }
            if (needFlags) {
                whereConditions.push(`EXISTS (
                  SELECT 1 FROM tpt_flags tf
                  WHERE tf.tpt_id = sc.ref_id
                    AND tf.flag IN (${inClause(input.flags!.length)})
                )`)
                params.push(...input.flags!)
            }

            const whereClause = whereConditions.join(' AND ')

            // Dedup by ref_id using ROW_NUMBER() over the scored FTS rows
            const cte = `
        WITH scored AS (
          SELECT
            sc.ref_type, sc.ref_id, sc.taxon_id, sc.part_id, sc.family,
            sc.entity_rank, sc.name, sc.synonyms, sc.display_name, sc.slug,
            bm25(search_fts) AS score
          FROM search_fts
          JOIN search_content sc ON sc.rowid = search_fts.rowid
          WHERE ${whereClause}
        ),
        ranked AS (
          SELECT *,
                 ROW_NUMBER() OVER (
                   PARTITION BY ref_id
                   ORDER BY score ASC, name ASC
                 ) AS rn
          FROM scored
        )
      `

            const data = db.prepare(`
        ${cte}
        SELECT ref_type, ref_id, taxon_id, part_id, family,
               entity_rank, name, synonyms, display_name, slug,
               score
        FROM ranked
        WHERE rn = 1
        ORDER BY score ASC, name ASC
        LIMIT ? OFFSET ?
      `).all(...params, input.limit, input.offset) as any[]

            // Get actual total count (not just page length)
            const total = db.prepare(`
        ${cte}
        SELECT COUNT(1) AS c
        FROM ranked
        WHERE rn = 1
      `).get(...params) as { c: number }

            // Facets over the same de-duplicated rowset (rn = 1)
            const familiesFacet = db.prepare(`
        ${cte}
        SELECT family, COUNT(*) AS count
        FROM ranked
        WHERE rn = 1 AND family IS NOT NULL
        GROUP BY family
      `).all(...params) as Array<{ family: string; count: number }>

            const cuisinesFacet = hasTable('tpt_cuisines') ? (db.prepare(`
        ${cte}
        SELECT tc.cuisine AS id, COUNT(*) AS count
        FROM ranked r
        JOIN tpt_cuisines tc ON tc.tpt_id = r.ref_id
        WHERE r.rn = 1
        GROUP BY tc.cuisine
      `).all(...params) as Array<{ id: string; count: number }>) : []

            const flagsFacet = hasTable('tpt_flags') ? (db.prepare(`
        ${cte}
        SELECT tf.flag AS id, COUNT(*) AS count
        FROM ranked r
        JOIN tpt_flags tf ON tf.tpt_id = r.ref_id
        WHERE r.rn = 1
        GROUP BY tf.flag
      `).all(...params) as Array<{ id: string; count: number }>) : []

            return {
                results: data.map(r => ({
                    kind: r.ref_type as 'taxon' | 'tp' | 'tpt',
                    id: r.ref_id as string,
                    score: r.score as number,
                    name: r.name as string,
                    displayName: r.display_name ?? null,
                    slug: r.slug ?? null,
                    taxonId: r.taxon_id ?? null,
                    partId: r.part_id ?? null,
                    family: r.family ?? null
                })),
                facets: {
                    families: familiesFacet.map(r => ({ id: r.family, count: r.count })),
                    cuisines: cuisinesFacet.map(r => ({ id: r.id, count: r.count })),
                    flags: flagsFacet.map(r => ({ id: r.id, count: r.count })),
                },
                total: total.c,
                limit: input.limit,
                offset: input.offset
            }
        }),

    suggest: t.procedure
        .input(z.object({
            q: z.string().min(1),
            type: z.enum(['any', 'taxon', 'tp', 'tpt']).default('any'),
            limit: z.number().min(1).max(20).default(8),
            taxonPrefix: z.string().optional()
        }))
        .query(({ input }) => {
            const qfts = makeFtsQuery(input.q)
            const stmt = db.prepare(`
        SELECT sc.ref_type, sc.ref_id, sc.name, sc.display_name, sc.entity_rank, sc.family,
               bm25(search_fts) AS score
        FROM search_fts
        JOIN search_content sc ON sc.rowid = search_fts.rowid
        WHERE search_fts MATCH ?
          AND (? = 'any' OR sc.ref_type = ?)
          AND (? IS NULL OR sc.taxon_id LIKE (? || '%'))
        ORDER BY score ASC, sc.name ASC
          LIMIT ?
      `)
            const rows = stmt.all(
                qfts,
                input.type, input.type,
                input.taxonPrefix ?? null, input.taxonPrefix ?? null,
                input.limit
            ) as any[]
            return rows.map(r => ({
                kind: r.ref_type as 'taxon' | 'tp' | 'tpt',
                id: r.ref_id as string,
                label: (r.display_name ?? r.name) as string,
                sub: r.ref_type === 'tpt' ? r.family : r.entity_rank
            }))
        }),
})
