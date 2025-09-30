import argparse, os, sqlite3, json, glob, re, sys, time
from datetime import datetime

def print_step(step, message):
    """Print a formatted step message."""
    print(f"🔧 {step}: {message}")

def print_progress(current, total, item=""):
    """Print progress indicator."""
    percentage = (current / total) * 100
    bar_length = 30
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '░' * (bar_length - filled_length)
    print(f"\r📊 Progress: |{bar}| {percentage:.1f}% ({current}/{total}) {item}", end='', flush=True)

def print_success(message):
    """Print a success message."""
    print(f"\n✅ {message}")

def print_error(message):
    """Print an error message."""
    print(f"\n❌ {message}")

def print_info(message):
    """Print an info message."""
    print(f"ℹ️  {message}")

parser = argparse.ArgumentParser(description="Compile food graph ontology from JSON/JSONL sources")
parser.add_argument("--in", dest="in_dir", required=True, help="Input directory containing ontology data")
parser.add_argument("--out", dest="out_path", required=True, help="Output SQLite database path")
parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
args = parser.parse_args()

print("🌱 Food Graph Ontology Compiler")
print("=" * 50)
start_time = time.time()
print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"📂 Input directory: {args.in_dir}")
print(f"💾 Output database: {args.out_path}")
print()

# Validate input directory
if not os.path.exists(args.in_dir):
    print_error(f"Input directory does not exist: {args.in_dir}")
    sys.exit(1)

# Create output directory
os.makedirs(os.path.dirname(args.out_path), exist_ok=True)
con = sqlite3.connect(args.out_path)
cur = con.cursor()
print_step("1/5", "Setting up database schema...")

cur.executescript("""
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  slug TEXT NOT NULL,
  rank TEXT NOT NULL,
  parent_id TEXT REFERENCES nodes(id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_nodes_slug_parent ON nodes(slug, parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_parent ON nodes(parent_id);
CREATE TABLE IF NOT EXISTS synonyms (
  node_id TEXT REFERENCES nodes(id) ON DELETE CASCADE,
  synonym TEXT NOT NULL,
  PRIMARY KEY (node_id, synonym)
);
CREATE TABLE IF NOT EXISTS node_attributes (
  node_id TEXT REFERENCES nodes(id) ON DELETE CASCADE,
  attr TEXT NOT NULL,
  val TEXT NOT NULL,
  PRIMARY KEY (node_id, attr, val)
);
CREATE TABLE IF NOT EXISTS attr_def (
  attr TEXT PRIMARY KEY,
  kind TEXT NOT NULL DEFAULT 'categorical', -- numeric|boolean|categorical
  role TEXT
);
CREATE TABLE IF NOT EXISTS attr_enum (
  attr TEXT NOT NULL REFERENCES attr_def(attr) ON DELETE CASCADE,
  val  TEXT NOT NULL,
  PRIMARY KEY (attr, val)
);
CREATE TABLE IF NOT EXISTS taxon_doc (
  taxon_id TEXT NOT NULL,
  lang TEXT NOT NULL DEFAULT 'en',
  summary TEXT NOT NULL,
  description_md TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  checksum TEXT NOT NULL,
  rank TEXT,
  latin_name TEXT,
  display_name TEXT,
  tags TEXT, -- JSON array as text
  PRIMARY KEY (taxon_id, lang),
  FOREIGN KEY (taxon_id) REFERENCES nodes(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_taxon_doc_taxon_id ON taxon_doc(taxon_id);
CREATE INDEX IF NOT EXISTS idx_taxon_doc_lang ON taxon_doc(lang);
CREATE INDEX IF NOT EXISTS idx_taxon_doc_updated ON taxon_doc(updated_at);
CREATE TABLE IF NOT EXISTS part_def (
  id   TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT,
  notes TEXT,
  parent_id TEXT REFERENCES part_def(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS part_synonym (
  part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  synonym TEXT NOT NULL,
  PRIMARY KEY (part_id, synonym)
);
CREATE TABLE IF NOT EXISTS has_part (
  taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  part_id  TEXT NOT NULL REFERENCES part_def(id) ON DELETE RESTRICT,
  PRIMARY KEY (taxon_id, part_id)
);
CREATE TABLE IF NOT EXISTS transform_def (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  identity INTEGER NOT NULL,
  schema_json TEXT,
  ordering INTEGER DEFAULT 999,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS transform_applicability (
  taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE RESTRICT,
  transform_id TEXT NOT NULL REFERENCES transform_def(id) ON DELETE RESTRICT,
  PRIMARY KEY (taxon_id, part_id, transform_id)
);
""")

