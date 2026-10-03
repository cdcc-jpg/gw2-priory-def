"""Pytest runner for Project Priory Competency Questions."""

import json
from pathlib import Path
import pytest
import rdflib

REPO_ROOT = Path(__file__).resolve().parent.parent
CQ_DIR = REPO_ROOT / "docs" / "competency_questions"
DEF_ONTOLOGY = REPO_ROOT / "ontology"
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")


@pytest.fixture(scope="session")
def merged_graph():
    """Builds and caches the full merged RDF graph."""
    g = rdflib.Graph()

    # Load all ontology files and instances from gw2-priory-def
    for ttl in DEF_ONTOLOGY.rglob("*.ttl"):
        g.parse(ttl, format="turtle")

    # Load all vocabularies from gw2-priory-ref
    if (REF_REPO / "vocab").exists():
        for ttl in (REF_REPO / "vocab").rglob("*.ttl"):
            g.parse(ttl, format="turtle")

    return g


def get_cq_files():
    """Discovers all .rq files in docs/competency_questions/."""
    rq_files = sorted(CQ_DIR.glob("*.rq"))
    return [rq for rq in rq_files if (rq.parent / f"{rq.stem}.expected.json").exists()]


@pytest.mark.parametrize("rq_file", get_cq_files(), ids=lambda p: p.stem)
def test_competency_question(merged_graph, rq_file):
    """Executes a competency question SPARQL query and validates against expected JSON."""
    expected_file = rq_file.parent / f"{rq_file.stem}.expected.json"

    with open(rq_file, "r", encoding="utf-8") as f:
        sparql_query = f.read()

    with open(expected_file, "r", encoding="utf-8") as f:
        expected_rows = json.load(f)

    res = merged_graph.query(sparql_query)
    vars = [str(v) for v in res.vars]

    actual_rows = []
    for row in res:
        d = {}
        for i, val in enumerate(row):
            d[vars[i]] = str(val) if val is not None else None
        actual_rows.append(d)

    assert len(actual_rows) == len(
        expected_rows
    ), f"Row count mismatch for {rq_file.name}: got {len(actual_rows)}, expected {len(expected_rows)}"

    assert (
        actual_rows == expected_rows
    ), f"Results mismatch for {rq_file.name}:\nActual: {actual_rows}\nExpected: {expected_rows}"
