import type Database from 'better-sqlite3'
import type { ComposeInput, ComposeResult, KV } from './index.js'

function orderKeyFromDB(db: Database) {
  const rows = db.prepare('SELECT id, ordering FROM transform_def').all() as Array<{id:string; ordering:number|null}>
  const map = new Map<string, number>()
  for (const r of rows) map.set(r.id, (r.ordering ?? 999))
  return (id: string) => map.get(id) ?? 999
}

function lastSeg(txId: string) {
  return txId.split(':').slice(1).join('/') // "tx:a:b:c" -> "a/b/c"
}

function encodeParams(obj: KV): string {
  // canonical: keys alpha-sorted; booleans as true/false; numbers without trailing zeros
  const keys = Object.keys(obj || {}).sort()
  const pairs = keys.map(k => {
    const v = (obj as any)[k]
    if (typeof v === 'number') return `${k}=${Number(v.toFixed(6)).toString()}`
    if (typeof v === 'boolean') return `${k}=${v ? 'true' : 'false'}`
    return `${k}=${String(v)}`
  })
  return pairs.join(',')
}

export function composeFoodState(db: Database, input: ComposeInput): ComposeResult {
  const errors: string[] = []
  const { taxonId, partId } = input

  // build order key once
  const ok = orderKeyFromDB(db)

  // 1) Basic existence checks
  const tx = db.prepare('SELECT id, parent_id FROM nodes WHERE id = ?').get(taxonId) as { id: string; parent_id: string | null } | undefined
  if (!tx) errors.push(`Unknown taxonId: ${taxonId}`)

  const part = db.prepare('SELECT id FROM part_def WHERE id = ?').get(partId) as { id: string } | undefined
  if (!part) errors.push(`Unknown partId: ${partId}`)

  if (errors.length) return { id: null, errors }

  // 2) Ensure taxon has the part (via lineage)
  const hasPart = db.prepare(`
    WITH RECURSIVE lineage(id) AS (
      SELECT id FROM nodes WHERE id = ?
      UNION ALL
      SELECT n.parent_id FROM nodes n JOIN lineage l ON n.id = l.id WHERE n.parent_id IS NOT NULL
    )
    SELECT 1 FROM has_part hp
    WHERE hp.part_id = ? AND hp.taxon_id IN (SELECT id FROM lineage)
    LIMIT 1
  `).get(taxonId, partId)
  if (!hasPart) errors.push(`Part ${partId} not applicable to ${taxonId}`)

  // 3) Load transform defs -> schema map
  const tdefs = db.prepare('SELECT id, identity, schema_json FROM transform_def').all() as Array<{ id: string; identity: 0|1; schema_json: string | null }>
  const defMap = new Map<string, { identity: boolean; schema: Array<{key:string;kind:string;enum?:string[]}> }>()
  for (const d of tdefs) {
    defMap.set(d.id, { identity: !!d.identity, schema: (d.schema_json ? JSON.parse(d.schema_json) : []) })
  }

  // 4) Validate input transforms and applicability
  const normTransforms: { id: string; params: KV }[] = []
  for (const t of input.transforms || []) {
    const def = defMap.get(t.id)
    if (!def) { errors.push(`Unknown transform: ${t.id}`); continue }

    // NEW: enforce identity flag
    if (!def.identity) {
      errors.push(`Transform ${t.id} is non-identity and cannot appear in the identity chain`);
      continue;
    }

    // applicability against lineage + part
    const allowed = db.prepare(`
      WITH RECURSIVE lineage(id) AS (
        SELECT id FROM nodes WHERE id = ?
        UNION ALL
        SELECT n.parent_id FROM nodes n JOIN lineage l ON n.id = l.id WHERE n.parent_id IS NOT NULL
      )
      SELECT 1
      FROM transform_applicability ta
      WHERE ta.part_id = ? AND ta.transform_id = ? AND ta.taxon_id IN (SELECT id FROM lineage)
      LIMIT 1
    `).get(taxonId, partId, t.id)
    if (!allowed) { errors.push(`Transform ${t.id} not applicable to ${taxonId} + ${partId}`); continue }

    // params validation
    const schema = def.schema
    const params = Object.assign({}, t.params || {})
    const allowedKeys = new Set(schema.map(s => s.key))
    // no extra keys
    for (const k of Object.keys(params)) {
      if (!allowedKeys.has(k)) { errors.push(`Transform ${t.id}: unknown param "${k}"`); }
    }
    // type & enum checks (lightweight)
    for (const spec of schema) {
      if (!(spec.key in params)) continue // optional by default in v0.1
      const v = (params as any)[spec.key]
      switch (spec.kind) {
        case 'boolean':
          if (typeof v !== 'boolean') errors.push(`Transform ${t.id}: param ${spec.key} must be boolean`)
          break
        case 'number':
          if (typeof v !== 'number' || Number.isNaN(v)) errors.push(`Transform ${t.id}: param ${spec.key} must be number`)
          break
        case 'enum':
          if (typeof v !== 'string' || !spec.enum?.includes(v)) errors.push(`Transform ${t.id}: param ${spec.key} must be one of [${(spec.enum||[]).join(', ')}]`)
          break
        case 'string':
          if (typeof v !== 'string') errors.push(`Transform ${t.id}: param ${spec.key} must be string`)
          break
      }
    }

    normTransforms.push({ id: t.id, params })
  }

  if (errors.length) return { id: null, errors }

  // 5) Canonicalize order and params encoding
  normTransforms.sort((a, b) => ok(a.id) - ok(b.id))

  // Only identity transforms affect the canonical fs path
  const identitySet = new Set<string>()
  for (const [id, def] of defMap.entries()) {
    if (def.identity) identitySet.add(id)
  }
  const identityTransforms = normTransforms.filter(t => identitySet.has(t.id))

  const chain = identityTransforms.map(t => {
    const p = encodeParams(t.params || {})
    return p ? `${t.id}{${p}}` : `${t.id}`
  }).join('/')

  // 6) Build fs:// path
  const path = [
    'fs:/',
    lastSeg(taxonId),                   // e.g., "animalia/chordata/.../sus/scrofa_domesticus"
    partId,                             // "part:muscle" or "part:cut:belly"
    chain ? chain : undefined
  ].filter(Boolean).join('/')

  return {
    id: path,
    errors: [],
    normalized: {
      taxonId,
      partId,
      transforms: normTransforms
    }
  }
}
