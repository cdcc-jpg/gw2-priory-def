# Changelog

All notable changes to **Project Priory (gw2-priory-def)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Phase 1 Bulk Catalog Ingestion:** Successfully crawled and ingested **all 56 official Legendary items** (Weapons, Armor, Trinkets, Backpacks, Sigils, Runes, and Relics) into partitioned instance graph [`ontology/instances/legendaries/all_legendary_items.ttl`](./ontology/instances/legendaries/all_legendary_items.ttl) with 100% SHACL validation pass.
- **Reference Taxonomies Expansion in `gw2-priory-ref`:**
  - Added [`vocab/armor_weights.ttl`](file:///Users/clementd/Documents/GitHub/gw2-priory-ref/vocab/armor_weights.ttl) defining `HeavyArmor`, `MediumArmor`, and `LightArmor` with SKOS concepts and definitions.
  - Added [`vocab/equipment_slots.ttl`](file:///Users/clementd/Documents/GitHub/gw2-priory-ref/vocab/equipment_slots.ttl) classifying all 16 armor and jewelry equipment slots.
  - Added [`vocab/item_types.ttl`](file:///Users/clementd/Documents/GitHub/gw2-priory-ref/vocab/item_types.ttl) mapping top-level ArenaNet API item type schemas.
- **Automated Catalog Ingestion CLI Runner:** Created [`scripts/ingest_catalog.py`](./scripts/ingest_catalog.py) to harvest, transform, and validate game entities from Semantic MediaWiki and the official REST API.
- **High-Speed 200-Item Chunking Client:** Enhanced [`ingestion/gw2_api.py`](./ingestion/gw2_api.py) with bulk batch chunking and local disk caching.
- **Polymorphic Multi-Discipline Recipe Selection:** Enhanced [`engine/account_diff.py`](./engine/account_diff.py) to dynamically prioritize recipe paths matching the player's active high-level crafting disciplines.
- **Schema & Naming Standardization:** Standardized `priory:requiredRating` across [`ontology/priory_core.ttl`](./ontology/priory_core.ttl) and [`ontology/priory_shacl.ttl`](./ontology/priory_shacl.ttl), and added equipment classes (`priory:Armor`, `priory:LegendaryArmor`, `priory:Trinket`, `priory:LegendaryTrinket`, `priory:LegendaryRelic`).
- Created complete technical documentation suite in [`docs/`](./docs/):
  - [`docs/README.md`](./docs/README.md): Documentation table of contents.
  - [`docs/architecture_overview.md`](./docs/architecture_overview.md): Comprehensive Neuro-Symbolic Sandwich architecture, topology, and comparison matrix.
  - [`docs/semantic_layers_deep_dive.md`](./docs/semantic_layers_deep_dive.md): Deep dive into Layer 1 (`ref`), Layer 2 (`def`), and Layer 3 (Triple Store & Delta Engine) with full Mermaid diagrams, N-ary relation patterns, and cross-layer execution traces.
  - [`docs/data_flow_and_reasoning.md`](./docs/data_flow_and_reasoning.md): Step-by-step query lifecycle trace with concrete JSON payloads and sequence diagrams.
  - [`docs/ontology_and_vocab_reference.md`](./docs/ontology_and_vocab_reference.md): Complete data dictionary of OWL Classes, Object/Data Properties, SKOS Concept Schemes, and SHACL Shapes.
- Created initial repository structure and agent rules in [`AGENTS.md`](./AGENTS.md).
- Initialized [`README.md`](./README.md) detailing project vision, neuro-symbolic architecture, and technology stack.
- Implemented core OWL 2 DL ontology schema in [`ontology/priory_core.ttl`](./ontology/priory_core.ttl) with N-ary relation patterns and RDF-star compatibility.
- Added Spatial & Navigation properties (`priory:vendorNPC`, `priory:zoneName`, `priory:waypointName`, `priory:nearestWaypoint`) to [`ontology/priory_core.ttl`](./ontology/priory_core.ttl).
- Added Upgrade Component classes (`priory:UpgradeComponent`, `priory:Sigil`, `priory:LegendarySigil`, `priory:Rune`, `priory:LegendaryRune`) to [`ontology/priory_core.ttl`](./ontology/priory_core.ttl).
- Added `UpgradeTypeScheme` in [`ontology/vocab/upgrade_types.ttl`](./ontology/vocab/upgrade_types.ttl) and comprehensive currency taxonomies in [`ontology/vocab/currencies.ttl`](./ontology/vocab/currencies.ttl).
- Created complete instance graph for **Legendary Sigil (ID: 91505)** in [`ontology/instances/legendary_sigil.ttl`](./ontology/instances/legendary_sigil.ttl) with Gift of Sigils (30 Clovers, 75 Mystic Motes, 750 Lucent Crystals, Symbols), Gift of Craftsmanship, Condensed Might, and Condensed Magic.
- Implemented SHACL validation shapes in [`ontology/priory_shacl.ttl`](./ontology/priory_shacl.ttl) for item properties, recipe cardinalities, discipline constraints, and vendor exchanges.
- Created seed Generation 1 Legendary Greatsword instance graph in [`ontology/instances/twilight_gen1.ttl`](./ontology/instances/twilight_gen1.ttl) with spatial waypoints for Miyani (`[&BBAEAAA=]`), Rojan (`[&BHsBAAA=]`), and Tactician Deathspark (`[&BO4CAAA=]`).
- Implemented in-memory graph store [`engine/graph_store.py`](./engine/graph_store.py) loading vocabularies, schemas, and instance graphs with SPARQL 1.1 querying.
- Implemented Dynamic Overlay & Account Delta Engine in [`engine/account_diff.py`](./engine/account_diff.py) with full support for target quantity scaling ($N \ge 1$), tree recipe discipline filtering, Legendary Armory detection, and automatic wallet currency resolution for vendor exchanges (e.g. Provisioner Tokens, Spirit Shards, Karma).
- Implemented Multi-Criteria Path & Constraint Solver in [`engine/path_solver.py`](./engine/path_solver.py) evaluating alternative Mystic Clover routes, precursor strategies, Provisioner Token routes, and gold valuations with `exhausted_sources` awareness.
- Implemented official GW2 API client in [`ingestion/gw2_api.py`](./ingestion/gw2_api.py) and complete 7-archetype Semantic MediaWiki client in [`ingestion/smw_client.py`](./ingestion/smw_client.py).
- Implemented Semantic Discovery & Concept Resolution Service in [`engine/semantic_query.py`](./engine/semantic_query.py) supporting taxonomic subsumption queries, polymorphic acquisition discovery, and chat code resolution with exact match prioritization and spatial waypoint extraction.
- Implemented plug-and-play LLM client interface in [`agent/llm_client.py`](./agent/llm_client.py) with live `GeminiLLMClient` (Google GenAI), `LocalOllamaClient`, and fallback `RuleBasedMockLLMClient`.
- Implemented Top LLM intent parser in [`agent/intent_parser.py`](./agent/intent_parser.py) extracting target quantity, playtime, game mode exclusions, exhausted sources, and budget with conversation context memory.
- Implemented Bottom LLM guide generator in [`agent/guide_generator.py`](./agent/guide_generator.py) synthesizing grounded, hallucination-free play session itineraries with turn-by-turn waypoint navigation.
- Implemented complete Neuro-Symbolic Sandwich pipeline orchestrator with stateful multi-turn `PrioryChatSession` in [`agent/orchestrator.py`](./agent/orchestrator.py).
- Added `.env.example` and `.gitignore` to securely handle local API credentials.
- Created live interactive multi-turn conversational CLI runner in [`priory_cli.py`](./priory_cli.py).
- Added comprehensive unit test suites in [`tests/test_ontology.py`](./tests/test_ontology.py), [`tests/test_engine.py`](./tests/test_engine.py), [`tests/test_semantic_query.py`](./tests/test_semantic_query.py), [`tests/test_agent.py`](./tests/test_agent.py), and [`tests/test_ingestion.py`](./tests/test_ingestion.py) with 100% pass rate (14 tests).
