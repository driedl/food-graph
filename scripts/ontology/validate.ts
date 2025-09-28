
#!/usr/bin/env tsx
import fs from 'node:fs'
import path from 'node:path'

type Taxon = {
  id: string
  parent: string | null
  rank: string
  display_name: string
  latin_name: string
  aliases?: string[]
  tags?: string[]
  deprecated_of?: string
}

const FORBIDDEN_TOKENS = [
  'raw','cooked','baked','fried','roasted','boiled','broiled','steamed',
  'canned','brined','greek','strained','enriched','refined','00','2%','1%','nonfat','skim','lowfat','reduced'
]

function isTxId(id: string){ return /^tx:[a-z0-9:_-]+$/.test(id) }
function readJsonl(file: string): Taxon[] {
  const txt = fs.readFileSync(file,'utf8')
  const out: Taxon[] = []
  txt.split(/\r?\n/).forEach((line, i) => {
    const ln = line.trim()
    if (!ln) return
    try {
      const obj = JSON.parse(ln)
      out.push(obj)
    } catch (e) {
      throw new Error(`Invalid JSON at ${file}:${i+1}`)
    }
  })
  return out
}

function walkDir(dir: string): string[] {
  const out: string[] = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name)
    if (entry.isDirectory()) out.push(...walkDir(p))
    else if (entry.isFile() && entry.name.endsWith('.jsonl')) out.push(p)
  }
  return out
}

function hasForbidden(str: string): string | null {
  const s = str.toLowerCase()
  for (const t of FORBIDDEN_TOKENS) {
    if (s.includes(t)) return t
  }
  return null
}

function main(){
  const dir = process.argv[2] || 'data/ontology/taxa'
  if (!fs.existsSync(dir)) {
    console.error(`[lint] directory not found: ${dir}`)
    process.exit(1)
  }

  const files = walkDir(dir)
  if (!files.length) {
    console.error('[lint] no .jsonl files found')
    process.exit(1)
  }

  const all: Taxon[] = []
  for (const f of files) all.push(...readJsonl(f))

  const byId = new Map<string, Taxon>()
  let errors = 0

  // Basic validation
  for (const t of all) {
    if (!t.id || !isTxId(t.id)) {
      console.error(`[id] invalid or missing: ${t.id}`)
      errors++
    }
    if (t.parent !== null && typeof t.parent !== 'string') {
      console.error(`[parent] bad parent for ${t.id}`)
      errors++
    }
    if (!t.rank || typeof t.rank !== 'string') {
      console.error(`[rank] missing rank for ${t.id}`)
      errors++
    }
    if (!t.display_name) {
      console.error(`[display_name] missing for ${t.id}`)
      errors++
    }
    if (!t.latin_name) {
      console.error(`[latin_name] missing for ${t.id}`)
      errors++
    }
    const bad1 = hasForbidden(t.display_name || '')
    if (bad1){
      console.error(`[name] process term "${bad1}" found in display_name for ${t.id}`)
      errors++
    }
    for (const al of (t.aliases || [])) {
      const bad2 = hasForbidden(al)
      if (bad2){
        console.error(`[alias] process term "${bad2}" found in alias for ${t.id}`)
        errors++
      }
    }
    if (byId.has(t.id)) {
      console.error(`[dup] duplicate id ${t.id}`)
      errors++
    } else {
      byId.set(t.id, t)
    }
  }

  // Parent existence & cycle check
  // Build adjacency and in-degree for cycle detection with DFS
  const visited = new Set<string>()
  const stack = new Set<string>()
  function dfs(id: string): boolean {
    if (stack.has(id)) return true // cycle
    if (visited.has(id)) return false
    visited.add(id); stack.add(id)
    const node = byId.get(id)!
    if (node.parent) {
      const p = byId.get(node.parent)
      if (!p) {
        console.error(`[parent] ${id} has unknown parent ${node.parent}`)
        errors++
      } else {
        if (dfs(node.parent)) return true
      }
    }
    stack.delete(id)
    return false
  }

  for (const id of byId.keys()) {
    if (dfs(id)) {
      console.error(`[cycle] detected in lineage at ${id}`)
      errors++
      break
    }
  }

  if (errors > 0) {
    console.error(`\n[lint] FAILED with ${errors} error(s)`)
    process.exit(1)
  } else {
    console.log(`[lint] OK — ${byId.size} taxa checked across ${files.length} file(s)`)
  }
}

main()
