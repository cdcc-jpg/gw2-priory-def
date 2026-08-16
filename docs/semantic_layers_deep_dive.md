# The Three Semantic Layers Deep Dive: `ref`, `def`, and the Triple Store

This document provides a comprehensive, detailed technical analysis of the **three foundational semantic layers** that power Project Priory.

As the Semantic Layer Lead, you must understand how these three layers interact, how W3C standards (SKOS, OWL 2 DL, SHACL, SPARQL 1.1) are applied, and how data flows through the unified graph.

---

## 🗺️ Architectural Map of the Three Semantic Layers

```mermaid
flowchart TB
    subgraph Layer1 ["LAYER 1: Reference Vocabularies (gw2-priory-ref)"]
        direction TB
        SKOS_Currencies["currencies.ttl<br>• skos:prefLabel 'Provisioner Token'<br>• skos:notation 35 (API ID)"]
        SKOS_Weapons["weapon_types.ttl<br>• weapon:Greatsword skos:broader weapon:TwoHandedWeapon"]
        SKOS_Disciplines["disciplines.ttl<br>• discipline:Weaponsmith, discipline:Armorsmith"]
        SKOS_Rarities["rarities.ttl<br>• rarity:Legendary, rarity:Ascended"]
        SKOS_Upgrades["upgrade_types.ttl<br>• upgrade:Sigil, upgrade:Rune"]
        SKOS_GameModes["game_modes.ttl<br>• gamemode:OpenWorld, gamemode:WvW, gamemode:Fractals"]
    end

    subgraph Layer2 ["LAYER 2: Definitions & Instances (gw2-priory-def)"]
        direction TB
        OWL_TBox["OWL 2 DL Schema (ontology/priory_core.ttl)<br>• Classes: priory:Item, priory:Recipe, priory:VendorExchangePath<br>• Properties: priory:requiresCurrency, priory:nearestWaypoint"]
        SHACL_Rules["SHACL Constraints (ontology/priory_shacl.ttl)<br>• Enforces ratings (0-500), cardinalities, mandatory labels"]
        ABox_Twilight["twilight_gen1.ttl (Instance Graph)<br>• item:30699, recipe:forge_twilight, waypoints"]
        ABox_Sigil["legendary_sigil.ttl (Instance Graph)<br>• item:91505, recipe:forge_legendary_sigil, Gift of Craftsmanship"]
    end

    subgraph Layer3 ["LAYER 3: Unified Triple Store & Graph Engine (engine/)"]
        direction TB
        Store["🏛️ PrioryGraphStore (In-Memory RDF Store)<br>Graph Union: ref + def TBox + def ABox<br>(1,056+ Loaded Triples)"]
        SPARQL_Engine["🔍 SPARQL 1.1 Query Engine<br>• Taxonomic Subsumption (skos:broader+)<br>• Parameterized Recipe DAG Traversal<br>• Spatial Waypoint Extraction"]
        Delta_Engine["⚙️ Account Delta Engine (account_diff.py)<br>• Recursive Multiplier Math (N >= 1)<br>• Wallet Currency Bridge (skos:notation)<br>• Legendary Armory Detection"]
        Solver["📐 Multi-Criteria Path Solver (path_solver.py)<br>• Exhausted Source Routing (Vault -> Fractals)<br>• Priority Knapsack Session Scheduler"]
        
        Store --> SPARQL_Engine
        SPARQL_Engine --> Delta_Engine
        Delta_Engine --> Solver
    end

    Layer1 -.->|"Loaded at Startup"| Store
    Layer2 -.->|"Loaded at Startup"| Store

    style Layer1 fill:#e3f2fd,stroke:#1565c0,stroke-width:2px;
    style Layer2 fill:#fce4ec,stroke:#c2185b,stroke-width:2px;
    style Layer3 fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px;
```

---

## 1. LAYER 1: The `ref` Layer (W3C SKOS Taxonomies)

