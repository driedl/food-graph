#!/usr/bin/env tsx
import { Database } from 'better-sqlite3'
import { pipelineConfig } from '../config.js'

const DB_PATH = pipelineConfig.outputs.database

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

function main() {
  const success = verifyDatabase()
  process.exit(success ? 0 : 1)
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main()
}
