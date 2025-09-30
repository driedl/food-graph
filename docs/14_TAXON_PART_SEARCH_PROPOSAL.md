# 14 — Taxon+Part Search Proposal

**Status**: Proposal  
**Author**: System  
**Date**: 2025-09-30  
**Goal**: Enable search for "Milk", "Cow milk", "Goat milk", etc. by materializing taxon+part combinations as searchable nodes.

---

## Executive Summary

We propose adding **materialized taxon+part nodes** to enable intuitive food searches. Currently, users can search for taxa ("Cattle", "Goat") but not for common food concepts like "Milk" or "Eggs". By generating virtual nodes for valid taxon+part combinations (e.g., `tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus + part:milk → "Cow Milk"`), we bridge the gap between biological taxonomy and culinary concepts.

**Phase 1**: Materialized taxon+part nodes in search  
**Phase 2**: Add transform chains (e.g., "Buttermilk", "Yogurt") — deferred to future ADR

---

## Progress Report (Updated 2025-01-27)

### ✅ What's Done (Design & Data)

**Design decisions locked:**

- Materialize **Taxon+Part (TP) nodes** for search (leaf-only by default)
- **Implied parts** mechanism so names collapse (e.g., "Potato" not "Potato (tuber)")
- Keep **docs out of search** (no taxon_doc FTS in combined search)
- **Name generation**: overrides > implied-part collapse > generic rules
- Leave **Phase 2 transforms** to a curated list (not combinatorial)

**Rules/metadata added (append-only):**

- `rules/parts_applicability.jsonl` — Base packs (dairy/eggs, meat/poultry) + add-ons C (seafood) & D (staples/vegetables/grains/legumes/nuts)
- `rules/implied_parts.jsonl` — Mark tuber, root, bulb, leaf, stem, flower, fruit, grain, seed as implied for common crops
- `rules/name_overrides.jsonl` — Seafood disambiguations (Cod, Haddock, Salmon, Shrimp/Lobster/Crab, Oysters/Clams/Scallops, Roe → Caviar/Salmon Roe)
- `rules/taxon_part_synonyms.jsonl` — Seafood synonyms (e.g., "ahi", "lox", "bacalhau", "ikura", "mentaiko"…)

### 🔄 What's Left (Implementation)

**ETL changes (compile.py):**

- Read the new files: `implied_parts.jsonl`, `name_overrides.jsonl`, `taxon_part_synonyms.jsonl`
- **Step 5.3**: build `taxon_part_nodes` (leaf-only) using `has_part` + implied-part collapse + name overrides + TP synonyms
- **FTS**: extend/populate unified `nodes_fts` with both taxa and TP rows (docs excluded)
- **(Optional)** lightweight triggers for TP ↔ has_part sync inside ETL-built DB

**API changes:**

- Update combined search to query **taxa + TP** only (no docs); tune weights so foody queries favor TP
- New `getTaxonPart` read endpoint (details for a TP id)
- (Optional) facet flags (`kind=animal/plant/fungus`, `rank=taxon_part`) for filtering

**UI changes:**

- Treat `taxon_part` as "Food" item in results; route to `/workbench/tp/:id`
- TP detail shows lineage, part, and (later) applicable transforms

### 📋 To Revisit (Metadata/Backlog)

- **Beef/Pork/Lamb naming**: broaden `name_overrides.jsonl` for muscle → "Beef", "Pork", "Lamb/Mutton", plus common **cuts** where helpful
- **Plant-part synonyms** (pulp/flesh/stone/bran/germ/greens, etc.) for better recall
- **Herbs & spices pack** (leaf/seed/bark/flower) and **fruits-by-cultivar** niceties
- **Curated Phase-2 derived foods** (`derived_foods.jsonl`): cheeses, yogurts, cultured dairy, etc.
- **Ranking polish**: BM25 weights, dedupe when TP name == taxon name (prefer TP)

---

## 1. Problem Statement

### Current State

- **Search works for taxa only**: Users can find "Cattle" (`tx:...bos:taurus`) or "Goat" (`tx:...capra:hircus`)
- **Parts are hidden**: "Milk" is defined in `part_def` and linked via `has_part` rules, but not directly searchable
- **Ontology has the data**: `parts_applicability.jsonl` already maps `part:milk` → multiple bovine taxa

### User Expectation

- Search for **"Milk"** → see "Cow Milk", "Goat Milk", "Sheep Milk", etc.
- Search for **"Egg"** → see "Chicken Egg", "Duck Egg", etc.
- Search for **"Apple"** → see "Apple (fruit)", distinguishing from seed/peel parts

### Gap

We need **searchable nodes** for taxon+part combinations that appear as first-class entities in the search API.

---

## 2. Ontology Assessment

### Is the Ontology Rich Enough?

**✅ YES** — The existing ontology has all necessary primitives:

| Component                    | Status      | Evidence                                                       |
| ---------------------------- | ----------- | -------------------------------------------------------------- |
| **Taxa**                     | ✅ Complete | 200+ taxa across plantae, animalia, fungi                      |
| **Parts**                    | ✅ Complete | 40+ parts (milk, egg, fruit, muscle, grain, etc.)              |
| **Part Applicability Rules** | ✅ Complete | `parts_applicability.jsonl` has 50+ rules mapping parts → taxa |
| **Part Hierarchy**           | ⚠️ Partial  | Some parts have `parent_id` (e.g., `part:cream` → `part:milk`) |
| **Part Synonyms**            | ✅ Present  | `part_synonym` table exists, populated from animal cuts        |
| **FTS Infrastructure**       | ✅ Complete | `nodes_fts` using SQLite FTS5, with triggers                   |

### What's Missing (Minor Gaps)

1. **Part Synonyms (Plant Parts)**: Animal cuts have aliases (from `animal_cuts/*.json`), but plant parts lack common synonyms:
   - `part:fruit` could use aliases: "flesh", "pulp"
   - `part:milk` could use: "whole milk", "raw milk"
   - **Impact**: Low — can be added incrementally

