#!/usr/bin/env tsx
import { spawn } from 'child_process'

async function runCommand(command: string, args: string[] = [], cwd: string = process.cwd()): Promise<boolean> {
  console.log(`Running: ${command} ${args.join(' ')}`)
  
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      stdio: 'inherit',
      cwd
    })

    child.on('close', (code: number | null) => {
      resolve(code === 0)
    })

    child.on('error', (error: Error) => {
      console.error(`Error running ${command}:`, error)
      resolve(false)
    })
  })
}

async function main() {
  console.log('🌱 Food Graph ETL Pipeline')
  console.log('='.repeat(50))
  console.log()

  const repoRoot = process.cwd().replace('/etl', '')
  console.log(`Running from repo root: ${repoRoot}`)

  const steps = [
    {
      name: 'Validate ontology data',
      command: 'python3',
      args: ['etl/python/validate_taxa.py', '--taxa-root', 'data/ontology/taxa']
    },
    {
      name: 'Compile taxonomic data',
      command: 'python3', 
      args: ['etl/python/compile_taxa.py', '--taxa-root', 'data/ontology/taxa', '--out', 'etl/dist/compiled/taxa/taxa.jsonl']
    },
    {
      name: 'Compile documentation',
      command: 'python3',
      args: ['etl/python/compile_docs.py', '--taxa-root', 'data/ontology/taxa', '--compiled-taxa', 'etl/dist/compiled/taxa/taxa.jsonl', '--out', 'etl/dist/compiled/docs.jsonl']
    },
    {
      name: 'Build database',
      command: 'python3',
      args: ['etl/python/compile.py', '--in', './etl/dist/compiled', '--out', './etl/dist/database/graph.dev.sqlite']
    },
    {
      name: 'Verify database and run smoke tests',
      command: 'tsx',
      args: ['etl/src/pipeline/steps/verify.ts']
    }
  ]

  for (let i = 0; i < steps.length; i++) {
    const step = steps[i]
    console.log(`Step ${i + 1}/${steps.length}: ${step.name}`)
    
    const success = await runCommand(step.command, step.args, repoRoot)
    
    if (success) {
      console.log(`✅ ${step.name}`)
    } else {
      console.log(`❌ ${step.name}`)
      console.log('Pipeline failed')
      process.exit(1)
    }
    console.log()
  }

  console.log('🎉 Pipeline completed successfully!')
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error)
}
