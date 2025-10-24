# Food Graph Architecture

## Overview

The Food Graph is a comprehensive knowledge graph that models the relationship between biological sources (taxa), anatomical parts, and food products through a structured ontology and evidence-based nutrition data. The system enables precise querying of food composition, nutritional properties, and culinary transformations.

## Core Entities

### 1. Taxa (T)
Biological sources in the food system, organized hierarchically by kingdom, genus, and species.

**Format**: `tx:{kingdom}:{genus}:{species}[:{cultivar/breed}]`

**Examples**:
- `tx:p:malus:domestica` (apple)
- `tx:a:bos:taurus` (cattle)
- `tx:f:agaricus:bisporus` (button mushroom)

**Key Features**:
- NCBI taxonomy integration for verification
- Hierarchical relationships (parent/child)
- Kingdom codes: `p` (plantae), `a` (animalia), `f` (fungi)

### 2. Parts (P)
Anatomical or process-derived components of biological sources.

**Format**: `part:[segment][:segment...]`

**Examples**:
- `part:fruit` (simple part)
- `part:egg:white` (hierarchical - white is component of egg)
- `part:muscle:ribeye` (hierarchical - ribeye is cut of muscle)

**Key Features**:
- Hierarchical structure for true component relationships
- Category classification (organ, muscle, fruit, etc.)
- Applicability rules for taxon-part combinations

### 3. Transforms (TF)
Culinary and processing operations that convert raw materials into food products.

**Format**: `tf:[segment]`

**Examples**:
- `tf:ferment` (fermentation)
- `tf:cook:roast` (roasting)
- `tf:preserve:cure` (curing)

**Key Features**:
- Identity parameters (temperature, duration, method)
- Applicability rules for part-transform combinations
- Family grouping for related transforms

### 4. Transformed Products (TPT)
Concrete food products resulting from the application of transforms to taxon-part combinations.

**Format**: `tpt:{taxon_id}:{part_id}:{family}:{identity_hash}`

**Examples**:
- `tpt:tx:a:salmo:salar:part:fillet:SMOKED:abc123` (smoked salmon)
- `tpt:tx:p:lactuca:sativa:part:leaf:FRESH:def456` (fresh lettuce)

**Key Features**:
- Deterministic ID generation based on identity parameters
- Family classification (SMOKED, FERMENTED, etc.)
- Comprehensive metadata and flags

## Evidence System

### 3-Tier Evidence Mapping

The system uses a sophisticated 3-tier approach to map external nutrition data to canonical food entities:

#### Tier 1: Taxon Resolution
- Uses NCBI database for taxonomic verification
- Resolves food names to canonical taxon IDs
- Skips processed food mixtures for efficiency

#### Tier 2: TPT Construction
- Constructs Taxon-Part-Transform combinations
- Uses lineage-based part filtering
- High-confidence results bypass Tier 3

#### Tier 3: Full Curation
- Processes low-confidence cases
- Can propose new parts/transforms via overlay system
- Only runs when needed for efficiency

### Nutrient Mapping

Comprehensive mapping of external nutrition data to canonical INFOODS format:

- **FDC Integration**: Maps 86+ FDC nutrient IDs to canonical format
- **Unit Conversion**: Automatic conversion between measurement units
- **Source Quality**: Weighted aggregation based on data source reliability
- **Provenance**: Tracks original values alongside converted values

## Database Schema

### Core Tables

#### `nodes`
Primary entity table storing taxa, parts, and transforms with hierarchical relationships.

#### `edges`
Relationship table connecting entities with typed edges (parent, applies_to, etc.).

#### `tpt_nodes`
Transformed product table with identity hashes and metadata.

#### `nutrients`
Canonical nutrient definitions with INFOODS IDs and units.

#### `nutrient_row`
Evidence data with original and converted values, source tracking.

#### `evidence_mapping`
Food ID to TPT mapping with confidence scores.

#### `nutrient_profile_rollup`
Pre-computed nutrient profiles with weighted statistics.

### Key Relationships

```
taxa --[parent]--> taxa
parts --[parent]--> parts
transforms --[applies_to]--> parts
tpt_nodes --[uses]--> taxa
tpt_nodes --[uses]--> parts
tpt_nodes --[uses]--> transforms
nutrient_row --[references]--> tpt_nodes
nutrient_row --[references]--> nutrients
```

## ETL Pipeline

### Stage Overview

The ETL pipeline processes data through 7 stages (0-G):

- **Stage 0**: Validation and preprocessing
- **Stage 1**: NCBI integration and verification
- **Stage A**: Transform normalization
- **Stage B**: Substrate materialization
- **Stage C**: Derived food ingestion
- **Stage D**: Family templatization
- **Stage E**: Canonicalization and ID generation
- **Stage F**: SQLite database creation
- **Stage G**: Evidence loading and rollup computation

### Data Flow

```
Ontology JSONL → ETL Pipeline → Graph Database → API
     ↓                ↓              ↓           ↓
Raw Data → Validation → Processing → SQLite → Queries
```

## API Architecture

### tRPC-based API
- Type-safe API with automatic client generation
- GraphQL-like queries with SQLite backend
- Real-time updates and caching

### Key Endpoints
- **Search**: Full-text search across taxa, parts, and TPTs
- **Navigation**: Hierarchical browsing of food categories
- **Nutrition**: Nutrient profiles and evidence queries
- **Metadata**: Flags, families, and culinary associations

## Quality Assurance

### Validation
- Schema validation at each ETL stage
- Referential integrity checks
- Data consistency validation

### Contracts
- Stage-specific output contracts
- Automated testing and verification
- Performance monitoring

### Curation
- Manual curation workflow for edge cases
- Overlay system for temporary modifications
- Proposal system for new entities

## Performance Characteristics

### Build Performance
- Full ETL pipeline: <30 seconds
- Incremental updates: <5 seconds
- Evidence loading: <1 second per source

### Query Performance
- Search queries: <100ms
- Navigation queries: <50ms
- Nutrient queries: <200ms

### Scalability
- Supports 100K+ taxa
- Handles 1M+ TPT combinations
- Processes 10M+ nutrient data points

## Future Extensions

### Planned Features
- Multi-language support
- Regulatory compliance flags
- Culinary recipe integration
- Machine learning embeddings

### Data Sources
- Canadian Nutrient File
- European food databases
- Branded food databases
- Scientific literature integration