.PHONY: run test its clean

APPLICATIONS ?= /mnt/data/application\ \(1\)\(1\).txt
OUTPUT_DIR ?= ukb_dmca
CACHE_DIR ?= .cache/ukb_dmca
ITS_SCRIPT ?= analyses/interrupted_time_series/shared/build_its_feasibility.py
PROJECT_ENTRY_TESTS ?= analyses/interrupted_time_series/project_entry/tests
PROJECT_ENTRY2_TESTS ?= analyses/interrupted_time_series/project_entry2/tests
PUBLICATION_TESTS ?= analyses/interrupted_time_series/publications/tests

run:
	python3 scripts/ukb_dmca_pipeline.py --applications "$(APPLICATIONS)" --output-dir "$(OUTPUT_DIR)" --cache-dir "$(CACHE_DIR)"

test:
	python3 -m unittest discover -s tests
	python3 -m unittest discover -s "$(PROJECT_ENTRY_TESTS)"
	python3 -m unittest discover -s "$(PROJECT_ENTRY2_TESTS)"
	python3 -m unittest discover -s "$(PUBLICATION_TESTS)"

its:
	python3 "$(ITS_SCRIPT)"

clean:
	rm -rf .cache/ukb_dmca
