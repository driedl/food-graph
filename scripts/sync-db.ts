#!/usr/bin/env tsx
import fs from 'node:fs'
import path from 'node:path'
import { env } from '@nutrition/config'

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
    console.log(`✅ Copied: ${s} -> ${d}`)
  } else {
    console.log(`⚠️  Source not found: ${s}`)
  }
}

console.log(`🔄 [sync-db] Copying ETL database from ETL to API...`)
console.log(`📂 Source: ${src}`)
console.log(`📂 Destination: ${dst}`)

copyIfExists(src, dst)
copyIfExists(`${src}-wal`, `${dst}-wal`)
copyIfExists(`${src}-shm`, `${dst}-shm`)

console.log('✅ [sync-db] Database sync completed!')
