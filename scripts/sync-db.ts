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

function copyIfExists(s: string, d: string): boolean {
  if (fs.existsSync(s)) {
    try {
      fs.mkdirSync(path.dirname(d), { recursive: true })
      fs.copyFileSync(s, d)
      console.log(`✅ Copied: ${s} -> ${d}`)
      return true
    } catch (error) {
      console.error(`❌ Failed to copy ${s}: ${error}`)
      return false
    }
  } else {
    console.log(`⚠️  Source not found: ${s}`)
    return false
  }
}

console.log(`🔄 [sync-db] Copying ETL database from ETL to API...`)
console.log(`📂 Source: ${src}`)
console.log(`📂 Destination: ${dst}`)

// Check if source database exists
if (!fs.existsSync(src)) {
  console.error(`❌ ETL database not found at ${src}. Run ETL compile first.`)
  process.exit(1)
}

// Copy main database file
const mainCopied = copyIfExists(src, dst)
if (!mainCopied) {
  console.error('❌ Failed to copy main database file')
  process.exit(1)
}

// Copy WAL/SHM files if they exist
copyIfExists(`${src}-wal`, `${dst}-wal`)
copyIfExists(`${src}-shm`, `${dst}-shm`)

console.log('✅ [sync-db] Database sync completed!')
