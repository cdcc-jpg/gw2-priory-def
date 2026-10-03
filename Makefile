.PHONY: check test test-cq test-all shacl reasoner clean help

PYTHON ?= python3

help:
	@echo "Project Priory — Ontological Engineering & Verification Targets"
	@echo "================================================================"
	@echo "  make check      - Full baseline check (TTL parse, SHACL, HermiT reasoner, tests)"
	@echo "  make test       - Run test suite with deprecation warnings suppressed"
	@echo "  make test-cq    - Run competency questions test suite"
	@echo "  make shacl      - Run SHACL shapes conformance validation"
	@echo "  make clean      - Clean python cache, coverage, and temporary test artifacts"

check:
	@$(PYTHON) tools/check_baseline.py

test:
	@$(PYTHON) -m pytest tests/ -v -W ignore::DeprecationWarning

test-cq:
	@$(PYTHON) -m pytest tests/test_competency_questions.py -v -W ignore::DeprecationWarning

clean:
	@rm -rf .pytest_cache htmlcov .coverage
	@find . -type d -name "__pycache__" -exec rm -rf {} +