2. **Part Display Names for Common Foods**: Some parts need better display names when combined with taxa:
   - `part:muscle` → "Beef" (for cattle), "Pork" (for pig), "Chicken" (for chicken)
   - **Impact**: Medium — affects search result quality

3. **Transform Chains (Phase 2)**: Not blocking for Phase 1
   - Buttermilk = `part:milk` + `tf:churn` + `tf:ferment`
   - Yogurt = `part:milk` + `tf:ferment{starter=yogurt_thermo}`

**Verdict**: Ontology is **production-ready for Phase 1**. Minor enrichments can be added post-launch.

---

## 3. Architecture Design

### 3.1 Conceptual Model

We introduce a **virtual node type** called `TaxonPartNode`:

```typescript
interface TaxonPartNode {
  id: string; // "tp:tx:...bos:taurus:part:milk"
  taxonId: string; // "tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus"
  partId: string; // "part:milk"
  name: string; // "Cow Milk"
  displayName: string; // "Milk (Cattle)"
  slug: string; // "milk-cattle"
  rank: 'taxon_part'; // Special rank for filtering
  kind: 'animal' | 'plant' | 'fungus'; // Inherited from part
}
```

### 3.2 Database Schema Changes

Add a new table `taxon_part_nodes` to the compiled database:

```sql
CREATE TABLE taxon_part_nodes (
  id TEXT PRIMARY KEY,                    -- "tp:tx:...bos:taurus:part:milk"
  taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  name TEXT NOT NULL,                     -- "Cow Milk"
  display_name TEXT NOT NULL,             -- "Milk (Cattle)"
  slug TEXT NOT NULL,
  rank TEXT DEFAULT 'taxon_part',
  kind TEXT,                              -- animal|plant|fungus (from part)
  UNIQUE(taxon_id, part_id)
);

CREATE INDEX idx_tp_taxon ON taxon_part_nodes(taxon_id);
CREATE INDEX idx_tp_part ON taxon_part_nodes(part_id);
```

### 3.3 FTS Integration

Extend the existing `nodes_fts` table to include taxon+part nodes:

#### Option A: Unified FTS Table (Recommended)

Modify `nodes_fts` to accept both taxa and taxon+part nodes:

```sql
-- Keep existing nodes_fts structure
CREATE VIRTUAL TABLE nodes_fts USING fts5(
  name,           -- "Cow Milk" or "Cattle"
  synonyms,       -- part synonyms + taxon aliases
  taxon_rank,     -- "species" or "taxon_part"
  kind            -- NULL for taxa, "animal"/"plant"/"fungus" for taxon_parts
);
```

**Populate taxon+part rows**:

```sql
INSERT INTO nodes_fts(name, synonyms, taxon_rank, kind)
SELECT
  tp.name,
  COALESCE(GROUP_CONCAT(ps.synonym, ' '), ''),
  'taxon_part',
  tp.kind
FROM taxon_part_nodes tp
LEFT JOIN part_synonym ps ON ps.part_id = tp.part_id
GROUP BY tp.id;
```

#### Option B: Separate FTS Table (Fallback)

Create `taxon_part_fts` if we want clean separation:

```sql
CREATE VIRTUAL TABLE taxon_part_fts USING fts5(
  name,           -- "Cow Milk"
  taxon_name,     -- "Cattle"
  part_name,      -- "Milk"
  synonyms        -- part synonyms
);
```

**Recommendation**: Use **Option A** for simplicity and unified search results.

### 3.4 Name Generation Logic

The quality of search results depends on intuitive names. Proposed algorithm:

```python
def generate_taxon_part_name(taxon: Taxon, part: Part) -> str:
    """
    Generate human-readable name for taxon+part combination.

    Examples:
      - Bos taurus + part:milk → "Cow Milk"
      - Gallus domesticus + part:egg → "Chicken Egg"
      - Malus domestica + part:fruit → "Apple"
    """
    # Use taxon's common name (display_name)
    taxon_name = taxon.display_name  # "Cattle" → prefer "Cow" (synonym)

    # Special handling for well-known taxa
    COMMON_NAMES = {
        "tx:...bos:taurus": "Cow",
        "tx:...capra:hircus": "Goat",
        "tx:...ovis:aries": "Sheep",
        "tx:...gallus:gallus_domesticus": "Chicken",
        "tx:...sus:scrofa_domesticus": "Pork"  # "Pig" for live, "Pork" for meat
    }
    taxon_name = COMMON_NAMES.get(taxon.id, taxon.display_name)

    part_name = part.name  # "Milk", "Egg", "Fruit"

    # Omit part name for fruits where taxon IS the common name
    if part.id == "part:fruit" and taxon.rank in ["species", "cultivar"]:
        return taxon_name  # "Apple", "Banana" (not "Apple Fruit")

    # For animal products, prefer "Part + Taxon" order
    if part.kind == "animal":
        return f"{taxon_name} {part_name}"  # "Cow Milk", "Chicken Egg"

    # For plant parts at higher ranks, use "Taxon Part"
    if taxon.rank in ["family", "genus"]:
        return f"{taxon_name} {part_name}"  # "Citrus Peel", "Wheat Grain"

    # Default: species-level plants
    return f"{taxon_name} ({part_name})"  # "Potato (Tuber)"
```

**Edge Cases**:

- **Muscle parts**: "Cattle Muscle" → "Beef" (via synonym/override table)
- **Cut parts**: "Cattle Brisket" (retain cut name)
- **Derived parts**: "Cow Cream" (from milk hierarchy)

---

## 4. ETL Pipeline Changes

### 4.1 New Compilation Step

Add step `5.3` in `etl/python/compile.py` after `has_part` materialization:

