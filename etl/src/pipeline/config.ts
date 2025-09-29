import { PipelineConfig } from './types.js'
import path from 'path'

export const pipelineConfig: PipelineConfig = {
  steps: [
    {
      id: 'validate',
      name: 'Validate ontology data',
      description: 'Validate taxonomic data integrity and consistency',
      command: 'python3',
      args: ['etl/python/validate_taxa.py', '--taxa-root', 'data/ontology/taxa']
    },
    {
      id: 'compile-taxa',
      name: 'Compile taxonomic data',
      description: 'Compile taxonomic hierarchy into JSONL format',
      command: 'python3',
      args: ['etl/python/compile_taxa.py', '--taxa-root', 'data/ontology/taxa', '--out', 'etl/dist/compiled/taxa/taxa.jsonl'],
      dependencies: ['validate']
    },
    {
      id: 'compile-docs',
      name: 'Compile documentation',
      description: 'Compile taxonomic documentation from .tx.md files',
      command: 'python3',
      args: ['etl/python/compile_docs.py', '--taxa-root', 'data/ontology/taxa', '--compiled-taxa', 'etl/dist/compiled/taxa/taxa.jsonl', '--out', 'etl/dist/compiled/docs.jsonl'],
      dependencies: ['compile-taxa']
    },
    {
      id: 'build-db',
      name: 'Build database',
      description: 'Compile ontology data into SQLite database with FTS',
      command: 'python3',
      args: ['etl/python/compile.py', '--in', './etl/dist/compiled', '--out', './etl/dist/database/graph.dev.sqlite'],
      dependencies: ['compile-docs']
    },
    {
      id: 'verify',
      name: 'Verify build',
      description: 'Verify database integrity and search functionality',
      command: 'tsx',
      args: ['etl/src/pipeline/steps/verify.ts'],
      dependencies: ['build-db']
    },
    {
      id: 'doc-report',
      name: 'Generate documentation report',
      description: 'Generate documentation coverage report and missing taxa list',
      command: 'tsx',
      args: [
        'etl/src/pipeline/steps/doc-reporter.ts',
        '--db-path', path.resolve(process.cwd().replace('/etl', ''), 'etl/dist/database/graph.dev.sqlite'),
        '--reports-dir', path.resolve(process.cwd().replace('/etl', ''), 'etl/reports')
      ],
      dependencies: ['verify']
    }
  ],
  inputs: {
    ontologyRoot: 'data/ontology',
    compiledDir: 'etl/dist/compiled',
    buildsDir: 'etl/dist/database'
  },
  outputs: {
    taxaJsonl: 'etl/dist/compiled/taxa/taxa.jsonl',
    docsJsonl: 'etl/dist/compiled/docs.jsonl',
    database: 'etl/dist/database/graph.dev.sqlite'
  }
}
