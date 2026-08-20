# Project Priory: Neuro-Symbolic Architecture & Pipeline Interaction Reference

This document provides a comprehensive technical breakdown and visual graphs illustrating the end-to-end data flow, component interactions, and the precise roles of the **Semantic Web Layer (OWL 2 DL, SKOS, RDFLib, SPARQL)** in Project Priory.

---

## 1. High-Level Architecture Overview

Project Priory executes a **Neuro-Symbolic Sandwich** pattern that combines the natural language strengths of Large Language Models with the strict determinism and verifiable truth of Semantic Web technologies and mathematical graph algorithms.

```mermaid
flowchart TD
    subgraph Layer1["1. Top Layer: Intent Extraction & Constraint Parsing"]
        User["User Natural Language Input"] --> Orchestrator["PrioryAgentOrchestrator\n(PrioryChatSession)"]
        Orchestrator --> IntentParser["IntentParser\n(Top LLM)"]
        IntentParser --> PydanticIntent["PlayerGoalIntent & ResolvedGoal\n(Typed Pydantic Schema)"]
    end

    subgraph Layer2["2. Core Layer: Semantic Knowledge Graph & Deterministic Math"]
        PydanticIntent --> SQS["SemanticQueryService\n(SPARQL Entity Resolution)"]
        SQS <--> GraphStore["PrioryGraphStore\n(In-Memory RDFLib Triples)"]
        GraphStore <--> TTL["OWL 2 DL Schemas & SKOS Vocabularies\n(priory_core.ttl, vocab/*.ttl, instances/*.ttl)"]
        
        SQS --> DiffEngine["AccountDiffEngine\n(DAG Traversal & Account Delta)"]
        DiffEngine <--> GraphStore
        DiffEngine <--> Account["Player AccountState\n(Materials, Bank, Wallet, Disciplines)"]
        
        DiffEngine --> Solver["PathSolver\n(Time-Gate, Gold & Route Optimization)"]
        Solver <--> GraphStore
        
        DiffEngine --> Ranker["AccountRanker\n(Leaderboards & Expansion Filters)"]
        Ranker <--> GraphStore
    end

    subgraph Layer3["3. Bottom Layer: Grounded Synthesis & User Presentation"]
        Solver --> SubgraphContext["Semantic Context Serialization\n(Waypoints, NPCs, Recipes)"]
        SubgraphContext --> GuideGen["GuideGenerator\n(Bottom LLM)"]
        DiffEngine --> GuideGen
        GuideGen --> PydanticGuide["PersonalizedGuide\n(Structured JSON Schema)"]
        PydanticGuide --> UserMarkdown["Rendered User Guide\n(Checklists, Chat Codes, Timetables)"]
    end

    classDef llm fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef semantic fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
    classDef engine fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;
    classDef output fill:#fff3e0,stroke:#f57c00,stroke-width:2px;

    class IntentParser,GuideGen llm;
    class SQS,GraphStore,TTL,SubgraphContext semantic;
    class Orchestrator,DiffEngine,Solver,Ranker,Account engine;
    class User,PydanticIntent,PydanticGuide,UserMarkdown output;
```

---

## 2. End-to-End Sequence & Interaction Flow

