# Changelog

All notable changes to **Project Priory (gw2-priory-def)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Created initial repository structure and agent rules in [`AGENTS.md`](./AGENTS.md).
- Initialized [`README.md`](./README.md) detailing project vision, neuro-symbolic architecture, and technology stack.
- Formulated technical design for the OWL 2 DL ontology, SKOS concept schemes, and GW2 API / Semantic MediaWiki ingestion pipeline.
- Implemented core OWL 2 DL ontology schema in [`ontology/priory_core.ttl`](./ontology/priory_core.ttl) with N-ary relation patterns and RDF-star compatibility.
- Added Spatial & Navigation properties (`priory:vendorNPC`, `priory:zoneName`, `priory:waypointName`, `priory:nearestWaypoint`) to [`ontology/priory_core.ttl`](./ontology/priory_core.ttl).
- Added Upgrade Component classes (`priory:UpgradeComponent`, `priory:Sigil`, `priory:LegendarySigil`, `priory:Rune`, `priory:LegendaryRune`) to [`ontology/priory_core.ttl`](./ontology/priory_core.ttl).
- Added `UpgradeTypeScheme` in [`ontology/vocab/upgrade_types.ttl`](./ontology/vocab/upgrade_types.ttl) and `currency:ProvisionerToken` in [`ontology/vocab/currencies.ttl`](./ontology/vocab/currencies.ttl).
- Created complete instance graph for **Legendary Sigil (ID: 91505)** in [`ontology/instances/legendary_sigil.ttl`](./ontology/instances/legendary_sigil.ttl) with Gift of Sigils, Gift of Craftsmanship, and Faction Provisioner waypoints (`[&BKgDAAA=]`).
- Implemented SHACL validation shapes in [`ontology/priory_shacl.ttl`](./ontology/priory_shacl.ttl) for item properties, recipe cardinalities, and discipline constraints.
- Created seed Generation 1 Legendary Greatsword instance graph in [`ontology/instances/twilight_gen1.ttl`](./ontology/instances/twilight_gen1.ttl) with spatial waypoints for Miyani (`[&BBAEAAA=]`), Rojan (`[&BHsBAAA=]`), and Tactician Deathspark (`[&BO4CAAA=]`).
- Implemented in-memory graph store [`engine/graph_store.py`](./engine/graph_store.py) loading vocabularies, schemas, and instance graphs with SPARQL 1.1 querying.
- Implemented Dynamic Overlay & Account Delta Engine in [`engine/account_diff.py`](./engine/account_diff.py) with full support for target quantity scaling ($N \ge 1$), tree recipe discipline filtering, and automatic wallet currency resolution for vendor exchanges (e.g. Provisioner Tokens, Spirit Shards, Karma).
- Implemented Multi-Criteria Path & Constraint Solver in [`engine/path_solver.py`](./engine/path_solver.py) evaluating alternative Mystic Clover routes, precursor strategies, Provisioner Token routes, and gold valuations with `exhausted_sources` awareness.
- Implemented official GW2 API client in [`ingestion/gw2_api.py`](./ingestion/gw2_api.py) and Semantic MediaWiki client in [`ingestion/smw_client.py`](./ingestion/smw_client.py).
- Implemented Semantic Discovery & Concept Resolution Service in [`engine/semantic_query.py`](./engine/semantic_query.py) supporting taxonomic subsumption queries, polymorphic acquisition discovery, and chat code resolution with exact match prioritization and spatial waypoint extraction.
- Implemented plug-and-play LLM client interface in [`agent/llm_client.py`](./agent/llm_client.py) with live `GeminiLLMClient` (Google GenAI), `LocalOllamaClient`, and fallback `RuleBasedMockLLMClient`.
- Implemented Top LLM intent parser in [`agent/intent_parser.py`](./agent/intent_parser.py) extracting target quantity, playtime, game mode exclusions, exhausted sources, and budget with conversation context memory.
- Implemented Bottom LLM guide generator in [`agent/guide_generator.py`](./agent/guide_generator.py) synthesizing grounded, hallucination-free play session itineraries with turn-by-turn waypoint navigation.
- Implemented complete Neuro-Symbolic Sandwich pipeline orchestrator with stateful multi-turn `PrioryChatSession` in [`agent/orchestrator.py`](./agent/orchestrator.py).
- Added `.env.example` and `.gitignore` to securely handle local API credentials.
- Created live interactive multi-turn conversational CLI runner in [`priory_cli.py`](./priory_cli.py).
- Added comprehensive unit test suites in [`tests/test_ontology.py`](./tests/test_ontology.py), [`tests/test_engine.py`](./tests/test_engine.py), [`tests/test_semantic_query.py`](./tests/test_semantic_query.py), and [`tests/test_agent.py`](./tests/test_agent.py) with 100% pass rate (12 tests).
