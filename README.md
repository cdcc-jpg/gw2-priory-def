# Project Priory (GW2 Semantic Layer & Neuro-Symbolic Engine)

**Project Priory** is a semantic intelligence layer and personalized reasoning engine for *Guild Wars 2*.

By combining formal Semantic Web standards (**OWL 2 DL**, **SKOS**, **SHACL**, **SPARQL**) with live player account data (**GW2 REST API**) and deep game domain knowledge (**GW2 Semantic MediaWiki**), Priory powers a **neuro-symbolic sandwich architecture** that allows players to receive mathematically verified, highly personalized in-game itineraries and progression guidance.

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
| **Controlled Vocabularies** | **SKOS** | Hierarchical concept schemes (`skos:ConceptScheme`, `skos:broader`) for game taxonomies: Item Rarities, Disciplines, Weapon Types, Game Modes, Expansions. |
| **ABox (Instance Data)** | **RDF / OWL Individuals** | Specific game items (e.g. *Twilight*, *Dusk*, *Mystic Clover*), recipe nodes, vendor exchanges, and live player inventory triples. |
| **Validation Layer** | **SHACL** | Validates ingested data integrity (ensures recipe counts are non-zero, prerequisites are linked, IDs are consistent). |
| **Query & Path Engine** | **SPARQL & NetworkX** | Executes graph pattern matching and topological/DAG traversal for dependency trees. |

---

## 🚀 Scope: Legendary Weapon Crafting (MVP)

The initial focus is the complete dependency and acquisition graph for **Legendary Weapons** (starting with Generation 1 weapons like *Twilight*, *Sunrise*, and *Bolt*), covering:
1. **Precursor Acquisition:** Crafting collection journey vs. Trading Post purchase vs. drop probability.
2. **Mystic Tribute / Gift of Fortune:** T6 material conversion, Mystic Clover sources (Mystic Forge, WvW reward tracks, Wizard's Vault, Fractal vendors).
3. **Gift of Mastery:** World Map Completion, WvW *Gift of Battle*, Spirit Shards, Karma / Obsidian Shards.
4. **Specific Weapon Gifts:** Dungeon currencies / *Tales of Dungeon Delving*, crafting discipline prerequisites (Weaponsmith 400/500, etc.).

---

## 🛠️ Technology Stack

* **Language:** Python 3.11+
* **Semantic Web & Graph:** `rdflib`, `pyoxigraph` (embedded high-performance SPARQL engine), `pyshacl`, `owlrl`
* **Graph Algorithms & DAGs:** `networkx`
* **API & Ingestion:** `httpx` (async client for GW2 REST API & MediaWiki API), `pydantic`
* **AI & LLM Orchestration:** `google-genai` / LiteLLM / Instructor with structured JSON outputs.

---

## 📂 Repository Structure

```
gw2-priory-def/
├── ontology/                 # OWL schemas, SKOS vocabularies, SHACL shapes
│   ├── priory_core.ttl       # OWL 2 DL Core schema
│   ├── priory_skos.ttl       # SKOS taxonomies & concept schemes
│   └── priory_shacl.ttl      # SHACL validation shapes
├── ingestion/                # Ingestion pipelines for GW2 API & Wiki SMW
│   ├── gw2_api.py            # Official REST API client
│   └── smw_client.py         # GW2 Wiki Semantic MediaWiki scraper/parser
├── engine/                   # Symbolic engine, triple store, graph solver
│   ├── graph_store.py        # Oxigraph / RDFLib SPARQL graph store
│   ├── account_diff.py       # Player inventory/progress delta engine
│   └── path_solver.py        # Multi-criteria optimization & DAG traversal
├── agent/                    # Neuro-symbolic LLM orchestration
│   ├── intent_parser.py      # Top LLM: natural language -> structured query
│   └── guide_generator.py    # Bottom LLM: deterministic plan -> user guide
├── tests/                    # Unit and integration tests
├── AGENTS.md                 # Agent and contribution rules
├── CHANGELOG.md              # Project changelog
└── README.md                 # Project documentation
```
