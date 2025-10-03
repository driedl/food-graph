// scripts/aggregate.ts

/**
 * filename: scripts/aggregate.ts
 *
 * Usage:
 *   pnpm ag                           # Interactive mode (default config)
 *   pnpm ag --config etl2             # Use ETL2 config
 *   pnpm ag --compact                 # Quick compact mode
 *   pnpm ag --summary                 # Summary mode (excerpts/signatures)
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

type ContentLevel = 'compact' | 'summary' | 'verbose';
type OutputDestination = 'console' | 'file' | 'both';

interface FileCategory {
  name: string;
  description: string;
  patterns: string[];
  ignore?: string[];
  includeExtensions?: string[];
  excludeExtensions?: string[];
  maxFileSize?: number;
  maxLines?: number;
}

interface AggregateConfig {
  name: string;
  description: string;
  categories: {
    [key: string]: FileCategory;
  };
  defaults: {
    contentLevel: ContentLevel;
    outputDestination: OutputDestination;
    outputFile?: string;
  };
  ui: {
    skipCategorySelection?: boolean;
    skipVerbositySelection?: boolean;
    customPrompts?: {
      [key: string]: string;
    };
  };
  processing: {
    maxAggregateFileSize: number;
  };
}

interface AggregateOptions {
  contentLevel: ContentLevel;
  outputDestination: OutputDestination;
  outputFile?: string;
  categories: string[];
  config: AggregateConfig;
  maxAggregateFileSize: number;
  summaryTruncationLines?: number;
}

interface FileInfo {
  path: string;
  size: number;
  lines: number;
  content: string;
}

// ---- Config Loading ------------------------------------------------------

function loadConfig(configName: string = 'default'): AggregateConfig {
  const configPath = resolve(process.cwd(), `scripts/aggregate/${configName}.json`);

  if (!existsSync(configPath)) {
    throw new Error(`Config file not found: ${configPath}`);
  }

  try {
    const configContent = readFileSync(configPath, 'utf-8');
    const config = JSON.parse(configContent) as AggregateConfig;

    // Validate required fields
    if (!config.name || !config.categories || !config.defaults || !config.processing) {
      throw new Error('Invalid config: missing required fields');
    }

    return config;
  } catch (error) {
    throw new Error(`Failed to load config ${configName}: ${error}`);
  }
}

function listAvailableConfigs(): string[] {
  const aggregateDir = resolve(process.cwd(), 'scripts/aggregate');
  const files = readdirSync(aggregateDir);

  return files
    .filter(file => file.endsWith('.json') && file !== 'default.json')
    .map(file => file.replace('.json', ''));
}

// ---- File Detection -------------------------------------------------------

function isCodeOrConfigFile(filePath: string, category: FileCategory): boolean {
  const ext = extname(filePath).toLowerCase();
  const fileName = basename(filePath).toLowerCase();

  // Check category-specific exclusions first
  if (category.excludeExtensions && category.excludeExtensions.includes(ext)) {
    return false;
  }

  // Check category-specific inclusions
  if (category.includeExtensions && category.includeExtensions.length > 0) {
    return category.includeExtensions.includes(ext);
  }

  // Default file type detection
  // Code files
  const codeExtensions = ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.py', '.sql'];
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
    'dist/**', // Exclude entire dist folder from all categories
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
    'data/sources/', // Exclude sources directory (can be huge)
    'artifacts/',
    '*.duckdb*',
    '*.db',
    '*.sqlite',
    '*.db-shm',
    '*.db-wal',
    '.generated/',
    'generated/code.md', // Exclude the output artifact from this script
    "routeTree.gen.ts",
    'scripts/aggregate.ts', // Exclude this utility script
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

async function discoverFiles(categories: string[], workspaceRoot: string, config: AggregateConfig): Promise<FileInfo[]> {
  const files: FileInfo[] = [];

  // Handle "all" category by selecting all other categories
  let categoriesToProcess = categories;
  if (categories.includes('all')) {
    categoriesToProcess = Object.keys(config.categories).filter(cat => cat !== 'all');
  }

  // Collect all files from included categories
  for (const categoryName of categoriesToProcess) {
    const category = config.categories[categoryName];
    if (category) {
      for (const pattern of category.patterns) {
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
            if (isCodeOrConfigFile(fullPath, category) && !shouldExclude(fullPath, workspaceRoot)) {
              const fileInfo = getFileInfo(fullPath, workspaceRoot);
              if (fileInfo) {
                // Apply category-specific file size limits
                if (category.maxFileSize && fileInfo.size > category.maxFileSize) {
                  continue;
                }
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

// ---- File Size Validation -------------------------------------------------

function validateAggregateSize(files: FileInfo[], maxSize: number): { valid: boolean; totalSize: number; message?: string } {
  const totalSize = files.reduce((sum, file) => sum + file.size, 0);

  if (totalSize <= maxSize) {
    return { valid: true, totalSize };
  }

  const sizeKB = (totalSize / 1024).toFixed(1);
  const maxKB = (maxSize / 1024).toFixed(1);

  return {
    valid: false,
    totalSize,
    message: `Aggregate size ${sizeKB}KB exceeds limit of ${maxKB}KB. Consider using summary mode or reducing file selection.`
  };
}

async function getSummaryTruncationLines(): Promise<number> {
  const answer = await inquirer.prompt([
    {
      type: 'number',
      name: 'lines',
      message: 'How many lines should be shown per file in summary mode?',
      default: 20,
      validate: (input: number) => {
        if (input < 1 || input > 1000) {
          return 'Please enter a number between 1 and 1000';
        }
        return true;
      }
    }
  ]);

  return answer.lines;
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

function summarizeFileContent(file: FileInfo, maxLines: number = 20): { summary: string; truncated: boolean } {
  const ext = extname(file.path).toLowerCase();
  const lines = file.content.split('\n');

  // JSONL files - first 10 lines
  if (ext === '.jsonl') {
    if (lines.length <= 10) {
      return { summary: file.content, truncated: false };
    }
    return { summary: lines.slice(0, 10).join('\n'), truncated: true };
  }

  // TypeScript/JavaScript - extract signatures
  if (['.ts', '.tsx', '.js', '.jsx'].includes(ext)) {
    const signatures: string[] = [];
    const imports: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      // Collect imports
      if (trimmed.startsWith('import ')) {
        imports.push(line);
      }
      // Collect exports, functions, classes, interfaces, types
      else if (
        trimmed.startsWith('export ') ||
        trimmed.match(/^(export\s+)?(async\s+)?function\s+\w+/) ||
        trimmed.match(/^(export\s+)?class\s+\w+/) ||
        trimmed.match(/^(export\s+)?interface\s+\w+/) ||
        trimmed.match(/^(export\s+)?type\s+\w+/) ||
        trimmed.match(/^(export\s+)?const\s+\w+\s*=/)
      ) {
        // Include previous line if it's a comment
        if (i > 0 && lines[i - 1].trim().startsWith('//')) {
          signatures.push(lines[i - 1]);
        }
        signatures.push(line);
      }
    }

    let result = '';
    if (imports.length > 0) {
      result += '// Imports\n' + imports.slice(0, 5).join('\n');
      if (imports.length > 5) result += '\n// ... more imports';
      result += '\n\n';
    }
    if (signatures.length > 0) {
      result += '// Signatures\n' + signatures.join('\n');
    }

    // If we extracted signatures, it's a summary (truncated)
    const truncated = signatures.length > 0 || imports.length > 0;
    return { summary: result || lines.slice(0, 20).join('\n'), truncated };
  }

  // JSON files - full if small, otherwise first 30 lines
  if (ext === '.json') {
    if (lines.length <= 50) {
      return { summary: file.content, truncated: false };
    }
    return { summary: lines.slice(0, 30).join('\n'), truncated: true };
  }

  // Markdown - first 50 lines or until section break
  if (ext === '.md') {
    let endLine = Math.min(50, lines.length);
    for (let i = 1; i < endLine; i++) {
      if (lines[i].startsWith('## ')) {
        endLine = i;
        break;
      }
    }
    const truncated = endLine < lines.length;
    return { summary: lines.slice(0, endLine).join('\n'), truncated };
  }

  // Python - extract function/class signatures
  if (ext === '.py') {
    const signatures: string[] = [];
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();
      if (trimmed.startsWith('def ') || trimmed.startsWith('class ')) {
        // Include previous line if it's a comment or decorator
        if (i > 0 && (lines[i - 1].trim().startsWith('#') || lines[i - 1].trim().startsWith('@'))) {
          signatures.push(lines[i - 1]);
        }
        signatures.push(line);
      }
    }
    const truncated = signatures.length > 0;
    return { summary: signatures.join('\n') || lines.slice(0, 20).join('\n'), truncated };
  }

  // SQL - first 20 lines
  if (ext === '.sql') {
    if (lines.length <= 20) {
      return { summary: file.content, truncated: false };
    }
    return { summary: lines.slice(0, 20).join('\n'), truncated: true };
  }

  // Default fallback - first 20 lines
  if (lines.length <= 20) {
    return { summary: file.content, truncated: false };
  }
  return { summary: lines.slice(0, 20).join('\n'), truncated: true };
}

function generateSummaryOutput(files: FileInfo[], maxLines: number = 20): string {
  let output = '# Codebase Summary Report\n\n';
  output += `Generated on: ${new Date().toISOString()}\n`;
  output += `Total files: ${files.length}\n`;

  // Calculate actual total size including truncation
  let actualTotalSize = 0;
  const fileSummaries = files.map(file => {
    const { summary, truncated } = summarizeFileContent(file, maxLines);
    const actualSize = Buffer.byteLength(summary, 'utf8');
    actualTotalSize += actualSize;
    return { file, summary, truncated, actualSize };
  });

  output += `Total size: ${formatSize(actualTotalSize)}\n`;
  output += `Summary truncation: ${maxLines} lines per file\n\n`;

  output += '## Files Overview\n\n';
  fileSummaries.forEach(({ file, actualSize, truncated }) => {
    const sizeLabel = truncated ? `${formatSize(actualSize)} (truncated from ${formatSize(file.size)})` : formatSize(file.size);
    output += `- **${file.path}** (${sizeLabel}, ${file.lines} lines)\n`;
  });

  output += '\n---\n\n';

  fileSummaries.forEach(({ file, summary, truncated, actualSize }) => {
    const truncateLabel = truncated ? ' *(truncated)*' : '';

    output += `## ${file.path}${truncateLabel}\n\n`;
    output += `**Size:** ${formatSize(actualSize)} | **Lines:** ${file.lines}\n\n`;
    output += '```\n';
    output += summary;
    output += '\n```\n\n';
  });

  return output;
}

// ---- Interactive CLI ------------------------------------------------------

async function getInteractiveOptions(config: AggregateConfig): Promise<AggregateOptions> {
  let contentLevel = config.defaults.contentLevel;
  let categories = ['all'];
  let outputDestination = config.defaults.outputDestination;
  let outputFile = config.defaults.outputFile;

  // Step 1: Content level (skip if configured)
  if (config.ui.skipVerbositySelection === true) {
    // Skip verbosity selection - use default
  } else {
    const contentLevelAnswer = await inquirer.prompt([
      {
        type: 'list',
        name: 'contentLevel',
        message: 'What content level do you want?',
        choices: [
          { name: 'Compact (file stats only)', value: 'compact' },
          { name: 'Summary (signatures/excerpts with metadata)', value: 'summary' },
          { name: 'Verbose (complete file contents - full AI context)', value: 'verbose' },
        ],
        default: config.defaults.contentLevel,
      },
    ]);
    contentLevel = contentLevelAnswer.contentLevel;
  }

  // Step 1.5: Get truncation lines if summary mode
  let summaryTruncationLines: number | undefined;
  if (contentLevel === 'summary') {
    summaryTruncationLines = await getSummaryTruncationLines();
  }

  // Step 2: Category selection (skip if configured)
  if (config.ui.skipCategorySelection === true) {
    // Skip category selection - use all categories
    categories = Object.keys(config.categories);
  } else {
    const categoryChoices = [
      { name: 'All Project Files - Select all categories', value: 'all' },
      ...Object.entries(config.categories).map(([key, cat]) => ({
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
    categories = categoriesAnswer.categories;
  }

  // Step 3: Output destination
  const outputMessage = config.ui.customPrompts?.outputDestination || 'Output destination?';
  const outputAnswer = await inquirer.prompt([
    {
      type: 'list',
      name: 'outputDestination',
      message: outputMessage,
      choices: [
        { name: 'Console only', value: 'console' },
        { name: `File only (${config.defaults.outputFile || 'generated/code.md'})`, value: 'file' },
        { name: 'Both console and file', value: 'both' },
      ],
      default: config.defaults.outputDestination,
    },
  ]);

  outputDestination = outputAnswer.outputDestination;
  outputFile = outputAnswer.outputDestination === 'file' || outputAnswer.outputDestination === 'both'
    ? (config.defaults.outputFile || 'generated/code.md')
    : undefined;

  return {
    contentLevel,
    categories,
    outputDestination,
    outputFile,
    config,
    maxAggregateFileSize: config.processing.maxAggregateFileSize,
    summaryTruncationLines
  };
}

// ---- Help Function ---------------------------------------------------------

function showHelp() {
  console.log(`
📁 Food Graph Codebase Aggregator

Usage:
  pnpm ag                    # Interactive mode (default config)
  pnpm ag --config etl2      # Use ETL2 config
  pnpm ag --compact          # Quick compact mode
  pnpm ag --summary          # Summary mode with excerpts
  pnpm ag --verbose          # Full verbose mode
  pnpm ag --categories all,web,api  # Specific categories (comma-separated)
  pnpm ag --list-configs     # List available configs
  pnpm ag --help             # Show this help

Content Levels:
  compact    - One line per file with size and line count
  summary    - File excerpts/signatures (JSONL: first 10 lines, TS/JS: signatures, etc.)
  verbose    - Full file contents (perfect for AI context)

Config System:
  --config <name>    - Use specific config (e.g., etl2)
  --list-configs     - Show available configurations
  Configs define categories, UI behavior, and processing limits

File Size Limits:
  Each config has a maxAggregateFileSize limit to prevent oversized outputs
  If exceeded, you'll be prompted to use summary mode or reduce file selection

Output Destinations:
  console    - Output directly to terminal
  file       - Save to configured output file
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
  pnpm ag                                    # Interactive selection (default config)
  pnpm ag --config etl2                      # ETL2 analysis (simplified flow)
  pnpm ag --verbose --categories web         # Web app only (full)
  pnpm ag --summary --categories web         # Web app only (signatures)
  pnpm ag --compact --categories api         # API code summary
  pnpm ag --verbose --categories all         # Everything
  pnpm ag --list-configs                     # Show available configs
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

  // List configs if requested
  if (args.includes('--list-configs')) {
    const configs = listAvailableConfigs();
    console.log('Available configurations:');
    configs.forEach(config => console.log(`  - ${config}`));
    console.log('  - default (built-in)');
    return;
  }

  const workspaceRoot = process.cwd();
  let options: AggregateOptions;

  // Parse config name
  let configName = 'default';
  const configIndex = args.indexOf('--config');
  if (configIndex !== -1 && configIndex + 1 < args.length) {
    const configArg = args[configIndex + 1];
    if (configArg && !configArg.startsWith('--')) {
      configName = configArg;
    }
  }

  // Load config
  let config: AggregateConfig;
  try {
    config = loadConfig(configName);
  } catch (error) {
    console.error(`❌ Error loading config '${configName}':`, error);
    return;
  }

  console.log(`📋 Using config: ${config.name} - ${config.description}`);

  // Parse command line arguments
  // Only go non-interactive if there are actual content/category arguments
  const hasContentArgs = args.includes('--compact') || args.includes('--summary') || args.includes('--verbose');
  const hasCategoryArgs = args.includes('--categories');

  if (args.includes('--interactive') || (!hasContentArgs && !hasCategoryArgs)) {
    options = await getInteractiveOptions(config);
  } else {
    // Parse content level
    let contentLevel: ContentLevel = config.defaults.contentLevel;
    if (args.includes('--compact')) {
      contentLevel = 'compact';
    } else if (args.includes('--summary')) {
      contentLevel = 'summary';
    } else if (args.includes('--verbose')) {
      contentLevel = 'verbose';
    }

    // Parse categories
    let categories: string[] = ['all']; // Default to all files
    const categoriesIndex = args.indexOf('--categories');
    if (categoriesIndex !== -1 && categoriesIndex + 1 < args.length) {
      const categoriesArg = args[categoriesIndex + 1];
      if (categoriesArg && !categoriesArg.startsWith('--')) {
        categories = categoriesArg.split(',').map(c => c.trim());
      }
    } else if (config.ui.skipCategorySelection) {
      // Use all categories if skipCategorySelection is true
      categories = Object.keys(config.categories);
    }

    options = {
      contentLevel,
      categories,
      outputDestination: config.defaults.outputDestination,
      outputFile: config.defaults.outputFile,
      config,
      maxAggregateFileSize: config.processing.maxAggregateFileSize
    };
  }

  console.log('🔍 Discovering files...');
  const files = await discoverFiles(options.categories, workspaceRoot, config);
  console.log(`📁 Found ${files.length} files in categories: ${options.categories.join(', ')}`);

  // Validate aggregate file size
  const sizeValidation = validateAggregateSize(files, options.maxAggregateFileSize);
  if (!sizeValidation.valid) {
    console.warn(`⚠️  ${sizeValidation.message}`);

    if (options.contentLevel === 'verbose') {
      console.log('💡 Try using summary mode to reduce file size:');
      console.log('   pnpm ag --summary --config ' + (configName === 'default' ? '' : configName));

      const answer = await inquirer.prompt([
        {
          type: 'confirm',
          name: 'useSummary',
          message: 'Switch to summary mode with custom truncation?',
          default: true
        }
      ]);

      if (answer.useSummary) {
        options.contentLevel = 'summary';
        options.summaryTruncationLines = await getSummaryTruncationLines();
        console.log('✅ Switched to summary mode');
      } else {
        console.warn('⚠️  Proceeding with verbose mode - output may be large');
      }
    } else {
      console.warn('⚠️  Proceeding despite file size limit - output may be large');
    }
  }

  console.log('📝 Generating output...');
  let output: string;
  let actualTotalSize = sizeValidation.totalSize;

  if (options.contentLevel === 'verbose') {
    output = generateVerboseOutput(files);
  } else if (options.contentLevel === 'summary') {
    output = generateSummaryOutput(files, options.summaryTruncationLines || 20);
    // Recalculate actual size for summary mode
    actualTotalSize = files.reduce((sum, file) => {
      const { summary } = summarizeFileContent(file, options.summaryTruncationLines || 20);
      return sum + Buffer.byteLength(summary, 'utf8');
    }, 0);
  } else {
    output = generateCompactOutput(files);
  }

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

  console.log(`📊 Summary: ${files.length} files processed (${formatSize(actualTotalSize)})`);
}

// ---- Run ------------------------------------------------------------------

if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch(console.error);
}