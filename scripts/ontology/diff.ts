
#!/usr/bin/env tsx
import fs from 'node:fs'
import path from 'node:path'

type Taxon = { id: string, parent: string | null }

function readJsonl(file: string): Taxon[] {
  const txt = fs.readFileSync(file,'utf8')
  const out: Taxon[] = []
  txt.split(/\r?\n/).forEach((line) => {
    const ln = line.trim()
    if (!ln) return
    out.push(JSON.parse(ln))
  })
  return out
}

function walk(dir: string): string[] {
  const out: string[] = []
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name)
    if (entry.isDirectory()) out.push(...walk(p))
    else if (entry.isFile() && entry.name.endsWith('.jsonl')) out.push(p)
  }
  return out
}

function load(dir: string){
  const res = new Map<string, Taxon>()
  for (const f of walk(dir)) for (const t of readJsonl(f)) res.set(t.id, t)
  return res
}

function main(){
  const oldDir = process.argv[2]
  const newDir = process.argv[3]
  if (!oldDir || !newDir) {
    console.error('Usage: pnpm ontology:diff <oldDir> <newDir>')
    process.exit(1)
  }
  const A = load(oldDir)
  const B = load(newDir)

  const added: string[] = []
  const removed: string[] = []
  const moved: string[] = []

  for (const id of B.keys()) if (!A.has(id)) added.push(id)
  for (const id of A.keys()) if (!B.has(id)) removed.push(id)
  for (const id of A.keys()) {
    const a = A.get(id)!
    const b = B.get(id)
    if (!b) continue
    if ((a.parent || null) !== (b.parent || null)) moved.push(id)
  }

  console.log(`Added: ${added.length}`)
  added.slice(0,50).forEach(id => console.log('  +', id))
  console.log(`Removed: ${removed.length}`)
  removed.slice(0,50).forEach(id => console.log('  -', id))
  console.log(`Moved: ${moved.length}`)
  moved.slice(0,50).forEach(id => console.log('  ~', id))

  if (removed.length > 0) process.exit(1)
}

main()