print_info("Clearing existing data...")
cur.execute("DROP TRIGGER IF EXISTS trg_nodes_ai")
cur.execute("DROP TRIGGER IF EXISTS trg_nodes_ad") 
cur.execute("DROP TRIGGER IF EXISTS trg_nodes_au")
cur.execute("DROP TRIGGER IF EXISTS trg_synonyms_ai")
cur.execute("DROP TRIGGER IF EXISTS trg_synonyms_ad")
cur.execute("DROP TABLE IF EXISTS nodes_fts")
cur.execute("DELETE FROM transform_applicability")
cur.execute("DELETE FROM transform_def")
cur.execute("DELETE FROM has_part")
cur.execute("DELETE FROM part_def")
cur.execute("DELETE FROM taxon_doc")
cur.execute("DELETE FROM synonyms")
cur.execute("DELETE FROM node_attributes")
cur.execute("DELETE FROM nodes")
cur.execute("DELETE FROM attr_def")
print_success("Database schema initialized and cleared")

def last_segment(tx_id: str) -> str:
    return tx_id.split(":")[-1]

# Load attributes registry
print_step("2/5", "Loading attribute definitions...")
attributes_file = os.path.join(args.in_dir, "attributes.json")
if not os.path.exists(attributes_file):
    print_error(f"Attributes file not found: {attributes_file}")
    sys.exit(1)

with open(attributes_file, "r", encoding="utf-8") as f:
    attrs = json.load(f)

print_info(f"Found {len(attrs)} attribute definitions")
for i, a in enumerate(attrs):
    kind_map = {"enum": "categorical", "string": "categorical", "number": "numeric", "boolean": "boolean"}
    kind = kind_map.get(a["kind"], "categorical")
    role = a.get("role")
    cur.execute("INSERT OR IGNORE INTO attr_def(attr, kind, role) VALUES (?,?,?)", (a["id"].replace("attr:", ""), kind, role))
    # enums (if any)
    if a.get("enum"):
        for ev in a["enum"]:
            cur.execute("INSERT OR IGNORE INTO attr_enum(attr, val) VALUES (?,?)", (a["id"].replace("attr:", ""), ev))
    if args.verbose:
        print(f"  • {a['id']} ({kind}) - {a.get('name', 'No name')}")

print_success(f"Loaded {len(attrs)} attribute definitions")

# Load parts registry
print_step("2.5/5", "Loading part definitions...")
parts_file = os.path.join(args.in_dir, "parts.json")
if not os.path.exists(parts_file):
    print_error(f"Parts file not found: {parts_file}")
    sys.exit(1)

with open(parts_file, "r", encoding="utf-8") as f:
    parts = json.load(f)

print_info(f"Found {len(parts)} parts")
for p in parts:
    cur.execute(
        "INSERT OR REPLACE INTO part_def(id,name,kind,notes) VALUES (?,?,?,?)",
        (p["id"], p["name"], p.get("kind"), p.get("notes"))
    )

# Capture any built-in applies_to on parts as rules
builtin_part_rules = []
for p in parts:
    if p.get("applies_to"):
        builtin_part_rules.append({"part": p["id"], "applies_to": p["applies_to"]})

