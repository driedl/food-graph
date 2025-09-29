import Database from 'better-sqlite3'
import fs from 'node:fs'
import path from 'node:path'
import { composeFoodState } from '../lib/foodstate'
import { env } from '@nutrition/config'

type Case = {
  name: string
  taxonId: string
  partId: string
  transforms: { id: string; params?: Record<string,unknown> }[]
}

const DB = env.DB_PATH
const CASES = path.resolve(process.cwd(), 'data/ontology/smoke_tests/edible_paths.json')

if (!fs.existsSync(DB)) {
  console.error(`DB not found at ${DB}. Build it via the compiler first.`)
  process.exit(1)
}
if (!fs.existsSync(CASES)) {
  console.error(`Smoke tests file missing: ${CASES}`)
  process.exit(1)
}

const db = new Database(DB)
const cases: Case[] = JSON.parse(fs.readFileSync(CASES, 'utf-8'))

let pass = 0, fail = 0
for (const c of cases) {
  const res = composeFoodState(db as any, c)
  if (res.errors.length === 0) {
    pass++
    console.log(`✅ ${c.name} -> ${res.id}`)
  } else {
    fail++
    console.log(`❌ ${c.name} ->`, res.errors.join('; '))
  }
}
console.log(`\nSummary: ${pass} passed, ${fail} failed`)
process.exit(fail ? 1 : 0)
