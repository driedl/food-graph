#!/usr/bin/env tsx
/**
 * Evidence Mapping Script
 * 
 * Wrapper script for the 3-tier evidence mapping system.
 * Provides easy access to common parameters and configurations.
 */

import { execSync } from 'child_process';
import { resolve } from 'path';

const args = process.argv.slice(2);

// Default configuration - using absolute paths so script can be run from anywhere
const defaults = {
    '--graph-db': resolve(process.cwd(), 'etl/build/database/graph.dev.sqlite'),
    '--ncbi-db': resolve(process.cwd(), 'etl/build/database/ncbi.sqlite'),
    '--fdc-dir': resolve(process.cwd(), 'data/sources/fdc'),
    '--output': resolve(process.cwd(), 'data/evidence/fdc-foundation'),
    '--model': 'gpt-5-mini',
    '--min-confidence': '0.7'
};

// Build command
const command = [
    'cd etl && python3 -m evidence.evidence_mapper',
    ...Object.entries(defaults).flatMap(([key, value]) => [key, value]),
    ...args
].join(' ');

console.log('Running evidence mapping with command:');
console.log(command);
console.log('');

try {
    execSync(command, { stdio: 'inherit' });
} catch (error) {
    console.error('Evidence mapping failed:', error);
    process.exit(1);
}
