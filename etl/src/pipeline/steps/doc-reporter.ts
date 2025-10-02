#!/usr/bin/env tsx
import { writeFileSync, mkdirSync, existsSync } from 'fs'
import path, { join, dirname, resolve } from 'path'
import Database from 'better-sqlite3'

interface TaxonNode {
  id: string
  parent?: string
  rank: string
  display_name: string
  latin_name: string
  aliases: string[]
}

interface DocFile {
  id: string
  rank: string
  latin_name: string
  display_name: string
  file_path: string
}

interface RankStats {
  rank: string
  total: number
  documented: number
  fillRate: number
  missing: TaxonNode[]
}

interface DocReport {
  generatedAt: string
  summary: {
    totalTaxa: number
    totalDocumented: number
    overallFillRate: number
  }
  byRank: RankStats[]
  missingByRank: { [rank: string]: TaxonNode[] }
}

export class DocumentationReporter {
  private dbPath: string
  private reportsDir: string

  constructor(dbPath?: string, reportsDir?: string) {
    // Default to workspace-relative paths
    const workspaceRoot = process.cwd().replace('/etl', '')
    this.dbPath = dbPath || resolve(workspaceRoot, 'etl/dist/database/graph.dev.sqlite')
    this.reportsDir = reportsDir || resolve(workspaceRoot, 'etl/reports')
  }

  async generateReport(): Promise<DocReport> {
    console.log('📊 Generating documentation report...')
    
    // Ensure reports directory exists
    if (!existsSync(this.reportsDir)) {
      mkdirSync(this.reportsDir, { recursive: true })
    }

    // Load all taxa from database
    const allTaxa = await this.loadAllTaxaFromDB()
    
    // Load all documentation from database
    const allDocs = await this.loadAllDocsFromDB()
    
    // Create lookup map for documented taxa
    const documentedIds = new Set(allDocs.map(doc => doc.id))
    
    // Group taxa by rank
    const taxaByRank = this.groupTaxaByRank(allTaxa)
    
    // Calculate statistics for each rank
    const byRank: RankStats[] = []
    const missingByRank: { [rank: string]: TaxonNode[] } = {}
    
    for (const [rank, taxa] of Object.entries(taxaByRank)) {
      const documented = taxa.filter(taxon => documentedIds.has(taxon.id))
      const missing = taxa.filter(taxon => !documentedIds.has(taxon.id))
      const fillRate = taxa.length > 0 ? (documented.length / taxa.length) * 100 : 0
      
      byRank.push({
        rank,
        total: taxa.length,
        documented: documented.length,
        fillRate: Math.round(fillRate * 100) / 100,
        missing
      })
      
      if (missing.length > 0) {
        missingByRank[rank] = missing
      }
    }
    
    // Sort by rank hierarchy (root -> domain -> kingdom -> phylum -> class -> order -> suborder -> family -> genus -> species -> variety -> cultivar -> form)
    const rankOrder = ['root', 'domain', 'kingdom', 'phylum', 'class', 'order', 'suborder', 'family', 'genus', 'species', 'variety', 'cultivar', 'form']
    byRank.sort((a, b) => {
      const aIndex = rankOrder.indexOf(a.rank)
      const bIndex = rankOrder.indexOf(b.rank)
      return aIndex - bIndex
    })
    
    // Calculate overall statistics
    const totalTaxa = allTaxa.length
    const totalDocumented = allDocs.length
    const overallFillRate = totalTaxa > 0 ? (totalDocumented / totalTaxa) * 100 : 0
    
    const report: DocReport = {
      generatedAt: new Date().toISOString(),
      summary: {
        totalTaxa,
        totalDocumented,
        overallFillRate: Math.round(overallFillRate * 100) / 100
      },
      byRank,
      missingByRank
    }
    
    // Write report files
    console.log('Writing report files...')
    await this.writeReportFiles(report)
    console.log('Report files written successfully')
    
    console.log(`✅ Documentation report generated`)
    console.log(`📈 Overall fill rate: ${overallFillRate.toFixed(1)}% (${totalDocumented}/${totalTaxa})`)
    
    return report
  }

  private async loadAllTaxaFromDB(): Promise<TaxonNode[]> {
    const db = new Database(this.dbPath)
    
    const taxa = db.prepare(`
      SELECT id, parent_id as parent, rank, name as display_name, name as latin_name
      FROM nodes
      ORDER BY id
    `).all() as TaxonNode[]
    
    db.close()
    return taxa
  }

  private async loadAllDocsFromDB(): Promise<DocFile[]> {
    const db = new Database(this.dbPath)
    
    const docs = db.prepare(`
      SELECT 
        td.taxon_id as id,
        n.rank,
        n.name as latin_name,
        n.name as display_name,
        '' as file_path
      FROM taxon_doc td
      JOIN nodes n ON td.taxon_id = n.id
      ORDER BY td.taxon_id
    `).all() as DocFile[]
    
    db.close()
    return docs
  }

  private groupTaxaByRank(taxa: TaxonNode[]): { [rank: string]: TaxonNode[] } {
    const grouped: { [rank: string]: TaxonNode[] } = {}
    
    for (const taxon of taxa) {
      if (!grouped[taxon.rank]) {
        grouped[taxon.rank] = []
      }
      grouped[taxon.rank].push(taxon)
    }
    
    return grouped
  }

