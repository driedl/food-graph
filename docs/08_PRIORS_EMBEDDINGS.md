# 08 — Priors & Embeddings

## Phylogenetic Priors
Use taxonomy for hierarchical shrinkage. For nutrient `n`:
```
θ̂_child = w * μ_child + (1-w) * μ_parent
```
with `w` from sample size/variance. Extend with sibling pooling at genus/family.

## Transform-Aware Borrowing
When borrowing across transforms, compose/invert retention and yields with uncertainty accounting.

## Embeddings
- Inputs: per-nutrient vectors (100 g basis), impute with priors.
- Models: PCA/autoencoder.
- Outputs: neighbor lists, clusters, anomaly scores.
- Storage: `models/embeddings/<model_id>/vectors.parquet`, `neighbors.parquet`.
- API: `/neighbors?id=...&k=20` for discovery/QA.
Policy: **Inform, don’t identify**.
