# Competency Questions (CQ) Harness

This directory contains the formal Competency Question harness for Project Priory.

Competency Questions are real-world domain questions expressed in plain natural language, paired with executable semantic queries (or constraints/axioms) and deterministic expected results against the knowledge graph.

---

## 1. Rules & Architecture Layers

Each competency question is mapped to the ontological or computational layer best equipped to answer it:

1. **OWL (Axiomatic / TBox Reasoner)**:
   * Used for taxonomic classification, satisfiability, subsumption, disjointness, and domain/range entailments.
2. **SHACL (Graph Validation / Structural Constraints)**:
   * Used for shape validation, cardinality constraints, type checks, and structural invariants.
3. **SPARQL (Instance Query / Graph Traversal)**:
   * Used for deterministic graph pattern matching, path traversal (`(priory:acquiredVia|priory:hasSubstituteSource)`), and relational queries across instances and vocabularies.
4. **Python (Dynamic Engine / Arithmetic Optimization)**:
   * Used for stateful arithmetic, live inventory diffing, cost minimization, and scheduling algorithms where formal OWL/SPARQL is insufficient or undecidable.

---

## 2. File Template & Structure

For each competency question `cqXX`:
1. `cqXX_<name>.rq`: The executable SPARQL query file.
2. `cqXX_<name>.expected.json`: The expected result dataset formatted as JSON (list of objects with binding keys), verified by hand against the RDF source files.
3. Metadata headers in each `.rq` file:
   ```sparql
   # Title: <Brief question summary>
   # Question: <Plain English natural language question>
   # Layer: <OWL | SHACL | SPARQL | Python>
   # Status: baseline
   # Source Files: <Relevant .ttl file paths>
   ```

---

## 3. Seed Baseline Questions

| CQ ID | Question | Layer | Status | Key Pattern / Predicate |
| :--- | :--- | :--- | :--- | :--- |
| **CQ01** | What acquisition pathways and substitute sources exist for Mystic Clover (item 19675)? | SPARQL | `baseline` | `(priory:acquiredVia\|priory:hasSubstituteSource)` |
| **CQ02** | What are the direct required items and quantities to forge Twilight in the Mystic Forge? | SPARQL | `baseline` | `recipe:forge_twilight`, `priory:hasIngredientRequirement` |
| **CQ03** | Which items can be acquired via vendor exchange using Astral Acclaim currency? | SPARQL | `baseline` | `priory:VendorExchangePath`, `currency:AstralAcclaim` |
| **CQ04** | What are all nine crafting disciplines in the reference vocabulary, along with their English labels and notations? | SPARQL | `baseline` | `priory-ref:DisciplineScheme`, `skos:prefLabel` |
| **CQ05** | Which legendary items specify a maximum Legendary Armory account saturation limit? | SPARQL | `baseline` | `priory:armoryMaxCap`, `rdfs:label` |

---

## 4. Execution

To execute the full competency question suite:
```bash
pytest tests/test_competency_questions.py -v
```
Or via the one-command check target:
```bash
make check
```
