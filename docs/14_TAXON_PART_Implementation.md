# 14 — Taxon+Part Search Implementation

**Status**: Phase 1 Complete ✅  
**Author**: System  
**Date**: 2025-01-27 (Updated 2025-09-30)  
**Goal**: Enable search for "Milk", "Cow milk", "Goat milk", etc. by materializing taxon+part combinations as searchable nodes.

---

## Executive Summary

**Phase 1 is fully implemented and working** - users can now search for common food concepts like "Milk", "Eggs", "Apple", "Beef" and get intuitive taxon+part results. The system materializes 450+ taxon+part nodes with proper naming (implied parts, overrides) and unified search across taxa and food concepts.

**Current Status**: ✅ Complete - All functionality working, database sync resolved, legacy tables cleaned up  
**Phase 2**: Transform chains (e.g., "Buttermilk", "Yogurt") — deferred to future ADR

---

## Implementation Status (Updated 2025-01-27)

### ✅ **COMPLETED**

**ETL Pipeline:**

- ✅ `taxon_part_nodes` table with 450+ entries
- ✅ Separate FTS tables: `taxa_fts` (330 entries) + `tp_fts` (450 entries)
- ✅ Rules system implemented:
  - `implied_parts.jsonl` — 181 rules for implicit parts (e.g., "Apple" → fruit)
  - `name_overrides.jsonl` — 102 rules for market names (e.g., "Beef", "Pork", "Cow Milk")
  - `taxon_part_policy.json` — Materialization policy (leaf-only by default)
  - `taxon_part_synonyms.jsonl` — Additional synonyms
- ✅ Name generation working with implied parts and overrides

**API Layer:**

- ✅ `search.combined` endpoint supports both `taxon` and `taxon_part` results
- ✅ `getTaxonPart` endpoint for detailed taxon+part information
- ✅ Proper ranking and deduplication
- ✅ Navigation objects for UI routing

**UI Layer:**

- ✅ Search results display taxon+part nodes with "Food" badges
- ✅ Unified treatment: UI treats TX/TP/TPT as backend concepts (no client routes)
- ✅ `onPickTP` handler navigates to workbench with taxon + part context
- ✅ Integration with existing workbench flow

### ✅ **ISSUES RESOLVED (2025-09-30)**

**Database Sync Problem:** ✅ FIXED

- ETL database has both FTS tables populated (`taxa_fts`: 330, `tp_fts`: 450)
- API database now properly synced with both FTS tables via `pnpm sync-db`
- Search using optimized FTS with BM25 ranking working correctly

**Legacy FTS Tables:** ✅ CLEANED UP

- Removed unused `taxon_doc_fts` and `nodes_fts_test` tables from compile.py
- Only active FTS tables remain: `taxa_fts` and `tp_fts`
- Database size reduced and cleaner schema

### 📋 **FUTURE ENHANCEMENTS**

**Metadata/Backlog:**

- **Plant-part synonyms** (pulp/flesh/stone/bran/germ/greens, etc.) for better recall
- **Herbs & spices pack** (leaf/seed/bark/flower) and **fruits-by-cultivar** niceties
- **Curated Phase-2 derived foods** (`derived_foods.jsonl`): cheeses, yogurts, cultured dairy, etc.
- **Ranking polish**: BM25 weights, dedupe when TP name == taxon name (prefer TP)

---

## **CURRENT STATUS: FULLY WORKING** ✅

### 🔧 **Database Sync: WORKING**

The database sync mechanism is working correctly:

- ✅ `pnpm sync-db` copies ETL database to API database
- ✅ `pnpm etl:build:sync` builds and syncs in one command
- ✅ Auto-sync in API startup when `AUTO_COPY_ETL_DB=true`
- ✅ FTS tables properly copied with WAL/SHM files

### 🎯 **FTS Search: WORKING**

- ✅ FTS-based search using `taxa_fts` and `tp_fts` tables
- ✅ Proper BM25 ranking across taxa and taxon+part results
- ✅ Optimized search response times
- ✅ Legacy unused FTS tables removed for cleaner schema

---

## **CURRENT FUNCTIONALITY STATUS**

**What's Working:**

- ✅ Search returns taxon+part results ("milk" → "Cow Milk", "Sheep Milk")
- ✅ Implied parts working ("apple" → "Apple (Fuji)", "Apple (Gala)")
- ✅ Name overrides working ("beef" → "Beef" instead of "Cattle Muscle")
- ✅ UI displays and navigates correctly with "Food" badges
- ✅ Unified treatment of TX/TP/TPT as backend concepts

**What Was Fixed:**

- ✅ Database sync (FTS tables now properly copied from ETL to API database)
- ✅ FTS-based search performance (now using optimized FTS with BM25 ranking)
- ✅ Legacy FTS tables cleaned up (removed unused `taxon_doc_fts` and `nodes_fts_test`)

---

## **PHASE 2: TRANSFORM CHAINS (FUTURE)**

**Scope**: Materialize common derived foods as taxon+part+transform nodes

**Examples**:

- **Buttermilk**: `tp:...bos:taurus:part:milk` + `tf:churn`
- **Yogurt**: `tp:...bos:taurus:part:milk` + `tf:ferment{starter=yogurt_thermo}`
- **Skim Milk**: `tp:...bos:taurus:part:milk` + `tf:standardize_fat{fat_pct=0.5}`

**Status**: Not started - deferred to future ADR

---

## **SUCCESS METRICS**

**Current Status**: ✅ 100% complete

- ✅ 450+ taxon+part nodes materialized
- ✅ Search functionality working with FTS optimization
- ✅ UI integration complete
- ✅ Database sync working correctly
- ✅ Legacy FTS tables cleaned up

**Production Ready**:

- ✅ FTS-based search performance with BM25 ranking
- ✅ Robust database sync mechanism
- ✅ Clean schema with only active FTS tables
- ✅ Ready for production use

---

_End of Document_
