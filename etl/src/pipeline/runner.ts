import { spawn } from 'child_process'
import { promisify } from 'util'
import chalk from 'chalk'
import ora from 'ora'
import { PipelineStep, BuildReport } from './types.js'
import { pipelineConfig as config } from './config.js'

export class PipelineRunner {
  private startTime = Date.now()
  private report: BuildReport = {
    success: false,
    duration: 0,
    steps: [],
    summary: { taxaCount: 0, synonymsCount: 0, docsCount: 0, ftsCount: 0 }
  }

  async run(stepsToRun?: string[], skipSteps?: string[]): Promise<BuildReport> {
    console.log(chalk.cyan('🌱 Food Graph ETL Pipeline'))
    console.log(chalk.cyan('=' * 50))
    console.log()

    const steps = this.filterSteps(config.steps, stepsToRun, skipSteps)
    
    for (const step of steps) {
      const stepStartTime = Date.now()
      const spinner = ora({
        text: `Step ${this.getStepNumber(step.id)}/${steps.length}: ${step.name}`,
        color: 'cyan'
      }).start()

      try {
        const success = await this.runStep(step)
        const duration = Date.now() - stepStartTime
        
        this.report.steps.push({
          id: step.id,
          success,
          duration,
          output: success ? 'Completed successfully' : 'Failed'
        })

        if (success) {
          spinner.succeed(chalk.green(`✅ ${step.name}`))
        } else {
          spinner.fail(chalk.red(`❌ ${step.name}`))
          this.report.success = false
          this.report.duration = Date.now() - this.startTime
          return this.report
        }
      } catch (error) {
        const duration = Date.now() - stepStartTime
        spinner.fail(chalk.red(`❌ ${step.name}`))
        
        this.report.steps.push({
          id: step.id,
          success: false,
          duration,
          error: error instanceof Error ? error.message : String(error)
        })
        
        this.report.success = false
        this.report.duration = Date.now() - this.startTime
        return this.report
      }
    }

    // Generate summary
    await this.generateSummary()
    
    this.report.success = true
    this.report.duration = Date.now() - this.startTime
    
    console.log()
    console.log(chalk.cyan('📊 COMPILATION SUMMARY'))
    console.log(chalk.cyan('=' * 50))
    console.log(chalk.green('✅ Build completed successfully'))
    console.log(`📈 Total nodes: ${this.report.summary.taxaCount}`)
    console.log(`🏷️  Total synonyms: ${this.report.summary.synonymsCount}`)
    console.log(`📚 Total documentation records: ${this.report.summary.docsCount}`)
    console.log(`🔍 Total FTS entries: ${this.report.summary.ftsCount}`)
    console.log(`⏱️  Execution time: ${(this.report.duration / 1000).toFixed(2)}s`)
    console.log(chalk.green('🎉 Pipeline completed successfully!'))
    
    return this.report
  }

  private filterSteps(steps: PipelineStep[], run?: string[], skip?: string[]): PipelineStep[] {
    let filtered = steps

    if (run && run.length > 0) {
      filtered = filtered.filter(step => run.includes(step.id))
    }

    if (skip && skip.length > 0) {
      filtered = filtered.filter(step => !skip.includes(step.id))
    }

    // Add dependencies for selected steps
    const selectedIds = new Set(filtered.map(s => s.id))
    const toAdd = new Set<string>()
    
    for (const step of filtered) {
      if (step.dependencies) {
        for (const dep of step.dependencies) {
          if (!selectedIds.has(dep)) {
            toAdd.add(dep)
          }
        }
      }
    }

    for (const depId of toAdd) {
      const depStep = steps.find(s => s.id === depId)
      if (depStep) {
        filtered.unshift(depStep)
      }
    }

    return filtered
  }

  private getStepNumber(stepId: string): number {
    return config.steps.findIndex(s => s.id === stepId) + 1
  }

  private async runStep(step: PipelineStep): Promise<boolean> {
    return new Promise((resolve) => {
      const args = step.args || []
      const child = spawn(step.command, args, {
        stdio: ['inherit', 'pipe', 'pipe'],
        cwd: process.cwd()
      })

      let stdout = ''
      let stderr = ''

      child.stdout?.on('data', (data) => {
        stdout += data.toString()
      })

      child.stderr?.on('data', (data) => {
        stderr += data.toString()
      })

      child.on('close', (code) => {
        resolve(code === 0)
      })

      child.on('error', () => {
        resolve(false)
      })
    })
  }

  private async generateSummary(): Promise<void> {
    try {
      const { Database } = await import('better-sqlite3')
      const db = new Database(config.outputs.database)
      
      const nodeCount = db.prepare('SELECT COUNT(*) as count FROM nodes').get() as { count: number }
      const synonymCount = db.prepare('SELECT COUNT(*) as count FROM synonyms').get() as { count: number }
      const docsCount = db.prepare('SELECT COUNT(*) as count FROM taxon_doc').get() as { count: number }
      const ftsCount = db.prepare('SELECT COUNT(*) as count FROM nodes_fts').get() as { count: number }
      
      this.report.summary = {
        taxaCount: nodeCount.count,
        synonymsCount: synonymCount.count,
        docsCount: docsCount.count,
        ftsCount: ftsCount.count
      }
      
      db.close()
    } catch (error) {
      console.warn('Could not generate summary:', error)
    }
  }
}
