# Food Graph Workbench UI Vision Plan

## Overview

This document outlines the transformation of the workbench from a "nice demo" into a true ontology QA console. The plan maps directly to the new ETL2 + API capabilities and focuses on developer productivity when exploring the food graph.

## Glossary (Canonical Terms)

- **Taxon**: A node in taxonomy (`nodes`), e.g. `tx:plantae:poaceae:triticum:aestivum`
- **Part**: A physical part (`part_def`), id like `part:seed`
- **TP**: Taxon+Part; synthetic node (`taxon_part_nodes.id`) → `${taxonId}:${partId}`
- **TPT**: Taxon+Part+Transform family canon (`tpt_nodes.id`)
- **Family**: Transform family (e.g., `cook`, `process`, `ferment`) on `tpt_nodes.family`
- **Flag**: Evaluated per-TPT (`tpt_flags.flag` + `flag_type`)
- **Cuisine**: Evaluated per-TPT (`tpt_cuisines.cuisine`)
- **FS**: FoodState path string (`fs:/…/part:…/tx:…{…}/…`)

## Goals (Dev-First)

- **Expose the black box**: Let you see raw structure, identity paths, relationships, and rollups fast
- **QA the ontology**: Spot gaps, oddities, and duplicates at a glance (parts coverage, family distribution, flags/cuisines, transform usage)
- **Be linkable**: Every view deep-links (taxon, TP, TPT, family, cuisine, FS)
- **Preview "real app" features** (families, cuisines, flags) without distracting from the QA mission
- **Stage for evidence**: Reserve space/affordances to bolt nutrition evidence on later

## Implementation Progress Tracking

### Phase 0: Foundation & Routing
- [ ] Create new route files (empty stubs)
- [ ] Convert App.tsx into shell with Outlet
- [ ] Implement URL redirects from /workbench/node/$id to /workbench/taxon/$id

### Phase 1: Search & Shell Integration
- [ ] Update LeftRail to use search.suggest API v2
- [ ] Implement FS deep links helper
- [ ] Add shell top bar with API status and build info

### Phase 2: Taxon Page
- [ ] Implement Taxon Overview tab with docs, parts coverage, families
- [ ] Add Graph and Lists tabs
- [ ] Wire up neighborhood queries and navigation

### Phase 3: TP Page (Taxon+Part)
- [ ] Build TP Overview with families filter and TPT list
- [ ] Create Transforms tab (read-only explorer)
- [ ] Implement Compare tab with pinboard functionality
- [ ] Update inspector with FoodStatePanel integration

### Phase 4: TPT Page
- [ ] Create TPT Overview with identity steps and related entities
- [ ] Add Explain tab with human-friendly summaries
- [ ] Build Graph tab with lineage and relationships
- [ ] Implement Suggestions in inspector

### Phase 5: QA Browsers
- [ ] Families page with drawer and filtering
- [ ] Cuisines page with TPT results
- [ ] Flags page with safety/dietary grouping
- [ ] Search QA page with raw scores and facets

### Phase 6: Overlays & Power Tools
- [x] Implement overlay toggle chips
- [x] Add data sources for overlays
- [x] Create compare/diff functionality

### Phase 7: Meta & Diagnostics
- [ ] Build Meta page with build info and counts
- [ ] Add artifact age warnings
- [ ] Implement FTS debug readouts

## App Shell (Stays Loaded for All Routes)

### App.tsx becomes a shell with:

**Top Bar** (left → title, right → status badges & build meta):
- "Nutrition Graph Workbench"
- API status: `health.ok ? "API: OK" : "API: down"`
- Build badge (Phase 7): `schema_version`, `build_time` (age in days)

**Three-Column Layout:**
- **LeftRail** (search + outline)
- **Center**: `<Outlet/>` for page body
- **RightRail**: route-specific inspector (entity-aware)

**Keyboard Shortcuts:**
- ⌘K/CTRL+K → focus search input in LeftRail
- `g` then `t` → go to Families
- `g` then `c` → go to Cuisines
- `g` then `f` → go to Flags
- `g` then `m` → go to Meta
- `[` and `]` → previous/next tab (when page has tabs)

## Information Architecture

### Global Layout (Stays Familiar)
- **Left rail**: Search + quick filters + outline
- **Center canvas**: The thing you're actually studying (graph, lists, tables)
- **Right rail (Inspector)**: Changes with entity type; shows raw details, utilities, and actions

## Pages — Center Content + Right Inspector

### 4.1 Taxon Page `/workbench/taxon/$id`

**Queries:**
- `taxonomy.neighborhood({ id, childLimit: limit, orderBy: 'name' })`

```ts
{ node: TaxonNode, parent?: TaxonNode, children: TaxonNode[], siblings: TaxonNode[], childCount: number }
type TaxonNode = { id: string; name: string; slug: string; rank: string }
```
- `taxonomy.pathToRoot({ id })` → `TaxonNode[]` (ordered root→…→node)
- `docs.getByTaxon({ taxonId })` → `{ summary?: string; description_md?: string; tags?: string[]; updated_at?: string } | null`
- `taxonomy.partTree({ id })`

```ts
Array<{ id: string; name: string; kind?: string; applicable: boolean; identityCount: number; nonIdentityCount: number; synonyms: string[] }>
```
- `facets.familiesForTaxon({ taxonId, limit?: number })`

```ts
Array<{ family: string; count: number }>
```

**Tabs:**
- **Overview** (default):
  - Header: `NodeHeader` with lineage crumbs
  - Left: `DocsPanel`
  - Right: "Structure" block:
    - "Children" table (paged) using StructureExplorer's table style
    - "Families under this taxon" chips (from facets). Click chip → `/workbench/families?family=<id>&taxonId=${currentId}`
  - "Parts coverage" panel:
    - Read-only `PartsPanel` variant (no selection)
    - Row click → `/workbench/tp/${taxonId}/${partId}`

- **Graph**:
  - `GraphView` centered on current node; children fanout
  - **Overlays bar** (chips reflecting `overlay=`):
    - `tptCount`: badge on child node (see overlays §6)
    - `familyDiversity`: badge count
    - `docPresence`: check dot if `docs.getByTaxon(child.id)` truthy (batched endpoint optional; if not, hide)

- **Lists**:
  - Children table with paging; "Show more" increases `limit`

**Inspector (Right) — Taxon:**
- "Node facts" (id, slug, rank, parent link)
- "Part tree" (same data as `partTree`, but **clickable** row → `/workbench/tp/...`)
- "Evidence (coming soon)" placeholder with stub CTA

**Empty/Loading:**
- Skeletons for header lines, list rows
- If taxon not found → show "Not found" within page body, offer a link back to root

### 4.2 TP Page `/workbench/tp/$taxonId/$partId`

**Queries:**
- `facets.familiesForTaxonPart({ taxonId, partId })` → `{ family, count }[]`
- `tpt.listForTP({ taxonId, partId, family?, limit, offset })`

```ts
{
  rows: Array<{ id: string; name?: string; family: string; identityHash: string } & { taxonId:string; partId:string }>
  total: number
}
```
- `taxonomy.getTransformsFor({ taxonId, partId, identityOnly: false })`

```ts
Array<{ id: string; name: string; identity: boolean; family: string; ordering: number; notes?: string; schema?: Array<{ key:string; kind:'boolean'|'number'|'string'|'enum'; enum?: string[] }> }>
```

**Tabs:**
- **Overview**:
  - Header: show Taxon name + Part name ("Taxon · Part")
  - Facet chips (families) across top; clicking sets `family=` query param
  - Table of TPT rows (name|family|id copy). Row click → `/workbench/tpt/${id}`
  - Paging with `limit/offset`

- **Transforms** (read-only explorer):
  - Use `TransformsPanel` but hide the include/param controls
  - Grouped by family as it already does

- **Compare** (pinboard):
  - URL param `compare=abc,def` (<=2 ids). Page shows:
    - Side-by-side **Identity Steps** for each TPT:

```ts
steps: Array<{ index:number; tf_id:string; params:Record<string,any> }>
```

available via `tpt.get({ id })` or new lightweight `tpt.identity({ id })`
    - Diff rules:
      - Align by index; if lengths differ, missing steps show "—"
      - Param diff: mark keys where JSON.stringify differs; for numbers, compare within epsilon 1e-6
  - Each TPT row in Overview includes a "pin" toggle that adds/removes its id to `compare=`

**Inspector (Right) — TP:**
- "TP identity" block:
  - Shows `taxonId`, `partId`, `tpId` (composed `${taxonId}:${partId}`) with **copy** buttons
- "FoodState composer":
  - Reuse `FoodStatePanel` but **display-only** FS preview constructed from currently selected identity transforms if you later add selection; for now, show canonical `fs:/…/part:<partId>` (no tx chain unless we later attach an identity chain)
- "Variants quick counts" (optional): show counts per family from `facets.familiesForTaxonPart`

**Empty/Loading:**
- If no TPTs found for a family filter, show a clear empty state and "Clear family filter" action

### 4.3 TPT Page `/workbench/tpt/$id`

**Queries:**
- `tpt.get({ id })` returns:

```ts
{
  id: string
  taxonId: string
  partId: string
  family: string
  name?: string
  synonyms?: string[]
  identityHash: string
  identity: Array<{ id:string; params?:Record<string,any> }>
  flags?: Array<{ flag:string; flag_type:'safety'|'dietary'|'misc' }>
  cuisines?: string[]
  related?: { variants: string[]; siblings: string[] } // ids
}
```
- `tpt.explain({ id })` → `{ steps: Array<{ label:string; details?:string }>, friendlyName?: string }`
- `entities.get({ id })` may be redundant; prefer `tpt.get`

**Tabs:**
- **Overview**:
  - Header: name || (taxon slug + part name + family label)
  - Pills: family, flags (chip per flag), cuisines (chips)
  - Identity steps list (index, tf_id, short param string)
  - **Related**:
    - Variants (same TP, different identity) — show list of names, click to open
    - Siblings (same part+family across other taxa) — list of taxon names + click

- **Explain**:
  - Friendly chain text from `tpt.explain`
  - Toggle to show raw `identity` JSON

- **Graph**:
  - Mini graph: lineage above (taxon path), same-family siblings below, variants lateral

**Inspector (Right) — TPT:**
- Copy buttons: `id`, `taxonId`, `partId`, `identityHash`
- Suggestions:
  - API: `tptAdvanced.suggest({ seedId: id, type: 'related'|'variants'|'substitutes', limit: 10 })`
  - Show card per suggestion: title, reason/explanation, score (0–1). Click → navigate

**Empty/Loading:**
- If TPT id missing/not found → in-body "Not found" + back to TP/Taxon actions when possible (if taxonId/partId were provided via query)

## Browsers (QA Lenses)

### 5.1 Families `/workbench/families`

**Queries:**
- `browse.getFamilies({ q?, limit, offset })` → `{ rows: Array<{ id:string; label?:string; count:number }>, total:number }`
- `browse.getFamilyEntities({ family, limit, offset })` → `{ rows: TPTBrief[], total:number }`

**Features:**
- Search/filter families by name
- Click family → shows entities list below with paging
- Entity rows show: name, id, taxonId/partId (if available)
- Actions: Open TP (when taxonId/partId present) or TPT
- URL state: `q`, `family`, `limit`, `offset`

**Implementation:**
- Left panel: families list with counts
- Right panel: selected family's entities (appears when family selected)
- Paging controls for both lists
- Click-through to TP/TPT pages

### 5.2 Cuisines `/workbench/cuisines`

**Queries:**
- `browse.getCuisines({ q?, limit, offset })` → `{ rows: Array<{ cuisine:string; count:number }>, total:number }`
- `browse.getCuisineEntities({ cuisine, limit, offset })` → `{ rows: TPTBrief[], total:number }`

**Features:**
- Search/filter cuisines by name
- Click cuisine → shows entities list below with paging
- Entity rows show: name, id, taxonId/partId (if available)
- Actions: Open TP (when taxonId/partId present) or TPT
- URL state: `q`, `cuisine`, `limit`, `offset`

**Implementation:**
- Left panel: cuisines list with counts
- Right panel: selected cuisine's entities (appears when cuisine selected)
- Paging controls for both lists
- Click-through to TP/TPT pages

### 5.3 Flags `/workbench/flags`

**Queries:**
- `browse.getFlags({ q? })` → `Array<{ type:string; items: Array<{ flag:string; count:number }> }>`
- `browse.getFlagEntities({ flag, type?, limit, offset })` → `{ rows: TPTBrief[], total:number }`

**Features:**
- Search/filter flags by name
- Grouped by `flag_type` (safety, dietary, misc)
- Click flag → shows entities list below with paging
- Entity rows show: name, id
- Actions: Open TPT
- URL state: `q`, `type`, `flag`, `limit`, `offset`

**Implementation:**
- Two-column grid: flags grouped by type
- Right panel: selected flag's entities (appears when flag selected)
- Paging controls for entities list
- Click-through to TPT pages

### 5.4 Search QA `/workbench/search`

**Inputs:**
- `q`, `type` (any|taxon|tp|tpt), optional filters (`taxonId`, `partId`, `family`)

**Queries:**
- `search.query({ q, type?, taxonId?, partId?, family?, limit, offset, withScores:true, debug:true })`

```ts
{
  rows: Array<{
    ref_id?: string
    id: string
    name?: string
    display_name?: string
    kind?: string
    ref_type?: string
    taxon_id?: string
    taxonId?: string
    part_id?: string
    partId?: string
    family?: string
    rank?: string
    slug?: string
    score?: number
  }>,
  total: number,
  facets?: {
    family?: Array<{ id: string; count: number }>
    rank?: Array<{ id: string; count: number }>
  }
}
```

**Features:**
- Freeform query with type filter dropdown
- Shows bm25 scores (lower is better)
- Context column: rank (taxon), part (tp), family (tpt)
- Facet chips for family/rank filtering
- Click-through to appropriate entity pages
- URL state: `q`, `type`, `taxonId`, `partId`, `family`, `limit`, `offset`

**Implementation:**
- Query bar with type selector
- Facets panel (family chips, rank chips)
- Results table with scores and context
- Paging controls
- Debug info about scoring strategy

### 5.5 Meta `/workbench/meta`

**Queries:**
- `meta` page shows:
  - `schema_version`
  - `build_time` (UTC ISO) + "Age: X days"
  - counts stored in `meta` (`taxa_count`, `parts_count`, `substrates_count`, `tpt_count`)
- If age > 14 days, show a yellow warning pill

## Routing (Authoritative)

### Entity Routes
- **Taxon**: `/workbench/taxon/$id`
- **TP**: `/workbench/tp/$taxonId/$partId` (both include prefixes, e.g., `tx:…` and `part:…`)
- **TPT**: `/workbench/tpt/$id`
- **FS** (resolver): `/workbench/fs/$` → parse then redirect to Taxon/TP

### Browser Routes
- **Families**: `/workbench/families`
- **Cuisines**: `/workbench/cuisines`
- **Flags**: `/workbench/flags`
- **Search QA**: `/workbench/search`
- **Meta**: `/workbench/meta`

### Legacy Redirect
- `/workbench/node/$id` → **redirect** (replace) to `/workbench/taxon/$id`

### Query Params (Uniform Across Pages)
- `tab`: one of `overview|graph|lists|transforms|compare|explain`
- `limit`: int (default 50), `offset`: int (default 0)
- `family`: string (family id) — TP & Search pages
- `cuisines`: comma list — Search/Cuisines pages
- `flags`: comma list — Search/Flags pages
- `overlay`: comma list (`tptCount|familyDiversity|docPresence|identityRichness|transform:<tfId>`)
- `compare`: comma list of up to 2 TPT ids (on TP & TPT pages)
- `q`, `type`: Search QA page only (`type=any|taxon|tp|tpt`)

