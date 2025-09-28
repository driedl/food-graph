// scripts/aggregate.ts

/**
 * filename: scripts/aggregate.ts
 *
 * Usage:
 *   pnpm ag                           # Interactive mode
 *   pnpm ag --compact                 # Quick compact mode
 *   pnpm ag --verbose                 # Full verbose mode
 *   pnpm ag --help                    # Show help
 *
 * Generates a comprehensive aggregate of food-graph project files for AI context.
 * Automatically detects relevant code and config files, excludes build artifacts.
 */

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, resolve, join, relative, extname, basename } from 'node:path';
import { readdirSync, statSync } from 'node:fs';
import { glob } from 'glob';
import inquirer from 'inquirer';

// ---- Types ----------------------------------------------------------------

type ContentLevel = 'compact' | 'verbose';
type OutputDestination = 'console' | 'file' | 'both';

interface FileCategory {
  name: string;
  pattern: string[];
  description: string;
  ignore?: string[];
}

interface AggregateOptions {
  contentLevel: ContentLevel;
  outputDestination: OutputDestination;
  outputFile?: string;
  categories: string[];
}

interface FileInfo {
  path: string;
  size: number;
  lines: number;
  content: string;
}

// ---- File Categories ------------------------------------------------------

const FILE_CATEGORIES: Record<string, FileCategory> = {
  web: {
    name: 'Web App',
    pattern: [
      'apps/web/**/*.ts',
      'apps/web/**/*.tsx',
      'apps/web/**/*.js',
      'apps/web/**/*.jsx',
      'apps/web/**/*.json',
      'apps/web/**/*.html',
      'apps/web/**/*.css',
      'apps/web/**/*.config.*',
      'packages/api-contract/**/*.ts',
      'packages/api-contract/**/*.tsx',
      'packages/api-contract/**/*.js',
      'packages/api-contract/**/*.jsx',
      'packages/api-contract/**/*.json',
    ],
    description: 'React frontend with tRPC client and API contracts',
  },
  api: {
    name: 'API Server',
    pattern: [
      'apps/api/**/*.ts',
      'apps/api/**/*.js',
      'apps/api/**/*.json',
      'apps/api/**/*.sql',
      'packages/api-contract/**/*.ts',
      'packages/api-contract/**/*.tsx',
      'packages/api-contract/**/*.js',
      'packages/api-contract/**/*.jsx',
      'packages/api-contract/**/*.json',
    ],
    description: 'tRPC server with SQLite, migrations, and API contracts',
  },
  etl: {
    name: 'ETL Processing',
    pattern: [
      'etl/**/*.py',
      'etl/**/*.md',
      'packages/shared/**/*.ts',
      'packages/shared/**/*.js',
      'packages/shared/**/*.json',
    ],
    description: 'Python scripts and shared utilities',
  },
  ontology: {
    name: 'Ontology Data',
    pattern: [
      'data/ontology/**/*.json',
      'data/ontology/**/*.jsonl',
      'data/sql/**/*.json',
      'data/builds/*.json', // Include metadata JSON files from builds
    ],
    ignore: [
      'data/ontology/compiled/**', // Exclude all compiled files (redundant with source files)
    ],
    description: 'Food ontology data and schemas',
  },
  scripts: {
    name: 'Project Scripts',
    pattern: [
      'scripts/**/*.ts',
      'scripts/**/*.js',
      'scripts/**/*.md',
    ],
    description: 'Build and utility scripts',
  },
  docs: {
    name: 'Documentation',
    pattern: [
      'docs/**/*.md',
      'README.md',
      'CONTRIBUTING.md',
    ],
    description: 'Project documentation',
  },
  config: {
    name: 'Configuration',
    pattern: [
      'package.json',
      'pnpm-workspace.yaml',
      'turbo.json',
      'tsconfig.base.json',
      '.gitignore',
      'README.md',
      'apps/*/package.json',
      'apps/*/tsconfig.json',
      'apps/*/vite.config.ts',
      'apps/*/tailwind.config.ts',
      'apps/*/postcss.config.js',
      'packages/*/package.json',
      'packages/*/tsconfig.json',
    ],
    description: 'Project config and package files',
  },
};

// ---- File Detection -------------------------------------------------------

