import { PipelineConfig } from './types.js'

export const pipelineConfig: PipelineConfig = {
  steps: [
    {
      id: 'validate',
      name: 'Validate ontology data',
      description: 'Validate taxonomic data integrity and consistency',
      command: 'python3',
      args: ['python/validate_taxa.py', '--taxa-root', 'data/ontology/taxa']
    },
    {
      id: 'compile-taxa',
      name: 'Compile taxonomic data',
      description: 'Compile taxonomic hierarchy into JSONL format',
      command: 'python3',
      args: ['python/compile_taxa.py', '--taxa-root', 'data/ontology/taxa', '--out', 'data/ontology/compiled/taxa/taxa.jsonl'],
      dependencies: ['validate']
    },
    {
      id: 'compile-docs',
      name: 'Compile documentation',
      description: 'Compile taxonomic documentation from .tx.md files',
      command: 'python3',
      args: ['python/compile_docs.py', '--taxa-root', 'data/ontology/taxa', '--compiled-taxa', 'data/ontology/compiled/taxa/taxa.jsonl', '--out', 'data/ontology/compiled/docs.jsonl'],
      dependencies: ['compile-taxa']
    },
    {
      id: 'build-db',
      name: 'Build database',
      description: 'Compile ontology data into SQLite database with FTS',
      command: 'python3',
      args: ['python/compile.py', '--in', './data/ontology/compiled', '--out', './data/builds/graph.dev.sqlite'],
      dependencies: ['compile-docs']
    },
    {
      id: 'verify',
      name: 'Verify build',
      description: 'Verify database integrity and search functionality',
      command: 'tsx',
      args: ['src/pipeline/steps/verify.ts'],
      dependencies: ['build-db']
    }
  ],
  inputs: {
    ontologyRoot: 'data/ontology',
    compiledDir: 'data/ontology/compiled',
    buildsDir: 'data/builds'
  },
  outputs: {
    taxaJsonl: 'data/ontology/compiled/taxa/taxa.jsonl',
    docsJsonl: 'data/ontology/compiled/docs.jsonl',
    database: 'data/builds/graph.dev.sqlite'
  }
}