**URL Write Rules:**
- Debounce writes by 150ms
- Never downgrade FS-intent (i.e., when composing FS preview) — but FS composition is **inspector-only**; entity pages use canonical entity routes
- Always **read/write URL state**, no hidden duplicates in component state

## Overlays (Calculations & UI)

**Toggle location**: top of Graph/Lists (Taxon page), state in `overlay=`.

- `tptCount`
  - If viewing a **Taxon** node's children: count distinct TPTs under each child's TP set
  - Implementation fallback (client-only): when a child row comes into view, fetch `tpt.countForTaxon({ id: childId })` (lightweight endpoint), else show "·"
- `familyDiversity`
  - Count distinct `family` for TPTs under child (same strategy as above)
- `docPresence`
  - Mark child with ✔ if `docs.getByTaxon(child.id)` exists (or batched: `docs.hasDocs({ ids:string[] })` → `{ id:boolean }[]`)
- `identityRichness`
  - Average identity step length for TPTs under child (optional endpoint `tpt.avgIdentityLenForTaxon({ id })`); otherwise omit overlay
- `transform:<tfId>`
  - Heat (count) of TPT identity steps containing `tfId` under child

**Rendering:**
- Each child node/row gets small pill(s): `[#tpt] [#fam] [✔doc] [len≈x] [tx:…]`. Keep minimal to avoid clutter

## Left Rail (Search + Outline) — Spec

### Search Behavior
- Input debounced 220ms; blank input shows Outline
- API: `search.suggest({ q: string, type: 'any'|'taxon'|'tp'|'tpt', limit: number, taxonPrefix?: string })`
- Return type (strict):

```ts
type SuggestItem =
  | { kind: 'taxon'; id: string; name: string; slug: string; rank: string }
  | { kind: 'tp'; id: string; taxonId: string; partId: string; name: string; displayName?: string; slug?: string }
  | { kind: 'tpt'; id: string; taxonId: string; partId: string; family: string; name?: string };
```

**Render:**
- Show mixed list; badge by kind:
  - taxon → `rank` pill
  - tp → "Food"
  - tpt → "TPT"
- Click routes:
  - taxon → `/workbench/taxon/${id}`
  - tp → `/workbench/tp/${taxonId}/${partId}`
  - tpt → `/workbench/tpt/${id}`
- "See all results" button → `/workbench/search?q=${q}`

### Outline Panel
- API: `taxonomy.getRoot()` → id; then `taxonomy.getChildren({ id, orderBy: 'name', offset: 0, limit: 100 })`
- Click → `/workbench/taxon/${id}`

### FS Resolver (used by `/workbench/fs/$`)
- util `navigateFs(fs: string)`:
  - API: `foodstate.parse({ fs })` returns:

```ts
{ taxonPath?: string[]; partId?: string; transforms?: Array<{ id: string; params?: Record<string, any> }> }
```
  - If `taxonPath`: construct `taxonId = 'tx:' + taxonPath.slice(from kingdom).join(':')`
  - If no `partId`: navigate `/workbench/taxon/${taxonId}`
  - If `partId`: navigate `/workbench/tp/${taxonId}/${partId}` (ignore transforms for routing; they are inspector-only)

**Edge Cases:**
- If parse fails → show toast in shell: "Invalid FS string"

## API-to-UI Mapping

### Taxon Mode
- `taxonomy.neighborhood`, `taxonomy.partTree`, `docs.getByTaxon`
- `facets.familiesForTaxon`, `taxa.getDerived`
- `taxonomy.getTransformsFor` (when part selected)

### TP Mode
- `taxonomy.getTransformsFor`, `facets.familiesForTaxonPart`
- `tpt.listForTP`, `tpt.resolveBestForTP`

### TPT Mode
- `tpt.get`, `tpt.explain`, `entities.get`
- `tptAdvanced.suggest`

### Browsers
- `browse.getFamilies`, `browse.getFamilyEntities`, `browse.getCuisines`
- `search.query`, `search.suggest`

## Component Inventory & File Layout

```
apps/web/src/components/
  layout/
    LeftRail.tsx      (update)
    OverlaysBar.tsx   (new)
  inspectors/
    InspectorTaxon.tsx (new)
    InspectorTP.tsx     (new)
    InspectorTPT.tsx    (new)
  panels/
    PartsPanel.tsx     (reuse; read-only mode flag)
    TransformsPanel.tsx(reuse; read-only mode flag)
    TPTComparePanel.tsx (new)
    FamilyDrawer.tsx     (new)
    EntityList.tsx       (new; simple table w/ paging)
  shared/
    CopyButton.tsx     (new)
    FacetChips.tsx     (new)
    BadgePill.tsx      (optional)
```

**Routes:**
```
apps/web/src/routes/
  workbench.tsx            (shell host)
  workbench.index.tsx      (empty)
  workbench.node.$id.tsx   (redirect → taxon)
  workbench.fs.$.tsx       (resolver)
  workbench.taxon.$id.tsx  (new page)
  workbench.tp.$taxonId.$partId.tsx (new page)
  workbench.tpt.$id.tsx    (new page)
  workbench.families.tsx   (new page)
  workbench.cuisines.tsx   (new page)
  workbench.flags.tsx      (new page)
  workbench.search.tsx     (new page)
  workbench.meta.tsx       (new page)
```

**Lib:**
```
apps/web/src/lib/
  nav.ts         (new: navigateFs, helpers)
  url.ts         (new: read/write common query params)
  types.ts       (new: shared TS types listed above)
```

### Reuse
- LeftRail (update to use search.suggest/search.query)
- NodeHeader, StructureExplorer (taxon)
- PartsPanel (taxon inspector)
- TransformsPanel (read-only in TP)
- FoodStatePanel (TP inspector)
- ErrorBoundary, GraphView

### New Components
- **Route shells**: `TaxonPage`, `TPPage`, `TPTPage`, `FamiliesPage`, `CuisinesPage`, `FlagsPage`, `SearchQAPage`, `MetaPage`
- **Inspectors**: `InspectorTaxon`, `InspectorTP`, `InspectorTPT`
- **Tools**: `TPTComparePanel`, `FamilyDrawer`, `OverlaysBar`, `EntityList`, `FacetChips`
- **TP Components**: `TPOverview`, `TPTransforms`, `TPCompare`
- **TPT Components**: `TPTOverview`, `TPTExplain`, `TPTGraph`

## Key Flows

1. **Search → Entity**: Type → select → route by kind → tab=overview
2. **Taxon → TP**: Click part in coverage → `/tp/$taxonId/$partId`
3. **TP → TPT**: Click row in TPT list → `/tpt/$id`
4. **Compare**: Pin two TPTs anywhere → opens Compare tab preloaded

## Loading, Empty, Error — Uniform Rules

- **Loading**: use existing Skeleton styles; table rows: 6–8 gray bars; header skeleton for names
- **Empty states**: "No results" with brief hint ("Try clearing filters" / "Remove family filter")
- **Errors**: Wrap center content with `ErrorBoundary`. Show an inline error card with a Retry button (simply `query.refetch()`)
- **Pagination**: Always show `Showing N of Total` if `total` known. Next/Prev buttons disabled appropriately; update `offset` in URL

## Performance & DX

- React Query options: `{ staleTime: 30_000, keepPreviousData: true, refetchOnWindowFocus: false }`
- Lazy-load heavy comps: `GraphView`, drawer internals
- Lists under 1k → no virtualization; beyond that, cap `limit` to 200 and require filters (guardrail in UI)

## Compare/Diff Rules (TP/TPT)

- **Identity step alignment**: index-based; if families contain optional "no-op"/alias steps, show them plainly; do not attempt semantic matching (no guessing)
- **Param diff**:
  - For primitives → direct compare; numbers within `1e-6` are equal
  - For arrays → compare length & each index (no set semantics)
  - Render changed keys with a subtle highlight background

## Definition of Done — Per Phase

**Phase 0 DoD:**
- New routes compile and render placeholders
- App shell shows `<Outlet/>`
- Legacy `/workbench/node/$id` redirects to `/workbench/taxon/$id`

**Phase 1 DoD:**
- LeftRail uses `search.suggest`; results route by type
- `/workbench/fs/...` resolves and navigates
- Top bar shows API status; (build badge can be a placeholder)

**Phase 2 DoD:**
- Taxon Overview shows docs, children list, families chips, read-only parts coverage
- Graph tab renders; overlay bar visible (chips toggle but may be no-op until Phase 6)
- Lists tab paginates

**Phase 3 DoD:**
- TP Overview lists TPTs; family filter works; paging works
- Transforms tab shows grouped transforms (read-only)
- Compare tab accepts two ids from query and renders side-by-side steps
- Inspector integrates FoodStatePanel with FS preview and paste-to-navigate

**Phase 4 DoD:**
- TPT Overview shows identity steps, flags, cuisines, related
- Explain tab renders friendly chain + raw JSON toggle
- Graph tab shows lineage + center TPT + variants with clickable navigation
- Inspector suggestions list navigates

**Phase 5 DoD:**
- Families/Cuisines/Flags pages show counts and lists; filters/paging round-trip via URL
- Search QA shows raw scores, facets, and notes strategy

### Phase 5 — Exact File Contents

#### A) `apps/web/src/routes/workbench.families.tsx`

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'

export const Route = createFileRoute('/workbench/families')({
  validateSearch: (s: Record<string, unknown>) => {
    const q = typeof s.q === 'string' ? s.q : ''
    const family = typeof s.family === 'string' ? s.family : ''
    const limit = Number.isFinite(Number(s.limit)) ? Math.max(1, Number(s.limit)) : 50
    const offset = Number.isFinite(Number(s.offset)) ? Math.max(0, Number(s.offset)) : 0
    return { q, family, limit, offset }
  },
  component: FamiliesPage,
})

