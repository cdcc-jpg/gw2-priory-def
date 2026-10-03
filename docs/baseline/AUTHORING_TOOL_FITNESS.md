# Authoring Tool Fitness Check: `leurn-app-ontology-tool`

**Target Repository:** `/Users/clementd/Documents/GitHub/leurn-app-ontology-tool`  
**Target Branch:** `chore/fitness-check` (created from `main`)  
**Auditor:** Project Priory Lead Architect & Fitness Evaluator  
**Date:** October 3, 2026  
**Evaluation Scope:** Assessment of whether `leurn-app-ontology-tool` can safely serve as a human authoring studio to edit `priory_core.ttl` by hand instead of Protégé.

---

## 1. Build & Test Baseline

* **`node_modules` Status:** Verified present and up to date (`packages/` and `apps/` dependencies resolved via root `package-lock.json`).
* **`npm run typecheck`:** **PASS** (0 TypeScript compilation errors across all 8 workspaces: `@leurn/core`, `@leurn/reasoner`, `@leurn/catalog`, `@leurn/sparql`, `@leurn/linter`, `@leurn/tradecraft`, `apps/studio`, `apps/extension`).
* **`npm test`:** **PASS** (96 passed, 0 failed, 0 skipped across 22 test suites).
* **Package Breakdown:**
  * `@leurn/core`: 28 tests passed (Manchester syntax, AST, IRI management, cascade rename).
  * `@leurn/reasoner`: 24 tests passed (Tableau/taxonomic classification, unsatisfiability detection).
  * `@leurn/catalog`: 16 tests passed (Turtle/RDF-XML parsing and serialization).
  * `@leurn/sparql`: 14 tests passed (In-memory triple store, Basic Graph Patterns, filters).
  * `@leurn/linter`: 14 tests passed (Structural integrity rules).
* **AGENT_HANDOVER.md & CHANGELOG.md Analysis:**
  * Handover documents indicate rapid alpha development with focus on visual canvas rendering (`apps/studio`).
  * Known defects recorded in changelog: canvas node ungrab bug (v0.3.1-alpha), class expression autocomplete race condition (v0.2.0-alpha).
  * Critical architectural note: Parsers and serializers in `@leurn/catalog` are custom hand-rolled implementations rather than industry-standard RDF engines (e.g. `N3.js` or `rdflib.js`).

---

## 2. Round-Trip Safety (Fidelity & Serialization)

To test whether the tool can safely open, edit, and save Priory files without data loss or corruption, test scripts were executed under `tools/fitness/roundtrip_runner.js` and compared using Python `rdflib.compare.isomorphic` and `graph_diff`:

* **Target File:** `ontology/priory_core.ttl` (Original: 881 triples)
* **Serialized Output:** 575 triples
* **Isomorphic Graph Test:** **FAILED (`Isomorphic: False`)**
* **Triples Lost (in original, missing in serialized):** **569 triples**
* **Triples Added (in serialized, missing in original):** **263 triples**

### Forensic Breakdown of Round-Trip Damage:
1. **Annotation Stripping:**
   * `rdfs:comment`: **100% LOST**. Every explanatory comment and documentation block in `priory_core.ttl` was silently dropped by `@leurn/catalog/src/turtleParser.ts`.
   * `skos:altLabel`, `skos:definition`, `skos:prefLabel`: **100% LOST**.
2. **Language Tag Deletion:**
   * All language tags (e.g., `"Game Item"@en`, `"Recipe"@en`) were completely stripped, converting localized literals into plain datatyped literals or unadorned strings.
3. **Prefix Mangling & Reordering:**
   * Serializer discarded original prefixes and injected unwanted fallback prefixes (`obo:`, `ro:`, `:`).
4. **Blank Node & List Regeneration:**
   * Anonymous blank nodes and `owl:unionOf` rdf:rest/rdf:first list structures were reconstructed with non-deterministic internal identifiers.
5. **Ordering & Formatting:**
   * Original comments, section banners (`# --- Materials, Gifts, Currencies ---`), and logical grouping were erased.

> [!CAUTION]
> **ROUND-TRIP SAFETY VERDICT: BROKEN / DANGEROUS**  
> `leurn-app-ontology-tool` CANNOT be used to save changes to `priory_core.ttl` or any other `.ttl` file in Project Priory. Saving through this tool destroys more than 60% of semantic annotations and comments.

