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
  kind TEXT NOT NULL DEFAULT 'categorical' -- numeric|boolean|categorical
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
""")

print_info("Clearing existing data...")
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
    cur.execute("INSERT OR IGNORE INTO attr_def(attr, kind) VALUES (?,?)", (a["id"].replace("attr:", ""), kind))
    if args.verbose:
        print(f"  • {a['id']} ({kind}) - {a.get('name', 'No name')}")

print_success(f"Loaded {len(attrs)} attribute definitions")

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

# Get rank distribution
rank_stats = cur.execute("SELECT rank, COUNT(*) FROM nodes GROUP BY rank ORDER BY COUNT(*) DESC").fetchall()

print(f"✅ Database created: {args.out_path}")
print(f"📈 Total nodes: {node_count}")
print(f"🏷️  Total synonyms: {synonym_count}")
print(f"🔧 Total attributes: {attr_count}")
print(f"📚 Total documentation records: {docs_count}")
print(f"\n📊 Node distribution by rank:")
for rank, count in rank_stats:
    print(f"  • {rank}: {count}")

end_time = time.time()
execution_time = end_time - start_time
print(f"\n⏱️  Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"⏱️  Execution time: {execution_time:.2f} seconds")
print("🎉 Compilation successful!")