import { z } from 'zod'
import { TRPCError } from '@trpc/server'
import { db } from '../db'
import { t } from './_t'
import { safeParseJSON } from './_util'

export const entitiesRouter = t.router({
    get: t.procedure
        .input(z.object({ id: z.string() }))
        .query(({ input }) => {
            const { id } = input

            // Determine entity type from ID prefix - FIXED: check TP first, then taxon
            let entityType: 'taxon' | 'tp' | 'tpt' | null = null
            if (id.startsWith('tx:') && id.includes(':part:')) entityType = 'tp'
            else if (id.startsWith('tx:')) entityType = 'taxon'
            else if (id.startsWith('tpt:')) entityType = 'tpt'

            if (!entityType) {
                throw new TRPCError({ code: 'NOT_FOUND', message: 'Invalid entity ID format' })
            }

            if (entityType === 'taxon') {
                const stmt = db.prepare(`
          SELECT id, name, slug, rank, parent_id as parentId
          FROM nodes WHERE id = ?
        `)
                const node = stmt.get(id) as any
                if (!node) throw new TRPCError({ code: 'NOT_FOUND' })

                // Get common parts for this taxon (using lineage for consistency)
                const partsStmt = db.prepare(`
          WITH RECURSIVE lineage(id) AS (
            SELECT id FROM nodes WHERE id = ?
            UNION ALL
            SELECT n.parent_id FROM nodes n JOIN lineage l ON n.id = l.id
            WHERE n.parent_id IS NOT NULL
          )
          SELECT DISTINCT p.id, p.name, COUNT(tpt.id) as derivedCount
          FROM has_part hp
          JOIN part_def p ON p.id = hp.part_id
          LEFT JOIN tpt_nodes tpt ON tpt.taxon_id = ? AND tpt.part_id = p.id
          WHERE hp.taxon_id IN (SELECT id FROM lineage)
          GROUP BY p.id, p.name
          ORDER BY derivedCount DESC, p.name ASC
          LIMIT 10
        `)
                const parts = partsStmt.all(id, id) as any[]

                // Get popular derived foods (TPTs)
                const derivedStmt = db.prepare(`
          SELECT id, name, family, synonyms
          FROM tpt_nodes
          WHERE taxon_id = ?
          ORDER BY name ASC
          LIMIT 10
        `)
                const derived = derivedStmt.all(id) as any[]

                return {
                    id: node.id,
                    docType: 'taxon' as const,
                    name: node.name,
                    displayName: node.name,
                    slug: node.slug,
                    rank: node.rank,
                    parentId: node.parentId,
                    commonParts: parts.map(p => ({
                        id: p.id,
                        name: p.name,
                        derivedCount: p.derivedCount
                    })),
                    popularDerived: derived.map(d => ({
                        id: d.id,
                        name: d.name,
                        family: d.family,
                        synonyms: safeParseJSON<string[]>(d.synonyms, [])
                    }))
                }
            }

            if (entityType === 'tp') {
                const stmt = db.prepare(`
          SELECT 
            tp.id, tp.taxon_id, tp.part_id, tp.name, tp.display_name, tp.slug, tp.rank,
            n.name AS taxon_name, n.rank AS taxon_rank,
            p.name AS part_name
          FROM taxon_part_nodes tp
          JOIN nodes n ON n.id = tp.taxon_id
          JOIN part_def p ON p.id = tp.part_id
          WHERE tp.id = ?
        `)
                const row = stmt.get(id) as any
                if (!row) throw new TRPCError({ code: 'NOT_FOUND' })

                // Get popular derived foods (TPTs) for this TP
                const derivedStmt = db.prepare(`
          SELECT id, name, family, synonyms
          FROM tpt_nodes
          WHERE taxon_id = ? AND part_id = ?
          ORDER BY name ASC
          LIMIT 10
        `)
                const derived = derivedStmt.all(row.taxon_id, row.part_id) as any[]

                // Get applicable transforms from new tpt_identity_steps table
                const transformsStmt = db.prepare(`
          SELECT DISTINCT 
            td.id,
            td.name,
            td.identity,
            td."order" as ordering
          FROM tpt_identity_steps s
          JOIN transform_def td ON td.id = s.tf_id
          WHERE s.taxon_id = ? AND s.part_id = ?
          ORDER BY td."order" ASC, td.name ASC
        `)
                const transforms = transformsStmt.all(row.taxon_id, row.part_id) as any[]

                return {
                    id: row.id,
                    docType: 'tp' as const,
                    name: row.display_name ?? row.name,
                    displayName: row.display_name ?? row.name,
                    slug: row.slug,
                    rank: row.rank,
                    taxon: {
                        id: row.taxon_id,
                        name: row.taxon_name,
                        rank: row.taxon_rank
                    },
                    part: {
                        id: row.part_id,
                        name: row.part_name
                    },
                    popularDerived: derived.map(d => ({
                        id: d.id,
                        name: d.name,
                        family: d.family,
                        synonyms: safeParseJSON<string[]>(d.synonyms, [])
                    })),
                    applicableTransforms: transforms.map(t => ({
                        id: t.id,
                        name: t.name,
                        identity: !!t.identity,
                        ordering: t.ordering ?? 999
                    }))
                }
            }

            if (entityType === 'tpt') {
                const stmt = db.prepare(`
          SELECT t.id, t.taxon_id, t.part_id, t.family, t.identity_hash,
                 t.name, t.synonyms, t.path_json,
                 n.name AS taxon_name, n.rank AS taxon_rank,
                 p.name AS part_name
          FROM tpt_nodes t
          JOIN nodes n ON n.id = t.taxon_id
          JOIN part_def p ON p.id = t.part_id
          WHERE t.id = ?
        `)
                const row = stmt.get(id) as any
                if (!row) throw new TRPCError({ code: 'NOT_FOUND' })

                const path = safeParseJSON<Array<{ id: string; params?: Record<string, any> }>>(row.path_json, [])
                const synonyms = safeParseJSON<string[]>(row.synonyms, [])

                // Get related TPTs (same taxon+part, different transforms)
                const relatedStmt = db.prepare(`
          SELECT id, name, family, path_json
          FROM tpt_nodes
          WHERE taxon_id = ? AND part_id = ? AND id != ?
          ORDER BY name ASC
          LIMIT 10
        `)
                const related = relatedStmt.all(row.taxon_id, row.part_id, id) as any[]

                // Get sibling TPTs (same part+family, different taxon)
                const siblingsStmt = db.prepare(`
          SELECT id, name, family, taxon_id
          FROM tpt_nodes
          WHERE part_id = ? AND family = ? AND id != ?
          ORDER BY name ASC
          LIMIT 10
        `)
                const siblings = siblingsStmt.all(row.part_id, row.family, id) as any[]

                return {
                    id: row.id,
                    docType: 'tpt' as const,
                    name: row.name ?? null,
                    displayName: row.name ?? null,
                    synonyms,
                    family: row.family,
                    identityHash: row.identity_hash,
                    taxon: {
                        id: row.taxon_id,
                        name: row.taxon_name,
                        rank: row.taxon_rank
                    },
                    part: {
                        id: row.part_id,
                        name: row.part_name
                    },
                    transformPath: path.map(step => ({
                        id: step.id,
                        params: step.params ?? {}
                    })),
                    related: {
                        upstream: {
                            taxon: row.taxon_id,
                            part: row.part_id
                        },
                        variants: related.map(r => ({
                            id: r.id,
                            name: r.name,
                            diff: 'Different transform path'
                        })),
                        siblings: siblings.map(s => ({
                            id: s.id,
                            name: s.name,
                            diff: 'Different taxon, same part'
                        }))
                    }
                }
            }

            throw new TRPCError({ code: 'NOT_FOUND' })
        }),
})
