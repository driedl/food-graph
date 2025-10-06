# Overview

**graph** is a stage‑based ETL that compiles the Food Graph into build artifacts for the API and UI.
It follows the TPT vision (Taxon, Taxon+Part, Taxon+Part+Transform) and the expanded 11‑stage compiler.

Guiding principles:

1. **Single responsibility** per stage (clear inputs/outputs).
2. **Deterministic**: identical inputs → identical outputs (byte‑for‑byte).
3. **Observable**: rich logs, JSON reports, lint findings.
4. **Recoverable**: any stage can be re‑run independently if its inputs change.
5. **Composable**: easy to add new stages (families, flags, expansions) without touching others.
