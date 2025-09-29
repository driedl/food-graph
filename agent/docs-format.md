# Prompt for Agents — “Taxon Doc Writer (Culinary-First, Nutrition-Aware, Multi-Paragraph)”

**Goal**
Write a taxon doc that orients a foodie to _where they are in the taxonomy_ and _what foods/uses belong here_. Keep nutrition in the long description (not the summary). Use a small set of consistent paragraphs that read top-down (most useful first).

**Inputs you’ll be given**

- `id`, `rank`, `latin_name`, `display_name` (with a short common gloss)
- Optional examples of included foods and known safety notes

**Output format (exactly this)**

```
---
id: <full tx path, no parent skipping>
rank: <kingdom|phylum|class|order|family|genus|species>
latin_name: <Latin name>
display_name: <Latin name> (<concise common gloss>)
lang: en
summary: <22–35 words orienting to place, contents, and culinary roles; no nutrition language.>
updated: <YYYY-MM-DD>  # use today in America/Los_Angeles
---
*Culinary scope & forms.* <2–4 sentences. Edible parts, mainstream preparations, processed products.>

*Texture & cooking logic.* <2–4 sentences. How structure dictates method; what over/undercooking does; technique cues.>

*Nutrition patterns (high-level).* <2–4 sentences. Macro/micro patterns, notable compounds, variability by species/cultivar/feed/season; avoid hard numbers unless distinctive.>

*Safety & handling.* <2–4 sentences. Allergens/toxins/pathogens, doneness, cold-chain; what matters at this node.>

*Variability, sourcing & storage.* <2–4 sentences. What drives differences (breed/species, origin, processing), and storage/shelf life tips.>
```

**Style rules**

- **Summary** = orientation only (place in tree + what it contains + common uses/forms). **No nutrition** or health claims. 22–35 words.
- **Description** = five short paragraphs with the exact italic lead-ins shown. No bullets. No repeating the summary.
- Present tense, neutral culinary voice. One space after periods.
- Prefer concrete, kitchen-relevant language over jargon. Numbers only if truly distinctive (e.g., “edible bones add calcium” is fine; avoid exact milligrams).

**Metadata rules**

- `id` must include the full path (no parent skipping).
- `display_name` pairs Latin with a concise parenthetical gloss.
- `updated` = today’s date in America/Los_Angeles.

**QA checklist (self-verify before finishing)**

- [ ] Summary cleanly orients (place + contents + uses), **no nutrition**.
- [ ] Five paragraphs present, each with the exact italic lead-in.
- [ ] Flow is **prep → method logic → nutrition pattern → safety → variability/storage**.
- [ ] Hazards/allergens relevant to the node are included.
- [ ] Rank and path match the node; filenames will be `LatinName (common gloss).md`.

**Tiny summary examples (Good vs Bad)**

- **Good:** "Pelagic fish family with firm, meaty flesh; includes tuna, mackerel, and bonito used as steaks, sashimi, canned products, and boldly flavored small fish for grilling, curing, and smoking."
- **Bad:** "High in omega-3 and very healthy fish eaten worldwide." (Too nutrition-forward; no orientation.)

---

## File Placement

**Where to place your `.tx.md` files:**

Place documentation files **alongside their corresponding `.jsonl` files** in the taxonomic hierarchy under `/data/ontology/taxa/`. The doc compilation script recursively searches for all `*.tx.md` files throughout the taxa tree.

**File naming convention:**

- Format: `{LatinName}--{common-gloss}.tx.md`
- Examples: `Actinopterygii--bony-fish.tx.md`, `Fabaceae--legumes.tx.md`

**Directory structure examples:**

```
/data/ontology/taxa/
├── Life--root.tx.md                    # Root level
├── Eukaryota--nucleated-organisms.tx.md
├── animalia/
│   ├── Animalia--animals.tx.md
│   ├── Chordata--vertebrates.tx.md
│   ├── Actinopterygii--bony-fish.tx.md
│   ├── Gadidae--cod-haddock-pollock.tx.md
│   └── animals.jsonl
├── fungi/
│   ├── Fungi--mushrooms.tx.md
│   └── fungi.jsonl
└── plantae/
    ├── Plantae--plants.tx.md
    └── families/
        ├── Fabaceae--legumes.tx.md
        ├── Fabaceae.jsonl
        ├── Poaceae--grasses.tx.md
        ├── Poaceae.jsonl
        └── ...
```

**Key points:**

