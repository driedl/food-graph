# Monorepo Optimization Analysis

**Status**: Analysis Complete, Implementation Pending  
**Priority**: High  
**Effort**: Medium (2-3 days)

## Overview

This document outlines suboptimal patterns identified in the food-graph monorepo and provides a roadmap for standardization. The analysis was conducted after fixing a critical path resolution issue in the ETL pipeline that caused documentation reports to show stale data (165 vs 166 docs).

## Context

The food-graph monorepo is a TypeScript-based project using:

- **Package Manager**: pnpm 9.0.0 with workspace configuration
- **Build System**: Turbo (primary) + direct pnpm + tsx
- **Runtime**: Node.js 20+ with ES modules
- **Database**: SQLite with better-sqlite3
- **Frontend**: React + Vite + Tailwind
- **Backend**: Fastify + tRPC
- **ETL**: Custom pipeline with TypeScript

## Current Architecture

```
/Users/daveriedl/git/food-graph/
├── apps/
│   ├── api/          # Fastify + tRPC API
│   └── web/          # React + Vite frontend
├── packages/
│   ├── shared/       # Shared types and utilities
│   ├── config/       # Environment and path configuration
│   └── api-contract/ # API type definitions
├── etl/              # ETL pipeline
├── data/             # Ontology data
└── docs/             # Documentation
```

## Identified Suboptimal Patterns

### 1. 🚨 Inconsistent Path Resolution Strategies

**Current State**:

- **API**: Uses `@nutrition/config` with environment variables
- **ETL**: Uses hardcoded relative paths with `process.cwd().replace('/etl', '')`
- **Web**: Uses TypeScript path mapping with `@nutrition/shared/*`
- **Root**: Uses `tsx` with relative paths from project root

**Impact**: Confusing, error-prone, and hard to maintain. Recently caused doc report to show stale data due to incorrect working directory resolution.

**Files Affected**:

- `apps/api/src/db.ts` - Uses `@nutrition/config`
- `etl/src/pipeline/steps/doc-reporter.ts` - Uses hardcoded paths
- `etl/src/pipeline/steps/verify.ts` - Uses hardcoded paths
- `apps/web/tsconfig.json` - Uses path mapping
- `scripts/run-sql.ts` - Uses relative paths

### 2. 🚨 Mixed Build Tool Usage

**Current State**:

- **Turbo**: Used for most tasks (`dev`, `build`, `lint`, `typecheck`)
- **Direct pnpm**: Used for ETL tasks (`etl:build`, `etl:smoke-tests`, `etl:verify`)
- **tsx**: Used for scripts (`sql`, `sql:repl`, `ag`)

**Impact**: Inconsistent caching, parallelization, and task orchestration.

**Files Affected**:

- `package.json` - Root scripts
- `turbo.json` - Turbo configuration
- `etl/package.json` - ETL scripts

### 3. 🚨 Inconsistent TypeScript Configuration

**Current State**:

- **API**: Minimal config, relies on base
- **Web**: Extensive path mapping with `@/*`, `@lib/*`, `@ui/*`
- **ETL**: Custom path mapping for `@nutrition/config`
- **Shared**: No build output, just type checking

**Impact**: Different import patterns, inconsistent module resolution.

**Files Affected**:

- `tsconfig.base.json` - Base configuration
- `apps/api/tsconfig.json` - API config
- `apps/web/tsconfig.json` - Web config
- `etl/tsconfig.json` - ETL config
- `packages/*/tsconfig.json` - Package configs

### 4. 🚨 Workspace Dependency Management Issues

**Current State**:

- **API**: Depends on `@nutrition/config` and `@nutrition/shared`
- **Web**: Only depends on `@nutrition/api-contract`
- **ETL**: Depends on `@nutrition/shared` and `@nutrition/config`
- **Shared**: No dependencies on other workspace packages

**Impact**: Circular dependency risks, unclear package boundaries.

**Files Affected**:

- `apps/api/package.json`
- `apps/web/package.json`
- `etl/package.json`
- `packages/shared/package.json`

### 5. 🚨 Inconsistent Script Patterns

**Current State**:

- **API dev**: `cd ../../ && tsx watch apps/api/src/index.ts` (changes working directory)
- **ETL dev**: `tsx watch src/pipeline/index.ts` (runs from ETL directory)
- **Web dev**: `vite` (standard tool)
- **Root scripts**: `tsx scripts/run-sql.ts` (runs from root)

**Impact**: Confusing for developers, inconsistent behavior.

**Files Affected**:

- `apps/api/package.json` - API scripts
- `etl/package.json` - ETL scripts
- `package.json` - Root scripts

### 6. 🚨 Mixed Module Systems

**Current State**:

- **All packages**: Use `"type": "module"` (ES modules)
- **Root scripts**: Use `tsx` (supports both CommonJS and ES modules)
- **Some imports**: Use `.js` extensions, others don't

**Impact**: Import/export confusion, potential runtime errors.

**Files Affected**:

- All `package.json` files
- Import statements across the codebase

### 7. 🚨 Inconsistent Output Directories

**Current State**:

- **API**: `dist/` (standard)
- **Web**: `dist/` (standard)
- **ETL**: `dist/` (standard)
- **Shared**: No build output (source-only)

**Impact**: Inconsistent build artifacts, unclear package boundaries.

**Files Affected**:

- `turbo.json` - Output configuration
- `tsconfig.json` files - Output directories

### 8. 🚨 Environment Variable Management

**Current State**:

