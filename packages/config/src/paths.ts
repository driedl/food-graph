import path from 'path'
import { fileURLToPath } from 'url'
import { readFileSync, existsSync } from 'fs'

// Find workspace root by looking for pnpm-workspace.yaml or package.json with "workspaces" field
const findWorkspaceRoot = (startDir: string): string => {
  let current = startDir
  while (current !== '/' && current !== '') {
    // Check for pnpm-workspace.yaml (most common)
    const pnpmWorkspacePath = path.join(current, 'pnpm-workspace.yaml')
    if (existsSync(pnpmWorkspacePath)) {
      return current
    }
    
    // Check for package.json with workspaces
    const packageJsonPath = path.join(current, 'package.json')
    if (existsSync(packageJsonPath)) {
      try {
        const pkg = JSON.parse(readFileSync(packageJsonPath, 'utf8'))
        if (pkg.workspaces || pkg.pnpm?.workspaces) {
          return current
        }
      } catch {
        // Continue searching
      }
    }
    
    const parent = path.dirname(current)
    if (parent === current) break // Reached root
    current = parent
  }
  throw new Error('Workspace root not found')
}

// Get workspace root
const __dirname = path.dirname(fileURLToPath(import.meta.url))
const workspaceRoot = findWorkspaceRoot(__dirname)

export const PATHS = {
  workspaceRoot,
  // Database paths
  database: 'etl/dist/database/graph.dev.sqlite',
  databaseAbsolute: path.join(workspaceRoot, 'etl/dist/database/graph.dev.sqlite'),
  
  // ETL paths
  etlRoot: 'etl',
  etlDist: 'etl/dist',
  etlCompiled: 'etl/dist/compiled',
  etlReports: 'etl/reports',
  
  // Data paths
  dataRoot: 'data',
  ontologyRoot: 'data/ontology',
  taxaRoot: 'data/ontology/taxa',
  
  // App paths
  appsRoot: 'apps',
  apiRoot: 'apps/api',
  webRoot: 'apps/web',
  
  // Package paths
  packagesRoot: 'packages',
  sharedRoot: 'packages/shared',
  configRoot: 'packages/config',
  apiContractRoot: 'packages/api-contract',
} as const

// Helper function to resolve paths relative to workspace root
export const resolvePath = (relativePath: string): string => {
  return path.join(workspaceRoot, relativePath)
}

// Helper function to get absolute paths for common locations
export const getAbsolutePaths = () => ({
  database: path.join(workspaceRoot, PATHS.database),
  etlReports: path.join(workspaceRoot, PATHS.etlReports),
  etlCompiled: path.join(workspaceRoot, PATHS.etlCompiled),
  taxaRoot: path.join(workspaceRoot, PATHS.taxaRoot),
})
