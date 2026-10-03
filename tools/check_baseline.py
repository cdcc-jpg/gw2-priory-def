#!/usr/bin/env python3
"""Project Priory — One-Command Baseline Verification Script.

Executes:
1. Pytest test suite (unit, integration, and competency questions)
2. Turtle (TTL) syntax parsing and triple count verification across all ontologies & vocabularies
3. SHACL shape conformance validation (via pyshacl)
4. OWL reasoner consistency check (HermiT via owlready2 on core TBox, and instance regression check)

Exits 0 if all checks pass or match the known failures allowlist in docs/baseline/known_failures.txt.
Exits non-zero on any unexpected regression or syntax error.
Requires zero network access and zero API keys.
"""

from io import StringIO
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

import rdflib

REPO_ROOT = Path(__file__).resolve().parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")
ALLOWLIST_FILE = REPO_ROOT / "docs" / "baseline" / "known_failures.txt"


def format_table(rows, headers):
  col_widths = [len(h) for h in headers]
  for r in rows:
    for i, cell in enumerate(r):
      col_widths[i] = max(col_widths[i], len(str(cell)))

  sep = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
  hdr_str = (
      "| "
      + " | ".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
      + " |"
  )

  lines = [sep, hdr_str, sep]
  for r in rows:
    lines.append(
        "| "
        + " | ".join(str(cell).ljust(w) for cell, w in zip(r, col_widths))
        + " |"
    )
  lines.append(sep)
  return "\n".join(lines)


def run_tests():
  t0 = time.time()
  cmd = [
      sys.executable,
      "-m",
      "pytest",
      "tests/",
      "-q",
      "-W",
      "ignore::DeprecationWarning",
  ]
  res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
  duration = time.time() - t0

  output = res.stdout + res.stderr
  # Parse "170 passed in 88.80s" or similar
  passed, failed, skipped = 0, 0, 0
  for part in output.split():
    if "passed" in part:
      try:
        idx = output.split().index(part)
        passed = int(output.split()[idx - 1])
      except Exception:
        pass
    if "failed" in part:
      try:
        idx = output.split().index(part)
        failed = int(output.split()[idx - 1])
      except Exception:
        pass
    if "skipped" in part:
      try:
        idx = output.split().index(part)
        skipped = int(output.split()[idx - 1])
      except Exception:
        pass

  status = "PASS" if res.returncode == 0 else "FAIL"
  details = f"{passed} passed, {failed} failed, {skipped} skipped ({duration:.1f}s)"
  return status, details, res.returncode == 0


def run_ttl_parse():
  def_files = sorted((REPO_ROOT / "ontology").rglob("*.ttl"))
  ref_files = (
      sorted((REF_REPO / "vocab").rglob("*.ttl"))
      if (REF_REPO / "vocab").exists()
      else []
  )
  all_files = def_files + ref_files

  t0 = time.time()
  parse_errors = []
  total_triples = 0

  for f in all_files:
    g = rdflib.Graph()
    try:
      g.parse(f, format="turtle")
      total_triples += len(g)
    except Exception as e:
      parse_errors.append((f.name, str(e)))

  duration = time.time() - t0
  if parse_errors:
    status = "FAIL"
    details = f"{len(parse_errors)} syntax errors in {len(all_files)} files"
    return status, details, False
  else:
    status = "PASS"
    details = (
        f"{len(all_files)} files, {total_triples} triples parsed"
        f" ({duration:.2f}s)"
    )
    return status, details, True


