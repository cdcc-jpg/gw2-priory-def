# End-to-End Data Flow & Reasoning Trace

This document details the exact lifecycle of player requests as they flow through every subsystem of Project Priory, providing concrete sequence diagrams, JSON payloads, mathematical state transitions, and spatial graph context.

---

## 1. End-to-End Information Flow Overview (Direct Recipe Query Trace)

### Scenario: *"Get me the recipe I need to follow to craft Twilight."*

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 User
    participant Orch as 🎛️ Orchestrator<br/>(agent/orchestrator.py)
    participant TopLLM as 🧠 Top LLM<br/>(agent/intent_parser.py)
    participant SQS as 🔮 SemanticQueryService<br/>(engine/semantic_query.py)
    participant KG as 📚 Knowledge Graph (RDF/OWL/SKOS)<br/>(engine/graph_store.py)
    participant Diff as ⚙️ AccountDiffEngine<br/>(engine/account_diff.py)
    participant Solver as ⏱️ PathSolver<br/>(engine/path_solver.py)
    participant BotLLM as ✍️ Bottom LLM<br/>(agent/guide_generator.py)

    User->>Orch: "Get me the recipe I need to follow to craft Twilight."
    
    rect rgb(230, 245, 255)
    Note over Orch,TopLLM: Layer 1: Natural Language Intent Parsing
    Orch->>TopLLM: Prompt + Pydantic Schema (PlayerGoalIntent)
    TopLLM-->>Orch: PlayerGoalIntent(target="Twilight", qty=1, type=DIRECT_TARGET)
    end

    rect rgb(245, 235, 250)
    Note over Orch,KG: Layer 2: Semantic Entity Resolution & Taxonomy Grounding
    Orch->>SQS: resolve_entity_by_text("Twilight")
    SQS->>KG: SPARQL: Match rdfs:label & skos:altLabel
    KG-->>SQS: item:30704 (Legendary Greatsword, chatCode: [&AgErZgAA])
    SQS-->>Orch: ResolvedGoal(item_id=30704, name="Twilight", qty=1)
    end

    rect rgb(235, 250, 235)
    Note over Orch,Solver: Layer 3: Deterministic Graph Traversal & Delta Math
    Orch->>Diff: compute_diff(goal_item_id=30704, qty=1, account_state)
    Diff->>KG: SPARQL: Recursive producedBy & hasIngredientRequirement DAG
    KG-->>Diff: Full 5-tier ingredient tree + discipline rules
    Diff-->>Orch: AccountDiffReport (owned vs. missing materials & wallet currencies)
    Orch->>Solver: solve_optimal_path(diff_report, account_state, tp_prices)
    Solver->>KG: SPARQL: Query substitute sources, milestones & time-gates
    KG-->>Solver: Milestone vendors, alternative currency exchanges
    Solver-->>Orch: OptimalCraftingPlan (5-phase roadmap, total gold cost, time-gates)
    end

    rect rgb(255, 245, 230)
    Note over Orch,BotLLM: Layer 4: Spatial Context & Grounded Synthesis
    Orch->>SQS: get_item_semantic_context_for_llm(30704)
    SQS->>KG: SPARQL: Fetch NPCs, zones, and waypoint chat codes
    KG-->>SQS: Subgraph (Miyani [&BBAEAAA=], Rojan [&BHsBAAA=])
    SQS-->>Orch: Grounded semantic facts block
    Orch->>BotLLM: Verified Facts + Optimal Plan + Pydantic Schema (PersonalizedGuide)
    BotLLM-->>Orch: Structured JSON (PersonalizedGuide)
    Orch->>User: Formatted Guide with Roadmap, Checklists & Chat Codes
    end
