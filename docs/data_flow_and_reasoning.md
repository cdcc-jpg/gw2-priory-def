# End-to-End Data Flow & Reasoning Trace

This document details the exact lifecycle of a player request as it flows through every subsystem of Project Priory, providing concrete JSON payloads, mathematical state transitions, and sequence diagrams.

---

## 1. Complete End-to-End Sequence Diagram

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
