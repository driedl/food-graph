import Database from 'better-sqlite3'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { ulid } from 'ulid'
import { env } from '@nutrition/config'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA_DIR = path.dirname(env.DB_PATH)
const DB_FILE = env.DB_PATH

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true })

export const db = new Database(DB_FILE)
db.pragma('journal_mode = WAL')

export function migrate() {
  db.exec(`CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY);`)
  const get = db.prepare('SELECT max(version) as v FROM schema_version').get() as { v: number | null }
  const current = get.v ?? 0
  const files = fs.readdirSync(path.join(__dirname, '..', 'migrations')).sort()
  let applied = 0
  for (const f of files) {
    const ver = Number(f.split('_')[0])
    if (ver > current) {
      const sql = fs.readFileSync(path.join(__dirname, '..', 'migrations', f), 'utf-8')
      db.exec(sql)
      db.prepare('INSERT INTO schema_version(version) VALUES (?)').run(ver)
      applied++
    }
  }
  if (applied) console.log(`[api] migrations applied: ${applied}`)
}

export function isEmpty() {
  const row = db.prepare('SELECT COUNT(*) as c FROM nodes').get() as { c: number }
  return row.c === 0
}

export function seedMinimal() {
  console.warn('⚠️  Using minimal seed data. Run "pnpm db:build" to load full ontology data.')
  
  const insertNode = db.prepare('INSERT INTO nodes (id, name, slug, rank, parent_id) VALUES (?, ?, ?, ?, ?)')
  const makeId = (slug: string) => slug + ':' + ulid().slice(0,6)

  const rootId = makeId('food')
  insertNode.run(rootId, 'Food', 'food', 'root', null)

  const kingdoms = [
    ['plant', 'Plant', 'kingdom'],
    ['animal', 'Animal', 'kingdom'],
    ['fungi', 'Fungi', 'kingdom'],
    ['microbe', 'Microbe', 'kingdom'],
    ['mineral', 'Mineral', 'kingdom'],
  ] as const

  for (const [slug, name, rank] of kingdoms) {
    insertNode.run(makeId(slug), name, slug, rank, rootId)
  }

  // seed a few attributes
  const attrs = ['process','style','fat_class','fat_pct','lean_pct','salt_level','refinement','enrichment','species','color','variety']
  const insertAttr = db.prepare('INSERT OR IGNORE INTO attr_def (attr, kind) VALUES (?, ?)')
  for (const a of attrs) insertAttr.run(a, 'categorical')
}
