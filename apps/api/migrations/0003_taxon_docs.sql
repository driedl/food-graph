-- Taxon documentation table
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

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_taxon_doc_taxon_id ON taxon_doc(taxon_id);
CREATE INDEX IF NOT EXISTS idx_taxon_doc_lang ON taxon_doc(lang);
CREATE INDEX IF NOT EXISTS idx_taxon_doc_updated ON taxon_doc(updated_at);

-- FTS for documentation content
CREATE VIRTUAL TABLE IF NOT EXISTS taxon_doc_fts
USING fts5(taxon_id UNINDEXED, lang UNINDEXED, summary, description_md, content='');

-- Seed FTS index
INSERT INTO taxon_doc_fts(taxon_id, lang, summary, description_md)
SELECT taxon_id, lang, summary, description_md
FROM taxon_doc;

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS trg_taxon_doc_ai AFTER INSERT ON taxon_doc BEGIN
  INSERT INTO taxon_doc_fts(taxon_id, lang, summary, description_md)
  VALUES (NEW.taxon_id, NEW.lang, NEW.summary, NEW.description_md);
END;

CREATE TRIGGER IF NOT EXISTS trg_taxon_doc_ad AFTER DELETE ON taxon_doc BEGIN
  DELETE FROM taxon_doc_fts WHERE taxon_id = OLD.taxon_id AND lang = OLD.lang;
END;

CREATE TRIGGER IF NOT EXISTS trg_taxon_doc_au AFTER UPDATE OF summary,description_md ON taxon_doc BEGIN
  UPDATE taxon_doc_fts 
  SET summary = NEW.summary, description_md = NEW.description_md
  WHERE taxon_id = NEW.taxon_id AND lang = NEW.lang;
END;