function FamiliesPage() {
  const router = Route.useRouter()
  const search = Route.useSearch() as { q: string; family: string; limit: number; offset: number }
  const setSearch = (patch: Partial<typeof search>) =>
    router.navigate({ to: '/workbench/families', search: (s: any) => ({ ...s, ...patch }) })

  const familiesQ = (trpc as any).browse?.getFamilies?.useQuery({
    q: search.q || undefined,
    limit: search.limit,
    offset: search.offset,
  })

  const rows: Array<any> = familiesQ?.data?.rows ?? []
  const total: number = familiesQ?.data?.total ?? rows.length

  const pickFamily = (fam: string) => setSearch({ family: fam, offset: 0 })

  const entitiesQ = (trpc as any).browse?.getFamilyEntities?.useQuery(
    {
      family: search.family || '',
      limit: search.limit,
      offset: search.offset,
    },
    { enabled: !!search.family }
  )
  const ents: any[] = entitiesQ?.data?.rows ?? []
  const entsTotal: number = entitiesQ?.data?.total ?? ents.length

  const gotoTPT = (id: string) =>
    router.navigate({ to: '/workbench/tpt/$id', params: { id } })
  const gotoTP = (taxonId: string, partId: string) =>
    router.navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId } })

  return (
    <div className="p-4 space-y-3">
      <div className="text-lg font-semibold">Families</div>

      {/* Search + selected family */}
      <div className="flex items-center gap-2">
        <Input
          placeholder="Filter families…"
          value={search.q}
          onChange={(e) => setSearch({ q: e.target.value, offset: 0 })}
        />
        <Button variant="outline" onClick={() => setSearch({ q: '', offset: 0 })} disabled={!search.q}>
          Clear
        </Button>
        <div className="ml-auto text-xs text-muted-foreground">
          {familiesQ?.isLoading ? 'Loading…' : `Total: ${total}`}
        </div>
      </div>

      {/* Families list */}
      <div className="rounded border divide-y">
        {(rows.length ? rows : []).map((r) => (
          <div key={r.id || r.family} className="p-2 flex items-center justify-between">
            <div className="min-w-0">
              <div className="text-sm font-medium truncate">{r.label || r.family || r.id}</div>
              <div className="text-[11px] text-muted-foreground">{r.id || r.family}</div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-[10px] uppercase">{r.count ?? r.tptCount ?? 0}</Badge>
              <Button size="sm" onClick={() => pickFamily(r.id || r.family)}>Open</Button>
            </div>
          </div>
        ))}
        {!rows.length && (
          <div className="p-3 text-sm text-muted-foreground">No families.</div>
        )}
      </div>

      {/* Selected family → entities */}
      {search.family && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">
              Family: <span className="font-mono">{search.family}</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {entitiesQ?.isLoading ? 'Loading…' : `Results: ${entsTotal}`}
            </div>
          </div>
          <div className="rounded border divide-y">
            {(ents.length ? ents : []).map((e) => (
              <div key={e.id} className="p-2 text-sm flex items-center justify-between">
                <div className="min-w-0">
                  <div className="truncate">{e.name || e.id}</div>
                  <div className="text-[11px] text-muted-foreground break-all">{e.id}</div>
                </div>
                <div className="flex items-center gap-2">
                  {e.taxonId && e.partId && (
                    <Button size="sm" variant="secondary" onClick={() => gotoTP(e.taxonId, e.partId)}>TP</Button>
                  )}
                  <Button size="sm" onClick={() => gotoTPT(e.id)}>TPT</Button>
                </div>
              </div>
            ))}
            {!ents.length && (
              <div className="p-3 text-sm text-muted-foreground">No entities.</div>
            )}
          </div>

          {/* simple pager */}
          <div className="flex justify-between items-center">
            <Button size="sm" variant="outline" onClick={() => setSearch({ offset: Math.max(0, search.offset - search.limit) })} disabled={search.offset <= 0}>Prev</Button>
            <div className="text-xs text-muted-foreground">offset {search.offset}</div>
            <Button size="sm" variant="outline" onClick={() => setSearch({ offset: search.offset + search.limit })} disabled={ents.length < search.limit}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}
```

#### B) `apps/web/src/routes/workbench.cuisines.tsx`

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'

export const Route = createFileRoute('/workbench/cuisines')({
  validateSearch: (s: Record<string, unknown>) => {
    const q = typeof s.q === 'string' ? s.q : ''
    const cuisine = typeof s.cuisine === 'string' ? s.cuisine : ''
    const limit = Number.isFinite(Number(s.limit)) ? Math.max(1, Number(s.limit)) : 50
    const offset = Number.isFinite(Number(s.offset)) ? Math.max(0, Number(s.offset)) : 0
    return { q, cuisine, limit, offset }
  },
  component: CuisinesPage,
})

function CuisinesPage() {
  const router = Route.useRouter()
  const search = Route.useSearch() as { q: string; cuisine: string; limit: number; offset: number }
  const setSearch = (patch: Partial<typeof search>) =>
    router.navigate({ to: '/workbench/cuisines', search: (s: any) => ({ ...s, ...patch }) })

  const cuisQ = (trpc as any).browse?.getCuisines?.useQuery({
    q: search.q || undefined,
    limit: search.limit,
    offset: search.offset,
  })

  const rows = cuisQ?.data?.rows ?? []
  const total = cuisQ?.data?.total ?? rows.length

  const pickCuisine = (c: string) => setSearch({ cuisine: c, offset: 0 })

  const entsQ = (trpc as any).browse?.getCuisineEntities?.useQuery(
    {
      cuisine: search.cuisine || '',
      limit: search.limit,
      offset: search.offset,
    },
    { enabled: !!search.cuisine }
  )
  const ents: any[] = entsQ?.data?.rows ?? []
  const entsTotal: number = entsQ?.data?.total ?? ents.length

  const gotoTPT = (id: string) =>
    router.navigate({ to: '/workbench/tpt/$id', params: { id } })
  const gotoTP = (taxonId: string, partId: string) =>
    router.navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId } })

  return (
    <div className="p-4 space-y-3">
      <div className="text-lg font-semibold">Cuisines</div>

      <div className="flex items-center gap-2">
        <Input
          placeholder="Filter cuisines…"
          value={search.q}
          onChange={(e) => setSearch({ q: e.target.value, offset: 0 })}
        />
        <Button variant="outline" onClick={() => setSearch({ q: '', offset: 0 })} disabled={!search.q}>
          Clear
        </Button>
        <div className="ml-auto text-xs text-muted-foreground">
          {cuisQ?.isLoading ? 'Loading…' : `Total: ${total}`}
        </div>
      </div>

      <div className="rounded border divide-y">
        {(rows.length ? rows : []).map((r: any) => (
          <div key={r.cuisine || r.id} className="p-2 flex items-center justify-between">
            <div className="min-w-0">
              <div className="text-sm font-medium truncate">{r.cuisine || r.id}</div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="text-[10px] uppercase">{r.count ?? r.tptCount ?? 0}</Badge>
              <Button size="sm" onClick={() => pickCuisine(r.cuisine || r.id)}>Open</Button>
            </div>
          </div>
        ))}
        {!rows.length && <div className="p-3 text-sm text-muted-foreground">No cuisines.</div>}
      </div>

      {search.cuisine && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">
              Cuisine: <span className="font-mono">{search.cuisine}</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {entsQ?.isLoading ? 'Loading…' : `Results: ${entsTotal}`}
            </div>
          </div>
          <div className="rounded border divide-y">
            {(ents.length ? ents : []).map((e) => (
              <div key={e.id} className="p-2 text-sm flex items-center justify-between">
                <div className="min-w-0">
                  <div className="truncate">{e.name || e.id}</div>
                  <div className="text-[11px] text-muted-foreground break-all">{e.id}</div>
                </div>
                <div className="flex items-center gap-2">
                  {e.taxonId && e.partId && (
                    <Button size="sm" variant="secondary" onClick={() => gotoTP(e.taxonId, e.partId)}>TP</Button>
                  )}
                  <Button size="sm" onClick={() => gotoTPT(e.id)}>TPT</Button>
                </div>
              </div>
            ))}
            {!ents.length && <div className="p-3 text-sm text-muted-foreground">No entities.</div>}
          </div>

          <div className="flex justify-between items-center">
            <Button size="sm" variant="outline" onClick={() => setSearch({ offset: Math.max(0, search.offset - search.limit) })} disabled={search.offset <= 0}>Prev</Button>
            <div className="text-xs text-muted-foreground">offset {search.offset}</div>
            <Button size="sm" variant="outline" onClick={() => setSearch({ offset: search.offset + search.limit })} disabled={ents.length < search.limit}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}
```

#### C) `apps/web/src/routes/workbench.flags.tsx`

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'
import { Input } from '@ui/input'

export const Route = createFileRoute('/workbench/flags')({
  validateSearch: (s: Record<string, unknown>) => {
    const q = typeof s.q === 'string' ? s.q : ''
    const type = typeof s.type === 'string' ? s.type : 'any' // 'safety' | 'dietary' | 'any'
    const flag = typeof s.flag === 'string' ? s.flag : ''
    const limit = Number.isFinite(Number(s.limit)) ? Math.max(1, Number(s.limit)) : 50
    const offset = Number.isFinite(Number(s.offset)) ? Math.max(0, Number(s.offset)) : 0
    return { q, type, flag, limit, offset }
  },
  component: FlagsPage,
})

function FlagsPage() {
  const router = Route.useRouter()
  const search = Route.useSearch() as { q: string; type: string; flag: string; limit: number; offset: number }
  const setSearch = (patch: Partial<typeof search>) =>
    router.navigate({ to: '/workbench/flags', search: (s: any) => ({ ...s, ...patch }) })

  const flagsQ = (trpc as any).browse?.getFlags?.useQuery({ q: search.q || undefined })
  const groups: Array<{ type: string; items: Array<{ flag: string; count: number }> }> = flagsQ?.data ?? []

  const entsQ = (trpc as any).browse?.getFlagEntities?.useQuery(
    {
      flag: search.flag || '',
      type: search.type === 'any' ? undefined : search.type,
      limit: search.limit,
      offset: search.offset,
    },
    { enabled: !!search.flag }
  )
  const ents: any[] = entsQ?.data?.rows ?? []
  const entsTotal: number = entsQ?.data?.total ?? ents.length

  const gotoTPT = (id: string) => router.navigate({ to: '/workbench/tpt/$id', params: { id } })

  return (
    <div className="p-4 space-y-3">
      <div className="text-lg font-semibold">Flags</div>

      <div className="flex items-center gap-2">
        <Input
          placeholder="Filter flags…"
          value={search.q}
          onChange={(e) => setSearch({ q: e.target.value, offset: 0 })}
        />
        <Button variant="outline" onClick={() => setSearch({ q: '', offset: 0 })} disabled={!search.q}>
          Clear
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        {groups.map((g) => (
          <div key={g.type} className="rounded border">
            <div className="px-2 py-1 text-[11px] uppercase tracking-wide text-muted-foreground border-b">{g.type}</div>
            <ul className="divide-y">
              {g.items.map((it) => (
                <li key={it.flag} className="p-2 flex items-center justify-between">
                  <div className="min-w-0 truncate">{it.flag}</div>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary" className="text-[10px] uppercase">{it.count}</Badge>
                    <Button size="sm" onClick={() => setSearch({ flag: it.flag, type: g.type, offset: 0 })}>Open</Button>
                  </div>
                </li>
              ))}
              {g.items.length === 0 && <li className="p-2 text-sm text-muted-foreground">None</li>}
            </ul>
          </div>
        ))}
        {groups.length === 0 && <div className="text-sm text-muted-foreground">No flags.</div>}
      </div>

      {search.flag && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">
              Flag: <span className="font-mono">{search.flag}</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {entsQ?.isLoading ? 'Loading…' : `Results: ${entsTotal}`}
            </div>
          </div>
          <div className="rounded border divide-y">
            {(ents.length ? ents : []).map((e) => (
              <div key={e.id} className="p-2 text-sm flex items-center justify-between">
                <div className="min-w-0">
                  <div className="truncate">{e.name || e.id}</div>
                  <div className="text-[11px] text-muted-foreground break-all">{e.id}</div>
                </div>
                <Button size="sm" onClick={() => gotoTPT(e.id)}>TPT</Button>
              </div>
            ))}
            {!ents.length && <div className="p-3 text-sm text-muted-foreground">No entities.</div>}
          </div>

          <div className="flex justify-between items-center">
            <Button size="sm" variant="outline" onClick={() => setSearch({ offset: Math.max(0, search.offset - search.limit) })} disabled={search.offset <= 0}>Prev</Button>
            <div className="text-xs text-muted-foreground">offset {search.offset}</div>
            <Button size="sm" variant="outline" onClick={() => setSearch({ offset: search.offset + search.limit })} disabled={ents.length < search.limit}>Next</Button>
          </div>
        </div>
      )}
    </div>
  )
}
```

#### D) `apps/web/src/routes/workbench.search.tsx`

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React, { useMemo } from 'react'
import { trpc } from '@/lib/trpc'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'
import { Separator } from '@ui/separator'

type ResultKind = 'any' | 'taxon' | 'tp' | 'tpt'

export const Route = createFileRoute('/workbench/search')({
  validateSearch: (s: Record<string, unknown>) => {
    const q = typeof s.q === 'string' ? s.q : ''
    const type: ResultKind = (['any','taxon','tp','tpt'] as const).includes(s.type as any) ? (s.type as ResultKind) : 'any'
    const taxonId = typeof s.taxonId === 'string' ? s.taxonId : ''
    const partId = typeof s.partId === 'string' ? s.partId : ''
    const family = typeof s.family === 'string' ? s.family : ''
    const limit = Number.isFinite(Number(s.limit)) ? Math.max(1, Number(s.limit)) : 50
    const offset = Number.isFinite(Number(s.offset)) ? Math.max(0, Number(s.offset)) : 0
    return { q, type, taxonId, partId, family, limit, offset }
  },
  component: SearchQA,
})

function SearchQA() {
  const router = Route.useRouter()
  const search = Route.useSearch() as {
    q: string; type: ResultKind; taxonId: string; partId: string; family: string; limit: number; offset: number
  }
  const setSearch = (patch: Partial<typeof search>) =>
    router.navigate({ to: '/workbench/search', search: (s: any) => ({ ...s, ...patch }) })

  const queryQ = (trpc as any).search?.query?.useQuery({
    q: search.q || '',
    type: search.type === 'any' ? undefined : search.type,
    taxonId: search.taxonId || undefined,
    partId: search.partId || undefined,
    family: search.family || undefined,
    limit: search.limit,
    offset: search.offset,
    withScores: true,
    debug: true,
  }, { enabled: !!search.q })

  const rows: any[] = queryQ?.data?.rows ?? []
  const total: number = queryQ?.data?.total ?? rows.length
  const facets = queryQ?.data?.facets ?? {}

  const gotoTaxon = (id: string) => router.navigate({ to: '/workbench/taxon/$id', params: { id } })
  const gotoTP = (taxonId: string, partId: string) =>
    router.navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId } })
  const gotoTPT = (id: string) => router.navigate({ to: '/workbench/tpt/$id', params: { id } })

  const kindBadge = (k: string) => {
    const label = k === 'tp' ? 'food' : k
    return <Badge variant="secondary" className="text-[10px] uppercase">{label}</Badge>
  }

  const colHint = useMemo(() => {
    return search.type === 'tpt' ? 'family' : search.type === 'tp' ? 'part' : 'rank'
  }, [search.type])

  return (
    <div className="p-4 space-y-3">
      <div className="text-lg font-semibold">Search QA</div>

      {/* query bar */}
      <div className="grid grid-cols-[1fr_auto_auto_auto] gap-2 items-center">
        <Input
          placeholder='Query (e.g. "buckwheat flour")'
          value={search.q}
          onChange={(e) => setSearch({ q: e.target.value, offset: 0 })}
        />
        <select
          className="border rounded px-2 py-1 bg-background text-sm"
          value={search.type}
          onChange={(e) => setSearch({ type: e.target.value as ResultKind, offset: 0 })}
        >
          <option value="any">any</option>
          <option value="taxon">taxon</option>
          <option value="tp">tp</option>
          <option value="tpt">tpt</option>
        </select>
        <Button variant="outline" onClick={() => setSearch({ q: '', offset: 0 })} disabled={!search.q}>Clear</Button>
        <div className="text-xs text-muted-foreground text-right">{queryQ?.isLoading ? 'Loading…' : `Total: ${total}`}</div>
      </div>

      {/* facets */}
      {!!search.q && (
        <div className="rounded border p-2">
          <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">Facets</div>
          <div className="flex flex-wrap gap-2 text-xs">
            {/* family facet */}
            {(facets?.family ?? []).map((f: any) => (
              <button key={f.id} className={`px-2 py-1 rounded border ${search.family === f.id ? 'bg-muted/60' : 'bg-background hover:bg-muted/40'}`} onClick={() => setSearch({ family: search.family === f.id ? '' : f.id, offset: 0 })}>
                {f.id} <span className="text-[10px] text-muted-foreground">({f.count})</span>
              </button>
            ))}
            {/* rank facet */}
            {(facets?.rank ?? []).map((f: any) => (
              <button key={f.id} className={`px-2 py-1 rounded border ${search.type==='taxon' && search.taxonId===f.id ? 'bg-muted/60' : 'bg-background hover:bg-muted/40'}`} disabled>
                {f.id} <span className="text-[10px] text-muted-foreground">({f.count})</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* results */}
      <div className="rounded border overflow-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-muted-foreground bg-muted/40 sticky top-0">
            <tr>
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Slug / ID</th>
              <th className="text-left px-3 py-2">{colHint}</th>
              <th className="text-left px-3 py-2">Score</th>
              <th className="w-32" />
            </tr>
          </thead>
          <tbody>
            {(rows.length ? rows : []).map((r: any) => (
              <tr key={r.ref_id || r.id} className="border-t hover:bg-muted/30">
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <div className="truncate">{r.name ?? r.display_name ?? r.id}</div>
                    {kindBadge(r.kind || r.ref_type)}
                  </div>
                </td>
                <td className="px-3 py-2 text-xs text-muted-foreground break-all">
                  {r.slug ? `/${r.slug}` : r.ref_id || r.id}
                </td>
                <td className="px-3 py-2 text-xs">
                  {r.family || r.rank || r.partId || '—'}
                </td>
                <td className="px-3 py-2 text-xs">{typeof r.score === 'number' ? r.score.toFixed(3) : r.score ?? '—'}</td>
                <td className="px-3 py-2">
                  <div className="flex items-center gap-1 justify-end">
                    {r.kind === 'taxon' || r.ref_type === 'taxon' ? (
                      <Button size="sm" variant="outline" onClick={() => gotoTaxon(r.ref_id || r.id)}>Open</Button>
                    ) : r.kind === 'tp' || r.ref_type === 'tp' ? (
                      <Button size="sm" variant="outline" onClick={() => gotoTP(r.taxon_id || r.taxonId, (r.part_id || r.partId)?.replace(/^part:/,'') || '')}>Open</Button>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => gotoTPT(r.ref_id || r.id)}>Open</Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {!rows.length && (
              <tr><td colSpan={5} className="px-3 py-4 text-sm text-muted-foreground">No results.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* raw debug */}
      {!!rows.length && (
        <div className="text-[11px] text-muted-foreground">
          Showing {rows.length} of {total}. Scores are raw bm25 (lower is better).
          <Separator className="my-2" />
        </div>
      )}

      {/* pager */}
      <div className="flex justify-between items-center">
        <Button size="sm" variant="outline" onClick={() => setSearch({ offset: Math.max(0, search.offset - search.limit) })} disabled={search.offset <= 0}>Prev</Button>
        <div className="text-xs text-muted-foreground">offset {search.offset}</div>
        <Button size="sm" variant="outline" onClick={() => setSearch({ offset: search.offset + search.limit })} disabled={rows.length < search.limit}>Next</Button>
      </div>
    </div>
  )
}
```

**Phase 6 DoD:**
- Overlays chips toggle; at least `docPresence` and `tptCount` annotate rows/nodes
- Transform heat overlay accepts `transform:<tfId>` and shows counts

**Phase 7 DoD:**
- Meta page shows build info and age warning
- FTS debug note present on Search QA

## Open Edges (Already Decided)

- **No server mutation** in this pass. Everything read-only
- **Part selection in Taxon inspector** navigates to TP page (not an in-place builder)
- **FS composing** stays inside `FoodStatePanel` and is informational; don't write FS URLs
- **Pins** for compare are **URL-only** (`compare=`). No local storage
- **Flags/Cuisines** display only when present on the returned row; do not fetch them separately if not included
- **Families labels**: prefer `family_meta.label`; fallback to raw id

## QA Checklist (Manual Smoke)

