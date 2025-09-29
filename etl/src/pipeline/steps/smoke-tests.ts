#!/usr/bin/env tsx
import Database from 'better-sqlite3'
import fs from 'node:fs'
import path from 'node:path'
import { composeFoodState, type ComposeInput } from '../../../../packages/shared/src/index.js'

type SmokeTestCase = {
  name: string
  taxonId: string
  partId: string
  transforms: { id: string; params?: Record<string, unknown> }[]
}

export function runSmokeTests(dbPath: string, smokeTestsPath: string): boolean {
  console.log('🧪 Running smoke tests...')
  
  try {
    // Check if smoke tests file exists
    if (!fs.existsSync(smokeTestsPath)) {
      console.log(`   • Smoke tests file not found: ${smokeTestsPath}`)
      console.log(`   • Skipping smoke tests (optional)`)
      return true // Don't fail the build if smoke tests are missing
    }

    // Check if database exists
    if (!fs.existsSync(dbPath)) {
      console.log(`   • Database not found at ${dbPath}`)
      console.log(`   • Cannot run smoke tests without database`)
      return false
    }

    const db = new Database(dbPath)
    const cases: SmokeTestCase[] = JSON.parse(fs.readFileSync(smokeTestsPath, 'utf-8'))

    let pass = 0
    let fail = 0
    const failures: string[] = []

    for (const testCase of cases) {
      const input: ComposeInput = {
        taxonId: testCase.taxonId,
        partId: testCase.partId,
        transforms: testCase.transforms
      }

      const result = composeFoodState(db as any, input)
      
      if (result.errors.length === 0) {
        pass++
        console.log(`   ✅ ${testCase.name} -> ${result.id}`)
      } else {
        fail++
        const errorMsg = `${testCase.name}: ${result.errors.join('; ')}`
        failures.push(errorMsg)
        console.log(`   ❌ ${errorMsg}`)
      }
    }

    db.close()

    console.log(`   • Summary: ${pass} passed, ${fail} failed`)
    
    if (fail > 0) {
      console.log(`   • Failed test cases:`)
      failures.forEach(failure => {
        console.log(`     - ${failure}`)
      })
      return false
    }

    return true

  } catch (error) {
    console.log(`   • Smoke tests execution failed: ${error}`)
    return false
  }
}

function main() {
  const repoRoot = process.cwd().replace('/etl', '')
  const dbPath = path.resolve(repoRoot, 'etl/dist/database/graph.dev.sqlite')
  const smokeTestsPath = path.resolve(repoRoot, 'data/tests/smoke/edible_paths.json')
  
  const success = runSmokeTests(dbPath, smokeTestsPath)
  process.exit(success ? 0 : 1)
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main()
}
