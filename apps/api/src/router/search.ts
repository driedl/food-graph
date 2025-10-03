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

            // Cuisines filter (requires JOIN with tpt_cuisines)
            let cuisineJoin = ''
            if (needCuisines) {
                cuisineJoin = 'LEFT JOIN tpt_cuisines tc ON sc.ref_id = tc.tpt_id'
                whereConditions.push(`tc.cuisine IN (${inClause(input.cuisines!.length)})`)
                params.push(...input.cuisines!)
            }

            // Flags filter (requires JOIN with tpt_flags)
            let flagsJoin = ''
            if (needFlags) {
                flagsJoin = 'LEFT JOIN tpt_flags tf ON sc.ref_id = tf.tpt_id'
                whereConditions.push(`tf.flag IN (${inClause(input.flags!.length)})`)
                params.push(...input.flags!)
            }

            const whereClause = whereConditions.join(' AND ')

            const base = `
        FROM search_fts
        JOIN search_content sc ON sc.rowid = search_fts.rowid
        ${cuisineJoin}
        ${flagsJoin}
        WHERE ${whereClause}
      `

            const data = db.prepare(`
        SELECT sc.ref_type, sc.ref_id, sc.taxon_id, sc.part_id, sc.family,
               sc.entity_rank, sc.name, sc.synonyms, sc.display_name, sc.slug,
               bm25(search_fts) AS score
        ${base}
        ORDER BY score ASC, sc.name ASC
        LIMIT ? OFFSET ?
      `).all(...params, input.limit, input.offset) as any[]

            // Get actual total count (not just page length)
            const total = db.prepare(`SELECT COUNT(1) AS c ${base}`).get(...params) as { c: number }

            // Get facets for the same query (without LIMIT/OFFSET)
            let facetRows: any[] = []
            try {
                const facetStmt = db.prepare(`
          SELECT 
            sc.family,
            ${cuisineJoin ? 'tc.cuisine' : 'NULL as cuisine'},
            ${flagsJoin ? 'tf.flag' : 'NULL as flag'},
            COUNT(*) as count
          ${base}
          GROUP BY sc.family, ${cuisineJoin ? 'tc.cuisine' : 'NULL'}, ${flagsJoin ? 'tf.flag' : 'NULL'}
        `)
                facetRows = facetStmt.all(...params) as any[]
            } catch (error) {
                // If tables don't exist, just get family facets
                try {
                    const simpleFacetStmt = db.prepare(`
            SELECT 
              sc.family,
              COUNT(*) as count
            ${base}
            GROUP BY sc.family
          `)
                    facetRows = simpleFacetStmt.all(...params) as any[]
                } catch {
                    // If even that fails, return empty facets
                    facetRows = []
                }
            }

            // Process facets
            const families = new Map<string, number>()
            const cuisines = new Map<string, number>()
            const flags = new Map<string, number>()

            facetRows.forEach(row => {
                if (row.family) families.set(row.family, (families.get(row.family) || 0) + row.count)
                if (row.cuisine) cuisines.set(row.cuisine, (cuisines.get(row.cuisine) || 0) + row.count)
                if (row.flag) flags.set(row.flag, (flags.get(row.flag) || 0) + row.count)
            })

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
                    families: Array.from(families.entries()).map(([id, count]) => ({ id, count })),
                    cuisines: Array.from(cuisines.entries()).map(([id, count]) => ({ id, count })),
                    flags: Array.from(flags.entries()).map(([id, count]) => ({ id, count }))
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
