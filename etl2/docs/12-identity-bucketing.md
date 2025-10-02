# Identity Param Bucketing

Stage **E** optionally buckets numeric identity parameters using `data/ontology/rules/param_buckets.json`.

**Spec (minimal):**
```json
{
  "tf:cure.nitrite_ppm": { "cuts": [0, 120], "labels": ["none", "low", "high"] }
}
```

Semantics: value ≤ cuts[i] → labels[i]; otherwise → last label.
This label is used in the identity payload (and thus the `identity_hash`), making small changes within a bucket hash-stable.

## Example

Given buckets:
```json
{
  "tf:cure.nitrite_ppm": { "cuts": [0, 120], "labels": ["none", "low", "high"] }
}
```

- `nitrite_ppm: 50` → `"low"` (50 ≤ 120)
- `nitrite_ppm: 150` → `"high"` (150 > 120)
- `nitrite_ppm: 0` → `"none"` (0 ≤ 0)

## Benefits

1. **Hash stability**: Small parameter changes within a bucket don't change the identity hash
2. **Semantic grouping**: Related parameter values are grouped together
3. **Optional**: No bucketing if `param_buckets.json` doesn't exist

## Implementation

The bucketing is applied in Stage E (`canon_ids.py`) after building the identity payload but before computing the hash. Parameter keys are formatted as `{transform_id}.{param_key}` (e.g., `tf:cure.nitrite_ppm`).