print_success(f"Loaded {len(parts)} parts (and {len(builtin_part_rules)} built-in applicability rules)")

# Load animal cut maps
print_step("2.6/5", "Loading animal cut maps...")
cuts_dir = os.path.join(args.in_dir, "animal_cuts")
cut_files = sorted(glob.glob(os.path.join(cuts_dir, "*.json")))
cut_pairs = []  # (taxon_id, part_id)

def ingest_node(node, parent_id=None):
    pid = node["id"]
    pname = node.get("name", pid.split(":")[-1])
    cur.execute(
        "INSERT OR REPLACE INTO part_def(id,name,kind,notes,parent_id) VALUES (?,?,?,?,?)",
        (pid, pname, "animal", node.get("notes"), parent_id)
    )
    for syn in node.get("aliases", []) or []:
        cur.execute("INSERT OR IGNORE INTO part_synonym(part_id, synonym) VALUES (?,?)", (pid, syn.lower().strip()))
    for ch in node.get("children", []) or []:
        ingest_node(ch, pid)

for cf in cut_files:
    with open(cf, "r", encoding="utf-8") as f:
        obj = json.load(f)
    taxa_for_file = obj.get("taxa", [])
    for root in obj.get("parts", []):
        ingest_node(root, None)
        # collect all part ids from this subtree for has_part
        stack = [root]
        ids = []
        while stack:
            n = stack.pop()
            ids.append(n["id"])
            stack.extend(n.get("children", []) or [])
        for tid in taxa_for_file:
            for pid in ids:
                cut_pairs.append((tid, pid))

print_success(f"Loaded animal cuts from {len(cut_files)} files")

# Load transform definitions
print_step("2.7/5", "Loading transform definitions...")
transforms_file = os.path.join(args.in_dir, "transforms.json")
if not os.path.exists(transforms_file):
    print_error(f"Transforms file not found: {transforms_file}")
    sys.exit(1)

with open(transforms_file, "r", encoding="utf-8") as f:
    tdefs = json.load(f)

print_info(f"Found {len(tdefs)} transform families")
for t in tdefs:
    schema_json = json.dumps(t.get("params", []), ensure_ascii=False)
    order = t.get("order", 999)
    notes = t.get("notes")
    cur.execute(
        "INSERT OR REPLACE INTO transform_def(id,name,identity,schema_json,ordering,notes) VALUES (?,?,?,?,?,?)",
        (t["id"], t["name"], 1 if t.get("identity") else 0, schema_json, order, notes)
    )
print_success(f"Loaded {len(tdefs)} transforms")

# Collect all taxa lines
print_step("3/5", "Loading taxa data...")
taxa_files = sorted(glob.glob(os.path.join(args.in_dir, "taxa", "*.jsonl")))
if not taxa_files:
    print_error(f"No taxa files found in {os.path.join(args.in_dir, 'taxa')}")
    sys.exit(1)

print_info(f"Found {len(taxa_files)} taxa files:")
for tf in taxa_files:
    filename = os.path.basename(tf)
    print(f"  • {filename}")