  private async writeReportFiles(report: DocReport): Promise<void> {
    console.log('Reports directory:', this.reportsDir)
    
    // Write JSON report
    const jsonPath = join(this.reportsDir, 'doc-report.json')
    console.log('Writing JSON to:', jsonPath)
    writeFileSync(jsonPath, JSON.stringify(report, null, 2))
    
    // Write Markdown report
    const mdPath = join(this.reportsDir, 'doc-report.md')
    console.log('Writing MD to:', mdPath)
    const mdContent = this.generateMarkdownReport(report)
    writeFileSync(mdPath, mdContent)
    
    // Write missing taxa list (for easy copy-paste)
    const missingPath = join(this.reportsDir, 'missing-docs.txt')
    console.log('Writing missing to:', missingPath)
    const missingContent = this.generateMissingTaxaList(report)
    writeFileSync(missingPath, missingContent)
  }

  private generateMarkdownReport(report: DocReport): string {
    let md = `# Documentation Coverage Report\n\n`
    md += `**Generated:** ${new Date(report.generatedAt).toLocaleString()}\n\n`
    
    md += `## Summary\n\n`
    md += `- **Total Taxa:** ${report.summary.totalTaxa.toLocaleString()}\n`
    md += `- **Documented:** ${report.summary.totalDocumented.toLocaleString()}\n`
    md += `- **Overall Fill Rate:** ${report.summary.overallFillRate}%\n\n`
    
    // Add progress bar visualization
    const progressBar = this.generateProgressBar(report.summary.overallFillRate)
    md += `**Progress:** ${progressBar}\n\n`
    
    md += `## Coverage by Rank\n\n`
    md += `| Rank | Total | Documented | Fill Rate | Missing |\n`
    md += `|------|-------|------------|-----------|----------|\n`
    
    for (const rank of report.byRank) {
      const missingCount = rank.missing.length
      const missingText = missingCount > 0 ? `${missingCount}` : '0'
      const fillRateText = rank.fillRate === 100 ? '✅ 100%' : 
                          rank.fillRate >= 80 ? `🟢 ${rank.fillRate}%` :
                          rank.fillRate >= 50 ? `🟡 ${rank.fillRate}%` :
                          rank.fillRate > 0 ? `🟠 ${rank.fillRate}%` : `🔴 ${rank.fillRate}%`
      md += `| ${rank.rank} | ${rank.total.toLocaleString()} | ${rank.documented.toLocaleString()} | ${fillRateText} | ${missingText} |\n`
    }
    
    md += `\n## Missing Documentation by Rank\n\n`
    
    for (const rank of report.byRank) {
      if (rank.missing.length > 0) {
        const rankTitle = rank.rank.charAt(0).toUpperCase() + rank.rank.slice(1)
        const missingCount = rank.missing.length
        md += `### ${rankTitle} (${missingCount} missing)\n\n`
        
        // Group by kingdom for better organization
        const groupedByKingdom = this.groupMissingByKingdom(rank.missing)
        for (const [kingdom, taxa] of Object.entries(groupedByKingdom)) {
          if (Object.keys(groupedByKingdom).length > 1) {
            md += `#### ${kingdom}\n\n`
          }
          for (const taxon of taxa) {
            md += `- \`${taxon.id}\` - ${taxon.display_name} (${taxon.latin_name})\n`
          }
          if (Object.keys(groupedByKingdom).length > 1) {
            md += `\n`
          }
        }
        md += `\n`
      }
    }
    
    return md
  }

  private generateMissingTaxaList(report: DocReport): string {
    let content = `# Missing Documentation Taxa IDs\n\n`
    content += `Generated: ${new Date(report.generatedAt).toLocaleString()}\n\n`
    
    for (const rank of report.byRank) {
      if (rank.missing.length > 0) {
        content += `## ${rank.rank.charAt(0).toUpperCase() + rank.rank.slice(1)} (${rank.missing.length} missing)\n\n`
        for (const taxon of rank.missing) {
          content += `${taxon.id}\n`
        }
        content += `\n`
      }
    }
    
    return content
  }

  private generateProgressBar(percentage: number): string {
    const filled = Math.round(percentage / 5) // 20 characters max
    const empty = 20 - filled
    return `[${'█'.repeat(filled)}${'░'.repeat(empty)}] ${percentage.toFixed(1)}%`
  }

  private groupMissingByKingdom(taxa: TaxonNode[]): { [kingdom: string]: TaxonNode[] } {
    const grouped: { [kingdom: string]: TaxonNode[] } = {}
    
    for (const taxon of taxa) {
      // Extract kingdom from taxon ID (e.g., "tx:animalia:..." -> "animalia")
      const kingdom = taxon.id.split(':')[1] || 'unknown'
      if (!grouped[kingdom]) {
        grouped[kingdom] = []
      }
      grouped[kingdom].push(taxon)
    }
    
    // Sort kingdoms alphabetically
    const sorted: { [kingdom: string]: TaxonNode[] } = {}
    Object.keys(grouped).sort().forEach(kingdom => {
      sorted[kingdom] = grouped[kingdom]
    })
    
    return sorted
  }
}

// CLI execution
if (import.meta.url === `file://${process.argv[1]}`) {
  // Parse command line arguments
  const args = process.argv.slice(2)
  const dbPathIndex = args.indexOf('--db-path')
  const reportsDirIndex = args.indexOf('--reports-dir')
  
  const dbPath = dbPathIndex !== -1 ? args[dbPathIndex + 1] : undefined
  const reportsDir = reportsDirIndex !== -1 ? args[reportsDirIndex + 1] : undefined
  
  const reporter = new DocumentationReporter(dbPath, reportsDir)
  reporter.generateReport().catch(console.error)
}
