# Project Priory (GW2 Semantic Layer & Neuro-Symbolic Engine)

**Project Priory** is a semantic intelligence layer and personalized reasoning engine for *Guild Wars 2*.

By combining formal Semantic Web standards (**OWL 2 DL**, **SKOS**, **SHACL**, **SPARQL**) with live player account data (**GW2 REST API**) and deep game domain knowledge (**GW2 Semantic MediaWiki**), Priory powers a **neuro-symbolic sandwich architecture** that allows players to receive mathematically verified, highly personalized in-game itineraries and progression guidance.

---

## 📚 Complete Technical Documentation Suite

For exhaustive technical breakdowns, data dictionaries, and sequence traces, see the [`docs/`](./docs/) directory:

* [🏛️ **System Architecture Overview**](./docs/architecture_overview.md) — The Neuro-Symbolic Sandwich, component topology, and execution model.
* [🔍 **The Three Semantic Layers Deep Dive**](./docs/semantic_layers_deep_dive.md) — Exhaustive analysis of `ref` (SKOS), `def` (OWL/SHACL/ABox), and the Triple Store graph engine with comprehensive Mermaid diagrams.
* [⚡ **End-to-End Data Flow & Reasoning Trace**](./docs/data_flow_and_reasoning.md) — Step-by-step trace of a live query with concrete JSON payloads and sequence diagrams.
* [📖 **Ontology & Vocabulary Reference Guide**](./docs/ontology_and_vocab_reference.md) — Formal catalog of all OWL Classes, Properties, SKOS Concept Schemes, and SHACL Shapes.

---

## 🏛️ Core Vision & Architecture

```
                                  [ Player Query + GW2 API Key ]
                                                │
                                                ▼
                         ┌─────────────────────────────────────────────┐
                         │      Top LLM: Intent & Constraint Parser    │
                         │  (Extracts goals, time budget, preferences) │
                         └──────────────────────┬──────────────────────┘
                                                │ Structured Query
                                                ▼
      ┌─────────────────────────────────────────────────────────────────────────────────┐
      │                      SYMBOLIC ENGINE & SEMANTIC LAYER                           │
      │                                                                                 │
      │  ┌───────────────────────┐  ┌───────────────────────┐  ┌─────────────────────┐  │
      │  │  GW2 Official API     │  │  GW2 Semantic Wiki    │  │  OWL/SKOS Ontology  │  │
      │  │  (Items, TP, Account) │  │  (Mystic Forge, Drops)│  │  (TBox & Concepts)  │  │
      │  └───────────┬───────────┘  └───────────┬───────────┘  └──────────┬──────────┘  │
      │              └─────────────────┐        │        ┌────────────────┘             │
      │                                ▼        ▼        ▼                              │
      │                     ┌────────────────────────────────────────┐                  │
      │                     │     Knowledge Graph / Triple Store     │                  │
      │                     │        (PyOxigraph / RDFLib)           │                  │
      │                     └───────────────────┬────────────────────┘                  │
      │                                         │                                       │
      │                                         ▼                                       │
      │                     ┌────────────────────────────────────────┐                  │
      │                     │  Account Graph Delta & Pathfinding     │                  │
      │                     │  (Prunes owned items, resolves routes) │                  │
      │                     └───────────────────┬────────────────────┘                  │
      │                                         │                                       │
      │                                         ▼                                       │
      │                     ┌────────────────────────────────────────┐                  │
      │                     │   Spatial & Waypoint Navigation Engine │                  │
      │                     │   (Injects NPCs, zones & [&ChatCodes]) │                  │
      │                     └───────────────────┬────────────────────┘                  │
      └─────────────────────────────────────────┼───────────────────────────────────────┘
                                                │ Verified Deterministic Plan
                                                ▼
                         ┌─────────────────────────────────────────────┐
                         │   Bottom LLM: Contextual Synthesis & Guide  │
                         │   (Explains trade-offs, chat codes, tips)   │
                         └──────────────────────┬──────────────────────┘
                                                │
                                                ▼
                                [ Actionable Daily Progression Plan ]
```

---

## 🧩 Semantic Web Modeling Strategy

