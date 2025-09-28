# 06 — Evidence & Computation

## Evidence Types
- **Lab assay** (method, sample size, uncertainty).
- **Database import** (FDC/CIQUAL/etc.) — cite release/version.
- **Manufacturer label** (jurisdiction, rounding policy).
- **Literature** (study metadata).

Evidence binds to a **FoodState** (or Mixture) and carries per-nutrient values on a 100 g edible basis (unless specified).

## Provenance (suggested fields)
`source, method, sample_size, year, region, moisture_basis, uncertainty, transform_lineage`

## Rollups (per node, per nutrient)
Selection policy: exact FoodState evidence → nearest ancestor → sibling estimate → foundation template. Aggregation via median/trimmed mean with sample-size weighting.

## Hierarchical Borrowing (Phylogenetic Priors)
Borrow strength along taxonomy when evidence is sparse:
- **Upward**: parent prior informs child via shrinkage.
- **Sibling**: within-genus pooled stats as an empirical Bayes prior.
- **Across transforms**: map through retention/yield when borrowing raw → cooked or vice versa.

## Embeddings (discovery & QA)
Fit nutrient-space embeddings (PCA/autoencoder) on normalized vectors; use neighbors for suggestions and anomaly detection. **Never** define identity from embeddings.

## QA & Guards
- Mass-closure checks; sodium/water sanity for brined vs raw.
- Within-node dispersion thresholds; neighbor similarity.
- Unit normalization and label rounding guards.

## Mixtures
DAG evaluation with caching; support pinned vs latest nested mixtures.
