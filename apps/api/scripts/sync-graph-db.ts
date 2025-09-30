import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import 'dotenv/config'
import { env } from '@nutrition/config'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const src = env.ETL_DB_PATH
const dst = env.DB_PATH

if (!src || !dst) {
  console.error('ETL_DB_PATH and DB_PATH must be set in config')
  process.exit(1)
}

function copyIfExists(s: string, d: string) {
  if (fs.existsSync(s)) {
    fs.mkdirSync(path.dirname(d), { recursive: true })
    fs.copyFileSync(s, d)
    console.log(`copied: ${s} -> ${d}`)
  }
}

console.log(`[db:sync] Copying ETL artifact from ${src} to ${dst}`)

copyIfExists(src, dst)
copyIfExists(`${src}-wal`, `${dst}-wal`)
copyIfExists(`${src}-shm`, `${dst}-shm`)

console.log('[db:sync] Done.')
