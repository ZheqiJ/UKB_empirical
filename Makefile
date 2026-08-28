.PHONY: run test its clean

APPLICATIONS ?= /mnt/data/application\ \(1\)\(1\).txt
OUTPUT_DIR ?= ukb_dmca
CACHE_DIR ?= .cache/ukb_dmca
ITS_SCRIPT ?= analyses/interrupted_time_series/scripts/build_its_feasibility.py

run:
	python3 scripts/ukb_dmca_pipeline.py --applications "$(APPLICATIONS)" --output-dir "$(OUTPUT_DIR)" --cache-dir "$(CACHE_DIR)"

test:
	python3 -m unittest discover -s tests

its:
	python3 "$(ITS_SCRIPT)"

clean:
	rm -rf .cache/ukb_dmca
