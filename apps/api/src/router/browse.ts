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
    getFamilies: t.procedure
        .input(z.object({
            q: z.string().optional(),
            limit: z.number().min(1).max(200).default(50),
            offset: z.number().min(0).default(0)
        }))
        .query(({ input }) => {
            try {
                const { q, limit, offset } = input

                // First get all families from tpt_nodes (actual data)
                let whereClause = "WHERE tpt.family IS NOT NULL"
                let params: any[] = []

                if (q && q.trim()) {
                    whereClause += " AND tpt.family LIKE ?"
                    params.push(`%${q}%`)
                }

                const stmt = db.prepare(`
                    SELECT 
                        tpt.family as id,
                        tpt.family as label,
                        COUNT(tpt.id) as count
                    FROM tpt_nodes tpt
                    ${whereClause}
                    GROUP BY tpt.family
                    ORDER BY count DESC, tpt.family ASC
                    LIMIT ? OFFSET ?
                `)

                const rows = stmt.all(...params, limit, offset) as any[]

                // Get total count for pagination
                const countStmt = db.prepare(`
                    SELECT COUNT(DISTINCT tpt.family) as total
                    FROM tpt_nodes tpt
                    ${whereClause}
                `)
                const total = (countStmt.get(...params) as any)?.total || 0

                return { rows, total }
            } catch (error) {
                console.error('Error in getFamilies:', error)
                return { rows: [], total: 0 }
            }
        }),

    // New: Get all cuisines with counts
    getCuisines: t.procedure
        .input(z.object({
            q: z.string().optional(),
            limit: z.number().min(1).max(200).default(50),
            offset: z.number().min(0).default(0)
        }))
        .query(({ input }) => {
            try {
                const { q, limit, offset } = input
                let whereClause = ""
                let params: any[] = []

                if (q && q.trim()) {
                    whereClause = "WHERE cuisine LIKE ?"
                    params.push(`%${q}%`)
                }

                const stmt = db.prepare(`
                    SELECT 
                        cuisine as id,
                        cuisine as label,
                        COUNT(*) as count
                    FROM tpt_cuisines
                    ${whereClause}
                    GROUP BY cuisine
                    ORDER BY count DESC, cuisine ASC
                    LIMIT ? OFFSET ?
                `)
                const rows = stmt.all(...params, limit, offset) as any[]

                // Get total count for pagination
                const countStmt = db.prepare(`
                    SELECT COUNT(DISTINCT cuisine) as total
                    FROM tpt_cuisines
                    ${whereClause}
                `)
                const total = (countStmt.get(...params) as any)?.total || 0

                return { rows, total }
            } catch (error) {
                console.error('Error in getCuisines:', error)
                return { rows: [], total: 0 }
            }
        }),

    // New: Get TPTs for a specific family
    getFamilyEntities: t.procedure
        .input(z.object({
            family: z.string().optional(),
            limit: z.number().min(1).max(200).default(50),
            offset: z.number().min(0).default(0)
        }))
        .query(({ input }) => {
            try {
                let whereClause = ""
                let params: any[] = []

                if (input.family) {
                    whereClause = "WHERE tpt.family = ?"
                    params = [input.family]
                }

                const stmt = db.prepare(`
                    SELECT 
                        tpt.id, tpt.name, tpt.family, tpt.synonyms,
                        n.name as taxon_name, p.name as part_name
                    FROM tpt_nodes tpt
                    JOIN nodes n ON n.id = tpt.taxon_id
                    JOIN part_def p ON p.id = tpt.part_id
                    ${whereClause}
                    ORDER BY tpt.name ASC
                    LIMIT ? OFFSET ?
                `)
                const rows = stmt.all(...params, input.limit, input.offset) as any[]

                // Get total count for pagination
                const countStmt = db.prepare(`
                    SELECT COUNT(*) as total
                    FROM tpt_nodes tpt
                    ${whereClause}
                `)
                const total = (countStmt.get(...params) as any)?.total || 0

                return { rows, total }
            } catch (error) {
                console.error('Error in getFamilyEntities:', error)
                return { rows: [], total: 0 }
            }
        }),

    // New: Get TPTs for a specific cuisine
    getCuisineEntities: t.procedure
        .input(z.object({
            cuisine: z.string().optional(),
            limit: z.number().min(1).max(200).default(50),
            offset: z.number().min(0).default(0)
        }))
        .query(({ input }) => {
            try {
                let whereClause = ""
                let params: any[] = []

                if (input.cuisine) {
                    whereClause = "WHERE tc.cuisine = ?"
                    params = [input.cuisine]
                }

                const stmt = db.prepare(`
                    SELECT 
                        tpt.id, tpt.name, tpt.family, tpt.synonyms,
                        n.name as taxon_name, p.name as part_name,
                        tc.cuisine
                    FROM tpt_cuisines tc
                    JOIN tpt_nodes tpt ON tpt.id = tc.tpt_id
                    JOIN nodes n ON n.id = tpt.taxon_id
                    JOIN part_def p ON p.id = tpt.part_id
                    ${whereClause}
                    ORDER BY tpt.name ASC
                    LIMIT ? OFFSET ?
                `)
                const rows = stmt.all(...params, input.limit, input.offset) as any[]

                // Get total count for pagination
                const countStmt = db.prepare(`
                    SELECT COUNT(*) as total
                    FROM tpt_cuisines tc
                    JOIN tpt_nodes tpt ON tpt.id = tc.tpt_id
                    ${whereClause}
                `)
                const total = (countStmt.get(...params) as any)?.total || 0

                return { rows, total }
            } catch (error) {
                console.error('Error in getCuisineEntities:', error)
                return { rows: [], total: 0 }
            }
        }),

    // New: Get all flags grouped by type
    getFlags: t.procedure
        .input(z.object({
            q: z.string().optional()
        }))
        .query(({ input }) => {
            try {
                const { q } = input
                let whereClause = ""
                let params: any[] = []

                if (q && q.trim()) {
                    whereClause = "WHERE tf.flag LIKE ?"
                    params.push(`%${q}%`)
                }

                const stmt = db.prepare(`
                    SELECT 
                        tf.flag,
                        tf.flag_type as type,
                        COUNT(*) as count
                    FROM tpt_flags tf
                    ${whereClause}
                    GROUP BY tf.flag, tf.flag_type
                    ORDER BY tf.flag_type ASC, count DESC, tf.flag ASC
                `)
                const rows = stmt.all(...params) as any[]

                // Group by type
                const groups: Array<{ type: string; items: Array<{ flag: string; count: number }> }> = []
                const typeMap = new Map<string, Array<{ flag: string; count: number }>>()

                rows.forEach(row => {
                    if (!typeMap.has(row.type)) {
                        typeMap.set(row.type, [])
                    }
                    typeMap.get(row.type)!.push({
                        flag: row.flag,
                        count: row.count
                    })
                })

                typeMap.forEach((items, type) => {
                    groups.push({ type, items })
                })

                return groups
            } catch (error) {
                console.error('Error in getFlags:', error)
                return []
            }
        }),

    // New: Get TPTs for a specific flag
    getFlagEntities: t.procedure
        .input(z.object({
            flag: z.string().optional(),
            type: z.string().optional(),
            limit: z.number().min(1).max(200).default(50),
            offset: z.number().min(0).default(0)
        }))
        .query(({ input }) => {
            try {
                let whereClause = "WHERE tf.flag = ?"
                let params: any[] = [input.flag]

                if (input.type) {
                    whereClause += " AND tf.flag_type = ?"
                    params.push(input.type)
                }

                const stmt = db.prepare(`
                    SELECT 
                        tpt.id, tpt.name, tpt.family, tpt.synonyms,
                        n.name as taxon_name, p.name as part_name,
                        tf.flag, tf.flag_type as type
                    FROM tpt_flags tf
                    JOIN tpt_nodes tpt ON tpt.id = tf.tpt_id
                    JOIN nodes n ON n.id = tpt.taxon_id
                    JOIN part_def p ON p.id = tpt.part_id
                    ${whereClause}
                    ORDER BY tpt.name ASC
                    LIMIT ? OFFSET ?
                `)
                const rows = stmt.all(...params, input.limit, input.offset) as any[]

                // Get total count for pagination
                const countStmt = db.prepare(`
                    SELECT COUNT(*) as total
                    FROM tpt_flags tf
                    JOIN tpt_nodes tpt ON tpt.id = tf.tpt_id
                    ${whereClause}
                `)
                const total = (countStmt.get(...params) as any)?.total || 0

                return { rows, total }
            } catch (error) {
                console.error('Error in getFlagEntities:', error)
                return { rows: [], total: 0 }
            }
        }),

    // New: Get all categories with metadata
    getCategories: t.procedure.query(() => {
        try {
            const stmt = db.prepare(`
        SELECT id, name, description, kind
        FROM categories
        ORDER BY name ASC
      `)
            return stmt.all() as any[]
        } catch {
            return []
        }
    }),

    // New: Get parts filtered by category
    getPartsByCategory: t.procedure
        .input(z.object({
            categoryId: z.string(),
            limit: z.number().min(1).max(200).default(50),
            offset: z.number().min(0).default(0)
        }))
        .query(({ input }) => {
            const stmt = db.prepare(`
        SELECT p.id, p.name, p.kind, p.parent_id as parentId,
               c.name as category_name, c.description as category_description, c.kind as category_kind
        FROM part_def p
        JOIN categories c ON p.category = c.id
        WHERE c.id = ?
        ORDER BY p.name ASC
        LIMIT ? OFFSET ?
      `)
            return stmt.all(input.categoryId, input.limit, input.offset) as any[]
        }),
})
