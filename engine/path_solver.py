"""Multi-Criteria Path & Optimization Solver for Project Priory.

Calculates the mathematically optimal acquisition and crafting routes based on:
1. Live Trading Post prices (Instant Buy vs. Buy Order).
2. Alternative item source valuations (Astral Acclaim vs. Fractal Vendor vs. Mystic Forge).
3. Player state delta (owned materials, bank, wallet currencies, crafting levels).
4. Player constraints (time budget, game mode exclusions, exhausted sources, liquid gold).
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
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
    """Evaluates alternative acquisition routes to find the lowest-cost, fastest route."""

    DEFAULT_PRICES = {
        29185: 280.0,  # Dusk (Precursor)
        19721: 0.22,   # Glob of Ectoplasm
        19675: 3.50,   # Mystic Clover (Forge expected cost)
        18845: 1.00,   # Icy Runestone (Fixed vendor cost)
        24562: 4.50,   # Superior Sigil of Force
        19628: 180.0,  # Gift of Magic (T6 fine mats total)
        19629: 175.0,  # Gift of Might (T6 fine mats total)
        19641: 35.0,   # Gift of Metal (Ingots)
        19640: 30.0,   # Gift of Darkness (Dungeon tokens + Darksteel)
        89140: 0.05,   # Pile of Lucent Crystal
        89175: 1.20,   # Mystic Mote
        89258: 0.35,   # Symbol of Control
        89182: 0.35,   # Symbol of Enhancement
        89216: 0.35,   # Symbol of Pain
        19725: 0.30,   # Vicious Claw
        19734: 0.30,   # Armored Scale
        19723: 0.25,   # Ancient Bone
        19728: 0.25,   # Vicious Fang
        19748: 0.45,   # Powerful Blood
        19745: 0.30,   # Potent Venom Sac
        19746: 0.35,   # Elaborate Totem
        19732: 0.20,   # Crystalline Dust
    }

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
        prices = dict(self.DEFAULT_PRICES)
        if tp_prices:
            prices.update(tp_prices)

        missing = diff_report.summary_missing_materials
        excluded = excluded_modes or []
        exhausted = exhausted_sources or []
        target_qty = diff_report.target_quantity

        # 1. Precursor Strategy (for weapons)
        precursor_strat = None
        dusk_cost = 0.0
        if diff_report.goal_item_id == 30699: # Twilight
            if "Dusk" not in missing:
                precursor_strat = "✅ Dusk is already owned in your inventory/bank. (0 gold needed)"
            else:
                dusk_buy_order = prices.get(29185, 280.0) * 0.85
                dusk_instant = prices.get(29185, 280.0)
                precursor_strat = (
                    f"Place a Trading Post **Buy Order** for Dusk at ~{dusk_buy_order:.0f} gold "
                    f"(saves ~{dusk_instant - dusk_buy_order:.0f}g over instant buy at {dusk_instant:.0f}g). "
                    f"Alternatively, craft via Tier 1-3 Precursor Collections if you enjoy the lore journey."
                )
                dusk_cost = dusk_buy_order

        # 2. Mystic Clover Optimization with Exhausted Sources Awareness
        clover_options = []
        clovers_needed = missing.get("Mystic Clover", 0)

        if clovers_needed > 0:
            vault_available = "WizardVault" not in exhausted
            # Option A: Wizard's Vault (Astral Acclaim)
            if vault_available:
                clovers_from_vault = min(clovers_needed, 20)
                clover_options.append(CloverStrategyOption(
                    source_name="Wizard's Vault (Astral Acclaim)",
                    clovers_obtainable=clovers_from_vault,
                    estimated_gold_cost=0.0,
                    required_currencies={"Astral Acclaim": clovers_from_vault * 6},
                    time_gate_note="Seasonal limit (20 clovers per refresh)",
                    recommended=True
                ))

            # Option B: Fractal Relic Vendor
            if "Fractals" not in excluded:
                is_rec = not vault_available
                clover_options.append(CloverStrategyOption(
                    source_name="Fractal Relic Vendor (BUY-2046 in Mistlock Sanctuary)",
                    clovers_obtainable=min(clovers_needed, 10),
                    estimated_gold_cost=min(clovers_needed, 10) * 1.5,
                    required_currencies={"Fractal Relic": min(clovers_needed, 10) * 150, "Spirit Shard": min(clovers_needed, 10) * 2},
                    time_gate_note="2 clovers per day limit",
                    recommended=is_rec
                ))

            # Option C: WvW / PvP Reward Tracks
            if "WvW" not in excluded:
                clover_options.append(CloverStrategyOption(
                    source_name="WvW / PvP Reward Tracks (Gift of Battle track)",
                    clovers_obtainable=min(clovers_needed, 14),
                    estimated_gold_cost=0.0,
                    required_currencies={},
                    time_gate_note="~4 to 8 hours of active gameplay per 2 clovers",
                    recommended=False
                ))

            # Option D: Mystic Forge Gambling (Fallback)
            clover_options.append(CloverStrategyOption(
                source_name="Mystic Forge Promotion (Clover Recipe)",
                clovers_obtainable=clovers_needed,
                estimated_gold_cost=clovers_needed * 3.50,
                required_currencies={"Spirit Shards": int(clovers_needed * 0.6), "Obsidian Shards": int(clovers_needed * 3.16)},
                time_gate_note="No time gate (unlimited, but probabilistic ~31.6% yield)",
                recommended=(not vault_available and "Fractals" in excluded)
            ))

        # 3. Calculate Estimated Total Gold Cost
        total_gold = dusk_cost
        total_gold += missing.get("Glob of Ectoplasm", 0) * prices.get(19721, 0.22)
        total_gold += missing.get("Icy Runestone", 0) * 1.0
        total_gold += missing.get("Superior Sigil of Force", 0) * prices.get(24562, 4.5)
        total_gold += missing.get("Gift of Magic", 0) * prices.get(19628, 180.0)
        total_gold += missing.get("Gift of Might", 0) * prices.get(19629, 175.0)
        total_gold += missing.get("Gift of Metal", 0) * prices.get(19641, 35.0)
        total_gold += missing.get("Gift of Darkness", 0) * prices.get(19640, 30.0)
        total_gold += missing.get("Pile of Lucent Crystal", 0) * prices.get(89140, 0.05)
        total_gold += missing.get("Symbol of Control", 0) * prices.get(89258, 0.35)
        total_gold += missing.get("Symbol of Enhancement", 0) * prices.get(89182, 0.35)
        total_gold += missing.get("Symbol of Pain", 0) * prices.get(89216, 0.35)
        total_gold += missing.get("Vicious Claw", 0) * prices.get(19725, 0.30)
        total_gold += missing.get("Armored Scale", 0) * prices.get(19734, 0.30)
        total_gold += missing.get("Ancient Bone", 0) * prices.get(19723, 0.25)
        total_gold += missing.get("Vicious Fang", 0) * prices.get(19728, 0.25)
        total_gold += missing.get("Powerful Blood", 0) * prices.get(19748, 0.45)
        total_gold += missing.get("Potent Venom Sac", 0) * prices.get(19745, 0.30)
        total_gold += missing.get("Elaborate Totem", 0) * prices.get(19746, 0.35)
        total_gold += missing.get("Crystalline Dust", 0) * prices.get(19732, 0.20)

        # 4. Identify Non-Negotiable Bottlenecks
        bottlenecks = []
        if missing.get("Gift of Exploration"):
            bottlenecks.append("🗺️ **Gift of Exploration:** Requires 100% Core Tyria Map Completion (Cannot be bought with gold).")
        if missing.get("Gift of Battle"):
            bottlenecks.append("⚔️ **Gift of Battle:** Requires completing the WvW Gift of Battle Reward Track (~4-8 hours WvW).")
        if missing.get("Bloodstone Shard"):
            bottlenecks.append("🔮 **Bloodstone Shard:** Requires 200 Spirit Shards from Miyani at the Mystic Forge.")
        if missing.get("Gift of Craftsmanship"):
            tokens_needed = 50 * target_qty
            bottlenecks.append(f"🏛️ **Gift of Craftsmanship ({tokens_needed} Provisioner Tokens):** Requires daily item trades with Faction Provisioners across HoT maps and major cities.")
        if diff_report.missing_disciplines:
            for d in diff_report.missing_disciplines:
                bottlenecks.append(f"🔨 **{d['discipline'].capitalize()} Level {d['required_rating']}:** Required to craft weapon or upgrade gifts.")

        # 5. Build Roadmap
        roadmap = []
        if diff_report.missing_disciplines:
            roadmap.append({
                "phase": "Phase 1: Crafting Discipline Setup",
                "action": f"Level crafting disciplines to {max(d['required_rating'] for d in diff_report.missing_disciplines)} using discovery guides.",
                "est_cost": "15-25 gold"
            })

        if missing.get("Gift of Craftsmanship"):
            roadmap.append({
                "phase": "Phase 2: Daily Provisioner Token Route",
                "action": f"Do daily Faction Provisioner trades (Verdant Brink, Auric Basin, Tangled Depths, Black Citadel) to collect {50 * target_qty} Provisioner Tokens.",
                "est_cost": "5-10 gold/day"
            })

        roadmap.append({
            "phase": "Phase 3: Guaranteed Clovers & Time-Gated Vendors",
            "action": "Claim alternative clover vendor routes or Mystic Forge promotions.",
            "est_cost": "0-15 gold"
        })

        roadmap.append({
            "phase": "Phase 4: Trading Post Materials & Mystic Forge Assembly",
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
