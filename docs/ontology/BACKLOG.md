
# Ontology Backlog (Pantry-100 → FDC Foundation 411)

## Milestone A — Pantry-100
Coverage of common home-cooking staples sufficient for recipes and tracking.

- Fruits: apple, banana, citrus (orange), berries, grapes, pineapple, melon
- Vegetables: tomato, potato, onion, garlic, carrot, leafy greens (kale, lettuce)
- Grains: rice (Oryza sativa), wheat (T. aestivum), oats (A. sativa), corn/maize
- Legumes: chickpea, lentil, peanut, common bean
- Nuts/Seeds: almond, walnut, hazelnut, sunflower, chia, flax
- Animal: chicken (Gallus gallus domesticus), cow (Bos taurus), salmon (Salmo salar)
- Dairy products via transforms: milk → yogurt/cheese/butter
- Oils: olive, canola, soybean, sunflower

## Milestone B — FDC Foundation 411
- Ensure lineage nodes exist for all 411 foundation foods:
  - Add missing genera/species; keep *process terms* out of taxonomy.
  - Represent forms via identity attributes/transforms (`process`, `salt_level`, `refinement`, `enrichment`, `style`, etc.).
- Importer output must produce a `missing_taxa.json` diff for any unknown species.

## QA Gates
- `ontology:lint` passes (no cycles, unknown parents, or process-terms in names).
- `ontology:diff` shows **no removals** without an explicit migration note.