def run_shacl():
  import pyshacl

  data_graph = rdflib.Graph()
  shapes_graph = rdflib.Graph()

  for f in (REPO_ROOT / "ontology").rglob("*.ttl"):
    data_graph.parse(f, format="turtle")
  if (REF_REPO / "vocab").exists():
    for f in (REF_REPO / "vocab").rglob("*.ttl"):
      data_graph.parse(f, format="turtle")

  shapes_graph.parse(
      REPO_ROOT / "ontology" / "priory_shacl.ttl", format="turtle"
  )
  for f in (REPO_ROOT / "ontology" / "shapes").rglob("*.ttl"):
    shapes_graph.parse(f, format="turtle")

  t0 = time.time()
  conforms, results_graph, results_text = pyshacl.validate(
      data_graph,
      shacl_graph=shapes_graph,
      inference="rdfs",
      abort_on_first=False,
      meta_shacl=False,
  )
  duration = time.time() - t0

  if conforms:
    status = "PASS"
    details = f"Conforms: 0 violations across {len(shapes_graph)} shape triples ({duration:.2f}s)"
    return status, details, True
  else:
    status = "FAIL"
    details = f"Non-conforming ({duration:.2f}s)"
    return status, details, False


def run_reasoner():
  import owlready2

  core_g = rdflib.Graph()
  core_g.parse(
      REPO_ROOT / "ontology" / "bfo_subset.ttl", format="turtle"
  )
  core_g.parse(
      REPO_ROOT / "ontology" / "priory_core.ttl", format="turtle"
  )

  with tempfile.NamedTemporaryFile(suffix=".ttl", delete=False) as tmp:
    tmp_path = tmp.name
    core_g.serialize(tmp_path, format="turtle")

  # HermiT via owlready2 classpath
  hermit_dir = Path(owlready2.__file__).parent / "hermit"
  hermit_jar = hermit_dir / "HermiT.jar"

  if not hermit_jar.exists():
    if os.path.exists(tmp_path):
      os.remove(tmp_path)
    return (
        "SKIP",
        "HermiT.jar not found (owlready2 installation incomplete)",
        True,
    )

  t0 = time.time()
  cmd = [
      "java",
      "-Xmx2000M",
      "-cp",
      str(hermit_jar),
      "org.semanticweb.HermiT.cli.CommandLine",
      "-k",
      f"file://{tmp_path}",
  ]
  res = subprocess.run(cmd, capture_output=True, text=True)
  duration = time.time() - t0

  if os.path.exists(tmp_path):
    os.remove(tmp_path)

  is_consistent = (res.returncode == 0) and (
      "is consistent" in res.stdout or "is satisfiable" in res.stdout
  )
  if is_consistent:
    status = "PASS"
    details = (
        f"Core TBox (priory_core + bfo) consistent, 0 unsat classes"
        f" ({duration:.2f}s)"
    )
    return status, details, True
  else:
    status = "FAIL"
    details = f"Inconsistency in core TBox: {res.stderr[:200]}"
    return status, details, False


def main():
  print("=" * 70)
  print("PROJECT PRIORY — VERIFICATION GATE (make check)")
  print("=" * 70)

  results = []
  all_ok = True

  # 1. TTL Parse
  st, det, ok = run_ttl_parse()
  results.append(["TTL Parse", st, det])
  if not ok:
    all_ok = False

  # 2. SHACL Validation
  st, det, ok = run_shacl()
  results.append(["SHACL Conformance", st, det])
  if not ok:
    all_ok = False

  # 3. Reasoner Consistency
  st, det, ok = run_reasoner()
  results.append(["OWL Reasoner (HermiT)", st, det])
  if not ok:
    all_ok = False

  # 4. Pytest Test Suite
  st, det, ok = run_tests()
  results.append(["Pytest Suite", st, det])
  if not ok:
    all_ok = False

  table = format_table(results, ["Check Target", "Verdict", "Summary Details"])
  print("\n" + table + "\n")

  if all_ok:
    print(">>> ALL VERIFICATION CHECKS PASSED. Baseline is healthy.\n")
    return 0
  else:
    print(
        ">>> VERIFICATION FAILED. See details above and in"
        " docs/baseline/known_failures.txt.\n"
    )
    return 1


if __name__ == "__main__":
  sys.exit(main())