**Repository:** `https://github.com/cdcc-jpg/gw2-priory-ref`  
**Standard:** [W3C SKOS (Simple Knowledge Organization System)](https://www.w3.org/TR/skos-reference/)  
**Primary Responsibility:** Authoritative, decoupled reference vocabularies that classify game concepts and bridge official ArenaNet API IDs to semantic entities.

### Why SKOS instead of OWL Classes?
In ontology design, using OWL classes for fixed taxonomies (like item rarities or weapon categories) leads to "Class Explosion" and makes multi-attribute classification rigid. SKOS allows concepts to exist as lightweight graph individuals organized into **hierarchical concept schemes**.

### Core SKOS Properties Used:
* `skos:ConceptScheme`: The container taxonomy (e.g. `currency:CurrencyScheme`, `weapon:WeaponTypeScheme`).
* `skos:Concept`: An individual concept node (e.g. `currency:ProvisionerToken`, `weapon:Greatsword`).
* `skos:prefLabel`: The authoritative human label in a specific language (`"Provisioner Token"@en`).
* `skos:altLabel`: Alternate slang, abbreviations, or synonyms (`"Leggy Sigil"@en`, `"GoM"@en`).
* `skos:broader`: Declares a parent category (`weapon:Greatsword skos:broader weapon:TwoHandedWeapon`).
* `skos:notation`: Stores the official ArenaNet API integer ID (`"35"^^xsd:integer`).

### Concrete Example: The Currency Bridge (`currencies.ttl`)
```turtle
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix currency: <https://priory.gw2/ref/currency/> .

currency:CurrencyScheme a skos:ConceptScheme ;
    rdfs:label "Guild Wars 2 Currency & Token Taxonomy"@en .

currency:ProvisionerToken a skos:Concept ;
    skos:inScheme currency:CurrencyScheme ;
    skos:prefLabel "Provisioner Token"@en ;
    skos:notation "35"^^xsd:integer . # <--- Matches ArenaNet API /v2/account/wallet ID

currency:AstralAcclaim a skos:Concept ;
    skos:inScheme currency:CurrencyScheme ;
    skos:prefLabel "Astral Acclaim"@en ;
    skos:notation "68"^^xsd:integer .
```

### The Hierarchical Weapon Taxonomy (`weapon_types.ttl`)
```mermaid
graph TD
    WeaponScheme["weapon:WeaponTypeScheme (skos:ConceptScheme)"] --> TwoHanded["weapon:TwoHandedWeapon (skos:Concept)"]
    WeaponScheme --> OneHanded["weapon:OneHandedWeapon (skos:Concept)"]
    WeaponScheme --> OffHand["weapon:OffHandWeapon (skos:Concept)"]

    TwoHanded ---|skos:narrower| GS["weapon:Greatsword"]
    TwoHanded ---|skos:narrower| Hammer["weapon:Hammer"]
    TwoHanded ---|skos:narrower| Staff["weapon:Staff"]
    TwoHanded ---|skos:narrower| Longbow["weapon:Longbow"]

    OneHanded ---|skos:narrower| Sword["weapon:Sword"]
    OneHanded ---|skos:narrower| Dagger["weapon:Dagger"]
    OneHanded ---|skos:narrower| Axe["weapon:Axe"]

    style WeaponScheme fill:#e8eaf6,stroke:#3f51b5;
    style TwoHanded fill:#c5cae9,stroke:#3f51b5;
    style OneHanded fill:#c5cae9,stroke:#3f51b5;
    style OffHand fill:#c5cae9,stroke:#3f51b5;
```

---

## 2. LAYER 2: The `def` Layer (OWL 2 DL Schemas & ABox Instances)

**Repository:** `https://github.com/cdcc-jpg/gw2-priory-def`  
**Standards:** [W3C OWL 2 DL](https://www.w3.org/TR/owl2-syntax/), [W3C SHACL](https://www.w3.org/TR/shacl/)  
**Primary Responsibility:** Formal schema (TBox), integrity validation shapes, and concrete game instance graphs (ABox) representing items, recipe DAGs, and spatial navigation.

---

### A. The Core Schema (TBox — `ontology/priory_core.ttl`)

Defines the class hierarchy and relationships governing how items transform into other items.

```mermaid
classDiagram
    class Item {
        +Integer gw2Id
        +String rdfs:label
        +String chatCode
        +Boolean isAccountBound
    }
    class EquipableItem
    class Weapon
    class LegendaryWeapon
    class PrecursorWeapon
    class UpgradeComponent
    class LegendarySigil
    class Recipe {
        +Integer outputQuantity
    }
    class DisciplineRecipe {
        +Integer requiresRating
    }
    class MysticForgeRecipe
    class IngredientRequirement {
        +Integer requiredQuantity
    }
    class AcquisitionPath
    class VendorExchangePath {
        +String vendorNPC
        +String zoneName
        +String waypointName
        +String nearestWaypoint
    }
    class TimeGate

    Item <|-- EquipableItem
    EquipableItem <|-- Weapon
    Weapon <|-- LegendaryWeapon
    Weapon <|-- PrecursorWeapon
    Item <|-- UpgradeComponent
    UpgradeComponent <|-- LegendarySigil

    Recipe <|-- DisciplineRecipe
    Recipe <|-- MysticForgeRecipe

    Item "1" --> "*" Recipe : priory:producedBy
    Recipe "1" --> "1" Item : priory:producesItem
    Recipe "1" --> "1..4" IngredientRequirement : priory:hasIngredientRequirement
    IngredientRequirement "1" --> "1" Item : priory:requiresItem

    Item "1" --> "*" AcquisitionPath : priory:acquiredVia
    AcquisitionPath <|-- VendorExchangePath
    VendorExchangePath --> "1" TimeGate : priory:hasTimeGate
```

---

### B. The Reified N-Ary Relation Pattern (Why We Need It)

In standard RDF, a triple is binary: `(Subject, Predicate, Object)`.  
However, crafting requires expressing **Subject (Recipe) $\rightarrow$ Object (Item) $\rightarrow$ Quantity (Integer)**.

To represent quantities without ambiguity, Project Priory uses the **W3C Reified N-Ary Relation Pattern**:

```mermaid
graph LR
    Recipe["recipe:forge_twilight<br>(priory:MysticForgeRecipe)"] -->|priory:hasIngredientRequirement| ReqNode["_:req1<br>(priory:IngredientRequirement)"]
    ReqNode -->|priory:requiresItem| ItemNode["item:19675<br>(Mystic Clover)"]
    ReqNode -->|priory:requiredQuantity| Qty["77<br>(xsd:integer)"]

    style Recipe fill:#fff3e0,stroke:#e65100;
    style ReqNode fill:#ffe0b2,stroke:#e65100;
    style ItemNode fill:#ffcc80,stroke:#e65100;
    style Qty fill:#ffebee,stroke:#c62828;
```

In Turtle (`.ttl`):
```turtle
recipe:forge_twilight a priory:MysticForgeRecipe ;
    priory:producesItem item:30699 ;
    priory:hasIngredientRequirement [
        a priory:IngredientRequirement ;
        priory:requiresItem item:19675 ; # Mystic Clover
        priory:requiredQuantity 77       # Exact quantity
    ] .
```

---

### C. The Instance Graph (ABox — `ontology/instances/`)

Instance graphs define actual items, recipes, vendor exchanges, and spatial waypoints in Guild Wars 2.

#### Example: Faction Provisioner Vendor Exchange with Spatial Waypoint
```turtle
item:89276 a priory:GiftItem ;
    rdfs:label "Gift of Craftsmanship"@en ;
    priory:gw2Id 89276 ;
    priory:hasRarity rarity:Legendary ;
    priory:isAccountBound true ;
    priory:acquiredVia [
        a priory:VendorExchangePath ;
        priory:requiresCurrency currency:ProvisionerToken ;
        priory:requiredQuantity 50 ;
        priory:vendorNPC "Faction Provisioner"@en ;
        priory:zoneName "Black Citadel"@en ;
        priory:waypointName "Junker's Waypoint"@en ;
        priory:nearestWaypoint "[&BKgDAAA=]" ; # <--- Clickable in-game waypoint code!
        priory:hasTimeGate [ a priory:TimeGate ; rdfs:label "Daily barter limit" ]
    ] .
```

---

### D. SHACL Validation Rules (`ontology/priory_shacl.ttl`)

Before any graph file is merged into production, `pyshacl` validates all triples against structural constraints to prevent corrupted data:

```turtle
priory:DisciplineRecipeShape a sh:NodeShape ;
    sh:targetClass priory:DisciplineRecipe ;
    sh:property [
        sh:path priory:requiresRating ;
        sh:datatype xsd:integer ;
        sh:minInclusive 0 ;
        sh:maxInclusive 500 ; # <--- Cannot exceed max crafting level 500
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:message "Discipline recipe must require a rating between 0 and 500."@en ;
    ] ;
    sh:property [
        sh:path priory:requiresDiscipline ;
        sh:minCount 1 ;
        sh:nodeKind sh:IRI ;
        sh:message "Must link to a valid SKOS Discipline Concept."@en ;
    ] .
```

---

## 3. LAYER 3: The Unified Triple Store & Graph Engine (`engine/`)

The engine manages the in-memory graph, executes SPARQL 1.1 queries, applies live player overlays, and optimizes gameplay routes.

```mermaid
graph TD
    subgraph Loader ["1. Graph Store (engine/graph_store.py)"]
        LoadAll["PrioryGraphStore.load_all()<br>1. Loads gw2-priory-ref/vocab/*.ttl<br>2. Loads gw2-priory-def/ontology/priory_core.ttl<br>3. Loads gw2-priory-def/ontology/instances/*.ttl<br>Result: Unified In-Memory Graph (1,056+ Triples)"]
    end

    subgraph Service ["2. Semantic Discovery Service (engine/semantic_query.py)"]
        TaxonomySearch["find_items_by_taxonomy()<br>SPARQL: ?item priory:hasWeaponType ?wt . ?wt skos:broader+ weapon:TwoHandedWeapon"]
        PathDiscovery["discover_acquisition_paths(item_id)<br>SPARQL: Discovers crafting, vendor, waypoints, time-gates"]
        EntityResolution["resolve_entity_by_text(query)<br>SPARQL: Exact label match -> Substring regex -> ChatCode match"]
    end

    subgraph Delta ["3. Account Delta Engine (engine/account_diff.py)"]
        DiffCompute["compute_diff(goal_id, account, target_quantity)<br>• Recursive DAG descent (_resolve_node)<br>• Multiplies ingredients by target_quantity (e.g. 2x)<br>• Subtracts owned materials in materials/bank/inventory/armory<br>• Wallet Currency Bridge: Resolves currency:ProvisionerToken (ID: 35)"]
    end

    subgraph SolverEngine ["4. Multi-Criteria Path Solver (engine/path_solver.py)"]
        PathSolve["solve_optimal_path(diff_report, account, tp_prices, exhausted_sources)<br>• Evaluates alternative clover routes (Vault vs Fractals vs Forge)<br>• Respects exhausted_sources (e.g. WizardVault)<br>• Priority-Based Knapsack Time Allocation"]
    end

    Loader --> Service
    Service --> Delta
    Delta --> SolverEngine
```

---

## 4. How the Three Layers Connect in a Single Query

Here is the complete cross-layer execution trace when a player requests `Gift of Craftsmanship`:

```mermaid
sequenceDiagram
    autonumber
    actor Player as Player
    participant TopLLM as Top LLM (IntentParser)
    participant SPARQL as SPARQL Engine (semantic_query.py)
    participant Store as Triple Store (ref + def)
    participant API as ArenaNet REST API
    participant Delta as Delta Engine (account_diff.py)
    participant Solver as Path Solver (path_solver.py)
    participant BottomLLM as Bottom LLM (GuideGenerator)

    Player->>TopLLM: "I want to craft 2 legendary sigils tonight. I have 90 mins."
    TopLLM->>SPARQL: Candidate string: "Legendary Sigil", Quantity: 2, Time: 90
    SPARQL->>Store: Query canonical item where label = "Legendary Sigil"
    Store-->>SPARQL: Matched URI item:91505 (GW2 ID: 91505, ChatCode: [&AgF5YwEA])
    
    API->>Delta: Fetch live snapshot (materials, bank, wallet, legendary armory)
    Delta->>Store: Recursive DAG traversal for item:91505 (multiplier = 2)
    Note over Store,Delta: Traverses to Gift of Craftsmanship (item:89276)<br>Reads priory:requiresCurrency currency:ProvisionerToken<br>Reads skos:notation 35 (from ref/currencies.ttl)
    
    Delta->>Delta: Inspects account.wallet[35] -> 440 owned vs 100 needed<br>Marks Gift of Craftsmanship as 100% SATISFIED!
    Delta->>Delta: Clovers: 60 needed - 20 owned = 40 missing
    Delta-->>Solver: DiffReport(missing_clovers=40, craftsmanship_satisfied=True)
    
    Solver->>Solver: Allocates 90 mins: 20m Vault Clovers + 70m Meta Farming<br>(Omits 15m Provisioner barter run because tokens are owned!)
    Solver-->>BottomLLM: OptimalPlan + Verified Subgraph Context
    BottomLLM->>Player: "✅ Provisioner Tokens Satisfied! [1] Buy Vault Clovers (20m) [2] Farm Silverwastes [&BF8HAAA=] (70m)"
```

---

## 5. Architectural Summary Table

| Layer | Physical Location | Standard | Role & Responsibility |
| :--- | :--- | :--- | :--- |
| **`ref`** | `gw2-priory-ref/vocab/*.ttl` | **W3C SKOS** | Controlled vocabularies, category hierarchies, API integer ID bridges (`skos:notation`), and human synonyms. |
| **`def` (Schema)** | `gw2-priory-def/ontology/priory_core.ttl` | **W3C OWL 2 DL** | TBox schema defining classes, object/data properties, N-ary relation patterns, and spatial waypoint properties. |
| **`def` (Shapes)** | `gw2-priory-def/ontology/priory_shacl.ttl` | **W3C SHACL** | Closed-world integrity validation enforcing data contracts on all triples before merging. |
| **`def` (Instances)** | `gw2-priory-def/ontology/instances/*.ttl` | **RDF Graphs** | Verified item DAGs (*Twilight*, *Legendary Sigil*), recipe combinations, vendor tables, and waypoint chat codes. |
| **Triple Store** | `gw2-priory-def/engine/graph_store.py` | **RDFLib / Oxigraph** | In-memory graph store holding the union of all `.ttl` files with SPARQL 1.1 query support. |
| **Delta Engine** | `gw2-priory-def/engine/account_diff.py` | **Python Math** | Multiplier-aware recursive inventory delta subtraction, wallet checks, and Legendary Armory detection. |
| **Path Solver** | `gw2-priory-def/engine/path_solver.py` | **Priority Knapsack** | Multi-criteria cost evaluation (Vault vs Forge) and time-budget session scheduler. |