```python
# Step 5.3: Materialize taxon_part_nodes
print_step("5.3/6", "Materializing taxon+part nodes for search...")

# Create table
cur.execute("""
    CREATE TABLE taxon_part_nodes (
        id TEXT PRIMARY KEY,
        taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
        part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        display_name TEXT NOT NULL,
        slug TEXT NOT NULL,
        rank TEXT DEFAULT 'taxon_part',
        kind TEXT,
        UNIQUE(taxon_id, part_id)
    )
""")

# Common name overrides (expand as needed)
COMMON_NAMES = {
    "tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus": "Cow",
    "tx:animalia:chordata:mammalia:artiodactyla:bovidae:capra:hircus": "Goat",
    "tx:animalia:chordata:mammalia:artiodactyla:bovidae:ovis:aries": "Sheep",
    "tx:animalia:chordata:aves:galliformes:phasianidae:gallus:gallus_domesticus": "Chicken",
    "tx:animalia:chordata:mammalia:artiodactyla:suidae:sus:scrofa_domesticus": "Pork"
}

# Generate nodes from has_part table
rows = []
has_part_pairs = cur.execute("SELECT taxon_id, part_id FROM has_part").fetchall()

for taxon_id, part_id in has_part_pairs:
    # Get taxon info
    taxon = cur.execute(
        "SELECT name, rank FROM nodes WHERE id = ?", (taxon_id,)
    ).fetchone()
    if not taxon:
        continue
    taxon_name, taxon_rank = taxon

    # Get part info
    part = cur.execute(
        "SELECT name, kind FROM part_def WHERE id = ?", (part_id,)
    ).fetchone()
    if not part:
        continue
    part_name, part_kind = part

    # Apply common name overrides
    display_taxon = COMMON_NAMES.get(taxon_id, taxon_name)

    # Generate name (simplified logic; expand per algorithm above)
    if part_id == "part:fruit" and taxon_rank in ["species", "cultivar", "variety"]:
        name = display_taxon
        display_name = display_taxon
    elif part_kind == "animal":
        name = f"{display_taxon} {part_name}"
        display_name = name
    else:
        name = f"{display_taxon} {part_name}"
        display_name = f"{display_taxon} ({part_name})"

    # Generate ID and slug
    tp_id = f"tp:{taxon_id}:{part_id}"
    slug = f"{taxon_id.split(':')[-1]}-{part_id.split(':')[-1]}"

    rows.append((tp_id, taxon_id, part_id, name, display_name, slug, "taxon_part", part_kind))

cur.executemany(
    "INSERT INTO taxon_part_nodes(id, taxon_id, part_id, name, display_name, slug, rank, kind) VALUES (?,?,?,?,?,?,?,?)",
    rows
)
print_success(f"Generated {len(rows)} taxon+part nodes")
```

### 4.2 FTS Population

Extend FTS5 step (currently at `6/6`) to include taxon+part nodes:

```python
# After populating nodes_fts with taxa, add taxon+part nodes:
cur.execute("""
    INSERT INTO nodes_fts(name, synonyms, taxon_rank, kind)
    SELECT
        tp.name,
        COALESCE(GROUP_CONCAT(ps.synonym, ' '), ''),
        'taxon_part',
        tp.kind
    FROM taxon_part_nodes tp
    LEFT JOIN part_synonym ps ON ps.part_id = tp.part_id
    GROUP BY tp.id
""")

tp_count = cur.execute("SELECT COUNT(*) FROM taxon_part_nodes").fetchone()[0]
print_success(f"Added {tp_count} taxon+part nodes to FTS index")
```

### 4.3 Triggers for Sync

Add triggers to keep `taxon_part_nodes` in sync with `has_part`:

```sql
-- Trigger: When has_part row added, regenerate taxon+part node
CREATE TRIGGER trg_has_part_ai AFTER INSERT ON has_part BEGIN
  INSERT OR REPLACE INTO taxon_part_nodes(id, taxon_id, part_id, name, display_name, slug, rank, kind)
  SELECT
    'tp:' || NEW.taxon_id || ':' || NEW.part_id,
    NEW.taxon_id,
    NEW.part_id,
    -- Simplified name generation (use logic from compile.py)
    (SELECT name FROM nodes WHERE id = NEW.taxon_id) || ' ' || (SELECT name FROM part_def WHERE id = NEW.part_id),
    (SELECT name FROM nodes WHERE id = NEW.taxon_id) || ' (' || (SELECT name FROM part_def WHERE id = NEW.part_id) || ')',
    (SELECT slug FROM nodes WHERE id = NEW.taxon_id) || '-' || REPLACE(NEW.part_id, 'part:', ''),
    'taxon_part',
    (SELECT kind FROM part_def WHERE id = NEW.part_id);
END;

-- Trigger: When has_part row deleted, remove taxon+part node
CREATE TRIGGER trg_has_part_ad AFTER DELETE ON has_part BEGIN
  DELETE FROM taxon_part_nodes WHERE taxon_id = OLD.taxon_id AND part_id = OLD.part_id;
END;
```

**Note**: These triggers are fallback for dynamic updates. Primary population happens in ETL compile step.

---

## 5. API Changes

### 5.1 New Search Endpoint

Enhance `search.combined` procedure in `apps/api/src/router.ts`:

```typescript
search: t.router({
  combined: t.procedure
    .input(
      z.object({
        q: z.string().min(1),
        kinds: z.array(z.enum(['taxon', 'taxon_part', 'doc'])).optional(),
        limit: z.number().min(1).max(100).default(20),
      })
    )
    .query(({ input }) => {
      const { q, kinds, limit } = input;
      const docQ = q; // FTS5 default syntax

      // Nodes FTS (taxa)
      const taxonFilter =
        !kinds || kinds.includes('taxon')
          ? `SELECT n.id, n.name, n.slug, n.rank, n.parent_id as parentId,
                  bm25(nodes_fts, 1.0, 0.5) AS score, 'taxon' AS kind
           FROM nodes n
           JOIN nodes_fts fts ON n.name = fts.name AND n.rank = fts.taxon_rank
           WHERE nodes_fts MATCH ? AND fts.taxon_rank != 'taxon_part'
           ORDER BY bm25(nodes_fts) ASC
           LIMIT ?`
          : null;

      // Taxon+Part FTS (NEW)
      const taxonPartFilter =
        !kinds || kinds.includes('taxon_part')
          ? `SELECT tp.id, tp.name, tp.slug, tp.rank, tp.taxon_id as parentId,
                  bm25(nodes_fts, 1.5, 1.0) AS score, 'taxon_part' AS kind
           FROM taxon_part_nodes tp
           JOIN nodes_fts fts ON tp.name = fts.name AND fts.taxon_rank = 'taxon_part'
           WHERE nodes_fts MATCH ?
           ORDER BY bm25(nodes_fts) ASC
           LIMIT ?`
          : null;

      // Docs FTS
      const docFilter =
        !kinds || kinds.includes('doc')
          ? `SELECT d.taxon_id as id, d.display_name as name, '' as slug, d.rank,
                  NULL as parentId,
                  bm25(taxon_doc_fts, 1.0, 1.0) AS score, 'doc' AS kind
           FROM taxon_doc_fts d
           WHERE taxon_doc_fts MATCH ?
           ORDER BY bm25(taxon_doc_fts) ASC
           LIMIT ?`
          : null;

      // Combine results
      const results: any[] = [];

      if (taxonFilter) {
        const taxa = db.prepare(taxonFilter).all(q, limit) as any[];
        results.push(...taxa);
      }

      if (taxonPartFilter) {
        const taxonParts = db.prepare(taxonPartFilter).all(q, limit) as any[];
        results.push(...taxonParts);
      }

      if (docFilter) {
        const docs = db.prepare(docFilter).all(docQ, limit) as any[];
        results.push(...docs);
      }

      // Deduplicate and sort by score
      const byId = new Map<string, any>();
      for (const r of results) {
        if (!byId.has(r.id) || byId.get(r.id).score > r.score) {
          byId.set(r.id, r);
        }
      }

      return Array.from(byId.values())
        .sort((a, b) => a.score - b.score)
        .slice(0, limit);
    }),
});
```

### 5.2 New Endpoint: Get Taxon+Part Details

Add endpoint to fetch details for a taxon+part node:

```typescript
taxonomy: t.router({
  // ... existing endpoints ...

  getTaxonPart: t.procedure
    .input(z.object({ id: z.string() })) // "tp:tx:...:part:milk"
    .query(({ input }) => {
      const tp = db
        .prepare(
          `
        SELECT 
          tp.id, tp.name, tp.display_name, tp.slug, tp.rank, tp.kind,
          tp.taxon_id, tp.part_id,
          n.name as taxon_name, n.rank as taxon_rank,
          p.name as part_name
        FROM taxon_part_nodes tp
        JOIN nodes n ON n.id = tp.taxon_id
        JOIN part_def p ON p.id = tp.part_id
        WHERE tp.id = ?
      `
        )
        .get(input.id);

      if (!tp) throw new TRPCError({ code: 'NOT_FOUND' });

      return tp;
    }),
});
```

---

## 6. UI Changes (Web App)

### 6.1 Search Results Display

Update `apps/web/src/App.tsx` (or dedicated search component) to handle `taxon_part` results:

```tsx
interface SearchResult {
  id: string;
  name: string;
  kind: 'taxon' | 'taxon_part' | 'doc';
  rank: string;
  score: number;
}

function SearchResultItem({ result }: { result: SearchResult }) {
  const icon =
    result.kind === 'taxon'
      ? '🌿'
      : result.kind === 'taxon_part'
        ? '🥛' // Use part-specific emoji
        : '📄';

  const badge = result.kind === 'taxon_part' ? 'Food' : result.rank;

  return (
    <div className="search-result">
      <span>{icon}</span>
      <div>
        <strong>{result.name}</strong>
        <Badge>{badge}</Badge>
      </div>
    </div>
  );
}
```

### 6.2 Navigate to Taxon+Part Node

When user clicks a `taxon_part` result, navigate to a detail view:

**URL Pattern**: `/workbench/tp/{taxonPartId}`

**Route**: `apps/web/src/routes/workbench.tp.$id.tsx`

```tsx
import { createFileRoute } from '@tanstack/react-router';
import { trpc } from '@/lib/trpc';

export const Route = createFileRoute('/workbench/tp/$id')({
  component: TaxonPartView,
});

function TaxonPartView() {
  const { id } = Route.useParams();
  const { data } = trpc.taxonomy.getTaxonPart.useQuery({ id });

  if (!data) return <div>Loading...</div>;

  return (
    <div>
      <h1>{data.display_name}</h1>
      <p>
        Taxon:{' '}
        <Link to={`/workbench/node/${data.taxon_id}`}>{data.taxon_name}</Link>
      </p>
      <p>Part: {data.part_name}</p>

      {/* Show available transforms */}
      <TransformsPanel taxonId={data.taxon_id} partId={data.part_id} />
    </div>
  );
}
```

---

## 7. Migration Path

### 7.1 Database Migration

Add new migration: `apps/api/migrations/0005_taxon_part_nodes.sql`