- **Search**: Type "wheat" → see taxon + foods + tpt; navigate each correctly
- **Taxon**: Parts coverage shows identity/non-identity counts; families facet chips present
- **TP**: Families filter narrows the list; compare works with two selections
- **TPT**: Identity steps visible; suggestions navigation works
- **Browsers**: Families/Cuisines/Flags list with counts; drilling down yields TPT rows
- **Overlays**: Enabling overlays marks rows/nodes with badges
- **Links**: Copy/paste any entity URL → exact state reproduces
- **FS**: Pasting FS path sends you to correct taxon (and part)

## Guardrails

- Keep each new route/page rendering even when queries return empty arrays
- All navigation is **URL-first** (no hidden state required to restore a view)
- Paginated lists: never block on facets; render rows as they come
- Use existing components/styles to avoid churn

## Phase 0 & 1 — Implementation Package

### Task Checklist (Apply in Order)

1. **Create new routes (stubs)**
   - `apps/web/src/routes/workbench.taxon.$id.tsx`
   - `apps/web/src/routes/workbench.tp.$taxonId.$partId.tsx`
   - `apps/web/src/routes/workbench.tpt.$id.tsx`
   - `apps/web/src/routes/workbench.families.tsx`
   - `apps/web/src/routes/workbench.cuisines.tsx`
   - `apps/web/src/routes/workbench.flags.tsx`
   - `apps/web/src/routes/workbench.search.tsx`
   - `apps/web/src/routes/workbench.meta.tsx`

2. **Implement FS resolver & legacy redirect**
   - Replace `apps/web/src/routes/workbench.fs.$.tsx` with resolver
   - Replace `apps/web/src/routes/workbench.node.$id.tsx` to redirect → `/workbench/taxon/$id`

3. **Convert `App.tsx` into the shell with `<Outlet/>`**
   - Replace `apps/web/src/App.tsx` with shell (keeps top bar + LeftRail)

4. **Update LeftRail to use `search.suggest` and route by kind**
   - Replace `apps/web/src/components/layout/LeftRail.tsx` with v2 version

**Notes:**
- Stubs are intentionally minimal; they read URL state, render headers/tabs placeholders, and compile now
- Where new API calls are referenced, uses safe `(trpc as any)` cast so TypeScript won't block while server endpoints land

### Expected Results After Phase 0 & 1

- App loads as a **shell** with LeftRail + center **page stubs** (via `<Outlet/>`) + right inspector placeholder
- Visiting:
  - `/workbench/taxon/<id>` shows the Taxon stub with tabs
  - `/workbench/tp/<taxonId>/<partId>` shows TP stub with tabs
  - `/workbench/tpt/<id>` shows TPT stub with tabs
  - `/workbench/node/<id>` **redirects** to `/workbench/taxon/<id>`
  - `/workbench/fs/<anything>` resolves using the parser and routes to taxon/TP
- LeftRail search uses `search.suggest`; clicking routes by type (taxon/tp/tpt); Enter opens `/workbench/search?q=…`

### Phase 0 & 1 — Exact File Contents

#### A) `apps/web/src/App.tsx` (Shell with Outlet)

```tsx
import { Outlet } from '@tanstack/react-router'
import { trpc } from './lib/trpc'
import LeftRail from './components/layout/LeftRail'
import { Badge } from '@ui/badge'

export default function App() {
  const health = trpc.health.useQuery(undefined, { refetchOnWindowFocus: false })

  return (
    <div className="p-4">
      {/* Top status bar */}
      <div className="mb-3 flex items-center justify-between">
        <div className="text-lg font-semibold tracking-tight">Nutrition Graph Workbench</div>
        <div className="flex items-center gap-2 text-xs">
          <div className="hidden lg:flex text-xs text-muted-foreground px-2 py-1 rounded-md border bg-muted/30">
            Press <kbd className="mx-1 rounded border bg-background px-1">⌘</kbd><span>K</span> to search
          </div>
          {health.data?.ok ? (
            <Badge className="border-green-600">API: OK</Badge>
          ) : (
            <Badge className="border-red-600">API: down</Badge>
          )}
          {/* Build info placeholder (Phase 7 will wire real values) */}
          <Badge variant="secondary">Build: —</Badge>
        </div>
      </div>

      {/* Shell layout: Left rail / Center outlet / Right inspector placeholder */}
      <div className="grid grid-cols-[280px,1fr,420px] gap-3 h-[calc(100vh-84px)]">
        {/* Left: Search, Filters, Outline */}
        <LeftRail
          rankColor={{
            root:'bg-slate-100 text-slate-700 border-slate-200',
            domain:'bg-zinc-100 text-zinc-700 border-zinc-200',
            kingdom:'bg-emerald-100 text-emerald-700 border-emerald-200',
            phylum:'bg-teal-100 text-teal-700 border-teal-200',
            class:'bg-cyan-100 text-cyan-700 border-cyan-200',
            order:'bg-sky-100 text-sky-700 border-sky-200',
            family:'bg-teal-100 text-teal-700 border-teal-200',
            genus:'bg-cyan-100 text-cyan-700 border-cyan-200',
            species:'bg-blue-100 text-blue-700 border-blue-200',
            cultivar:'bg-violet-100 text-violet-700 border-violet-200',
            variety:'bg-violet-100 text-violet-700 border-violet-200',
            breed:'bg-violet-100 text-violet-700 border-violet-200',
            product:'bg-amber-100 text-amber-700 border-amber-200',
            form:'bg-amber-100 text-amber-700 border-amber-200',
          }}
          // These are not used anymore (routing handled inside LeftRail), keep as no-ops for compatibility
          currentId=""
          onPick={() => {}}
          onPickTP={() => {}}
        />

        {/* Center: route-driven page body */}
        <div className="min-h-0 flex flex-col">
          <Outlet />
        </div>

        {/* Right: inspector placeholder (entity-specific inspectors land in Phase 2+) */}
        <div className="min-h-0 flex flex-col gap-3">
          <div className="flex-1 min-h-0 border rounded-md p-3 text-sm text-muted-foreground">
            Inspector — will adapt to Taxon / TP / TPT in later phases.
          </div>
        </div>
      </div>
    </div>
  )
}
```

#### B) `apps/web/src/routes/workbench.node.$id.tsx` (Legacy Redirect)

```tsx
import { createFileRoute, redirect } from '@tanstack/react-router'

export const Route = createFileRoute('/workbench/node/$id')({
  beforeLoad: ({ params }) => {
    throw redirect({ to: '/workbench/taxon/$id', params: { id: params.id }, replace: true })
  },
  component: () => null,
})
```

#### C) `apps/web/src/routes/workbench.fs.$.tsx` (FS Resolver)

```tsx
import { createFileRoute, useRouter } from '@tanstack/react-router'
import React, { useEffect } from 'react'
import { trpc } from '@/lib/trpc'

export const Route = createFileRoute('/workbench/fs/$')({
  component: FSResolver,
})

function FSResolver() {
  const router = useRouter()
  const { $: splat } = Route.useParams()
  // splat is the entire tail after /workbench/fs/
  const fs = React.useMemo(() => 'fs:/' + decodeURIComponent(splat || ''), [splat])

  const parseQ = (trpc as any).foodstate?.parse?.useQuery({ fs }, { retry: 0 })

  useEffect(() => {
    const d = parseQ?.data as any
    if (!d) return
    let taxonId: string | null = null
    const kingdoms = ['plantae', 'animalia', 'fungi']
    if (Array.isArray(d.taxonPath)) {
      const ki = d.taxonPath.findIndex((s: string) => kingdoms.includes(s))
      if (ki >= 0) taxonId = 'tx:' + d.taxonPath.slice(ki).join(':')
    }
    if (taxonId) {
      if (d.partId) {
        router.navigate({ to: `/workbench/tp/${taxonId}/${d.partId}`, replace: true })
      } else {
        router.navigate({ to: `/workbench/taxon/${taxonId}`, replace: true })
      }
    } else {
      router.navigate({ to: '/workbench', replace: true })
    }
  }, [parseQ?.data, router])

  return <div className="p-4 text-sm text-muted-foreground">Resolving FoodState…</div>
}
```

#### D) `apps/web/src/routes/workbench.taxon.$id.tsx` (Stub)

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/workbench/taxon/$id')({
  component: TaxonPage,
})

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      className={`text-xs px-2 py-1 rounded border ${active ? 'bg-muted/60' : 'bg-background hover:bg-muted/40'}`}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

function TaxonPage() {
  const { id } = Route.useParams()
  const search = Route.useSearch<{ tab?: 'overview' | 'graph' | 'lists' }>()
  const tab = search.tab ?? 'overview'
  const router = Route.useRouter()

  const setTab = (t: typeof tab) => {
    router.navigate({ to: '/workbench/taxon/$id', params: { id }, search: (s: any) => ({ ...s, tab: t }) })
  }

  return (
    <div className="min-h-0 flex flex-col">
      <div className="rounded-md border p-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-base font-semibold">Taxon</div>
            <div className="text-xs text-muted-foreground break-all">{id}</div>
          </div>
          <div className="flex gap-1">
            <TabButton active={tab === 'overview'} onClick={() => setTab('overview')}>Overview</TabButton>
            <TabButton active={tab === 'graph'} onClick={() => setTab('graph')}>Graph</TabButton>
            <TabButton active={tab === 'lists'} onClick={() => setTab('lists')}>Lists</TabButton>
          </div>
        </div>
      </div>

      <div className="mt-3 flex-1 min-h-0 rounded-md border p-3 text-sm text-muted-foreground">
        {tab === 'overview' && <div>Overview stub — docs, parts coverage, families chips (Phase 2)</div>}
        {tab === 'graph' && <div>Graph stub — overlays bar (Phase 2/6)</div>}
        {tab === 'lists' && <div>Lists stub — paged children (Phase 2)</div>}
      </div>
    </div>
  )
}
```

#### E) `apps/web/src/routes/workbench.tp.$taxonId.$partId.tsx` (Stub)

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/workbench/tp/$taxonId.$partId')({
  component: TPPage,
})

function TPPage() {
  const { taxonId, partId } = Route.useParams()
  const search = Route.useSearch<{ tab?: 'overview' | 'transforms' | 'compare'; family?: string; compare?: string }>()
  const tab = search.tab ?? 'overview'
  const router = Route.useRouter()

  const setTab = (t: typeof tab) =>
    router.navigate({ to: '/workbench/tp/$taxonId.$partId', params: { taxonId, partId }, search: (s: any) => ({ ...s, tab: t }) })

  return (
    <div className="min-h-0 flex flex-col">
      <div className="rounded-md border p-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-base font-semibold">TP (Taxon+Part)</div>
            <div className="text-xs text-muted-foreground break-all">{taxonId} · {partId}</div>
          </div>
          <div className="flex gap-1">
            <button className={`text-xs px-2 py-1 rounded border ${tab==='overview'?'bg-muted/60':'bg-background'}`} onClick={() => setTab('overview')}>Overview</button>
            <button className={`text-xs px-2 py-1 rounded border ${tab==='transforms'?'bg-muted/60':'bg-background'}`} onClick={() => setTab('transforms')}>Transforms</button>
            <button className={`text-xs px-2 py-1 rounded border ${tab==='compare'?'bg-muted/60':'bg-background'}`} onClick={() => setTab('compare')}>Compare</button>
          </div>
        </div>
      </div>

      <div className="mt-3 flex-1 min-h-0 rounded-md border p-3 text-sm text-muted-foreground">
        {tab === 'overview' && <div>Overview stub — families filter + TPT table (Phase 3)</div>}
        {tab === 'transforms' && <div>Transforms stub — read-only explorer (Phase 3)</div>}
        {tab === 'compare' && <div>Compare stub — pinboard & identity diff (Phase 3)</div>}
      </div>
    </div>
  )
}
```

#### F) `apps/web/src/routes/workbench.tpt.$id.tsx` (Stub)

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/workbench/tpt/$id')({
  component: TPTPage,
})

function TPTPage() {
  const { id } = Route.useParams()
  const search = Route.useSearch<{ tab?: 'overview' | 'explain' | 'graph' }>()
  const tab = search.tab ?? 'overview'
  const router = Route.useRouter()
  const setTab = (t: typeof tab) => router.navigate({ to: '/workbench/tpt/$id', params: { id }, search: (s: any) => ({ ...s, tab: t }) })

  return (
    <div className="min-h-0 flex flex-col">
      <div className="rounded-md border p-3">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-base font-semibold">TPT</div>
            <div className="text-xs text-muted-foreground break-all">{id}</div>
          </div>
          <div className="flex gap-1">
            <button className={`text-xs px-2 py-1 rounded border ${tab==='overview'?'bg-muted/60':'bg-background'}`} onClick={() => setTab('overview')}>Overview</button>
            <button className={`text-xs px-2 py-1 rounded border ${tab==='explain'?'bg-muted/60':'bg-background'}`} onClick={() => setTab('explain')}>Explain</button>
            <button className={`text-xs px-2 py-1 rounded border ${tab==='graph'?'bg-muted/60':'bg-background'}`} onClick={() => setTab('graph')}>Graph</button>
          </div>
        </div>
      </div>

      <div className="mt-3 flex-1 min-h-0 rounded-md border p-3 text-sm text-muted-foreground">
        {tab === 'overview' && <div>Overview stub — identity, flags, cuisines, related (Phase 4)</div>}
        {tab === 'explain' && <div>Explain stub — friendly chain + raw JSON toggle (Phase 4)</div>}
        {tab === 'graph' && <div>Graph stub — lineage & siblings (Phase 4)</div>}
      </div>
    </div>
  )
}
```

#### G) Browser Route Stubs

**`apps/web/src/routes/workbench.families.tsx`:**
```tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/workbench/families')({
  component: () => (
    <div className="rounded-md border p-3 text-sm text-muted-foreground">
      Families browser stub — counts list + drawer (Phase 5)
    </div>
  ),
})
```

**`apps/web/src/routes/workbench.cuisines.tsx`:**
```tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/workbench/cuisines')({
  component: () => (
    <div className="rounded-md border p-3 text-sm text-muted-foreground">
      Cuisines browser stub — counts list (Phase 5)
    </div>
  ),
})
```

**`apps/web/src/routes/workbench.flags.tsx`:**
```tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/workbench/flags')({
  component: () => (
    <div className="rounded-md border p-3 text-sm text-muted-foreground">
      Flags dashboard stub — grouped by type (Phase 5)
    </div>
  ),
})
```

**`apps/web/src/routes/workbench.search.tsx`:**
```tsx
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/workbench/search')({
  validateSearch: (search: Record<string, unknown>) => {
    return {
      q: typeof search.q === 'string' ? search.q : '',
      type: (['any','taxon','tp','tpt'] as const).includes(search.type as any) ? (search.type as any) : 'any',
    }
  },
  component: SearchQA,
})

function SearchQA() {
  const search = Route.useSearch() as { q: string; type: 'any'|'taxon'|'tp'|'tpt' }
  return (
    <div className="rounded-md border p-3">
      <div className="text-sm font-medium">Search QA</div>
      <div className="text-xs text-muted-foreground">q=<code>{search.q || '∅'}</code> · type=<code>{search.type}</code></div>
      <div className="mt-3 text-sm text-muted-foreground">Results/facets/score table stub (Phase 5)</div>
    </div>
  )
}
```

**`apps/web/src/routes/workbench.meta.tsx`:**
```tsx
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/workbench/meta')({
  component: () => (
    <div className="rounded-md border p-3 text-sm">
      <div className="font-medium">Meta</div>
      <div className="text-xs text-muted-foreground">Build info & counts stub (Phase 7)</div>
    </div>
  ),
})
```

#### H) `apps/web/src/components/layout/LeftRail.tsx` (Phase-1 Search.Suggest Wiring)

```tsx
import { useEffect, useMemo, useState } from 'react'
import { trpc } from '../../lib/trpc'
import { Card, CardContent, CardHeader, CardTitle } from '@ui/card'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'
import { Separator } from '@ui/separator'
import { Skeleton } from '@ui/skeleton'
import { useRouter } from '@tanstack/react-router'

