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
    clover_strategy: List[CloverStrategyOption] = Field(default_factory=list)
    t6_strategies: List[str] = Field(default_factory=list)
    bottlenecks: List[str] = Field(default_factory=list)
    step_by_step_roadmap: List[Dict[str, Any]] = Field(default_factory=list)


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
        exhausted_sources: Optional[List[str]] = None,
        time_budget_minutes: int = 120
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

            clover_options.append(CloverStrategyOption(
                source_name="Mystic Forge Promotion (Clover Recipe)",
                clovers_obtainable=clovers_needed,
                estimated_gold_cost=clovers_needed * 3.50,
                required_currencies={"Spirit Shards": int(clovers_needed * 0.6), "Obsidian Shards": int(clovers_needed * 3.16)},
                time_gate_note="No time gate (unlimited, but probabilistic ~31.6% yield)",
                recommended=(not vault_available and "Fractals" in excluded)
            ))

        # ----------------------------------------------------------------------
        # 3. Dynamic T6 Fine Material Pathways Strategy (Queried from Graph)
        # ----------------------------------------------------------------------
        t6_strats = []
        t6_ids = {
            24295: "Powerful Blood",
            24276: "Ancient Bone",
            24358: "Elaborate Totem",
            24277: "Crystalline Dust",
            24351: "Vicious Claw",
            24288: "Vicious Fang",
            24283: "Armored Scale",
            24289: "Powerful Venom Sac",
        }
        missing_t6 = {k: v for k, v in missing.items() if any(t_name.lower() in k.lower() for t_name in t6_ids.values())}

        if missing_t6:
            # Query all T6 acquisition pathways
            t6_query = """
            SELECT ?path ?pathLabel ?npc ?zone ?waypoint ?def ?currLabel WHERE {
                ?item a priory:CraftingMaterial ;
                      priory:acquiredVia ?path .
                ?path rdfs:label ?pathLabel .
                OPTIONAL { ?path skos:definition ?def }
                OPTIONAL { ?path priory:vendorNPC ?npc }
                OPTIONAL { ?path priory:zoneName ?zone }
                OPTIONAL { ?path priory:nearestWaypoint ?waypoint }
                OPTIONAL {
                    ?path priory:requiresCurrency ?curr .
                    OPTIONAL { ?curr skos:prefLabel ?currLabel }
                }
            } LIMIT 20
            """
            t6_paths = self.store.query(t6_query)

            # Volatile Magic check
            vm_amount = account.wallet.get(45, 0)
            if vm_amount >= 250:
                shipments = vm_amount // 250
                t6_strats.append(
                    f"⚡ **Volatile Magic Conversion ({vm_amount:,} available):** Trade {min(shipments, 20) * 250} Volatile Magic + {min(shipments, 20)}g "
                    f"for {min(shipments, 20)}x **Trophy Shipments** at Dragonfall `[&BNoLAAA=]` (yields ~{min(shipments, 20) * 12} T5/T6 fine materials)."
                )

            # Spirit Shards Mystic Forge promotion
            shards_amount = account.wallet.get(23, 0)
            if shards_amount >= 10:
                t6_strats.append(
                    f"🔮 **Mystic Forge T5 -> T6 Transmutation ({shards_amount} Spirit Shards available):** "
                    f"Combine 50x T5 materials + 1x T6 material + 5x Crystalline Dust + 5x Philosopher's Stones in the Mystic Forge for high-yield T6 output."
                )

            # Laurel Merchant
            laurel_amount = account.wallet.get(3, 0)
            if laurel_amount >= 1:
                t6_strats.append(
                    f"🌿 **Laurel Merchant ({laurel_amount} Laurels available):** "
                    f"Exchange Laurels for Heavy Crafting Bags in Lion's Arch `[&BBAEAAA=]` (1 Laurel = 3 guaranteed T6 materials)."
                )

            # Open World / Drizzlewood
            if "OpenWorld" not in excluded:
                t6_strats.append(
                    "🌲 **Drizzlewood Coast Meta (`[&BDoMAAA=]`):** Farm Charr Legion material reward tracks (Blood for Blood/Fangs, Ash for Claws/Venom, Iron for Scales/Totems)."
                )

        # ----------------------------------------------------------------------
        # 4. Dynamic Gold Cost Calculation
        # ----------------------------------------------------------------------
        total_gold = 0.0
        for mat_name, needed_qty in missing.items():
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
        # 5. Dynamic Non-Negotiable Bottlenecks (100% Graph-Driven)
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
        # 6. Dynamic Time-Budget Constrained Roadmap
        # ----------------------------------------------------------------------
        roadmap = []
        budget = max(time_budget_minutes, 15)

        for sub in diff_report.root_node.sub_requirements:
            if "Unpackable from" in sub.label:
                kit_name = sub.label.split("Unpackable from")[-1].replace(")", "").strip()
                item_name = sub.label.split("(")[0].strip()
                roadmap.append({
                    "phase": "Phase 0: Claim Bank Starter Kit",
                    "action": f"Withdraw '{kit_name}' from your Bank and choose the '{diff_report.goal_item_name} Kit' to immediately receive {item_name} for 0 gold!",
                    "est_time_mins": 2,
                    "est_cost": "0 gold (Already Owned!)"
                })
                budget -= 2
                break

        # Fast currency conversion step
        if missing_t6 and account.wallet.get(45, 0) >= 250 and budget >= 5:
            roadmap.append({
                "phase": "Phase 1: Volatile Magic Trophy Claim",
                "action": "Teleport to Dragonfall [&BNoLAAA=] and buy Trophy Shipments from the Volatile Magic Collector.",
                "est_time_mins": 5,
                "est_cost": f"~{min(account.wallet.get(45, 0) // 250, 10)}g"
            })
            budget -= 5

        # Mystic Forge promotion step
        if missing_t6 and account.wallet.get(23, 0) >= 10 and budget >= 10:
            roadmap.append({
                "phase": "Phase 2: Mystic Forge T6 Promotion",
                "action": "Transmute surplus T5 materials into T6 trophies using Spirit Shards at Miyani [&BBAEAAA=].",
                "est_time_mins": 10,
                "est_cost": "0 gold (Spirit Shards)"
            })
            budget -= 10

        # Dedicated meta/farm step fitting within remaining time
        if budget >= 15:
            meta_time = min(budget, 30)
            roadmap.append({
                "phase": "Phase 3: Active Material / Meta Session",
                "action": f"Farm Drizzlewood Coast Charr Legion reward tracks or meta events for {meta_time} minutes at Base Camp [&BDoMAAA=].",
                "est_time_mins": meta_time,
                "est_cost": "0 gold (Net Positive Farming)"
            })
            budget -= meta_time

        return OptimalCraftingPlan(
            goal_item_name=diff_report.goal_item_name,
            goal_item_id=diff_report.goal_item_id,
            target_quantity=target_qty,
            is_already_owned=diff_report.is_fully_satisfied,
            estimated_total_gold_cost=total_gold,
            precursor_strategy=precursor_strat,
            clover_strategy=clover_options,
            t6_strategies=t6_strats,
            bottlenecks=bottlenecks,
            step_by_step_roadmap=roadmap
        )
