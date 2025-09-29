#!/usr/bin/env tsx
import Database from 'better-sqlite3'
import path from 'node:path'
import { runSmokeTests } from './smoke-tests.js'

// Use absolute path to database
const DB_PATH = path.resolve(process.cwd().replace('/etl', ''), 'etl/dist/database/graph.dev.sqlite')

function verifyDatabase(): boolean {
  console.log('🔍 Verifying database integrity...')
  
  try {
    const db = new Database(DB_PATH)
    
    // Test basic connectivity
    const nodeCount = db.prepare('SELECT COUNT(*) as count FROM nodes').get() as { count: number }
    const ftsCount = db.prepare('SELECT COUNT(*) as count FROM nodes_fts').get() as { count: number }
    
    console.log(`   • Database connectivity: OK`)
    console.log(`   • Nodes: ${nodeCount.count}`)
    console.log(`   • FTS entries: ${ftsCount.count}`)
    
    // Test FTS search functionality
    const riceResults = db.prepare(`
      SELECT n.id, n.name, n.rank 
      FROM nodes n 
      JOIN nodes_fts fts ON n.rowid = fts.rowid 
      WHERE nodes_fts MATCH 'rice*' 
      LIMIT 3
    `).all() as Array<{ id: string; name: string; rank: string }>
    
    if (riceResults.length > 0) {
      console.log(`   • FTS search test: OK (found ${riceResults.length} rice results)`)
      console.log(`     - ${riceResults[0].name} (${riceResults[0].rank})`)
    } else {
      console.log(`   • FTS search test: FAILED (no rice results found)`)
      db.close()
      return false
    }
    
    db.close()
    return true
    
  } catch (error) {
    console.log(`   • Database verification: FAILED`)
    console.log(`     Error: ${error}`)
    return false
  }
}

function runAllVerification(): boolean {
  console.log('🔍 Running comprehensive verification...')
  console.log()
  
  // Step 1: Basic database verification
  const dbVerification = verifyDatabase()
  if (!dbVerification) {
    return false
  }
  
  console.log()
  
  // Step 2: Smoke tests for composition model
  const repoRoot = process.cwd().replace('/etl', '')
  const smokeTestsPath = path.resolve(repoRoot, 'data/tests/smoke/edible_paths.json')
  const smokeTestsPass = runSmokeTests(DB_PATH, smokeTestsPath)
  
  console.log()
  
  if (smokeTestsPass) {
    console.log('✅ All verification steps passed')
    return true
  } else {
    console.log('❌ Verification failed')
    return false
  }
}

function main() {
  const success = runAllVerification()
  process.exit(success ? 0 : 1)
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main()
}
