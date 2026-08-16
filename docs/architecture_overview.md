# System Architecture Overview

This document describes the high-level architecture of **Project Priory**, explaining how natural language understanding, deterministic knowledge graphs, live game API telemetry, and mathematical path optimization collaborate to guide players.

---

## 1. The Core Paradigm: The Neuro-Symbolic Sandwich

Traditional AI assistants hallucinate numbers, miscalculate recipes, and cannot inspect live game state. Procedural codebases (standard scripts) lack natural language flexibility and struggle with conversational reasoning.

Project Priory solves this using a **Neuro-Symbolic Sandwich**:

```mermaid
graph TD
    User(["👤 Player Prompt<br><i>'I want to craft 2 legendary sigils tonight. I have 90 mins.'</i>"])
    
    subgraph LayerTop ["1. Top Neural Layer (Intent & Entity Extraction)"]
        TopLLM["🧠 Top LLM (IntentParser)<br>• Cleans human slang/typos<br>• Extracts target, quantity, time budget, exclusions<br>• Normalizes text candidate: 'Legendary Sigil'"]
    end

    subgraph LayerMiddle ["2. Middle Symbolic Layer (Deterministic Graph & Math Engine)"]
        direction TB
        SPARQL["🔍 Semantic Resolution (SPARQL)<br>Resolves candidate string to canonical URI: item:91505"]
        
        GW2API["🌐 Official ArenaNet API (v2)<br>Fetches live snapshot: Bank, Materials, Wallet, Armory"]
        
        TripleStore["🏛️ Unified Triple Store (RDFLib / Oxigraph)<br>• Layer 1: ref (SKOS Taxonomies)<br>• Layer 2: def (OWL Schemas & Recipe DAGs)"]
        
        DeltaEngine["⚙️ Account Delta Engine<br>• Recursive DAG Traversal<br>• N-Quantity Multiplier: 2x Sigil = 60 Clovers<br>• Live Subtraction: 60 needed - 20 owned = 40 missing<br>• Wallet Check: 440 Tokens >= 100 needed (Satisfied!)"]
        
        PathSolver["📐 Path & Constraint Solver<br>• Lowest Cost Ranking (Vault @ 0g vs Forge @ 3.5g)<br>• Priority Knapsack Scheduler: 15m Reset + 75m Farm"]
        
        SPARQL --> TripleStore
        TripleStore --> DeltaEngine
        GW2API --> DeltaEngine
        DeltaEngine --> PathSolver
    end

    subgraph LayerBottom ["3. Bottom Neural Layer (Contextual Guide Generation)"]
        BottomLLM["💡 Bottom LLM (GuideGenerator)<br>• Formats verified math into in-game checklist<br>• Injects clickable waypoint chat codes: [&BKgDAAA=]<br>• Provides human coaching, tips, and motivation"]
    end

    User --> TopLLM
    TopLLM --> SPARQL
    PathSolver --> BottomLLM
    BottomLLM --> Result(["🎯 Personalized In-Game Action Plan<br><i>Turn-by-turn checklist with zero hallucinations</i>"])

    style LayerTop fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    style LayerMiddle fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    style LayerBottom fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
```

---

## 2. Why This Architecture Wins

| Aspect | Pure LLM (e.g. ChatGPT / Claude) | Standard Web Calculator (e.g. GW2Efficiency) | Project Priory (Neuro-Symbolic) |
| :--- | :--- | :--- | :--- |
| **Natural Language** | ✅ Fluid and conversational | ❌ None (rigid drop-down UI only) | ✅ **Fluid, multi-turn conversational chat** |
| **Recipe Accuracy** | ❌ Hallucinates fake recipes and quantities | ✅ 100% exact math | ✅ **100% exact math grounded in RDF graph** |
| **Live Account State** | ❌ Cannot check bank or armory | ✅ Reads live API | ✅ **Reads live API (materials, wallet, armory)** |
| **Personalized Routing** | ❌ Guesses arbitrary schedules | ❌ Fixed static tables (no time budgeting) | ✅ **Dynamic knapsack time-budget optimization** |
| **In-Game Navigation** | ❌ Frequently hallucinates wrong waypoints | ❌ Disconnected from current play session | ✅ **Verified in-game waypoint codes `[&...]`** |

---

## 3. High-Level Component Topology

```mermaid
flowchart LR
    subgraph RepoRef ["gw2-priory-ref (Repository)"]
        SKOS_Vocab["SKOS Concept Schemes<br>• Currencies (ID mappings)<br>• Weapon & Upgrade Types<br>• Crafting Disciplines<br>• Rarities & Game Modes"]
    end

    subgraph RepoDef ["gw2-priory-def (Repository)"]
        OWL_Schema["OWL 2 DL Ontology (priory_core.ttl)<br>Classes, Object/Data Properties, N-ary Relations"]
        SHACL_Shapes["SHACL Shapes (priory_shacl.ttl)<br>Closed-world structural validation rules"]
        RDF_Instances["Instance Graphs (ontology/instances/)<br>Twilight, Legendary Sigil, Recipes, Waypoints"]
        Engine["Core Engine (engine/)<br>• GraphStore (RDFLib)<br>• SemanticQueryService (SPARQL)<br>• AccountDiffEngine (Delta Math)<br>• PathSolver (Optimization)"]
        Agent["Agent Orchestration (agent/)<br>• IntentParser (Top LLM)<br>• GuideGenerator (Bottom LLM)<br>• PrioryChatSession (Multi-turn)"]
        Ingestion["Ingestion Bridges (ingestion/)<br>• GW2ApiClient (Official REST API)<br>• GW2SMWClient (Semantic MediaWiki)"]
    end

    SKOS_Vocab --> Engine
    OWL_Schema --> Engine
    SHACL_Shapes --> Engine
    RDF_Instances --> Engine
    Ingestion --> Engine
    Engine --> Agent
```

---

## 4. Summary of Subsystems

1. **The Reference Repository (`gw2-priory-ref`):** Provides the authoritative, immutable controlled vocabularies and taxonomies across all Guild Wars 2 systems.
2. **The Definition Repository (`gw2-priory-def`):** Implements the formal OWL 2 DL domain schema, SHACL constraints, item dependency graphs, graph algorithms, and AI orchestrators.
3. **The Ingestion Pipeline:** Queries the official ArenaNet REST API and the Semantic MediaWiki API, converting game data into validated RDF triples.
4. **The Agent Orchestrator:** Implements multi-turn stateful sessions, taking player goals and returning hallucination-free, waypoint-navigated game plans.
