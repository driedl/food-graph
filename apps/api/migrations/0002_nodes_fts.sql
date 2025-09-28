CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(name, slug, content='nodes', content_rowid='rowid');

CREATE TRIGGER IF NOT EXISTS nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(rowid, name, slug) VALUES (new.rowid, new.name, new.slug);
END;

CREATE TRIGGER IF NOT EXISTS nodes_ad AFTER DELETE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, name, slug) VALUES('delete', old.rowid, old.name, old.slug);
END;

CREATE TRIGGER IF NOT EXISTS nodes_au AFTER UPDATE ON nodes BEGIN
  INSERT INTO nodes_fts(nodes_fts, rowid, name, slug) VALUES('delete', old.rowid, old.name, old.slug);
  INSERT INTO nodes_fts(rowid, name, slug) VALUES (new.rowid, new.name, new.slug);
END;

-- Populate FTS for existing data
INSERT INTO nodes_fts(rowid, name, slug) 
SELECT rowid, name, slug FROM nodes;
