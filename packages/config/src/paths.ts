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
  // Database paths (ETL2 only)
  database: 'etl2/build/database/graph.dev.sqlite',
  databaseAbsolute: path.join(workspaceRoot, 'etl2/build/database/graph.dev.sqlite'),

  // ETL2 paths
  etl2Root: 'etl2',
  etl2Build: 'etl2/build',
  etl2Database: 'etl2/build/database',
  etl2Reports: 'etl2/build/report',

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
  etl2Reports: path.join(workspaceRoot, PATHS.etl2Reports),
  etl2Build: path.join(workspaceRoot, PATHS.etl2Build),
  taxaRoot: path.join(workspaceRoot, PATHS.taxaRoot),
})
