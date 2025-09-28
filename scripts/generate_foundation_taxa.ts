#!/usr/bin/env -S node --no-warnings
/**
 * Foundation 411 → NDJSON (taxonomy nodes)
 * 
 * Inputs:
 *   --fdc <path.csv|json>   USDA FDC "Foundation Foods" export (minimal: description/name field)
 *   --out <path.jsonl>      Output NDJSON file with real LF newlines
 * 
 * Behavior:
 *   - Normalizes names → slug
 *   - Assigns tentative kingdom and species/genus where confident via mapping dict
 *   - Falls back to 'unclassified' under kingdom with tags ["needs_taxonomy"]
 */
import fs from 'node:fs'
import path from 'node:path'

const arg = Object.fromEntries(process.argv.slice(2).reduce((acc, cur, i, arr) => {
  if (cur.startsWith('--')) acc.push([cur.slice(2), arr[i+1]])
  return acc
}, [] as Array<[string, string]>))

if (!arg.fdc || !arg.out) {
  console.error('Usage: tsx scripts/generate_foundation_taxa.ts --fdc foundation.csv --out data/ontology/taxa/foundation-411.jsonl')
  process.exit(1)
}

// --- minimal CSV loader (no deps) ---
function parseCSV(txt: string): Array<Record<string,string>> {
  const lines = txt.split('\n').filter(l => l.trim().length)
  const header = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g,''))
  return lines.slice(1).map(l => {
    const cols: string[] = []
    let cur = ''
    let inQ = false
    for (let i=0;i<l.length;i++){
      const ch = l[i]
      if (ch === '"' && l[i+1] === '"') { cur+='"'; i++; continue }
      if (ch === '"') { inQ = !inQ; continue }
      if (ch === ',' && !inQ) { cols.push(cur); cur=''; continue }
      cur += ch
    }
    cols.push(cur)
    const obj: Record<string,string> = {}
    header.forEach((h, i) => {
      obj[h] = (cols[i] ?? '').trim().replace(/^"|"$/g,'')
    })
    return obj
  })
}

function slugify(s: string){
  return s.normalize('NFKD').replace(/[^\w\s-]+/g,'').replace(/\s+/g,'-').replace(/-+/g,'-').toLowerCase()
}

// --- curated mapping (grow over time) ---
const map: Record<string, {id: string, display_name: string, parent: string, rank: string, latin_name?: string}> = {
  // examples; extend via PRs:
  'apple': { id: 'tx:plantae:rosaceae:malus:domestica', display_name: 'Apple', parent: 'tx:plantae', rank: 'species', latin_name: 'Malus domestica' },
  'banana': { id: 'tx:plantae:musaceae:musa:acuminata', display_name: 'Banana', parent: 'tx:plantae', rank: 'species', latin_name: 'Musa acuminata' },
  'rice': { id: 'tx:plantae:poaceae:oryza:sativa', display_name: 'Rice', parent: 'tx:plantae', rank: 'species', latin_name: 'Oryza sativa' },
  'oat': { id: 'tx:plantae:poaceae:avena:sativa', display_name: 'Oat', parent: 'tx:plantae', rank: 'species', latin_name: 'Avena sativa' },
  'wheat': { id: 'tx:plantae:poaceae:triticum:aestivum', display_name: 'Wheat', parent: 'tx:plantae', rank: 'species', latin_name: 'Triticum aestivum' },
  'hazelnut': { id: 'tx:plantae:fagales:betulaceae:corylus:avellana', display_name: 'Hazelnut', parent: 'tx:plantae', rank: 'species', latin_name: 'Corylus avellana' },
  'chickpea': { id: 'tx:plantae:fabaceae:cicer:arietinum', display_name: 'Chickpea', parent: 'tx:plantae', rank: 'species', latin_name: 'Cicer arietinum' },
  'cow milk': { id: 'tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus', display_name: 'Cow', parent: 'tx:animalia', rank: 'species', latin_name: 'Bos taurus' },
  'salmon': { id: 'tx:animalia:chordata:actinopterygii:salmonidae:salmo:salar', display_name: 'Atlantic salmon', parent: 'tx:animalia', rank: 'species', latin_name: 'Salmo salar' }
}

function classify(name: string){
  const key = name.toLowerCase().replace(/[^a-z\s]/g,' ').replace(/\s+/g,' ').trim()
  for (const kw of Object.keys(map)) {
    if (key.includes(kw)) {
      return { ...map[kw], aliases: [name] }
    }
  }
  // heuristic kingdom
  const kingdom = /milk|beef|pork|chicken|turkey|salmon|tuna|egg|yogurt|cheese|butter/.test(key) ? 'animalia'
                 : /mushroom|yeast/.test(key) ? 'fungi'
                 : /salt|soda|bicarbonate/.test(key) ? 'mineral'
                 : 'plantae'
  const id = `tx:${kingdom}:unclassified:${slugify(name)}`
  return {
    id,
    display_name: name,
    parent: `tx:${kingdom}`,
    rank: 'unclassified',
    aliases: [name],
    tags: ['needs_taxonomy']
  }
}

const ext = path.extname(arg.fdc).toLowerCase()
let rows: Array<Record<string,string>>
if (ext === '.csv') {
  rows = parseCSV(fs.readFileSync(arg.fdc, 'utf8'))
} else if (ext === '.json') {
  const raw = JSON.parse(fs.readFileSync(arg.fdc, 'utf8'))
  rows = Array.isArray(raw) ? raw : raw.items || raw.data || []
} else {
  console.error('Input must be .csv or .json')
  process.exit(2)
}

// Try common fields
const nameField = ['description','food','name','Display_Name','Sample_Description'].find(k => rows[0] && k in rows[0])
if (!nameField) {
  console.error('Could not find a name/description column in the FDC input.')
  process.exit(3)
}

const out = fs.createWriteStream(arg.out, { encoding: 'utf8' })
for (const r of rows) {
  const name = String(r[nameField]).trim()
  if (!name) continue
  const node = classify(name)
  out.write(JSON.stringify({
    id: node.id,
    parent: node.parent ?? null,
    rank: node.rank ?? 'species',
    display_name: node.display_name,
    latin_name: node.latin_name ?? undefined,
    tags: node.tags ?? [],
    aliases: node.aliases ?? []
  }, null, 0) + "\n")
}
out.end()
console.log(`[ok] wrote ${arg.out}`)