```mermaid
sequenceDiagram
    autonumber
    actor Player as 👤 Player
    participant Orch as 🎛️ Orchestrator<br/>(agent/orchestrator.py)
    participant TopLLM as 🧠 Top LLM<br/>(agent/intent_parser.py)
    participant SQS as 🔮 SemanticQueryService<br/>(engine/semantic_query.py)
    participant KG as 📚 GraphStore & RDF Triples<br/>(engine/graph_store.py)
    participant Diff as ⚙️ AccountDiffEngine<br/>(engine/account_diff.py)
    participant Solver as ⏱️ PathSolver<br/>(engine/path_solver.py)
    participant BotLLM as ✍️ Bottom LLM<br/>(agent/guide_generator.py)

    Player->>Orch: "I want to craft 2 legendary sigils tonight, have 90 mins, no WvW"
    
    %% Step 1: Top LLM Intent Parsing
    Orch->>TopLLM: user_prompt + Pydantic schema (PlayerGoalIntent)
    TopLLM-->>Orch: PlayerGoalIntent(target="legendary sigils", qty=2, time=90, excluded=["WvW"])

    %% Step 2: Semantic Entity Resolution
    Orch->>SQS: resolve_entity_by_text("legendary sigils")
    SQS->>KG: SPARQL: Match rdfs:label & skos:altLabel + stemming ("sigil")
    KG-->>SQS: Return item:91505 (Legendary Sigil)
    SQS-->>Orch: ResolvedGoal(item_id=91505, name="Legendary Sigil", qty=2)

    %% Step 3: Recipe DAG Traversal & Account Diffing
    Orch->>Diff: compute_diff(goal_item_id=91505, target_quantity=2, account_state)
    Diff->>KG: SPARQL: Recursive producedBy, hasIngredient, requiresItem, unpacksInto
    KG-->>Diff: Full ingredient DAG & discipline requirements
    Note over Diff: Deducts player's Material Storage (20 Clovers owned)<br/>Checks Wallet (440 Provisioner Tokens owned)<br/>Checks Bank for unpackable containers
    Diff-->>Orch: AccountDiffReport(missing: 40 Clovers, 1500 Lucent Crystals, Gift of Craftsmanship SATISFIED)

    %% Step 4: Multi-Criteria Route Optimization
    Orch->>Solver: solve_optimal_path(diff_report, time_budget=90, excluded=["WvW"])
    Solver->>KG: SPARQL: Discover substitute sources, daily time-gates & vendor currencies
    KG-->>Solver: Alternative routes (Wizard's Vault, Fractals, Vendor Exchanges)
    Note over Solver: Filters out WvW reward tracks<br/>Calculates currency conversions (Volatile Magic ➔ T6)<br/>Projects calendar time-gates
    Solver-->>Orch: OptimalCraftingPlan(checklist, step-by-step roadmap, time_gate_days=0)

    %% Step 5: Subgraph Context Extraction
    Orch->>SQS: get_item_semantic_context_for_llm(91505)
    SQS->>KG: SPARQL: Extract spatial waypoints, NPC names, and direct recipe facts
    KG-->>SQS: Subgraph triples (Waypoint: [&BPwCAAA=], NPC: Miyani)
    SQS-->>Orch: Grounded semantic markdown context

    %% Step 6: Bottom LLM Guide Generation
    Orch->>BotLLM: Grounded Facts + Optimal Plan + Pydantic schema (PersonalizedGuide)
    BotLLM-->>Orch: Structured JSON (PersonalizedGuide)
    
    %% Step 7: Output
    Orch->>Player: Rendered Markdown Checklist & Waypoint Navigation
```

---

## 3. Data Transformation Pipeline

The data representation undergoes precise typed transformations across each boundary:

```mermaid
stateDiagram-v2
    direction LR
    
    [*] --> RawString: 1. User Prompt
    RawString --> PlayerGoalIntentJSON: 2. Top LLM Structured Output
    PlayerGoalIntentJSON --> ResolvedGoalObject: 3. Intent Parser Validation
    ResolvedGoalObject --> SPARQLBindings: 4. Semantic Entity Linking
    SPARQLBindings --> RDFSubgraphs: 5. RDFLib Graph Execution
    RDFSubgraphs --> ItemNodeDAG: 6. Recursive Recipe Traversal
    ItemNodeDAG --> AccountDiffReport: 7. Inventory Delta Math
    AccountDiffReport --> OptimalCraftingPlan: 8. Constraint & Time-Gate Solver
    OptimalCraftingPlan --> GroundedFactsMarkdown: 9. Semantic Subgraph Serialization
    GroundedFactsMarkdown --> PersonalizedGuideJSON: 10. Bottom LLM Synthesis
    PersonalizedGuideJSON --> RenderedMarkdown: 11. Final Player Output
    RenderedMarkdown --> [*]
```

