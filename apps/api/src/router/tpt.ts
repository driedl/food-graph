import { z } from 'zod'
import { TRPCError } from '@trpc/server'
import { db } from '../db'
import { t } from './_t'
import { safeParseJSON, asString } from './_util'

export const tptRouter = t.router({
    /** Fetch a single canonical TPT node by id with flags, cuisines, and related TPTs */
    get: t.procedure
        .input(z.object({
            id: z.string(),
            includeFlags: z.boolean().default(true),
            includeCuisines: z.boolean().default(true),
            includeRelated: z.boolean().default(true)
        }))
        .query(({ input }) => {
            const row = db.prepare(`
        SELECT t.id, t.taxon_id, t.part_id, t.family, t.identity_hash,
               t.name, t.synonyms, t.path_json,
               n.name   AS taxon_name, n.rank AS taxon_rank,
               p.name   AS part_name
        FROM tpt_nodes t
        JOIN nodes n ON n.id = t.taxon_id
        JOIN part_def p ON p.id = t.part_id
        WHERE t.id = ?
      `).get(input.id) as any
            if (!row) throw new TRPCError({ code: 'NOT_FOUND' })
            const path = safeParseJSON<Array<{ id: string; params?: Record<string, any> }>>(row.path_json, [])
            const synonyms = safeParseJSON<string[]>(row.synonyms, [])

            // Get flags if requested
            let flags: string[] = []
            if (input.includeFlags) {
                try {
                    const flagRows = db.prepare(`
                        SELECT tf.flag
                        FROM tpt_flags tf
                        WHERE tf.tpt_id = ?
                    `).all(input.id) as Array<{ flag: string }>
                    flags = flagRows.map(r => r.flag)
                } catch {
                    flags = []
                }
            }

            // Get cuisines if requested
            let cuisines: string[] = []
            if (input.includeCuisines) {
                try {
                    const cuisineRows = db.prepare(`
                        SELECT tc.cuisine
                        FROM tpt_cuisines tc
                        WHERE tc.tpt_id = ?
                    `).all(input.id) as Array<{ cuisine: string }>
                    cuisines = cuisineRows.map(r => r.cuisine)
                } catch {
                    cuisines = []
                }
            }

            // Get related TPTs if requested
            let related = { siblings: [], variants: [] }
            if (input.includeRelated) {
                try {
                    // Get related TPTs (same taxon+part, different transforms)
                    const relatedRows = db.prepare(`
                        SELECT id, name, family, path_json
                        FROM tpt_nodes
                        WHERE taxon_id = ? AND part_id = ? AND id != ?
                        ORDER BY name ASC
                        LIMIT 10
                    `).all(row.taxon_id, row.part_id, input.id) as any[]

                    // Get sibling TPTs (same part+family, different taxon)
                    const siblingRows = db.prepare(`
                        SELECT id, name, family, taxon_id
                        FROM tpt_nodes
                        WHERE part_id = ? AND family = ? AND id != ?
                        ORDER BY name ASC
                        LIMIT 10
                    `).all(row.part_id, row.family, input.id) as any[]

                    related = {
                        siblings: siblingRows.map(r => ({
                            id: r.id,
                            name: r.name,
                            family: r.family,
                            taxonId: r.taxon_id
                        })),
                        variants: relatedRows.map(r => ({
                            id: r.id,
                            name: r.name,
                            family: r.family
                        }))
                    }
                } catch {
                    related = { siblings: [], variants: [] }
                }
            }

            return {
                id: row.id,
                taxonId: row.taxon_id,
                partId: row.part_id,
                family: row.family,
                identityHash: row.identity_hash,
                name: row.name ?? null,
                synonyms,
                identity: path,              // identity-only path (ordered)
                taxon: { id: row.taxon_id, name: row.taxon_name, rank: row.taxon_rank },
                part: { id: row.part_id, name: row.part_name },
                flags,
                cuisines,
                related
            }
        }),

    /** Human-friendly breakdown of a TPT's identity steps */
    explain: t.procedure
        .input(z.object({ id: z.string() }))
        .query(({ input }) => {
            const row = db.prepare(`
        SELECT t.id, t.taxon_id, t.part_id, t.family, t.identity_hash,
               t.name, t.synonyms, t.path_json,
               n.name AS taxon_name, p.name AS part_name
        FROM tpt_nodes t
        JOIN nodes n ON n.id = t.taxon_id
        JOIN part_def p ON p.id = t.part_id
        WHERE t.id = ?
      `).get(input.id) as any
            if (!row) throw new TRPCError({ code: 'NOT_FOUND' })
            const path = safeParseJSON<Array<{ id: string; params?: Record<string, any> }>>(row.path_json, [])
            const steps = path.map(s => {
                const params = Object.entries(s.params ?? {})
                    .map(([k, v]) => `${k}=${String(v)}`)
                    .join(', ')
                return { id: s.id, params: s.params ?? {}, label: params ? `${s.id}(${params})` : s.id }
            })
            const summary = [
                `family=${row.family}`,
                `identity=[${steps.map(s => s.label).join(' → ')}]`
            ].join(' • ')
            return {
                id: row.id,
                taxonId: row.taxon_id,
                partId: row.part_id,
                family: row.family,
                identityHash: row.identity_hash,
                taxonName: row.taxon_name,
                partName: row.part_name,
                name: row.name ?? null,
                steps,
                summary
            }
        }),

    /** List TPTs for a (taxonId, partId) optionally filtered by family */
    listForTP: t.procedure
        .input(z.object({
            taxonId: z.string(),
            partId: z.string(),
            family: z.string().optional(),
            limit: z.number().min(1).max(200).default(50),
            offset: z.number().min(0).default(0)
        }))
        .query(({ input }) => {
            const stmt = db.prepare(`
        SELECT id, family, identity_hash, name, synonyms, path_json
        FROM tpt_nodes
        WHERE taxon_id = ? AND part_id = ?
          AND (? IS NULL OR family = ?)
        ORDER BY family ASC, id ASC
        LIMIT ? OFFSET ?
      `)
            const rows = stmt.all(input.taxonId, input.partId,
                input.family ?? null, input.family ?? null,
                input.limit, input.offset) as any[]
            return rows.map(r => ({
                id: r.id,
                family: r.family,
                identityHash: r.identity_hash,
                name: r.name ?? null,
                synonyms: safeParseJSON<string[]>(r.synonyms, []),
                identity: safeParseJSON(r.path_json, [])
            }))
        }),

    /** Best-effort resolver: given a TP + freeform transforms, pick the closest TPT. */
    resolveBestForTP: t.procedure
        .input(z.object({
            taxonId: z.string(),
            partId: z.string(),
            transforms: z.array(z.object({
                id: z.string(),
                params: z.record(z.any()).optional()
            })).default([]),
            familyHint: z.string().optional(),
        }))
        .query(({ input }) => {
            const { taxonId, partId, transforms, familyHint } = input
            const candRows = db.prepare(`
        SELECT t.id, t.family, t.identity_hash, t.name, t.synonyms, t.path_json,
               GROUP_CONCAT(DISTINCT s.tf_id) AS tf_ids
        FROM tpt_nodes t
        JOIN tpt_identity_steps s ON s.tpt_id = t.id
        WHERE t.taxon_id = ? AND t.part_id = ?
          AND (? IS NULL OR t.family = ?)
        GROUP BY t.id, t.family, t.identity_hash, t.name, t.synonyms, t.path_json
      `).all(taxonId, partId, familyHint ?? null, familyHint ?? null) as any[]
            if (!candRows.length) return null

            const inIds = new Set(transforms.map(t => t.id))
            const inParams = new Map<string, Record<string, any>>(
                transforms.map(t => [t.id, t.params ?? {}])
            )

            type Scored = {
                id: string
                family: string
                score: number
                name: string | null
                matched: string[]
                missing: string[]
                extra: string[]
            }

            const scored: Scored[] = candRows.map(r => {
                const candIds = new Set((r.tf_ids || '').split(',').filter(Boolean))
                const candPath = safeParseJSON<Array<{ id: string; params?: Record<string, any> }>>(r.path_json, [])
                const candParamsById = new Map(candPath.map(s => [s.id, s.params ?? {}]))

                const inter = [...candIds].filter(id => inIds.has(id))
                const missing = [...candIds].filter(id => !inIds.has(id))
                const extra = [...inIds].filter(id => !candIds.has(id))

                // Jaccard / F1-like score
                const prec = inter.length / Math.max(1, inIds.size)
                const rec = inter.length / Math.max(1, candIds.size)
                const f1 = (prec + rec) > 0 ? (2 * prec * rec) / (prec + rec) : 0

                // Param agreement bonus (small, capped)
                let bonus = 0
                for (const id of inter) {
                    const a = inParams.get(id) ?? {}
                    const b = candParamsById.get(id) ?? {}
                    for (const [k, av] of Object.entries(a)) {
                        if (k in b && asString(av) === asString(b[k])) bonus += 0.05
                    }
                }
                bonus = Math.min(bonus, 0.25)

                return {
                    id: r.id,
                    family: r.family,
                    name: r.name ?? null,
                    score: Number((f1 + bonus).toFixed(4)),
                    matched: inter,
                    missing,
                    extra,
                }
            })

            // Pick highest score, stable tie-break by family then id
            scored.sort((a, b) => {
                if (b.score !== a.score) return b.score - a.score
                if (a.family !== b.family) return a.family.localeCompare(b.family)
                return a.id.localeCompare(b.id)
            })

            return scored[0]
        }),
})