rows = []
total_lines = 0
for i, tf in enumerate(taxa_files):
    filename = os.path.basename(tf)
    print(f"\n📖 Processing {filename}...")
    
    file_rows = []
    with open(tf, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                file_rows.append(obj)
                total_lines += 1
            except json.JSONDecodeError as e:
                print_error(f"JSON decode error in {filename} line {line_num}: {e}")
                continue
    
    rows.extend(file_rows)
    print(f"  ✓ Loaded {len(file_rows)} taxa from {filename}")

print_success(f"Loaded {len(rows)} taxa from {len(taxa_files)} files")

# Load documentation data
print_step("3.5/5", "Loading documentation data...")
docs_file = os.path.join(args.in_dir, "docs.jsonl")
docs_rows = []
if os.path.exists(docs_file):
    print_info(f"Found documentation file: {os.path.basename(docs_file)}")
    with open(docs_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                docs_rows.append(obj)
            except json.JSONDecodeError as e:
                print_error(f"JSON decode error in docs line {line_num}: {e}")
                continue
    print_success(f"Loaded {len(docs_rows)} documentation records")
else:
    print_info("No documentation file found, skipping...")

# Load rules file
print_step("3.6/5", "Loading parts applicability rules...")
rules_dir = os.path.join(args.in_dir, "rules")
os.makedirs(rules_dir, exist_ok=True)
parts_rules_file = os.path.join(rules_dir, "parts_applicability.jsonl")
parts_rules = []
if os.path.exists(parts_rules_file):
    with open(parts_rules_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                parts_rules.append(obj)
            except json.JSONDecodeError as e:
                print_error(f"JSON decode error in parts_applicability line {line_num}: {e}")
else:
    print_info("No parts_applicability.jsonl found, proceeding with built-in applies_to only.")

print_success(f"Loaded {len(parts_rules)} parts applicability rules")

# Load transform applicability rules
print_step("3.7/5", "Loading transform applicability rules...")
tx_rules_file = os.path.join(args.in_dir, "rules", "transform_applicability.jsonl")
tx_rules = []
if os.path.exists(tx_rules_file):
    with open(tx_rules_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line: 
                continue
            try:
                obj = json.loads(line)
                tx_rules.append(obj)
            except json.JSONDecodeError as e:
                print_error(f"JSON decode error in transform_applicability line {line_num}: {e}")
else:
    print_info("No transform_applicability.jsonl found; continuing without explicit rules.")
print_success(f"Loaded {len(tx_rules)} transform applicability rules")

# --- NEW: load naming assets (implied parts, overrides, tp synonyms) ----------
print_step("3.8/5", "Loading naming rules (implied parts, overrides, synonyms)...")

def _read_jsonl(path):
    rows = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return rows

implied_parts_rules = _read_jsonl(os.path.join(args.in_dir, "rules", "implied_parts.jsonl"))
name_overrides_rules = _read_jsonl(os.path.join(args.in_dir, "rules", "name_overrides.jsonl"))
tp_syn_rules = _read_jsonl(os.path.join(args.in_dir, "rules", "taxon_part_synonyms.jsonl"))

print_success(f"Loaded implied_parts={len(implied_parts_rules)}, "
              f"name_overrides={len(name_overrides_rules)}, tp_synonyms={len(tp_syn_rules)}")

# Insert nodes in parent-first order using topological sort
print_step("4/5", "Sorting taxa by hierarchy depth...")
def depth(tx_id: str) -> int:
    return tx_id.count(":")

# Create a mapping of node_id to object for quick lookup
node_map = {obj["id"]: obj for obj in rows}

# Topological sort to ensure parents are inserted before children
def topological_sort(nodes):
    # Create adjacency list
    graph = {}
    in_degree = {}
    
    for node in nodes:
        node_id = node["id"]
        graph[node_id] = []
        in_degree[node_id] = 0
    
    # Build graph and calculate in-degrees
    for node in nodes:
        node_id = node["id"]
        parent = node.get("parent")
        if parent and parent in node_map:
            graph[parent].append(node_id)
            in_degree[node_id] += 1
    
    # Kahn's algorithm for topological sort
    queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        current = queue.pop(0)
        result.append(node_map[current])
        
        for neighbor in graph[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    
    return result

rows = topological_sort(rows)

# Group by depth for better progress reporting
depth_groups = {}
for row in rows:
    d = depth(row["id"])
    if d not in depth_groups:
        depth_groups[d] = []
    depth_groups[d].append(row)

print_info(f"Taxa grouped by depth: {len(depth_groups)} levels")

print_step("5/5", "Inserting taxa into database...")
nodes_inserted = 0
synonyms_inserted = 0

for i, o in enumerate(rows):
    node_id = o["id"]
    name = o.get("display_name") or o.get("latin_name") or last_segment(node_id)
    slug = last_segment(node_id).lower()
    rank = o["rank"]
    parent = o.get("parent")
    
    # Insert node
    cur.execute(
        "INSERT OR REPLACE INTO nodes(id, name, slug, rank, parent_id) VALUES(?,?,?,?,?)",
        (node_id, name, slug, rank, parent)
    )
    nodes_inserted += 1
    
    # Insert synonyms
    for syn in o.get("aliases", []):
        s = syn.strip().lower()
        if s:
            cur.execute("INSERT OR IGNORE INTO synonyms(node_id, synonym) VALUES(?,?)", (node_id, s))
            synonyms_inserted += 1
    
    # Progress indicator
    if (i + 1) % 10 == 0 or i == len(rows) - 1:
        print_progress(i + 1, len(rows), f"({node_id})")

print_success(f"Inserted {nodes_inserted} nodes and {synonyms_inserted} synonyms")

# Materialize has_part relationships
print_step("5.1/5", "Materializing has_part (taxon ↔ part) from rules...")

# Gather all taxa ids from DB
all_taxa = [row[0] for row in cur.execute("SELECT id FROM nodes").fetchall()]

def expand_applies_to(rule, all_ids):
    prefixes = rule.get("applies_to", [])
    exclude = set(rule.get("exclude", []))
    for pref in prefixes:
        for tid in all_ids:
            if tid.startswith(pref) and tid not in exclude:
                yield (tid, rule["part"])

pairs = set()

# Built-in part applies_to from parts.json
for r in builtin_part_rules:
    for pair in expand_applies_to(r, all_taxa):
        pairs.add(pair)

# External rules JSONL
for r in parts_rules:
    for pair in expand_applies_to(r, all_taxa):
        pairs.add(pair)

# Animal cut pairs
for pair in cut_pairs:
    pairs.add(pair)

cur.executemany("INSERT OR IGNORE INTO has_part(taxon_id, part_id) VALUES (?,?)", list(pairs))
print_success(f"has_part rows inserted: {len(pairs)}")

# Materialize transform_applicability
print_step("5.2/5", "Materializing transform_applicability...")

# Cache: all taxa, and has_part pairs
all_taxa = [row[0] for row in cur.execute("SELECT id FROM nodes").fetchall()]
hp_pairs = set((row[0], row[1]) for row in cur.execute("SELECT taxon_id, part_id FROM has_part").fetchall())

def expand_taxa(prefix: str):
    matched = [tid for tid in all_taxa if tid.startswith(prefix)]
    return matched

# Lint: unknown transform ids
known_tf = set(r[0] for r in cur.execute("SELECT id FROM transform_def").fetchall())
for rule in tx_rules:
    if rule["transform"] not in known_tf:
        print_error(f"Unknown transform in rule: {rule['transform']}")

# Lint: unknown parts in rules
known_parts = set(r[0] for r in cur.execute("SELECT id FROM part_def").fetchall())
for r in parts_rules:
    p = r["part"]
    if p not in known_parts:
        print_error(f"Unknown part in parts_applicability: {p}")

rows = set()
for rule in tx_rules:
    t_id = rule["transform"]
    applies = rule.get("applies_to", [])
    excludes = rule.get("exclude", [])
    excluded = set()
    for ex in excludes:
        for tid in expand_taxa(ex["taxon_prefix"]):
            for pid in ex.get("parts", []):
                excluded.add((tid, pid))
    for ap in applies:
        parts = ap.get("parts", [])
        matched = expand_taxa(ap["taxon_prefix"])
        if not matched:
            print_error(f"No taxa matched for transform rule prefix: {ap['taxon_prefix']}")
        for tid in matched:
            for pid in parts:
                if (tid, pid) in hp_pairs and (tid, pid) not in excluded:
                    rows.add((tid, pid, t_id))

cur.executemany(
    "INSERT OR IGNORE INTO transform_applicability(taxon_id, part_id, transform_id) VALUES (?,?,?)",
    list(rows)
)
print_success(f"transform_applicability rows inserted: {len(rows)}")

# --- NEW: Step 5.3 materialize Taxon+Part nodes (TP) --------------------------
print_step("5.3/5", "Materializing taxon+part nodes (with implied-part collapse & overrides)...")

# Create TP table
cur.execute("""
    CREATE TABLE IF NOT EXISTS taxon_part_nodes (
      id TEXT PRIMARY KEY,
      taxon_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
      part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
      name TEXT NOT NULL,
      display_name TEXT NOT NULL,
      slug TEXT NOT NULL,
      rank TEXT NOT NULL DEFAULT 'taxon_part',
      kind TEXT,
      UNIQUE(taxon_id, part_id)
    )
""")
cur.execute("DELETE FROM taxon_part_nodes")

# Helpers
def _is_prefix(pfx: str, s: str) -> bool:
    return s.startswith(pfx)

def _is_implied(taxon_id: str, part_id: str) -> bool:
    for r in implied_parts_rules:
        applies_to = r.get("applies_to", [])
        part = r.get("part")
        exclude = set(r.get("exclude", []))
        if part == part_id and taxon_id not in exclude:
            for prefix in applies_to:
                if _is_prefix(prefix, taxon_id):
                    return True
    return False

def _override_name(taxon_id: str, part_id: str) -> str | None:
    # choose most-specific rule (longest matching taxon_id)
    best = None
    best_len = -1
    for r in name_overrides_rules:
        tid = r.get("taxon_id")
        pid = r.get("part_id")
        nm = r.get("name")
        if not (tid and pid and nm):
            continue
        if pid == part_id and _is_prefix(tid, taxon_id) and len(tid) > best_len:
            best, best_len = nm, len(tid)
    return best

def _tp_extra_synonyms(taxon_id: str, part_id: str) -> list[str]:
    acc = []
    for r in tp_syn_rules:
        tid = r.get("taxon_id")
        pid = r.get("part_id")
        syns = r.get("synonyms", [])
        if tid and pid and _is_prefix(tid, taxon_id) and pid == part_id:
            acc.extend([s.strip().lower() for s in syns if s and isinstance(s, str)])
    return acc

# Build child/descendant index to support "leaf-for-this-part" filtering
children = {}
for nid, pid in cur.execute("SELECT id, parent_id FROM nodes"):
    if pid:
        children.setdefault(pid, []).append(nid)

def _descendants_with_part(start_id: str, wanted_part: str, hp_set: set[tuple[str,str]]) -> bool:
    stack = children.get(start_id, [])[:]
    while stack:
        cur_id = stack.pop()
        if (cur_id, wanted_part) in hp_set:
            return True
        stack.extend(children.get(cur_id, []) or [])
    return False

# Pull has_part pairs
hp_pairs = [(row[0], row[1]) for row in cur.execute("SELECT taxon_id, part_id FROM has_part")]
hp_set = set(hp_pairs)

# Rank/kingdom lookup
node_info = { row[0]: (row[1], row[2]) for row in cur.execute("SELECT id, name, rank FROM nodes") } # id -> (name, rank)
def _kingdom(tid: str) -> str | None:
    parts = tid.split(":")
    return parts[1] if len(parts) > 2 and parts[0] == "tx" else None

# part info & synonyms
part_info = { row[0]: (row[1], row[2]) for row in cur.execute("SELECT id, name, COALESCE(kind,'') FROM part_def") } # id -> (name, kind)
part_syn = {}
for pid, syn in cur.execute("SELECT part_id, synonym FROM part_synonym"):
    part_syn.setdefault(pid, set()).add(syn.strip().lower())

rows = []
fts_tp_rows = []  # (name, synonyms, 'taxon_part', kind)

for taxon_id, part_id in hp_pairs:
    tax_name, tax_rank = node_info.get(taxon_id, (None, None))
    if not tax_name:
        continue
    p_name, p_kind = part_info.get(part_id, (None, None))
    if not p_name:
        continue

    # Filter: prefer leaf-for-this-part; also allow species-level under animalia even if descendants exist
    skip = False
    if _descendants_with_part(taxon_id, part_id, hp_set):
        # keep if animalia at (sub)species to allow "Beef" + "Wagyu" side-by-side
        kg = _kingdom(taxon_id)
        keep_non_leaf = (kg == "animalia" and tax_rank in ("species", "subspecies"))
        skip = not keep_non_leaf
    if skip:
        continue

    # 1) name override (most specific wins)
    ov = _override_name(taxon_id, part_id)
    if ov:
        name = ov
        display_name = ov
    else:
        # 2) implied part collapse
        if _is_implied(taxon_id, part_id):
            name = tax_name
            display_name = tax_name
        else:
            # 3) sensible defaults
            if p_kind == "animal":
                name = f"{tax_name} {p_name}"
                display_name = name
            else:
                if part_id == "part:fruit" and tax_rank in ("species", "variety", "cultivar"):
                    name = tax_name
                    display_name = tax_name
                else:
                    name = f"{tax_name} {p_name}"
                    display_name = f"{tax_name} ({p_name})"

    tp_id = f"tp:{taxon_id}:{part_id}"
    slug = f"{taxon_id.split(':')[-1]}-{part_id.split(':')[-1]}".lower()
    rows.append((tp_id, taxon_id, part_id, name, display_name, slug, "taxon_part", p_kind))

    # Build synonyms for FTS (part synonyms + curated TP synonyms)
    syns = set()
    syns |= set(part_syn.get(part_id, set()))
    syns |= set(_tp_extra_synonyms(taxon_id, part_id))
    fts_tp_rows.append((name, " ".join(sorted(syns)), "taxon_part", p_kind))

cur.executemany(
    "INSERT OR REPLACE INTO taxon_part_nodes(id,taxon_id,part_id,name,display_name,slug,rank,kind) VALUES (?,?,?,?,?,?,?,?)",
    rows
)
print_success(f"Taxon+Part nodes generated: {len(rows)}")

# Insert documentation
if docs_rows:
    print_step("5.5/5", "Inserting documentation...")
    docs_inserted = 0
    
    for doc in docs_rows:
        cur.execute("""
            INSERT OR REPLACE INTO taxon_doc(
                taxon_id, lang, summary, description_md,
                updated_at, checksum, rank, latin_name, display_name, tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc["taxon_id"],
            doc["lang"],
            doc["summary"],
            doc["description_md"],
            doc["updated_at"],
            doc["checksum"],
            doc.get("rank"),
            doc.get("latin_name"),
            doc.get("display_name"),
            json.dumps(doc.get("tags", [])) if doc.get("tags") else None
        ))
        docs_inserted += 1
    
    print_success(f"Inserted {docs_inserted} documentation records")

# Create and populate FTS table for search functionality
print_step("6/6", "Creating full-text search index...")

# Create FTS table (now unified: taxa + taxon_part)
cur.execute("""
    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts
    USING fts5(name, synonyms, taxon_rank, kind);
""")

# Populate FTS table with TAXA first
cur.execute("""
    INSERT INTO nodes_fts(name,synonyms,taxon_rank,kind)
    SELECT n.name, COALESCE(GROUP_CONCAT(s.synonym,' '), ''), n.rank, NULL
    FROM nodes n
    LEFT JOIN synonyms s ON s.node_id = n.id
    GROUP BY n.id;
""")

# Populate FTS with TAXON+PART rows (names + merged synonyms)
if fts_tp_rows:
    cur.executemany(
        "INSERT INTO nodes_fts(name, synonyms, taxon_rank, kind) VALUES (?,?,?,?)",
        fts_tp_rows
    )

fts_count = cur.execute("SELECT COUNT(*) FROM nodes_fts").fetchone()[0]
print_success(f"Created FTS index with {fts_count} entries")

# Create triggers to keep FTS in sync
cur.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_nodes_ai AFTER INSERT ON nodes BEGIN
      INSERT INTO nodes_fts(name,synonyms,taxon_rank,kind)
      VALUES (NEW.name, '', NEW.rank, NULL);
    END;
""")

cur.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_nodes_ad AFTER DELETE ON nodes BEGIN
      DELETE FROM nodes_fts WHERE name = OLD.name AND taxon_rank = OLD.rank AND kind IS NULL;
    END;
""")

cur.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_nodes_au AFTER UPDATE OF name,rank ON nodes BEGIN
      UPDATE nodes_fts SET name = NEW.name, taxon_rank = NEW.rank
      WHERE name = OLD.name AND taxon_rank = OLD.rank AND kind IS NULL;
    END;
""")

cur.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_synonyms_ai AFTER INSERT ON synonyms BEGIN
      UPDATE nodes_fts SET synonyms = TRIM(
        COALESCE(synonyms,'') || ' ' || NEW.synonym
      ) WHERE rowid = (
        SELECT n.rowid FROM nodes n WHERE n.id = NEW.node_id
      );
    END;
""")

cur.execute("""
    CREATE TRIGGER IF NOT EXISTS trg_synonyms_ad AFTER DELETE ON synonyms BEGIN
      UPDATE nodes_fts SET synonyms = (
        SELECT TRIM(COALESCE(GROUP_CONCAT(s2.synonym,' '), ''))
        FROM synonyms s2 WHERE s2.node_id = OLD.node_id
      ) WHERE rowid = (
        SELECT n.rowid FROM nodes n WHERE n.id = OLD.node_id
      );
    END;
""")

print_success("Created FTS triggers for automatic synchronization")

# Final commit and summary
print("\n" + "=" * 50)
print("📊 COMPILATION SUMMARY")
print("=" * 50)

con.commit()
con.close()

# Get final statistics
con = sqlite3.connect(args.out_path)
cur = con.cursor()

node_count = cur.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
synonym_count = cur.execute("SELECT COUNT(*) FROM synonyms").fetchone()[0]
attr_count = cur.execute("SELECT COUNT(*) FROM attr_def").fetchone()[0]
docs_count = cur.execute("SELECT COUNT(*) FROM taxon_doc").fetchone()[0]
has_part_count = cur.execute("SELECT COUNT(*) FROM has_part").fetchone()[0]
tf_count = cur.execute("SELECT COUNT(*) FROM transform_def").fetchone()[0]
tfap_count = cur.execute("SELECT COUNT(*) FROM transform_applicability").fetchone()[0]
fts_count = cur.execute("SELECT COUNT(*) FROM nodes_fts").fetchone()[0]

# Get rank distribution
rank_stats = cur.execute("SELECT rank, COUNT(*) FROM nodes GROUP BY rank ORDER BY COUNT(*) DESC").fetchall()

print(f"✅ Database created: {args.out_path}")
print(f"📈 Total nodes: {node_count}")
print(f"🏷️  Total synonyms: {synonym_count}")
print(f"🔧 Total attributes: {attr_count}")
print(f"📚 Total documentation records: {docs_count}")
print(f"🧩 Total has_part rows: {has_part_count}")
print(f"🛠️  Total transform defs: {tf_count}")
print(f"🔗 Total transform_applicability rows: {tfap_count}")
print(f"🔍 Total FTS entries: {fts_count}")
print(f"\n📊 Node distribution by rank:")
for rank, count in rank_stats:
    print(f"  • {rank}: {count}")

end_time = time.time()
execution_time = end_time - start_time
print(f"\n⏱️  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"⏱️  Execution time: {execution_time:.2f} seconds")
print("🎉 Compilation successful!")