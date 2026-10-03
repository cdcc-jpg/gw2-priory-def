# Project Priory — Ontologist Groundwork & Baseline Handoff

**Author:** Antigravity Groundwork Agent  
**Date:** October 3, 2026  
**Branches Created:**
- `gw2-priory-def`: `chore/groundwork` (branched from `feat/catalog-v0.1`)
- `leurn-app-ontology-tool`: `chore/fitness-check` (branched from `main`)
- `gw2-priory-ref`: Clean / untouched (`feat/catalog-v0.1`)

---

## 1. Groundwork Status & Execution Summary

### 1.1 What Ran and Passed
1. **Full Pytest Test Suite (`tests/`)**:
   * Executed 170 tests (165 pre-existing engine/agent/ontology tests + 5 newly introduced Competency Question verification tests in `tests/test_competency_questions.py`).
   * **Result:** 170 passed, 0 failed, 0 skipped.
2. **TTL Syntax Parsing & Triple Inventory**:
   * Parsed all 62 `.ttl` files across `gw2-priory-def` (50 files) and `gw2-priory-ref` (12 files) via RDFLib 7.6.0.
   * **Result:** 0 parse errors; 21,300 total raw triples, merging into 19,803 distinct triples.
3. **SHACL Conformance Validation (`pyshacl 0.31.0`)**:
   * Validated merged data graph against `priory_shacl.ttl`, `character_shape.ttl`, and `role_shape.ttl` (376 shape triples).
   * **Result:** Under standard RDFS inference, **Conforms: True** (0 violations in 1.89s).
4. **OWL Reasoner Consistency on Core TBox**:
   * Executed HermiT 1.4.3 via `owlready2` under Java 1.8.0_501 on `priory_core.ttl` + `bfo_subset.ttl`.
   * **Result:** **Consistent: True**; 0 unsatisfiable classes in 0.96s.
5. **One-Command Verification Gate (`make check`)**:
   * Implemented `tools/check_baseline.py` and `Makefile` target `make check`.
   * Runs tests, TTL parse, SHACL, and HermiT in under 90s offline without network or API keys.
6. **Competency Question Harness (`docs/competency_questions/`)**:
   * Created scaffolding, runner, and 5 seed SPARQL queries (`cq01` to `cq05`) with verified expected JSON datasets.
   * Includes `cq01_mystic_clover_sources.rq` testing `(priory:acquiredVia|priory:hasSubstituteSource)`.
7. **Authoring Tool Fitness Check (`leurn-app-ontology-tool`)**:
   * Completed build/test baseline, round-trip fidelity benchmark, reasoner cross-check, scale profiling, SPARQL engine tests, 10-workflow evaluation, and code review in `docs/baseline/AUTHORING_TOOL_FITNESS.md`.

### 1.2 What Failed and Why
1. **Full Merged Graph Inconsistency under HermiT**:
   * When instance files and vocabularies are merged with `priory_core.ttl`, HermiT reports an inconsistent ontology.
   * **Root Causes Forensically Isolated:**
     a. `priory:LedgerToken owl:disjointWith priory:Item` (`priory_core.ttl:166`) conflicts with 3 individuals (`item:19675`, `item:19976`, `item:19721`) asserted as both `priory:ContainerizedToken` and `priory:Item`/`priory:CraftingMaterial`.
     b. `priory:zoneLevel` range is `xsd:integer` (`priory_core.ttl:275`), but instances in `core_exploration.ttl` assign string literals `"1-80"` and `"70-80"`.
     c. Datatype properties with `rdfs:range xsd:string` (`priory:vendorNPC`, `priory:zoneName`) receive language-tagged `rdf:langString` literals (e.g. `"Lion's Arch"@en`, `"Leivas"@en`), which are disjoint from `xsd:string` in OWL 2 DL.
   * Documented in `docs/baseline/known_failures.txt`.
2. **Authoring Studio Round-Trip Serialization**:
   * `packages/catalog` in `leurn-app-ontology-tool` dropped 569 triples out of 881 on `priory_core.ttl`, stripped all `rdfs:comment` and `skos:altLabel` annotations, erased all language tags (`@en`), and regenerated blank nodes.

### 1.3 What Could Not Be Run and Why
* **ROBOT CLI (`robot.jar`)**: Not installed on the local system (`which robot` returned not found). Owlready2 with HermiT 1.4.3 was used as the reference OWL 2 DL reasoner instead.

---

## 2. Integrity & Zero-Semantic-Change Confirmation

* **Zero Changes to Ontologies or Vocabularies:** `git diff feat/catalog-v0.1 -- ontology/` and `git diff feat/catalog-v0.1 -- vocab/` show **0 changed files and 0 diff lines**. No `.ttl` files in `ontology/` or `vocab/` were modified.
* **No Secrets Committed:** Verified that no GW2 API keys, user tokens, or private credentials were copied or introduced into any new or changed file.
* **Sensitive Data in Pre-Existing Files Reported:** Detailed in `docs/baseline/HYGIENE.md`:
  * `docs/research/api_model_discrepancy_audit.md` (lines 6–7) contains a real GW2 API key token, Account ID GUID, and username `Xenext.3106`. Recommended for sanitization before public exposure.

---