---

## 4. The Three Touchpoints of the Semantic Web Layer

```mermaid
flowchart LR
    subgraph T1["Touchpoint 1: Semantic Resolution"]
        direction TB
        A1["Fuzzy Natural Language\n('leggy sigil', 'gen 2 staff')"] --> A2["SKOS Taxonomy & altLabel Match\n(priory_ref:weapon, priory_ref:rarity)"]
        A2 --> A3["Canonical Entity IRI\n(<https://priory.gw2/id/item/91505>)"]
    end

    subgraph T2["Touchpoint 2: Graph Reasoning & Math Grounding"]
        direction TB
        B1["Canonical Entity IRI"] --> B2["SPARQL Recipe DAG & Vendor Traversal\n(priory:producedBy, priory:hasSubstituteSource)"]
        B2 --> B3["Deterministic Math Engine\n(AccountDiffEngine & PathSolver)"]
    end

    subgraph T3["Touchpoint 3: Spatial & Factual Serialization"]
        direction TB
        C1["Engine Solution & Item IDs"] --> C2["SPARQL Spatial & NPC Extraction\n(priory:nearestWaypoint, priory:vendorNPC)"]
        C2 --> C3["Factual Prompt Context for Bottom LLM\n(Zero hallucinated waypoints or costs)"]
    end

    T1 --> T2 --> T3

    classDef box fill:#fafafa,stroke:#616161,stroke-width:1px;
    class T1,T2,T3 box;
```

---

## 5. Granular Component & Data Specification Matrix

