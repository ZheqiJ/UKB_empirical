.PHONY: run test test-archive its clean

APPLICATIONS ?= /mnt/data/application\ \(1\)\(1\).txt
OUTPUT_DIR ?= ukb_dmca
CACHE_DIR ?= .cache/ukb_dmca
ITS_SCRIPT ?= new_comparative_its/scripts/new_comparative_its.py
CURRENT_TESTS ?= new_comparative_its/tests
PROJECT_ENTRY_TESTS ?= archive/02_project_entry_its/tests
PROJECT_ENTRY2_TESTS ?= archive/03_project_entry_high_vs_lower/tests
PUBLICATION_TESTS ?= archive/04_publication_its/tests

run:
	python3 scripts/ukb_dmca_pipeline.py --applications "$(APPLICATIONS)" --output-dir "$(OUTPUT_DIR)" --cache-dir "$(CACHE_DIR)"

test:
	python3 -m unittest discover -s tests
	python3 -m unittest discover -s "$(CURRENT_TESTS)"

test-archive:
	python3 -m unittest discover -s "$(PROJECT_ENTRY_TESTS)"
	python3 -m unittest discover -s "$(PROJECT_ENTRY2_TESTS)"
	python3 -m unittest discover -s "$(PUBLICATION_TESTS)"

its:
	python3 "$(ITS_SCRIPT)"

clean:
	rm -rf .cache/ukb_dmca
