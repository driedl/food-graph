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
  node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  synonym TEXT NOT NULL,
  PRIMARY KEY (node_id, synonym)
);

CREATE TABLE IF NOT EXISTS node_attributes (
  node_id TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
  attr TEXT NOT NULL,
  val TEXT NOT NULL,
  PRIMARY KEY (node_id, attr, val)
);

CREATE TABLE IF NOT EXISTS attr_def (
  attr TEXT PRIMARY KEY,
  kind TEXT NOT NULL CHECK(kind IN ('numeric','boolean','categorical'))
);