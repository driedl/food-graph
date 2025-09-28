.PHONY: validate compile all

validate:
	python3 scripts/validate_taxa.py --taxa-root data/ontology/taxa

compile:
	python3 scripts/compile_taxa.py --taxa-root data/ontology/taxa --out data/ontology/compiled/taxa/taxa.jsonl

all:
	make validate && make compile

# Build database from compiled assets
db-build:
	pnpm db:build
