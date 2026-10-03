# Python Domain Logic Location Map

## Rules Extracted

| Rule Description | File | Line | Classification |
| --- | --- | --- | --- |
| Evaluate missing crafting disciplines and mastery ratings for Legendaries | `engine/account_diff.py` | L1851 | **OWL (axiomatic)** / SHACL-SPARQL |
| Unpackability inference (player owns container, ergo conditionally owns contents) | `engine/account_diff.py` | L1544 | **SPARQL CONSTRUCT** |
| Recursive DAG multiplier logic calculating missing tree units based on inventory | `engine/account_diff.py` | L1525 | **Must stay in Python** (Arithmetic) |
| Priority weighting heuristics for assigning daily tasks (e.g. Prov Tokens = 95.0 for Gen2) | `engine/path_solver.py` | L2048 | **SHACL-SPARQL** / Python |
| Knapsack dynamic scheduling algorithm based on session time budgets | `engine/path_solver.py` | L1902 | **Must stay in Python** (Optimization) |
| Live Buy vs. Craft vs. Vault arbitrage price comparison | `engine/path_solver.py` | L422 | **Must stay in Python** (Dynamic APIs) |
| Precursor acquisition strategy fallback if readiness_pct < 100.0 | `engine/twilight_journey_solver.py` | L242 | **SHACL-SPARQL** |
| Hardcoded 8.0 hours for Gift of Battle if missing | `engine/twilight_journey_solver.py` | L252 | **SPARQL CONSTRUCT** / SHACL |
| Map exploration estimate based on lacking Gift of Exploration | `engine/twilight_journey_solver.py` | L251 | **SPARQL CONSTRUCT** |
| Wizard's Vault exhaustion forcing fallback to Legendary Starter Kits | `engine/twilight_journey_solver.py` | L284 | **SHACL-SPARQL** / Python |

## Top 10 Candidates to Move to Semantic Layer

1. **Legendary Prerequisite Validation** (`account_diff.py:L1851`): Moving mastery and crafting discipline requirements to OWL axiomatic class restrictions or SHACL validation constraints perfectly maps to semantic reasoning.
2. **Container Unpackability** (`account_diff.py:L1544`): Can be replaced with a `SPARQL CONSTRUCT` query that dynamically asserts ownership of contents when a container is in the inventory.
3. **Gift of Battle Cost Estimation** (`twilight_journey_solver.py:L252`): The 8-hour flat cost for WvW could be attached directly as a data property in the RDF graph rather than hardcoded in Python.
4. **Map Exploration Cost Estimation** (`twilight_journey_solver.py:L251`): Time estimates for map completion should be node properties within the `AcquisitionPath` instances in the graph.
5. **Wizard's Vault Exhaustion Logic** (`twilight_journey_solver.py:L284`): Rule-based fallback mechanisms can be expressed as a `SHACL` conditional constraint.
6. **Precursor Acquisition Strategy Selection** (`twilight_journey_solver.py:L242`): Recommending the optimal path could be driven by a SPARQL query sorting by a generated cost metric.
7. **Daily Task Priority Weights** (`path_solver.py:L2048`): Static priority weights (e.g., assigning a 95 weight for Gen2 provisioner tokens) belongs in the TTL definitions of the paths, queried via SPARQL, rather than Python `if-else` blocks.
8. **Time-gate Dependency Validation** (`twilight_journey_solver.py`): Checking for daily crafting limits (e.g., Mithrillium) should be enforced via SHACL constraints on the `Recipe` or `TimeGate` ontology nodes.
9. **Event/Lounge Feature Requirements** (`path_solver.py`): Requiring a VIP lounge pass for certain fast routes can be inferred using OWL property chains (`hasLoungeAccess -> enablesRoute`).
10. **Arbitrage Eligibility Flags** (`path_solver.py`): While the math stays in Python, the boolean flags for *whether* an item is eligible for arbitrage (e.g. `isTradeable`, `isCraftable`) should purely be driven by the graph.
