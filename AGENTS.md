# Agent Rules & Contribution Guidelines

This repository hosts **Project Priory (gw2-priory-def)**, a neuro-symbolic semantic layer and knowledge-guided reasoning system for *Guild Wars 2*.

All AI agents and contributors working on this repository must adhere to the following rules:

---

## 1. Change Tracking & Documentation
* **Maintain the Changelog:** Every feature, architectural change, bug fix, or data ingestion update must be recorded in [`CHANGELOG.md`](file:///Users/clementd/Documents/GitHub/gw2-priory-def/CHANGELOG.md) following the [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) standard.
* **Keep `README.md` Updated:** When introducing new modules, ontology namespaces, or CLI/API tools, update [`README.md`](file:///Users/clementd/Documents/GitHub/gw2-priory-def/README.md) with relevant usage instructions and architectural diagrams.
* **Document Ontology Decisions:** Any additions or modifications to the OWL ontology, SKOS concept schemes, or SHACL shape definitions must be accompanied by inline comments and commit notes explaining the domain rationale.

---

## 2. Semantic Web & Modeling Standards
* **Ontology Layer (TBox):** Use **OWL 2 DL** for formal schema definitions (Classes, Object/Data Properties, Domain/Range restrictions, Transitivity, Inverse properties).
* **Taxonomy & Concept Schemes:** Use **SKOS** (`skos:ConceptScheme`, `skos:Concept`, `skos:broader`, `skos:narrower`, `skos:prefLabel`) for controlled vocabularies (e.g. item rarities, weapon types, crafting disciplines, game modes).
* **Instance Layer (ABox):** Represent game entities (specific items, recipes, vendor exchanges) as RDF graph individuals (`owl:NamedIndividual`) typed by OWL classes and classified by SKOS concepts.
* **Integrity & Validation:** Enforce data constraints using **SHACL** (Shapes Constraint Language) before committing triples to the knowledge graph.
* **Determinism First:** Ground all mathematical counts, recipe dependencies, acquisition paths, and player inventory balances in verified graph logic before passing data to LLM layers.

---

## 3. Code Quality & Modularity
* Keep modules cleanly separated:
  * `ontology/`: OWL schemas, SKOS taxonomies, SHACL shapes.
  * `ingestion/`: GW2 REST API clients, Semantic MediaWiki scrapers/parsers.
  * `engine/`: Triple store management, SPARQL queries, graph solvers, and account diff calculator.
  * `agent/`: LLM prompt orchestration, intent parsing, neuro-symbolic sandwich pipelines.
* Ensure type safety with Pydantic / TypedDicts where appropriate.