---

## 3. Reasoner Cross-Check (HermiT vs `@leurn/reasoner`)

The tool's internal TypeScript reasoner was benchmarked against the reference OWL 2 DL reasoner (HermiT 1.4.3 via Owlready2) using `priory_core.ttl` and a synthetic test ontology (`docs/baseline/fitness/synthetic.ttl`).

### 3.1 Benchmark Results Table

| OWL Construct / Test Feature | HermiT (Reference) | `@leurn/reasoner` | Agreement | Notes on Tool Reasoner |
| :--- | :--- | :--- | :--- | :--- |
| **Taxonomic Subsumption (`subClassOf`)** | Consistent; full hierarchy | Consistent; inferred 170 subsumptions | **AGREE** | Fast in-memory transitive closure. |
| **Unsatisfiability (`owl:Nothing`)** | Flags `CatDog` as unsatisfiable | Flags `CatDog` as unsatisfiable | **AGREE** | Detects direct `owl:disjointWith` clashes. |
| **`owl:equivalentClass` with `owl:Restriction`** | Full classification | Partial | **PARTIAL** | Only handles simple existential restrictions. |
| **`owl:someValuesFrom`** | Inferred | Inferred | **AGREE** | Handled when restricted to named classes. |
| **`owl:allValuesFrom`** | Full classification | Ignored / Incomplete | **DISAGREE** | Universal quantification is skipped. |
| **Cardinality (`minCardinality`, `maxCardinality`)** | Validated | Unsupported | **DISAGREE** | Silently ignored. |
| **`owl:propertyChainAxiom`** | Inferred | Unsupported | **DISAGREE** | Complex property chains not evaluated. |
| **`owl:TransitiveProperty`** | Inferred | Handled for `subClassOf` only | **PARTIAL** | Arbitrary transitive object properties skipped. |
| **`owl:inverseOf`** | Bidirectional inference | Partial | **PARTIAL** | Object property invertibility partially traced. |
| **`owl:FunctionalProperty`** | Enforced | Unsupported | **DISAGREE** | Does not infer equality between individuals. |
| **Datatype Lexical Range Checking** | Strict (detects `1-80` for `xsd:integer`) | None | **DISAGREE** | Literal values are not validated against XSD. |

### 3.2 Implemented OWL Profile
* `@leurn/reasoner` implements an **ad-hoc EL-like fragment** of OWL 2 with simple propositional disjointness. It is NOT a complete OWL 2 DL reasoner and lacks tableau-based model generation.

---

## 4. Scale & Performance Benchmark

Performance was measured using `tools/fitness/scale_test.js`:

| Target Dataset | Size / Triples | Load & Parse Time | Classification Time | SPARQL Query Time |
| :--- | :--- | :--- | :--- | :--- |
| `priory_core.ttl` | 40.8 KB / 881 triples | **6.17 ms** | **1.80 ms** | **5.14 ms** |
| `competitive_armor_and_eternity_recipes.ttl` | 85.5 KB / 2,144 triples | **7.24 ms** | **0.81 ms** | **6.80 ms** |
| Full Merged Priory Graph (Synthetic Proxy) | 1.95 MB / ~20,000 triples | **148.5 ms** | **38.2 ms** | **112.0 ms** |

* **Scalability Verdict:** In-memory performance for graph structures up to 20,000 triples is fast (<150ms). No memory leaks, crashes, or execution timeouts occurred during classification.

---

## 5. SPARQL Engine Check (`@leurn/sparql`)

The five seed competency questions from Task C were evaluated against `@leurn/sparql`:

1. **CQ01 (`(priory:acquiredVia|priory:hasSubstituteSource)` Property Path):**
   * Result: **FAILED / EMPTY**
   * Cause: Property path union syntax `(path1|path2)` is unsupported by the query planner.
2. **CQ02 (Direct Forge Ingredients with `priory:hasIngredientRequirement`):**
   * Result: **PASSED** (BGP matching and variable bindings work for standard triple patterns).
3. **CQ03 (Astral Acclaim Vendor Exchange):**
   * Result: **PASSED** (BGP and literal filters work).
4. **CQ04 (Crafting Disciplines with `skos:prefLabel` & `skos:notation`):**
   * Result: **PARTIAL** (`FILTER (lang(?label) = 'en')` is unsupported; returns all un-filtered tags).
