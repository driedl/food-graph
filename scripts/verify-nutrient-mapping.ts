#!/usr/bin/env tsx
/**
 * Nutrient Mapping Verification Script
 * 
 * Verifies that FDC-to-INFOODS nutrient mappings are complete and consistent.
 * Compares nutrients.json with fdc_to_infoods.jsonl crosswalk file.
 */

import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

interface NutrientDefinition {
    id: string;
    name: string;
    class: string;
    unit: string;
    sr_legacy_num?: string;
    fdc_candidates: string[];
    fdc_unit: string;
    unit_factor_from_fdc: number;
    fdc_alt_units: any[];
    aliases: string[];
    is_sum_or_derived: boolean;
    computed_from?: any[];
    label_priority: boolean;
    rounding: { decimals: number };
    confidence: string;
    notes_method?: string;
}

interface CrosswalkMapping {
    fdc_id: string;
    infoods_id: string;
    fdc_unit: string;
    infoods_unit: string;
    conversion_factor: number;
    confidence: string;
}

interface NutrientsData {
    canonical_scheme: string;
    version: string;
    notes: string;
    metadata: any;
    nutrients: NutrientDefinition[];
}

function loadNutrientsJson(): NutrientsData {
    const path = join(process.cwd(), 'data/ontology/nutrients.json');
    if (!existsSync(path)) {
        throw new Error(`nutrients.json not found at ${path}`);
    }
    return JSON.parse(readFileSync(path, 'utf-8'));
}

function loadCrosswalkMappings(): CrosswalkMapping[] {
    const path = join(process.cwd(), 'data/ontology/crosswalks/fdc_to_infoods.jsonl');
    if (!existsSync(path)) {
        throw new Error(`fdc_to_infoods.jsonl not found at ${path}`);
    }

    const content = readFileSync(path, 'utf-8');
    return content.trim().split('\n')
        .filter(line => line.trim())
        .map(line => JSON.parse(line));
}

function verifyMappings(): void {
    console.log('🔍 Verifying FDC-to-INFOODS nutrient mappings...\n');

    const nutrientsData = loadNutrientsJson();
    const crosswalkMappings = loadCrosswalkMappings();

    console.log(`📊 Loaded ${nutrientsData.nutrients.length} nutrients from nutrients.json`);
    console.log(`📊 Loaded ${crosswalkMappings.length} mappings from crosswalk file\n`);

    // Build expected mappings from nutrients.json
    const expectedMappings = new Map<string, NutrientDefinition>();
    const fdcToNutrient = new Map<string, string>();

    for (const nutrient of nutrientsData.nutrients) {
        for (const fdcId of nutrient.fdc_candidates) {
            expectedMappings.set(fdcId, nutrient);
            fdcToNutrient.set(fdcId, nutrient.id);
        }
    }

    console.log(`📊 Expected ${expectedMappings.size} FDC candidate mappings\n`);

    // Verify crosswalk mappings
    let matches = 0;
    let mismatches = 0;
    const issues: string[] = [];

    for (const mapping of crosswalkMappings) {
        const expected = expectedMappings.get(mapping.fdc_id);

        if (!expected) {
            issues.push(`❌ FDC ${mapping.fdc_id}: Not found in nutrients.json fdc_candidates`);
            mismatches++;
            continue;
        }

        // Check INFOODS ID match
        if (mapping.infoods_id !== expected.id) {
            issues.push(`❌ FDC ${mapping.fdc_id}: Crosswalk maps to ${mapping.infoods_id}, expected ${expected.id}`);
            mismatches++;
            continue;
        }

        // Check unit match
        if (mapping.infoods_unit !== expected.unit) {
            issues.push(`❌ FDC ${mapping.fdc_id}: Crosswalk unit ${mapping.infoods_unit}, expected ${expected.unit}`);
            mismatches++;
            continue;
        }

        // Check conversion factor match
        if (Math.abs(mapping.conversion_factor - expected.unit_factor_from_fdc) > 0.0001) {
            issues.push(`❌ FDC ${mapping.fdc_id}: Crosswalk factor ${mapping.conversion_factor}, expected ${expected.unit_factor_from_fdc}`);
            mismatches++;
            continue;
        }

        matches++;
    }

    // Check for missing mappings
    const crosswalkFdcIds = new Set(crosswalkMappings.map(m => m.fdc_id));
    for (const [fdcId, nutrient] of expectedMappings) {
        if (!crosswalkFdcIds.has(fdcId)) {
            issues.push(`❌ FDC ${fdcId}: Missing from crosswalk (maps to ${nutrient.id})`);
            mismatches++;
        }
    }

    // Report results
    console.log(`✅ Matches: ${matches}/${crosswalkMappings.length}`);
    console.log(`❌ Mismatches: ${mismatches}`);

    if (issues.length > 0) {
        console.log('\n🚨 Issues found:');
        issues.slice(0, 20).forEach(issue => console.log(`  ${issue}`));
        if (issues.length > 20) {
            console.log(`  ... and ${issues.length - 20} more issues`);
        }
    } else {
        console.log('\n✅ All mappings are consistent!');
    }

    // Summary statistics
    console.log('\n📈 Summary:');
    console.log(`  Total nutrients: ${nutrientsData.nutrients.length}`);
    console.log(`  FDC candidates: ${expectedMappings.size}`);
    console.log(`  Crosswalk mappings: ${crosswalkMappings.length}`);
    console.log(`  Matches: ${matches}`);
    console.log(`  Issues: ${mismatches}`);

    // Confidence breakdown
    const confidenceCounts = new Map<string, number>();
    for (const nutrient of nutrientsData.nutrients) {
        const conf = nutrient.confidence || 'unknown';
        confidenceCounts.set(conf, (confidenceCounts.get(conf) || 0) + 1);
    }

    console.log('\n🎯 Confidence breakdown:');
    for (const [conf, count] of confidenceCounts) {
        console.log(`  ${conf}: ${count} nutrients`);
    }

    // Derived nutrients
    const derivedCount = nutrientsData.nutrients.filter(n => n.is_sum_or_derived).length;
    console.log(`\n🧮 Derived nutrients: ${derivedCount}/${nutrientsData.nutrients.length}`);

    if (mismatches > 0) {
        process.exit(1);
    }
}

// Run verification
try {
    verifyMappings();
} catch (error) {
    console.error('❌ Verification failed:', error.message);
    process.exit(1);
}
