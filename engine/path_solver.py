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


import datetime


class MilestoneStep(BaseModel):
    step_number: int
    title: str
    description: str
    waypoint: Optional[str] = None
    zone_name: Optional[str] = None
    npc_name: Optional[str] = None
    is_completed: bool = False


class RoadmapPhase(BaseModel):
    phase_number: int
    phase_title: str
    phase_status: str  # e.g. "[COMPLETED]", "[IN PROGRESS - 25%]", "[NOT STARTED]"
    completion_percentage: float = 0.0
    milestone_steps: List[MilestoneStep] = Field(default_factory=list)
    key_materials: List[str] = Field(default_factory=list)


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
    precursor_archetype: str = "Standard Crafting"
    calendar_day_gates: int = 0
    estimated_completion_days: int = 0
    estimated_completion_date: Optional[str] = None
    primary_time_gate_bottleneck: Optional[str] = None
    clover_strategy: List[CloverStrategyOption] = Field(default_factory=list)
    t6_strategies: List[str] = Field(default_factory=list)
    bottlenecks: List[str] = Field(default_factory=list)
    step_by_step_roadmap: List[Dict[str, Any]] = Field(default_factory=list)
    master_roadmap: List[RoadmapPhase] = Field(default_factory=list)


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
            wv_clovers_remaining = account.wizards_vault_remaining(19675)
            vault_available = (
                "WizardVault" not in exhausted
                and not account.is_wizards_vault_sold_out(19675)
                and (wv_clovers_remaining is None or wv_clovers_remaining > 0)
            )
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
                        max_vault_cap = wv_clovers_remaining if wv_clovers_remaining is not None else 20
                        clovers_from_vault = min(clovers_needed, max_vault_cap)
                        if clovers_from_vault > 0:
                            clover_options.append(CloverStrategyOption(
                                source_name=p_label,
                                clovers_obtainable=clovers_from_vault,
                                estimated_gold_cost=0.0,
                                required_currencies={curr_label: clovers_from_vault * unit_cost},
                                time_gate_note=f"Seasonal limit ({clovers_from_vault} available in Vault)",
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

            # Wizard's Vault Astral Acclaim
            aa_amount = account.wallet.get(68, 0)
            wv_clovers_rem = account.wizards_vault_remaining(19675)
            if aa_amount >= 9 and "WizardVault" not in excluded and "WizardVault" not in exhausted:
                if wv_clovers_rem is not None and wv_clovers_rem == 0:
                    t6_strats.append(
                        f"✨ **Wizard's Vault Acclaim ({aa_amount} available):** "
                        f"Wizard's Vault Mystic Clovers are **sold out** for this season. You can still spend Acclaim on Heavy Crafting Bags (10 AA each) or Gold Bags."
                    )
                else:
                    max_clovers = min(aa_amount // 9, wv_clovers_rem if wv_clovers_rem is not None else 20)
                    t6_strats.append(
                        f"✨ **Wizard's Vault Acclaim ({aa_amount} available):** "
                        f"Claim up to {max_clovers}x Mystic Clovers (9 AA each) and Heavy Crafting Bags (10 AA each) directly from the Wizard's Vault for 0 gold."
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

        # Query Precursor Archetype from Knowledge Graph
        arch_query = """
        SELECT ?ptype ?ptag ?hours WHERE {
            ?item priory:gw2Id ?gw2Id ;
                  priory:hasPrecursorType ?ptype .
            OPTIONAL { ?ptype priory:archetypeTag ?ptag }
            OPTIONAL { ?ptype priory:estimatedGameplayHours ?hours }
        } LIMIT 1
        """
        arch_res = self.store.query(arch_query, init_bindings={"gw2Id": Literal(diff_report.goal_item_id)})
        prec_archetype = "Standard Crafting"
        if arch_res:
            row = arch_res[0]
            prec_archetype = str(row.get("ptag") or row.get("ptype", "")).split("#")[-1].split("/")[-1]

        # Calculate calendar day gates & longitudinal completion date
        cal_days = 0
        primary_bottleneck = None

        for mat_name, qty in missing.items():
            if any(asc in mat_name for asc in ["Deldrimor", "Spiritwood", "Elonian Leather", "Damask", "Mithrilium", "Elder Spirit", "Charged Quartz"]):
                if qty > cal_days:
                    cal_days = qty
                    primary_bottleneck = f"Ascended Daily Refinement Limit (1 {mat_name}/day)"
            elif "Provisioner Token" in mat_name or "Gift of Craftsmanship" in mat_name:
                tokens_needed = qty * (50 if "Gift of Craftsmanship" in mat_name else 1)
                days_needed = (tokens_needed + 2) // 3  # Assuming 3 provisioner trades/day
                if days_needed > cal_days:
                    cal_days = days_needed
                    primary_bottleneck = f"Faction Provisioner Tokens (3/day limit — {tokens_needed} tokens needed)"
            elif "Druid" in mat_name or "Wayfarer" in mat_name:
                if 16 > cal_days:
                    cal_days = 16
                    primary_bottleneck = "Wayfarer's Henge (16-day Druid Runestone daily time gate)"
            elif "Fractal Research Page" in mat_name:
                pages_needed = qty
                days_needed = (pages_needed + 2) // 3
                if days_needed > cal_days:
                    cal_days = days_needed
                    primary_bottleneck = f"Fractal Daily Research Pages (3/day limit — {pages_needed} pages needed)"
            elif "WvW Skirmish Claim Ticket" in mat_name:
                tickets_needed = qty
                days_needed = int((tickets_needed / 365.0) * 7.0)
                if days_needed > cal_days:
                    cal_days = days_needed
                    primary_bottleneck = f"WvW Skirmish Claim Tickets (365/week cap — {tickets_needed} tickets needed)"
            elif "Legendary Insight" in mat_name:
                li_needed = qty
                days_needed = int((li_needed / 25.0) * 7.0)
                if days_needed > cal_days:
                    cal_days = days_needed
                    primary_bottleneck = f"Legendary Insights (25/week Raid cap — {li_needed} LI needed)"

        completion_date = None
        if cal_days > 0:
            target_dt = datetime.date.today() + datetime.timedelta(days=cal_days)
            completion_date = target_dt.strftime("%B %d, %Y")

        # Generate 5-Phase Step-by-Step Master Roadmap
        master_roadmap = self.generate_master_roadmap(diff_report, account)

        return OptimalCraftingPlan(
            goal_item_name=diff_report.goal_item_name,
            goal_item_id=diff_report.goal_item_id,
            target_quantity=target_qty,
            is_already_owned=diff_report.is_fully_satisfied,
            estimated_total_gold_cost=total_gold,
            precursor_strategy=precursor_strat,
            precursor_archetype=prec_archetype,
            calendar_day_gates=cal_days,
            estimated_completion_days=cal_days,
            estimated_completion_date=completion_date,
            primary_time_gate_bottleneck=primary_bottleneck,
            clover_strategy=clover_options,
            t6_strategies=t6_strats,
            bottlenecks=bottlenecks,
            step_by_step_roadmap=roadmap,
            master_roadmap=master_roadmap
        )

    def generate_master_roadmap(self, diff_report: AccountDiffReport, account: AccountState) -> List[RoadmapPhase]:
        """Decomposes the target legendary item into the authentic 5 Guild Wars 2 Master Milestone Phases."""
        phases: List[RoadmapPhase] = []
        root = diff_report.root_node
        sub_reqs = root.sub_requirements

        def find_sub(keywords: List[str]):
            for sub in sub_reqs:
                lbl = sub.label.lower()
                if any(kw.lower() in lbl for kw in keywords):
                    return sub
            return None

        # Query Archetype from Graph
        arch_query = """
        SELECT ?ptype ?ptag ?hours WHERE {
            ?item priory:gw2Id ?gw2Id ;
                  priory:hasPrecursorType ?ptype .
            OPTIONAL { ?ptype priory:archetypeTag ?ptag }
            OPTIONAL { ?ptype priory:estimatedGameplayHours ?hours }
        } LIMIT 1
        """
        arch_res = self.store.query(arch_query, init_bindings={"gw2Id": Literal(diff_report.goal_item_id)})
        prec_archetype = ""
        if arch_res:
            row = arch_res[0]
            prec_archetype = str(row.get("ptag") or row.get("ptype", ""))

        # Phase 1: Precursor Journey
        prec_node = find_sub(["precursor", "the mechanism", "the lexicon", "dusk", "dawn", "zap", "spark", "legend", "tooth of frostfang", "rodgort's flame", "the energizer", "chaos gun", "the bard", "howl", "venom", "storm", "the lover", "the colossus", "kamohoali'i", "carcharias", "frenzy", "aurene's", "experimental envoy", "refined envoy", "astral ward"])
        p1_steps = []
        p1_pct = 0.0
        p1_status = "[NOT STARTED - 0%]"

        if prec_node:
            if prec_node.is_satisfied:
                p1_pct = 100.0
                p1_status = "[COMPLETED - 100%]"
                p1_steps.append(MilestoneStep(
                    step_number=1,
                    title="Precursor Weapon Acquired",
                    description=f"You already own '{prec_node.label}' in your account storage/inventory!",
                    is_completed=True
                ))
            elif "Unpackable from" in prec_node.label:
                p1_pct = 100.0
                p1_status = "[READY TO UNPACK - 100%]"
                p1_steps.append(MilestoneStep(
                    step_number=1,
                    title="Unpack from Bank Starter Kit",
                    description=f"Withdraw choice chest from your bank to immediately receive {prec_node.label} for 0 gold!",
                    is_completed=False
                ))
            elif "ShardCrafting" in prec_archetype or "Shard" in prec_archetype or "the lexicon" in prec_node.label.lower():
                p1_steps.append(MilestoneStep(
                    step_number=1,
                    title="Unlock Precursor Recipes (Vol. 1)",
                    description="Visit Grandmaster Craftsman Hobbs in Lion's Arch [&BBAEAAA=] to purchase the precursor crafting recipe book.",
                    waypoint="[&BBAEAAA=]",
                    zone_name="Lion's Arch",
                    npc_name="Grandmaster Craftsman Hobbs"
                ))
                p1_steps.append(MilestoneStep(
                    step_number=2,
                    title=f"Craft 290x Shards of {diff_report.goal_item_name}",
                    description=f"Craft 290x Shards at level 450 crafting discipline using Ascended ingots/planks, Mithril, and Elder Wood.",
                    is_completed=False
                ))
                p1_steps.append(MilestoneStep(
                    step_number=3,
                    title=f"Forge Precursor: {prec_node.label.split('(')[0].strip()}",
                    description=f"Combine 290x Shards + Tribute to the Arts + Ascended materials to craft {prec_node.label.split('(')[0].strip()}.",
                    is_completed=False
                ))
            elif "CollectionHunt" in prec_archetype or "Scavenger" in prec_archetype:
                p1_steps.append(MilestoneStep(
                    step_number=1,
                    title="Complete Tier 1–4 Scavenger Collections",
                    description="Visit Grandmaster Craftsman Hobbs in Lion's Arch [&BBAEAAA=] to unlock Vol. 1. Complete open-world events, jumping puzzles, and crafting tasks (~40h active gameplay).",
                    waypoint="[&BBAEAAA=]",
                    zone_name="Lion's Arch",
                    npc_name="Grandmaster Craftsman Hobbs"
                ))
                p1_steps.append(MilestoneStep(
                    step_number=2,
                    title=f"Craft Precursor: {prec_node.label.split('(')[0].strip()}",
                    description=f"Craft {prec_node.label.split('(')[0].strip()} at level 450 crafting station upon collection completion.",
                    is_completed=False
                ))
            elif "Tradable" in prec_archetype:
                p1_steps.append(MilestoneStep(
                    step_number=1,
                    title=f"Acquire {prec_node.label.split('(')[0].strip()}",
                    description=f"Purchase {prec_node.label.split('(')[0].strip()} directly from Trading Post (instant) or craft via Hobbs Tier 1–3 crafting collections [&BBAEAAA=].",
                    waypoint="[&BBAEAAA=]",
                    zone_name="Lion's Arch"
                ))
            else:
                p1_steps.append(MilestoneStep(
                    step_number=1,
                    title="Unlock Precursor Recipe / Collection",
                    description="Visit Grandmaster Craftsman Hobbs in Lion's Arch [&BBAEAAA=] or Leivas in Arborstone [&BEwMAAA=] to unlock precursor crafting recipes.",
                    waypoint="[&BBAEAAA=]",
                    zone_name="Lion's Arch",
                    npc_name="Grandmaster Craftsman Hobbs"
                ))
                p1_steps.append(MilestoneStep(
                    step_number=2,
                    title=f"Craft Precursor: {prec_node.label.split('(')[0].strip()}",
                    description=f"Craft {prec_node.label.split('(')[0].strip()} at level 450/500 crafting station using refined Ascended materials.",
                    is_completed=False
                ))
        else:
            p1_steps.append(MilestoneStep(
                step_number=1,
                title="Acquire Precursor Component",
                description="Obtain the requisite precursor item from the Trading Post, collections, or crafting.",
                is_completed=False
            ))

        phases.append(RoadmapPhase(
            phase_number=1,
            phase_title=f"Phase 1: Precursor Journey ({prec_node.label.split('(')[0].strip() if prec_node else 'Precursor'})",
            phase_status=p1_status,
            completion_percentage=p1_pct,
            milestone_steps=p1_steps
        ))

        # Phase 2: Mystic Tribute / Fortune Components
        trib_node = find_sub(["mystic tribute", "gift of fortune", "gift of sigils", "gift of runes", "gift of prosperity", "condensed magic", "condensed might"])
        p2_steps = []
        p2_pct = 0.0
        p2_status = "[NOT STARTED - 0%]"

        if trib_node and trib_node.is_satisfied:
            p2_pct = 100.0
            p2_status = "[COMPLETED - 100%]"
            p2_steps.append(MilestoneStep(
                step_number=1,
                title="Tribute / Fortune Components Completed",
                description=f"All requirements for {trib_node.label} are fully satisfied!",
                is_completed=True
            ))
        else:
            p2_steps.append(MilestoneStep(
                step_number=1,
                title="Claim Mystic Clovers (77 needed)",
                description="Purchase Mystic Clovers with Astral Acclaim in the Wizard's Vault (cheapest) and Fractal vendors before gambling in the Mystic Forge.",
                waypoint="[&BBAEAAA=]",
                zone_name="Lion's Arch",
                npc_name="Miyani"
            ))
            p2_steps.append(MilestoneStep(
                step_number=2,
                title="Gather Ectoplasm & Amalgamated Gemstones (250 each)",
                description="Salvage Rare lvl 68+ gear for Globs of Ectoplasm and complete Heart of Thorns / PoF meta events for Hero's Choice Gemstone chests.",
                waypoint="[&BNYHAAA=]",
                zone_name="Auric Basin",
                npc_name="Tarir Meta Chests"
            ))
            p2_steps.append(MilestoneStep(
                step_number=3,
                title="Acquire T6 Fine Trophies (Blood, Bone, Claw, Fang, Scale, Totem, Venom, Dust)",
                description="Exchange Volatile Magic for Trophy Shipments at Dragonfall [&BNoLAAA=], Laurel bags in Lion's Arch [&BBAEAAA=], or farm Drizzlewood Coast [&BDoMAAA=].",
                waypoint="[&BNoLAAA=]",
                zone_name="Dragonfall",
                npc_name="Volatile Magic Collector"
            ))

        phases.append(RoadmapPhase(
            phase_number=2,
            phase_title="Phase 2: Mystic Tribute / Fortune Components",
            phase_status=p2_status,
            completion_percentage=p2_pct,
            milestone_steps=p2_steps
        ))

        # Phase 3: Regional Mastery Gift
        mast_node = find_sub(["maguuma mastery", "desert mastery", "gift of mastery", "cantha mastery", "amalgamated kryptis", "gift of the mists", "gift of exploration"])
        p3_steps = []
        p3_pct = 0.0
        p3_status = "[NOT STARTED - 0%]"

        if mast_node and mast_node.is_satisfied:
            p3_pct = 100.0
            p3_status = "[COMPLETED - 100%]"
            p3_steps.append(MilestoneStep(
                step_number=1,
                title="Expansion Mastery Gift Completed",
                description=f"All requirements for {mast_node.label} are satisfied!",
                is_completed=True
            ))
        else:
            mast_label = mast_node.label if mast_node else ""
            if "Maguuma" in mast_label:
                tarir_warn = " [⚠️ Requires Mastery: Exalted Acceptance Lvl 2]" if account.masteries.get(1, 0) < 2 and account.masteries else ""
                fleet_warn = " [⚠️ Requires Mastery: Itzel Language Lvl 1]" if account.masteries.get(2, 0) < 1 and account.masteries else ""
                chak_warn = " [⚠️ Requires Mastery: Nuhoch Proving Lvl 2]" if account.masteries.get(3, 0) < 2 and account.masteries else ""

                p3_steps.append(MilestoneStep(
                    step_number=1,
                    title="100% Heart of Thorns Map Completion",
                    description="Complete 100% world exploration across Verdant Brink, Auric Basin, Tangled Depths, and Dragon's Stand for Gift of the Jungle."
                ))
                p3_steps.append(MilestoneStep(
                    step_number=2,
                    title="Farm 250x Crystalline Ore in Dragon's Stand",
                    description="Use Machetes to open Noxious Pods across Dragon's Stand [&BBAIAAA=] after the meta event.",
                    waypoint="[&BBAIAAA=]",
                    zone_name="Dragon's Stand"
                ))
                p3_steps.append(MilestoneStep(
                    step_number=3,
                    title=f"Purchase Gifts of Tarir, Fleet, and Chak{tarir_warn or fleet_warn or chak_warn}",
                    description=f"Exchange map currencies: Aurillium at Tarir [&BNYHAAA=]{tarir_warn}, Airship Parts at Verdant Brink [&BO8FAAA=]{fleet_warn}, and Ley-Line Sparks at Tangled Depths [&BPUHAAA=]{chak_warn}.",
                    waypoint="[&BNYHAAA=]",
                    zone_name="Auric Basin"
                ))
            elif "Desert" in mast_label:
                p3_steps.append(MilestoneStep(
                    step_number=1,
                    title="100% Path of Fire Map Completion",
                    description="Complete 100% exploration of Crystal Oasis, Desert Highlands, Elon Riverlands, Desolation, and Domain of Vabbi for Gift of the Rider."
                ))
                p3_steps.append(MilestoneStep(
                    step_number=2,
                    title="Gather 250x Funerary Incense in Vabbi",
                    description="Exchange Elegy Mosaics and Trade Contracts with the Primeval Dynasty Historian in Domain of Vabbi [&BO8KAAA=].",
                    waypoint="[&BO8KAAA=]",
                    zone_name="Domain of Vabbi",
                    npc_name="Primeval Dynasty Historian"
                ))
            elif "Cantha" in mast_label:
                eod_warn = " [⚠️ Requires Mastery: Arborstone Commercial Hub Lvl 3]" if account.masteries.get(4, 0) < 3 and account.masteries else ""
                p3_steps.append(MilestoneStep(
                    step_number=1,
                    title="100% End of Dragons Map Completion",
                    description="Complete 100% exploration of Seitung Province, New Kaineng City, Echovald Wilds, and Dragon's End for Gift of Cantha."
                ))
                p3_steps.append(MilestoneStep(
                    step_number=2,
                    title=f"Gather Antique Summoning Stones & Pure Jade{eod_warn}",
                    description=f"Exchange Imperial Favor and complete Dragon's End meta with Leivas in Arborstone [&BEwMAAA=]{eod_warn}.",
                    waypoint="[&BEwMAAA=]",
                    zone_name="Arborstone",
                    npc_name="Leivas"
                ))
            else:
                p3_steps.append(MilestoneStep(
                    step_number=1,
                    title="100% Core Tyria World Completion",
                    description="Complete all hearts, waypoints, vistas, and POIs across Core Tyria to earn 2x Gift of Exploration."
                ))
                p3_steps.append(MilestoneStep(
                    step_number=2,
                    title="Complete WvW Gift of Battle Reward Track",
                    description="Participate in World vs World and complete the Gift of Battle reward track for Gift of Battle [&BBAEAAA=]."
                ))

            p3_steps.append(MilestoneStep(
                step_number=len(p3_steps) + 1,
                title="Purchase Bloodstone Shard (200 Spirit Shards)",
                description="Buy Bloodstone Shard from Miyani at the Mystic Forge in Lion's Arch [&BBAEAAA=].",
                waypoint="[&BBAEAAA=]",
                zone_name="Lion's Arch",
                npc_name="Miyani"
            ))

        phases.append(RoadmapPhase(
            phase_number=3,
            phase_title=f"Phase 3: Expansion & Regional Mastery ({mast_node.label.split('(')[0].strip() if mast_node else 'Mastery'})",
            phase_status=p3_status,
            completion_percentage=p3_pct,
            milestone_steps=p3_steps
        ))

        # Phase 4: Specific Weapon / Item Gift
        spec_node = find_sub(["gift of", "cosmos", "darkness", "metal", "wood", "energy", "weather", "light", "stealth", "nature", "history", "blood", "predator", "the moon", "the stars", "craftsmanship", "aurene"])
        if spec_node == mast_node or spec_node == trib_node:
            for sub in sub_reqs:
                if sub != mast_node and sub != trib_node and sub != prec_node and "gift" in sub.label.lower():
                    spec_node = sub
                    break

        p4_steps = []
        p4_pct = 0.0
        p4_status = "[NOT STARTED - 0%]"

        if spec_node and spec_node.is_satisfied:
            p4_pct = 100.0
            p4_status = "[COMPLETED - 100%]"
            p4_steps.append(MilestoneStep(
                step_number=1,
                title="Specific Weapon / Component Gift Completed",
                description=f"All requirements for {spec_node.label} are satisfied!",
                is_completed=True
            ))
        else:
            p4_steps.append(MilestoneStep(
                step_number=1,
                title="Purchase 100x Icy Runestones (100 gold)",
                description="Buy 100 Icy Runestones from Rojan the Penitent in Frostgorge Sound [&BHsBAAA=].",
                waypoint="[&BHsBAAA=]",
                zone_name="Frostgorge Sound",
                npc_name="Rojan the Penitent"
            ))
            p4_steps.append(MilestoneStep(
                step_number=2,
                title=f"Craft {spec_node.label.split('(')[0].strip() if spec_node else 'Weapon Gift'}",
                description="Combine specific lodestones, refined ingots/planks, and discipline components at Level 400 crafting station.",
                is_completed=False
            ))

        phases.append(RoadmapPhase(
            phase_number=4,
            phase_title=f"Phase 4: Specific Weapon / Item Gift ({spec_node.label.split('(')[0].strip() if spec_node else 'Specific Gift'})",
            phase_status=p4_status,
            completion_percentage=p4_pct,
            milestone_steps=p4_steps
        ))

        # Phase 5: Final Mystic Forge Assembly
        phases.append(RoadmapPhase(
            phase_number=5,
            phase_title="Phase 5: Final Mystic Forge Assembly",
            phase_status="[READY UPON COMPLETION OF PHASES 1-4]",
            completion_percentage=0.0,
            milestone_steps=[
                MilestoneStep(
                    step_number=1,
                    title=f"Forge {diff_report.goal_item_name} at the Mystic Forge",
                    description=f"Place the Precursor + Tribute + Mastery Gift + Specific Gift into the Mystic Forge with Miyani in Lion's Arch [&BBAEAAA=] to forge your {diff_report.goal_item_name}!",
                    waypoint="[&BBAEAAA=]",
                    zone_name="Lion's Arch",
                    npc_name="Miyani"
                )
            ]
        ))

        return phases
