# Stage Catalog (0→K)

This is the authoritative stage blueprint. We will bring these online incrementally; file names are indicative.

| ID | Name | Module | Inputs | Outputs | Notes |
|---:|------|--------|--------|---------|------|
| 0 | Ontology Compile | `stages/stage_0/` | taxa/, ontology assets | `compiled/taxa.jsonl`, `compiled/*.json`, `compiled/rules/`, `compiled/docs.jsonl` | Compile taxa shards; copy assets; compile docs |
| A | Load + Lint | `stages/a_load_lint.py` | ontology, rules | `report/lint.json`, `tmp/transforms_canon.json`, `tmp/flags.rules.validated.json` | Schema + xref validation; transform normalization; rules normalization |
| B | Substrate Graph (T×P) | `stages/b_substrates.py` | parts, implied parts, animal cuts, policy | `graph/substrates.jsonl` | Materialize allowed (taxon, part) pairs; apply promoted parts proto‑paths |
| C | Curated TPT Seed | `stages/c_tpt_seed.py` | derived_foods.jsonl, substrates | `tmp/tpt_seed.jsonl` | Validate seeds; strip non‑identity steps; family assignment (explicit/pattern) |
| D | Family Expansions | `stages/d_family_expand.py` | families.json, allowlist, buckets | `tmp/tpt_generated.jsonl` | Instantiate minimal identity paths without explosion |
| E | Canonicalization & IDs | `stages/e_canon_ids.py` | transforms_canon, buckets | `tmp/tpt_canon.jsonl` | Sort steps; bucket params; compute identity hash & final ID |
| F | Naming & Synonyms | `stages/f_names_syns.py` | name_overrides, tp_synonyms | `tmp/tpt_named.jsonl` | Resolve display names & synonyms; cuisines & regions |
| G | Diet & Safety Flags | `stages/g_flags.py` | diet_safety_rules.jsonl | `tmp/tpt_named.jsonl` (updated) | Evaluate guarded rules with params (nitrite, smoke, pasteurize, etc.) |
| H | Graph Edges | `stages/h_edges.py` | prior outputs | `graph/edges.jsonl` | T --has_part--> P; P --transforms_to--> TPT; etc. |
| I | TPT Meta | `stages/i_tpt_meta.py` | prior outputs | `out/tpt_meta.jsonl` | Denormalized card blobs for API |
| J | Search Docs | `stages/j_search_docs.py` | TP, TPT, promoted parts | `out/search_docs.jsonl` | Unified search corpus |
| K | Database | `stages/k_database.py` | everything | `database/graph.dev.sqlite` | API-ready SQLite with FTS (T and TP first; TPT later) |

### Error codes (curated TPT path)

- **E001** invalid transform (non‑identity or not applicable)
- **E002** missing substrate edge (taxon×part)
- **E003** family not resolvable from path
- **E004** promoted part uses identity TF in `proto_path`
- **E005** deterministic ID collision (auto `~v2`, log it)
- **E006** unsafe/ambiguous dietary inference