5. **CQ05 (Legendary Armory Saturation Caps):**
   * Result: **PASSED** (`ORDER BY` works).

---

## 6. Authoring Workflow Evaluation (10 Essential Modeller Workflows)

| # | Modeller Workflow | Verdict | Evidence & File Citations |
| :-: | :--- | :--- | :--- |
| **1** | **Add class with Manchester restriction** | **PARTIAL** | AST parser handles syntax, but silent `catch` blocks in `@leurn/core/src/manchester.ts:1125,1160,1193` swallow invalid syntax. |
| **2** | **Rename IRI with cascading reference updates** | **WORKS** | `packages/core/src/ontology.ts:renameEntity()` updates all references across axioms and restrictions in memory. |
| **3** | **Run reasoner & view consistency status** | **WORKS** | `packages/reasoner/src/index.ts:classify()` executes within 2ms and flags inconsistent classes like `CatDog`. |
| **4** | **View inference explanation / justification** | **PARTIAL** | Simple single-step subsumption explanations work; multi-step restrictions and property chain proofs are unsupported. |
| **5** | **Undo / Redo edits** | **WORKS** | Studio frontend history stack (`apps/studio/src/store/history.ts`) captures reversible action diffs. |
| **6** | **Save without reformatting the file** | **BROKEN** | Serializer drops 569 triples on `priory_core.ttl`, erases all comments and language tags. |
| **7** | **Add object property with domain and range** | **WORKS** | Supported in TBox data structure; correctly serializes property signatures. |
| **8** | **Edit SKOS concept schemes and taxonomy** | **BROKEN** | Serializer strips SKOS annotations (`skos:altLabel`, `skos:definition`, language tags). |
| **9** | **Import / Export standard OWL Turtle** | **BROKEN** | Non-isomorphic round-trip due to hand-rolled parsing logic. |
| **10** | **Live syntax validation & error highlighting** | **PARTIAL** | Basic AST error catching works, but silent fallback to string names masks expression syntax errors. |

---

## 7. Code Quality & Architectural Risk Review

A code review of `packages/core`, `packages/reasoner`, and `packages/catalog` surfaced three architectural risks:

1. **Hand-Rolled Parsers (`packages/catalog/src/turtleParser.ts`, `rdfXmlParser.ts`):**
   * Instead of utilizing an authoritative, specification-compliant RDF parser (such as `N3.js`), the package relies on custom string tokenizers and regexes.
   * This is the direct root cause of all dropped comments, lost annotations, and stripped `@en` language tags.
2. **Silent Exception Catch Blocks (`packages/core/src/manchester.ts`):**
   * Line 1125: `catch (e) { /* Fallback */ }`
   * Line 1160: `catch (e) { /* ignore */ }`
   * Line 1193: `catch (e) { /* If it fails to parse as expression, treat as name */ }`
   * This design masks syntax errors from the user; a typo in a Manchester restriction silently degrades into a plain named entity rather than reporting a parse error.
3. **Unimplemented SPARQL Features (`packages/sparql/src/engine.ts`):**
   * Property paths (`|`, `/`, `*`), `UNION` blocks, and SPARQL language filter functions (`langMatches`) are partially implemented or stubbed.

---

## 8. Definitive Handoff Verdict

> [!IMPORTANT]
> ### Safe to Use For:
> * **Interactive Visual Exploration:** Browsing existing class taxonomies, inspecting class hierarchies, and viewing graph connections visually in the studio interface.
> * **Isolated Experimentation:** Authoring small, isolated scratch ontologies that do not require comment preservation or standard metadata retention.
> * **Rapid In-Memory Subsumption Checking:** Fast local sanity checking of basic class subsumption and direct disjointness.
>
> ### NOT Safe to Use For:
> * **Editing Production Priory Ontologies:** **UNDER NO CIRCUMSTANCES should this tool be used to save edits directly to `priory_core.ttl`, `character.ttl`, shapes, or reference vocabularies.**
> * Doing so will permanently strip comments, erase SKOS definitions, delete language tags, and mangle prefix headers.
> * **Recommendation:** The human ontologist should continue using Protégé or a standard text editor (VS Code with Turtle/OWL extensions) for direct file authoring until the `@leurn/catalog` parser and serializer are replaced with `N3.js` or `rdflib`.
