.PHONY: run test clean

APPLICATIONS ?= /mnt/data/application\ \(1\)\(1\).txt
OUTPUT_DIR ?= .
CACHE_DIR ?= .cache/ukb_dmca

run:
	python3 scripts/ukb_dmca_pipeline.py --applications "$(APPLICATIONS)" --output-dir "$(OUTPUT_DIR)" --cache-dir "$(CACHE_DIR)"

test:
	python3 -m unittest discover -s tests

clean:
	rm -rf .cache/ukb_dmca