function isCodeOrConfigFile(filePath: string): boolean {
  const ext = extname(filePath).toLowerCase();
  const fileName = basename(filePath).toLowerCase();
  
  // Code files
  const codeExtensions = ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.py'];
  if (codeExtensions.includes(ext)) {
    return true;
  }
  
  // Configuration files
  const configFiles = [
    'package.json',
    'tsconfig.json',
    'vite.config.ts',
    'tailwind.config.ts',
    'postcss.config.js',
    'pnpm-workspace.yaml',
    'README.md',
    '.gitignore',
    'Dockerfile',
    'docker-compose.yml',
    '.env.example',
    '.env.local.example'
  ];
  
  if (configFiles.includes(fileName)) {
    return true;
  }
  
  // Config extensions (but exclude lock files)
  const configExtensions = ['.json', '.jsonl', '.yaml', '.yml', '.toml', '.env'];
  if (configExtensions.includes(ext)) {
    const excludeConfigFiles = [
      'pnpm-lock.yaml',
      'package-lock.json',
      'yarn.lock',
      'bun.lockb'
    ];
    return !excludeConfigFiles.includes(fileName);
  }
  
  // Documentation
  if (ext === '.md' && fileName !== 'CHANGELOG.md') {
    return true;
  }
  
  return false;
}

function shouldExclude(filePath: string, workspaceRoot: string): boolean {
  const relativePath = relative(workspaceRoot, filePath);
  
  // Always exclude common non-code directories and files
  const excludePatterns = [
    'node_modules',
    '.git',
    'dist',
    'build',
    '.next',
    '.nuxt',
    'coverage',
    '.nyc_output',
    '.vscode',
    '.idea',
    '*.log',
    '*.tmp',
    '*.cache',
    '.DS_Store',
    'Thumbs.db',
    'data/builds/', // Exclude builds directory (includes DB files)
    'data/sources/', // Exclude sources directory (can be huge)
    'scripts/', // Exclude scripts directory
    'artifacts/',
    '*.duckdb*',
    '*.db',
    '*.sqlite',
    '*.db-shm',
    '*.db-wal',
    '.generated/',
    'generated/code.md', // Exclude the output artifact from this script
    "routeTree.gen.ts",
    'apps/web/src/components/ui/' // Exclude shadcn UI components to reduce bloat
  ];

  return excludePatterns.some(pattern => {
    if (pattern.endsWith('/')) {
      return relativePath.startsWith(pattern);
    }
    if (pattern.includes('*')) {
      const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
      return regex.test(relativePath);
    }
    // For patterns without '/' or '*', only match if they appear as directory segments
    // This prevents filenames containing the pattern from being excluded
    const pathSegments = relativePath.split('/');
    return pathSegments.some(segment => segment === pattern);
  });
}

function getFileInfo(filePath: string, workspaceRoot: string): FileInfo | null {
  try {
    const stats = statSync(filePath);
    if (!stats.isFile()) return null;

    const content = readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    
    return {
      path: relative(workspaceRoot, filePath),
      size: stats.size,
      lines,
      content
    };
  } catch (error) {
    console.warn(`Warning: Could not read file ${filePath}: ${error}`);
    return null;
  }
}

// ---- File Discovery -------------------------------------------------------

async function discoverFiles(categories: string[], workspaceRoot: string): Promise<FileInfo[]> {
  const files: FileInfo[] = [];

  // Handle "all" category by selecting all other categories
  let categoriesToProcess = categories;
  if (categories.includes('all')) {
    categoriesToProcess = Object.keys(FILE_CATEGORIES).filter(cat => cat !== 'all');
  }

  // Collect all files from included categories
  for (const categoryName of categoriesToProcess) {
    const category = FILE_CATEGORIES[categoryName];
    if (category) {
      for (const pattern of category.pattern) {
        try {
          const defaultIgnore = ['node_modules/**', '.git/**', 'dist/**', 'build/**', '*.log', '*.tmp', '*.cache', '*.db*', '*.sqlite*'];
          const categoryIgnore = category.ignore || [];
          const allIgnore = [...defaultIgnore, ...categoryIgnore];
          
          const matches = await glob(pattern, {
            ignore: allIgnore,
            cwd: workspaceRoot,
          });
          
          for (const match of matches) {
            const fullPath = join(workspaceRoot, match);
            if (isCodeOrConfigFile(fullPath) && !shouldExclude(fullPath, workspaceRoot)) {
              const fileInfo = getFileInfo(fullPath, workspaceRoot);
              if (fileInfo) {
                files.push(fileInfo);
              }
            }
          }
        } catch (error) {
          console.warn(`Warning: Failed to expand pattern "${pattern}":`, error);
        }
      }
    }
  }

  // Remove duplicates
  return [...new Set(files.map(f => f.path))].map(path => 
    files.find(f => f.path === path)!
  );
}