const RANKS = ['domain','kingdom','phylum','class','order','family','genus','species','product','form','cultivar','variety','breed'] as const

export default function LeftRail({
  rankColor,
  rootId,
  currentId,
  onPick,
  onPickTP,
}: {
  rankColor: Record<string, string>
  rootId?: string
  currentId: string
  onPick: (id: string) => void
  onPickTP: (taxonId: string, partId: string) => void
}) {
  const router = useRouter()

  // Search + filters
  const [qInput, setQInput] = useState('')
  const [q, setQ] = useState('')
  const [rankFilter, setRankFilter] = useState<string[]>([])

  useEffect(() => {
    const t = setTimeout(() => setQ(qInput.trim()), 220)
    return () => clearTimeout(t)
  }, [qInput])

  // v2 suggest (fallback-safe with any-cast during scaffold)
  const suggest = (trpc as any).search?.suggest?.useQuery(
    { q, type: 'any', limit: 25 },
    { enabled: q.length > 0 }
  )

  const rawResults = (suggest?.data as any[] | undefined) ?? []
  const results = useMemo(() => {
    if (!rankFilter.length) return rawResults
    return rawResults.filter((r: any) => {
      if (r.kind === 'tp' || r.kind === 'tpt') return true
      return rankFilter.includes(r.rank)
    })
  }, [rawResults, rankFilter])

  // Outline
  const childrenQ = trpc.taxonomy.getChildren.useQuery(
    { id: rootId || '', orderBy: 'name', offset: 0, limit: 100 },
    { enabled: !!rootId }
  )

  const clickResult = (row: any) => {
    if (row.kind === 'taxon') onPick(row.id)
    else if (row.kind === 'tp') onPickTP(row.taxonId, row.partId)
    else if (row.kind === 'tpt') router.navigate({ to: `/workbench/tpt/${row.id}` })
  }

  const toggleRank = (r: string) => {
    setRankFilter((prev) => (prev.includes(r) ? prev.filter((x) => x !== r) : [...prev, r]))
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Find</CardTitle>
      </CardHeader>
      <CardContent className="flex-1 min-h-0 flex flex-col gap-3">
        <div className="flex gap-2">
          <Input
            placeholder="Search taxa, foods & TPTs (⌘K)…"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && qInput.trim()) {
                router.navigate({ to: '/workbench/search', search: { q: qInput.trim(), type: 'any' } })
              }
            }}
          />
          {q && (
            <Button size="sm" variant="outline" onClick={() => { setQInput(''); setQ('') }}>
              Clear
            </Button>
          )}
        </div>

        <div className="flex flex-wrap gap-1">
          {RANKS.map((r) => (
            <button
              key={r}
              className={`text-[11px] rounded border px-1.5 py-0.5 ${rankFilter.includes(r) ? 'bg-muted/70' : 'bg-background'}`}
              onClick={() => toggleRank(r)}
            >
              {r}
            </button>
          ))}
        </div>

        {/* Results */}
        {q ? (
          <div className="flex-1 min-h-0 overflow-auto rounded-md border">
            <div className="bg-muted/50 border-b px-3 py-2 text-xs">
              {suggest?.isLoading ? 'Searching…' : `Results (${results.length})`}
            </div>
            {suggest?.isLoading ? (
              <div className="p-3 space-y-2">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Skeleton className="h-4 flex-1" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                ))}
              </div>
            ) : results.length === 0 ? (
              <div className="p-6 text-center text-sm text-muted-foreground">No results</div>
            ) : (
              <ul className="divide-y">
                {results.map((n: any) => (
                  <li
                    key={(n.kind === 'tp' || n.kind === 'tpt') ? n.id : n.id}
                    className="flex items-center justify-between px-3 py-2 text-sm cursor-pointer hover:bg-muted/40"
                    onClick={() => clickResult(n)}
                  >
                    <div className="min-w-0">
                      <div className="truncate">{n.name || n.slug || n.id}</div>
                      {n.slug && <div className="text-xs text-muted-foreground truncate">/{n.slug}</div>}
                    </div>
                    {n.kind === 'tp' ? (
                      <span className="inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase bg-amber-100 text-amber-700 border-amber-200">
                        Food
                      </span>
                    ) : n.kind === 'tpt' ? (
                      <span className="inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase bg-purple-100 text-purple-700 border-purple-200">
                        TPT
                      </span>
                    ) : (
                      <span className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${rankColor[n.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>
                        {n.rank}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <>
            <Separator />
            <div className="text-xs font-medium">Outline</div>
            <div className="text-[11px] text-muted-foreground -mt-1">Root → Kingdoms</div>
            <div className="min-h-0 overflow-auto">
              {childrenQ.isLoading ? (
                <div className="space-y-1 mt-2">
                  {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-4" />)}
                </div>
              ) : (
                <ul className="space-y-1 mt-2">
                  {(childrenQ.data as any[] | undefined)?.map((k) => (
                    <li key={k.id}>
                      <button
                        className={`w-full text-left px-2 py-1 rounded hover:bg-muted/40 ${currentId === k.id ? 'bg-muted/60' : ''}`}
                        onClick={() => onPick(k.id)}
                      >
                        <div className="flex items-center justify-between">
                          <span className="truncate">{k.name}</span>
                          <Badge variant="secondary" className="text-[10px] uppercase">{k.rank}</Badge>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
```

## Phase 2 — Taxon Page Implementation Package

### Task Checklist (Apply in Order)

1. **Create new components**
   - `apps/web/src/components/taxon/TaxonOverview.tsx`
   - `apps/web/src/components/taxon/TaxonGraph.tsx`
   - `apps/web/src/components/taxon/TaxonLists.tsx`
   - `apps/web/src/components/OverlaysBar.tsx`
   - `apps/web/src/types.ts`

2. **Update the Taxon route to use these components**
   - Replace `apps/web/src/routes/workbench.taxon.$id.tsx` with the version below

**Notes:**
- Any API that might not exist yet is accessed via `(trpc as any)` to avoid type-blockers; when your server lands them, just remove the casts
- Overlays are URL-first (`overlay=a,b,c`). Right now, they show chips and stubbed badges. Phase 6 will wire real data
- Components compile now, render sensible placeholders, and already have the query hooks wired so we can fill them in later without reshaping

### Expected Results After Phase 2

- `/workbench/taxon/:id`:
  - **Overview**: docs summary stub, parts coverage grouped by kind, families chips (if API available), derived sampler (if API available)
  - **Graph**: center node + children graph using `GraphView`; overlay chips toggle and reflect in URL (`overlay=`)
  - **Lists**: paged children table; "Show more" increases `limit` in URL and re-queries `neighborhood`
- URL state: `tab=overview|graph|lists`, `overlay=parts,identity,...`, `limit=50` (increases by 50 with "Show more")

## Phase 3 — TP Page Implementation Package

### Task Checklist (Apply in Order)

1. **Update shared types (extend the file from Phase 2)**
   - Add `TransformMeta` and `TPTLite` interfaces to `apps/web/src/types.ts`

2. **Create new TP components**
   - `apps/web/src/components/tp/TPOverview.tsx`
   - `apps/web/src/components/tp/TPTransforms.tsx`
   - `apps/web/src/components/tp/TPCompare.tsx`

3. **Update the TP route to use these components**
   - Replace `apps/web/src/routes/workbench.tp.$taxonId.$partId.tsx` with the full implementation

4. **Add TPT placeholder route**
   - Create `apps/web/src/routes/workbench.tpt.$id.tsx` as a placeholder for Phase 4

**Notes:**
- All API calls use `(trpc as any)` casts to avoid type-blockers during scaffold
- URL state includes `tab`, `families` (comma-separated), `limit`, `tpta`, `tptb` for compare pins
- Inspector integrates `FoodStatePanel` with FS preview and paste-to-navigate functionality
- Compare tab provides side-by-side identity step viewing with pinboard functionality

### Expected Results After Phase 3

- `/workbench/tp/:taxonId/:partId`:
  - **Overview**: Families facet chips (URL-backed), TPT list with paging and click-through
  - **Transforms**: Read-only explorer by family + "Resolve best TPT" (navigates)
  - **Compare**: Pin two TPTs via query params (`tpta`, `tptb`) and see side-by-side identity steps
  - **Inspector**: FoodState composer prefilled with `fs:/…/part:<id>` and FS paste-to-jump
- URL state: `tab=overview|transforms|compare`, `family=fermented,fried`, `limit=50`, `tpta=`, `tptb=`

## Phase 4 — TPT Page Implementation Package

### Task Checklist (Apply in Order)

1. **Update shared types (extend the file from Phase 3)**
   - Add `IdentityStep` and `TPTDetail` interfaces to `apps/web/src/types.ts`

2. **Create new TPT components**
   - `apps/web/src/components/tpt/TPTOverview.tsx`
   - `apps/web/src/components/tpt/TPTExplain.tsx`
   - `apps/web/src/components/tpt/TPTGraph.tsx`

3. **Update the TPT route to use these components**
   - Replace `apps/web/src/routes/workbench.tpt.$id.tsx` with the full implementation

**Notes:**
- All API calls use `(trpc as any)` casts to avoid type-blockers during scaffold
- URL state includes `tab` parameter for switching between Overview, Explain, and Graph
- Inspector integrates suggestions list and FoodStatePanel with FS preview and paste-to-navigate
- Graph tab provides lineage visualization with clickable navigation to related entities

### Expected Results After Phase 4

- `/workbench/tpt/:id`:
  - **Overview**: metadata, flags, cuisines, identity steps, and related (siblings/variants) navigation
  - **Explain**: human-readable text from `tpt.explain` + raw JSON toggle
  - **Graph**: lineage above → center TPT → variants below; clickable to navigate
  - **Inspector**: suggestions list (dev) + FoodState tools (paste FS to jump)
- URL state: `tab=overview|explain|graph`

### Phase 2 — Exact File Contents

#### A) `apps/web/src/types.ts`

```ts
export interface TaxonNode {
  id: string
  name: string
  slug: string
  rank: string
  parentId?: string | null
}

export interface Neighborhood {
  node: TaxonNode
  parent?: TaxonNode | null
  children: TaxonNode[]
  childCount: number
  siblings: Array<{ id: string; name: string }>
}

export interface PartInfo {
  id: string
  name: string
  kind?: string
  applicable: boolean
  identityCount: number
  nonIdentityCount: number
  synonyms: string[]
}

export type OverlayKey =
  | 'parts'
  | 'identity'
  | 'families'
  | 'docs'
  | 'transformUsage'

/** TP-level */
export interface TransformMeta {
  id: string
  name: string
  identity: boolean
  ordering: number
  family: string
  notes?: string | null
  /** simple schema; enough for read-only display */
  schema?: Array<{ key: string; kind: 'boolean' | 'number' | 'string' | 'enum'; enum?: string[] }> | null
}

export interface TPTLite {
  id: string
  taxonId: string
  partId: string
  family: string
  name?: string | null
  identityHash: string
}

export interface IdentityStep {
  id: string
  params?: Record<string, any> | null
}

export interface TPTDetail {
  id: string
  taxonId: string
  partId: string
  family: string
  name?: string | null
  synonyms?: string[] | null
  identity?: IdentityStep[]         // preferred
  path?: IdentityStep[]             // fallback (older API)
  identityHash?: string
  flags?: string[]                  // may also be exposed via separate endpoint
  cuisines?: string[]               // same note as flags
}
```

#### B) `apps/web/src/components/OverlaysBar.tsx`

```tsx
import { OverlayKey } from '@/types'

const OVERLAY_LABEL: Record<OverlayKey, string> = {
  parts: 'Parts availability',
  identity: 'Identity richness',
  families: 'Family diversity',
  docs: 'Docs presence',
  transformUsage: 'Transform usage',
}

export function OverlaysBar({
  active,
  onToggle,
}: {
  active: OverlayKey[]
  onToggle: (key: OverlayKey) => void
}) {
  const keys = Object.keys(OVERLAY_LABEL) as OverlayKey[]
  return (
    <div className="flex flex-wrap gap-1">
      {keys.map((k) => {
        const on = active.includes(k)
        return (
          <button
            key={k}
            className={`text-[11px] px-2 py-1 rounded border ${on ? 'bg-muted/70 border-blue-300' : 'bg-background hover:bg-muted/40'}`}
            onClick={() => onToggle(k)}
          >
            {OVERLAY_LABEL[k]}
          </button>
        )
      })}
    </div>
  )
}
```

#### C) `apps/web/src/components/taxon/TaxonOverview.tsx`

```tsx
import { trpc } from '@/lib/trpc'
import { useMemo } from 'react'
import { Badge } from '@ui/badge'
import { Separator } from '@ui/separator'
import type { PartInfo, TaxonNode } from '@/types'

export function TaxonOverview({
  id,
}: {
  id: string
}) {
  const neighborhood = trpc.taxonomy.neighborhood.useQuery(
    { id, childLimit: 25, orderBy: 'name' },
    { keepPreviousData: true }
  )
  const lineage = trpc.taxonomy.pathToRoot.useQuery({ id })
  const docs = trpc.docs.getByTaxon.useQuery({ taxonId: id })
  const parts = trpc.taxonomy.partTree.useQuery({ id })
  // Optional facets (behind any-cast during scaffold)
  const families = (trpc as any).facets?.familiesForTaxon?.useQuery({ taxonId: id })
  const derived = (trpc as any).taxa?.getDerived?.useQuery({ id, limit: 10 })

  const node = neighborhood.data?.node as TaxonNode | undefined
  const children = neighborhood.data?.children ?? []
  const childCount = neighborhood.data?.childCount ?? 0

  // Group parts by kind
  const partGroups = useMemo(() => {
    const list = (parts.data as PartInfo[] | undefined) ?? []
    const g: Record<string, PartInfo[]> = {}
    for (const p of list) {
      const k = p.kind || 'other'
      g[k] ||= []
      g[k].push(p)
    }
    return g
  }, [parts.data])

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="text-base font-semibold">{node?.name || '—'}</div>
          <div className="text-xs text-muted-foreground break-all">/{node?.slug || '—'}</div>
        </div>
        {node?.rank && (
          <Badge variant="secondary" className="text-[10px] uppercase">{node.rank}</Badge>
        )}
      </div>

      {/* Lineage crumbs */}
      <div className="text-xs text-muted-foreground flex items-center gap-1">
        {(lineage.data ?? []).map((p: any, i: number, a: any[]) => (
          <span key={p.id} className="flex items-center gap-1">
            <span className="underline">{p.name}</span>
            {i < a.length - 1 && <span>›</span>}
          </span>
        ))}
      </div>

      <Separator />

      {/* Docs summary */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Documentation</div>
        {docs.isLoading ? (
          <div className="text-sm text-muted-foreground">Loading…</div>
        ) : docs.data?.summary || docs.data?.description_md ? (
          <div className="prose prose-sm max-w-none">
            {docs.data?.summary && <p>{docs.data.summary}</p>}
            {!docs.data?.summary && docs.data?.description_md && (
              <p className="italic text-muted-foreground">Has description; summary unavailable.</p>
            )}
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">No documentation.</div>
        )}
      </div>

      {/* Parts coverage (heatmap-lite) */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Parts coverage</div>
        {parts.isLoading ? (
          <div className="text-sm text-muted-foreground">Loading parts…</div>
        ) : (
          <div className="space-y-3">
            {Object.entries(partGroups).map(([kind, rows]) => (
              <div key={kind}>
                <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-1">{kind}</div>
                <div className="grid grid-cols-2 gap-2">
                  {rows.map((p) => (
                    <div key={p.id} className={`rounded border p-2 ${p.applicable ? '' : 'opacity-50'}`}>
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-sm">{p.name}</div>
                        <div className="flex items-center gap-1">
                          {p.identityCount > 0 && (
                            <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded">
                              {p.identityCount}I
                            </span>
                          )}
                          {p.nonIdentityCount > 0 && (
                            <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded">
                              {p.nonIdentityCount}T
                            </span>
                          )}
                        </div>
                      </div>
                      <div className="text-[11px] text-muted-foreground break-all">{p.id}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
            {Object.keys(partGroups).length === 0 && (
              <div className="text-sm text-muted-foreground">No parts found.</div>
            )}
          </div>
        )}
      </div>

      {/* Families for this taxon */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Families (rollup)</div>
        {families?.isLoading ? (
          <div className="text-sm text-muted-foreground">Loading families…</div>
        ) : (families?.data?.length ?? 0) > 0 ? (
          <div className="flex flex-wrap gap-1">
            {(families?.data ?? []).slice(0, 24).map((f: any) => (
              <span key={f.family} className="text-[11px] px-2 py-0.5 rounded border bg-background">
                {f.family} <span className="text-muted-foreground">· {f.count}</span>
              </span>
            ))}
          </div>
        ) : (
          <div className="text-sm text-muted-foreground">No families found.</div>
        )}
      </div>

      {/* Derived foods sampler */}
      <div className="space-y-2">
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Derived foods (sample)</div>
        {derived?.isLoading ? (
          <div className="text-sm text-muted-foreground">Loading…</div>
        ) : (derived?.data?.length ?? 0) > 0 ? (
          <ul className="text-sm space-y-1">
            {(derived?.data ?? []).map((r: any) => (
              <li key={r.id} className="flex items-center justify-between">
                <span className="truncate">{r.name || r.id}</span>
                <Badge variant="secondary" className="text-[10px] uppercase">{r.family || 'tpt'}</Badge>
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-sm text-muted-foreground">No derived entities.</div>
        )}
        <div className="text-[11px] text-muted-foreground">Full rollups later (Phase 2+).</div>
      </div>

      {/* Children summary */}
      <div className="text-xs text-muted-foreground">
        Children shown: {(children as any[]).length}{childCount > (children as any[]).length ? ` of ${childCount}` : ''}
      </div>
    </div>
  )
}
```

#### D) `apps/web/src/components/taxon/TaxonGraph.tsx`

```tsx
import { useMemo } from 'react'
import GraphView from '@/components/GraphView'
import { OverlaysBar } from '@/components/OverlaysBar'
import type { OverlayKey, TaxonNode } from '@/types'
import type { Edge, Node } from 'reactflow'
import { Badge } from '@ui/badge'

export function TaxonGraph({
  node,
  children,
  overlays,
  onToggleOverlay,
}: {
  node?: TaxonNode
  children: TaxonNode[]
  overlays: OverlayKey[]
  onToggleOverlay: (k: OverlayKey) => void
}) {
  const { nodes, edges } = useMemo(() => {
    if (!node) return { nodes: [] as Node[], edges: [] as Edge[] }
    const ns: Node[] = [
      {
        id: node.id,
        type: 'taxon',
        position: { x: 0, y: 0 },
        data: { ...node, isCenter: true, childCount: children.length },
      },
    ]
    const es: Edge[] = []
    children.forEach((c, i) => {
      ns.push({
        id: c.id,
        type: 'taxon',
        position: { x: (i - (children.length - 1) / 2) * 220, y: 160 },
        data: { ...c, isCenter: false },
      })
      es.push({ id: `${node.id}->${c.id}`, source: node.id, target: c.id, type: 'smoothstep' } as Edge)
    })
    return { nodes: ns, edges: es }
  }, [node, children])

  return (
    <div className="space-y-3">
      <OverlaysBar active={overlays} onToggle={onToggleOverlay} />
      <GraphView nodes={nodes} edges={edges} layout="tree" />
      {overlays.length > 0 && (
        <div className="text-xs text-muted-foreground">
          {/* Placeholder legend to prove overlay state plumbs through */}
          Active overlays:{' '}
          {overlays.map((k) => (
            <Badge key={k} variant="secondary" className="text-[10px] uppercase mr-1">{k}</Badge>
          ))}
        </div>
      )}
    </div>
  )
}
```

#### E) `apps/web/src/components/taxon/TaxonLists.tsx`

```tsx
import { RANK_COLOR } from '@/lib/constants'
import type { TaxonNode } from '@/types'

export function TaxonLists({
  rows,
  total,
  limit,
  onShowMore,
  onPick,
}: {
  rows: TaxonNode[]
  total: number
  limit: number
  onShowMore: () => void
  onPick: (id: string) => void
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-sm font-medium">Children</div>
        <div className="text-xs text-muted-foreground">
          Showing {rows.length}{total > rows.length ? ` of ${total}` : ''}
        </div>
      </div>
      <div className="min-h-0 overflow-auto rounded border">
        <table className="w-full text-sm">
          <thead className="text-xs text-muted-foreground bg-muted/40 sticky top-0">
            <tr>
              <th className="text-left font-medium px-3 py-2">Name</th>
              <th className="text-left font-medium px-3 py-2">Slug</th>
              <th className="text-left font-medium px-3 py-2">Rank</th>
              <th className="w-8"></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr
                key={r.id}
                className="group border-t hover:bg-muted/30 cursor-pointer"
                onClick={() => onPick(r.id)}
              >
                <td className="px-3 py-2">{r.name}</td>
                <td className="px-3 py-2 text-xs text-muted-foreground">/{r.slug}</td>
                <td className="px-3 py-2">
                  <span className={`inline-flex items-center rounded border px-2 py-0.5 text-[10px] uppercase ${RANK_COLOR[r.rank] || 'bg-zinc-100 text-zinc-700 border-zinc-200'}`}>{r.rank}</span>
                </td>
                <td className="px-3 py-2 pr-3 text-right">
                  <span className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground">→</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {total > rows.length && (
        <div className="mt-2 flex justify-center">
          <button
            className="text-xs px-3 py-1 rounded border bg-background hover:bg-muted/40"
            onClick={onShowMore}
          >
            Show more
          </button>
        </div>
      )}
      <div className="text-[11px] text-muted-foreground">
        Paging is client-driven via <code>childLimit</code> query param to neighborhood (stub).
      </div>
    </div>
  )
}
```

#### F) `apps/web/src/routes/workbench.taxon.$id.tsx` (Updated)

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'
import { trpc } from '@/lib/trpc'
import { TaxonOverview } from '@/components/taxon/TaxonOverview'
import { TaxonGraph } from '@/components/taxon/TaxonGraph'
import { TaxonLists } from '@/components/taxon/TaxonLists'
import type { OverlayKey, TaxonNode } from '@/types'

export const Route = createFileRoute('/workbench/taxon/$id')({
  validateSearch: (search: Record<string, unknown>) => {
    const tab = (['overview','graph','lists'] as const).includes(search.tab as any) ? (search.tab as any) : 'overview'
    const overlayStr = typeof search.overlay === 'string' ? search.overlay : ''
    const overlays = overlayStr
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean) as OverlayKey[]
    const limit = Number.isFinite(Number(search.limit)) ? Math.max(10, Math.min(500, Number(search.limit))) : 50
    return { tab, overlays, limit }
  },
  component: TaxonPage,
})

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      className={`text-xs px-2 py-1 rounded border ${active ? 'bg-muted/60' : 'bg-background hover:bg-muted/40'}`}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

function TaxonPage() {
  const { id } = Route.useParams()
  const router = Route.useRouter()
  const search = Route.useSearch() as { tab: 'overview' | 'graph' | 'lists'; overlays: OverlayKey[]; limit: number }

  // Neighborhood drives most views; keep data when switching tabs
  const neighborhood = trpc.taxonomy.neighborhood.useQuery(
    { id, childLimit: search.limit, orderBy: 'name' },
    { keepPreviousData: true }
  )

  const node = neighborhood.data?.node as TaxonNode | undefined
  const children = (neighborhood.data?.children ?? []) as TaxonNode[]
  const total = neighborhood.data?.childCount ?? children.length

  const setTab = (t: typeof search.tab) => {
    router.navigate({ to: '/workbench/taxon/$id', params: { id }, search: (s: any) => ({ ...s, tab: t }) })
  }
  const toggleOverlay = (k: OverlayKey) => {
    const next = search.overlays.includes(k) ? search.overlays.filter((x) => x !== k) : [...search.overlays, k]
    router.navigate({
      to: '/workbench/taxon/$id',
      params: { id },
      search: (s: any) => ({ ...s, overlays: next }),
    })
  }
  const showMore = () => {
    router.navigate({
      to: '/workbench/taxon/$id',
      params: { id },
      search: (s: any) => ({ ...s, limit: (s.limit ?? 50) + 50 }),
    })
  }

  return (
    <div className="min-h-0 flex flex-col">
      <div className="rounded-md border p-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <div className="text-base font-semibold">Taxon</div>
            <div className="text-xs text-muted-foreground break-all">{id}</div>
          </div>
          <div className="flex gap-1">
            <TabButton active={search.tab === 'overview'} onClick={() => setTab('overview')}>Overview</TabButton>
            <TabButton active={search.tab === 'graph'} onClick={() => setTab('graph')}>Graph</TabButton>
            <TabButton active={search.tab === 'lists'} onClick={() => setTab('lists')}>Lists</TabButton>
          </div>
        </div>
      </div>

      <div className="mt-3 flex-1 min-h-0 rounded-md border p-3">
        {search.tab === 'overview' && <TaxonOverview id={id} />}

        {search.tab === 'graph' && (
          <TaxonGraph
            node={node}
            children={children}
            overlays={search.overlays}
            onToggleOverlay={toggleOverlay}
          />
        )}

        {search.tab === 'lists' && (
          <TaxonLists
            rows={children}
            total={total}
            limit={search.limit}
            onShowMore={showMore}
            onPick={(childId) => router.navigate({ to: '/workbench/taxon/$id', params: { id: childId }, search })}
          />
        )}
      </div>
    </div>
  )
}
```

### Phase 3 — Exact File Contents

#### A) `apps/web/src/types.ts` (Extended)

```ts
export interface TaxonNode {
  id: string
  name: string
  slug: string
  rank: string
  parentId?: string | null
}

export interface Neighborhood {
  node: TaxonNode
  parent?: TaxonNode | null
  children: TaxonNode[]
  childCount: number
  siblings: Array<{ id: string; name: string }>
}

export interface PartInfo {
  id: string
  name: string
  kind?: string
  applicable: boolean
  identityCount: number
  nonIdentityCount: number
  synonyms: string[]
}

export type OverlayKey =
  | 'parts'
  | 'identity'
  | 'families'
  | 'docs'
  | 'transformUsage'

/** TP-level */
export interface TransformMeta {
  id: string
  name: string
  identity: boolean
  ordering: number
  family: string
  notes?: string | null
  /** simple schema; enough for read-only display */
  schema?: Array<{ key: string; kind: 'boolean' | 'number' | 'string' | 'enum'; enum?: string[] }> | null
}

export interface TPTLite {
  id: string
  taxonId: string
  partId: string
  family: string
  name?: string | null
  identityHash: string
}
```

#### B) `apps/web/src/components/tp/TPOverview.tsx`

```tsx
import { useMemo } from 'react'
import { trpc } from '@/lib/trpc'
import type { TPTLite } from '@/types'
import { Badge } from '@ui/badge'

export function TPOverview({
  taxonId,
  partId,
  families,
  limit,
  onToggleFamily,
  onShowMore,
  onOpenTPT,
}: {
  taxonId: string
  partId: string
  families: string[]
  limit: number
  onToggleFamily: (f: string) => void
  onShowMore: () => void
  onOpenTPT: (id: string) => void
}) {
  // families facet for TP
  const famQ = (trpc as any).facets?.familiesForTaxonPart?.useQuery({ taxonId, partId })
  // list TPTs for this TP
  const listQ = (trpc as any).tpt?.listForTP?.useQuery({ taxonId, partId, families, limit }, { keepPreviousData: true })

  const allFamilies: Array<{ family: string; count: number }> = famQ?.data ?? []
  const rows: TPTLite[] = listQ?.data?.rows ?? listQ?.data ?? []
  const total: number = listQ?.data?.total ?? rows.length

  const facetMap = useMemo(() => {
    const m = new Map<string, number>()
    for (const f of allFamilies) m.set(f.family, f.count)
    return m
  }, [allFamilies])

  return (
    <div className="space-y-4">
      {/* Facet chips */}
      <div>
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">Families</div>
        <div className="flex flex-wrap gap-1">
          {(allFamilies ?? []).map((f) => {
            const on = families.includes(f.family)
            return (
              <button
                key={f.family}
                className={`text-[11px] px-2 py-1 rounded border ${on ? 'bg-muted/70 border-blue-300' : 'bg-background hover:bg-muted/40'}`}
                onClick={() => onToggleFamily(f.family)}
              >
                {f.family} <span className="text-muted-foreground">· {f.count}</span>
              </button>
            )
          })}
          {(allFamilies?.length ?? 0) === 0 && (
            <div className="text-sm text-muted-foreground">No families found.</div>
          )}
        </div>
      </div>

      {/* TPT table */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">Derived entities (TPT)</div>
          <div className="text-xs text-muted-foreground">
            Showing {rows.length}{total > rows.length ? ` of ${total}` : ''}
          </div>
        </div>
        <div className="rounded border overflow-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted-foreground bg-muted/40 sticky top-0">
              <tr>
                <th className="text-left font-medium px-3 py-2">Name</th>
                <th className="text-left font-medium px-3 py-2">Family</th>
                <th className="text-left font-medium px-3 py-2">Identity</th>
                <th className="w-8"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr
                  key={r.id}
                  className="group border-t hover:bg-muted/30 cursor-pointer"
                  onClick={() => onOpenTPT(r.id)}
                >
                  <td className="px-3 py-2">{r.name || r.id}</td>
                  <td className="px-3 py-2">
                    <Badge variant="secondary" className="text-[10px] uppercase">{r.family}</Badge>
                  </td>
                  <td className="px-3 py-2 text-xs font-mono">{r.identityHash.slice(0, 10)}…</td>
                  <td className="px-3 py-2 pr-3 text-right">
                    <span className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground">→</span>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr><td className="px-3 py-4 text-sm text-muted-foreground" colSpan={4}>No results</td></tr>
              )}
            </tbody>
          </table>
        </div>
        {total > rows.length && (
          <div className="mt-2 flex justify-center">
            <button
              className="text-xs px-3 py-1 rounded border bg-background hover:bg-muted/40"
              onClick={onShowMore}
            >
              Show more
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
```

#### C) `apps/web/src/components/tp/TPTransforms.tsx`

```tsx
import { trpc } from '@/lib/trpc'
import type { TransformMeta } from '@/types'
import { Badge } from '@ui/badge'
import { Button } from '@ui/button'

export function TPTransforms({
  taxonId,
  partId,
  onResolved,
}: {
  taxonId: string
  partId: string
  onResolved: (tptId: string) => void
}) {
  const transformsQ = trpc.taxonomy.getTransformsFor.useQuery(
    { taxonId, partId, identityOnly: false },
    { keepPreviousData: true }
  )
  const resolveQ = (trpc as any).tpt?.resolveBestForTP?.useQuery(
    { taxonId, partId },
    { enabled: false }
  )

  const data: TransformMeta[] = transformsQ.data ?? []
  const grouped = data.reduce((acc: Record<string, TransformMeta[]>, t) => {
    acc[t.family] ||= []
    acc[t.family].push(t)
    return acc
  }, {})

  return (
    <div className="space-y-4 text-sm">
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">Available transforms for the selected part. (read-only)</div>
        <Button
          size="sm"
          disabled={resolveQ.isFetching}
          onClick={async () => {
            const r = await resolveQ.refetch()
            const id = r.data?.id || r.data // support either shape
            if (id) onResolved(String(id))
          }}
        >
          {resolveQ.isFetching ? 'Resolving…' : 'Resolve best TPT'}
        </Button>
      </div>

      {transformsQ.isLoading ? (
        <div className="text-muted-foreground">Loading transforms…</div>
      ) : data.length === 0 ? (
        <div className="text-muted-foreground">No transforms for this part.</div>
      ) : (
        Object.entries(grouped).map(([family, list]) => (
          <div key={family} className="space-y-2">
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground border-b pb-1">{family}</div>
            <div className="grid grid-cols-1 gap-2">
              {list
                .sort((a, b) => (a.ordering ?? 999) - (b.ordering ?? 999))
                .map((t) => (
                  <div key={t.id} className="rounded border p-2">
                    <div className="flex items-center justify-between">
                      <div className="font-medium">{t.name}</div>
                      <Badge variant={t.identity ? 'default' : 'secondary'} className="text-[10px] uppercase">
                        {t.identity ? 'identity' : 'non-identity'}
                      </Badge>
                    </div>
                    {t.notes && (
                      <div className="text-[11px] text-muted-foreground mt-1 italic">{t.notes}</div>
                    )}
                    {t.schema && t.schema.length > 0 && (
                      <div className="mt-2 grid grid-cols-2 gap-2">
                        {t.schema.map((p) => (
                          <div key={p.key} className="space-y-0.5">
                            <div className="text-[11px] text-muted-foreground">{p.key}</div>
                            <div className="text-[11px] text-muted-foreground/70">
                              {p.kind}{p.kind === 'enum' && p.enum ? `: [${p.enum.join(', ')}]` : ''}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
```

#### D) `apps/web/src/components/tp/TPCompare.tsx`

```tsx
import { useMemo } from 'react'
import { trpc } from '@/lib/trpc'
import { Input } from '@ui/input'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'

function Steps({
  id,
  label,
}: {
  id?: string
  label: string
}) {
  const getQ = id ? (trpc as any).tpt?.get?.useQuery({ id }) : null
  const steps: Array<any> = getQ?.data?.identity ?? getQ?.data?.path ?? []
  const meta = getQ?.data

  return (
    <div className="rounded border p-2 min-h-[200px]">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-medium">{label}</div>
        {id && <Badge variant="secondary" className="text-[10px] uppercase">TPT</Badge>}
      </div>
      {!id ? (
        <div className="text-sm text-muted-foreground">Pin a TPT on the left.</div>
      ) : getQ?.isLoading ? (
        <div className="text-sm text-muted-foreground">Loading…</div>
      ) : steps.length === 0 ? (
        <div className="text-sm text-muted-foreground">No identity steps.</div>
      ) : (
        <ol className="text-sm list-decimal ml-4 space-y-1">
          {steps.map((s: any, i: number) => (
            <li key={i}>
              <span className="font-mono text-[11px]">{s.id}</span>
              {s.params && Object.keys(s.params).length > 0 && (
                <span className="text-[11px] text-muted-foreground"> — {JSON.stringify(s.params)}</span>
              )}
            </li>
          ))}
        </ol>
      )}
      {meta?.family && (
        <div className="text-[11px] text-muted-foreground mt-2">Family: {meta.family}</div>
      )}
    </div>
  )
}

export function TPCompare({
  tpta,
  tptb,
  onSetA,
  onSetB,
}: {
  tpta?: string
  tptb?: string
  onSetA: (id: string) => void
  onSetB: (id: string) => void
}) {
  const aVal = useMemo(() => tpta ?? '', [tpta])
  const bVal = useMemo(() => tptb ?? '', [tptb])

  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="space-y-2">
        <div className="flex gap-2">
          <Input
            placeholder="Paste TPT id"
            defaultValue={aVal}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onSetA((e.target as HTMLInputElement).value.trim())
            }}
          />
          <Button
            variant="secondary"
            onClick={() => {
              const el = (document.activeElement as HTMLInputElement)
              if (el && el.value) onSetA(el.value.trim())
            }}
          >
            Pin
          </Button>
        </div>
        <Steps id={tpta} label="A" />
      </div>
      <div className="space-y-2">
        <div className="flex gap-2">
          <Input
            placeholder="Paste TPT id"
            defaultValue={bVal}
            onKeyDown={(e) => {
              if (e.key === 'Enter') onSetB((e.target as HTMLInputElement).value.trim())
            }}
          />
          <Button
            variant="secondary"
            onClick={() => {
              const el = (document.activeElement as HTMLInputElement)
              if (el && el.value) onSetB(el.value.trim())
            }}
          >
            Pin
          </Button>
        </div>
        <Steps id={tptb} label="B" />
      </div>
    </div>
  )
}
```

#### E) `apps/web/src/routes/workbench.tp.$taxonId.$partId.tsx` (Updated)

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React, { useMemo } from 'react'
import { trpc } from '@/lib/trpc'
import { TPOverview } from '@/components/tp/TPOverview'
import { TPTransforms } from '@/components/tp/TPTransforms'
import { TPCompare } from '@/components/tp/TPCompare'
import { FoodStatePanel } from '@/components/inspector/FoodStatePanel'
import { Button } from '@ui/button'
import { Badge } from '@ui/badge'

export const Route = createFileRoute('/workbench/tp/$taxonId.$partId')({
  validateSearch: (search: Record<string, unknown>) => {
    const tab = (['overview','transforms','compare'] as const).includes(search.tab as any) ? (search.tab as any) : 'overview'
    const families = typeof search.family === 'string' && search.family
      ? (search.family as string).split(',').map((s) => s.trim()).filter(Boolean)
      : []
    const limit = Number.isFinite(Number(search.limit)) ? Math.max(10, Math.min(500, Number(search.limit))) : 50
    const tpta = typeof search.tpta === 'string' ? (search.tpta as string) : undefined
    const tptb = typeof search.tptb === 'string' ? (search.tptb as string) : undefined
    return { tab, families, limit, tpta, tptb }
  },
  component: TPPage,
})

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      className={`text-xs px-2 py-1 rounded border ${active ? 'bg-muted/60' : 'bg-background hover:bg-muted/40'}`}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

function TPPage() {
  const { taxonId, partId } = Route.useParams()
  const router = Route.useRouter()
  const search = Route.useSearch() as {
    tab: 'overview' | 'transforms' | 'compare'
    families: string[]
    limit: number
    tpta?: string
    tptb?: string
  }

  // fetch minimal node info for header / FS
  const lineageQ = trpc.taxonomy.pathToRoot.useQuery({ id: taxonId })
  const partTreeQ = trpc.taxonomy.partTree.useQuery({ id: taxonId })

  const fsPreview = useMemo(() => {
    const slugs = (lineageQ.data ?? []).map((n: any) => n.slug)
    if (!slugs.length) return ''
    const segs = ['fs:/' + slugs.join('/')]
    // NOTE: API uses "part:xxx" form for part ids; UI passes raw id here
    const pid = partId.startsWith('part:') ? partId : `part:${partId}`
    segs.push(pid)
    return segs.join('/')
  }, [lineageQ.data, partId])

  const setTab = (t: typeof search.tab) => {
    router.navigate({ to: '/workbench/tp/$taxonId.$partId', params: { taxonId, partId }, search: (s: any) => ({ ...s, tab: t }) })
  }
  const toggleFamily = (f: string) => {
    const on = search.families.includes(f)
    const next = on ? search.families.filter((x) => x !== f) : [...search.families, f]
    router.navigate({ to: '/workbench/tp/$taxonId.$partId', params: { taxonId, partId }, search: (s: any) => ({ ...s, family: next.join(',') }) })
  }
  const showMore = () => {
    router.navigate({ to: '/workbench/tp/$taxonId.$partId', params: { taxonId, partId }, search: (s: any) => ({ ...s, limit: (s.limit ?? 50) + 50 }) })
  }
  const openTPT = (id: string) => {
    router.navigate({ to: '/workbench/tpt/$id', params: { id } })
  }
  const setA = (id: string) => {
    router.navigate({ to: '/workbench/tp/$taxonId.$partId', params: { taxonId, partId }, search: (s: any) => ({ ...s, tpta: id }) })
  }
  const setB = (id: string) => {
    router.navigate({ to: '/workbench/tp/$taxonId.$partId', params: { taxonId, partId }, search: (s: any) => ({ ...s, tptb: id }) })
  }

  return (
    <div className="grid grid-cols-[1fr,360px] gap-3 min-h-0">
      {/* Center */}
      <div className="min-h-0 flex flex-col">
        <div className="rounded-md border p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="text-base font-semibold truncate">TP (Taxon + Part)</div>
              <div className="text-xs text-muted-foreground break-all">{taxonId} · {partId}</div>
            </div>
            <div className="flex gap-1">
              <TabButton active={search.tab === 'overview'} onClick={() => setTab('overview')}>Overview</TabButton>
              <TabButton active={search.tab === 'transforms'} onClick={() => setTab('transforms')}>Transforms</TabButton>
              <TabButton active={search.tab === 'compare'} onClick={() => setTab('compare')}>Compare</TabButton>
            </div>
          </div>
        </div>

        <div className="mt-3 flex-1 min-h-0 rounded-md border p-3 overflow-auto">
          {search.tab === 'overview' && (
            <TPOverview
              taxonId={taxonId}
              partId={partId}
              families={search.families}
              limit={search.limit}
              onToggleFamily={toggleFamily}
              onShowMore={showMore}
              onOpenTPT={openTPT}
            />
          )}

          {search.tab === 'transforms' && (
            <TPTransforms
              taxonId={taxonId}
              partId={partId}
              onResolved={(id) => openTPT(id)}
            />
          )}

          {search.tab === 'compare' && (
            <TPCompare
              tpta={search.tpta}
              tptb={search.tptb}
              onSetA={setA}
              onSetB={setB}
            />
          )}
        </div>
      </div>

      {/* Inspector (Right) */}
      <div className="min-h-0 rounded-md border p-3">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">Inspector</div>
          <Badge variant="secondary" className="text-[10px] uppercase">FoodState</Badge>
        </div>
        <div className="mt-2">
          <FoodStatePanel
            fsPreview={fsPreview}
            loadingValidate={false}
            result={undefined}
            onCopy={(s) => navigator.clipboard.writeText(s)}
            onValidate={() => {}}
            onParse={(fs) => {
              // Allow FS paste to jump
              const parseQ = (trpc as any).foodstate?.parse?.useQuery({ fs }, { enabled: false })
              // Fire-and-forget: user can paste fs and router will navigate when parse resolves
              ;(async () => {
                const r = await parseQ.refetch()
                const taxonPath: string[] = r.data?.taxonPath ?? []
                const part = r.data?.partId
                if (taxonPath.length >= 1) {
                  const txid = 'tx:' + taxonPath.join(':')
                  const pid = (part ?? '').replace(/^part:/, '')
                  if (pid) router.navigate({ to: '/workbench/tp/$taxonId.$partId', params: { taxonId: txid, partId: pid } })
                  else router.navigate({ to: '/workbench/taxon/$id', params: { id: txid } })
                }
              })()
            }}
            permalink={typeof window !== 'undefined' ? window.location.href : undefined}
          />
        </div>

        {/* Quick links into part tree (optional) */}
        <div className="mt-3 text-xs text-muted-foreground">
          {(partTreeQ.data as any[] | undefined)?.length ? (
            <div>Part tree available.</div>
          ) : (
            <div>No part tree metadata for this node.</div>
          )}
        </div>

        <div className="mt-3">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setTab('overview')}
          >
            Back to Overview
          </Button>
        </div>
      </div>
    </div>
  )
}
```

#### F) `apps/web/src/routes/workbench.tpt.$id.tsx` (Placeholder)

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React from 'react'

export const Route = createFileRoute('/workbench/tpt/$id')({
  component: () => (
    <div className="p-4">
      <div className="rounded-md border p-3">
        <div className="text-base font-semibold">TPT</div>
        <div className="text-xs text-muted-foreground">Coming in Phase 4.</div>
      </div>
    </div>
  ),
})
```

### Phase 4 — Exact File Contents

#### A) `apps/web/src/types.ts` (Extended)

```ts
export interface TaxonNode {
  id: string
  name: string
  slug: string
  rank: string
  parentId?: string | null
}

export interface Neighborhood {
  node: TaxonNode
  parent?: TaxonNode | null
  children: TaxonNode[]
  childCount: number
  siblings: Array<{ id: string; name: string }>
}

export interface PartInfo {
  id: string
  name: string
  kind?: string
  applicable: boolean
  identityCount: number
  nonIdentityCount: number
  synonyms: string[]
}

export type OverlayKey =
  | 'parts'
  | 'identity'
  | 'families'
  | 'docs'
  | 'transformUsage'

/** TP-level */
export interface TransformMeta {
  id: string
  name: string
  identity: boolean
  ordering: number
  family: string
  notes?: string | null
  /** simple schema; enough for read-only display */
  schema?: Array<{ key: string; kind: 'boolean' | 'number' | 'string' | 'enum'; enum?: string[] }> | null
}

export interface TPTLite {
  id: string
  taxonId: string
  partId: string
  family: string
  name?: string | null
  identityHash: string
}

export interface IdentityStep {
  id: string
  params?: Record<string, any> | null
}

export interface TPTDetail {
  id: string
  taxonId: string
  partId: string
  family: string
  name?: string | null
  synonyms?: string[] | null
  identity?: IdentityStep[]         // preferred
  path?: IdentityStep[]             // fallback (older API)
  identityHash?: string
  flags?: string[]                  // may also be exposed via separate endpoint
  cuisines?: string[]               // same note as flags
}
```

#### B) `apps/web/src/components/tpt/TPTOverview.tsx`

```tsx
import { trpc } from '@/lib/trpc'
import type { TPTDetail } from '@/types'
import { Badge } from '@ui/badge'

export function TPTOverview({
  id,
  onOpenTP,
  onOpenTPT,
}: {
  id: string
  onOpenTP: (taxonId: string, partId: string) => void
  onOpenTPT: (id: string) => void
}) {
  const getQ = (trpc as any).tpt?.get?.useQuery({ id })
  const meta: TPTDetail | undefined = getQ?.data
  const flagsQ = (trpc as any).tpt?.flags?.useQuery({ id }, { enabled: !!id && !meta?.flags })
  const cuisinesQ = (trpc as any).tpt?.cuisines?.useQuery({ id }, { enabled: !!id && !meta?.cuisines })
  const relatedQ = (trpc as any).tpt?.related?.useQuery({ id })

  const steps = meta?.identity ?? meta?.path ?? []
  const flags: string[] = meta?.flags ?? flagsQ?.data ?? []
  const cuisines: string[] = meta?.cuisines ?? cuisinesQ?.data ?? []
  const related = relatedQ?.data ?? { siblings: [], variants: [] }

  if (getQ?.isLoading) return <div className="text-sm text-muted-foreground">Loading TPT…</div>
  if (!meta) return <div className="text-sm text-muted-foreground">TPT not found.</div>

  return (
    <div className="space-y-4">
      {/* Top meta */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-base font-semibold truncate">{meta.name || meta.id}</div>
          <div className="text-xs text-muted-foreground break-all">{meta.id}</div>
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <Badge variant="secondary" className="text-[10px] uppercase">{meta.family}</Badge>
            <button
              className="text-[11px] underline decoration-dotted"
              onClick={() => onOpenTP(meta.taxonId, meta.partId)}
              title="Open TP (Taxon+Part)"
            >
              {meta.taxonId} · {meta.partId}
            </button>
          </div>
        </div>
      </div>

      {/* Flags & cuisines */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Flags</div>
          <div className="flex flex-wrap gap-1">
            {flags.length ? flags.map((f) => (
              <Badge key={f} variant="secondary" className="text-[10px]">{f}</Badge>
            )) : <div className="text-sm text-muted-foreground">—</div>}
          </div>
        </div>
        <div>
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Cuisines</div>
          <div className="flex flex-wrap gap-1">
            {cuisines.length ? cuisines.map((c) => (
              <Badge key={c} variant="secondary" className="text-[10px]">{c}</Badge>
            )) : <div className="text-sm text-muted-foreground">—</div>}
          </div>
        </div>
      </div>

      {/* Identity steps */}
      <div>
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Identity steps</div>
        {steps.length === 0 ? (
          <div className="text-sm text-muted-foreground">None</div>
        ) : (
          <ol className="text-sm list-decimal ml-4 space-y-1">
            {steps.map((s, i) => (
              <li key={i}>
                <span className="font-mono text-[11px]">{s.id}</span>
                {s.params && Object.keys(s.params || {}).length > 0 && (
                  <span className="text-[11px] text-muted-foreground"> — {JSON.stringify(s.params)}</span>
                )}
              </li>
            ))}
          </ol>
        )}
      </div>

      {/* Related */}
      <div>
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1">Related</div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <div className="text-[11px] text-muted-foreground mb-1">Siblings</div>
            <div className="flex flex-wrap gap-1">
              {(related.siblings ?? []).slice(0, 20).map((r: any) => (
                <button
                  key={r.id}
                  className="text-xs px-2 py-1 rounded border bg-background hover:bg-muted/40"
                  onClick={() => onOpenTPT(r.id)}
                >
                  {r.name || r.id}
                </button>
              ))}
              {(related.siblings ?? []).length === 0 && <div className="text-sm text-muted-foreground">—</div>}
            </div>
          </div>
          <div>
            <div className="text-[11px] text-muted-foreground mb-1">Variants</div>
            <div className="flex flex-wrap gap-1">
              {(related.variants ?? []).slice(0, 20).map((r: any) => (
                <button
                  key={r.id}
                  className="text-xs px-2 py-1 rounded border bg-background hover:bg-muted/40"
                  onClick={() => onOpenTPT(r.id)}
                >
                  {r.name || r.id}
                </button>
              ))}
              {(related.variants ?? []).length === 0 && <div className="text-sm text-muted-foreground">—</div>}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
```

#### C) `apps/web/src/components/tpt/TPTExplain.tsx`

```tsx
import { useState } from 'react'
import { trpc } from '@/lib/trpc'
import { Button } from '@ui/button'

export function TPTExplain({ id }: { id: string }) {
  const explainQ = (trpc as any).tpt?.explain?.useQuery({ id })
  const detailQ = (trpc as any).tpt?.get?.useQuery({ id })
  const [showRaw, setShowRaw] = useState(false)

  if (explainQ?.isLoading || detailQ?.isLoading) {
    return <div className="text-sm text-muted-foreground">Loading…</div>
  }
  const text: string | undefined = explainQ?.data?.text ?? explainQ?.data
  const raw = detailQ?.data

  return (
    <div className="space-y-3 text-sm">
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground">Human-readable explanation of identity and naming.</div>
        <Button size="sm" variant="outline" onClick={() => setShowRaw((v) => !v)}>
          {showRaw ? 'Hide raw' : 'Show raw'}
        </Button>
      </div>
      {text ? (
        <div className="leading-relaxed whitespace-pre-wrap">{text}</div>
      ) : (
        <div className="text-muted-foreground">No explanation available.</div>
      )}
      {showRaw && (
        <pre className="text-xs border rounded p-2 bg-muted/30 overflow-auto">{JSON.stringify(raw, null, 2)}</pre>
      )}
    </div>
  )
}
```

#### D) `apps/web/src/components/tpt/TPTGraph.tsx`

```tsx
import { useMemo } from 'react'
import { trpc } from '@/lib/trpc'
import GraphView from '@/components/GraphView'
import type { Edge, Node } from 'reactflow'

export function TPTGraph({
  id,
  onOpenTPT,
  onOpenTP,
}: {
  id: string
  onOpenTPT: (id: string) => void
  onOpenTP: (taxonId: string, partId: string) => void
}) {
  const metaQ = (trpc as any).tpt?.get?.useQuery({ id })
  const meta = metaQ?.data
  const lineageQ = trpc.taxonomy.pathToRoot.useQuery({ id: meta?.taxonId ?? '' }, { enabled: !!meta?.taxonId })
  const relatedQ = (trpc as any).tpt?.related?.useQuery({ id }, { enabled: !!id })

  const nodesEdges = useMemo(() => {
    if (!meta) return { nodes: [], edges: [] }
    const nodes: Node[] = []
    const edges: Edge[] = []

    // lineage above
    const lineage: Array<any> = lineageQ.data ?? []
    lineage.forEach((n: any, idx: number) => {
      nodes.push({
        id: n.id,
        type: 'taxon',
        position: { x: (idx - (lineage.length - 1) / 2) * 160, y: -120 },
        data: { ...n, isCenter: false },
      })
      if (idx < lineage.length - 1) {
        const next = lineage[idx + 1]
        edges.push({ id: `${n.id}->${next.id}`, source: n.id, target: next.id, type: 'smoothstep' })
      }
    })

    // center node = TPT
    nodes.push({
      id: meta.id,
      type: 'taxon',
      position: { x: 0, y: 0 },
      data: { name: meta.name || meta.id, slug: (meta.family || 'tpt'), rank: 'tpt', isCenter: true },
    })
    if (lineage.length) {
      const lastTaxon = lineage[lineage.length - 1]
      edges.push({ id: `${lastTaxon.id}->${meta.id}`, source: lastTaxon.id, target: meta.id, type: 'smoothstep' })
    }

    // variants/siblings below
    const related = relatedQ?.data ?? { variants: [], siblings: [] }
    const variants = related.variants ?? []
    variants.forEach((v: any, i: number) => {
      nodes.push({
        id: v.id,
        type: 'taxon',
        position: { x: (i - (variants.length - 1) / 2) * 160, y: 140 },
        data: { name: v.name || v.id, slug: v.family, rank: 'tpt', isCenter: false },
      })
      edges.push({ id: `${meta.id}->${v.id}`, source: meta.id, target: v.id, type: 'smoothstep' })
    })

    return { nodes, edges }
  }, [meta, lineageQ.data, relatedQ?.data])

  if (metaQ?.isLoading) return <div className="text-sm text-muted-foreground">Loading…</div>
  if (!meta) return <div className="text-sm text-muted-foreground">Not found.</div>

  return (
    <div className="space-y-3">
      <GraphView
        nodes={nodesEdges.nodes}
        edges={nodesEdges.edges}
        layout="radial"
        onNodeClick={(nid) => {
          if (nid === meta.id) return
          if (nid.startsWith('tx:')) onOpenTP(nid, meta.partId)
          else onOpenTPT(nid)
        }}
      />
      <div className="text-[11px] text-muted-foreground">
        Tip: Click any node to navigate (taxon nodes open TP with this part).
      </div>
    </div>
  )
}
```

#### E) `apps/web/src/routes/workbench.tpt.$id.tsx` (Updated)

```tsx
import { createFileRoute } from '@tanstack/react-router'
import React, { useMemo } from 'react'
import { trpc } from '@/lib/trpc'
import { TPTOverview } from '@/components/tpt/TPTOverview'
import { TPTExplain } from '@/components/tpt/TPTExplain'
import { TPTGraph } from '@/components/tpt/TPTGraph'
import { Badge } from '@ui/badge'
import { Button } from '@ui/button'
import { FoodStatePanel } from '@/components/inspector/FoodStatePanel'

export const Route = createFileRoute('/workbench/tpt/$id')({
  validateSearch: (s: Record<string, unknown>) => {
    const tab = (['overview','explain','graph'] as const).includes(s.tab as any) ? (s.tab as any) : 'overview'
    return { tab }
  },
  component: TPTPage,
})

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      className={`text-xs px-2 py-1 rounded border ${active ? 'bg-muted/60' : 'bg-background hover:bg-muted/40'}`}
      onClick={onClick}
    >
      {children}
    </button>
  )
}

function TPTPage() {
  const { id } = Route.useParams()
  const router = Route.useRouter()
  const search = Route.useSearch() as { tab: 'overview' | 'explain' | 'graph' }

  // minimal meta for header + FS
  const metaQ = (trpc as any).tpt?.get?.useQuery({ id })
  const meta = metaQ?.data

  const lineageQ = trpc.taxonomy.pathToRoot.useQuery({ id: meta?.taxonId ?? '' }, { enabled: !!meta?.taxonId })

  // Basic FS preview (taxon path + part only; identity omitted for readability)
  const fsPreview = useMemo(() => {
    const slugs = (lineageQ.data ?? []).map((n: any) => n.slug)
    if (!slugs.length || !meta?.partId) return ''
    const pid = meta.partId.startsWith('part:') ? meta.partId : `part:${meta.partId}`
    return `fs:/${slugs.join('/')}/${pid}`
  }, [lineageQ.data, meta?.partId])

  const setTab = (t: typeof search.tab) => {
    router.navigate({ to: '/workbench/tpt/$id', params: { id }, search: (s: any) => ({ ...s, tab: t }) })
  }

  const openTP = (taxonId: string, partId: string) =>
    router.navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId, partId } })

  const openTPT = (tid: string) =>
    router.navigate({ to: '/workbench/tpt/$id', params: { id: tid } })

  // Suggestions (right inspector)
  const suggestQ = (trpc as any).tptAdvanced?.suggest?.useQuery({ id }, { enabled: !!id })

  return (
    <div className="grid grid-cols-[1fr,360px] gap-3 min-h-0">
      {/* Center */}
      <div className="min-h-0 flex flex-col">
        <div className="rounded-md border p-3">
          <div className="flex items-center justify-between gap-2">
            <div className="min-w-0">
              <div className="text-base font-semibold truncate">{meta?.name || id}</div>
              <div className="text-xs text-muted-foreground break-all">{id}</div>
              {meta?.family && (
                <div className="mt-1 flex items-center gap-2">
                  <Badge variant="secondary" className="text-[10px] uppercase">{meta.family}</Badge>
                  <button
                    className="text-[11px] underline decoration-dotted"
                    onClick={() => meta && openTP(meta.taxonId, meta.partId)}
                    title="Open TP (Taxon+Part)"
                  >
                    {meta?.taxonId} · {meta?.partId}
                  </button>
                </div>
              )}
            </div>
            <div className="flex gap-1">
              <TabButton active={search.tab === 'overview'} onClick={() => setTab('overview')}>Overview</TabButton>
              <TabButton active={search.tab === 'explain'} onClick={() => setTab('explain')}>Explain</TabButton>
              <TabButton active={search.tab === 'graph'} onClick={() => setTab('graph')}>Graph</TabButton>
            </div>
          </div>
        </div>

        <div className="mt-3 flex-1 min-h-0 rounded-md border p-3 overflow-auto">
          {search.tab === 'overview' && (
            <TPTOverview id={id} onOpenTP={openTP} onOpenTPT={openTPT} />
          )}
          {search.tab === 'explain' && (
            <TPTExplain id={id} />
          )}
          {search.tab === 'graph' && (
            <TPTGraph id={id} onOpenTPT={openTPT} onOpenTP={openTP} />
          )}
        </div>
      </div>

      {/* Inspector */}
      <div className="min-h-0 rounded-md border p-3 space-y-3">
        <div className="flex items-center justify-between">
          <div className="text-sm font-medium">Suggestions</div>
          <Badge variant="secondary" className="text-[10px] uppercase">Dev</Badge>
        </div>

        {suggestQ?.isLoading ? (
          <div className="text-sm text-muted-foreground">Loading…</div>
        ) : (suggestQ?.data ?? []).length === 0 ? (
          <div className="text-sm text-muted-foreground">No suggestions.</div>
        ) : (
          <ul className="space-y-1">
            {(suggestQ?.data ?? []).map((s: any) => (
              <li key={s.id}>
                <button
                  className="w-full text-left px-2 py-1 rounded border hover:bg-muted/40"
                  onClick={() => openTPT(String(s.id))}
                >
                  <div className="text-sm truncate">{s.name || s.id}</div>
                  <div className="text-[11px] text-muted-foreground">{s.family}</div>
                </button>
              </li>
            ))}
          </ul>
        )}

        <div className="pt-2 border-t">
          <div className="text-xs font-medium mb-1">FoodState</div>
          <FoodStatePanel
            fsPreview={fsPreview}
            loadingValidate={false}
            result={undefined}
            onCopy={(s) => navigator.clipboard.writeText(s)}
            onValidate={() => {}}
            onParse={(fs) => {
              const parseQ = (trpc as any).foodstate?.parse?.useQuery({ fs }, { enabled: false })
              ;(async () => {
                const r = await parseQ.refetch()
                const taxonPath: string[] = r.data?.taxonPath ?? []
                const part = r.data?.partId
                if (taxonPath.length >= 1) {
                  const txid = 'tx:' + taxonPath.join(':')
                  const pid = (part ?? '').replace(/^part:/, '')
                  if (pid) router.navigate({ to: '/workbench/tp/$taxonId/$partId', params: { taxonId: txid, partId: pid } })
                  else router.navigate({ to: '/workbench/taxon/$id', params: { id: txid } })
                }
              })()
            }}
            permalink={typeof window !== 'undefined' ? window.location.href : undefined}
          />
        </div>
      </div>
    </div>
  )
}
```

## Work Breakdown (For Cursor Agent)

1. **Phase 0-1**: Apply the implementation package above (routes, shell, search)
2. **Phase 2**: Apply the Taxon page implementation package above (Overview, Graph, Lists components)
3. **Phase 3**: TP Overview TPT list + family filter + read-only Transforms + Compare
4. **Phase 4**: TPT Overview + Explain + Graph + Suggestions
5. **Phase 5**: ✅ QA browsers (Families, Cuisines, Flags, Search QA) - **COMPLETE**
6. **Phase 6**: Wire overlays data sources
7. **Phase 7**: Meta page & build age badge in shell
8. **Phase 8**: Polish (keyboard shortcuts, copy buttons, empty states, loading skeletons)