```

#### Step-by-Step Flow Breakdown
1. **Top LLM Intent Parsing (`agent/intent_parser.py`):**
   * Parses the user prompt into typed `PlayerGoalIntent(target_entity="Twilight", target_quantity=1, goal_type=GoalType.DIRECT_TARGET)`.
2. **Semantic Entity Resolution (`engine/semantic_query.py`):**
   * Executes SPARQL over `PrioryGraphStore` matching `rdfs:label` and `skos:altLabel`.
   * Resolves text `"Twilight"` to canonical IRI `item:30704` (GW2 ID `30704`, Chat Code `[&AgErZgAA]`, `rarity:Legendary`, `weapon:Greatsword`).
3. **Deterministic Recipe DAG Traversal & Account Delta (`engine/account_diff.py`):**
   * Traverses `recipe:forge_twilight` recursively down to raw leaves (*Dusk*, *Gift of Fortune*, *Gift of Mastery*, *Gift of Twilight*).
   * Cross-references live `AccountState` (materials, bank, wallet, armory unlock status).
   * Computes exact missing materials, currency requirements (Spirit Shards, Karma), and discipline skill requirements (Weaponsmith 400, Armorsmith 400).
4. **Multi-Criteria Route Optimization & Milestones (`engine/path_solver.py`):**
   * Formulates the authentic **5-Phase Master Roadmap** (*Phase 1: Precursor Journey*, *Phase 2: Mystic Fortune/Tribute*, *Phase 3: Tyrian Mastery*, *Phase 4: Specific Weapon Gift*, *Phase 5: Final Mystic Forge Assembly*).
   * Calculates live Trading Post costs for tradeable missing components.
5. **Spatial Context Extraction (`engine/semantic_query.py`):**
   * Queries spatial milestone vendor individuals: **Miyani** (`[&BBAEAAA=]`), **Rojan the Penitent** (`[&BHsBAAA=]`), and **Grandmaster Hobbs** (`[&BBAEAAA=]`).
6. **Bottom LLM Grounded Synthesis (`agent/guide_generator.py`):**
   * Synthesizes the finalized, hallucination-free progression guide with formatted roadmap, copyable chat codes, and checklists.

---

## 2. Complex Multi-Constraint Sequence & Payload Trace

### Scenario: *"I want to craft 2 legendary sigils tonight. I have 90 mins."*

```mermaid
sequenceDiagram
    autonumber
    actor User as 👤 Player
    participant CLI as 💻 priory_cli.py
    participant Session as 💬 PrioryChatSession
    participant Intent as 🧠 IntentParser (Top LLM)
    participant SPARQL as 🔍 SemanticQueryService
    participant Store as 🏛️ PrioryGraphStore (Triple Store)
    participant API as 🌐 ArenaNet REST API (GW2ApiClient)
    participant Delta as ⚙️ AccountDiffEngine
    participant Solver as 📐 PathSolver
    participant Guide as 💡 GuideGenerator (Bottom LLM)

    User->>CLI: "I want to craft 2 legendary sigils tonight. I have 90 mins."
    CLI->>Session: send_message(prompt)
    
    %% Step 1: Intent Parsing
    Session->>Intent: parse_intent(prompt, context)
    Intent->>Intent: Top LLM extraction -> PlayerGoalIntent JSON
    Intent->>SPARQL: resolve_entity_by_text("Legendary Sigil")
    SPARQL->>Store: Exact match SPARQL query (label = "Legendary Sigil")
    Store-->>SPARQL: Entity: item:91505, GW2 ID: 91505, ChatCode: [&AgF5YwEA]
    SPARQL-->>Intent: ResolvedGoal(item_id=91505, quantity=2, time=90)
    Intent-->>Session: ResolvedGoal

    %% Step 2: Live API Sync
    Session->>API: fetch_account_snapshot()
    API-->>Session: AccountState(materials, bank, wallet={35: 440}, armory={91505: 0})

    %% Step 3: Delta Math
    Session->>Delta: compute_diff(goal_id=91505, account, target_quantity=2)
    Delta->>Store: Recursive DAG expansion (_resolve_node)
    Note over Delta,Store: Expands Gift of Sigils (91508) -> 60 Clovers (needs 60, owns 20 -> 40 missing)<br>Expands Gift of Craftsmanship (89276) -> Provisioner Tokens (needs 100, owns 440 in wallet -> SATISFIED!)
    Delta-->>Session: AccountDiffReport(missing_clovers=40, craftsmanship_satisfied=True)

    %% Step 4: Multi-Criteria Path Solving
    Session->>Solver: solve_optimal_path(diff_report, account, tp_prices)
    Solver->>Solver: Calculates costs: Wizard's Vault @ 0g (40*60=2400 Acclaim) vs Forge @ 140g<br>Schedules 90m: 20m Vault Clovers + 70m Meta Farming
    Solver-->>Session: OptimalCraftingPlan

    %% Step 5: Subgraph Context & Guide Synthesis
    Session->>SPARQL: get_item_semantic_context_for_llm(91505)
    SPARQL->>Store: Extract direct recipes, currencies, waypoints
    Store-->>SPARQL: Markdown Subgraph Facts
    SPARQL-->>Session: semantic_context
    
    Session->>Guide: generate_guide(goal, diff_report, semantic_context)
    Guide->>Guide: Bottom LLM synthesis -> Injects waypoint [&BKgDAAA=] and [&BF8HAAA=]
    Guide-->>Session: PersonalizedGuide
    Session-->>CLI: PersonalizedGuide
    CLI-->>User: Renders In-Game Checklist & Recommendations