```sql
-- Migration 0005: Add taxon+part nodes for search

-- Create taxon_part_nodes table (if not already created by ETL)
CREATE TABLE IF NOT EXISTS taxon_part_nodes (
  id TEXT PRIMARY KEY,
  taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  display_name TEXT NOT NULL,
  slug TEXT NOT NULL,
  rank TEXT DEFAULT 'taxon_part',
  kind TEXT,
  UNIQUE(taxon_id, part_id)
);

CREATE INDEX IF NOT EXISTS idx_tp_taxon ON taxon_part_nodes(taxon_id);
CREATE INDEX IF NOT EXISTS idx_tp_part ON taxon_part_nodes(part_id);

-- Populate from has_part (basic name generation)
INSERT OR IGNORE INTO taxon_part_nodes(id, taxon_id, part_id, name, display_name, slug, rank, kind)
SELECT
  'tp:' || hp.taxon_id || ':' || hp.part_id,
  hp.taxon_id,
  hp.part_id,
  n.name || ' ' || p.name,
  n.name || ' (' || p.name || ')',
  n.slug || '-' || REPLACE(hp.part_id, 'part:', ''),
  'taxon_part',
  p.kind
FROM has_part hp
JOIN nodes n ON n.id = hp.taxon_id
JOIN part_def p ON p.id = hp.part_id;

-- Add to FTS
INSERT INTO nodes_fts(name, synonyms, taxon_rank, kind)
SELECT
  tp.name,
  COALESCE(GROUP_CONCAT(ps.synonym, ' '), ''),
  'taxon_part',
  tp.kind
FROM taxon_part_nodes tp
LEFT JOIN part_synonym ps ON ps.part_id = tp.part_id
GROUP BY tp.id;

-- Triggers
CREATE TRIGGER IF NOT EXISTS trg_has_part_ai AFTER INSERT ON has_part BEGIN
  INSERT OR REPLACE INTO taxon_part_nodes(id, taxon_id, part_id, name, display_name, slug, rank, kind)
  SELECT
    'tp:' || NEW.taxon_id || ':' || NEW.part_id,
    NEW.taxon_id,
    NEW.part_id,
    n.name || ' ' || p.name,
    n.name || ' (' || p.name || ')',
    n.slug || '-' || REPLACE(NEW.part_id, 'part:', ''),
    'taxon_part',
    p.kind
  FROM nodes n, part_def p
  WHERE n.id = NEW.taxon_id AND p.id = NEW.part_id;

  INSERT INTO nodes_fts(name, synonyms, taxon_rank, kind)
  SELECT
    tp.name,
    COALESCE(GROUP_CONCAT(ps.synonym, ' '), ''),
    'taxon_part',
    tp.kind
  FROM taxon_part_nodes tp
  LEFT JOIN part_synonym ps ON ps.part_id = tp.part_id
  WHERE tp.taxon_id = NEW.taxon_id AND tp.part_id = NEW.part_id
  GROUP BY tp.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_has_part_ad AFTER DELETE ON has_part BEGIN
  DELETE FROM taxon_part_nodes WHERE taxon_id = OLD.taxon_id AND part_id = OLD.part_id;
  DELETE FROM nodes_fts WHERE rowid IN (
    SELECT rowid FROM nodes_fts WHERE taxon_rank = 'taxon_part'
    -- Note: FTS cleanup is approximate; full rebuild recommended
  );
END;
```

### 7.2 ETL Update

Update `etl/python/compile.py` to include step `5.3` (see Section 4.1).

**Testing**: Run full ETL rebuild:

```bash
cd etl
python python/compile.py --in dist/compiled --out dist/database/graph.dev.sqlite
```

### 7.3 API Update

1. Update `apps/api/src/router.ts` with new search logic (Section 5.1)
2. Add `getTaxonPart` endpoint (Section 5.2)
3. Run API locally: `pnpm --filter @nutrition/api dev`

### 7.4 Web UI Update

1. Add search result handling for `taxon_part` kind
2. Create route `workbench.tp.$id.tsx`
3. Test search: query "milk", "egg", "apple"

---

## 8. Testing Plan

### 8.1 ETL Tests

**Smoke Test**: Add to `data/tests/smoke/taxon_part_search.json`

```json
{
  "name": "Taxon+Part Search Smoke Tests",
  "tests": [
    {
      "query": "milk",
      "expected_results": ["Cow Milk", "Goat Milk", "Sheep Milk"],
      "kind": "taxon_part"
    },
    {
      "query": "egg",
      "expected_results": ["Chicken Egg"],
      "kind": "taxon_part"
    },
    {
      "query": "apple",
      "expected_results": ["Apple"],
      "kind": "taxon_part"
    }
  ]
}
```

**Validation Checks**:

- All `has_part` rows have corresponding `taxon_part_nodes` entry
- FTS index includes all taxon+part nodes
- No duplicate names for same taxon+part combination

### 8.2 API Tests

**Unit Tests** (`apps/api/src/router.test.ts`):

```typescript
describe('search.combined', () => {
  it('returns taxon_part results for "milk"', async () => {
    const results = await caller.search.combined({
      q: 'milk',
      kinds: ['taxon_part'],
    });
    expect(results).toContainEqual(
      expect.objectContaining({ name: 'Cow Milk', kind: 'taxon_part' })
    );
  });

  it('ranks taxon_part higher than taxon for food queries', async () => {
    const results = await caller.search.combined({ q: 'milk' });
    const firstResult = results[0];
    expect(firstResult.kind).toBe('taxon_part'); // "Cow Milk" before "Cattle"
  });
});
```

### 8.3 UI Tests

**Manual QA Checklist**:

- [ ] Search for "milk" → see "Cow Milk", "Goat Milk", "Sheep Milk"
- [ ] Click "Cow Milk" → navigate to `/workbench/tp/tp:tx:...:part:milk`
- [ ] Detail page shows taxon lineage and part info
- [ ] Transform panel shows applicable transforms (e.g., `tf:ferment`, `tf:skim`)

---

## 9. Phase 2: Transform Chains (Future)

### Scope

Materialize common derived foods as taxon+part+transform nodes:

**Examples**:

- **Buttermilk**: `tp:...bos:taurus:part:milk` + `tf:churn`
- **Yogurt**: `tp:...bos:taurus:part:milk` + `tf:ferment{starter=yogurt_thermo}`
- **Skim Milk**: `tp:...bos:taurus:part:milk` + `tf:standardize_fat{fat_pct=0.5}`

