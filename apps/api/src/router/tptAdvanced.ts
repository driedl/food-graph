import { z } from 'zod'
import { TRPCError } from '@trpc/server'
import { db } from '../db'
import { t } from './_t'
import { asString } from './_util'

export const tptAdvancedRouter = t.router({
    // Validate a TPT specification without creating it
    validate: t.procedure
        .input(z.object({
            taxonId: z.string(),
            partId: z.string(),
            transforms: z.array(z.object({
                id: z.string(),
                params: z.record(z.any()).optional()
            })).default([])
        }))
        .query(({ input }) => {
            const { taxonId, partId, transforms } = input

            // Check if taxon exists
            const taxonStmt = db.prepare('SELECT id, name FROM nodes WHERE id = ?')
            const taxon = taxonStmt.get(taxonId) as any
            if (!taxon) {
                return {
                    valid: false,
                    errors: [`Taxon ${taxonId} not found`],
                    warnings: []
                }
            }

            // Check if part exists and is applicable to taxon
            const partStmt = db.prepare(`
        SELECT p.id, p.name
        FROM part_def p
        JOIN has_part hp ON hp.part_id = p.id
        WHERE p.id = ? AND hp.taxon_id = ?
      `)
            const part = partStmt.get(partId, taxonId) as any
            if (!part) {
                return {
                    valid: false,
                    errors: [`Part ${partId} not applicable to taxon ${taxonId}`],
                    warnings: []
                }
            }

            // Validate transforms
            const errors: string[] = []
            const warnings: string[] = []

            // Check if transforms are used in existing TPTs for this taxon+part
            const existingTransformsStmt = db.prepare(`
        SELECT DISTINCT s.tf_id as id
        FROM tpt_identity_steps s
        WHERE s.taxon_id = ? AND s.part_id = ?
      `)
            const existingTransforms = existingTransformsStmt.all(taxonId, partId) as Array<{ id: string }>
            const existingTransformIds = new Set(existingTransforms.map(t => t.id))

            for (const transform of transforms) {
                if (!existingTransformIds.has(transform.id)) {
                    errors.push(`Transform ${transform.id} not found in existing TPTs for ${taxonId}:${partId}`)
                }
                // Basic parameter validation
                if (transform.id.includes('identity') && Object.keys(transform.params || {}).length === 0) {
                    warnings.push(`Identity transform ${transform.id} should have parameters`)
                }
            }

            // Find nearest curated TPT
            const nearestStmt = db.prepare(`
        SELECT id, name, path_json
        FROM tpt_nodes
        WHERE taxon_id = ? AND part_id = ?
        ORDER BY name ASC
        LIMIT 1
      `)
            const nearest = nearestStmt.get(taxonId, partId) as any

            return {
                valid: errors.length === 0,
                errors,
                warnings,
                nearestCurated: nearest ? {
                    id: nearest.id,
                    name: nearest.name,
                    diff: 'Different transform path'
                } : null
            }
        }),

    // Compile a TPT from specification
    compile: t.procedure
        .input(z.object({
            taxonId: z.string(),
            partId: z.string(),
            transforms: z.array(z.object({
                id: z.string(),
                params: z.record(z.any()).optional()
            })).default([])
        }))
        .query(({ input }) => {
            const { taxonId, partId, transforms } = input

            // Check applicability with proper status detection
            const status = db.prepare(`
        SELECT
          CASE WHEN n.id IS NULL THEN 'taxon_missing'
               WHEN p.id IS NULL THEN 'part_missing'
               WHEN hp.taxon_id IS NULL THEN 'part_not_applicable'
               ELSE 'ok' END AS status
        FROM (SELECT ? AS id) input
        LEFT JOIN nodes n      ON n.id = input.id
        LEFT JOIN part_def p   ON p.id = ?
        LEFT JOIN has_part hp  ON hp.part_id = p.id AND hp.taxon_id = input.id
      `).get(taxonId, partId) as { status: string }

            if (status.status !== 'ok') {
                throw new TRPCError({ code: 'NOT_FOUND', message: status.status })
            }

            // Generate canonical ID and identity hash
            const identityPath = transforms.map(t => `${t.id}${Object.keys(t.params || {}).length > 0 ? `{${Object.entries(t.params || {}).map(([k, v]) => `${k}=${v}`).join(',')}}` : ''}`).join('→')
            const identityHash = Buffer.from(identityPath).toString('base64').slice(0, 16)
            const canonicalId = `tpt:${taxonId.split(':').slice(1).join('_')}:${partId.split(':').slice(1).join('_')}:${identityHash}`

            // Check if already exists
            const existingStmt = db.prepare('SELECT id, name FROM tpt_nodes WHERE id = ?')
            const existing = existingStmt.get(canonicalId) as any

            if (existing) {
                return {
                    canonicalId: existing.id,
                    identityHash,
                    name: existing.name,
                    alreadyExists: true
                }
            }

            // Generate name from transforms (use transform IDs as names)
            const transformNames = transforms.map(t => t.id)
            const generatedName = transformNames.length > 0 ? transformNames.join(' ') : 'Custom Food'

            return {
                canonicalId,
                identityHash,
                name: generatedName,
                alreadyExists: false,
                transformPath: transforms.map(t => ({
                    id: t.id,
                    params: t.params || {}
                }))
            }
        }),

    // Get suggestions for a TPT
    suggest: t.procedure
        .input(z.object({
            seedId: z.string(),
            type: z.enum(['related', 'variants', 'substitutes']).default('related'),
            limit: z.number().min(1).max(20).default(10)
        }))
        .query(({ input }) => {
            const { seedId, type, limit } = input

            // Get seed TPT info
            const seedStmt = db.prepare(`
        SELECT tpt.id, tpt.name, tpt.taxon_id, tpt.part_id, tpt.family
        FROM tpt_nodes tpt
        WHERE tpt.id = ?
      `)
            const seed = seedStmt.get(seedId) as any
            if (!seed) {
                throw new TRPCError({ code: 'NOT_FOUND', message: 'Seed TPT not found' })
            }

            let suggestions: any[] = []

            if (type === 'related') {
                // Same taxon or same part
                const stmt = db.prepare(`
          SELECT 
            tpt.id, tpt.name, tpt.family,
            CASE 
              WHEN tpt.taxon_id = ? THEN 'Same taxon, different part'
              WHEN tpt.part_id = ? THEN 'Same part, different taxon'
              ELSE 'Related'
            END as reason,
            CASE 
              WHEN tpt.taxon_id = ? AND tpt.part_id = ? THEN 1.0
              WHEN tpt.taxon_id = ? OR tpt.part_id = ? THEN 0.8
              ELSE 0.5
            END as score
          FROM tpt_nodes tpt
          WHERE tpt.id != ? 
            AND (tpt.taxon_id = ? OR tpt.part_id = ?)
          ORDER BY score DESC, tpt.name ASC
          LIMIT ?
        `)
                suggestions = stmt.all(seed.taxon_id, seed.part_id, seed.taxon_id, seed.part_id, seed.taxon_id, seed.part_id, seedId, seed.taxon_id, seed.part_id, limit) as any[]
            } else if (type === 'variants') {
                // Same taxon+part, different transforms
                const stmt = db.prepare(`
          SELECT 
            tpt.id, tpt.name, tpt.family,
            'Different transform path' as reason,
            0.9 as score
          FROM tpt_nodes tpt
          WHERE tpt.taxon_id = ? AND tpt.part_id = ? AND tpt.id != ?
          ORDER BY tpt.name ASC
          LIMIT ?
        `)
                suggestions = stmt.all(seed.taxon_id, seed.part_id, seedId, limit) as any[]
            } else if (type === 'substitutes') {
                // Same family, different taxon+part
                const stmt = db.prepare(`
          SELECT 
            tpt.id, tpt.name, tpt.family,
            'Same family, different source' as reason,
            0.7 as score
          FROM tpt_nodes tpt
          WHERE tpt.family = ? AND tpt.id != ?
          ORDER BY tpt.name ASC
          LIMIT ?
        `)
                suggestions = stmt.all(seed.family, seedId, limit) as any[]
            }

            return {
                seed: {
                    id: seed.id,
                    name: seed.name
                },
                suggestions: suggestions.map(s => ({
                    id: s.id,
                    name: s.name,
                    reason: s.reason,
                    score: s.score
                }))
            }
        }),
})
