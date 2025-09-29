#!/usr/bin/env tsx
import { Command } from 'commander'
import chalk from 'chalk'
import { PipelineRunner } from './runner.js'

const program = new Command()

program
  .name('etl-pipeline')
  .description('Food Graph ETL Pipeline')
  .version('1.0.0')

program
  .command('build')
  .description('Run the full ETL pipeline')
  .option('-s, --step <step>', 'Run only specific step(s)', (value) => value.split(','))
  .option('--skip <steps>', 'Skip specific step(s)', (value) => value.split(','))
  .option('--verbose', 'Verbose output')
  .action(async (options) => {
    const runner = new PipelineRunner()
    const report = await runner.run(options.step, options.skip)
    
    if (!report.success) {
      console.error(chalk.red('\n❌ Pipeline failed'))
      process.exit(1)
    }
  })

program
  .command('validate')
  .description('Run validation only')
  .action(async () => {
    const runner = new PipelineRunner()
    const report = await runner.run(['validate'])
    
    if (!report.success) {
      console.error(chalk.red('\n❌ Validation failed'))
      process.exit(1)
    }
  })

program
  .command('clean')
  .description('Clean build artifacts')
  .action(async () => {
    const { exec } = await import('child_process')
    const { promisify } = await import('util')
    const execAsync = promisify(exec)
    
    console.log(chalk.yellow('🧹 Cleaning build artifacts...'))
    
    try {
      await execAsync('rm -rf data/ontology/compiled/*')
      await execAsync('rm -rf etl/dist/database/*')
      console.log(chalk.green('✅ Clean completed'))
    } catch (error) {
      console.error(chalk.red('❌ Clean failed:'), error)
      process.exit(1)
    }
  })

// Handle direct execution
if (import.meta.url === `file://${process.argv[1]}`) {
  program.parse()
}
