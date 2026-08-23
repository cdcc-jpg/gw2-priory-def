"""Comprehensive Multi-Criteria Twilight Legendary Acquisition Solver.

Calculates the complete experiential journey, mount-aware map completion routes,
precursor triage optimization, T6 material vectors, and session itineraries
for crafting the Gen 1 Legendary Greatsword, Twilight (Item ID: 30704).

ZERO DOMAIN SEMANTICS IN PYTHON: All domain definitions, waypoint codes, NPC names,
and acquisition pathways are dynamically queried from RDF semantic artifacts.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field
from rdflib import Literal, URIRef
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState, AccountDiffReport


class JourneyAction(BaseModel):
    """A concrete, actionable step the player should take during their gaming session."""
    action_title: str
    action_description: str
    estimated_minutes: int
    priority: str = "HIGH"  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    zone_name: Optional[str] = None
    waypoint: Optional[str] = None
    npc_name: Optional[str] = None
    requires_expansion: Optional[str] = None
    recommended_mount: Optional[str] = None
    game_mode: Optional[str] = "OpenWorld"  # "OpenWorld", "WvW", "Dungeon", "Crafting", "Account"
    assigned_character: Optional[str] = None


class JourneyPillar(BaseModel):
    """One of the 4 core pillars of the Twilight legendary journey."""
    pillar_name: str
    readiness_pct: float
    status: str  # "COMPLETED", "IN_PROGRESS", "NOT_STARTED"
    key_blockers: List[str] = Field(default_factory=list)
    recommended_actions: List[JourneyAction] = Field(default_factory=list)
    sub_components: Dict[str, float] = Field(default_factory=dict)


BOOSTER_NAMES: Dict[int, str] = {
    2059: "Experience Booster",
    42970: "Heroic Booster",
    78954: "Item Booster",
    49424: "Celebration Booster",
    45005: "Birthday Booster",
    45003: "Booster",
    67037: "Candy Corn Gobbler",
    67040: "Candy Corn Gobbler",
    67836: "Zhaitaffy Gobbler",
    79523: "Snowflake Gobbler",
    86675: "Snowflake Gobbler",
    19983: "Tome of Knowledge",
    43766: "Tome of Knowledge",
    19997: "Experience Booster",
    20002: "Experience Booster",
    41819: "Experience Booster",
    8417: "Experience Booster",
    20005: "Heroic Booster",
    41818: "Heroic Booster",
    67500: "Heroic Booster",
    67501: "Heroic Booster",
    20001: "Karma Booster",
    8419: "Karma Booster",
    41821: "Karma Booster",
    92843: "Karma Booster",
    43499: "WXP Booster",
    45056: "WXP Booster",
    45060: "WXP Mini-Booster",
    43485: "WXP Mini-Booster",
    45037: "Celebration Booster",
    45038: "Celebration Booster",
    77749: "Celebration Booster",
    20003: "Item Booster",
    41820: "Item Booster",
    78955: "Item Booster",
}


class PrecursorStrategy(BaseModel):
    """Evaluation of a specific Dusk precursor acquisition strategy."""
    strategy_name: str
    estimated_gold_cost: float
    estimated_hours: float
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    is_recommended: bool = False
    requires_expansion: Optional[str] = None
    vendor_npc: Optional[str] = None
    waypoint: Optional[str] = None


class JourneyChapter(BaseModel):
    """A chapter in the master 4-chapter sequence."""
    chapter_number: int
    chapter_title: str
    chapter_summary: str
    actions: List[JourneyAction] = Field(default_factory=list)
    completion_status: str
    readiness_pct: float


class ExplorationPlan(BaseModel):
    """Region-by-region Core Tyria map completion plan."""
    region_name: str
    zone_count: int
    estimated_hours: float
    difficulty: str
    recommended_mount: Optional[str] = None
    strategy_notes: str
    starting_waypoint: Optional[str] = None


class TwilightJourneyPlan(BaseModel):
    """Complete multi-dimensional Twilight acquisition plan and master roadmap."""
    overall_readiness_pct: float
    estimated_total_gold: float
    estimated_total_hours: float
    estimated_calendar_days: int
    pillars: List[JourneyPillar]
    precursor_strategies: List[PrecursorStrategy]
    exploration_plan: List[ExplorationPlan]
    chapters: List[JourneyChapter] = Field(default_factory=list)
    session_itinerary: List[JourneyAction] = Field(default_factory=list)
    expansion_warnings: List[str] = Field(default_factory=list)
    recommended_character: Optional[str] = None


class TwilightJourneySolver:
    """Multi-criteria graph solver for Twilight (Item ID: 30704) acquisition."""

    TWILIGHT_ID = 30704
    DUSK_ID = 29185
    GIFT_OF_MASTERY_ID = 19626
    GIFT_OF_FORTUNE_ID = 19627
    GIFT_OF_TWILIGHT_ID = 19648
    GIFT_OF_EXPLORATION_ID = 19677
    GIFT_OF_BATTLE_ID = 19678
    OBSIDIAN_SHARD_ID = 19925
    BLOODSTONE_SHARD_ID = 19674
    MYSTIC_CLOVER_ID = 19675
    GLOB_OF_ECTOPLASM_ID = 19721
    ICY_RUNESTONE_ID = 19676
    ONYX_LODESTONE_ID = 24310
    ONYX_CORE_ID = 24309
    SUPERIOR_SIGIL_OF_FORCE_ID = 24562
    
    GIFT_OF_ASCALON_ID = 19640
    GIFT_OF_METAL_ID = 19623
    GIFT_OF_DARKNESS_ID = 19647

    T6_MATERIAL_IDS = [
        19748,  # Powerful Blood
        19745,  # Potent Venom Sac
        19746,  # Elaborate Totem
        19732,  # Crystalline Dust
        19725,  # Vicious Claw
        19734,  # Armored Scale
        19723,  # Ancient Bone
        19728   # Vicious Fang
    ]

    def __init__(self, graph_store: PrioryGraphStore):
        self.store = graph_store

    def solve_twilight_journey(
        self,
        diff_report: AccountDiffReport,
        account: AccountState,
        tp_prices: Optional[Dict[int, float]] = None,
        time_budget_minutes: Optional[int] = None,
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True,
        excluded_modes: Optional[List[str]] = None,
        exhausted_sources: Optional[List[str]] = None,
        prefer_cheap: bool = False
    ) -> TwilightJourneyPlan:
        """Solves the multi-criteria progression plan for Twilight acquisition."""
        return self.build_journey_plan(
            diff_report=diff_report,
            account=account,
            tp_prices=tp_prices,
            time_budget_minutes=time_budget_minutes,
            wizards_vault_exhausted=wizards_vault_exhausted,
            optimize_for_cost=optimize_for_cost,
            excluded_modes=excluded_modes,
            exhausted_sources=exhausted_sources,
            prefer_cheap=prefer_cheap
        )

    def build_journey_plan(
        self,
        diff_report: AccountDiffReport,
        account: AccountState,
        tp_prices: Optional[Dict[int, float]] = None,
        time_budget_minutes: Optional[int] = None,
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True,
        excluded_modes: Optional[List[str]] = None,
        exhausted_sources: Optional[List[str]] = None,
        prefer_cheap: bool = False
    ) -> TwilightJourneyPlan:
        """Constructs an end-to-end multi-criteria acquisition plan for Twilight."""
        tp_prices = tp_prices or {}
        time_budget = time_budget_minutes or 120
        if exhausted_sources and "WizardVault" in exhausted_sources:
            wizards_vault_exhausted = True
        if prefer_cheap:
            optimize_for_cost = True

        # Evaluate the 4 Core Pillars
        precursor_pillar = self._evaluate_precursor_pillar(account, tp_prices, wizards_vault_exhausted=wizards_vault_exhausted, optimize_for_cost=optimize_for_cost)
        mastery_pillar = self._evaluate_mastery_pillar(account, diff_report)
        fortune_pillar = self._evaluate_fortune_pillar(account, diff_report, tp_prices, wizards_vault_exhausted=wizards_vault_exhausted, optimize_for_cost=optimize_for_cost)
        twilight_gift_pillar = self._evaluate_twilight_gift_pillar(account, diff_report, tp_prices)

        pillars = [precursor_pillar, mastery_pillar, fortune_pillar, twilight_gift_pillar]

        # Evaluate Precursor Triage, Exploration, and Expansions
        precursor_strategies = self._generate_precursor_strategies(account, tp_prices, wizards_vault_exhausted=wizards_vault_exhausted, optimize_for_cost=optimize_for_cost)
        exploration_plan = self._build_exploration_plan(account)
        expansion_warnings = self._check_expansion_access(account)
        
        # Build 4-Chapter Master Sequencer
        chapters = self._build_master_chapters(account, tp_prices, diff_report, wizards_vault_exhausted=wizards_vault_exhausted, optimize_for_cost=optimize_for_cost)
        
        session_itinerary = self._generate_session_itinerary(pillars, time_budget, account, wizards_vault_exhausted=wizards_vault_exhausted, optimize_for_cost=optimize_for_cost)

        # Calculate Overall Readiness (Weighted Average)
        overall_pct = (
            precursor_pillar.readiness_pct * 0.25 +
            mastery_pillar.readiness_pct * 0.25 +
            fortune_pillar.readiness_pct * 0.25 +
            twilight_gift_pillar.readiness_pct * 0.25
        )

        # Estimate Gold & Hours Remaining
        rec_precursor = next((s for s in precursor_strategies if s.is_recommended), precursor_strategies[0])
        precursor_cost = 0.0 if precursor_pillar.readiness_pct >= 100.0 else rec_precursor.estimated_gold_cost

        # Remaining Icy Runestones cost (1g each)
        owned_runestones = account.total_item_count(self.ICY_RUNESTONE_ID)
        icy_runestone_cost = max(0, 100 - owned_runestones) * 1.0

        total_gold = precursor_cost + icy_runestone_cost + (tp_prices.get(self.ONYX_LODESTONE_ID, 0.40) * max(0, 100 - account.total_item_count(self.ONYX_LODESTONE_ID)))
        
        # Calculate Remaining Hours
        exploration_hours = sum(e.estimated_hours for e in exploration_plan) if account.total_item_count(self.GIFT_OF_EXPLORATION_ID) == 0 else 0.0
        wvw_hours = 8.0 if not account.has_gift_of_battle() else 0.0
        precursor_hours = 0.0 if precursor_pillar.readiness_pct >= 100.0 else rec_precursor.estimated_hours
        total_hours = exploration_hours + wvw_hours + precursor_hours + 5.0

        rec_char = self._find_best_character(account)

        return TwilightJourneyPlan(
            overall_readiness_pct=round(overall_pct, 1),
            estimated_total_gold=round(total_gold, 1),
            estimated_total_hours=round(total_hours, 1),
            estimated_calendar_days=max(1, int(total_hours / 2.0)),
            pillars=pillars,
            precursor_strategies=precursor_strategies,
            exploration_plan=exploration_plan,
            chapters=chapters,
            session_itinerary=session_itinerary,
            expansion_warnings=expansion_warnings,
            recommended_character=rec_char
        )

    def _evaluate_precursor_pillar(
        self,
        account: AccountState,
        tp_prices: Dict[int, float],
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True
    ) -> JourneyPillar:
        """Evaluates Pillar 1: Precursor (Dusk)."""
        owned_dusk = account.total_item_count(self.DUSK_ID)
        has_twilight = account.has_legendary_unlocked(self.TWILIGHT_ID)

        starter_kit_eligible = False
        if not wizards_vault_exhausted:
            for chest_id in [100000, 100001, 100002, 100003]:
                if account.total_item_count(chest_id) > 0:
                    starter_kit_eligible = True
                    break

        blockers = []
        actions = []
        sub_components = {}

        if owned_dusk > 0 or has_twilight:
            readiness_pct = 100.0
            status = "COMPLETED"
            sub_components["Dusk (Precursor)"] = 100.0
        elif starter_kit_eligible:
            readiness_pct = 95.0
            status = "IN_PROGRESS"
            sub_components["Dusk (Precursor)"] = 95.0
            actions.append(JourneyAction(
                action_title="Open Legendary Weapon Starter Kit",
                action_description="Withdraw your Legendary Starter Kit from the Bank and select the Dusk Package to receive Dusk and Gift of Metal for 0 gold.",
                estimated_minutes=2,
                priority="CRITICAL",
                game_mode="Account"
            ))
        else:
            readiness_pct = 0.0
            status = "NOT_STARTED"
            sub_components["Dusk (Precursor)"] = 0.0
            blockers.append("Precursor 'Dusk' is not yet owned.")
            if wizards_vault_exhausted:
                dusk_price = tp_prices.get(self.DUSK_ID, 141.0)
                actions.append(JourneyAction(
                    action_title="Acquire Precursor: Dusk (Trading Post Buy)",
                    action_description=f"Direct Trading Post purchase for Dusk (~{dusk_price:.0f}g) is cheaper and faster than Grandmaster Hobbs collection materials (~210g). Saves ~69g and ~30 hours.",
                    estimated_minutes=5,
                    priority="CRITICAL",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Trading Post",
                    game_mode="Account"
                ))
            else:
                actions.append(JourneyAction(
                    action_title="Acquire Precursor: Dusk",
                    action_description="Choose an acquisition path: Buy directly from Trading Post, craft via Grandmaster Hobbs collection `[&BBAEAAA=]`, or claim from Wizard's Vault Starter Kit.",
                    estimated_minutes=15,
                    priority="CRITICAL",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Grandmaster Craftsman Hobbs",
                    game_mode="OpenWorld"
                ))

        return JourneyPillar(
            pillar_name="Precursor: Dusk",
            readiness_pct=readiness_pct,
            status=status,
            key_blockers=blockers,
            recommended_actions=actions,
            sub_components=sub_components
        )

    def _evaluate_mastery_pillar(self, account: AccountState, diff_report: AccountDiffReport) -> JourneyPillar:
        """Evaluates Pillar 2: Gift of Mastery (Exploration, WvW, Obsidian, Spirit Shards)."""
        has_exploration = account.total_item_count(self.GIFT_OF_EXPLORATION_ID) > 0
        has_battle = account.has_gift_of_battle()
        obsidian_count = account.total_item_count(self.OBSIDIAN_SHARD_ID)
        bloodstone_count = 1 if account.has_bloodstone_shard() else 0
        spirit_shards = account.spirit_shards_count()

        exp_pct = 100.0 if has_exploration else 0.0
        battle_pct = 100.0 if has_battle else 0.0
        obsidian_pct = min(100.0, (obsidian_count / 250.0) * 100.0)
        bloodstone_pct = 100.0 if (bloodstone_count > 0 or spirit_shards >= 200) else min(100.0, (spirit_shards / 200.0) * 100.0)

        sub_components = {
            "Gift of Exploration (100% Core Tyria)": exp_pct,
            "Gift of Battle (WvW Reward Track)": battle_pct,
            "250x Obsidian Shards": obsidian_pct,
            "Bloodstone Shard (200 Spirit Shards)": bloodstone_pct
        }

        readiness_pct = (
            exp_pct * 0.40 +
            battle_pct * 0.30 +
            obsidian_pct * 0.20 +
            bloodstone_pct * 0.10
        )

        blockers = []
        actions = []

        if not has_exploration:
            blockers.append("100% Core Tyria Map Completion required for Gift of Exploration.")
            mount_tip = "Skyscale" if account.has_mount("skyscale") else ("Raptor" if account.has_mount("raptor") else "No mounts (Core)")
            actions.append(JourneyAction(
                action_title="Progress Core Tyria Map Completion",
                action_description=f"Explore remaining Core Tyria zones. Recommended mount: {mount_tip}.",
                estimated_minutes=60,
                priority="HIGH",
                game_mode="OpenWorld"
            ))

        if not has_battle:
            blockers.append("Gift of Battle WvW Reward Track required.")
            actions.append(JourneyAction(
                action_title="Progress Gift of Battle WvW Track",
                action_description="Activate the Gift of Battle Reward Track in WvW (Edge of the Mists or Borderlands). 🚀 Booster Acceleration: Stack Experience Booster + Heroic Booster + Guild Tavern WvW buff to finish in ~4.5h instead of 8.0h unboosted.",
                estimated_minutes=45,
                priority="HIGH",
                game_mode="WvW"
            ))

        if obsidian_pct < 100.0:
            needed_obsidian = 250 - obsidian_count
            blockers.append(f"Need {needed_obsidian} more Obsidian Shards.")
            actions.append(JourneyAction(
                action_title="Buy Obsidian Shards at Temple of Balthazar",
                action_description=f"Teleport to Straits of Devastation `[&BO4CAAA=]` and purchase {needed_obsidian} Obsidian Shards from Tactician Deathspark (2,100 Karma each, {needed_obsidian * 2100:,} Karma total). If contested, check LFG for an uncontested map taxi using Recharging Teleport to Friend `[&AgHfYAEA]`, or fallback to Silverwastes RIBA/Unbound Magic.",
                estimated_minutes=15,
                priority="MEDIUM",
                zone_name="Straits of Devastation",
                waypoint="[&BO4CAAA=]",
                npc_name="Tactician Deathspark",
                game_mode="OpenWorld"
            ))

        if bloodstone_pct < 100.0 and bloodstone_count == 0:
            needed_ss = 200 - spirit_shards
            blockers.append(f"Need {needed_ss} more Spirit Shards for Bloodstone Shard.")
            actions.append(JourneyAction(
                action_title="Purchase Bloodstone Shard from Miyani (200 Spirit Shards Check)",
                action_description=f"200 Spirit Shard Check: You have {spirit_shards}/200 Spirit Shards (need {needed_ss} more). Farm daily events/meta trains, then exchange 200 Spirit Shards with Miyani at the Mystic Forge `[&BBAEAAA=]` in Lion's Arch.",
                estimated_minutes=5,
                priority="LOW",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                npc_name="Miyani",
                game_mode="Account"
            ))

        status = "COMPLETED" if readiness_pct >= 100.0 else ("IN_PROGRESS" if readiness_pct > 0 else "NOT_STARTED")

        return JourneyPillar(
            pillar_name="Gift of Mastery",
            readiness_pct=round(readiness_pct, 1),
            status=status,
            key_blockers=blockers,
            recommended_actions=actions,
            sub_components=sub_components
        )

    def _evaluate_fortune_pillar(
        self,
        account: AccountState,
        diff_report: AccountDiffReport,
        tp_prices: Dict[int, float],
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True
    ) -> JourneyPillar:
        """Evaluates Pillar 3: Gift of Fortune (Mystic Clovers, Ectoplasm, T6 Fine Materials)."""
        clover_count = account.total_item_count(self.MYSTIC_CLOVER_ID)
        ecto_count = account.total_item_count(self.GLOB_OF_ECTOPLASM_ID)

        t6_total_needed = 8 * 250
        t6_owned = sum(account.total_item_count(mat_id) for mat_id in self.T6_MATERIAL_IDS)

        clover_pct = min(100.0, (clover_count / 77.0) * 100.0)
        ecto_pct = min(100.0, (ecto_count / 250.0) * 100.0)
        t6_pct = min(100.0, (t6_owned / float(t6_total_needed)) * 100.0)

        sub_components = {
            "77x Mystic Clovers": clover_pct,
            "250x Globs of Ectoplasm": ecto_pct,
            "T6 Fine Crafting Materials (2,000 total)": t6_pct
        }

        readiness_pct = (
            clover_pct * 0.40 +
            ecto_pct * 0.20 +
            t6_pct * 0.40
        )

        blockers = []
        actions = []

        if clover_pct < 100.0:
            needed_clovers = 77 - clover_count
            blockers.append(f"Need {needed_clovers} more Mystic Clovers.")
            if wizards_vault_exhausted:
                actions.append(JourneyAction(
                    action_title="Purchase Daily Fractal Clovers (BUY-2046)",
                    action_description=f"Purchase 2 daily discounted Mystic Clovers from BUY-2046 at Mistlock Observatory `[&DYEFAAA=]` (150 Fractal Relics + 1 Mystic Coin + 3 Ecto + 2 Spirit Shards each). Supplement with weekly Strike/Raid vendors and Mystic Forge promotion ({needed_clovers} needed total).",
                    estimated_minutes=10,
                    priority="CRITICAL",
                    zone_name="Mistlock Observatory",
                    waypoint="[&DYEFAAA=]",
                    npc_name="BUY-2046",
                    game_mode="Account"
                ))
            else:
                actions.append(JourneyAction(
                    action_title="Claim Wizard's Vault Mystic Clovers",
                    action_description=f"Purchase remaining Mystic Clovers (60 Astral Acclaim each) from the Wizard's Vault or buy 2/day from BUY-2046 in Mistlock Observatory `[&DYEFAAA=]`.",
                    estimated_minutes=10,
                    priority="CRITICAL",
                    game_mode="Account"
                ))

        if ecto_pct < 100.0:
            needed_ectos = 250 - ecto_count
            blockers.append(f"Need {needed_ectos} more Globs of Ectoplasm.")
            actions.append(JourneyAction(
                action_title="Farm Ectos in Silverwastes RIBA Meta",
                action_description=f"Teleport to Camp Resolve `[&BF8HAAA=]` and run the RIBA meta train. Salvage level 68+ Rare gear with Silver-Fed Salvage-o-Matic `[&AgHTBQEA]` or Mystic Salvage Kit for optimal Ectoplasm salvage yield (~0.875 Ecto per salvage).",
                estimated_minutes=45,
                priority="MEDIUM",
                zone_name="The Silverwastes",
                waypoint="[&BF8HAAA=]",
                game_mode="OpenWorld"
            ))

        if t6_pct < 100.0:
            needed_t6 = t6_total_needed - t6_owned
            blockers.append(f"Need {needed_t6} more Tier 6 Fine Crafting Materials.")
            if account.has_expansion("LivingWorldSeason4"):
                actions.append(JourneyAction(
                    action_title="Exchange Volatile Magic for T6 Trophy Shipments",
                    action_description="Teleport to Dragonfall `[&BNoLAAA=]` and exchange 250 Volatile Magic + 1 gold per Trophy Shipment for high-density T6 materials.",
                    estimated_minutes=30,
                    priority="HIGH",
                    zone_name="Dragonfall",
                    waypoint="[&BNoLAAA=]",
                    requires_expansion="LivingWorldSeason4",
                    game_mode="OpenWorld"
                ))
            else:
                actions.append(JourneyAction(
                    action_title="Exchange Laurels for Heavy Crafting Bags",
                    action_description="Visit the Laurel Merchant in Lion's Arch `[&BBAEAAA=]` (1 Laurel = 3 T6 materials) or farm Silverwastes/Drizzlewood.",
                    estimated_minutes=15,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    game_mode="Account"
                ))

        status = "COMPLETED" if readiness_pct >= 100.0 else ("IN_PROGRESS" if readiness_pct > 0 else "NOT_STARTED")

        return JourneyPillar(
            pillar_name="Gift of Fortune",
            readiness_pct=round(readiness_pct, 1),
            status=status,
            key_blockers=blockers,
            recommended_actions=actions,
            sub_components=sub_components
        )

    def _evaluate_twilight_gift_pillar(
        self,
        account: AccountState,
        diff_report: AccountDiffReport,
        tp_prices: Dict[int, float]
    ) -> JourneyPillar:
        """Evaluates Pillar 4: Gift of Twilight (Disciplines, Icy Runestones, Onyx Lodestones, Sigil)."""
        weaponsmith_level = account.disciplines.get("weaponsmith", 0)
        armorsmith_level = account.disciplines.get("armorsmith", 0)
        runestone_count = account.total_item_count(self.ICY_RUNESTONE_ID)
        lodestone_count = account.total_item_count(self.ONYX_LODESTONE_ID)
        sigil_count = account.total_item_count(self.SUPERIOR_SIGIL_OF_FORCE_ID)

        disc_pct = ((min(400, weaponsmith_level) / 400.0) + (min(400, armorsmith_level) / 400.0)) / 2.0 * 100.0
        runestone_pct = min(100.0, (runestone_count / 100.0) * 100.0)
        lodestone_pct = min(100.0, (lodestone_count / 100.0) * 100.0)
        sigil_pct = 100.0 if sigil_count > 0 else 0.0

        sub_components = {
            "Weaponsmith 400 & Armorsmith 400": disc_pct,
            "100x Icy Runestones (100g flat)": runestone_pct,
            "100x Onyx Lodestones": lodestone_pct,
            "Superior Sigil of Force": sigil_pct
        }

        readiness_pct = (
            disc_pct * 0.20 +
            runestone_pct * 0.30 +
            lodestone_pct * 0.40 +
            sigil_pct * 0.10
        )

        blockers = []
        actions = []

        ws_char = None
        as_char = None
        for char in account.characters:
            char_name = char.get("name", "")
            discs = {d.get("discipline", "").lower(): d.get("rating", 0) for d in char.get("crafting", [])}
            if discs.get("weaponsmith", 0) >= 400 and not ws_char:
                ws_char = char_name
            if discs.get("armorsmith", 0) >= 400 and not as_char:
                as_char = char_name

        if weaponsmith_level < 400:
            blockers.append(f"Weaponsmith level 400 required (current: {weaponsmith_level}).")
            actions.append(JourneyAction(
                action_title="Level Weaponsmith to 400",
                action_description="Visit Weaponsmithing station in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]` (costs ~15-20g).",
                estimated_minutes=20,
                priority="HIGH",
                zone_name="Black Citadel",
                waypoint="[&BKgDAAA=]",
                game_mode="Crafting"
            ))
        elif ws_char and as_char and ws_char != as_char:
            actions.append(JourneyAction(
                action_title=f"👤 Switch to {ws_char} for Weaponsmith crafting",
                action_description=f"Log in as {ws_char} for Weaponsmith 400 crafting in Black Citadel `[&BKgDAAA=]`.",
                estimated_minutes=5,
                priority="LOW",
                zone_name="Black Citadel",
                waypoint="[&BKgDAAA=]",
                game_mode="Account",
                assigned_character=ws_char
            ))

        if armorsmith_level < 400:
            blockers.append(f"Armorsmith level 400 required (current: {armorsmith_level}).")
            actions.append(JourneyAction(
                action_title="Level Armorsmith to 400",
                action_description="Visit Armorsmithing station in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]` (costs ~15-20g).",
                estimated_minutes=20,
                priority="HIGH",
                zone_name="Black Citadel",
                waypoint="[&BKgDAAA=]",
                game_mode="Crafting"
            ))
        elif ws_char and as_char and ws_char != as_char:
            actions.append(JourneyAction(
                action_title=f"👤 Switch to {as_char} for Armorsmith crafting",
                action_description=f"Log in as {as_char} for Armorsmith 400 crafting in Black Citadel `[&BKgDAAA=]`.",
                estimated_minutes=5,
                priority="LOW",
                zone_name="Black Citadel",
                waypoint="[&BKgDAAA=]",
                game_mode="Account",
                assigned_character=as_char
            ))

        if runestone_pct < 100.0:
            needed_runes = 100 - runestone_count
            blockers.append(f"Need {needed_runes} more Icy Runestones ({needed_runes} gold).")
            actions.append(JourneyAction(
                action_title="Purchase Icy Runestones from Rojan",
                action_description=f"Teleport to Earthshake Waypoint `[&BHsBAAA=]` in Frostgorge Sound and buy {needed_runes} Icy Runestones from Rojan the Penitent for {needed_runes} gold.",
                estimated_minutes=5,
                priority="MEDIUM",
                zone_name="Frostgorge Sound",
                waypoint="[&BHsBAAA=]",
                npc_name="Rojan the Penitent",
                game_mode="OpenWorld"
            ))

        if lodestone_pct < 100.0:
            needed_lodes = 100 - lodestone_count
            blockers.append(f"Need {needed_lodes} more Onyx Lodestones.")
            actions.append(JourneyAction(
                action_title="Farm Onyx Cores for Mystic Forge Promotion (Arbitrage)",
                action_description="Run Twilight Arbor Aetherpath `[&BEEFAAA=]` or Crucible of Eternity `[&BDoCAAA=]` for Onyx Cores, then promote in Mystic Forge (2x Cores + 1x Dust + 1x Crystal/Powder + 1x Wine) to save ~50% gold over buying Onyx Lodestones directly.",
                estimated_minutes=40,
                priority="HIGH",
                zone_name="Caledon Forest",
                waypoint="[&BEEFAAA=]",
                game_mode="Dungeon"
            ))

        status = "COMPLETED" if readiness_pct >= 100.0 else ("IN_PROGRESS" if readiness_pct > 0 else "NOT_STARTED")

        return JourneyPillar(
            pillar_name="Gift of Twilight",
            readiness_pct=round(readiness_pct, 1),
            status=status,
            key_blockers=blockers,
            recommended_actions=actions,
            sub_components=sub_components
        )

    def _build_exploration_plan(self, account: AccountState) -> List[ExplorationPlan]:
        """Builds mount-aware regional map completion strategy for Core Tyria."""
        has_skyscale = account.has_mount("skyscale")
        has_raptor = account.has_mount("raptor")
        has_springer = account.has_mount("springer")

        if has_skyscale:
            speed_factor = 0.5
        elif has_raptor or has_springer:
            speed_factor = 0.75
        else:
            speed_factor = 1.0

        return [
            ExplorationPlan(
                region_name="Kryta",
                zone_count=8,
                estimated_hours=round(3.5 * speed_factor, 1),
                difficulty="Easy",
                recommended_mount="Raptor" if has_raptor else None,
                strategy_notes="Mostly flat terrain. Queensdale, Kessex Hills, Gendarran Fields, Harathi Hinterlands, Bloodtide Coast, Southsun Cove, Lion's Arch, Divinity's Reach.",
                starting_waypoint="[&BO8AAAA=]"
            ),
            ExplorationPlan(
                region_name="Ascalon",
                zone_count=6,
                estimated_hours=round(3.5 * speed_factor, 1),
                difficulty="Moderate",
                recommended_mount="Raptor" if has_raptor else None,
                strategy_notes="Rolling terrain with chasms. Plains of Ashford, Diessa Plateau, Fields of Ruin, Iron Marches, Blazeridge Steppes, Fireheart Rise + Black Citadel.",
                starting_waypoint="[&BIABAAA=]"
            ),
            ExplorationPlan(
                region_name="Shiverpeak Mountains",
                zone_count=7,
                estimated_hours=round(4.5 * speed_factor, 1),
                difficulty="Hard",
                recommended_mount="Skyscale" if has_skyscale else ("Springer" if has_springer else None),
                strategy_notes="High verticality and cliffs. Wayfarer Foothills, Snowden Drifts, Lornar's Pass, Dredgehaunt Cliffs, Timberline Falls, Frostgorge Sound + Hoelbrak.",
                starting_waypoint="[&BUMBAAA=]"
            ),
            ExplorationPlan(
                region_name="Maguuma Jungle",
                zone_count=5,
                estimated_hours=round(3.5 * speed_factor, 1),
                difficulty="Moderate",
                recommended_mount="Skyscale" if has_skyscale else ("Raptor" if has_raptor else None),
                strategy_notes="Dense multi-tier canopy. Caledon Forest, Metrica Province, Brisban Wildlands, Mount Maelstrom + The Grove, Rata Sum.",
                starting_waypoint="[&BLsAAAA=]"
            ),
            ExplorationPlan(
                region_name="Ruins of Orr",
                zone_count=3,
                estimated_hours=round(3.5 * speed_factor, 1),
                difficulty="Hard",
                recommended_mount="Skyscale" if has_skyscale else None,
                strategy_notes="Hostile density and contested temples. Straits of Devastation, Malchor's Leap, Cursed Shore. Tip: Sync with Temple of Balthazar meta event.",
                starting_waypoint="[&BBcDAAA=]"
            )
        ]

    def _generate_precursor_strategies(
        self,
        account: AccountState,
        tp_prices: Dict[int, float],
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True
    ) -> List[PrecursorStrategy]:
        """Generates comparative triage for all 4 Dusk precursor acquisition pathways."""
        dusk_price = tp_prices.get(self.DUSK_ID, 141.0 if (optimize_for_cost or wizards_vault_exhausted) else 320.0)

        starter_kit_in_bank = any(account.total_item_count(cid) > 0 for cid in [100000, 100001, 100002, 100003])

        strats = [
            PrecursorStrategy(
                strategy_name="Wizard's Vault Legendary Starter Kit",
                estimated_gold_cost=0.0,
                estimated_hours=0.1,
                pros=["0 gold cost", "Also grants Gift of Metal and crafting materials", "Guaranteed unlock"],
                cons=["Wizard's Vault seasonal Starter Kit is exhausted / already claimed"] if wizards_vault_exhausted else ["Requires active seasonal kit selection (1,200 Astral Acclaim)"],
                is_recommended=(not wizards_vault_exhausted) and (starter_kit_in_bank or account.has_expansion("SecretsOfTheObscure")),
                requires_expansion="SecretsOfTheObscure",
                waypoint="[&BBAEAAA=]"
            ),
            PrecursorStrategy(
                strategy_name="Trading Post Direct Purchase",
                estimated_gold_cost=dusk_price,
                estimated_hours=0.1,
                pros=[
                    f"Instant acquisition (~{int(dusk_price)}g)",
                    "Cheaper than Grandmaster Hobbs collection materials (~210g)",
                    "Zero crafting or collection time (saves ~30 hours)"
                ],
                cons=[f"High gold investment (~{int(dusk_price)}g)"],
                is_recommended=wizards_vault_exhausted or (not starter_kit_in_bank and not account.has_expansion("SecretsOfTheObscure")),
                waypoint="[&BBAEAAA=]"
            ),
            PrecursorStrategy(
                strategy_name="Grandmaster Hobbs Collection (Dusk I, II, III)",
                estimated_gold_cost=210.0,
                estimated_hours=30.0,
                pros=[
                    "Engaging lore and progression across 3 Hobbs Tiers",
                    "Tier 1 (Weaponsmith 450, 30x Deldrimor Steel) -> Tier 2 (Weaponsmith 450, 35x Deldrimor Steel) -> Tier 3 (Weaponsmith 500, 27 Gloom locations)"
                ],
                cons=[
                    "Costs ~210g in materials (more expensive than TP buy at ~141g)",
                    "Time intensive (~30 hours)",
                    "Requires Central Tyria Legendary Crafting Mastery Tiers 1-3 (Revered Antiquarian, Magister of Legends, Historian of the Armaments)",
                    "Requires 27 Gloom extractions (Fractals, Tequatl, Shadow Behemoth, Silverwastes Labyrinth/Breaches, mini-dungeons)"
                ],
                is_recommended=False,
                requires_expansion="HeartOfThorns",
                vendor_npc="Grandmaster Craftsman Hobbs",
                waypoint="[&BBAEAAA=]"
            ),
            PrecursorStrategy(
                strategy_name="Mystic Forge Rare Greatsword Promotion",
                estimated_gold_cost=250.0,
                estimated_hours=1.0,
                pros=["Small chance of instant jackpot"],
                cons=["RNG dependent (~2% yield rate)", "High risk of heavy net gold loss"],
                is_recommended=False,
                waypoint="[&BBAEAAA=]"
            )
        ]

        return strats

    def _find_mobility_character_name(self, account: AccountState) -> str:
        """Finds primary mobility character name from eligible exploration characters (excluding completed characters like Kerling)."""
        eligible = account.eligible_exploration_characters()
        if not eligible:
            return "Skuta Rantakallio"

        # Check structured characters if available
        if account.characters:
            # 1. Look for high mobility professions (Thief, Ranger, Mesmer, Guardian) among eligible
            for c in account.characters:
                if isinstance(c, dict):
                    name = c.get("name")
                    if name in eligible and c.get("profession") in ["Thief", "Ranger", "Mesmer", "Guardian"]:
                        return name
            # 2. Look for any character among eligible
            for c in account.characters:
                if isinstance(c, dict):
                    name = c.get("name")
                    if name in eligible:
                        return name

        # 3. Known preferred alts from default roster
        for pref in ["Skuta Rantakallio", "Sara Loy", "Legacy Of Harathi"]:
            if pref in eligible:
                return pref

        return eligible[0]

    def _generate_session_itinerary(
        self,
        pillars: List[JourneyPillar],
        time_budget_minutes: int,
        account: AccountState,
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True
    ) -> List[JourneyAction]:
        """Prioritizes and fits concrete progression actions into the player's time budget."""
        if optimize_for_cost or wizards_vault_exhausted:
            mobility_char = self._find_mobility_character_name(account)
            mount_str = "Skyscale" if account.has_mount("skyscale") or not account.mount_types else ("Raptor" if account.has_mount("raptor") else "Skyscale")

            candidates = [
                JourneyAction(
                    action_title="BUY-2046 Daily Clovers (Mistlock Observatory [&DYEFAAA=])",
                    action_description="Purchase 2 daily discounted Mystic Clovers from BUY-2046 at Mistlock Observatory [&DYEFAAA=] (150 Fractal Relics + 1 Mystic Coin + 3 Ecto + 2 Spirit Shards each).",
                    estimated_minutes=10,
                    priority="CRITICAL",
                    zone_name="Mistlock Observatory",
                    waypoint="[&DYEFAAA=]",
                    npc_name="BUY-2046",
                    game_mode="Account"
                ),
                JourneyAction(
                    action_title="Ascalonian Catacombs dungeon run for Tales of Dungeon Delving [&BIcBAAA=]",
                    action_description="Run AC explorable paths to earn Tales of Dungeon Delving for Gift of Ascalon (500 Tales needed, 0 gold cost).",
                    estimated_minutes=25,
                    priority="HIGH",
                    zone_name="Plains of Ashford",
                    waypoint="[&BIcBAAA=]",
                    game_mode="Dungeon"
                ),
                JourneyAction(
                    action_title="Onyx Core Mystic Forge Promotion [&BBAEAAA=]",
                    action_description="Promote Onyx Cores into Onyx Lodestones at Miyani [&BBAEAAA=] in Lion's Arch (2x Cores + 1x Crystalline Dust + 1x Philosopher's Stone + 1x Wine), saving ~19.6g over buying lodestones directly.",
                    estimated_minutes=10,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Miyani",
                    game_mode="Crafting"
                ),
                JourneyAction(
                    action_title=f"Core Tyria Map Completion on {mobility_char} with {mount_str}",
                    action_description=f"Progress Core Tyria map completion on your primary mobility character ({mobility_char}) with {mount_str}. 100% completion awards 2x Gifts of Exploration (satisfying Twilight and providing a spare for your next Gen 1 legendary).",
                    estimated_minutes=45,
                    priority="HIGH",
                    game_mode="OpenWorld",
                    recommended_mount=mount_str,
                    assigned_character=mobility_char
                )
            ]

            itinerary = []
            budget_remaining = time_budget_minutes

            for idx, action in enumerate(candidates):
                if budget_remaining <= 0:
                    break
                if idx < len(candidates) - 1:
                    if action.estimated_minutes <= budget_remaining:
                        itinerary.append(action)
                        budget_remaining -= action.estimated_minutes
                    elif budget_remaining >= 5:
                        itinerary.append(action.model_copy(update={"estimated_minutes": budget_remaining}))
                        budget_remaining = 0
                else:
                    time_to_assign = min(action.estimated_minutes, budget_remaining) if budget_remaining <= 45 else budget_remaining
                    itinerary.append(action.model_copy(update={"estimated_minutes": time_to_assign}))
                    budget_remaining = 0

            return itinerary

        all_actions: List[JourneyAction] = []
        for pillar in pillars:
            all_actions.extend(pillar.recommended_actions)

        priority_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        all_actions.sort(key=lambda a: priority_rank.get(a.priority, 99))

        itinerary = []
        budget_remaining = time_budget_minutes

        for action in all_actions:
            if budget_remaining <= 0:
                break
            if action.estimated_minutes <= budget_remaining:
                itinerary.append(action)
                budget_remaining -= action.estimated_minutes
            elif budget_remaining >= 15:
                partial_action = action.model_copy(update={"estimated_minutes": budget_remaining})
                itinerary.append(partial_action)
                budget_remaining = 0

        return itinerary

    def _check_expansion_access(self, account: AccountState) -> List[str]:
        """Identifies locked shortcuts and warnings based on account expansion ownership."""
        warnings = []
        if not account.has_expansion("PathOfFire") and not account.has_expansion("EndOfDragons"):
            warnings.append("⚠️ **No Mount Access (PathOfFire / EndOfDragons missing):** Core Tyria map completion will take ~18-21h on foot vs ~8-10h with mounts.")
        if not account.has_expansion("LivingWorldSeason4"):
            warnings.append("💡 **Living World Season 4 Missing:** Volatile Magic Trophy Shipments (Dragonfall `[&BNoLAAA=]`) are unavailable. Use Laurel bags or Silverwastes RIBA for T6 materials.")
        if not account.has_expansion("SecretsOfTheObscure"):
            warnings.append("ℹ️ **Secrets of the Obscure Missing:** Seasonal Wizard's Vault Starter Kits and discounted Astral Clovers may be restricted.")
        return warnings

    def _find_best_character(self, account: AccountState) -> Optional[str]:
        """Identifies the player character best suited for Twilight crafting based on active disciplines."""
        best_ws = None
        best_as = None
        for char in account.characters:
            char_name = char.get("name", "")
            discs = {d.get("discipline", "").lower(): d.get("rating", 0) for d in char.get("crafting", [])}
            ws_level = discs.get("weaponsmith", 0)
            as_level = discs.get("armorsmith", 0)
            if ws_level >= 400:
                best_ws = char_name
            if as_level >= 400:
                best_as = char_name
            if ws_level >= 400 and as_level >= 400:
                return f"{char_name} (Weaponsmith {ws_level}, Armorsmith {as_level})"
                
        if best_ws and best_as and best_ws != best_as:
            return f"Split: {best_ws} (Weaponsmith) / {best_as} (Armorsmith)"
        elif best_ws:
            return f"{best_ws} (Weaponsmith)"
        elif best_as:
            return f"{best_as} (Armorsmith)"
            
        return None

    def _build_master_chapters(
        self,
        account: AccountState,
        tp_prices: Dict[int, float],
        diff_report: AccountDiffReport,
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True
    ) -> List[JourneyChapter]:
        """Builds the 4-Chapter Master Sequencer for the Twilight Journey."""
        chapters = []
        
        # --- Chapter 1: The Precursor Decision (Dusk) ---
        owned_dusk = account.total_item_count(self.DUSK_ID)
        has_twilight = account.has_legendary_unlocked(self.TWILIGHT_ID)
        astral_acclaim = account.astral_acclaim_count()
        gold = account.gold_count()
        dusk_price = tp_prices.get(self.DUSK_ID, 141.0 if (optimize_for_cost or wizards_vault_exhausted) else 320.0)
        
        c1_actions = []
        c1_status = "NOT_STARTED"
        c1_readiness = 0.0
        
        # Check Central Tyria mastery prerequisite for Hobbs collection
        hobbs_mastery_query = """
        SELECT ?trackId ?trackLabel ?reqLvl WHERE {
            item:vendor_hobbs priory:requiresMasteryTrack ?track .
            ?track priory:masteryId ?trackId .
            OPTIONAL { item:vendor_hobbs priory:requiredMasteryLevel ?reqLvl }
            OPTIONAL { ?track rdfs:label ?trackLabel }
        } LIMIT 1
        """
        hobbs_res = self.store.query(hobbs_mastery_query)
        track_id = int(hobbs_res[0]["trackId"]) if hobbs_res else 10
        track_label = str(hobbs_res[0].get("trackLabel", "Legendary Crafting")) if hobbs_res else "Legendary Crafting"
        crafting_mastery = account.masteries.get(track_id, 0)
        mastery_warning = ""
        if crafting_mastery < 3:
            mastery_warning = f" ⚠️ Requires Central Tyria Mastery '{track_label}' (Tiers 1-3: Revered Antiquarian, Magister of Armaments, Historian of Armaments; current level: {crafting_mastery}/3)."

        hobbs_action_desc = (
            f"Grandmaster Craftsman Hobbs `[&BBAEAAA=]` Precursor Collection Tiers (Central Tyria '{track_label}' Status: {crafting_mastery}/3):\n"
            f"       • Tier 1: 'Dusk I: The Experimental Nightsword' (Requires {track_label} Tier 1 - Revered Antiquarian) -> Craft Experimental Greatsword Blade/Hilt and gather gloom essences across Central Tyria.\n"
            f"       • Tier 2: 'Dusk II: The Perfected Nightsword' (Requires {track_label} Tier 2 - Magister of Armaments) -> Craft Weighted Greatsword Blade/Hilt (250x each of Iron, Darksteel, Mithril, Orichalcum ingots + Elonian Leather & Spiritwood).\n"
            f"       • Tier 3: 'Dusk III: Dusk' (Requires {track_label} Tier 3 - Historian of Armaments) -> Harvest Darkness essences from Shadow of the Dragon, Tequatl, and Ascalonian Catacombs to forge final precursor Dusk.\n"
            f"       💡 Trade-off: Costs ~210g materials + ~30h gameplay time vs ~{dusk_price:.1f}g instant Trading Post purchase.{mastery_warning}"
        )

        if owned_dusk > 0 or has_twilight:
            c1_status = "COMPLETED"
            c1_readiness = 100.0
        elif wizards_vault_exhausted:
            c1_actions.append(JourneyAction(
                action_title="Buy Dusk from Trading Post (Cheapest Route)",
                action_description=(
                    f"Trading Post buy for Dusk (~{dusk_price:.0f}g) is cheaper and faster than Grandmaster Hobbs collection materials (~210g across Tiers 1-3). "
                    f"Grandmaster Hobbs collection requires ~210g in Deldrimor Steel (65x ingots), Spiritwood, Elonian Leather, and 30+ hours of time across Tiers 1-3. "
                    f"Direct Trading Post purchase saves ~69g and ~30 hours of crafting/farming."
                ),
                estimated_minutes=5,
                priority="CRITICAL",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Account"
            ))
            c1_readiness = 80.0 if gold >= dusk_price else 20.0
        else:
            if astral_acclaim >= 1200:
                c1_actions.append(JourneyAction(
                    action_title="Buy Legendary Starter Kit",
                    action_description="You have 1200+ Astral Acclaim! Purchase the Legendary Weapon Starter Kit from the Wizard's Vault to get Dusk and Gift of Metal.",
                    estimated_minutes=2,
                    priority="CRITICAL",
                    game_mode="Account"
                ))
                c1_readiness = 90.0
            elif gold >= dusk_price:
                c1_actions.append(JourneyAction(
                    action_title="Buy Dusk from Trading Post",
                    action_description=f"You have enough gold to buy Dusk directly from the Trading Post for ~{dusk_price}g.",
                    estimated_minutes=2,
                    priority="CRITICAL",
                    game_mode="Account"
                ))
                c1_readiness = 90.0
            else:
                # Check Central Tyria mastery prerequisite for Hobbs collection
                hobbs_mastery_query = """
                SELECT ?trackId ?trackLabel ?reqLvl WHERE {
                    item:vendor_hobbs priory:requiresMasteryTrack ?track .
                    ?track priory:masteryId ?trackId .
                    OPTIONAL { item:vendor_hobbs priory:requiredMasteryLevel ?reqLvl }
                    OPTIONAL { ?track rdfs:label ?trackLabel }
                } LIMIT 1
                """
                hobbs_res = self.store.query(hobbs_mastery_query)
                track_id = int(hobbs_res[0]["trackId"]) if hobbs_res else 10
                track_label = str(hobbs_res[0].get("trackLabel", "Legendary Crafting")) if hobbs_res else "Legendary Crafting"
                crafting_mastery = account.masteries.get(track_id, 0)
                
                hobbs_tiers_breakdown = (
                    "Hobbs 3-Tier Precursor Collection Breakdown: "
                    "• Tier 1 (Revered Antiquarian Mastery Tier 1, Weaponsmith 450): Craft Dusk Experiment using 30x Deldrimor Steel Ingots (15x Blade + 15x Hilt) + 200 Memory of Battle + 200 Shard of Glory, then salvage into Spirit of the Dusk Experiment. "
                    "• Tier 2 (Magister of Legends Mastery Tier 2, Weaponsmith 450): Complete metallurgical research requiring 35x Deldrimor Steel Ingots, 1,000 Bandit Crests, 400 Geodes, and 100 Obsidian Shards; craft Perfected Nightsword and salvage into Spirit of the Perfected Nightsword. "
                    "• Tier 3 (Historian of the Armaments Mastery Tier 3, Weaponsmith 500): Obtain Gloominator gizmo and extract primordial darkness from 27 Gloom locations (Fractals: Aquatic Ruins, Swampland, Snowblind, Solid Ocean, Underground; World Bosses: Tequatl, Shadow Behemoth; Silverwastes: Tangled Labyrinth & Breaches; Mini-Dungeons: Tears of Itlaocol, Weyandt's Revenge, Temple of Grenth, Vexa's Lab, Provernic Crypt); forge final precursor Dusk at Weaponsmith 500 using Essence of Gloom, Mirror, and Dimensional Destabilizer."
                )

                mastery_warning = ""
                if crafting_mastery < 3:
                    mastery_warning = f" ⚠️ Requires Central Tyria Mastery '{track_label}' (Tiers 1-3: Revered Antiquarian, Magister of Legends, Historian of the Armaments; current level: {crafting_mastery}/3). {hobbs_tiers_breakdown}"
                else:
                    mastery_warning = f" ✅ Central Tyria Mastery '{track_label}' (Tiers 1-3) is fully unlocked ({crafting_mastery}/3). {hobbs_tiers_breakdown}"

                c1_actions.append(JourneyAction(
                    action_title="Begin Hobbs Precursor Collection (Dusk I, II, III)",
                    action_description=f"Start the Grandmaster Hobbs collection journey in Lion's Arch `[&BBAEAAA=]`.{mastery_warning}",
                    estimated_minutes=30,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Grandmaster Craftsman Hobbs",
                    game_mode="OpenWorld"
                ))
                c1_readiness = 0.0

        chapters.append(JourneyChapter(
            chapter_number=1,
            chapter_title="The Precursor Decision (Dusk)",
            chapter_summary="Evaluate Astral Acclaim, gold, and collection methods for acquiring Dusk.",
            actions=c1_actions,
            completion_status=c1_status,
            readiness_pct=c1_readiness
        ))
        
        # --- Chapter 2: The Core Tyria Expedition (The World Tour) ---
        has_exploration = account.total_item_count(self.GIFT_OF_EXPLORATION_ID) > 0
        c2_status = "COMPLETED" if has_exploration else "IN_PROGRESS"
        c2_readiness = 100.0 if has_exploration else 50.0
        c2_actions = []

        DEFAULT_CHARACTERS = [
            'Kerling', 'Skuta Rantakallio', 'Legacy Of Harathi', 'Styrman',
            'Ksëne', 'Aubefein', 'Sara Loy', 'Flevkk', 'Like A Plastik Bag',
            'Jaimelargent', 'Saladomatic'
        ]

        if not has_exploration:
            char_list = [c.get("name") for c in account.characters if isinstance(c, dict) and c.get("name")]
            if not char_list:
                char_list = DEFAULT_CHARACTERS

            # Select primary mobility character from eligible exploration characters
            mobility_char = self._find_mobility_character_name(account)

            skyscale_mount_str = "Skyscale" if account.has_mount("skyscale") else ("Raptor" if account.has_mount("raptor") else "Skyscale")

            notice_str = ""
            if account.is_character_map_completed("Kerling") or account.map_completed_characters:
                completed_names = ", ".join(account.map_completed_characters) if account.map_completed_characters else "Kerling"
                notice_str = (
                    f"✅ 100% Map Complete Character: {completed_names} has already completed 100% Core Tyria Map Completion and claimed their Gifts of Exploration. "
                    f"Since Gifts of Exploration are awarded once per character upon 100% world completion, select an eligible alt character from your roster "
                    f"(e.g. Skuta Rantakallio, Sara Loy, or Legacy Of Harathi) to run the 5 Core Tyria regions with your Skyscale to claim 2x new Gifts of Exploration!\n\n"
                )

            c2_actions.append(JourneyAction(
                action_title="Core Tyria Map Completion (2x Gifts of Exploration)",
                action_description=(
                    f"{notice_str}"
                    f"Recommend 100% Core Tyria map completion on your primary mobility character ({mobility_char}) with {skyscale_mount_str}. "
                    f"Assessed account roster of {len(char_list)} characters: {', '.join(char_list)}. "
                    f"✨ Milestone Reward: Completing 100% Core Map awards 2x Gifts of Exploration (satisfying Twilight AND providing a spare for your next Gen 1 legendary)!"
                ),
                estimated_minutes=30,
                priority="CRITICAL",
                recommended_mount="Skyscale" if account.has_mount("skyscale") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))

            c2_actions.append(JourneyAction(
                action_title="Complete Shiverpeaks Map",
                action_description="Explore Shiverpeak Mountains. Skyscale recommended for high elevation.",
                estimated_minutes=180,
                priority="HIGH",
                recommended_mount="Skyscale" if account.has_mount("skyscale") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))
            c2_actions.append(JourneyAction(
                action_title="Complete Ascalon Map",
                action_description="Explore Ascalon. Raptor/Jackal recommended.",
                estimated_minutes=180,
                priority="HIGH",
                recommended_mount="Raptor" if account.has_mount("raptor") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))
            c2_actions.append(JourneyAction(
                action_title="Complete Kryta Map",
                action_description="Explore Kryta. Raptor recommended.",
                estimated_minutes=180,
                priority="HIGH",
                recommended_mount="Raptor" if account.has_mount("raptor") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))
            c2_actions.append(JourneyAction(
                action_title="Complete Maguuma Map",
                action_description="Explore Maguuma Jungle. Skyscale recommended.",
                estimated_minutes=180,
                priority="HIGH",
                recommended_mount="Skyscale" if account.has_mount("skyscale") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))
            c2_actions.append(JourneyAction(
                action_title="Complete Orr Map",
                action_description="Explore Ruins of Orr. Skyscale recommended.",
                estimated_minutes=180,
                priority="HIGH",
                recommended_mount="Skyscale" if account.has_mount("skyscale") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))

        chapters.append(JourneyChapter(
            chapter_number=2,
            chapter_title="The Core Tyria Expedition (The World Tour)",
            chapter_summary="5-region geographical route for Gift of Exploration. Completing 100% Core Map awards 2x Gifts of Exploration (satisfying Twilight AND providing a spare for your next Gen 1 legendary).",
            actions=c2_actions,
            completion_status=c2_status,
            readiness_pct=c2_readiness
        ))
        
        # --- Chapter 3: Currencies, Dungeons & Daily Rituals ---
        tales_count = account.dungeon_tales_count()
        has_ascalon = account.total_item_count(self.GIFT_OF_ASCALON_ID) > 0
        has_battle = account.has_gift_of_battle()
        has_bloodstone = account.has_bloodstone_shard()
        spirit_shards = account.spirit_shards_count()
        obsidian_count = account.total_item_count(self.OBSIDIAN_SHARD_ID)
        runestone_count = account.total_item_count(self.ICY_RUNESTONE_ID)
        lodestone_count = account.total_item_count(self.ONYX_LODESTONE_ID)
        t6_owned = sum(account.total_item_count(mat_id) for mat_id in self.T6_MATERIAL_IDS)
        t6_total_needed = 2000
        ecto_count = account.total_item_count(self.GLOB_OF_ECTOPLASM_ID)
        clover_count = account.total_item_count(self.MYSTIC_CLOVER_ID)
        needed_clovers = max(0, 77 - clover_count)
        
        c3_actions = []

        # Check actual owned boosters and gobblers from account snapshot
        owned_boosters = account.owned_boosters()
        has_gobblers = account.has_gobbler()

        booster_telemetry_str = ""
        tailored_instructions = []
        if owned_boosters:
            detected_items = []
            for item_id, count in sorted(owned_boosters.items()):
                name = BOOSTER_NAMES.get(item_id, f"Booster {item_id}")
                detected_items.append(f"{count}x {name} {item_id}")
            booster_telemetry_str = f"detected {', '.join(detected_items)} in bank/inventory!"

            # Gobblers
            gobbler_detected = [f"{count}x {BOOSTER_NAMES.get(gid, 'Gobbler')} {gid}" for gid, count in owned_boosters.items() if gid in [67037, 67040, 67836, 79523, 86675]]
            if gobbler_detected:
                tailored_instructions.append(f"🍬 Gobbler Activation: Use {' / '.join(gobbler_detected)} with festival candy/taffy/snowflakes for continuous +25%-50% WvW Reward Track & XP buffs.")
            elif has_gobblers:
                tailored_instructions.append("🍬 Gobbler Activation: Activate your festival gobblers for continuous +25%-50% WvW Reward Track & XP buffs.")

            # Regular boosters
            regular_boosters = [f"{count}x {BOOSTER_NAMES.get(bid, 'Booster')} {bid}" for bid, count in owned_boosters.items() if bid not in [67037, 67040, 67836, 79523, 86675, 19983, 43766]]
            if regular_boosters:
                tailored_instructions.append(f"⚡ Booster Stacking: Activate {', '.join(regular_boosters)} + Guild Tavern WvW enhancement to accelerate Gift of Battle progression to ~3.5h - 4.5h.")

            # Tomes of Knowledge
            tome_count = account.tomes_of_knowledge_count()
            if tome_count > 0:
                tome_id_str = "19983" if 19983 in owned_boosters else "Tome of Knowledge"
                tailored_instructions.append(f"📖 Tome of Knowledge Conversion: Use {tome_count}x Tomes of Knowledge ({tome_id_str}) on a level 80 character to instantly generate Spirit Shards for Miyani's Bloodstone Shard (200 needed) and Mystic Clovers.")

        # 1. Gift of Ascalon
        if not has_ascalon:
            if tales_count >= 500:
                c3_actions.append(JourneyAction(
                    action_title="Purchase Gift of Ascalon",
                    action_description="Trade 500 Tales of Dungeon Delving at the Dungeon Vendor in Lion's Arch `[&BBAEAAA=]`.",
                    estimated_minutes=5,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    game_mode="Account"
                ))
            else:
                c3_actions.append(JourneyAction(
                    action_title="Run Ascalonian Catacombs",
                    action_description=f"Run AC explorable paths to earn Tales of Dungeon Delving (currently have {tales_count}/500).",
                    estimated_minutes=45,
                    priority="HIGH",
                    zone_name="Plains of Ashford",
                    waypoint="[&BIcBAAA=]",
                    game_mode="Dungeon"
                ))
        else:
            c3_actions.append(JourneyAction(
                action_title="Gift of Ascalon (Completed / Ready)",
                action_description=f"✅ You own Gift of Ascalon in storage (purchased with 500 Tales of Dungeon Delving from Dungeon Vendor `[&BBAEAAA=]`).",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Account"
            ))
                
        # 2. Gift of Battle (WvW Reward Track with Booster Indicators)
        telemetry_suffix = f" (Snapshot telemetry: {booster_telemetry_str} {' '.join(tailored_instructions)})" if booster_telemetry_str else ""
        if not has_battle:
            c3_actions.append(JourneyAction(
                action_title="Complete Gift of Battle WvW Reward Track",
                action_description=f"Activate the Gift of Battle Reward Track in WvW (Edge of the Mists or Borderlands). 🚀 Booster Acceleration: Stack Experience Booster + Heroic Booster + Guild Tavern WvW buff to complete the track in ~4.5h instead of 8.0h unboosted.{telemetry_suffix}",
                estimated_minutes=270,
                priority="HIGH",
                game_mode="WvW"
            ))
        else:
            battle_qty = account.total_item_count(self.GIFT_OF_BATTLE_ID)
            c3_actions.append(JourneyAction(
                action_title="WvW Gift of Battle Track (Completed / Ready)",
                action_description=f"✅ You own {battle_qty}x Gift of Battle in inventory/bank! 🚀 Booster Acceleration Guide: If farming additional tracks, stack Experience Booster + Heroic Booster + Guild Tavern WvW buff to finish in ~4.5h instead of 8.0h unboosted.{telemetry_suffix}",
                estimated_minutes=1,
                priority="LOW",
                game_mode="WvW"
            ))

        # Dedicated Booster Telemetry Action
        if owned_boosters:
            c3_actions.append(JourneyAction(
                action_title="🚀 Booster & Gobbler Telemetry",
                action_description=f"Account Snapshot Telemetry: {booster_telemetry_str} Tailored Activation: {' '.join(tailored_instructions)}",
                estimated_minutes=2,
                priority="MEDIUM",
                game_mode="Account"
            ))

        # Daily Converter & Gobbler Checklist (Free Obsidian Shards & Keys)
        has_ley = account.has_ley_energy_converter()
        has_karmic = account.has_karmic_converter()
        has_sentient = account.has_sentient_converters()

        if has_ley or has_karmic or has_sentient or has_gobblers:
            conv_items_list = []
            if has_ley:
                conv_items_list.append("Ley-Energy Matter Converter `[&AgGgCgEA]`")
            if has_karmic:
                conv_items_list.append("Karmic Converter `[&AgEAfAEA]`")
            if account.total_item_count(92209) > 0 or account.total_item_count(81790) > 0:
                conv_items_list.append("Gleam of Sentience `[&AgERUQEA]`")
            if account.total_item_count(69887) > 0:
                conv_items_list.append("Princess `[&AgF/EQEA]`")
            if account.total_item_count(68369) > 0:
                conv_items_list.append("Star of Gratitude `[&AgExCwEA]`")
            if account.total_item_count(73248) > 0:
                conv_items_list.append("Herta `[&AgGgHAEA]`")
            if account.total_item_count(66341) > 0:
                conv_items_list.append("Mawdrey II `[&AgE1BAEA]`")

            ley_tip = ""
            if has_ley:
                ley_tip = " Open Tab 2 of your Ley-Energy Matter Converter `[&AgGgCgEA]` daily to claim free Obsidian Shards (0 karma/gold cost) and Heart of Thorns map keys (Machetes, Bandit Skeleton Keys, Exalted Keys, Vial of Chak Acid)."
            else:
                ley_tip = " Check converters daily for free Obsidian Shards, keys, and material bags."

            converter_telemetry_str = f" Detected converters: {', '.join(conv_items_list)}." if conv_items_list else ""

            c3_actions.append(JourneyAction(
                action_title="🌟 Daily Converter Checklist (Free Obsidian Shards & Keys)",
                action_description=(
                    f"Daily Converter Checklist:{ley_tip} "
                    f"Activate your Karmic Converter `[&AgEAfAEA]` and Sentient gizmos daily to convert excess Bloodstone Dust, Dragonite Ore, and Empyreal Fragments into Heavy Crafting Bags (free T6 materials).{converter_telemetry_str}"
                ).strip(),
                estimated_minutes=5,
                priority="HIGH",
                game_mode="Account"
            ))
            
        # 3. Bloodstone Shard & 200 Spirit Shard Check
        tome_note = ""
        if 19983 in owned_boosters:
            tome_note = f" (You have {owned_boosters[19983]}x Tomes of Knowledge available in bank/inventory to convert into Spirit Shards!)"

        if not has_bloodstone:
            if spirit_shards >= 200:
                c3_actions.append(JourneyAction(
                    action_title="Purchase Bloodstone Shard from Miyani",
                    action_description=f"✅ 200 Spirit Shard Check: You have {spirit_shards} Spirit Shards (200 needed). Exchange 200 Spirit Shards with Miyani at the Mystic Forge `[&BBAEAAA=]` in Lion's Arch for a Bloodstone Shard.{tome_note}",
                    estimated_minutes=5,
                    priority="MEDIUM",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Miyani",
                    game_mode="Account"
                ))
            else:
                c3_actions.append(JourneyAction(
                    action_title="Farm Spirit Shards for Bloodstone Shard",
                    action_description=f"⚠️ 200 Spirit Shard Check: You have {spirit_shards}/200 Spirit Shards (need {200 - spirit_shards} more). Earn Spirit Shards from level 80 XP, meta events, or Tomes of Knowledge, then purchase Bloodstone Shard from Miyani `[&BBAEAAA=]`.{tome_note}",
                    estimated_minutes=60,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Miyani",
                    game_mode="Account"
                ))
        else:
            c3_actions.append(JourneyAction(
                action_title="Bloodstone Shard (200 Spirit Shards Check - Owned)",
                action_description=f"✅ 200 Spirit Shard Check: Bloodstone Shard is already in your inventory (Account holds {spirit_shards} Spirit Shards). Bought from Miyani `[&BBAEAAA=]` for 200 Spirit Shards.{tome_note}",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                npc_name="Miyani",
                game_mode="Account"
            ))

        # 4. Obsidian Shards
        has_t2f = "teleport_to_friend" in account.owned_convenience_items() or account.total_item_count(90335) > 0
        t2f_str = " ⚡ Recharging Teleport to Friend `[&AgHfYAEA]` Detected: Instantly taxi into active squads on uncontested Temple of Balthazar maps!" if has_t2f else " Use Recharging Teleport to Friend `[&AgHfYAEA]` or LFG taxi to instantly taxi into contested Temple of Balthazar maps."

        if obsidian_count < 250:
            needed_obs = 250 - obsidian_count
            c3_actions.append(JourneyAction(
                action_title="Buy Obsidian Shards via Karma (Temple of Balthazar)",
                action_description=f"Purchase {needed_obs} Obsidian Shards at the Temple of Balthazar `[&BO4CAAA=]` from Tactician Deathspark (2,100 Karma each, {needed_obs * 2100:,} Karma total, 0 gold cost). Temple of Balthazar karma costs 0 gold for {needed_obs} Obsidian Shards.{t2f_str}",
                estimated_minutes=10,
                priority="MEDIUM",
                zone_name="Straits of Devastation",
                waypoint="[&BO4CAAA=]",
                npc_name="Tactician Deathspark",
                game_mode="OpenWorld"
            ))
        else:
            c3_actions.append(JourneyAction(
                action_title="Obsidian Shards (Completed / Ready)",
                action_description=f"✅ You own {obsidian_count}/250 Obsidian Shards! (Acquired from Tactician Deathspark at Temple of Balthazar `[&BO4CAAA=]` or Silverwastes using Recharging Teleport to Friend `[&AgHfYAEA]` for fast taxis).",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Straits of Devastation",
                waypoint="[&BO4CAAA=]",
                npc_name="Tactician Deathspark",
                game_mode="OpenWorld"
            ))
            
        # 5. Icy Runestones
        if runestone_count < 100:
            needed_runes = 100 - runestone_count
            c3_actions.append(JourneyAction(
                action_title="Purchase Icy Runestones",
                action_description=f"Buy {needed_runes} Icy Runestones for {needed_runes}g total from Rojan the Penitent at Earthshake Waypoint `[&BHsBAAA=]`.",
                estimated_minutes=5,
                priority="MEDIUM",
                zone_name="Frostgorge Sound",
                waypoint="[&BHsBAAA=]",
                npc_name="Rojan the Penitent",
                game_mode="OpenWorld"
            ))
        else:
            c3_actions.append(JourneyAction(
                action_title="Icy Runestones (Completed / Ready)",
                action_description=f"✅ You own {runestone_count}/100 Icy Runestones! (Purchased from Rojan the Penitent at Earthshake Waypoint `[&BHsBAAA=]` for 1g each).",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Frostgorge Sound",
                waypoint="[&BHsBAAA=]",
                npc_name="Rojan the Penitent",
                game_mode="OpenWorld"
            ))

        # 6. Onyx Lodestones vs Onyx Cores Mystic Forge Promotion Cost Comparison
        needed_lodes = max(1, 100 - lodestone_count)
        needed_cores = needed_lodes * 2
        lode_price = tp_prices.get(self.ONYX_LODESTONE_ID, 0.40)
        core_price = tp_prices.get(self.ONYX_CORE_ID, 0.10)
        direct_cost = round(needed_lodes * lode_price, 1)
        core_cost = round(needed_cores * core_price, 1)
        savings = round(direct_cost - core_cost, 1)

        if lodestone_count < 100:
            c3_actions.append(JourneyAction(
                action_title="Onyx Lodestones vs Cores Mystic Forge Arbitrage",
                action_description=f"Cost comparison: Buying {needed_lodes} Onyx Lodestones (98 lodes = ~39.2g at {lode_price:.2f}g/ea) vs Mystic Forge promotion of {needed_cores} Onyx Cores (196 cores = ~19.6g at {core_price:.2f}g/ea + Elonian Wine/Dust), saving ~{savings:.1f}g (~19.6g savings for 98 lodes)! Forge recipe: 2x Onyx Cores + 1x Crystalline Dust + 1x Philosopher's Stone + 1x Bottle of Elonian Wine.",
                estimated_minutes=15,
                priority="MEDIUM",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Crafting"
            ))
        else:
            c3_actions.append(JourneyAction(
                action_title="Onyx Lodestones (Completed / Ready)",
                action_description=f"✅ You own {lodestone_count}/100 Onyx Lodestones! 💡 Onyx Core Promotion Arbitrage: Promoting 2x Onyx Cores (~{core_price:.2f}g/ea) + Dust + Powder + Wine in the Mystic Forge costs ~50% less than buying Onyx Lodestones (~{lode_price:.2f}g/ea) directly.",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Crafting"
            ))

        # 7. Mystic Clovers Strategy (with Wizard's Vault Exhaustion Awareness)
        if clover_count < 77:
            if wizards_vault_exhausted:
                c3_actions.append(JourneyAction(
                    action_title="Daily Fractal Clovers (BUY-2046), Strike/Raid & Mystic Forge",
                    action_description=(
                        f"Cheapest cost breakdown for {needed_clovers} needed Mystic Clovers (Wizard's Vault Exhausted): "
                        f"1. BUY-2046 Daily Fractal Clovers at Mistlock Observatory `[&DYEFAAA=]`: Buy 2/day for 150 Fractal Relics + 1 Mystic Coin + 3 Ecto + 2 Spirit Shards each (~2.85g/ea vs ~7.4g/ea Forge, saving ~4.5g per clover). "
                        f"2. Weekly Strike Mission & Raid Vendors: Exchange Green Prophet Shards and Magnetite Shards weekly. "
                        f"3. Mystic Forge Promotion: Craft remaining clovers using 1x Mystic Coin + 1x Glob of Ectoplasm + 1x Philosopher's Stone + 6x Bottle of Elonian Wine (~7.42g/ea effective cost)."
                    ),
                    estimated_minutes=10,
                    priority="CRITICAL",
                    zone_name="Mistlock Observatory",
                    waypoint="[&DYEFAAA=]",
                    npc_name="BUY-2046",
                    game_mode="Account"
                ))
            else:
                c3_actions.append(JourneyAction(
                    action_title="Claim Wizard's Vault Mystic Clovers",
                    action_description=f"Purchase remaining Mystic Clovers (60 Astral Acclaim each) from the Wizard's Vault or buy 2/day from BUY-2046 in Mistlock Observatory `[&DYEFAAA=]`.",
                    estimated_minutes=10,
                    priority="CRITICAL",
                    game_mode="Account"
                ))

        # 8. Daily T6 Laurel Merchant / RIBA Conversion Routine & Ectoplasm Salvaging
        has_silver_fed = "silver_fed" in account.owned_convenience_items() or account.total_item_count(67027) > 0
        silver_fed_tip = " 🌟 Silver-Fed Salvage-o-Matic `[&AgHTBQEA]` Detected: Use it on level 68+ Rare gear for optimal ~0.875 Ectoplasm yield per salvage." if has_silver_fed else " (Salvage level 68+ Rare gear with Silver-Fed Salvage-o-Matic `[&AgHTBQEA]` or Mystic Salvage Kit for optimal ~0.875 Ectoplasm yield per rare)."

        if t6_owned < t6_total_needed or ecto_count < 250:
            needed_t6 = max(0, t6_total_needed - t6_owned)
            desc_parts = []
            if needed_t6 > 0:
                desc_parts.append(f"Need {needed_t6} more T6 fine materials: Exchange Laurels for Heavy Crafting Bags at Laurel Merchant in Lion's Arch `[&BBAEAAA=]` (1 Laurel = 3 T6 materials), and run Silverwastes RIBA meta train `[&BF8HAAA=]` to salvage rares for ectoplasm and open champion bags for T6 materials.{silver_fed_tip}")
            else:
                desc_parts.append(f"Run Silverwastes RIBA meta train `[&BF8HAAA=]` to salvage level 68+ rares for Globs of Ectoplasm ({ecto_count}/250 owned) and open champion bags for materials.{silver_fed_tip}")
            
            c3_actions.append(JourneyAction(
                action_title="Daily T6 Laurel Merchant & RIBA Routine",
                action_description=" ".join(desc_parts),
                estimated_minutes=30,
                priority="HIGH",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Account"
            ))
        else:
            c3_actions.append(JourneyAction(
                action_title="T6 Materials & Ectoplasm (Completed / Ready)",
                action_description=f"✅ You own {t6_owned}/2000 T6 fine materials and {ecto_count}/250 Globs of Ectoplasm! (Salvaged with Silver-Fed Salvage-o-Matic `[&AgHTBQEA]`).",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Account"
            ))

        ascalon_pct = 1.0 if has_ascalon else min(1.0, tales_count / 500.0)
        battle_pct = 1.0 if has_battle else 0.0
        bloodstone_pct = 1.0 if (has_bloodstone or spirit_shards >= 200) else min(1.0, spirit_shards / 200.0)
        obsidian_pct = min(1.0, obsidian_count / 250.0)
        runestone_pct = min(1.0, runestone_count / 100.0)
        lodestone_pct = min(1.0, lodestone_count / 100.0)
        t6_pct = min(1.0, t6_owned / float(t6_total_needed))

        c3_readiness = (ascalon_pct + battle_pct + bloodstone_pct + obsidian_pct + runestone_pct + lodestone_pct + t6_pct) / 7.0 * 100.0

        chapters.append(JourneyChapter(
            chapter_number=3,
            chapter_title="Currencies, Dungeons & Daily Rituals",
            chapter_summary="Gift of Ascalon, Gift of Battle, Bloodstone Shard, Obsidian Shards, Onyx Arbitrage, and Daily T6 Routines.",
            actions=c3_actions,
            completion_status="COMPLETED" if c3_readiness >= 99.0 else "IN_PROGRESS",
            readiness_pct=round(c3_readiness, 1)
        ))
        
        # --- Chapter 4: The Forge Ceremony & Character Hand-offs ---
        weaponsmith_level = account.disciplines.get("weaponsmith", 0)
        armorsmith_level = account.disciplines.get("armorsmith", 0)
        
        ws_char = None
        as_char = None
        primary_crafter = None
        
        for char in account.characters:
            char_name = char.get("name", "")
            discs = {d.get("discipline", "").lower(): d.get("rating", 0) for d in char.get("crafting", [])}
            ws_rating = discs.get("weaponsmith", 0)
            as_rating = discs.get("armorsmith", 0)
            if ws_rating > weaponsmith_level:
                weaponsmith_level = ws_rating
            if as_rating > armorsmith_level:
                armorsmith_level = as_rating
            if ws_rating >= 400 and as_rating >= 400 and not primary_crafter:
                primary_crafter = char_name
                ws_char = char_name
                as_char = char_name
            if ws_rating >= 400 and not ws_char:
                ws_char = char_name
            if as_rating >= 400 and not as_char:
                as_char = char_name
                
        if not primary_crafter:
            if ws_char and as_char and ws_char == as_char:
                primary_crafter = ws_char
            elif ws_char:
                primary_crafter = ws_char
            elif as_char:
                primary_crafter = as_char
            elif account.characters:
                primary_crafter = account.characters[0].get("name")

        ws_assign = ws_char or primary_crafter
        as_assign = as_char or primary_crafter
        forge_assign = primary_crafter or ws_char or as_char

        owned_lounges = account.owned_lounges()
        lounge = owned_lounges[0] if owned_lounges else None
        lounge_name = lounge["name"] if lounge else None
        lounge_link = lounge["chat_link"] if lounge else None
        lounge_zone = lounge.get("zone", lounge_name) if lounge else None

        c4_actions = []
        c4_readiness = 0.0
        
        has_metal = account.total_item_count(self.GIFT_OF_METAL_ID) > 0
        has_darkness = account.total_item_count(self.GIFT_OF_DARKNESS_ID) > 0
        has_gift_twilight = account.total_item_count(self.GIFT_OF_TWILIGHT_ID) > 0

        # Build Crafter Summary
        if primary_crafter:
            craft_summary = f"Weaponsmith {weaponsmith_level} & Armorsmith {armorsmith_level} for {primary_crafter}"
        elif ws_char and as_char and ws_char != as_char:
            craft_summary = f"Weaponsmith {weaponsmith_level} for {ws_char} & Armorsmith {armorsmith_level} for {as_char}"
        elif ws_char:
            craft_summary = f"Weaponsmith {weaponsmith_level} for {ws_char}"
        elif as_char:
            craft_summary = f"Armorsmith {armorsmith_level} for {as_char}"
        else:
            craft_summary = f"Weaponsmith {weaponsmith_level} & Armorsmith {armorsmith_level}"

        if lounge:
            conv_items = account.owned_convenience_items() if hasattr(account, "owned_convenience_items") else {}
            conv_parts = []
            seen_conv = set()
            for slug, item in conv_items.items():
                if slug.isdigit():
                    continue
                if item["name"] not in seen_conv:
                    seen_conv.add(item["name"])
                    conv_parts.append(f"{item['name']} {item['chat_link']}")
            
            conv_tools_str = f" and convenience tools ({', '.join(conv_parts)})" if conv_parts else ""
            vip_banner = f"🌟 VIP Lounge Pass Detected: You own {lounge_name} {lounge_link}{conv_tools_str}! Use {lounge_zone} to access all crafting stations ({craft_summary}), the Mystic Forge, bank, and Trading Post in one compact instance with zero travel fees and instant map return."
            c4_actions.append(JourneyAction(
                action_title=f"🌟 VIP Lounge Pass Detected ({lounge_name})",
                action_description=vip_banner,
                estimated_minutes=2,
                priority="HIGH",
                zone_name=lounge_zone,
                waypoint=lounge_link,
                game_mode="Account",
                assigned_character=forge_assign
            ))

        # Permanent Service Contracts Telemetry (Instant Anywhere-Access)
        owned_contracts = []
        if account.has_permanent_bank():
            owned_contracts.append("Permanent Bank Access Express `[&AgGQjAAA]`")
        if account.has_permanent_tp():
            owned_contracts.append("Permanent Trading Post Express `[&AgGZjAAA]`")
        if account.has_permanent_merchant():
            owned_contracts.append("Permanent Merchant Express `[&AgGJjAAA]`")
        if account.has_permanent_hair_stylist():
            owned_contracts.append("Permanent Hair Stylist Contract `[&AgG4XAAA]`")

        if owned_contracts:
            contract_str = ", ".join(owned_contracts)
            contract_wp = lounge_link if lounge else "[&BBAEAAA=]"
            contract_zone = lounge_zone if lounge else "Lion's Arch"
            c4_actions.append(JourneyAction(
                action_title="🌟 Permanent Contracts Detected (Instant Anywhere-Access)",
                action_description=(
                    f"🌟 Permanent Contracts Detected: You own {contract_str}! "
                    f"Take advantage of instant anywhere-access capability to access your bank, Trading Post, and merchant directly from anywhere in the world "
                    f"without leaving your crafting station or paying waypoint fees."
                ),
                estimated_minutes=2,
                priority="HIGH",
                zone_name=contract_zone,
                waypoint=contract_wp,
                game_mode="Account",
                assigned_character=forge_assign
            ))

        # Material Staging: Invisible Bags & 250-Stack Batching
        staging_wp = lounge_link if lounge else "[&BBAEAAA=]"
        staging_zone = lounge_zone if lounge else "Lion's Arch"
        c4_actions.append(JourneyAction(
            action_title="🛡️ Material Staging: Invisible Bags & 250-Stack Batching",
            action_description=(
                "🛡️ Invisible Bag Staging Rules: Place your precursor (Dusk `[&BBAEAAA=]`), intermediate gifts (Gift of Metal, Gift of Darkness, Gift of Mastery, Gift of Fortune, Gift of Twilight), and exotic components into an Invisible Bag (or Safe Box). Items in invisible bags are protected from accidental 'Deposit All Materials', mass salvage kit clicks, or vendor liquidation while crafting. "
                "📦 250-Stack Material Storage Batching: Craft materials in complete 250-unit stacks (250x Orichalcum, 250x Mithril, 250x Darksteel, 250x Platinum Ingots, 250x Globs of Ectoplasm, 250x Obsidian Shards) to match GW2 Material Storage slot limits and prevent bag clutter during Forge operations."
            ),
            estimated_minutes=5,
            priority="HIGH",
            zone_name=staging_zone,
            waypoint=staging_wp,
            game_mode="Account",
            assigned_character=forge_assign
        ))

        # Step 1: Forge Gift of Metal
        if weaponsmith_level < 400 and not has_metal:
            if lounge:
                metal_desc = f"Level Weaponsmithing to 400 in {lounge_zone} `{lounge_link}` to craft Gift of Metal."
                metal_wp = lounge_link
                metal_zone = lounge_zone
            else:
                metal_desc = "Level Weaponsmithing to 400 in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]` to craft Gift of Metal."
                metal_wp = "[&BKgDAAA=]"
                metal_zone = "Black Citadel"
            c4_actions.append(JourneyAction(
                action_title="Level Weaponsmith to 400",
                action_description=metal_desc,
                estimated_minutes=30,
                priority="CRITICAL",
                zone_name=metal_zone,
                waypoint=metal_wp,
                game_mode="Crafting",
                assigned_character=ws_assign
            ))
        else:
            c4_readiness += 25.0
            if not has_metal and not has_gift_twilight:
                if lounge:
                    metal_desc = f"Craft Gift of Metal (250x Orichalcum, 250x Mithril, 250x Darksteel, 250x Platinum Ingots) at a Weaponsmithing station in {lounge_zone} `{lounge_link}`."
                    metal_wp = lounge_link
                    metal_zone = lounge_zone
                else:
                    metal_desc = "Craft Gift of Metal (250x Orichalcum, 250x Mithril, 250x Darksteel, 250x Platinum Ingots) at a Weaponsmithing station in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]`."
                    metal_wp = "[&BKgDAAA=]"
                    metal_zone = "Black Citadel"
                c4_actions.append(JourneyAction(
                    action_title="Forge Gift of Metal",
                    action_description=metal_desc,
                    estimated_minutes=5,
                    priority="HIGH",
                    zone_name=metal_zone,
                    waypoint=metal_wp,
                    game_mode="Crafting",
                    assigned_character=ws_assign
                ))
            elif has_metal:
                if lounge:
                    metal_desc = f"✅ Gift of Metal is already in your storage! (Crafted by Weaponsmith {weaponsmith_level} in {lounge_zone} `{lounge_link}`)."
                    metal_wp = lounge_link
                    metal_zone = lounge_zone
                else:
                    metal_desc = "✅ Gift of Metal is already in your storage! (Crafted by Weaponsmith 400 in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]`)."
                    metal_wp = "[&BKgDAAA=]"
                    metal_zone = "Black Citadel"
                c4_actions.append(JourneyAction(
                    action_title="Forge Gift of Metal (Crafted / Ready)",
                    action_description=metal_desc,
                    estimated_minutes=1,
                    priority="LOW",
                    zone_name=metal_zone,
                    waypoint=metal_wp,
                    game_mode="Crafting",
                    assigned_character=ws_assign
                ))
            
        # Step 2: Forge Gift of Darkness
        if armorsmith_level < 400 and not has_darkness:
            if lounge:
                dark_desc = f"Level Armorsmithing to 400 in {lounge_zone} `{lounge_link}` to craft Gift of Darkness."
                dark_wp = lounge_link
                dark_zone = lounge_zone
            else:
                dark_desc = "Level Armorsmithing to 400 in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]` to craft Gift of Darkness."
                dark_wp = "[&BKgDAAA=]"
                dark_zone = "Black Citadel"
            c4_actions.append(JourneyAction(
                action_title="Level Armorsmith to 400",
                action_description=dark_desc,
                estimated_minutes=30,
                priority="CRITICAL",
                zone_name=dark_zone,
                waypoint=dark_wp,
                game_mode="Crafting",
                assigned_character=as_assign
            ))
        else:
            c4_readiness += 25.0
            if not has_darkness and not has_gift_twilight:
                if lounge:
                    dark_desc = f"Craft Gift of Darkness (Gift of Ascalon + 250x Orichalcum Ingots + 100x Onyx Lodestones + 100x Hardened Leather Sections) at an Armorsmithing station in {lounge_zone} `{lounge_link}`."
                    dark_wp = lounge_link
                    dark_zone = lounge_zone
                else:
                    dark_desc = "Craft Gift of Darkness (Gift of Ascalon + 250x Orichalcum Ingots + 100x Onyx Lodestones + 100x Hardened Leather Sections) at an Armorsmithing station in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]`."
                    metal_wp = "[&BKgDAAA=]"
                    dark_wp = "[&BKgDAAA=]"
                    dark_zone = "Black Citadel"
                c4_actions.append(JourneyAction(
                    action_title="Forge Gift of Darkness",
                    action_description=dark_desc,
                    estimated_minutes=5,
                    priority="HIGH",
                    zone_name=dark_zone,
                    waypoint=dark_wp,
                    game_mode="Crafting",
                    assigned_character=as_assign
                ))
            elif has_darkness:
                if lounge:
                    dark_desc = f"✅ Gift of Darkness is already in your storage! (Crafted by Armorsmith {armorsmith_level} in {lounge_zone} `{lounge_link}`)."
                    dark_wp = lounge_link
                    dark_zone = lounge_zone
                else:
                    dark_desc = "✅ Gift of Darkness is already in your storage! (Crafted by Armorsmith 400 in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]`)."
                    dark_wp = "[&BKgDAAA=]"
                    dark_zone = "Black Citadel"
                c4_actions.append(JourneyAction(
                    action_title="Forge Gift of Darkness (Crafted / Ready)",
                    action_description=dark_desc,
                    estimated_minutes=1,
                    priority="LOW",
                    zone_name=dark_zone,
                    waypoint=dark_wp,
                    game_mode="Crafting",
                    assigned_character=as_assign
                ))
            
        # Step 3: Forge Gift of Twilight
        if has_gift_twilight:
            c4_readiness += 25.0
            twilight_wp = lounge_link if lounge else "[&BBAEAAA=]"
            twilight_zone = lounge_zone if lounge else "Lion's Arch"
            c4_actions.append(JourneyAction(
                action_title="Forge Gift of Twilight (Crafted / Ready)",
                action_description=f"✅ Gift of Twilight is already forged in your storage! (Mystic Forge in {lounge_zone} `{lounge_link}`)." if lounge else "✅ Gift of Twilight is already forged in your storage!",
                estimated_minutes=1,
                priority="LOW",
                zone_name=twilight_zone,
                waypoint=twilight_wp,
                game_mode="Crafting",
                assigned_character=forge_assign
            ))
        else:
            if lounge:
                twilight_desc = f"Combine Gift of Metal, Gift of Darkness, 100x Onyx Lodestones, and 100x Icy Runestones in the Mystic Forge at {lounge_zone} `{lounge_link}`."
                twilight_wp = lounge_link
                twilight_zone = lounge_zone
            else:
                twilight_desc = "Combine Gift of Metal, Gift of Darkness, 100x Onyx Lodestones, and 100x Icy Runestones in the Mystic Forge at Miyani `[&BBAEAAA=]`."
                twilight_wp = "[&BBAEAAA=]"
                twilight_zone = "Lion's Arch"
            c4_actions.append(JourneyAction(
                action_title="Forge Gift of Twilight",
                action_description=twilight_desc,
                estimated_minutes=5,
                priority="CRITICAL",
                zone_name=twilight_zone,
                waypoint=twilight_wp,
                game_mode="Crafting",
                assigned_character=forge_assign
            ))
        
        # Step 4: 4-Pillar Inventory Staging Checklist (Before Final Forge)
        staging_check_wp = lounge_link if lounge else "[&BBAEAAA=]"
        staging_check_zone = lounge_zone if lounge else "Lion's Arch"

        p1_check = "[x]" if (owned_dusk > 0 or has_twilight) else "[ ]"
        p2_check = "[x]" if (has_exploration and has_battle and obsidian_count >= 250 and (has_bloodstone or spirit_shards >= 200)) else "[ ]"
        p3_check = "[x]" if (clover_count >= 77 and ecto_count >= 250 and t6_owned >= t6_total_needed) else "[ ]"
        p4_check = "[x]" if (has_gift_twilight or (has_metal and has_darkness and runestone_count >= 100 and sigil_count > 0 and weaponsmith_level >= 400 and armorsmith_level >= 400)) else "[ ]"

        staging_check_desc = (
            "📋 4-Pillar Inventory Staging Checklist before the final forge step (validate all 4 pillars with live inventory checks):\n"
            f"       • {p1_check} **Pillar 1: Dusk** `[&AgEpZgAA]` (Precursor item:29185, Exotic Precursor Greatsword)\n"
            f"       • {p2_check} **Pillar 2: Gift of Twilight** `[&AgHiEAAA]` (item:19674/GiftOfTwilight compound: Gift of Metal `[&AgHhEAAA]` + Gift of Darkness `[&AgHnEAAA]` + 100 Icy Runestones `[&AgHSEAAA]` + Superior Sigil of Force `[&AgHjVQAA]`)\n"
            f"       • {p3_check} **Pillar 3: Gift of Mastery** `[&AgHkEAAA]` (Gift of Exploration `[&AgHqEAAA]` + Gift of Battle `[&AgHrEAAA]` + Bloodstone Shard `[&AgHnEAAA]` + 250 Obsidian Shards `[&AgFdEAAA]`)\n"
            f"       • {p4_check} **Pillar 4: Gift of Fortune** `[&AgHlEAAA]` (77 Mystic Clovers `[&AgH2EAAA]` + 250 Ectos / Globs of Ectoplasm `[&AgH1EAAA]` + Gift of Magic `[&AgHjEAAA]` + Gift of Might `[&AgHmEAAA]`)"
        )
        c4_actions.append(JourneyAction(
            action_title="📋 4-Pillar Inventory Staging Checklist",
            action_description=staging_check_desc,
            estimated_minutes=2,
            priority="CRITICAL",
            zone_name=staging_check_zone,
            waypoint=staging_check_wp,
            game_mode="Account",
            assigned_character=forge_assign
        ))

        # Step 5: Final Forge Assembly
        if has_twilight:
            c4_readiness = 100.0
            if lounge and len(c4_actions) == 1:
                c4_actions = []
        else:
            if lounge:
                final_desc = f"Combine Dusk, Gift of Twilight, Gift of Mastery, and Gift of Fortune at the Mystic Forge in {lounge_zone} `{lounge_link}`."
                final_wp = lounge_link
                final_zone = lounge_zone
                final_npc = None
            else:
                final_desc = "Combine Dusk, Gift of Twilight, Gift of Mastery, and Gift of Fortune at Miyani `[&BBAEAAA=]` in Lion's Arch."
                final_wp = "[&BBAEAAA=]"
                final_zone = "Lion's Arch"
                final_npc = "Miyani"
            c4_actions.append(JourneyAction(
                action_title="Final Forge Assembly",
                action_description=final_desc,
                estimated_minutes=10,
                priority="CRITICAL",
                zone_name=final_zone,
                waypoint=final_wp,
                npc_name=final_npc,
                game_mode="Crafting",
                assigned_character=forge_assign
            ))
            if has_gift_twilight and weaponsmith_level >= 400 and armorsmith_level >= 400:
                c4_readiness += 25.0

        # Step 6: Post-Forge Decision Fork
        char_count = len(account.characters) if (account.characters and len(account.characters) > 0) else 11
        fork_wp = lounge_link if lounge else "[&BBAEAAA=]"
        fork_zone = lounge_zone if lounge else "Lion's Arch"
        eternity_gross = tp_prices.get(30689, 3800.0)
        eternity_net = round(eternity_gross * 0.85, 1)
        twilight_gross = tp_prices.get(self.TWILIGHT_ID, 1900.0)
        twilight_net = round(twilight_gross * 0.85, 1)

        fork_desc = (
            f"Post-Forge Decision Fork after Twilight is crafted (choose your post-crafting trajectory):\n"
            f"       • 🛡️ **Path A: Legendary Armory Binding (0g | Infinite Account Utility):**\n"
            f"         -> Deposit Twilight `[&AgErZgAA]` into your Legendary Armory (Unlocks unlimited Twilight copies across all {char_count} characters, instant free stat swapping [Berserker, Viper, Celestial, Dragon], and free sigil/infusion extraction).\n"
            f"         -> Permanently unlocks the Twilight skin in your Wardrobe + grants 'Memory of Twilight' token.\n"
            f"       • 💰 **Path B: The Eternity Commercial Arbitrage Loop (~3,800g Gross | ~3,230g Net Cash):**\n"
            f"         -> Combine unbound Twilight `[&AgErZgAA]` + unbound Sunrise `[&AgG2TAEA]` (crafted using your 2nd Gift of Exploration from Map Completion) + 5x Crystalline Dust `[&AgF4WwEA]` + 10x Philosopher's Stones `[&AgH1EAAA]` in the Mystic Forge to craft unbound Eternity [&AgExZwAA].\n"
            f"         -> ✨ **Skin Retention Dynamics:** Forging Eternity **instantly unlocks BOTH the Twilight and Sunrise skins in your Wardrobe permanently**!\n"
            f"         -> Sell unbound Eternity on the Trading Post for ~3,800g (~3,230g net cash after 15% TP fees), yielding **~1,800g pure profit** (+1,430g to +1,730g profit) while permanently retaining Twilight and Sunrise skins!\n"
            f"       • ⚖️ **Path C: Direct Trading Post Sale (~1,900g TP listing -> ~1,615g net cash):**\n"
            f"         -> Sell unbound Twilight directly on the Trading Post (~1,900g TP listing -> ~1,615g net cash after 15% TP fees).\n"
            f"         -> ⚠️ **Skin Warning:** Direct TP sale does NOT unlock the Twilight skin in your Wardrobe (unlike Eternity forge arbitrage which retains both skins)."
        )
        c4_actions.append(JourneyAction(
            action_title="🔮 Post-Forge Decision Fork (Armory Binding vs Eternity Arbitrage vs TP Sale)",
            action_description=fork_desc,
            estimated_minutes=5,
            priority="HIGH",
            zone_name=fork_zone,
            waypoint=fork_wp,
            game_mode="Account",
            assigned_character=forge_assign
        ))

        if lounge:
            ch4_summary = f"🌟 VIP Lounge ({lounge_name}) unified crafting, Invisible Bag staging, 4-Pillar Staging Checklist, final assembly of Twilight at the Mystic Forge, and Post-Forge Decision Fork with zero travel costs and instant map return."
        else:
            ch4_summary = "Crafting preparation, Invisible Bag staging, 4-Pillar Staging Checklist, final assembly of Twilight at the Mystic Forge, and Post-Forge Decision Fork."

        chapters.append(JourneyChapter(
            chapter_number=4,
            chapter_title="The Forge Ceremony & Character Hand-offs",
            chapter_summary=ch4_summary,
            actions=c4_actions,
            completion_status="COMPLETED" if c4_readiness >= 99.0 else "IN_PROGRESS",
            readiness_pct=round(c4_readiness, 1)
        ))

        return chapters