// ---- Output Generation -----------------------------------------------------

function formatSize(bytes: number): string {
  const kb = bytes / 1024;
  return kb.toFixed(1) + 'kb';
}

function generateVerboseOutput(files: FileInfo[]): string {
  let output = '# Codebase Aggregation Report\n\n';
  output += `Generated on: ${new Date().toISOString()}\n`;
  output += `Total files: ${files.length}\n`;
  output += `Total size: ${formatSize(files.reduce((sum, file) => sum + file.size, 0))}\n\n`;
  
  output += '## Files Overview\n\n';
  files.forEach(file => {
    output += `- **${file.path}** (${formatSize(file.size)}, ${file.lines} lines)\n`;
  });
  
  output += '\n---\n\n';
  
  files.forEach(file => {
    output += `## ${file.path}\n\n`;
    output += `**Size:** ${formatSize(file.size)} | **Lines:** ${file.lines}\n\n`;
    output += '```\n';
    output += file.content;
    output += '\n```\n\n';
  });
  
  return output;
}

function generateCompactOutput(files: FileInfo[]): string {
  let output = '# Codebase Summary\n\n';
  output += `Generated on: ${new Date().toISOString()}\n`;
  output += `Total files: ${files.length}\n`;
  output += `Total size: ${formatSize(files.reduce((sum, file) => sum + file.size, 0))}\n\n`;
  
  // Find the longest filename for alignment
  const maxPathLength = Math.max(...files.map(f => f.path.length));
  
  output += '## Files\n\n';
  files.forEach(file => {
    const paddedPath = file.path.padEnd(maxPathLength);
    const sizeStr = formatSize(file.size).padStart(8);
    const linesStr = file.lines.toString().padStart(6);
    output += `${paddedPath} ${sizeStr} ${linesStr} lines\n`;
  });
  
  return output;
}

// ---- Interactive CLI ------------------------------------------------------

async function getInteractiveOptions(): Promise<AggregateOptions> {
  // Step 1: Content level
  const contentLevelAnswer = await inquirer.prompt([
    {
      type: 'list',
      name: 'contentLevel',
      message: 'What content level do you want?',
      choices: [
        { name: 'Compact (summary with file stats)', value: 'compact' },
        { name: 'Verbose (dump everything - complete AI context)', value: 'verbose' },
      ],
      default: 'verbose',
    },
  ]);

  // Step 2: Category selection
  const categoryChoices = [
    { name: 'All Project Files - Select all categories', value: 'all' },
    ...Object.entries(FILE_CATEGORIES).map(([key, cat]) => ({
      name: `${cat.name} - ${cat.description}`,
      value: key,
    }))
  ];

  const categoriesAnswer = await inquirer.prompt([
    {
      type: 'checkbox',
      name: 'categories',
      message: 'Which categories to include?',
      choices: categoryChoices,
      default: ['all'], // Default to all files
    },
  ]);

  // Step 4: Output destination
  const outputAnswer = await inquirer.prompt([
    {
      type: 'list',
      name: 'outputDestination',
      message: 'Output destination?',
      choices: [
        { name: 'Console only', value: 'console' },
        { name: 'File only (generated/code.md)', value: 'file' },
        { name: 'Both console and file', value: 'both' },
      ],
      default: 'file',
    },
  ]);

  return {
    contentLevel: contentLevelAnswer.contentLevel,
    categories: categoriesAnswer.categories,
    outputDestination: outputAnswer.outputDestination,
    outputFile: outputAnswer.outputDestination === 'file' || outputAnswer.outputDestination === 'both' 
      ? 'generated/code.md' 
      : undefined
  };
}

