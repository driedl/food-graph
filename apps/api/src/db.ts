import Database from 'better-sqlite3'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { env } from '@nutrition/config'

// API's own database location (where we copy the ETL2 database to)
const DB_PATH = env.DB_PATH
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA_DIR = path.dirname(DB_PATH)
const DB_FILE = DB_PATH

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true })

console.log('[api] Connecting to database:', DB_FILE)
let db = new Database(DB_FILE)
db.pragma('journal_mode = WAL')

// Export a getter that returns the current database instance
export { db }

function copyETLArtifact() {
  const src = env.ETL2_DB_PATH  // ETL2 source database
  const dst = DB_PATH           // API's own database location

  if (!fs.existsSync(src)) {
    throw new Error(`[api] ETL2 artifact not found at ${src}. Run ETL2 compile first.`)
  }

  console.log(`[api] Auto-copying ETL2 artifact: ${src} -> ${dst}`)

  // Ensure destination directory exists
  fs.mkdirSync(path.dirname(dst), { recursive: true })

  // Copy main database file
  fs.copyFileSync(src, dst)

  // Copy WAL/SHM files if they exist (for WAL mode)
  const walSrc = `${src}-wal`
  const shmSrc = `${src}-shm`
  const walDst = `${dst}-wal`
  const shmDst = `${dst}-shm`

  if (fs.existsSync(walSrc)) fs.copyFileSync(walSrc, walDst)
  if (fs.existsSync(shmSrc)) fs.copyFileSync(shmSrc, shmDst)

  console.log(`[api] ETL2 artifact copied successfully`)
}

function tableExists(name: string): boolean {
  const row = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name=?").get(name)
  return !!row
}


function getArtifactAge(): number | null {
  try {
    if (!tableExists('meta')) return null
    const row = db.prepare("SELECT val FROM meta WHERE key='build_time'").get() as { val?: string } | undefined
    if (!row?.val) return null

    const builtAt = new Date(row.val).getTime()
    const now = Date.now()
    return Math.floor((now - builtAt) / (1000 * 60 * 60 * 24)) // days
  } catch { return null }
}

export function verifyGraphArtifact() {
  // Basic presence checks
  const requiredTables = [
    'nodes',
    'part_def',
    'has_part',
    'taxon_doc',
    'taxon_part_nodes',
    'tpt_nodes',
    'search_content',
    'search_fts',
    'meta',
    'transform_def',
    'tpt_identity_steps',
    'taxon_ancestors'
  ]
  const missing = requiredTables.filter(t => !tableExists(t))
  if (missing.length) {
    if (env.AUTO_COPY_ETL_DB === 'true') {
      console.log(`[api] Graph DB missing required tables: ${missing.join(', ')}. Auto-copying from ETL2...`)
      copyETLArtifact()
      // Reconnect to the copied database
      db.close()
      db = new Database(DB_PATH)
      db.pragma('journal_mode = WAL')
      // Re-run verification on the copied database (but don't recurse)
      const missingAfterCopy = requiredTables.filter(t => !tableExists(t))
      if (missingAfterCopy.length) {
        throw new Error(
          `[api] Graph DB still missing required tables after copy: ${missingAfterCopy.join(', ')}. ` +
          `Source database may be incomplete.`
        )
      }
    } else {
      throw new Error(
        `[api] Graph DB is missing required tables: ${missing.join(', ')}. ` +
        `Rebuild via ETL2 and copy the artifact to ${DB_PATH}.`
      )
    }
  }

  // No hard schema-version enforcement for Stage-F artifacts.

  const builtAt = tableExists('meta')
    ? (db.prepare("SELECT val FROM meta WHERE key='build_time'").get() as { val?: string } | undefined)?.val
    : undefined
  const age = getArtifactAge()
  const ageWarning = age && age > 7 ? ` (⚠️ ${age} days old)` : ''

  console.log(`[api] Graph DB verified${builtAt ? ` (build_time=${builtAt})` : ''}${ageWarning}`)

  // Warning for old artifacts in development
  if (env.NODE_ENV === 'development' && age && age > 7) {
    console.warn(`[api] Graph artifact is ${age} days old. Consider rebuilding with ETL2 for latest changes.`)
  }
}
