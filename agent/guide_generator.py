"""Bottom LLM: Contextual Synthesis & Guide Generator for Project Priory.

Transforms deterministic knowledge graph facts, spatial waypoint navigation, and account delta reports into
engaging, personalized, and actionable in-game progression guides with zero hallucinations.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from agent.intent_parser import ResolvedGoal
from engine.account_diff import AccountDiffReport
from agent.llm_client import BaseLLMClient, get_default_llm_client


class ActionStep(BaseModel):
    """A concrete, actionable step for the player's gaming session with waypoint navigation."""
    step_number: int
    title: str
    estimated_time_minutes: int
    game_mode: str
    description: str
    chat_code: Optional[str] = None


class PersonalizedGuide(BaseModel):
    """The final synthesized progression guide."""
    goal_name: str
    target_quantity: int = 1
    chat_code: Optional[str]
    readiness_percentage: int
    executive_summary: str
    strategic_recommendations: List[str]
    session_checklist: List[ActionStep]
    missing_materials_summary: Dict[str, int]
    missing_disciplines_summary: List[str]
    motivational_tip: str


class GuideGenerator:
    """Generates personalized guides with spatial navigation from deterministic graph deltas."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_default_llm_client()

    def generate_guide(
        self,
        goal: ResolvedGoal,
        diff_report: AccountDiffReport,
        semantic_context: str
    ) -> PersonalizedGuide:
        """Synthesizes deterministic diff results and spatial waypoints into a structured guide."""
        intent = goal.intent
        missing_mats = diff_report.summary_missing_materials
        target_qty = diff_report.target_quantity
        exhausted = intent.exhausted_sources
        goal_display = f"{target_qty}x {goal.resolved_item_name}" if target_qty > 1 else goal.resolved_item_name

        missing_discs = [
            f"{d['discipline'].capitalize()} (Needs level {d['required_rating']}, current: {d['current_rating']})"
            for d in diff_report.missing_disciplines
        ]

        # Calculate readiness score
        total_items_needed = sum(missing_mats.values())
        readiness = 0 if total_items_needed > 1000 else max(5, 100 - (total_items_needed // 15))
        if diff_report.is_fully_satisfied:
            readiness = 100

        # Strategic analysis based on intent & constraints
        recommendations = []
        if "WvW" in intent.excluded_game_modes and "Gift of Battle" in missing_mats:
            recommendations.append(
                "⚠️ **WvW Trade-off Alert:** *Gift of Battle* strictly requires the WvW Gift of Battle Reward Track. "
                "Since you want to avoid WvW, consider using WvW Reward Track potions or joining easy daily semi-afk camps."
            )
        
        # Provisioner Tokens recommendation
        if "Gift of Craftsmanship" in missing_mats:
            total_tokens = 50 * target_qty
            recommendations.append(
                f"🏛️ **Provisioner Tokens ({total_tokens} needed for {goal_display}):** "
                f"Trade daily with Faction Provisioners in major racial cities and Heart of Thorns outposts. "
                f"The cheapest trades are Obsidian Shards (Iron Marches), Ectoplasm, and Tier 3-5 rare gear."
            )
        elif goal.resolved_item_id == 91505:
            recommendations.append(
                f"✅ **Provisioner Tokens Ready:** Your account has enough Provisioner Tokens (or Gifts of Craftsmanship) to fulfill this requirement immediately!"
            )

        # Mystic Clover strategy with exhausted awareness
        if "Mystic Clover" in missing_mats:
            clovers_needed = missing_mats["Mystic Clover"]
            if "WizardVault" in exhausted:
                recommendations.append(
                    f"🎲 **Mystic Clovers ({clovers_needed} needed — Wizard's Vault Exhausted):** "
                    f"Since you have already claimed your seasonal Vault clovers, switch to **Fractal Vendor BUY-2046** (2/day limit for 150 relics) "
                    f"or craft them via the **Mystic Forge** promotion recipe."
                )
            else:
                recommendations.append(
                    f"🎲 **Mystic Clovers ({clovers_needed} needed for {goal_display}):** "
                    f"Use Astral Acclaim from the Wizard's Vault first (cheapest & guaranteed), then buy 2/day from Fractal vendors "
                    f"before gambling in the Mystic Forge."
                )

        if "Dusk" in missing_mats:
            recommendations.append(
                "🗡️ **Precursor Weapon (Dusk):** "
                "Compare current Trading Post buy price against Tier 1-3 collection crafting costs before committing gold."
            )

        # Build personalized session checklist with waypoint navigation
        checklist = []
        allocated_time = 0
        step_num = 1

        # Step 1: Crafting disciplines if missing
        if missing_discs:
            checklist.append(ActionStep(
                step_number=step_num,
                title="Level Up Crafting Discipline",
                estimated_time_minutes=30,
                game_mode="OpenWorld",
                description=f"Visit any major city crafting station to level up {', '.join(missing_discs)} using fast discovery guides.",
                chat_code=None
            ))
            allocated_time += 30
            step_num += 1

        # Step 2: Daily Provisioner Tokens (If missing tokens) OR Immediate Exchange (If tokens owned)
        if "Gift of Craftsmanship" in missing_mats and allocated_time < intent.time_budget_minutes:
            checklist.append(ActionStep(
                step_number=step_num,
                title="Daily Faction Provisioner Barter Run",
                estimated_time_minutes=15,
                game_mode="OpenWorld",
                description="Teleport to Junker's Waypoint [&BKgDAAA=] in Black Citadel. Speak to Faction Provisioner to trade for today's time-gated Provisioner Tokens.",
                chat_code="[&BKgDAAA=]"
            ))
            allocated_time += 15
            step_num += 1
        elif goal.resolved_item_id == 91505 and allocated_time < intent.time_budget_minutes:
            checklist.append(ActionStep(
                step_number=step_num,
                title=f"Exchange Tokens for {target_qty}x Gift of Craftsmanship",
                estimated_time_minutes=5,
                game_mode="OpenWorld",
                description=f"Teleport to Junker's Waypoint [&BKgDAAA=] in Black Citadel. Speak to Faction Provisioner to exchange {50 * target_qty} Provisioner Tokens for {target_qty}x Gift of Craftsmanship.",
                chat_code="[&BKgDAAA=]"
            ))
            allocated_time += 5
            step_num += 1

        # Step 3: Clovers: Wizard's Vault (if not exhausted) OR Fractal Vendor / Mystic Forge (if exhausted)
        if "Mystic Clover" in missing_mats and allocated_time < intent.time_budget_minutes:
            if "WizardVault" not in exhausted:
                checklist.append(ActionStep(
                    step_number=step_num,
                    title="Complete Daily Wizard's Vault Tasks",
                    estimated_time_minutes=20,
                    game_mode="OpenWorld",
                    description="Complete daily objectives to claim Astral Acclaim and purchase remaining Mystic Clovers directly from the Vault.",
                    chat_code=None
                ))
                allocated_time += 20
                step_num += 1
            elif "Fractals" not in intent.excluded_game_modes:
                checklist.append(ActionStep(
                    step_number=step_num,
                    title="Buy Daily Fractal Clovers (BUY-2046)",
                    estimated_time_minutes=10,
                    game_mode="Fractals",
                    description="Visit BUY-2046 in the Fractal Observatory / Mistlock Sanctuary to buy today's 2 time-gated Mystic Clovers.",
                    chat_code=None
                ))
                allocated_time += 10
                step_num += 1

        # Step 4: Icy Runestones if crafting Twilight
        if "Icy Runestone" in missing_mats and allocated_time < intent.time_budget_minutes:
            checklist.append(ActionStep(
                step_number=step_num,
                title="Purchase 100x Icy Runestones (100g)",
                estimated_time_minutes=5,
                game_mode="OpenWorld",
                description="Teleport to Earthshake Waypoint [&BHsBAAA=] in Frostgorge Sound. Purchase 100 Icy Runestones from Rojan the Penitent.",
                chat_code="[&BHsBAAA=]"
            ))
            allocated_time += 5
            step_num += 1

        # Step 5: Material Farming / Gold Generation
        remaining_time = max(20, intent.time_budget_minutes - allocated_time)
        meta_waypoint = "[&BF8HAAA=]" # Silverwastes Camp Resolve
        checklist.append(ActionStep(
            step_number=step_num,
            title="Gather Materials & Farm Meta Events",
            estimated_time_minutes=remaining_time,
            game_mode="OpenWorld",
            description=f"Teleport to Camp Resolve Waypoint {meta_waypoint} in Silverwastes (or Drizzlewood Coast) to farm gold, Lodestones, and Lucent Motes.",
            chat_code=meta_waypoint
        ))

        summary = (
            f"Here is your personalized progression plan for **{goal_display}** "
            f"tailored to your {intent.time_budget_minutes}-minute playtime tonight."
        )

        tip = (
            "💡 **Priory Tip:** Paste waypoint chat codes (e.g. [&BKgDAAA=]) into in-game chat to instantly open your map and teleport directly to vendors!"
        )

        return PersonalizedGuide(
            goal_name=goal.resolved_item_name,
            target_quantity=target_qty,
            chat_code=goal.chat_code,
            readiness_percentage=readiness,
            executive_summary=summary,
            strategic_recommendations=recommendations,
            session_checklist=checklist,
            missing_materials_summary=missing_mats,
            missing_disciplines_summary=missing_discs,
            motivational_tip=tip
        )
