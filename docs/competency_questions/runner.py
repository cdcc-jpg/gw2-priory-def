#!/usr/bin/env python3
"""Standalone runner for Project Priory Competency Questions."""

import json
from pathlib import Path
import sys
import rdflib

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CQ_DIR = REPO_ROOT / "docs" / "competency_questions"
DEF_ONTOLOGY = REPO_ROOT / "ontology"
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")


def run_all_cqs():
    print("Building merged graph for Competency Questions...")
    g = rdflib.Graph()
    for ttl in DEF_ONTOLOGY.rglob("*.ttl"):
        g.parse(ttl, format="turtle")
    if (REF_REPO / "vocab").exists():
        for ttl in (REF_REPO / "vocab").rglob("*.ttl"):
            g.parse(ttl, format="turtle")

    rq_files = sorted(CQ_DIR.glob("*.rq"))
    print(f"Discovered {len(rq_files)} competency question(s).")

    passed = 0
    failed = 0

    for rq_file in rq_files:
        expected_file = rq_file.parent / f"{rq_file.stem}.expected.json"
        if not expected_file.exists():
            print(f"SKIP: {rq_file.name} (no expected JSON found)")
            continue

        with open(rq_file, "r", encoding="utf-8") as f:
            sparql_query = f.read()
        with open(expected_file, "r", encoding="utf-8") as f:
            expected_rows = json.load(f)

        try:
            res = g.query(sparql_query)
            vars = [str(v) for v in res.vars]
            actual_rows = []
            for row in res:
                d = {}
                for i, val in enumerate(row):
                    d[vars[i]] = str(val) if val is not None else None
                actual_rows.append(d)

            if actual_rows == expected_rows:
                print(f"PASS: {rq_file.name} ({len(actual_rows)} rows matched)")
                passed += 1
            else:
                print(f"FAIL: {rq_file.name} (results mismatch)")
                print(f"  Expected {len(expected_rows)} rows, got {len(actual_rows)}")
                failed += 1
        except Exception as e:
            print(f"ERROR: {rq_file.name}: {e}")
            failed += 1

    print(f"\nSummary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_cqs())