```

---

## 2. Step-by-Step Data Payload Transitions

### Step 1: Player Natural Language Prompt
```text
"I want to craft 2 legendary sigils tonight. I have 90 mins."
```

---

### Step 2: Top LLM Structured Intent Output
The Top LLM converts the natural text into a structured Pydantic object:
```json
{
  "goal_item_query": "Legendary Sigil",
  "target_quantity": 2,
  "time_budget_minutes": 90,
  "excluded_game_modes": [],
  "preferred_game_modes": [],
  "exhausted_sources": [],
  "liquid_gold_budget": null
}
```

---

### Step 3: Semantic Entity Resolution
`SemanticQueryService.resolve_entity_by_text` runs an exact label match query against the Knowledge Graph:
```sparql
SELECT DISTINCT ?item ?gw2Id ?label ?chatCode WHERE {
    ?item priory:gw2Id ?gw2Id ;
          rdfs:label ?label .
    OPTIONAL { ?item priory:chatCode ?chatCode }
    FILTER (lcase(str(?label)) = "legendary sigil")
}
```
**Matched Entity:**
* **URI:** `<https://priory.gw2/id/item/91505>`
* **GW2 ID:** `91505`
* **Label:** `"Legendary Sigil"`
* **Chat Code:** `"[&AgF5YwEA]"`

---

### Step 4: Live Account State (`AccountState`)
The `GW2ApiClient` fetches the player's live account snapshot from ArenaNet REST endpoints:
```json
{
  "materials": {
    "19675": 20,       // 20 Mystic Clovers owned
    "19721": 150       // 150 Globs of Ectoplasm owned
  },
  "bank": {},
  "inventory": {},
  "wallet": {
    "35": 440,         // 440 Provisioner Tokens owned!
    "68": 500          // 500 Astral Acclaim owned
  },
  "legendary_armory": {
    "91505": 0         // 0 Sigils in Armory (Goal: 2)
  },
  "disciplines": {
    "weaponsmith": 500
  }
}
```

---

### Step 5: Deterministic Delta Math (`AccountDiffEngine`)
The engine descends the recipe DAG recursively with multiplier $N = 2$:

$$\text{Mystic Clovers Required} = 30 \times 2 = 60\text{ Clovers}$$
$$\text{Missing Clovers} = \max(0, 60 - 20\text{ owned}) = \mathbf{40\text{ Clovers Missing}}$$

$$\text{Provisioner Tokens Required} = 50 \times 2 = 100\text{ Tokens}$$
$$\text{Owned in Wallet} = 440\text{ Tokens} \ge 100 \implies \mathbf{Gift\ of\ Craftsmanship\ is\ 100\%\ Satisfied!}$$

**Diff Report Summary:**
```json
{
  "goal_item_id": 91505,
  "goal_item_name": "Legendary Sigil",
  "target_quantity": 2,
  "is_fully_satisfied": false,
  "missing_materials": {
    "Mystic Clover": 40,
    "Pile of Lucent Crystal": 1500,
    "Symbol of Control": 150,
    "Symbol of Enhancement": 150,
    "Symbol of Pain": 150,
    "Vicious Claw": 200,
    "Powerful Blood": 200
  },
  "missing_disciplines": []
}
```

---

### Step 6: Multi-Criteria Path Solving (`PathSolver`)
The solver allocates the player's 90-minute time budget:
1. **Urgency 1 (Daily Reset Tasks):**
   * *Provisioner Barter Run:* **0 mins** (Omitted because 440 tokens already satisfy the requirement!).
   * *Wizard's Vault Clovers:* **20 mins** (Claim 40 clovers for 2,400 Astral Acclaim).
2. **Urgency 2 (Elastic Material Farming):**
   * $\text{Remaining Time} = 90 - 20 = \mathbf{70\text{ mins}}$ allocated to Silverwastes / Drizzlewood meta farming.

---

### Step 7: Final Synthesized Progression Guide
The Bottom LLM receives the verified numbers and spatial waypoints, producing the final clean response:

```text
──────────────────────────────────────────────────────────────────────────────
 🎯  OPTIMAL PROGRESSION GUIDE: 2x LEGENDARY SIGIL [&AgF5YwEA]
──────────────────────────────────────────────────────────────────────────────
📊 Overall Account Readiness: 45%

💡 STRATEGIC RECOMMENDATIONS:
   ✅ Provisioner Tokens Ready: Your account has enough Provisioner Tokens (440 owned vs 100 needed) to fulfill this requirement immediately!
   🎲 Mystic Clovers (40 needed): Use Astral Acclaim from the Wizard's Vault first (60 Acclaim each).

📋 ACTIONABLE SESSION PLAN (Tonight's 90 mins):
   [1] Complete Daily Wizard's Vault Tasks (~20 mins | OpenWorld)
       -> Complete daily objectives to claim Astral Acclaim and purchase remaining Mystic Clovers.
   [2] Gather Materials & Farm Meta Events (~70 mins | OpenWorld) [[&BF8HAAA=]]
       -> Teleport to Camp Resolve Waypoint [&BF8HAAA=] in Silverwastes to farm gold, Lodestones, and Lucent Motes.

📦 REMAINING DELTA TO CRAFT:
   • Mystic Clover: 40 needed
   • Pile of Lucent Crystal: 1500 needed
   • Symbol of Control: 150 needed
   • Symbol of Enhancement: 150 needed
   • Symbol of Pain: 150 needed
```