| Stage | Class / Module | Input Data | 🔍 Semantic Web Operation | Output Data | Concrete Payload Example |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Input** | CLI / UI | Human text | *None (Raw input).* | `str` | `"I want to craft 2 legendary sigils tonight, have 90 mins, no WvW"` |
| **2. Intent Parse** | [`IntentParser`](../agent/intent_parser.py)<br>`agent/intent_parser.py` | `user_prompt: str` | Top LLM compiles prompt into Pydantic schema [`PlayerGoalIntent`](../agent/intent_parser.py). | `PlayerGoalIntent` | `goal_type: SPECIFIC_ITEM`<br>`target_item_name: "legendary sigils"`<br>`target_quantity: 2`<br>`time_budget_minutes: 90`<br>`excluded_game_modes: ["WvW"]` |
| **3. Entity Resolution** | [`SemanticQueryService`](../engine/semantic_query.py)<br>`engine/semantic_query.py` | `"legendary sigils"` | **⚡ SPARQL Query over SKOS Vocabularies:**<br>• Regex query against `rdfs:label` and `skos:altLabel`<br>• Subsumption check on `a priory:LegendarySigil`<br>• Morphological stemming (`sigils` $\to$ `sigil`) | `ResolvedGoal` | `resolved_item_id: 91505`<br>`resolved_item_name: "Legendary Sigil"`<br>`chat_code: "[&AgH5WgEA]"` |
| **4. DAG Traversal** | [`AccountDiffEngine`](../engine/account_diff.py)<br>`engine/account_diff.py` | `item_id: 91505`<br>`multiplier: 2` | **⚡ Recursive SPARQL Tree Query:**<br>`?item priory:producedBy ?recipe .`<br>`?recipe priory:hasIngredient ?req .`<br>`?req priory:requiresItem ?child ; priory:requiresQuantity ?qty .` | `ItemRequirementNode` DAG | • 60x Mystic Clover<br>• 1500x Lucent Crystal<br>• 150x Symbol of Control<br>• 2x Gift of Craftsmanship |
| **5. Account Delta** | [`AccountDiffEngine`](../engine/account_diff.py)<br>`engine/account_diff.py` | Tree DAG + Player [`AccountState`](../engine/account_diff.py) | **⚡ Ontology Container & Discipline Rules:**<br>• Checks `?c priory:unpacksInto ?item` (Starter Kits in bank)<br>• Checks `?recipe priory:requiresDiscipline ?d` against player levels | [`AccountDiffReport`](../engine/account_diff.py) | • Missing Clovers: `40` (60 needed - 20 owned)<br>• Missing Lucent Crystals: `1500`<br>• Gift of Craftsmanship: `SATISFIED` (Wallet has 440 Provisioner Tokens) |
| **6. Source Discovery** | [`SemanticQueryService`](../engine/semantic_query.py)<br>`engine/semantic_query.py` | Missing IDs (`19675`, `89271`, etc.) | **⚡ SPARQL Polymorphic Source Query:**<br>`?item priory:hasSubstituteSource ?path .`<br>Discovers `priory:VendorExchange`, `priory:RewardTrack`, `priory:nearestWaypoint`, and `priory:hasTimeGate`. | `Dict[str, Any]` (Acquisition Paths) | • Wizard's Vault Astral Acclaim<br>• Fractal Relic Vendor (`[&BEEFAAA=]`, 2/day limit)<br>• WvW Reward Tracks |
| **7. Multi-Criteria Solving** | [`PathSolver`](../engine/path_solver.py)<br>`engine/path_solver.py` | `diff_report`, `budget: 90m`, `excluded: ["WvW"]` | **⚡ Time-Gate & Currency Constraint Filtering:**<br>• Filters out `priory:hasGameMode gamemode:WvW`<br>• Queries `priory:requiresCurrency currency:VolatileMagic` for T6 conversion math<br>• Computes calendar bottleneck dates from `priory:dailyCap` | [`OptimalCraftingPlan`](../engine/path_solver.py) | • Checklist: 3 tasks fitting 90-min budget<br>• Estimated Completion: Today (0 time-gate days)<br>• Recommended T6 currency conversions |
| **8. Grounding Context** | [`SemanticQueryService`](../engine/semantic_query.py)<br>`engine/semantic_query.py` | `item_id: 91505` | **⚡ Graph Neighborhood Serialization:**<br>Serializes connected RDF triples into verified Markdown bullet points. | `semantic_context: str` | Facts block passed to Bottom LLM:<br>`### Semantic Entity: Legendary Sigil`<br>`* Waypoints: [&BPwCAAA=]`<br>`* Direct Recipes: Mystic Forge` |
| **9. Guide Synthesis** | [`GuideGenerator`](../agent/guide_generator.py)<br>`agent/guide_generator.py` | Verified Plan + Grounded Context | Bottom LLM strictly formats verified math and waypoints into typed schema [`PersonalizedGuide`](../agent/guide_generator.py). | [`PersonalizedGuide`](../agent/guide_generator.py) | Structured JSON with checklist steps, exact time allocations, and strategic advice. |
| **10. UI Output** | [`PrioryChatSession`](../agent/orchestrator.py)<br>`agent/orchestrator.py` | `guide: PersonalizedGuide` | *None (formatting and rendering).* | Formatted User Guide | Final user-facing markdown output with interactive task boxes and in-game chat codes. |

---

## 6. Architectural Guarantees

1. **Zero Domain Semantics in Python**:
   Per [`AGENTS.md`](../AGENTS.md), no entity labels, weapon taxonomies, currencies, or action verbs are hardcoded in Python. All vocabularies and hierarchy rules reside exclusively in `.ttl` files.

2. **Zero Mathematical Hallucination**:
   The LLM never computes material counts, gold subtractions, or recipe requirements. All arithmetic is calculated through deterministic DAG traversal in [`AccountDiffEngine`](../engine/account_diff.py).

3. **Zero Spatial Hallucination**:
   Waypoint chat links (e.g. `[&BPwCAAA=]`), zone names, and NPC identifiers are fetched directly from ontology instances, ensuring all navigation advice is verifiable in the live game.
