# 17 — TPT Implementation Plan

**Status**: Ready to Execute  
**Author**: System  
**Date**: 2025-01-27  
**Goal**: Implement the unified T/TP/TPT food node system as outlined in the TPT Vision document.

---

## Executive Summary

This plan implements the **unified food node system** where T (Taxon), TP (Taxon+Part), and TPT (Taxon+Part+Transform) are first-class peers in search and navigation. The implementation follows the vision document's architecture while building on our existing TP foundation.

**Key Outcomes:**
- Unified `food_nodes_fts` search across all node types
- Curated TPT catalog with 25+ high-impact derived foods
- Enhanced part system with promotion rules and derived parts
- Complete API surface for food node operations
- Rich UX patterns for discovery and exploration

---

## Phase 1: Foundation & Ontology (Week 1)

### 1.1 Enhanced Parts System

**Goal**: Implement the part promotion system and derived parts as outlined in the vision.

**Tasks:**

1. **Extend Parts Schema** (`data/ontology/parts.json`)
   ```json
   {
     "id": "part:butter",
     "name": "Butter",
     "kind": "derived",
     "parent_id": "part:cream",
     "proto_path": [
       {"id": "tf:separate", "params": {"from": "milk", "to": "cream"}},
       {"id": "tf:churn", "params": {"time_min": 20}}
     ],
     "byproducts": [
       {"part_id": "part:buttermilk", "notes": "churned"}
     ]
   }
   ```

2. **Add Missing Parts**
   - `part:butter` (promoted derived part)
   - `part:buttermilk` (churned)
   - `part:curd` (cheese substrate)
   - `part:whey` (cheese byproduct)
   - `part:flour` (promoted derived part)
   - `part:soy_milk` (promoted derived part)

3. **Update ETL Pipeline** (`etl/python/compile.py`)
   - Add `kind` field to `part_def` table
   - Add `parent_id`, `proto_path`, `byproducts` fields
   - Implement part promotion validation

### 1.2 Transform System Enhancements

**Goal**: Add missing transforms and implement identity vs process parameter distinction.

**Tasks:**

1. **Add Missing Transforms** (`data/ontology/transforms.json`)
   ```json
   {
     "id": "tf:churn",
     "name": "Churn",
     "identity": true,
     "order": 20,
     "params": [
       {"key": "time_min", "kind": "number", "unit": "min"}
     ],
     "yields_hint": {
       "part": "part:butter",
       "byproducts": ["part:buttermilk"]
     }
   }
   ```

2. **Transform Categories** (add to existing transforms):
   - **Part-changing**: `tf:separate`, `tf:press`, `tf:churn`, `tf:coagulate`, `tf:split`, `tf:dehull`
   - **Identity-bearing**: `tf:ferment`, `tf:cure`, `tf:smoke`, `tf:age`, `tf:stretch`, `tf:cook_curd`, `tf:refine_oil`, `tf:dry`
   - **Non-identity**: `tf:cook`, `tf:blanch`, `tf:soak`, `tf:pasteurize`, `tf:homogenize`, `tf:standardize_fat`

3. **Identity Parameter Marking**
   - Add `identity_param: true/false` to transform parameters
   - Update `foodstate.compose()` to only include identity params in hash

### 1.3 Transform Applicability Rules

**Goal**: Add the missing applicability rules from external assessment.

**Tasks:**

1. **Add to `data/ontology/rules/transform_applicability.jsonl`**:
   ```jsonl
   {"transform":"tf:ferment","applies_to":[{"taxon_prefix":"tx:plantae:brassicaceae","parts":["part:leaf"]},{"taxon_prefix":"tx:plantae:cucurbitaceae:cucumis:sativus","parts":["part:fruit"]}]}
   {"transform":"tf:salt","applies_to":[{"taxon_prefix":"tx:plantae:brassicaceae","parts":["part:leaf"]},{"taxon_prefix":"tx:plantae:cucurbitaceae:cucumis:sativus","parts":["part:fruit"]}]}
   {"transform":"tf:strain","applies_to":[{"taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:bovidae","parts":["part:milk","part:curd","part:whey"]}]}
   {"transform":"tf:coagulate","applies_to":[{"taxon_prefix":"tx:animalia:chordata:mammalia:artiodactyla:bovidae","parts":["part:whey","part:curd"]}]}
   ```