## 3. Menu of Hands-On Tasks for the Human Ontologist

Ordered by strategic ontological value:

### Task 1: Resolve the `LedgerToken` vs `Item` Disjointness Conflict
* **Estimated Size:** < 1 hour
* **Context:** `priory:LedgerToken owl:disjointWith priory:Item` (`priory_core.ttl:166`). In BFO terms, is a containerized item (e.g. Mystic Coin, Ectoplasm) an independent continuant playing an ingredient/token role, or is it an information entity?
* **Options for Human:**
  1. Remove `priory:LedgerToken owl:disjointWith priory:Item`.
  2. Model `ContainerizedToken` as a `BFO_0000023` (Role) played by an `Item` rather than a subclass of `LedgerToken` (an information content entity).
  3. Remove `priory:Item` rdf:type assertions from `clover_sources.ttl` and `common_material_refinements.ttl`.
* **Verification Check:** Run HermiT reasoner on `clover_sources.ttl` + `priory_core.ttl`. Must report `is consistent`.

### Task 2: Fix Datatype Range Violations on `zoneLevel` and String Annotations
* **Estimated Size:** < 1 hour
* **Context:** `zoneLevel` range is `xsd:integer` (`priory_core.ttl:275`), but values are `"1-80"`. Properties with `rdfs:range xsd:string` reject `@en` literals.
* **Options for Human:**
  1. Change `priory:zoneLevel` range to `xsd:string`, or introduce `priory:minZoneLevel` / `priory:maxZoneLevel` as integers.
  2. Change `rdfs:range xsd:string` on `vendorNPC` and `zoneName` to `rdf:langString` or `rdfs:Literal`.
* **Verification Check:** `python3 -c "import subprocess... CommandLine -k file://..."` passes on `core_exploration.ttl` and `dungeon_tokens.ttl`.

### Task 3: Ground Unparented Domain Classes in BFO 2020 / IAO
* **Estimated Size:** A few hours
* **Context:** As documented in `docs/baseline/AXIOM_AUDIT.md` and `docs/baseline/BFO_ALIGNMENT_NOTES.md`, 18 classes (including `priory:Recipe`, `priory:AcquisitionPath`, `priory:IngredientRequirement`) lack parentage in BFO.
* **Options for Human:**
  1. Classify `Recipe` under `iao:IAO_0000030` (Information Content Entity) or `IAO_0000104` (Plan Specification) rather than describing it as a process.
  2. Ground `AcquisitionPath` under `IAO_0000104` (Plan Specification) or `bfo:BFO_0000016` (Disposition).
  3. Ground `IngredientRequirement` under `bfo:BFO_0000020` (Specifically Dependent Continuant) or IAO information item.
* **Verification Check:** Re-run `docs/baseline/AXIOM_AUDIT.md` script; missing BFO ancestor count drops to 0.

### Task 4: Migrate Top Python Rules into Declarative Semantics
* **Estimated Size:** 1 day
* **Context:** `docs/baseline/LOGIC_LOCATION_MAP.md` extracted 10 prime candidates where Python `if-else` branching encodes domain knowledge.
* **Options for Human:**
  1. Candidate 1: Express Legendary Prerequisites as OWL class restrictions on `LegendaryItem` or SHACL constraints.
  2. Candidate 2: Write a SPARQL CONSTRUCT query for container unpackability inference (`AccountState` conditionally owning contents).
  3. Candidate 7: Attach daily priority weights directly to `AcquisitionPath` RDF individuals in `priory_core.ttl` or instance graphs.
* **Verification Check:** Run `make test` and verify solvers produce identical itineraries using graph queries.

### Task 5: Expand Competency Question Suite
* **Estimated Size:** A few hours
* **Context:** The scaffold in `docs/competency_questions/` has 5 seed questions.
* **Options for Human:** Author CQ06–CQ25 covering multi-discipline crafting handoffs, milestone vendor requirements, and regional material trees.
* **Verification Check:** `pytest tests/test_competency_questions.py -v` executes all new `.rq` files against their `.expected.json`.

---

## 4. Open Questions & Architectural Risks for the Human Ontologist

1. **Upper Ontology Commitment (BFO vs Pragmatism):**
   * Is strict BFO realism (disjoint continuants vs occurrents, pure material realism) practical for a virtual MMORPG inventory where "items" simultaneously behave as physical objects, currency balances, unlock flags, and database primary keys?
   * *Risk:* Imposing strict BFO disjointness axioms without clear role reification will cause recurring HermiT inconsistency across automated ingestion.
2. **Authoring Tool Strategy (`leurn-app-ontology-tool` vs Protégé):**
   * The custom TypeScript authoring tool cannot be trusted to serialize `.ttl` files in its current state (drops comments and annotations).
   * *Risk:* If an ontologist edits `priory_core.ttl` in the studio and hits Save, the repository's rich documentation and SKOS definitions will be permanently erased.
   * *Action:* Keep using Protégé or VS Code until the `@leurn/catalog` serializer is rewritten.
3. **Repository Hygiene & Untracking:**
   * Should `run_command.txt` and `scratch_check_bank.py` be removed from Git tracking (`git rm --cached`)?
   * Should `data/cache/api_items.json` (1.18 MB) be migrated to Git LFS or generated on demand?