- **API**: Uses `@nutrition/config` with Zod validation
- **ETL**: Uses hardcoded paths
- **Web**: Uses Vite's built-in env handling
- **Root**: Uses `.env` file overrides

**Impact**: Inconsistent configuration management.

**Files Affected**:

- `packages/config/src/index.ts` - Config package
- `.env` - Environment overrides
- `apps/web/vite.config.ts` - Vite config

### 9. 🚨 Inconsistent Linting Setup

**Current State**:

- **Root**: Has `.eslintrc.cjs` with TypeScript rules
- **Packages**: Individual `lint` scripts
- **ETL**: No visible linting configuration

**Impact**: Inconsistent code quality standards.

**Files Affected**:

- `.eslintrc.cjs` - Root ESLint config
- Package `lint` scripts

### 10. 🚨 Database Path Hardcoding

**Current State**:

- **API**: Uses `@nutrition/config` (good)
- **ETL**: Uses `process.cwd().replace('/etl', '')` (bad)
- **Root scripts**: Uses `etl/dist/database/graph.dev.sqlite` (bad)

**Impact**: Brittle, hard to change database location.

**Files Affected**:

- `packages/config/src/paths.ts` - Centralized paths
- `etl/src/pipeline/steps/*.ts` - ETL scripts
- `scripts/run-sql.ts` - Root scripts

## Implementation Roadmap

### Phase 1: Path Resolution Standardization (COMPLETED)

- ✅ Created centralized path configuration in `@nutrition/config`
- ✅ Updated ETL pipeline to use absolute paths
- ✅ Fixed doc report path resolution issue

### Phase 2: Build Tool Unification (PENDING)

**Priority**: High  
**Effort**: 1 day

**Tasks**:

1. Move all ETL scripts to Turbo tasks
2. Update `turbo.json` to include ETL tasks
3. Remove direct pnpm calls from root scripts
4. Standardize script execution patterns

**Files to Modify**:

- `turbo.json` - Add ETL tasks
- `package.json` - Update root scripts
- `etl/package.json` - Remove redundant scripts

### Phase 3: TypeScript Configuration Standardization (PENDING)

**Priority**: High  
**Effort**: 1 day

**Tasks**:

1. Standardize path mapping across all packages
2. Ensure consistent base configuration inheritance
3. Add missing TypeScript configs for packages
4. Standardize import/export patterns

**Files to Modify**:

- `tsconfig.base.json` - Add common path mappings
- All `tsconfig.json` files - Standardize configurations
- Import statements - Add `.js` extensions consistently

### Phase 4: Package Boundary Clarification (PENDING)

**Priority**: Medium  
**Effort**: 0.5 days

**Tasks**:

1. Define clear package responsibilities
2. Remove circular dependencies
3. Standardize workspace dependency patterns
4. Add package documentation

**Files to Modify**:

- All `package.json` files - Clean up dependencies
- `packages/*/README.md` - Add package documentation

### Phase 5: Environment Management Unification (PENDING)

**Priority**: Medium  
**Effort**: 0.5 days

**Tasks**:

1. Use `@nutrition/config` everywhere
2. Remove hardcoded paths
3. Standardize environment variable handling
4. Add configuration validation

**Files to Modify**:

- `etl/src/pipeline/steps/*.ts` - Use config package
- `scripts/*.ts` - Use config package
- `apps/web/vite.config.ts` - Use config package

### Phase 6: Linting and Code Quality Standardization (PENDING)

**Priority**: Low  
**Effort**: 0.5 days

**Tasks**:

1. Standardize ESLint configuration
2. Add missing linting configs
3. Ensure consistent code quality standards
4. Add pre-commit hooks

**Files to Modify**:

- `.eslintrc.cjs` - Standardize rules
- Package `lint` scripts - Ensure consistency
- Add `.eslintrc.js` files for packages if needed

## Implementation Guidelines

### For Empty Context Agents

1. **Start with Phase 2** - Build tool unification is the most impactful
2. **Test thoroughly** - Each phase should be tested independently
3. **Maintain backward compatibility** - Don't break existing functionality
4. **Use the centralized config** - Leverage `@nutrition/config` for all paths
5. **Follow the established patterns** - Use the API package as a reference

### Key Files to Understand

1. **`packages/config/src/paths.ts`** - Centralized path configuration
2. **`packages/config/src/index.ts`** - Environment variable management
3. **`turbo.json`** - Build system configuration
4. **`tsconfig.base.json`** - Base TypeScript configuration
5. **`pnpm-workspace.yaml`** - Workspace structure

### Testing Strategy

1. **Unit tests** - Test individual package builds
2. **Integration tests** - Test cross-package functionality
3. **End-to-end tests** - Test full pipeline execution
4. **Performance tests** - Ensure build times don't regress

### Success Criteria

- [ ] All packages use consistent path resolution
- [ ] All tasks use Turbo for orchestration
- [ ] All packages have consistent TypeScript configuration
- [ ] All packages have clear boundaries and dependencies
- [ ] All scripts use centralized configuration
- [ ] All packages have consistent linting
- [ ] Database paths are centralized and configurable

## Related Issues

- **Fixed**: Doc report showing stale data (165 vs 166 docs)
- **Root Cause**: ETL pipeline running from wrong working directory
- **Solution**: Implemented centralized path configuration

## Notes

- The path resolution fix (Phase 1) has been implemented and tested
- The ETL pipeline now correctly generates reports with 166 docs
- This analysis should be revisited after each phase is completed
- Consider adding automated testing for path resolution to prevent regressions
