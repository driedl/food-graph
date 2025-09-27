import argparse, os, sqlite3
parser = argparse.ArgumentParser()
parser.add_argument("--in", dest="in_dir", required=True)
parser.add_argument("--out", dest="out_path", required=True)
args = parser.parse_args()
os.makedirs(os.path.dirname(args.out_path), exist_ok=True)
con = sqlite3.connect(args.out_path)
cur = con.cursor()
# minimal tables to satisfy API migrations later
cur.executescript("""
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, name TEXT, slug TEXT, rank TEXT, parent_id TEXT);
CREATE TABLE IF NOT EXISTS synonyms (node_id TEXT, synonym TEXT, PRIMARY KEY(node_id, synonym));
CREATE TABLE IF NOT EXISTS node_attributes (node_id TEXT, attr TEXT, val TEXT, PRIMARY KEY(node_id, attr, val));
CREATE TABLE IF NOT EXISTS attr_def (attr TEXT PRIMARY KEY, kind TEXT NOT NULL DEFAULT 'categorical');
""")
con.commit(); con.close()
print(f"Built {args.out_path}")