### Challenges

1. **Combinatorial Explosion**: Many taxa × parts × transforms
2. **Naming**: "Cow Yogurt" vs "Yogurt (Cow)" vs "Yogurt"
3. **Canonicalization**: Which transforms to materialize?

### Proposed Approach

- Create `taxon_part_transform_nodes` table for **curated** combinations only
- Use `transform_applicability` rules to filter valid transforms
- Limit to `identity=true` transforms (per foodstate logic)
- Add search synonyms: "yogurt" → `tp:...bos:taurus:part:milk/tf:ferment`

**Deferred to**: ADR 0003 (pending approval)

---

## 10. Open Questions & Risks

### 10.1 Open Questions

1. **Part Hierarchy Handling**: Should "Cream" appear as its own taxon+part node, or only as a child of "Milk"?
   - **Recommendation**: Materialize both; use `parent_id` in `part_def` for UI grouping

2. **Muscle vs. Meat Names**: "Cattle Muscle" is technically correct but "Beef" is expected.
   - **Recommendation**: Add `part_override_names` table mapping `(taxon, part) → display_name`

3. **Search Ranking**: Should taxon+part nodes always rank above pure taxa?
   - **Recommendation**: Use higher BM25 weight (1.5 vs 1.0) for taxon_part results

### 10.2 Risks

| Risk                                                     | Likelihood | Impact | Mitigation                                          |
| -------------------------------------------------------- | ---------- | ------ | --------------------------------------------------- |
| **Naming conflicts**: "Apple" for fruit vs. "Apple Seed" | Medium     | High   | Use name generation algorithm with rank-aware logic |
| **Performance**: Large FTS table                         | Low        | Medium | FTS5 handles 10K+ rows efficiently; add pagination  |
| **Data quality**: Missing part synonyms                  | Medium     | Low    | Incremental enrichment post-launch                  |
| **User confusion**: Taxon vs. taxon+part in UI           | Medium     | Medium | Clear visual distinction (icons, badges)            |

---

## 11. Success Metrics

### Pre-Launch

- [ ] ETL compiles without errors
- [ ] 100+ taxon+part nodes generated
- [ ] All smoke tests pass
- [ ] FTS search returns expected results

### Post-Launch (Week 1)

- [ ] 80%+ of food searches return taxon+part results
- [ ] Average search result relevance score > 0.7 (user feedback)
- [ ] Zero production errors related to taxon+part nodes

### Long-Term (Month 1)

- [ ] User searches predominantly target taxon+part nodes (60%+ CTR)
- [ ] Ontology coverage: 90% of common foods have taxon+part entry
- [ ] Phase 2 (transforms) scoped and approved

---

## 12. Appendices

### A. Example Data

**has_part rows** (existing):

```
tx:animalia:...:bos:taurus, part:milk
tx:animalia:...:capra:hircus, part:milk
tx:animalia:...:ovis:aries, part:milk
tx:animalia:...:gallus:gallus_domesticus, part:egg
tx:plantae:...:malus:domestica, part:fruit
```

**Generated taxon_part_nodes**:

```
tp:tx:animalia:...:bos:taurus:part:milk, "Cow Milk", taxon_part, animal
tp:tx:animalia:...:capra:hircus:part:milk, "Goat Milk", taxon_part, animal
tp:tx:animalia:...:ovis:aries:part:milk, "Sheep Milk", taxon_part, animal
tp:tx:animalia:...:gallus:gallus_domesticus:part:egg, "Chicken Egg", taxon_part, animal
tp:tx:plantae:...:malus:domestica:part:fruit, "Apple", taxon_part, plant
```

### B. SQL Queries Reference

**Search for "milk"**:

```sql
SELECT tp.name, tp.kind, bm25(nodes_fts) AS score
FROM taxon_part_nodes tp
JOIN nodes_fts fts ON tp.name = fts.name AND fts.taxon_rank = 'taxon_part'
WHERE nodes_fts MATCH 'milk'
ORDER BY score ASC
LIMIT 10;
```

**Get all parts for a taxon** (existing):

```sql
WITH RECURSIVE lineage(id) AS (
  SELECT id FROM nodes WHERE id = 'tx:animalia:...:bos:taurus'
  UNION ALL
  SELECT n.parent_id FROM nodes n JOIN lineage l ON n.id = l.id WHERE n.parent_id IS NOT NULL
)
SELECT DISTINCT p.id, p.name
FROM has_part hp
JOIN part_def p ON p.id = hp.part_id
WHERE hp.taxon_id IN (SELECT id FROM lineage);
```

---

## 13. Decision Log

| Date       | Decision                                            | Rationale                                               |
| ---------- | --------------------------------------------------- | ------------------------------------------------------- |
| 2025-09-30 | Use unified `nodes_fts` table for taxa + taxon+part | Simplifies search logic; single BM25 ranking            |
| 2025-09-30 | Defer transform chains to Phase 2                   | Avoid complexity; validate core taxon+part search first |
| 2025-09-30 | Use `taxon_part` as special rank value              | Enables filtering in queries without new schema         |
| 2025-09-30 | Generate names at ETL compile time                  | Ensures consistency; avoids runtime overhead            |

---

## 14. Next Steps

1. **Review & Approve**: Stakeholder sign-off on proposal
2. **Implement ETL Changes**: Add step `5.3` to `compile.py` (1 day)
3. **Database Migration**: Create `0005_taxon_part_nodes.sql` (0.5 days)
4. **API Updates**: Extend search endpoint (1 day)
5. **UI Updates**: Add taxon+part result handling (1 day)
6. **Testing**: Smoke tests + manual QA (1 day)
7. **Deploy**: Roll out to dev environment (0.5 days)
8. **Monitor**: Track search metrics for 1 week
9. **Phase 2 Planning**: Scope transform chains (pending feedback)

