-- contentless FTS so we can index names + synonyms
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts
USING fts5(id UNINDEXED, name, synonyms, rank, content='');

-- seed index from current rows
INSERT INTO nodes_fts(id,name,synonyms,rank)
SELECT n.id, n.name, COALESCE(GROUP_CONCAT(s.synonym,' '), ''), n.rank
FROM nodes n
LEFT JOIN synonyms s ON s.node_id = n.id
GROUP BY n.id;

-- triggers to keep it in sync
CREATE TRIGGER IF NOT EXISTS trg_nodes_ai AFTER INSERT ON nodes BEGIN
  INSERT INTO nodes_fts(id,name,synonyms,rank)
  VALUES (NEW.id, NEW.name, '', NEW.rank);
END;

CREATE TRIGGER IF NOT EXISTS trg_nodes_ad AFTER DELETE ON nodes BEGIN
  DELETE FROM nodes_fts WHERE id = OLD.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_nodes_au AFTER UPDATE OF name,rank ON nodes BEGIN
  UPDATE nodes_fts SET name = NEW.name, rank = NEW.rank WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS trg_synonyms_ai AFTER INSERT ON synonyms BEGIN
  UPDATE nodes_fts SET synonyms = TRIM(
    COALESCE(synonyms,'') || ' ' || NEW.synonym
  ) WHERE id = NEW.node_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_synonyms_ad AFTER DELETE ON synonyms BEGIN
  -- rebuild synonyms bag when a synonym is removed
  UPDATE nodes_fts SET synonyms = (
    SELECT TRIM(COALESCE(GROUP_CONCAT(s2.synonym,' '), ''))
    FROM synonyms s2 WHERE s2.node_id = OLD.node_id
  ) WHERE id = OLD.node_id;
END;