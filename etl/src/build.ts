#!/usr/bin/env tsx
import { spawn } from 'child_process'

async function runCommand(command: string, args: string[] = [], cwd: string = process.cwd()): Promise<boolean> {
  console.log(`Running: ${command} ${args.join(' ')}`)
  
  return new Promise((resolve) => {
    const child = spawn(command, args, {
      stdio: 'inherit',
      cwd
    })

    child.on('close', (code) => {
      resolve(code === 0)
    })

    child.on('error', (error) => {
      console.error(`Error running ${command}:`, error)
      resolve(false)
    })
  })
}

async function main() {
  console.log('🌱 Food Graph ETL Pipeline')
  console.log('=' * 50)
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
      args: ['etl/python/compile_taxa.py', '--taxa-root', 'data/ontology/taxa', '--out', 'data/ontology/compiled/taxa/taxa.jsonl']
    },
    {
      name: 'Compile documentation',
      command: 'python3',
      args: ['etl/python/compile_docs.py', '--taxa-root', 'data/ontology/taxa', '--compiled-taxa', 'data/ontology/compiled/taxa/taxa.jsonl', '--out', 'data/ontology/compiled/docs.jsonl']
    },
    {
      name: 'Build database',
      command: 'python3',
      args: ['etl/python/compile.py', '--in', './data/ontology/compiled', '--out', './data/builds/graph.dev.sqlite']
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