- Place `.tx.md` files in the **same directory** as the corresponding `.jsonl` file
- The compilation script will find them automatically via recursive search
- Maintain the hierarchical structure that matches the taxonomic relationships
- Use consistent naming: `{LatinName}--{descriptive-common-name}.tx.md`

---

## Sample taxon doc (multi-paragraph)

```
---
id: tx:animalia:chordata
rank: phylum
latin_name: Chordata
display_name: Vertebrates
lang: en
summary: Vertebrate animals spanning fishes, birds, and mammals; this node groups foods from flesh, eggs, and milk plus stocks and cured products, with wide variation in texture, flavor, and culinary roles.
updated: 2025-09-29
---
*Culinary scope & forms.* This node covers table meats and offal, finfish and roe, and the two major secondary products unique to vertebrates—eggs and milk—with their vast derivative families (custards, cheeses, yogurts, butter, ghee). Butchery yields quick-cooking tender cuts and slow-cooking collageny ones; bones and skins become stocks, broths, and gelatin. Fish present as fillets, steaks, whole small species, and canned/smoked forms; eggs appear fresh, preserved, and as functional ingredients; dairy spans fresh, cultured, aged, and clarified styles. Across the node, techniques run from raw or lightly cured (e.g., sashimi, gravlax) to high-heat searing, braises, smoking, and confit.

*Texture & cooking logic.* Choose methods by muscle structure and connective tissue: delicate white fish reward gentle heat; darker, oilier fish tolerate grill and smoke; fast-twitch poultry breast dries quickly while thighs handle simmering; well-marbled or sinewy red-meat cuts shine with time and moisture to convert collagen to gelatin. Egg proteins set predictably with temperature, enabling emulsions and foams; dairy fats and casein stabilize sauces and carry volatile aromas. Salting, aging, and curing reshape water activity, tenderness, and flavor concentration.

*Nutrition patterns (high-level).* Edible outputs here typically supply complete amino acids; micronutrient “centers of gravity” shift by subgroup—heme iron and B12 concentrate in many red meats and fish; oily fish add long-chain omega-3s; small bone-in fish and many dairy styles contribute calcium; slow-cooked skins/bones yield collagen/gelatin. Actual values swing with species, cut, feed, season, and processing (e.g., brining raises sodium; trimming/pasteurization alter fat and vitamin profiles). Treat child nodes as the place to encode specific ranges and exceptions.

*Safety & handling.* Quality pivots on cold-chain, cleanliness, and doneness targets. Finfish can form histamine if temperature-abused; some large predators accumulate more mercury than small, short-lived species. Parasite controls (freezing where required) apply to raw fish uses. Poultry demands careful cross-contamination control; ground meats cook through; cured meats vary in nitrite/salt. Milk and certain cheeses are pasteurized in many markets; eggs vary by washing and shell integrity—store accordingly. Allergies cluster in milk and eggs; fish allergy is distinct from shellfish.

*Variability, sourcing & storage.* Husbandry and habitat drive flavor and fat (grass- vs grain-finished beef; wild- vs farmed fish), while age, activity, and breed/species explain texture and color. Provenance, season, and processing (frozen-at-sea vs fresh, wet- vs dry-aged) shape outcomes more than many recipes do. Store most raw items very cold and use promptly; freeze to extend life at some texture cost. Cure, smoke, or can to trade perishability for salt and intensity. Use species/cut metadata downstream to recommend cooking methods and serving cadences that fit the ingredient at hand.
```

---

## Blank template (copy, paste, fill)

```
---
id: tx:<full:path:here>
rank: <rank>
latin_name: <Latin name>
display_name: <english translation of latin name>
lang: en
summary: <22–35 words orienting to place, contents, and culinary roles; no nutrition language.>
updated: <YYYY-MM-DD>
---
*Culinary scope & forms.* <2–4 sentences. Edible parts, mainstream preparations, processed products.>

*Texture & cooking logic.* <2–4 sentences. Structure → method; doneness cues; what over/undercooking does.>

*Nutrition patterns (high-level).* <2–4 sentences. Macro/micro patterns and notable compounds; variability by species/cultivar/feed/season; avoid exact numbers unless distinctive.>

*Safety & handling.* <2–4 sentences. Allergens/toxins/pathogens; cold-chain; doneness; cross-contamination; curing/smoking considerations.>

*Variability, sourcing & storage.* <2–4 sentences. What drives differences; storage and shelf-life tips; processing tradeoffs (fresh/frozen/cured/canned).>
```