**Total Effort**: ~5-6 days (1 engineer)

---

_End of Proposal_
Awesome—here’s a **tight, revised plan** that bakes in your feedback (implicit parts, leaf-only policy with kingdom fallbacks, no doc FTS, ontology-friendly changes, and a curated path for Phase 2).

# Revised Plan — Taxon ✕ Part Search (v2)

## 0) What’s changing vs. v1

- **Implicit parts**: “Honeycrisp” resolves to fruit, “Potato” to tuber, but we don’t show “(fruit)”/“(tuber)” when it’s obvious.
- **No doc search**: Docs are out of the FTS story.
- **Ontology-first**: we add small, expressive rules files; minimal code hardcoding.
- **Leaf-first materialization** with **kingdom policies + exceptions**; breeds can co-exist with species (e.g., Wagyu beef and beef).
- **Separate FTS for taxon_part** remains (safer, cleaner).
- **Phase 2 (derived foods)** is curated via a data file.

---

## 1) Ontology assets (new/updated)

### A) Implied parts (new)

`data/ontology/rules/implied_parts.jsonl`

```jsonl
{"applies_to":["tx:plantae:...:malus:"],"part":"part:fruit","exclude":[]}
{"applies_to":["tx:plantae:...:solanum:tuberosum"],"part":"part:tuber"}
{"applies_to":["tx:plantae:...:triticum:"],"part":"part:grain"}
{"applies_to":["tx:plantae:...:oryza:"],"part":"part:grain"}
{"applies_to":["tx:plantae:...:brassica:oleracea:var:italica"],"part":"part:flower"}
```

- Prefix-based, with optional `exclude`.
- One implied part per taxon (if multiple rules match, first specific wins).

### B) Materialization policy (new)

`data/ontology/rules/taxon_part_policy.json`

```json
{
  "default": {
    "animalia": ["species", "breed"],
    "plantae": ["species", "variety", "cultivar"],
    "fungi": ["species"]
  },
  "allowlist": [
    // optional non-leaf or higher-rank exceptions, per part
    { "taxon_id": "tx:animalia:...:bos:taurus", "parts": ["part:muscle"] },
    {
      "taxon_id": "tx:plantae:...:citrus",
      "parts": ["part:peel", "part:fruit"]
    }
  ],
  "blocklist": [
    // explicit exclusions if needed
  ]
}
```

- We **only materialize leaves** by default (no children in `nodes`) that match the allowed ranks.
- `allowlist` lets you include well-known non-leaves (rare, but there if needed).

### C) Name overrides (new)

`data/ontology/rules/name_overrides.jsonl`

```jsonl
{"taxon_id":"tx:animalia:...:bos:taurus","part_id":"part:muscle","name":"Beef","display_name":"Beef"}
{"taxon_id":"tx:animalia:...:ovis:aries","part_id":"part:muscle","name":"Lamb","display_name":"Lamb"}
{"taxon_id":"tx:animalia:...:sus:scrofa_domesticus","part_id":"part:muscle","name":"Pork","display_name":"Pork"}
{"taxon_id":"tx:animalia:...:gallus:gallus_domesticus","part_id":"part:egg","name":"Chicken Egg","display_name":"Chicken Egg"}
{"taxon_id":"tx:animalia:...:bos:taurus","part_id":"part:milk","name":"Cow Milk","display_name":"Cow Milk"}
```

- Minimal surface for “market names” and meat nomenclature.
- Breeds (e.g., Wagyu) can have their own overrides:

```jsonl
{
  "taxon_id": "tx:animalia:...:bos:taurus:breed:wagyu",
  "part_id": "part:muscle",
  "name": "Wagyu Beef"
}
```

### D) Part synonyms enrichment (update)

- Add `aliases` into `parts.json` (e.g., fruit → “flesh”, “pulp”; milk → “dairy”, “whole milk”; grain → “kernels”, “groats”).
- ETL will ingest these aliases into `part_synonym` (see §3).

### E) Phase 2 curated derived foods (new)

`data/ontology/rules/derived_foods.jsonl`

```jsonl
{
  "id": "tpt:bos_taurus:milk:yogurt",
  "taxon_id": "tx:animalia:...:bos:taurus",
  "part_id": "part:milk",
  "transforms": [
    {
      "id": "tf:ferment",
      "params": {
        "starter": "yogurt_thermo"
      }
    }
  ],
  "name": "Yogurt",
  "synonyms": [
    "Yoghurt",
    "Dahi"
  ],
  "notes": "Curated; identity-safe chain"
}
```

- Only **curated** combos appear. No combinatorial explosion.

---

## 2) Database schema (surgical additions)

Keep current schema. Add:

```sql
-- Searchable food nodes (taxon × part)
CREATE TABLE IF NOT EXISTS taxon_part_nodes (
  id TEXT PRIMARY KEY,                    -- "tp:tx:...:part:milk"
  taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  name TEXT NOT NULL,                     -- user-facing canonical label
  display_name TEXT NOT NULL,             -- may equal name
  slug TEXT NOT NULL,
  rank TEXT NOT NULL DEFAULT 'taxon_part',
  kingdom TEXT,                           -- 'animalia'|'plantae'|'fungi' (from taxon_id)
  is_implicit INTEGER NOT NULL DEFAULT 0, -- 1 if part is implied (hide suffix)
  UNIQUE(taxon_id, part_id)
);

-- Dedicated FTS for taxon_part (docs are intentionally excluded)
CREATE VIRTUAL TABLE IF NOT EXISTS taxon_part_fts
USING fts5(name, synonyms, kingdom, implicit);
```

_(No runtime triggers; ETL rebuilds these.)_

---

## 3) ETL changes (fits your current pipeline)

### Load new rules

- Parse **implied_parts**, **policy**, **name_overrides**, **derived_foods**.
- Extend parts ingestion to push **parts.json `aliases`** into `part_synonym`.

