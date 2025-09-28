# 09 — Classifications & Overlays

## Regulatory/Market Classifications (Parallel Labelings)
External category systems as labelings over nodes:
```json
{ "scheme": "hs", "code": "1509", "label": "Olive oil", "applies_to": ["tx:plantae:olive"] }
```
Use for trade analytics, label filters, alternate navigation.

## Functional Classes (Derived)
Create FunctionalClass nodes (oils, flours, cheeses) with `is_functional` edges from canonical nodes. Always anchor to lineage to avoid “flat-only” drift.

## Commodity Layer
For ambiguous/market concepts, mint **Commodity** nodes anchored to taxa (one or many) with confidence. Map free text → Commodity → canonical FoodStates via Parts + Transforms.

## Product Overlay
Branded items live outside canonical identity:
- Black-box labels (evidence only), or
- Decomposed mixtures referencing canonical ingredients.
Products **never** define canonical IDs.
