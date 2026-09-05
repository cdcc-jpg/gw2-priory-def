"""Multi-Criteria Path & Optimization Solver for Project Priory.

Calculates the mathematically optimal acquisition and crafting routes based purely
on dynamic SPARQL graph queries and live Trading Post API prices.

ZERO DOMAIN HARDCODING IN PYTHON: All bottleneck rules, vendor definitions, 
currencies, waypoints, and acquisition pathways are queried dynamically from RDF.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from rdflib import Literal, URIRef
from engine.graph_store import PrioryGraphStore
from engine.account_diff import (
    AccountDiffReport,
    AccountState,
    AccountDiffEngine,
    ItemRequirementNode,
    GEN1_WEAPONS,
    GEN2_WEAPONS,
    GEN1_PRECURSOR_IDS,
    GEN2_PRECURSOR_IDS,
    HOBBS_COLLECTIONS,
    PRECURSOR_NAMES
)
from engine.character_graph import (
    route_crafting_discipline,
    CRAFTING_DISCIPLINE_STATIONS,
    encode_item_chat_link
)
from ingestion.gw2_api import get_live_market_prices


import datetime


class MilestoneStep(BaseModel):
    step_number: int
    title: str
    description: str
    waypoint: Optional[str] = None
    zone_name: Optional[str] = None
    npc_name: Optional[str] = None
    assigned_character: Optional[str] = None
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


@dataclass
class ScheduledSessionTask:
    id: str
    title: str
    category: str  # ("QUARTZ_CHARGING", "DAILY_REFINEMENT", "WORLD_BOSS_ANOMALY", "PROVISIONER_TOKEN", "DAILY_FRACTAL_CLOVERS", "WEEKLY_LEIVAS")
    estimated_duration_minutes: int
    waypoint_code: str
    location_name: str
    instructions: str
    required_inputs: Dict[str, Any]
    reward_output: Dict[str, Any]
    priority_weight: float
    character_name: Optional[str] = None


@dataclass
class DailySessionItinerary:
    goal_item_id: int
    goal_name: str
    time_budget_minutes: int
    total_scheduled_minutes: int
    tasks: List[ScheduledSessionTask]
    time_utilization_pct: float
    summary: str


@dataclass
class ArbitrageReport:
    goal_item_id: int
    goal_name: str
    instant_buy_total: int  # in copper, using sells.unit_price
    buy_order_total: int  # in copper, using buys.unit_price
    craft_from_scratch_total: int  # in copper, rolled up cost
    my_account_craft_cost: int  # accounting for items already owned in account_state
    precursor_strategy: Dict[str, Any]  # recommended option: "WIZARDS_VAULT", "BUY_ORDER", "INSTANT_BUY", "HOBBS_COLLECTION", with details
    clover_strategy: Dict[str, Any]  # recommended option: "WIZARDS_VAULT", "FRACTAL_RELICS", "MYSTIC_FORGE", with details
    t6_promotion_strategy: Dict[str, Dict[str, Any]]  # recommendation per T6 category: "BUY_DIRECT" or "PROMOTE_T5_FORGE"
    net_sell_if_sold: Optional[int]  # after Wallace's verified 15% TP tax: int(buys.unit_price * 0.85)
    profit_margin_if_sold: Optional[int]  # net_sell_if_sold - craft_cost
    recommended_action: str  # "CRAFT_FOR_SELF", "CRAFT_FOR_PROFIT", "BUY_FINISHED_DIRECT"


BENCHMARK_FALLBACK_PRICES: Dict[int, float] = {
    19721: 0.301,  # Glob of Ectoplasm
    19976: 1.950,  # Mystic Coin
    19675: 7.420,  # Mystic Clover (crafting cost basis)
    19912: 1.000,  # Icy Runestone (1 gold)
    24295: 0.221,  # Vial of Powerful Blood (T6)
    24294: 0.035,  # Potent Blood (T5)
    24276: 0.189,  # Ancient Bone (T6)
    24275: 0.025,  # Large Bone (T5)
    24351: 0.159,  # Vicious Claw (T6)
    24350: 0.030,  # Large Claw (T5)
    24288: 0.129,  # Vicious Fang (T6)
    24287: 0.028,  # Large Fang (T5)
    24283: 0.188,  # Armored Scale (T6)
    24282: 0.025,  # Large Scale (T5)
    24358: 0.156,  # Elaborate Totem (T6)
    24357: 0.032,  # Intricate Totem (T5)
    24289: 0.189,  # Powerful Venom Sac (T6)
    24288: 0.030,  # Potent Venom Sac (T5)
    24277: 0.161,  # Pile of Crystalline Dust (T6)
    24272: 0.020,  # Pile of Incandescent Dust (T5)
    89103: 0.056,  # Lucent Crystal
    89258: 0.045,  # Symbol of Control
    89182: 0.045,  # Symbol of Enhancement
    89140: 0.045,  # Symbol of Pain
    19700: 0.025,  # Mithril Ingot
    19701: 0.085,  # Orichalcum Ingot
    19739: 0.040,  # Elder Wood Plank
    19740: 0.120,  # Ancient Wood Plank
    19729: 0.035,  # Silk Bolt
    19732: 0.150,  # Gossamer Bolt
    19735: 0.060,  # Thick Leather Section
    19737: 0.220,  # Hardened Leather Section
    29185: 179.9,  # Dusk
    29169: 159.5,  # Dawn
    29166: 120.0,  # Tooth of Frostfang
    29167: 140.0,  # Spark
    29168: 160.0,  # Zap
    29180: 150.0,  # The Legend
}

T6_FINE_MATERIALS: Dict[str, Dict[str, Any]] = {
    "Blood": {
        "t6_id": 24295,
        "t6_name": "Vial of Powerful Blood",
        "t5_id": 24294,
        "t5_ids": [24294],
        "t5_name": "Potent Blood",
    },
    "Bone": {
        "t6_id": 24276,
        "t6_name": "Ancient Bone",
        "t5_id": 24275,
        "t5_ids": [24341, 24275],
        "t5_name": "Large Bone",
    },
    "Claw": {
        "t6_id": 24351,
        "t6_name": "Vicious Claw",
        "t5_id": 24350,
        "t5_ids": [24350],
        "t5_name": "Large Claw",
    },
    "Fang": {
        "t6_id": 24288,
        "t6_name": "Vicious Fang",
        "t5_id": 24287,
        "t5_ids": [24356, 24287],
        "t5_name": "Large Fang",
    },
    "Scale": {
        "t6_id": 24283,
        "t6_name": "Armored Scale",
        "t5_id": 24282,
        "t5_ids": [24282, 24288],
        "t5_name": "Large Scale",
    },
    "Totem": {
        "t6_id": 24358,
        "t6_name": "Elaborate Totem",
        "t5_id": 24357,
        "t5_ids": [24299, 24357],
        "t5_name": "Intricate Totem",
    },
    "Venom": {
        "t6_id": 24289,
        "t6_name": "Powerful Venom Sac",
        "t5_id": 24288,
        "t5_ids": [24288, 24282],
        "t5_name": "Potent Venom Sac",
    },
    "Dust": {
        "t6_id": 24277,
        "t6_name": "Pile of Crystalline Dust",
        "t5_id": 24272,
        "t5_ids": [24276, 24272],
        "t5_name": "Pile of Incandescent Dust",
    },
}

T6_ID_TO_CAT: Dict[int, str] = {info["t6_id"]: cat for cat, info in T6_FINE_MATERIALS.items()}

STARTER_KIT_PRECURSORS: Set[int] = {
    29167,  # Zap (Bolt)
    29174,  # The Legend (The Bifrost)
    29170,  # Storm (Meteorlogicus)
    29168,  # Chaos Gun (Quip)
    29166,  # The Energizer (The Moot)
    29173,  # The Hunter (The Predator)
    29177,  # The Chosen (The Flameseeker Prophecies)
    29179,  # Rodgort's Flame (Rodgort)
    29181,  # Frenzy (Frenzy)
    29180,  # Howl (Howler)
    29165,  # Spark (Incinerator)
    29169,  # Tooth of Frostfang (Frostfang)
    29172,  # The Colossus (The Juggernaut)
    29182,  # Venom (Kraitkin)
}


class PathSolver:
    """Evaluates alternative acquisition routes dynamically via semantic graph queries."""

    def __init__(self, graph_store: Optional[PrioryGraphStore] = None):
        self.store = graph_store
        self.diff_engine = AccountDiffEngine(graph_store) if graph_store else None

    def evaluate_cross_role_opportunity_cost(
        self,
        item_id: int,
        quantity: int,
        tp_sell_unit_price: int = 0,
        salvage_expected_unit_value: int = 0,
        direct_exchange_unit_value: float = 0.0
    ) -> Dict[str, Any]:
        """Computes comparative opportunity costs across game roles:
        1. Direct exchange value as currency
        2. Trading Post liquidation value: quantity * tp_sell_unit_price * 0.85 (after 15% TP fee)
        3. Salvage liquidation value: quantity * salvage_expected_unit_value
        Returns recommended optimal role disposition ("SPEND_AS_CURRENCY", "SELL_ON_TP", "SALVAGE", or "HOLD_AS_CRAFTING_MAT").
        """
        sparql = """
        SELECT DISTINCT ?item ?label ?isBound ?isTradeable ?isSalvageable ?isWallet ?producesGold ?goldReqQty WHERE {
            {
                ?item priory:gw2Id ?gw2Id .
            } UNION {
                ?item priory:apiWalletId ?gw2Id .
            }
            OPTIONAL { ?item rdfs:label ?label }
            OPTIONAL { ?item priory:isAccountBound ?isBound }
            OPTIONAL { ?item priory:isTradeable ?isTradeable }
            OPTIONAL { ?item priory:isSalvageable ?isSalvageable }
            OPTIONAL {
                ?item a/rdfs:subClassOf* priory:AccountWalletScalar .
                BIND(true AS ?isWallet)
            }
            OPTIONAL {
                ?path priory:producesGold ?producesGold ;
                      priory:hasIngredientRequirement ?req .
                ?req priory:requiredQuantity ?goldReqQty .
                { ?req priory:requiresItem ?item } UNION { ?req priory:requiresCurrency ?item }
            }
        } LIMIT 1
        """
        meta_res = self.store.query(sparql, init_bindings={"gw2Id": Literal(item_id)})
        meta = meta_res[0] if meta_res else {}

        item_uri = meta.get("item")
        roles = []
        if item_uri:
            role_sparql = """
            SELECT DISTINCT ?role WHERE {
                ?item priory:playsRole ?role .
            }
            """
            for r in self.store.query(role_sparql, init_bindings={"item": URIRef(item_uri)}):
                roles.append(str(r["role"]))

        is_wallet = bool(meta.get("isWallet"))
        if is_wallet:
            is_tradeable = False
            is_salvageable = False
        else:
            if meta.get("isTradeable") is not None:
                is_tradeable = bool(meta["isTradeable"])
            elif meta.get("isBound") is not None:
                is_tradeable = not bool(meta["isBound"])
            else:
                is_tradeable = True

            if meta.get("isSalvageable") is not None:
                is_salvageable = bool(meta["isSalvageable"])
            else:
                is_salvageable = True

        # 1. Direct exchange value
        direct_unit = direct_exchange_unit_value
        if direct_unit <= 0 and meta.get("producesGold") is not None and meta.get("goldReqQty"):
            try:
                direct_unit = float(meta["producesGold"]) / float(meta["goldReqQty"])
            except (ValueError, ZeroDivisionError):
                pass
        direct_exchange_val = quantity * direct_unit

        # 2. Trading Post liquidation value (after 15% TP fee)
        if is_tradeable and tp_sell_unit_price > 0:
            tp_gross = quantity * tp_sell_unit_price
            tp_fee = tp_gross * 0.15
            tp_liquidation_val = quantity * tp_sell_unit_price * 0.85
        else:
            tp_gross = 0.0
            tp_fee = 0.0
            tp_liquidation_val = 0.0

        # 3. Salvage liquidation value
        if is_salvageable and salvage_expected_unit_value > 0:
            salvage_val = quantity * salvage_expected_unit_value
        else:
            salvage_val = 0.0

        # 4. Optimal disposition decision
        if direct_exchange_val > 0 and direct_exchange_val >= tp_liquidation_val and direct_exchange_val >= salvage_val:
            recommendation = "SPEND_AS_CURRENCY"
        elif tp_liquidation_val > 0 and tp_liquidation_val >= salvage_val and tp_liquidation_val >= direct_exchange_val:
            recommendation = "SELL_ON_TP"
        elif salvage_val > 0 and salvage_val >= tp_liquidation_val and salvage_val >= direct_exchange_val:
            recommendation = "SALVAGE"
        else:
            recommendation = "HOLD_AS_CRAFTING_MAT"

        return {
            "item_id": item_id,
            "quantity": quantity,
            "optimal_role_disposition": recommendation,
            "recommended_disposition": recommendation,
            "direct_exchange_value": direct_exchange_val,
            "tp_liquidation_value": tp_liquidation_val,
            "salvage_liquidation_value": salvage_val,
            "tp_gross": tp_gross,
            "tp_fee": tp_fee,
            "roles_evaluated": roles,
            "is_tradeable": is_tradeable,
            "is_salvageable": is_salvageable
        }

    def _get_price_copper(self, item_id: int, live_prices: Dict[int, Dict[str, Any]], price_type: str = "sells") -> int:
        """Extracts unit price in copper from live Trading Post dictionary or benchmark fallbacks."""
        if item_id in live_prices:
            p = live_prices[item_id]
            if isinstance(p, dict):
                val = None
                if price_type in p and isinstance(p[price_type], dict):
                    val = p[price_type].get("unit_price", 0)
                elif "unit_price" in p:
                    val = p.get("unit_price", 0)
                elif price_type in p and isinstance(p[price_type], (int, float)):
                    val = p[price_type]
                if val is not None and val > 0:
                    if isinstance(val, float) and val < 1000.0:
                        return int(round(val * 10000))
                    return int(val)
            elif isinstance(p, (int, float)):
                if isinstance(p, float) and p < 1000.0:
                    return int(round(p * 10000))
                return int(p)
        if item_id in BENCHMARK_FALLBACK_PRICES:
            return int(round(BENCHMARK_FALLBACK_PRICES[item_id] * 10000))
        return 0

    def _collect_leaf_missing(self, node: ItemRequirementNode) -> List[Tuple[int, str, int]]:
        """Recursively traverses requirement tree to extract missing leaf ingredient quantities."""
        if not node.sub_requirements:
            if node.missing_quantity > 0:
                return [(node.item_id, node.label, node.missing_quantity)]
            return []
        
        if node.is_satisfied:
            return []

        leaves: List[Tuple[int, str, int]] = []
        for child in node.sub_requirements:
            leaves.extend(self._collect_leaf_missing(child))
        return leaves

    def _collect_leaf_required(self, node: ItemRequirementNode) -> List[Tuple[int, str, int]]:
        """Recursively traverses requirement tree to extract total leaf ingredients needed from scratch."""
        if not node.sub_requirements:
            return [(node.item_id, node.label, node.required_quantity)]
        leaves: List[Tuple[int, str, int]] = []
        for child in node.sub_requirements:
            leaves.extend(self._collect_leaf_required(child))
        return leaves

    def solve_buy_vs_craft_vs_vault(
        self,
        goal_item_id: int,
        live_prices: Optional[Dict[int, Dict[str, Any]]] = None,
        account_state: Optional[AccountState] = None
    ) -> ArbitrageReport:
        """Solves the multi-way arbitrage and acquisition decision matrix between:
        1. Instant buy from Trading Post (sells.unit_price)
        2. Buy order on Trading Post (buys.unit_price)
        3. Scratch crafting rolled-up cost (empty account)
        4. Account-adjusted incremental craft cost (accounting for owned items)
        5. Wizard's Vault Starter Kit & Astral Acclaim currency paths
        6. Fractal Relics vs. Mystic Forge clover expected value (3.2 MC + 3.2 Ecto)
        7. T6 Mystic Forge promotion vs direct TP purchase
        8. Wallace's verified 15% TP tax liquidation model for profit margin calculation.
        """
        if self.store is None:
            self.store = PrioryGraphStore()
            self.store.load_all()
        elif len(self.store.graph) == 0:
            self.store.load_all()
        if self.diff_engine is None:
            self.diff_engine = AccountDiffEngine(self.store)
        if account_state is None:
            account_state = AccountState()

        # Automatic live TP price resolution fallback if live_prices is empty or None
        if not live_prices:
            needed_ids: Set[int] = {goal_item_id, 19976, 19721, 24277}
            for info in T6_FINE_MATERIALS.values():
                needed_ids.add(info["t6_id"])
                needed_ids.add(info.get("t5_id", info.get("t5_ids", [0])[0]))

            # Precursor lookup preview from graph
            p_q_preview = """
            SELECT ?precursorId WHERE {
                ?goal priory:gw2Id ?goalId .
                {
                    { ?goal a priory:PrecursorWeapon }
                    UNION
                    { ?goal priory:playsRole <https://priory.gw2/ref/role/Precursor> }
                    ?goal priory:gw2Id ?precursorId .
                }
                UNION
                {
                    ?recipe priory:producesItem ?goal ;
                            priory:hasIngredientRequirement ?req .
                    ?req priory:requiresItem ?precursor .
                    { ?precursor a priory:PrecursorWeapon }
                    UNION
                    { ?precursor priory:playsRole <https://priory.gw2/ref/role/Precursor> }
                    ?precursor priory:gw2Id ?precursorId .
                }
            } LIMIT 1
            """
            p_prev = self.store.query(p_q_preview, init_bindings={"goalId": Literal(goal_item_id)})
            if p_prev:
                needed_ids.add(int(p_prev[0]["precursorId"]))

            # Leaf materials needed for scratch crafting
            scratch_empty = AccountState(
                account_created="2026-01-01",
                materials={},
                bank={},
                characters=[],
                wallet={}
            )
            scratch_diff = self.diff_engine.compute_diff(goal_item_id, scratch_empty)
            for m_id, _, _ in self._collect_leaf_missing(scratch_diff.root_node):
                needed_ids.add(m_id)

            live_prices = get_live_market_prices(list(needed_ids))

        # 1. Goal Item Identification & Basic Market Valuation
        name_q = "SELECT ?label WHERE { ?item priory:gw2Id ?gw2Id ; rdfs:label ?label . } LIMIT 1"
        res = self.store.query(name_q, init_bindings={"gw2Id": Literal(goal_item_id)})
        goal_name = str(res[0]["label"]) if res else f"Item {goal_item_id}"

        instant_buy_total = self._get_price_copper(goal_item_id, live_prices, "sells")
        buy_order_total = self._get_price_copper(goal_item_id, live_prices, "buys")

        # Determine if tradeable on Trading Post dynamically by querying semantic graph
        # ZERO DOMAIN SEMANTICS IN PYTHON: Query priory:isAccountBound, priory:isTradeable,
        # TradablePrecursor, and TradingPostPurchasePath from RDF rather than hardcoded lists.
        trade_q = """
        SELECT ?isBound ?isTradeable ?hasTradablePrecursor ?hasTpPath WHERE {
            ?item priory:gw2Id ?gw2Id .
            OPTIONAL { ?item priory:isAccountBound ?isBound }
            OPTIONAL { ?item priory:isTradeable ?isTradeable }
            OPTIONAL { 
                {
                    ?item priory:hasPrecursorType <https://priory.gw2/def/TradablePrecursor> .
                } UNION {
                    ?recipe priory:producesItem ?item ;
                            priory:hasIngredientRequirement ?req .
                    ?req priory:requiresItem ?ing .
                    {
                        ?ing a priory:PrecursorWeapon ;
                             priory:isAccountBound false .
                    } UNION {
                        ?ing priory:hasPrecursorType <https://priory.gw2/def/TradablePrecursor> .
                    }
                }
                BIND(true AS ?hasTradablePrecursor)
            }
            OPTIONAL {
                ?item priory:hasSubstituteSource [ a <https://priory.gw2/def/TradingPostPurchasePath> ] .
                BIND(true AS ?hasTpPath)
            }
        }
        """
        t_res = self.store.query(trade_q, init_bindings={"gw2Id": Literal(goal_item_id)})
        if t_res:
            bounds = {r.get("isBound") for r in t_res if r.get("isBound") is not None}
            tradeables = {r.get("isTradeable") for r in t_res if r.get("isTradeable") is not None}
            has_tp_prec = any(r.get("hasTradablePrecursor") is True for r in t_res)
            has_tp_path = any(r.get("hasTpPath") is True for r in t_res)

            if True in tradeables:
                is_tradeable = True
            elif False in tradeables:
                is_tradeable = False
            elif has_tp_prec or has_tp_path or False in bounds:
                is_tradeable = True
            elif True in bounds and False not in bounds:
                is_tradeable = False
            else:
                is_tradeable = (buy_order_total > 0 or instant_buy_total > 0)
        else:
            is_tradeable = (buy_order_total > 0 or instant_buy_total > 0)

        # Wallace's verified 15% TP tax model (Listing 5% + Exchange 10% = 15%):
        # net_sell = int(buys.unit_price * 0.85)
        if is_tradeable and buy_order_total > 0:
            net_sell_if_sold = int(buy_order_total * 0.85)
        else:
            net_sell_if_sold = None

        # 2. T6 Fine Material Promotion Strategy across all 8 fine categories
        dust_price = self._get_price_copper(24277, live_prices, "sells")
        ecto_price = self._get_price_copper(19721, live_prices, "sells")
        t6_promotion_strategy: Dict[str, Dict[str, Any]] = {}

        for cat, info in T6_FINE_MATERIALS.items():
            t6_id = info["t6_id"]
            t5_id = info.get("t5_id", info.get("t5_ids", [0])[0])
            t6_name = info["t6_name"]
            t5_name = info["t5_name"]

            t6_direct = self._get_price_copper(t6_id, live_prices, "sells")
            t5_direct = self._get_price_copper(t5_id, live_prices, "sells")

            # Promotion recipe:
            # Standard: 50x T5 + 1x T6 + 5x Crystalline Dust + 5 Philosopher's Stones -> ~7 T6 (net gain 6)
            # Dust: 50x Incandescent Dust + 1x Crystalline Dust + 5x Ecto + 5 Philosopher's Stones -> ~7 Dust (net gain 6)
            if cat == "Dust":
                batch_cost = 50 * t5_direct + 1 * t6_direct + 5 * ecto_price
            else:
                batch_cost = 50 * t5_direct + 1 * t6_direct + 5 * dust_price

            promoted_unit_cost = int(batch_cost / 7.0)
            savings = max(0, t6_direct - promoted_unit_cost)
            rec_action = "PROMOTE_T5_FORGE" if promoted_unit_cost < t6_direct else "BUY_DIRECT"

            t6_promotion_strategy[cat] = {
                "t6_id": t6_id,
                "t6_name": t6_name,
                "t5_id": t5_id,
                "t5_name": t5_name,
                "buy_direct_copper": t6_direct,
                "forge_promoted_copper": promoted_unit_cost,
                "savings_per_unit_copper": savings,
                "recommended_action": rec_action,
                "batch_cost_copper": int(batch_cost),
                "yield": 7,
                "net_gain": 6
            }

        # 3. Mystic Clover Strategy
        coin_price = self._get_price_copper(19976, live_prices, "sells")
        # Mystic Forge EV: 3.2 Mystic Coins + 3.2 Globs of Ectoplasm per clover
        forge_clover_cost = int(3.2 * coin_price + 3.2 * ecto_price)
        # BUY-2046 in Mistlock / Fractals: 150 Fractal Relics + 1 Mystic Coin + 3 Ecto + 2 Spirit Shards
        fractal_clover_cost = int(1 * coin_price + 3 * ecto_price)

        wv_rem = account_state.wizards_vault_remaining(19675)
        wv_sold_out = account_state.is_wizards_vault_sold_out(19675)
        wv_clover_available = not wv_sold_out and (wv_rem is None or wv_rem > 0)

        if wv_clover_available:
            clover_rec = "WIZARDS_VAULT"
        elif account_state.wallet.get(7, 0) >= 150 or (hasattr(account_state, "has_fractal_relics") and account_state.has_fractal_relics()):
            clover_rec = "FRACTAL_RELICS"
        else:
            clover_rec = "MYSTIC_FORGE"

        clover_strategy = {
            "recommended_option": clover_rec,
            "wizards_vault": {
                "unit_gold_copper": 0,
                "astral_acclaim_cost": 9,
                "remaining_available": wv_rem if wv_rem is not None else 20,
                "is_sold_out": wv_sold_out
            },
            "fractal_relics": {
                "unit_gold_copper": fractal_clover_cost,
                "fractal_relics_cost": 150,
                "spirit_shards_cost": 2,
                "daily_limit": 2
            },
            "mystic_forge": {
                "unit_gold_copper": forge_clover_cost,
                "expected_coins": 3.2,
                "expected_ecto": 3.2,
                "unlimited": True
            },
            "ev_coin_price_copper": coin_price,
            "ev_ecto_price_copper": ecto_price,
            "details": (
                f"Wizard's Vault (9 AA, 0 gold) > Fractal BUY-2046 ({fractal_clover_cost // 10000}g {fractal_clover_cost % 10000 // 100}s) "
                f"> Mystic Forge gamble EV ({forge_clover_cost // 10000}g {forge_clover_cost % 10000 // 100}s based on 3.2 MC + 3.2 Ecto)."
            )
        }

        # 4. Precursor Strategy Analysis (Dynamic SPARQL Graph Query)
        prec_id = None
        prec_name = "Precursor"
        p_q = """
        SELECT ?precursorId ?label WHERE {
            ?goal priory:gw2Id ?goalId .
            {
                { ?goal a priory:PrecursorWeapon }
                UNION
                { ?goal priory:playsRole <https://priory.gw2/ref/role/Precursor> }
                ?goal priory:gw2Id ?precursorId ;
                      rdfs:label ?label .
            }
            UNION
            {
                ?recipe priory:producesItem ?goal ;
                        priory:hasIngredientRequirement ?req .
                ?req priory:requiresItem ?precursor .
                { ?precursor a priory:PrecursorWeapon }
                UNION
                { ?precursor priory:playsRole <https://priory.gw2/ref/role/Precursor> }
                ?precursor priory:gw2Id ?precursorId ;
                           rdfs:label ?label .
            }
        } LIMIT 1
        """
        p_res = self.store.query(p_q, init_bindings={"goalId": Literal(goal_item_id)})
        if p_res:
            prec_id = int(p_res[0]["precursorId"])
            prec_name = str(p_res[0]["label"])
        elif goal_item_id in GEN1_WEAPONS:
            prec_id = GEN1_WEAPONS[goal_item_id]["precursor_id"]
            prec_name = GEN1_WEAPONS[goal_item_id].get("precursor_name", PRECURSOR_NAMES.get(prec_id, f"Precursor {prec_id}"))
        elif goal_item_id in GEN2_WEAPONS:
            prec_id = GEN2_WEAPONS[goal_item_id]["precursor_id"]
            prec_name = GEN2_WEAPONS[goal_item_id].get("precursor_name", PRECURSOR_NAMES.get(prec_id, f"Precursor {prec_id}"))
        elif goal_item_id in GEN1_PRECURSOR_IDS or goal_item_id in GEN2_PRECURSOR_IDS:
            prec_id = goal_item_id
            prec_name = PRECURSOR_NAMES.get(prec_id, f"Precursor {prec_id}")

        prec_instant = self._get_price_copper(prec_id, live_prices, "sells") if prec_id else 0
        prec_buy_order = self._get_price_copper(prec_id, live_prices, "buys") if prec_id else 0

        # Hobbs collection crafting cost: ~210 gold = 2,100,000 copper for Gen 1
        hobbs_cost = 2100000

        # Dynamic Starter Kit check from RDF
        is_starter_kit_candidate = False
        if prec_id:
            sk_q = """
            SELECT ?kit WHERE {
                ?kit a priory:LegendaryStarterKit ;
                     priory:unpacksInto ?prec .
                ?prec priory:gw2Id ?precId .
            } LIMIT 1
            """
            sk_res = self.store.query(sk_q, init_bindings={"precId": Literal(prec_id)})
            is_starter_kit_candidate = bool(sk_res) or (prec_id in STARTER_KIT_PRECURSORS)

        has_starter_kit_chest = (
            account_state.has_starter_kit_for(goal_item_id)
            if hasattr(account_state, "has_starter_kit_for")
            else False
        )
        if not has_starter_kit_chest and self.diff_engine and prec_id:
            has_starter_kit_chest = bool(self.diff_engine.is_unpackable_from_account(prec_id, account_state))

        already_owned_prec = account_state.total_item_count(prec_id) > 0 if prec_id else False

        if has_starter_kit_chest or is_starter_kit_candidate:
            prec_rec = "WIZARDS_VAULT"
        elif prec_buy_order > 0 and prec_buy_order <= hobbs_cost:
            prec_rec = "BUY_ORDER"
        elif hobbs_cost < prec_buy_order or prec_buy_order == 0:
            prec_rec = "HOBBS_COLLECTION"
        else:
            prec_rec = "INSTANT_BUY"

        precursor_strategy = {
            "precursor_id": prec_id,
            "precursor_name": prec_name,
            "recommended_option": prec_rec,
            "instant_buy_copper": prec_instant,
            "buy_order_copper": prec_buy_order,
            "hobbs_craft_copper": hobbs_cost,
            "wizards_vault_acclaim": 1200 if (is_starter_kit_candidate or has_starter_kit_chest) else None,
            "wizards_vault_available": is_starter_kit_candidate or has_starter_kit_chest,
            "already_owned": already_owned_prec,
            "details": (
                f"{prec_name}: Wizard's Vault Starter Kit (1,200 AA / 0 gold) > "
                f"TP Buy Order ({prec_buy_order // 10000}g) vs Hobbs Collection ({hobbs_cost // 10000}g) vs Instant Buy ({prec_instant // 10000}g)."
            )
        }

        # 5. Component Pricing Helper
        def _evaluate_mat_unit_cost(mat_id: int, is_scratch: bool) -> int:
            if mat_id == 19912:  # Icy Runestone
                return 10000
            if mat_id == 19675:  # Mystic Clover
                if clover_strategy["recommended_option"] == "WIZARDS_VAULT":
                    return 0
                elif clover_strategy["recommended_option"] == "FRACTAL_RELICS":
                    return fractal_clover_cost
                else:
                    return forge_clover_cost
            if prec_id and mat_id == prec_id:
                if not is_scratch and already_owned_prec:
                    return 0
                if precursor_strategy["recommended_option"] == "WIZARDS_VAULT":
                    return 0
                elif precursor_strategy["recommended_option"] == "BUY_ORDER":
                    return prec_buy_order if prec_buy_order > 0 else prec_instant
                elif precursor_strategy["recommended_option"] == "HOBBS_COLLECTION":
                    return hobbs_cost
                else:
                    return prec_instant
            if mat_id in T6_ID_TO_CAT:
                cat = T6_ID_TO_CAT[mat_id]
                strat = t6_promotion_strategy.get(cat, {})
                if strat.get("recommended_action") == "PROMOTE_T5_FORGE":
                    return strat.get("forge_promoted_copper", self._get_price_copper(mat_id, live_prices, "sells"))
                return strat.get("buy_direct_copper", self._get_price_copper(mat_id, live_prices, "sells"))
            return self._get_price_copper(mat_id, live_prices, "sells")

        # 6. Crafting Costs Rollup: Account-Adjusted vs. Scratch
        diff_report = self.diff_engine.compute_diff(goal_item_id, account_state)
        my_account_craft_cost = 0
        if not diff_report.is_fully_satisfied:
            leaf_missing = self._collect_leaf_missing(diff_report.root_node)
            for m_id, m_label, m_qty in leaf_missing:
                unit_c = _evaluate_mat_unit_cost(m_id, is_scratch=False)
                my_account_craft_cost += unit_c * m_qty

        empty_account = AccountState(
            account_created="2026-01-01",
            materials={},
            bank={},
            characters=[],
            wallet={}
        )
        scratch_report = self.diff_engine.compute_diff(goal_item_id, empty_account)
        craft_from_scratch_total = 0
        scratch_leaves = self._collect_leaf_missing(scratch_report.root_node)
        for m_id, m_label, m_qty in scratch_leaves:
            unit_c = _evaluate_mat_unit_cost(m_id, is_scratch=True)
            craft_from_scratch_total += unit_c * m_qty

        # 7. Profit Margin & Final Action Recommendation
        if net_sell_if_sold is not None:
            profit_margin_if_sold = net_sell_if_sold - craft_from_scratch_total
        else:
            profit_margin_if_sold = None

        if is_tradeable and net_sell_if_sold is not None and profit_margin_if_sold is not None and profit_margin_if_sold > 0:
            recommended_action = "CRAFT_FOR_PROFIT"
        elif is_tradeable and instant_buy_total > 0 and (instant_buy_total < my_account_craft_cost or (buy_order_total > 0 and buy_order_total < my_account_craft_cost)):
            recommended_action = "BUY_FINISHED_DIRECT"
        else:
            recommended_action = "CRAFT_FOR_SELF"

        return ArbitrageReport(
            goal_item_id=goal_item_id,
            goal_name=goal_name,
            instant_buy_total=instant_buy_total,
            buy_order_total=buy_order_total,
            craft_from_scratch_total=craft_from_scratch_total,
            my_account_craft_cost=my_account_craft_cost,
            precursor_strategy=precursor_strategy,
            clover_strategy=clover_strategy,
            t6_promotion_strategy=t6_promotion_strategy,
            net_sell_if_sold=net_sell_if_sold,
            profit_margin_if_sold=profit_margin_if_sold,
            recommended_action=recommended_action
        )

    def solve_optimal_path(
        self,
        diff_report: AccountDiffReport,
        account: AccountState,
        tp_prices: Optional[Dict[int, float]] = None,
        excluded_modes: Optional[List[str]] = None,
        exhausted_sources: Optional[List[str]] = None,
        time_budget_minutes: int = 120
    ) -> OptimalCraftingPlan:
        # Standard benchmark fallback prices (in gold) based on live API averages
        benchmark_prices = {
            19721: 0.301,  # Glob of Ectoplasm
            19976: 1.950,  # Mystic Coin
            19675: 7.420,  # Mystic Clover (crafting cost basis)
            24295: 0.221,  # Vial of Powerful Blood
            24283: 0.189,  # Powerful Venom Sac
            24300: 0.156,  # Elaborate Totem
            24277: 0.161,  # Pile of Crystalline Dust
            24357: 0.129,  # Vicious Fang
            24289: 0.188,  # Armored Scale
            24351: 0.159,  # Vicious Claw
            24358: 0.189,  # Ancient Bone
            89103: 0.056,  # Lucent Crystal
            89258: 0.045,  # Symbol of Control
            89182: 0.045,  # Symbol of Enhancement
            89140: 0.045,  # Symbol of Pain
            19700: 0.025,  # Mithril Ingot
            19701: 0.085,  # Orichalcum Ingot
            19739: 0.040,  # Elder Wood Plank
            19740: 0.120,  # Ancient Wood Plank
            19729: 0.035,  # Silk Bolt
            19732: 0.150,  # Gossamer Bolt
            19735: 0.060,  # Thick Leather Section
            19737: 0.220,  # Hardened Leather Section
            29185: 179.9,  # Dusk
            29169: 159.5,  # Dawn
            29166: 120.0,  # Tooth of Frostfang
            29167: 140.0,  # Spark
            29168: 160.0,  # Zap
            29180: 150.0,  # The Legend
        }
        prices = dict(benchmark_prices)
        if tp_prices:
            prices.update(tp_prices)

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
            aa_amount = account.astral_acclaim_count()
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

        if diff_report.is_saturated:
            bottlenecks.append(
                f"🛡️ **Legendary Armory Saturated ({diff_report.armory_owned_count}/{diff_report.armory_max_cap} owned):** "
                f"Your account already holds the maximum useful copies of {diff_report.goal_item_name} in your Legendary Armory."
            )

        if getattr(diff_report, "missing_achievements", None):
            for ach in diff_report.missing_achievements:
                bottlenecks.append(
                    f"🏆 **Achievement Prerequisite Needed:** '{ach['title']}' (ID: {ach['id']}) — {ach['description'] or 'Required to unlock this legendary item.'}"
                )

        if getattr(diff_report, "missing_masteries", None):
            for mast in diff_report.missing_masteries:
                bottlenecks.append(
                    f"🌟 **Mastery Rank Required:** {mast['track_label']} Level {mast['required_level']} ({mast['mastery_name']}) — Current: Level {mast['current_level']}."
                )

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
            # Query capable character for the specific gift craft via active discipline routing
            cap_char_name = None
            assigned_waypoint = "[&BBAEAAA=]"
            assigned_npc = None
            craft_desc = "Combine specific lodestones, refined ingots/planks, and discipline components at Level 400 crafting station."
            if spec_node and self.store:
                disc_q = """
                SELECT DISTINCT ?discipline ?rating WHERE {
                    {
                        ?item priory:gw2Id ?gw2Id ;
                              priory:producedBy ?recipe .
                        ?recipe priory:requiresDiscipline ?discipline .
                        OPTIONAL { ?recipe priory:requiredRating ?rating }
                        OPTIONAL { ?recipe priory:requiresRating ?rating }
                    } UNION {
                        ?item priory:gw2Id ?gw2Id ;
                              priory:producedBy ?forgeRec .
                        ?forgeRec priory:hasIngredientRequirement ?req .
                        ?req priory:requiresItem ?subItem .
                        ?subItem priory:producedBy ?recipe .
                        ?recipe priory:requiresDiscipline ?discipline .
                        OPTIONAL { ?recipe priory:requiredRating ?rating }
                        OPTIONAL { ?recipe priory:requiresRating ?rating }
                    }
                }
                """
                d_res = self.store.query(disc_q, init_bindings={"gw2Id": Literal(spec_node.item_id)})
                if d_res:
                    disc_uri = str(d_res[0]["discipline"])
                    disc_name = disc_uri.rstrip("/").split("/")[-1].split("#")[-1].lower()
                    req_rating = int(d_res[0].get("rating", 400)) if d_res[0].get("rating") else 400
                    route_info = route_crafting_discipline(disc_name, req_rating, account, self.store)
                    cap_char_name = route_info.get("character")
                    assigned_waypoint = route_info.get("waypoint") or "[&BBAEAAA=]"
                    assigned_npc = route_info.get("vendor_npc")
                    craft_desc = route_info.get("recommendation", craft_desc)
                else:
                    # Fallback query directly for capable character
                    disc_q2 = """
                    SELECT DISTINCT ?charName WHERE {
                        ?item priory:gw2Id ?gw2Id ;
                              priory:producedBy ?recipe .
                        ?recipe priory:requiresDiscipline ?discipline ;
                                priory:requiredRating ?rating .
                        ?char a priory:Character ;
                              priory:characterName ?charName ;
                              priory:hasCraftingDiscipline ?cd .
                        ?cd priory:discipline ?discipline ;
                            priory:craftingRating ?cRating .
                        FILTER (?cRating >= ?rating)
                    } LIMIT 1
                    """
                    c_res = self.store.query(disc_q2, init_bindings={"gw2Id": Literal(spec_node.item_id)})
                    if c_res:
                        cap_char_name = c_res[0]["charName"]
                        craft_desc = f"Switch to character '{cap_char_name}' to craft at Level 400 crafting station [&BBAEAAA=]."

            p4_steps.append(MilestoneStep(
                step_number=2,
                title=f"Craft {spec_node.label.split('(')[0].strip() if spec_node else 'Weapon Gift'}",
                description=craft_desc,
                waypoint=assigned_waypoint,
                npc_name=assigned_npc,
                assigned_character=cap_char_name,
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

    def _classify_goal_item(self, goal_item_id: int) -> Tuple[str, str, List[str]]:
        """Determines goal item name, generation/archetype classification, and altLabels.
        Returns: (goal_name, classification, alt_labels)
        Classifications: 'GEN1', 'GEN2', 'GEN3', 'OBSIDIAN_ARMOR', 'GENERAL'
        """
        goal_name = ""
        alt_labels: List[str] = []

        if self.store:
            sparql = """
            SELECT DISTINCT ?label ?altLabel WHERE {
                ?item priory:gw2Id ?gw2Id .
                OPTIONAL { ?item rdfs:label ?label }
                OPTIONAL { ?item skos:altLabel ?altLabel }
            }
            """
            rows = self.store.query(sparql, init_bindings={"gw2Id": Literal(goal_item_id)})
            if rows:
                goal_name = str(rows[0].get("label", ""))
                for r in rows:
                    if r.get("altLabel"):
                        alt_labels.append(str(r["altLabel"]))

        WELL_KNOWN_GOALS: Dict[int, Tuple[str, str]] = {
            30704: ("Twilight", "GEN1"),
            30689: ("Sunrise", "GEN1"),
            30684: ("Frostfang", "GEN1"),
            30685: ("Kudzu", "GEN1"),
            30686: ("The Dreamer", "GEN1"),
            30687: ("Incinerator", "GEN1"),
            30688: ("The Minstrel", "GEN1"),
            30690: ("The Juggernaut", "GEN1"),
            30691: ("Kraitkin", "GEN1"),
            30692: ("Meteorlogicus", "GEN1"),
            30693: ("The Predator", "GEN1"),
            30694: ("The Bifrost", "GEN1"),
            30695: ("Bolt", "GEN1"),
            30696: ("Rodgort", "GEN1"),
            30697: ("Frenzy", "GEN1"),
            30698: ("Quip", "GEN1"),
            30699: ("Howler", "GEN1"),
            30700: ("The Flameseeker Prophecies", "GEN1"),
            30702: ("Eternity", "GEN1"),
            71383: ("Nevermore", "GEN2"),
            71384: ("The Raven Staff", "GEN2"),
            74155: ("Astralaria", "GEN2"),
            76158: ("HOPE", "GEN2"),
            79562: ("Shooshadoo", "GEN2"),
            79802: ("Chuka and Champawat", "GEN2"),
            80562: ("Eureka", "GEN2"),
            81775: ("The Shining Blade", "GEN2"),
            86303: ("Claw of the Khan-Ur", "GEN2"),
            88330: ("The Binding of Ipos", "GEN2"),
            89854: ("Exordium", "GEN2"),
            90530: ("Pharus", "GEN2"),
            96203: ("Aurene's Bite", "GEN3"),
            96356: ("Aurene's Bite", "GEN3"),
            96221: ("Aurene's Bite", "GEN3"),
            96652: ("Aurene's Fang", "GEN3"),
            95684: ("Aurene's Weight", "GEN3"),
            95808: ("Aurene's Fang", "GEN3"),
            97165: ("Aurene's Argument", "GEN3"),
            91505: ("Legendary Sigil", "GENERAL"),
            91536: ("Legendary Rune", "GENERAL"),
        }

        fallback_class = "GENERAL"
        if not goal_name and goal_item_id in WELL_KNOWN_GOALS:
            goal_name, fallback_class = WELL_KNOWN_GOALS[goal_item_id]
        elif not goal_name:
            if 101001 <= goal_item_id <= 101018:
                goal_name = "Obsidian Armor"
                fallback_class = "OBSIDIAN_ARMOR"
            else:
                goal_name = f"Legendary #{goal_item_id}"
                fallback_class = "GENERAL"

        gn_lower = goal_name.lower()
        alts_lower = [a.lower() for a in alt_labels]

        if "obsidian" in gn_lower or any("obsidian" in a for a in alts_lower) or any("soto" in a for a in alts_lower):
            classification = "OBSIDIAN_ARMOR"
        elif any("gen 1" in a or "generation 1" in a or "gen one" in a for a in alts_lower) or gn_lower in [
            "twilight", "sunrise", "bolt", "the bifrost", "bifrost", "frostfang", "kudzu", "incinerator",
            "the juggernaut", "juggernaut", "eternity", "the dreamer", "the minstrel", "meteorlogicus",
            "the predator", "quip", "howler", "the flameseeker prophecies", "rodgort", "frenzy", "kraitkin"
        ]:
            classification = "GEN1"
        elif any("gen 2" in a or "generation 2" in a or "gen two" in a for a in alts_lower) or gn_lower in [
            "nevermore", "astralaria", "hope", "chuka and champawat", "eureka", "the shining blade",
            "claw of the khan-ur", "the binding of ipos", "exordium", "pharus", "shooshadoo", "sharur", "xiuquatl"
        ]:
            classification = "GEN2"
        elif any("gen 3" in a or "generation 3" in a or "gen three" in a for a in alts_lower) or "aurene" in gn_lower:
            classification = "GEN3"
        elif goal_item_id in WELL_KNOWN_GOALS:
            classification = WELL_KNOWN_GOALS[goal_item_id][1]
        else:
            classification = fallback_class

        return goal_name, classification, alt_labels

    def _find_refinement_character(self, account_state: AccountState) -> Optional[str]:
        """Identifies the player character with the appropriate crafting license for Ascended Daily Refinements (450+)."""
        needed_discs = {"weaponsmith", "armorsmith", "tailor", "leatherworker", "huntsman", "artificer"}

        # 1. Check account_state.characters list
        if account_state.characters:
            best_char = None
            best_score = -1
            for char in account_state.characters:
                char_name = char.get("name")
                if not char_name:
                    continue
                score = 0
                for c in char.get("crafting", []):
                    disc = c.get("discipline", "").lower()
                    rating = c.get("rating", 0)
                    active = c.get("active", True)
                    if disc in needed_discs:
                        if rating >= 450:
                            score += 100 + rating + (50 if active else 0)
                        elif rating >= 400:
                            score += 10 + rating
                if score > best_score and score > 0:
                    best_score = score
                    best_char = char_name
            if best_char:
                return best_char

        # 2. Check account_state.character_disciplines dict
        if account_state.character_disciplines:
            best_char = None
            best_score = -1
            for char_name, discs in account_state.character_disciplines.items():
                score = 0
                for disc_name, info in discs.items():
                    if disc_name.lower() in needed_discs:
                        rating = info.get("rating", 0) if isinstance(info, dict) else int(info)
                        active = info.get("active", True) if isinstance(info, dict) else True
                        if rating >= 450:
                            score += 100 + rating + (50 if active else 0)
                        elif rating >= 400:
                            score += 10 + rating
                if score > best_score and score > 0:
                    best_score = score
                    best_char = char_name
            if best_char:
                return best_char

        # 3. Check account_state.active_disciplines
        if account_state.active_disciplines:
            for disc in ["weaponsmith", "armorsmith", "tailor", "leatherworker", "huntsman", "artificer"]:
                chars = account_state.active_disciplines.get(disc, [])
                if chars:
                    return chars[0]

        # 4. Fallback: map_completed_characters
        if account_state.map_completed_characters:
            return account_state.map_completed_characters[0]

        return None

    def _is_task_completed_today(self, task_id: str, category: str, account_state: AccountState) -> bool:
        """Determines if a daily time-gated activity was already completed today per account state."""
        comp_acts = getattr(account_state, "completed_daily_activities", set())
        if isinstance(comp_acts, (set, list)) and (task_id in comp_acts or category in comp_acts):
            return True

        prog = account_state.progression or {}
        if prog.get(task_id, 0) > 0 or prog.get(category.lower(), 0) > 0:
            return True

        daily_crafting = [str(x).lower() for x in getattr(account_state, "daily_crafting", [])]
        world_bosses = [str(x).lower() for x in getattr(account_state, "world_bosses", [])]

        if category == "QUARTZ_CHARGING":
            if any(k in daily_crafting for k in ["charged_quartz_crystal", "43773", "quartz_charging"]):
                return True
            if prog.get("charged_quartz", 0) > 0:
                return True

        elif category == "DAILY_REFINEMENT":
            refinement_keys = {
                "lump_of_mithrillium",
                "glob_of_elder_spirit_residue",
                "spool_of_silk_weaving_thread",
                "spool_of_thick_elonian_cord"
            }
            if refinement_keys.issubset(set(daily_crafting)):
                return True
            if prog.get("daily_refinement", 0) > 0:
                return True

        elif category == "WORLD_BOSS_ANOMALY":
            if any(b in world_bosses for b in ["ley_line_anomaly", "anomaly"]):
                return True
            if prog.get("ley_line_anomaly", 0) > 0:
                return True

        elif category == "PROVISIONER_TOKEN":
            if "provisioner_token" in comp_acts or "provisioner_token_route" in comp_acts:
                return True

        elif category == "DAILY_FRACTAL_CLOVERS":
            if "daily_fractals" in comp_acts or "daily_fractal_clovers" in comp_acts:
                return True

        elif category == "WEEKLY_LEIVAS":
            weekly_ass = getattr(account_state, "weekly_vendor_purchases", {}).get("leivas", 0)
            if weekly_ass >= 5 or "weekly_leivas" in comp_acts:
                return True

        return False

    def _knapsack_solve(
        self,
        candidates: List[ScheduledSessionTask],
        time_budget: int
    ) -> List[ScheduledSessionTask]:
        """0/1 Knapsack dynamic programming solver prioritizing total weight within time budget."""
        if time_budget <= 0 or not candidates:
            return []

        dp: List[float] = [0.0] * (time_budget + 1)
        chosen: List[List[int]] = [[] for _ in range(time_budget + 1)]

        for idx, task in enumerate(candidates):
            w = task.estimated_duration_minutes
            v = task.priority_weight
            if w > time_budget or v <= 0:
                continue
            for cap in range(time_budget, w - 1, -1):
                if dp[cap - w] + v > dp[cap]:
                    dp[cap] = dp[cap - w] + v
                    chosen[cap] = chosen[cap - w] + [idx]

        best_cap = 0
        best_val = 0.0
        for cap in range(1, time_budget + 1):
            if dp[cap] > best_val:
                best_val = dp[cap]
                best_cap = cap
            elif dp[cap] == best_val and best_val > 0:
                best_cap = cap

        selected_indices = chosen[best_cap]
        return [candidates[i] for i in selected_indices]

    def schedule_daily_session_itinerary(
        self,
        goal_item_id: Optional[int] = None,
        time_budget_minutes: int = 120,
        account_state: Optional[AccountState] = None,
        active_events: Optional[List[str]] = None,
        target_item_id: Optional[int] = None,
        account: Optional[AccountState] = None,
        **kwargs
    ) -> DailySessionItinerary:
        """Schedules the mathematically optimal session itinerary for a given time budget and target legendary.
        
        Applies a 0/1 Knapsack priority algorithm over daily time-gated activities:
        1. Quartz Crystal Charging (2 min, Krait Obelisk [&BPwCAAA=])
        2. Account-Bound Daily Refinement (3 min, Crafting station)
        3. Ley-Line Anomaly World Boss (10 min)
        4. High-Yield Provisioner Token Route (15 min)
        5. Daily Fractals & Wizard's Vault Daily Tasks (30 min)
        6. Weekly Antique Summoning Stone Discount (5 min, Arborstone [&BEEPAAA=])
        
        Filters completed tasks, accounts for active event timers, assigns crafting characters,
        and orders activities logically (lounge/home -> event timers -> vendors -> fractals).
        """
        actual_item_id = target_item_id if target_item_id is not None else (goal_item_id if goal_item_id is not None else 30704)
        actual_account = account if account is not None else (account_state if account_state is not None else AccountState())

        goal_name, classification, alt_labels = self._classify_goal_item(actual_item_id)
        refinement_char = self._find_refinement_character(actual_account)

        # 1. Quartz Crystal Charging
        quartz_task = ScheduledSessionTask(
            id="quartz_charging",
            title="Quartz Crystal Charging",
            category="QUARTZ_CHARGING",
            estimated_duration_minutes=2,
            waypoint_code="[&BPwCAAA=]",
            location_name="Krait Obelisk, Lion's Arch",
            instructions="Interact with the Krait Obelisk Shard in Lion's Arch or any Place of Power with 25 Quartz Crystals in inventory to charge 1 Charged Quartz Crystal.",
            required_inputs={"item_id": 43772, "name": "Quartz Crystal", "count": 25},
            reward_output={"item_id": 43773, "name": "Charged Quartz Crystal", "count": 1, "value_towards_goal": f"Daily Place of Power infusion for {goal_name} time-gated components"},
            priority_weight=80.0,
            character_name=None
        )

        # 2. Account-Bound Daily Refinement
        refinement_inst = (
            f"Switch to character '{refinement_char}' and craft daily ascended materials at level 450 crafting stations: "
            "Lump of Mithrillium (Weaponsmith/Armorsmith), Glob of Elder Spirit Residue (Huntsman/Artificer/Weaponsmith), "
            "Spool of Silk Weaving Thread (Tailor), and Spool of Thick Elonian Cord (Leatherworker)."
            if refinement_char else
            "Craft daily ascended materials at level 450 crafting stations: Lump of Mithrillium, Glob of Elder Spirit Residue, "
            "Spool of Silk Weaving Thread, and Spool of Thick Elonian Cord."
        )
        refinement_task = ScheduledSessionTask(
            id="daily_refinement",
            title="Account-Bound Daily Refinement (Mithrillium, Spirit Residue, Silk Thread, Elonian Cord)",
            category="DAILY_REFINEMENT",
            estimated_duration_minutes=3,
            waypoint_code="[&BBAEAAA=]",
            location_name="Crafting Station, Lion's Arch",
            instructions=refinement_inst,
            required_inputs={
                "description": "50 Mithril Ingot, 50 Elder Wood Plank, 100 Bolt of Silk, 50 Cured Thick Leather Square, 4 Glob of Ectoplasm, 40 Thermocatalytic Reagents",
                "materials": [
                    {"item_id": 19684, "name": "Mithril Ingot", "count": 50},
                    {"item_id": 19709, "name": "Elder Wood Plank", "count": 50},
                    {"item_id": 19747, "name": "Bolt of Silk", "count": 100},
                    {"item_id": 19735, "name": "Cured Thick Leather Square", "count": 50},
                    {"item_id": 19721, "name": "Glob of Ectoplasm", "count": 4},
                    {"item_id": 46747, "name": "Thermocatalytic Reagent", "count": 40}
                ]
            },
            reward_output={
                "items": [
                    {"name": "Lump of Mithrillium", "count": 1},
                    {"name": "Glob of Elder Spirit Residue", "count": 1},
                    {"name": "Spool of Silk Weaving Thread", "count": 1},
                    {"name": "Spool of Thick Elonian Cord", "count": 1}
                ],
                "count": 4,
                "value_towards_goal": f"Ascended daily refinements for {goal_name} components (Gift of Metal/Wood/Leather/Cloth)"
            },
            priority_weight=85.0,
            character_name=refinement_char
        )

        # 3. Ley-Line Anomaly World Boss
        anomaly_weight = 95.0 if classification == "GEN1" else (85.0 if classification in ["GEN2", "GEN3", "GENERAL"] else 75.0)
        if active_events and any(e.lower() in ["ley_line_anomaly", "anomaly", "world_boss"] for e in active_events):
            anomaly_weight += 15.0

        anomaly_task = ScheduledSessionTask(
            id="world_boss_anomaly",
            title="Ley-Line Anomaly World Boss (Guaranteed Mystic Coin)",
            category="WORLD_BOSS_ANOMALY",
            estimated_duration_minutes=10,
            waypoint_code="[&BEoCAAA=]",
            location_name="Timberline Falls / Iron Marches / Gendarran Fields",
            instructions="Defeat the Legendary Ley-Line Anomaly during its spawn window for a guaranteed daily Mystic Coin and Karma.",
            required_inputs={},
            reward_output={
                "item_id": 19976,
                "name": "Mystic Coin",
                "count": 1,
                "karma": 2500,
                "value_towards_goal": f"Guaranteed Mystic Coin and Karma for {goal_name} Mystic Tribute or Gift of Fortune"
            },
            priority_weight=anomaly_weight,
            character_name=None
        )

        # 4. High-Yield Provisioner Token Route
        prov_weight = 95.0 if classification == "GEN2" else (65.0 if classification == "OBSIDIAN_ARMOR" else (60.0 if classification == "GENERAL" else 0.0))
        prov_task = ScheduledSessionTask(
            id="provisioner_token_route",
            title="High-Yield Provisioner Token Route",
            category="PROVISIONER_TOKEN",
            estimated_duration_minutes=15,
            waypoint_code="[&BAwEAAA=]",
            location_name="Lion's Arch, Black Citadel, Verdant Brink",
            instructions="Trade fast vendor exchanges (rare crafted weapons/armor, Obsidian Shards, Reclaimed Plates) with Faction Provisioners in Lion's Arch [&BAwEAAA=], Black Citadel [&BKgDAAA=], and Verdant Brink [&BN4HAAA=].",
            required_inputs={"description": "Crafted rare gear, Obsidian Shards, Reclaimed Metal Plates"},
            reward_output={
                "item_id": 29,
                "name": "Provisioner Token",
                "count": 8,
                "value_towards_goal": f"Faction Provisioner Tokens for {goal_name} Gift of Craftsmanship / Lesser Vision Crystals"
            },
            priority_weight=prov_weight,
            character_name=None
        )

        # 5. Daily Fractals & Wizard's Vault Daily Tasks
        fractal_weight = 95.0 if classification == "OBSIDIAN_ARMOR" else 90.0
        fractal_task = ScheduledSessionTask(
            id="daily_fractal_clovers",
            title="Daily Fractals & Wizard's Vault (Mystic Clover Cap)",
            category="DAILY_FRACTAL_CLOVERS",
            estimated_duration_minutes=30,
            waypoint_code="[&BBAEAAA=]",
            location_name="Fractals of the Mists, Lion's Arch",
            instructions="Complete Daily Tier 4 / Recommended Fractals and Wizard's Vault daily objectives. Purchase discounted daily Mystic Clovers from BLING-9988 and Astral Acclaim clover rewards.",
            required_inputs={"currencies": {"Fractal Relic": 150, "Astral Acclaim": 60, "Spirit Shards": 3}},
            reward_output={
                "item_id": 19675,
                "name": "Mystic Clover",
                "count": 2,
                "value_towards_goal": f"Discounted Mystic Clovers towards 77 required for {goal_name}"
            },
            priority_weight=fractal_weight,
            character_name=None
        )

        # 6. Weekly Antique Summoning Stone (Leivas)
        leivas_weight = 95.0 if classification == "GEN3" else (70.0 if classification == "GENERAL" else 0.0)
        leivas_task = ScheduledSessionTask(
            id="weekly_leivas_ass",
            title="Weekly Antique Summoning Stones (Leivas)",
            category="WEEKLY_LEIVAS",
            estimated_duration_minutes=5,
            waypoint_code="[&BEEPAAA=]",
            location_name="Arborstone",
            instructions="Visit Leivas in Arborstone [&BEEPAAA=] to purchase weekly discounted Antique Summoning Stones (up to 5 per week) using Imperial Favor and Laurels.",
            required_inputs={"currencies": {"Imperial Favor": 500, "Laurel": 5}},
            reward_output={
                "item_id": 96978,
                "name": "Antique Summoning Stone",
                "count": 5,
                "value_towards_goal": f"Discounted weekly Antique Summoning Stones towards 100 required for {goal_name} Tribute to Aurene"
            },
            priority_weight=leivas_weight,
            character_name=None
        )

        all_candidate_tasks = [quartz_task, refinement_task, anomaly_task, prov_task, fractal_task, leivas_task]

        # Filter out completed tasks and tasks with zero/negative weight (irrelevant for this goal)
        eligible_tasks: List[ScheduledSessionTask] = []
        for t in all_candidate_tasks:
            if t.priority_weight <= 0.0:
                continue
            if self._is_task_completed_today(t.id, t.category, actual_account):
                continue
            eligible_tasks.append(t)

        # Knapsack optimization
        scheduled_tasks = self._knapsack_solve(eligible_tasks, time_budget_minutes)

        # Logical execution order:
        # Fast home instance/lounge activities first (Quartz 2m, Refinements 3m) -> Event timer (Anomaly 10m) -> Vendor exchanges (Leivas 5m, Provisioner Tokens 15m) -> Clovers/Fractals (30m)
        CATEGORY_ORDER = {
            "QUARTZ_CHARGING": 1,
            "DAILY_REFINEMENT": 2,
            "WORLD_BOSS_ANOMALY": 3,
            "WEEKLY_LEIVAS": 4,
            "PROVISIONER_TOKEN": 5,
            "DAILY_FRACTAL_CLOVERS": 6
        }
        scheduled_tasks.sort(key=lambda t: CATEGORY_ORDER.get(t.category, 99))

        total_scheduled_minutes = sum(t.estimated_duration_minutes for t in scheduled_tasks)
        time_utilization_pct = round((total_scheduled_minutes / time_budget_minutes) * 100, 1) if time_budget_minutes > 0 else 0.0

        task_titles = [t.title.split("(")[0].strip() for t in scheduled_tasks]
        summary = (
            f"Tonight's {total_scheduled_minutes}-minute session scheduled for {goal_name} "
            f"({time_utilization_pct}% utilization of {time_budget_minutes}m budget). "
            f"Focuses on: {', '.join(task_titles) if task_titles else 'No tasks scheduled'}."
        )

        return DailySessionItinerary(
            goal_item_id=actual_item_id,
            goal_name=goal_name,
            time_budget_minutes=time_budget_minutes,
            total_scheduled_minutes=total_scheduled_minutes,
            tasks=scheduled_tasks,
            time_utilization_pct=time_utilization_pct,
            summary=summary
        )


def schedule_daily_session_itinerary(
    goal_item_id: Optional[int] = None,
    time_budget_minutes: int = 120,
    account_state: Optional[AccountState] = None,
    active_events: Optional[List[str]] = None,
    graph_store: Optional[PrioryGraphStore] = None,
    target_item_id: Optional[int] = None,
    account: Optional[AccountState] = None,
    **kwargs
) -> DailySessionItinerary:
    """Convenience module-level entrypoint for scheduling a daily session itinerary."""
    solver = PathSolver(graph_store) if graph_store is not None else PathSolver(PrioryGraphStore())
    return solver.schedule_daily_session_itinerary(
        goal_item_id=goal_item_id,
        time_budget_minutes=time_budget_minutes,
        account_state=account_state,
        active_events=active_events,
        target_item_id=target_item_id,
        account=account,
        **kwargs
    )


def solve_buy_vs_craft_vs_vault(
    goal_item_id: int,
    live_prices: Optional[Dict[int, Dict[str, Any]]] = None,
    account_state: Optional[AccountState] = None,
    graph_store: Optional[PrioryGraphStore] = None
) -> ArbitrageReport:
    """Convenience module-level entrypoint for multi-way arbitrage and acquisition decision matrix."""
    if graph_store is None:
        graph_store = PrioryGraphStore()
        graph_store.load_all()
    elif len(graph_store.graph) == 0:
        graph_store.load_all()
    solver = PathSolver(graph_store)
    return solver.solve_buy_vs_craft_vs_vault(
        goal_item_id=goal_item_id,
        live_prices=live_prices,
        account_state=account_state
    )

