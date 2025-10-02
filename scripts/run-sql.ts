#!/usr/bin/env tsx
import 'dotenv/config'
import { env } from '@nutrition/config'
import Database from 'better-sqlite3'
import { argv, exit, stdin } from 'node:process'

// Determine the correct DB_PATH based on FOOD_DB_SOURCE (same logic as apps/api/src/db.ts)
const getDbPath = () => {
  const src = env.FOOD_DB_SOURCE
  const path = src === 'mise' ? env.FOOD_DB_PATH_MISE : env.FOOD_DB_PATH_ETL
  if (!path) throw new Error(`No DB path for source ${src}`)
  return path
}

const db = new Database(getDbPath())
db.pragma('journal_mode = WAL')

const help = `Usage:
  pnpm sql "SELECT * FROM nodes LIMIT 3"
  pnpm sql --repl
  echo 'SELECT count(*) c FROM nodes;' | pnpm sql --stdin

Database: ${getDbPath()}
Source: ${env.FOOD_DB_SOURCE}
`

async function main() {
  if (argv.includes('--help')) { console.log(help); return }

  const useRepl = argv.includes('--repl')
  const useStdin = argv.includes('--stdin')
  
  if (useRepl) {
    console.log(`SQLite REPL (better-sqlite3) → ${env.DB_PATH}\nType SQL and press Enter. Ctrl+C to exit.`)
    const readline = await import('node:readline/promises')
    const rl = readline.createInterface({ input: stdin, output: process.stdout })
    while (true) {
      const q = await rl.question('sql> ')
      if (!q.trim()) continue
      try { 
        const rows = db.prepare(q).all()
        console.log(JSON.stringify(rows, null, 2)) 
      }
      catch (e: any) { console.error('Error:', e.message) }
    }
  } else if (useStdin) {
    let sql = ''
    for await (const chunk of stdin) sql += chunk
    const rows = db.prepare(sql).all()
    console.log(JSON.stringify(rows, null, 2))
  } else {
    const q = argv.slice(2).join(' ')
    if (!q) { console.log(help); exit(1) }
    const rows = db.prepare(q).all()
    console.log(JSON.stringify(rows, null, 2))
  }
}

main()
