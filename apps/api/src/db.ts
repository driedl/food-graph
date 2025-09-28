import Database from 'better-sqlite3'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { ulid } from 'ulid'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rootEnvPath = path.resolve(process.cwd(), '.env')
if (fs.existsSync(rootEnvPath)) {
  // best-effort: load root .env in case index.ts wasn't the one to do it
  await import('dotenv/config')
}
const DB_PATH = process.env.DB_PATH ?? path.join(process.cwd(), '..', '..', 'data', 'builds', 'graph.dev.sqlite')
const DATA_DIR = path.dirname(DB_PATH)
const DB_FILE = DB_PATH

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true })

export const db = new Database(DB_FILE)
db.pragma('journal_mode = WAL')

export function migrate() {
  db.exec(`
  CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    rank TEXT NOT NULL,
    parent_id TEXT REFERENCES nodes(id) ON DELETE CASCADE
  );
  CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id);
  CREATE UNIQUE INDEX IF NOT EXISTS idx_nodes_slug_parent ON nodes(slug, parent_id);

  CREATE TABLE IF NOT EXISTS synonyms (
    node_id TEXT REFERENCES nodes(id) ON DELETE CASCADE,
    synonym TEXT NOT NULL,
    PRIMARY KEY (node_id, synonym)
  );

  CREATE TABLE IF NOT EXISTS node_attributes (
    node_id TEXT REFERENCES nodes(id) ON DELETE CASCADE,
    attr TEXT NOT NULL,
    val TEXT NOT NULL,
    PRIMARY KEY (node_id, attr, val)
  );

  CREATE TABLE IF NOT EXISTS attr_def (
    attr TEXT PRIMARY KEY,
    kind TEXT NOT NULL DEFAULT 'categorical'  -- numeric | boolean | categorical
  );
  `)
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
