## Quick QA checklist (NDJSON hygiene)

**IDs & prefixes**

- Use stable prefixes: `tx:` for taxa, `attr:` for attributes.
- IDs are lowercase, snake/kebab acceptable; never embed spaces.
- Children must have valid existing `parent` IDs (no dangling references).

**Ranks & kinds**

- Taxa must have a valid `rank` from {kingdom, family, genus, species, variety, cultivar, form}.
- Attributes must set `"kind":"attribute"` (no `rank` field).

**Names**

- `display_name`: human-readable, title-case where natural (“Potato (Yukon Gold)”).
- `latin_name`: scientific binomial when applicable; empty string `""` only for purely synthetic nodes.
- Avoid marketing adjectives in `display_name` (e.g., “premium”, “fresh”).

**Aliases**

- Include common spellings and plurals (e.g., “pistachio”, “pistachios”).
- No duplicates; no capitalization variants unless meaning changes.

**Attributes**

- Every attribute defines: `datatype`, `cardinality`, `default`, and either `enum` or `unit`.
- `normalize_terms` only maps real-world labels → canonical values; do not include regex in NDJSON.
- `applies_to` should be broad (e.g., a kingdom/family) unless truly specific.

**Dupes & conflicts**

- Before adding, run a de-dupe pass by `display_name` (case-insensitive) and by `latin_name`.
- If two nodes represent the same thing at different ranks, prefer the **lower** valid rank (e.g., species over genus).

**Tags**

- Keep tags compact and functional (e.g., `["foundation"]` for core staples, `["facet"]` for UI filters).

**Consistency spot-checks (per PR)**

- Pick 5 random lines: confirm JSON validity, required keys present, and parent chain resolves to a kingdom.
- Confirm new `attr:` IDs show in UI facet registry (once we wire it).
