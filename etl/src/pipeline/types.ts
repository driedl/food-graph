export interface PipelineStep {
  id: string
  name: string
  description: string
  command: string
  args?: string[]
  dependencies?: string[]
}

export interface PipelineConfig {
  steps: PipelineStep[]
  inputs: {
    ontologyRoot: string
    compiledDir: string
    buildsDir: string
  }
  outputs: {
    taxaJsonl: string
    docsJsonl: string
    database: string
  }
}

export interface BuildReport {
  success: boolean
  duration: number
  steps: Array<{
    id: string
    success: boolean
    duration: number
    output?: string
    error?: string
  }>
  summary: {
    taxaCount: number
    synonymsCount: number
    docsCount: number
    ftsCount: number
  }
}