| Component | Standard | Purpose in Project Priory |
| :--- | :--- | :--- |
| **TBox (Ontology Schema)** | **OWL 2 DL** | Defines formal relations, classes (`Item`, `LegendaryWeapon`, `Recipe`, `AcquisitionPath`, `TimeGate`), object properties (`requiresIngredient`, `hasSubstituteSource`), cardinalities, and logical axioms. |
| **Controlled Vocabularies** | **SKOS** | Hierarchical concept schemes (`skos:ConceptScheme`, `skos:broader`, `skos:notation`) for game taxonomies: Item Rarities, Disciplines, Weapon Types, Currencies, Game Modes. |
| **ABox (Instance Data)** | **RDF / OWL Individuals** | Specific game items (e.g. *Twilight*, *Dusk*, *Legendary Sigil*), recipe DAG nodes, vendor exchanges, and live player inventory triples. |
| **Integrity & Constraints** | **W3C SHACL** | Enforces closed-world validation shapes before merging triples into the graph (e.g. discipline rating bounds, mandatory labels, output cardinalities). |
| **Dynamic Delta Engine** | **SPARQL 1.1 + Python Math** | Computes the recursive inventory difference ($N \ge 1$ multiplier), resolves wallet currencies, and detects the **Legendary Armory**. |

---

## 🚀 Quick Start: Running the Interactive Copilot

### 1. Prerequisites & Environment
Ensure Python 3.10+ is installed. Clone both repositories:
```bash
git clone https://github.com/cdcc-jpg/gw2-priory-def.git
git clone https://github.com/cdcc-jpg/gw2-priory-ref.git
```

Set up your `.env` file (see `.env.example`):
```bash
GW2_API_KEY="YOUR-ARENANET-API-KEY"
GEMINI_API_KEY="YOUR-GOOGLE-GEMINI-KEY"
```

### 2. Run the Live Interactive CLI
```bash
# Interactive multi-turn conversation mode:
python3 priory_cli.py

# Or one-shot query:
python3 priory_cli.py "I want to craft 2 legendary sigils tonight. I have 90 mins."
```

### 3. Run the Lightweight Web GUI (Developer Explorer)
> [!NOTE]
> **Architectural Decision:** This lightweight Flask interface (`web/app.py`, `run_web.py`) serves as a temporary developer GUI and conversational playground for the neuro-symbolic semantic layer before full integration into the main *gw2priory* frontend website.

```bash
python3 run_web.py
# Open your browser at http://127.0.0.1:5001
```

### 4. Run the Automated Test Suite
```bash
python3 -m unittest discover tests
```

---

## 📂 Repository Structure

```
gw2-priory-def/
├── docs/                        # Complete technical documentation suite
│   ├── README.md                # Documentation Table of Contents
│   ├── architecture_overview.md # Neuro-Symbolic Sandwich & component topology
│   ├── semantic_layers_deep_dive.md # Detailed ref, def & Triple Store deep dive
│   ├── data_flow_and_reasoning.md   # Step-by-step query lifecycle trace
│   └── ontology_and_vocab_reference.md # Complete data dictionary
├── ontology/                    # OWL 2 DL Schemas, SHACL Shapes & Instances
│   ├── priory_core.ttl          # Core OWL 2 DL schema (TBox)
│   ├── priory_shacl.ttl         # SHACL validation shapes
│   ├── instances/               # Verified RDF item instance graphs (ABox)
│   │   ├── twilight_gen1.ttl    # Twilight Gen 1 Legendary Greatsword DAG
│   │   └── legendary_sigil.ttl  # Legendary Sigil Mystic Forge DAG
│   └── vocab/                   # Local copy of SKOS taxonomies (from gw2-priory-ref)
├── engine/                      # Graph Store & Deterministic Reasoning
│   ├── graph_store.py           # In-memory RDF graph store loader
│   ├── semantic_query.py        # SPARQL 1.1 query & concept resolution service
│   ├── account_diff.py          # Dynamic overlay & inventory delta math
│   └── path_solver.py           # Multi-criteria optimization & knapsack scheduler
├── agent/                       # Neuro-Symbolic AI Agent Layer
│   ├── llm_client.py            # Plug-and-play LLM client (Gemini, Ollama, Mock)
│   ├── intent_parser.py         # Top LLM: Natural Language intent parsing
│   ├── guide_generator.py       # Bottom LLM: Grounded guide synthesis & waypoints
│   └── orchestrator.py          # Central Sandwich orchestrator & multi-turn session
├── ingestion/                   # Data Ingestion Bridges
│   ├── gw2_api.py               # Official ArenaNet REST API Client (v2)
│   └── smw_client.py            # Complete 7-archetype Semantic MediaWiki crawler
├── web/                         # Lightweight Developer Web GUI (Flask)
│   ├── app.py                   # Flask server & REST API
│   ├── templates/index.html     # Semantic GUI template
│   └── static/                  # Vanilla CSS & JS controller
├── tests/                       # Automated Unit Test Suites (40 tests)
├── run_web.py                   # Web GUI runner script
├── priory_cli.py                # Interactive CLI runner
├── CHANGELOG.md                 # Project version changelog
└── README.md                    # Project overview
```
