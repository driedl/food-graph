import Database from 'better-sqlite3'
import path from 'node:path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import { env } from '@nutrition/config'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const DATA_DIR = path.dirname(env.DB_PATH)
const DB_FILE = env.DB_PATH

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true })

console.log('[api] Connecting to database:', DB_FILE)
export const db = new Database(DB_FILE)
db.pragma('journal_mode = WAL')

function copyETLArtifact() {
  const src = env.ETL_DB_PATH
  const dst = env.DB_PATH
  
  if (!fs.existsSync(src)) {
    throw new Error(`[api] ETL artifact not found at ${src}. Run ETL compile first.`)
  }
  
  console.log(`[api] Auto-copying ETL artifact: ${src} -> ${dst}`)
  
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
  
  console.log('[api] ETL artifact copied successfully')
}

function tableExists(name: string): boolean {
  const row = db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name=?").get(name)
  return !!row
}

function getMetaVersion(): number | null {
  try {
    if (!tableExists('meta')) return null
    const row = db.prepare("SELECT val FROM meta WHERE key='schema_version'").get() as { val?: string } | undefined
    return row?.val ? Number(row.val) : null
  } catch { return null }
}

function getUserVersion(): number | null {
  try {
    const row = db.prepare('PRAGMA user_version').get() as { user_version?: number }
    return typeof row?.user_version === 'number' ? row.user_version : null
  } catch { return null }
}

function getArtifactAge(): number | null {
  try {
    if (!tableExists('meta')) return null
    const row = db.prepare("SELECT val FROM meta WHERE key='built_at'").get() as { val?: string } | undefined
    if (!row?.val) return null
    
    const builtAt = new Date(row.val).getTime()
    const now = Date.now()
    return Math.floor((now - builtAt) / (1000 * 60 * 60 * 24)) // days
  } catch { return null }
}

export function verifyGraphArtifact() {
  // Basic presence checks
  const requiredTables = ['nodes', 'taxa_fts', 'tp_fts', 'part_def', 'has_part', 'taxon_part_nodes']
  const missing = requiredTables.filter(t => !tableExists(t))
  if (missing.length) {
    if (env.AUTO_COPY_ETL_DB === 'true') {
      console.log(`[api] Graph DB missing required tables: ${missing.join(', ')}. Auto-copying from ETL...`)
      copyETLArtifact()
      // Reconnect to the copied database
      db.close()
      const newDb = new Database(env.DB_PATH)
      Object.assign(db, newDb)
      db.pragma('journal_mode = WAL')
      // Re-run verification on the copied database
      return verifyGraphArtifact()
    } else {
      throw new Error(
        `[api] Graph DB is missing required tables: ${missing.join(', ')}. ` +
        `Rebuild via ETL and copy the artifact to ${env.DB_PATH}.`
      )
    }
  }

  // Version checks
  const metaVer = getMetaVersion()
  const pragmaVer = getUserVersion()
  const ver = metaVer ?? pragmaVer
  if (ver == null) {
    if (env.AUTO_COPY_ETL_DB === 'true') {
      console.log('[api] Graph DB has no schema version. Auto-copying from ETL...')
      copyETLArtifact()
      // Reconnect and re-verify
      db.close()
      const newDb = new Database(env.DB_PATH)
      Object.assign(db, newDb)
      db.pragma('journal_mode = WAL')
      return verifyGraphArtifact()
    } else {
      throw new Error(
        `[api] Graph DB has no schema version (meta.schema_version or PRAGMA user_version). ` +
        `Rebuild via ETL >= v${env.MIN_GRAPH_SCHEMA_VERSION} and copy the artifact.`
      )
    }
  }
  if (ver < env.MIN_GRAPH_SCHEMA_VERSION) {
    if (env.AUTO_COPY_ETL_DB === 'true') {
      console.log(`[api] Graph DB schema_version=${ver} is below API requirement=${env.MIN_GRAPH_SCHEMA_VERSION}. Auto-copying from ETL...`)
      copyETLArtifact()
      // Reconnect and re-verify
      db.close()
      const newDb = new Database(env.DB_PATH)
      Object.assign(db, newDb)
      db.pragma('journal_mode = WAL')
      return verifyGraphArtifact()
    } else {
      throw new Error(
        `[api] Graph DB schema_version=${ver} is below API requirement=${env.MIN_GRAPH_SCHEMA_VERSION}. ` +
        `Rebuild via ETL and copy the new artifact.`
      )
    }
  }
  
  const builtAt = tableExists('meta')
    ? (db.prepare("SELECT val FROM meta WHERE key='built_at'").get() as { val?: string } | undefined)?.val
    : undefined
  const age = getArtifactAge()
  const ageWarning = age && age > 7 ? ` (⚠️ ${age} days old)` : ''
  
  console.log(`[api] Graph DB verified (schema_version=${ver}${builtAt ? `, built_at=${builtAt}` : ''}${ageWarning})`)
  
  // Warning for old artifacts in development
  if (env.NODE_ENV === 'development' && age && age > 7) {
    console.warn(`[api] Graph artifact is ${age} days old. Consider rebuilding with ETL for latest changes.`)
  }
}
