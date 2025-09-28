.PHONY: validate compile compile-docs all

validate:
	python3 scripts/validate_taxa.py --taxa-root data/ontology/taxa

compile:
	python3 scripts/compile_taxa.py --taxa-root data/ontology/taxa --out data/ontology/compiled/taxa/taxa.jsonl

compile-docs:
	python3 scripts/compile_docs.py --taxa-root data/ontology/taxa --compiled-taxa data/ontology/compiled/taxa/taxa.jsonl --out data/ontology/compiled/docs.jsonl

all:
	make validate && make compile && make compile-docs

# Build database from compiled assets
db-build:
	pnpm db:build