### 1.4 Curated TPT Catalog

**Goal**: Implement the 25+ curated derived foods from external assessment.

**Tasks:**

1. **Expand `data/ontology/rules/derived_foods.jsonl`** with external assessment's curated foods:
   - Dairy: yogurt, greek yogurt, kefir, labneh, evaporated milk, sweetened condensed milk, milk powder, buttermilk, butter, ghee, mozzarella, cheddar, ricotta, feta
   - Meat: bacon, pancetta, pastrami, corned beef, smoked brisket
   - Fish: smoked salmon, gravlax, salt cod
   - Vegetables: sauerkraut, kimchi, fermented pickles
   - Oils: extra virgin olive oil, refined olive oil

2. **TPT ID Convention**: `tpt:<genus_or_species_slug>:<part_slug>:<product_slug>`
   - Example: `tpt:bos_taurus:milk:yogurt`

3. **Enhanced TPT Schema**:
   ```json
   {
     "id": "tpt:bos_taurus:milk:yogurt",
     "taxon_id": "tx:animalia:chordata:mammalia:artiodactyla:bovidae:bos:taurus",
     "part_id": "part:milk",
     "transforms": [
       {"id": "tf:ferment", "params": {"starter": "yogurt_thermo", "temp_C": 43, "time_h": 6}}
     ],
     "name": "Yogurt",
     "synonyms": ["Yoghurt", "Dahi"],
     "tags": ["dairy", "fermented"],
     "notes": "Thermophilic yogurt culture"
   }
   ```

---

## Phase 2: Database & ETL (Week 2)

### 2.1 Unified Food Nodes Schema

**Goal**: Implement the unified `food_nodes` table as the primary storage for T/TP/TPT.

**Tasks:**

