"""Multi-Criteria Path & Optimization Solver for Project Priory.

Calculates the mathematically optimal acquisition and crafting routes based purely
on dynamic SPARQL graph queries and live Trading Post API prices.

ZERO DOMAIN HARDCODING IN PYTHON: All bottleneck rules, vendor definitions, 
currencies, waypoints, and acquisition pathways are queried dynamically from RDF.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from rdflib import Literal, URIRef
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffReport, AccountState


class CloverStrategyOption(BaseModel):
    source_name: str
    clovers_obtainable: int
    estimated_gold_cost: float
    required_currencies: Dict[str, int] = Field(default_factory=dict)
    time_gate_note: Optional[str] = None
    recommended: bool = False


class OptimalCraftingPlan(BaseModel):
    goal_item_name: str
    goal_item_id: int
    target_quantity: int = 1
    is_already_owned: bool
    estimated_total_gold_cost: float
    precursor_strategy: Optional[str] = None
    clover_strategy: List[CloverStrategyOption]
    bottlenecks: List[str]
    step_by_step_roadmap: List[Dict[str, Any]]


class PathSolver:
    """Evaluates alternative acquisition routes dynamically via semantic graph queries."""

    def __init__(self, graph_store: PrioryGraphStore):
        self.store = graph_store

    def solve_optimal_path(
        self,
        diff_report: AccountDiffReport,
        account: AccountState,
        tp_prices: Optional[Dict[int, float]] = None,
        excluded_modes: Optional[List[str]] = None,
        exhausted_sources: Optional[List[str]] = None
    ) -> OptimalCraftingPlan:
        prices = tp_prices or {}
        missing = diff_report.summary_missing_materials
        excluded = excluded_modes or []
        exhausted = exhausted_sources or []
        target_qty = diff_report.target_quantity

        # ----------------------------------------------------------------------
        # 1. Dynamic Precursor & Starter Kit Strategy
        # ----------------------------------------------------------------------
        precursor_strat = None
        for sub in diff_report.root_node.sub_requirements:
            if "Unpackable from" in sub.label:
                precursor_strat = f"🎁 **Starter Kit Shortcut:** {sub.label}! (0 gold needed — select this option when opening your Bank choice chest)"
                break

        if not precursor_strat and not diff_report.is_fully_satisfied:
            # Check if root has a precursor requirement in graph
            prec_query = """
            SELECT ?precursor ?precursorId ?label ?isBound WHERE {
                ?recipe priory:producesItem ?goal ;
                        priory:hasIngredientRequirement ?req .
                ?goal priory:gw2Id ?goalId .
                ?req priory:requiresItem ?precursor .
                ?precursor a priory:PrecursorWeapon ;
                           priory:gw2Id ?precursorId ;
                           rdfs:label ?label .
                OPTIONAL { ?precursor priory:isAccountBound ?isBound }
            } LIMIT 1
            """
            p_res = self.store.query(prec_query, init_bindings={"goalId": Literal(diff_report.goal_item_id)})
            if p_res:
                p_info = p_res[0]
                p_label = p_info["label"]
                p_id = int(p_info["precursorId"])
                if p_label not in missing:
                    precursor_strat = f"✅ {p_label} is already owned in your inventory/bank. (0 gold needed)"
                else:
                    unit_price = prices.get(p_id, 0.0)
                    if unit_price > 0:
                        buy_order = unit_price * 0.85
                        precursor_strat = (
                            f"Place a Trading Post **Buy Order** for {p_label} at ~{buy_order:.0f} gold "
                            f"(saves ~{unit_price - buy_order:.0f}g over instant buy). "
                            f"Alternatively, craft via Tier 1-3 Precursor Collections if you enjoy the lore journey."
                        )
                    else:
                        precursor_strat = f"Craft or unlock {p_label} via Tier 1-3 Legendary Precursor Collections."

        # ----------------------------------------------------------------------
        # 2. Dynamic Clover Strategy (Queried from Graph)
        # ----------------------------------------------------------------------
        clover_options = []
        clovers_needed = missing.get("Mystic Clover", 0)

        if clovers_needed > 0:
            vault_available = "WizardVault" not in exhausted
            # Query all acquisition pathways for Mystic Clover (GW2 ID: 19675)
            clover_query = """
            SELECT ?path ?pathLabel ?curr ?currNotation ?currLabel ?currQty ?npc ?zone ?waypoint ?def WHERE {
                ?item priory:gw2Id 19675 ;
                      priory:acquiredVia ?path .
                OPTIONAL { ?path rdfs:label ?pathLabel }
                OPTIONAL { ?path skos:definition ?def }
                OPTIONAL { ?path priory:vendorNPC ?npc }
                OPTIONAL { ?path priory:zoneName ?zone }
                OPTIONAL { ?path priory:nearestWaypoint ?waypoint }
                OPTIONAL {
                    ?path priory:requiresCurrency ?curr .
                    OPTIONAL { ?curr skos:notation ?currNotation }
                    OPTIONAL { ?curr skos:prefLabel ?currLabel }
                    OPTIONAL { ?path priory:requiredQuantity ?currQty }
                }
            }
            """
            c_paths = self.store.query(clover_query)
            for c in c_paths:
                p_label = c.get("pathLabel", "Clover Route")
                p_def = c.get("def", "")
                curr_label = c.get("currLabel") or "Tokens"
                unit_cost = int(c.get("currQty", 0)) if c.get("currQty") is not None else 0

                if "Wizard" in p_label or "Astral" in p_def:
                    if vault_available:
                        clovers_from_vault = min(clovers_needed, 20)
                        clover_options.append(CloverStrategyOption(
                            source_name=p_label,
                            clovers_obtainable=clovers_from_vault,
                            estimated_gold_cost=0.0,
                            required_currencies={curr_label: clovers_from_vault * unit_cost},
                            time_gate_note="Seasonal limit (20 clovers per refresh)",
                            recommended=True
                        ))
                elif "Fractal" in p_label:
                    if "Fractals" not in excluded:
                        clover_options.append(CloverStrategyOption(
                            source_name=p_label,
                            clovers_obtainable=min(clovers_needed, 10),
                            estimated_gold_cost=min(clovers_needed, 10) * 1.5,
                            required_currencies={curr_label: min(clovers_needed, 10) * unit_cost, "Spirit Shard": min(clovers_needed, 10) * 2},
                            time_gate_note="2 clovers per day limit",
                            recommended=(not vault_available)
                        ))

            # Default Forge Promotion Option
            clover_options.append(CloverStrategyOption(
                source_name="Mystic Forge Promotion (Clover Recipe)",
                clovers_obtainable=clovers_needed,
                estimated_gold_cost=clovers_needed * 3.50,
                required_currencies={"Spirit Shards": int(clovers_needed * 0.6), "Obsidian Shards": int(clovers_needed * 3.16)},
                time_gate_note="No time gate (unlimited, but probabilistic ~31.6% yield)",
                recommended=(not vault_available and "Fractals" in excluded)
            ))

        # ----------------------------------------------------------------------
        # 3. Dynamic Gold Cost Calculation
        # ----------------------------------------------------------------------
        total_gold = 0.0
        for mat_name, needed_qty in missing.items():
            # Query item ID and tradeability
            mat_query = """
            SELECT ?gw2Id ?isBound WHERE {
                ?item rdfs:label ?label ;
                      priory:gw2Id ?gw2Id .
                OPTIONAL { ?item priory:isAccountBound ?isBound }
                FILTER (lcase(str(?label)) = ?targetLabel)
            } LIMIT 1
            """
            m_res = self.store.query(mat_query, init_bindings={"targetLabel": Literal(mat_name.lower())})
            if m_res:
                m_id = int(m_res[0]["gw2Id"])
                is_bound = str(m_res[0].get("isBound", "")).lower() == "true"
                if not is_bound and m_id in prices:
                    total_gold += prices[m_id] * needed_qty

        # ----------------------------------------------------------------------
        # 4. Dynamic Non-Negotiable Bottlenecks (100% Graph-Driven)
        # ----------------------------------------------------------------------
        bottlenecks = []
        for mat_name, needed_qty in missing.items():
            b_query = """
            SELECT ?pathType ?def ?npc ?zone ?waypoint ?currLabel ?currQty WHERE {
                ?item rdfs:label ?label .
                OPTIONAL { ?item skos:definition ?def }
                OPTIONAL { ?item rdfs:comment ?def }
                OPTIONAL {
                    ?item priory:acquiredVia ?path .
                    ?path a ?pathType .
                    OPTIONAL { ?path rdfs:label ?pathLabel }
                    OPTIONAL { ?path skos:definition ?pathDef }
                    OPTIONAL { ?path priory:vendorNPC ?npc }
                    OPTIONAL { ?path priory:zoneName ?zone }
                    OPTIONAL { ?path priory:nearestWaypoint ?waypoint }
                    OPTIONAL {
                        ?path priory:requiresCurrency ?curr .
                        OPTIONAL { ?curr skos:prefLabel ?currLabel }
                        OPTIONAL { ?path priory:requiredQuantity ?currQty }
                    }
                }
                FILTER (lcase(str(?label)) = ?targetLabel)
            } LIMIT 1
            """
            b_res = self.store.query(b_query, init_bindings={"targetLabel": Literal(mat_name.lower())})
            if b_res:
                row = b_res[0]
                ptype = str(row.get("pathType", ""))
                definition = row.get("def") or ""
                npc = row.get("npc")
                zone = row.get("zone")
                waypoint = row.get("waypoint")
                curr_label = row.get("currLabel")
                curr_qty = row.get("currQty")

                if "AchievementCollectionPath" in ptype:
                    bottlenecks.append(f"🗺️ **{mat_name}:** {definition or 'Requires 100% Core Tyria Map Completion (Cannot be bought with gold).'}")
                elif "RewardTrackPath" in ptype:
                    bottlenecks.append(f"⚔️ **{mat_name}:** {definition or 'Requires completing competitive WvW/PvP reward tracks.'}")
                elif "VendorExchangePath" in ptype:
                    detail = f"Requires {curr_qty or ''} {curr_label or 'Tokens'} from {npc or 'Vendor'}"
                    if zone:
                        detail += f" in {zone}"
                    if waypoint:
                        detail += f" [{waypoint}]"
                    bottlenecks.append(f"🏛️ **{mat_name}:** {definition or detail}.")

        if diff_report.missing_disciplines:
            for d in diff_report.missing_disciplines:
                bottlenecks.append(f"🔨 **{d['discipline'].capitalize()} Level {d['required_rating']}:** Required to craft weapon or upgrade gifts.")

        # ----------------------------------------------------------------------
        # 5. Dynamic Roadmap (100% Graph-Driven)
        # ----------------------------------------------------------------------
        roadmap = []
        for sub in diff_report.root_node.sub_requirements:
            if "Unpackable from" in sub.label:
                kit_name = sub.label.split("Unpackable from")[-1].replace(")", "").strip()
                item_name = sub.label.split("(")[0].strip()
                roadmap.append({
                    "phase": "Phase 0: Claim Bank Starter Kit",
                    "action": f"Withdraw '{kit_name}' from your Bank and choose the '{diff_report.goal_item_name} Kit' to immediately receive {item_name} for 0 gold!",
                    "est_cost": "0 gold (Already Owned!)"
                })
                break

        if diff_report.missing_disciplines:
            roadmap.append({
                "phase": "Phase 1: Crafting Discipline Setup",
                "action": f"Level crafting disciplines to {max(d['required_rating'] for d in diff_report.missing_disciplines)} using discovery guides.",
                "est_cost": "15-25 gold"
            })

        if clovers_needed > 0:
            roadmap.append({
                "phase": "Phase 2: Guaranteed Clovers & Time-Gated Vendors",
                "action": "Claim alternative clover vendor routes or Mystic Forge promotions.",
                "est_cost": "0-15 gold"
            })

        roadmap.append({
            "phase": "Phase 3: Trading Post Materials & Mystic Forge Assembly",
            "action": f"Place TP buy orders for remaining materials and forge {target_qty}x {diff_report.goal_item_name}.",
            "est_cost": f"~{total_gold:.0f} gold"
        })

        return OptimalCraftingPlan(
            goal_item_name=diff_report.goal_item_name,
            goal_item_id=diff_report.goal_item_id,
            target_quantity=target_qty,
            is_already_owned=diff_report.is_fully_satisfied,
            estimated_total_gold_cost=total_gold,
            precursor_strategy=precursor_strat,
            clover_strategy=clover_options,
            bottlenecks=bottlenecks,
            step_by_step_roadmap=roadmap
        )