// ---- Help Function ---------------------------------------------------------

function showHelp() {
  console.log(`
📁 Food Graph Codebase Aggregator

Usage:
  pnpm ag                    # Interactive mode (default)
  pnpm ag --compact          # Quick compact mode
  pnpm ag --verbose          # Full verbose mode
  pnpm ag --categories all,web,api  # Specific categories (comma-separated)
  pnpm ag --help             # Show this help

Content Levels:
  compact    - One line per file with size and line count
  verbose    - Full file contents (perfect for AI context)

File Categories:
  all        - All project files (selects all other categories)
  web        - React frontend application with tRPC client and API contracts
  api        - tRPC server with SQLite database and API contracts
  etl        - Python scripts and shared utilities
  ontology   - Food ontology data and schemas
  scripts    - Build and utility scripts
  docs       - Project documentation
  config     - Project configuration, package management, and documentation

Output Destinations:
  console    - Output directly to terminal
  file       - Save to generated/code.md
  both       - Output to both terminal and file

The script automatically detects relevant code and config files:
  ✅ TypeScript/JavaScript files (.ts, .tsx, .js, .jsx)
  ✅ Python files (.py)
  ✅ Configuration files (package.json, tsconfig.json, vite.config.ts, etc.)
  ✅ Documentation (README.md, etc.)
  ❌ Lock files (pnpm-lock.yaml, package-lock.json)
  ❌ Build artifacts (dist/, node_modules/, *.db, etc.)
  ❌ Data files (data/ directory - excludes sources which can be huge)
  ❌ Shadcn UI components (apps/web/src/components/ui/)

Examples:
  pnpm ag                                    # Interactive selection
  pnpm ag --verbose --categories web         # Web app only
  pnpm ag --compact --categories api         # API code summary
  pnpm ag --verbose --categories all         # Everything
  pnpm ag --verbose --categories web,api     # Web app + API
  pnpm ag --verbose --categories ontology    # Ontology data only
  pnpm ag --verbose --categories scripts,docs # Scripts and documentation
`);
}

// ---- Main Function ---------------------------------------------------------

async function main() {
  const args = process.argv.slice(2);

  // Show help if requested
  if (args.includes('--help') || args.includes('-h')) {
    showHelp();
    return;
  }

  const workspaceRoot = process.cwd();
  let options: AggregateOptions;

  // Parse command line arguments
  if (args.includes('--interactive') || args.length === 0) {
    options = await getInteractiveOptions();
  } else {
    // Parse content level
    let contentLevel: ContentLevel = 'verbose';
    if (args.includes('--compact')) {
      contentLevel = 'compact';
    }

    // Parse categories
    let categories: string[] = ['all']; // Default to all files
    const categoriesIndex = args.indexOf('--categories');
    if (categoriesIndex !== -1 && categoriesIndex + 1 < args.length) {
      const categoriesArg = args[categoriesIndex + 1];
      if (categoriesArg && !categoriesArg.startsWith('--')) {
        categories = categoriesArg.split(',').map(c => c.trim());
      }
    }

    options = {
      contentLevel,
      categories,
      outputDestination: 'file',
      outputFile: 'generated/code.md'
    };
  }

  console.log('🔍 Discovering files...');
  const files = await discoverFiles(options.categories, workspaceRoot);
  console.log(`📁 Found ${files.length} files in categories: ${options.categories.join(', ')}`);

  console.log('📝 Generating output...');
  const output = options.contentLevel === 'verbose' 
    ? generateVerboseOutput(files)
    : generateCompactOutput(files);

  // Output to file if specified
  if (options.outputFile && (options.outputDestination === 'file' || options.outputDestination === 'both')) {
    const outFile = resolve(options.outputFile);
    mkdirSync(dirname(outFile), { recursive: true });
    writeFileSync(outFile, output);
    console.log(`✅ Output written → ${outFile}`);
  }

  // Output to console if specified
  if (options.outputDestination === 'console' || options.outputDestination === 'both') {
    console.log('\n' + '='.repeat(50));
    console.log('OUTPUT:');
    console.log('='.repeat(50));
    console.log(output);
  }

  console.log(`📊 Summary: ${files.length} files processed`);
}

// ---- Run ------------------------------------------------------------------

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}