### Materialize taxon_part_nodes (after has_part / transforms)

Rules applied in order:

1. **Candidate pairs** = `has_part` rows.
2. **Leaf filter** = taxon has no children (by `nodes` table), AND taxon rank in kingdom policy allowlist; OR explicitly allowed in `policy.allowlist`.
3. **Compute `kingdom`** from `taxon_id`.
4. **Implied part?**
   - If taxon matches an implied rule for this `part_id`, set `is_implicit=1`.

5. **Name resolution**:
   - If `name_overrides` has entry → use it.
   - Else:
     - **Implicit** → `name = display_name = taxon.display_name` (e.g., “Honeycrisp”, “Potato”, “Wheat”).
       (We still index part synonyms so “fruit”, “tuber”, “grain” queries find them.)
     - **Animal** non-implicit → `"${CommonTaxon} ${PartName}"` (Cow Milk, Chicken Egg).
     - **Plant fruit at species/var/cultivar** → implicit path above will typically catch it; fallback never shows “(fruit)”.
     - **Other plants** → `"${Taxon} (${PartName})"` if not implicit and not overridden (e.g., “Potato (Peel)”).

6. **Slug** = `"{lastSeg(taxon)}-{lastSeg(part)}"` unless overridden.
7. Insert unique `(taxon_id, part_id)` rows.

### Populate `taxon_part_fts`

```sql
INSERT INTO taxon_part_fts(name, synonyms, kingdom, implicit)
SELECT
  tp.name,
  TRIM(
    COALESCE(tx_syn.syns,'') || ' ' ||
    COALESCE(pt_syn.syns,'') || ' ' ||
    CASE WHEN tp.is_implicit=1 THEN (SELECT name FROM part_def WHERE id=tp.part_id) ELSE '' END
  ),
  tp.kingdom,
  CASE tp.is_implicit WHEN 1 THEN '1' ELSE '0' END
FROM taxon_part_nodes tp
LEFT JOIN (
  SELECT node_id, GROUP_CONCAT(synonym,' ') syns
  FROM synonyms GROUP BY node_id
) tx_syn ON tx_syn.node_id = tp.taxon_id
LEFT JOIN (
  SELECT part_id, GROUP_CONCAT(synonym,' ') syns
  FROM part_synonym GROUP BY part_id
) pt_syn ON pt_syn.part_id = tp.part_id;
```

- Note: we also tuck the **part name** into synonyms when implicit, so “apple fruit” still finds “Apple”.

_(Leave existing `nodes_fts` exactly as-is.)_

---

## 4) Search behavior (API)

- **No doc FTS**: only `nodes_fts` (taxa) + `taxon_part_fts` (foods).
- **Ranking & dedupe**:
  - Execute two queries; normalize to a common shape.
  - If a **taxon_part** exists for the **same taxon** with `is_implicit=1`, **hide/demote** the raw taxon result for commodity queries.
    - Heuristic: if query tokens match the taxon’s name OR its synonyms, prefer the **implicit** `taxon_part`.

  - Weight `taxon_part` slightly higher for everyday food queries (milk, egg, apple, potato).

- **Filters**:
  - Optional param `kinds: ['taxon','taxon_part']` (default both).
  - Optional param `kingdom` filter on `taxon_part` via FTS column (for “animal milk” vs “plant milk” queries later if needed).

---

## 5) UI behavior

- Results:
  - **taxon_part** → badge “Food”; show `name` as-is (implicit items display clean: “Honeycrisp”, “Potato”).
  - **taxon** → badge with rank; generally appears when there’s no implicit mapping.

- Clicking `taxon_part`:
  - `/workbench/tp/:id` shows taxon lineage, the part (even when implicit), and **available transforms** (from current `transform_applicability`).

---

## 6) Phase 2 — Curated derived foods

- **Data-driven** via `rules/derived_foods.jsonl`.
- New table `taxon_part_transform_nodes` + `tpt_fts` (separate from v1).
- Each record must pass `composeFoodState` validation (identity-only chains).
- Names/synonyms come from the file (e.g., Yogurt, Skim Milk, Buttermilk).
- Search unions three sources: taxa, taxon_part, **tpt**; default ranking: tpt ≥ taxon_part ≥ taxon for commodity terms.

---

## 7) Testing & acceptance

**Smoke tests** (extend your existing suite):

- “milk” → Cow Milk, Goat Milk, Sheep Milk (taxon_part)
- “egg” → Chicken Egg (taxon_part)
- “honeycrisp” → Honeycrisp (implicit fruit, taxon_part, no “(fruit)”)
- “potato” → Potato (implicit tuber)
- “wheat”/“rice” → Wheat/Rice (implicit grain)
- “wagyu beef” → Wagyu Beef (breed muscle override)
- Ensure raw taxa are **not duplicated** next to their implicit food for the same string.

**ETL invariants**:

- Every `has_part` that passes policy → exactly one `taxon_part_nodes` row.
- `taxon_part_fts` count ≥ nodes count.
- No duplicates by `(taxon_id, part_id)`.
- Implicit rows have `is_implicit=1`.

---

## 8) Rollout steps

1. Add the four rules files (implied parts, policy, overrides, derived foods).
2. Update ETL:
   - Load rules, ingest parts aliases, build `taxon_part_nodes`, build `taxon_part_fts`.

3. Adjust API search combiner (union + dedupe + light boosting).
4. UI: show `taxon_part` badge; keep current workbench view.
5. Ship smoke tests; verify.

---

## 9) Why this works

- **Implicit parts** give you clean, human labels while remaining formally precise underneath.
- **Leaf-first policy** keeps the graph tidy, with escape hatches (allowlist) for iconic non-leaf lines.
- **Separate FTS** avoids destabilizing existing triggers and makes rollback trivial.
- **Data-over-code** (rules files) lets you iterate naming and coverage fast—perfect for early dev.