1. **Create `food_nodes` Table** (`etl/python/compile.py`)
   ```sql
   CREATE TABLE food_nodes (
     id TEXT PRIMARY KEY,
     doc_type TEXT NOT NULL CHECK (doc_type IN ('T', 'TP', 'TPT')),
     taxon_id TEXT REFERENCES nodes(id) ON DELETE CASCADE,
     part_id TEXT REFERENCES part_def(id) ON DELETE CASCADE,
     transform_path TEXT, -- JSON array for TPT
     name TEXT NOT NULL,
     display_name TEXT NOT NULL,
     slug TEXT NOT NULL,
     synonyms TEXT, -- JSON array
     tags TEXT, -- JSON array
     popularity_score REAL DEFAULT 0.0,
     search_name TEXT, -- denormalized for FTS
     taxon_tokens TEXT, -- for faceting
     part_tokens TEXT,
     transform_tokens TEXT,
     created_at TEXT DEFAULT CURRENT_TIMESTAMP,
     updated_at TEXT DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. **Create `food_nodes_fts` FTS5 Table**
   ```sql
   CREATE VIRTUAL TABLE food_nodes_fts USING fts5(
     search_name,
     taxon_tokens,
     part_tokens,
     transform_tokens,
     content='food_nodes',
     content_rowid='rowid'
   );
   ```

3. **Create Edge Tables**
   ```sql
   CREATE TABLE food_node_edges (
     from_id TEXT NOT NULL,
     to_id TEXT NOT NULL,
     edge_type TEXT NOT NULL,
     PRIMARY KEY (from_id, to_id, edge_type),
     FOREIGN KEY (from_id) REFERENCES food_nodes(id) ON DELETE CASCADE,
     FOREIGN KEY (to_id) REFERENCES food_nodes(id) ON DELETE CASCADE
   );
   ```

### 2.2 ETL Pipeline Updates

**Goal**: Update ETL to materialize unified food nodes.

**Tasks:**

1. **Update `compile.py`**:
   - Add TPT materialization logic
   - Implement part promotion validation
   - Generate unified search tokens
   - Create food node edges (T→TP, TP→TPT)

2. **TPT Materialization Logic**:
   ```python
   def materialize_tpt(tpt_data):
       # Validate transforms against applicability rules
       # Generate canonical transform path
       # Create search tokens
       # Insert into food_nodes table
   ```

3. **Search Token Generation**:
   - `search_name`: name + synonyms + selected aliases
   - `taxon_tokens`: taxon family, common names
   - `part_tokens`: part name with `part:` prefix
   - `transform_tokens`: transform names, process descriptors

### 2.3 Identity Hash Implementation

**Goal**: Implement TPT identity hashing as specified in vision.

**Tasks:**

1. **Update `foodstate.compose()`** to generate TPT identity hash:
   ```typescript
   function generateTPTIdentityHash(taxonId: string, partId: string, transforms: Transform[]): string {
     const identityTransforms = transforms
       .filter(t => t.identity)
       .map(t => ({
         id: t.id,
         params: extractIdentityParams(t.params)
       }));
     
     const normalized = {
       taxonId,
       partId,
       transforms: identityTransforms.sort((a, b) => a.ordering - b.ordering)
     };
     
     return hash(JSON.stringify(normalized));
   }
   ```

2. **Identity Parameter Extraction**:
   - Only include parameters marked as `identity_param: true`
   - Exclude process parameters (time, temperature ranges)

---

## Phase 3: API Layer (Week 3)

### 3.1 Unified Search API

**Goal**: Implement the unified search across T/TP/TPT nodes.

**Tasks:**

1. **Update `search.combined`** endpoint:
   ```typescript
   search: t.router({
     combined: t.procedure
       .input(z.object({
         q: z.string(),
         docTypes: z.array(z.enum(['T', 'TP', 'TPT'])).optional(),
         filters: z.object({
           partKind: z.string().optional(),
           tags: z.array(z.string()).optional(),
           taxonFamily: z.string().optional()
         }).optional(),
         limit: z.number().default(20)
       }))
       .query(({ input }) => {
         // Unified FTS search across food_nodes_fts
         // Apply doc_type boosting
         // Apply filters
         // Return mixed results with badges
       })
   })
   ```

2. **Search Ranking Logic**:
   - Exact name match > synonym > alias > token overlap
   - Doc type boosting (TPT for commodity terms, TP for part terms, T for species terms)
   - Popularity scoring
   - Transform chain length penalty

### 3.2 Food Node Lookup API

**Goal**: Implement detailed food node lookup with context.

**Tasks:**

1. **Add `foodNodes.getById`** endpoint:
   ```typescript
   foodNodes: t.router({
     getById: t.procedure
       .input(z.object({ id: z.string() }))
       .query(({ input }) => {
         // Return normalized node payload
         // Include neighbor panel for TPT
         // Include applicable transforms for TP
       })
   })
   ```

2. **Browse Endpoints**:
   - `GET /taxa/:taxonId/parts` → top TPs
   - `GET /taxa/:taxonId/derived?partId=part:milk&tags=fermented` → curated TPTs

3. **Compile TPT Endpoint**:
   - `POST /compile-tpt` for power users and ETL validation
   - Returns canonical identity hash and diff to nearest curated TPT

### 3.3 Suggestion API

**Goal**: Implement related node suggestions.

**Tasks:**

1. **Add `suggest.related`** endpoint:
   ```typescript
   suggest: t.router({
     related: t.procedure
       .input(z.object({ seedId: z.string() }))
       .query(({ input }) => {
         // Find related nodes based on:
         // - Same taxon (different parts)
         // - Same part (different taxa)
         // - Similar transform paths
         // - Popular combinations
       })
   })
   ```

---

## Phase 4: UI Enhancements (Week 4)

### 4.1 Unified Search Interface

**Goal**: Implement the unified search UI with mixed results.

**Tasks:**

1. **Update Search Component**:
   - Mixed results list with badges ("Derived", "Part", "Taxon")
   - Transform path chips for TPT results
   - Filter sidebar (Part kind, Cuisine, "Only derived foods")
   - Intent-based result ordering

2. **Search Result Cards**:
   - TPT: Show transform timeline, variants, upstream/downstream
   - TP: Show applicable transforms, popular derived foods
   - T: Show common parts, popular derived foods

### 4.2 Enhanced Entity Pages

**Goal**: Implement rich entity pages for each node type.

**Tasks:**

1. **Taxon Pages** (e.g., Cow):
   - "Common parts" (TP grid)
   - "Popular derived foods" (TPT grid)
   - Cross-taxon suggestions ("Try with goat")

2. **Part Pages** (e.g., Milk):
   - Group TPTs by style: Fresh → Fermented → Cheese → Butter/Fat
   - Transform chips for filtering
   - Process flow visualization

3. **TPT Pages** (e.g., Bacon):
   - Hero with name, synonyms, badges
   - Transform timeline with identity params
   - Variants rail (Pancetta, Guanciale)
   - "Swap taxon/part" suggestions

### 4.3 Builder Mode

**Goal**: Implement advanced TPT builder with snapping.

**Tasks:**

1. **TPT Builder Component**:
   - Start from TP with "Add transforms" tray
   - Real-time validation and snapping to curated TPTs
   - Transform parameter forms with identity marking
   - Preview of canonical path

2. **Snapping Logic**:
   - Detect when user input matches existing TPT
   - Show "Looks like Greek yogurt → open card" suggestions
   - Highlight differences in parameters

### 4.4 Contextual Surfacing

**Goal**: Implement contextual suggestions throughout the UI.

**Tasks:**

1. **TP Page Banners**:
   - "Common derived foods from this part" when landing on TP
   - Ranked TPT chips with quick actions

2. **TPT Page Context**:
   - "Upstream" (TP & Taxon) navigation
   - "Downstream variants" (sibling TPTs)
   - Related taxa suggestions

3. **Disambiguation UI**:
   - Compact chooser for ambiguous queries
   - "Do you mean the fish (Taxon), fillet (Part) or smoked salmon (Derived)?"

---

## Phase 5: Governance & Analytics (Week 5)

### 5.1 Curation Governance

**Goal**: Implement governance and validation for TPT curation.

**Tasks:**

1. **Linter Implementation**:
   - Validate TPT ID format
   - Check transform applicability
   - Verify identity parameter usage
   - Ensure required fields (name, synonyms, rationale)

2. **PR Labels & Workflow**:
   - `derived:add`, `derived:edit`, `derived:deprecate` labels
   - Required rationale for new TPTs
   - Automated validation in CI

3. **Curation Guidelines**:
   - Document boundary rules (Part vs TPT vs promoted Part)
   - Provide decision checklist for new entries
   - Establish review process for edge cases

### 5.2 Analytics & Telemetry

**Goal**: Implement analytics for search optimization and curation.

**Tasks:**

1. **Search Analytics**:
   - Track search → click → node ID patterns
   - Monitor CTR by doc type and ranking position
   - Identify popular search terms without results

2. **Ranking Optimization**:
   - A/B test doc type boosts
   - Tune transform familiarity penalties
   - Optimize based on user engagement

3. **Curation Insights**:
   - Identify high-engagement TPTs for promotion
   - Flag low-engagement TPTs for review
   - Suggest new TPTs based on search patterns

### 5.3 Performance & Monitoring

**Goal**: Ensure system performance and reliability.

**Tasks:**

1. **Performance Optimization**:
   - FTS query optimization
   - Caching for popular searches
   - Database indexing for edge queries

2. **Monitoring & Alerting**:
   - Search latency monitoring
   - Error rate tracking
   - Database performance metrics

3. **Load Testing**:
   - Test unified search under load
   - Validate FTS performance with large catalogs
   - Ensure responsive UI with mixed results

---

## Phase 6: Expansion & Polish (Week 6)

### 6.1 Catalog Expansion

**Goal**: Expand curated TPT catalog based on usage patterns.

**Tasks:**

1. **High-Impact Additions**:
   - Grains & bakery (bread, pasta, crackers)
   - Sweets & confections (chocolate, candy)
   - Beverages (wine, beer, kombucha)
   - Spices & seasonings

2. **Regional Specialties**:
   - Asian cuisines (miso, tempeh, kimchi variants)
   - European specialties (cheese varieties, cured meats)
   - Latin American (fermented corn, chiles)

3. **Part Promotion Candidates**:
   - Evaluate TPTs for promotion to derived parts
   - Implement promotion workflow
   - Update downstream references

### 6.2 Advanced Features

**Goal**: Implement advanced features for power users.

**Tasks:**

1. **Semantic Search**:
   - Integrate embeddings for semantic similarity
   - Blend with lexical search results
   - Improve handling of synonyms and related terms

2. **Advanced Filtering**:
   - Cuisine/region filters
   - Dietary restriction filters
   - Process complexity filters

3. **Export & Integration**:
   - API for external integrations
   - Data export formats
   - Webhook notifications for changes

### 6.3 Documentation & Training

**Goal**: Complete documentation and user training materials.

**Tasks:**

1. **User Documentation**:
   - Search guide with examples
   - TPT builder tutorial
   - API documentation

2. **Curator Training**:
   - Boundary rules guide
   - Curation best practices
   - Quality assurance checklist

3. **Developer Documentation**:
   - Architecture overview
   - Extension points
   - Performance guidelines

---

## Success Metrics

### Phase 1-2 (Foundation)
- ✅ All missing transforms and parts added
- ✅ TPT catalog with 25+ curated foods
- ✅ Unified food nodes schema implemented
- ✅ ETL pipeline updated and tested

### Phase 3-4 (API & UI)
- ✅ Unified search working across T/TP/TPT
- ✅ Rich entity pages for all node types
- ✅ TPT builder with snapping
- ✅ Contextual suggestions throughout UI

### Phase 5-6 (Governance & Polish)
- ✅ Linter and governance in place
- ✅ Analytics and ranking optimization
- ✅ Performance monitoring and optimization
- ✅ Expanded catalog with 100+ TPTs

### Long-term Goals
- **User Experience**: Users can find familiar foods (TPT) instantly while discovering underlying biology
- **Curation Quality**: High-quality, culturally accurate derived foods with clear provenance
- **System Performance**: Sub-100ms search response times with unified FTS
- **Extensibility**: Clear patterns for adding new TPTs and promoting parts
- **Analytics**: Data-driven optimization of search ranking and curation

---

## Risk Mitigation

### Technical Risks
- **FTS Performance**: Implement proper indexing and query optimization
- **Data Consistency**: Robust validation and linting prevent inconsistencies
- **Migration Complexity**: Phased rollout with backward compatibility

### Product Risks
- **User Confusion**: Clear UI patterns and badges distinguish node types
- **Curation Quality**: Governance and review process ensure accuracy
- **Performance**: Monitoring and optimization prevent degradation

### Operational Risks
- **Maintenance Overhead**: Automated validation and clear patterns reduce burden
- **Scalability**: Unified architecture scales better than separate systems
- **Data Quality**: Linting and governance prevent quality issues

---

## Conclusion

This implementation plan delivers the unified T/TP/TPT food node system as envisioned, building on our existing TP foundation while adding the curated TPT layer. The phased approach ensures low-risk delivery while providing immediate user value through better search and discovery.

The result will be a coherent, scalable system where users can find familiar foods instantly while exploring the underlying biological and processing logic that defines them.
