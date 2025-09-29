-- Ontology extensions: parts hierarchy, attributes with roles/enums, transform ordering
-- parts: hierarchy + synonyms
ALTER TABLE part_def ADD COLUMN parent_id TEXT REFERENCES part_def(id) ON DELETE SET NULL;
CREATE TABLE IF NOT EXISTS part_synonym (
  part_id TEXT NOT NULL REFERENCES part_def(id) ON DELETE CASCADE,
  synonym TEXT NOT NULL,
  PRIMARY KEY (part_id, synonym)
);

-- attributes: role + enums
ALTER TABLE attr_def ADD COLUMN role TEXT CHECK(role IN ('identity_param','taxon_refinement','covariate','facet')) DEFAULT NULL;
CREATE TABLE IF NOT EXISTS attr_enum (
  attr TEXT NOT NULL REFERENCES attr_def(attr) ON DELETE CASCADE,
  val  TEXT NOT NULL,
  PRIMARY KEY (attr, val)
);

-- transforms: ordering + notes
ALTER TABLE transform_def ADD COLUMN ordering INTEGER DEFAULT 999;
ALTER TABLE transform_def ADD COLUMN notes TEXT;
