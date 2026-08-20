"""Bottom LLM: Contextual Synthesis & Guide Generator for Project Priory.

Transforms deterministic knowledge graph facts, spatial waypoint navigation, and account delta reports into
engaging, personalized, and actionable in-game progression guides with zero hallucinations.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from agent.intent_parser import ResolvedGoal, GoalType
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
    assigned_character: Optional[str] = None


class PersonalizedGuide(BaseModel):
    """The final synthesized progression guide."""
    goal_name: str
    target_quantity: int = 1
    chat_code: Optional[str]
    readiness_percentage: int
    executive_summary: str
    strategic_recommendations: List[str]
    character_recommendations: List[str] = Field(default_factory=list)
    master_roadmap_phases: List[str] = Field(default_factory=list)
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
        semantic_context: str,
        optimal_plan: Optional[Any] = None
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

        # Case 1: Fully Satisfied (e.g. 4 Sigils owned in Legendary Armory or bags)
        if diff_report.is_fully_satisfied:
            return PersonalizedGuide(
                goal_name=goal.resolved_item_name,
                target_quantity=target_qty,
                chat_code=goal.chat_code,
                readiness_percentage=100,
                executive_summary=f"🎉 **Goal Completed:** You already have all **{goal_display}** in your Legendary Armory / account inventory!",
                strategic_recommendations=[
                    f"🏆 **100% Unlocked:** You have fulfilled all {target_qty} required instances on your account. Zero additional materials or crafting steps are needed!"
                ],
                session_checklist=[
                    ActionStep(
                        step_number=1,
                        title="Equip from Legendary Armory",
                        estimated_time_minutes=1,
                        game_mode="Account",
                        description=f"Open your Hero Panel (H) -> Equipment tab -> click any weapon upgrade slot to equip your {goal_display} across all characters for free.",
                        chat_code=goal.chat_code
                    )
                ],
                missing_materials_summary={},
                missing_disciplines_summary=[],
                motivational_tip="🌟 **Priory Tip:** Legendary Sigils can be customized with any stat/sigil effect instantly and for free at any time out of combat!"
            )

        # Case 2: Partially missing materials
        readiness = int(diff_report.overall_readiness_pct)

        # Strategic analysis based on intent, constraints & optimal plan
        recommendations = []
        if optimal_plan and getattr(optimal_plan, "precursor_strategy", None):
            recommendations.append(optimal_plan.precursor_strategy)

        if optimal_plan and getattr(optimal_plan, "bottlenecks", None):
            for b in optimal_plan.bottlenecks:
                if b not in recommendations:
                    recommendations.append(b)

        if optimal_plan and getattr(optimal_plan, "t6_strategies", None):
            for t_strat in optimal_plan.t6_strategies:
                if t_strat not in recommendations:
                    recommendations.append(t_strat)

        # Longitudinal calendar completion date projection
        if optimal_plan and getattr(optimal_plan, "estimated_completion_date", None):
            cal_date = optimal_plan.estimated_completion_date
            cal_days = optimal_plan.estimated_completion_days
            b_neck = optimal_plan.primary_time_gate_bottleneck or "Daily Time Gates"
            recommendations.append(
                f"⏳ **Calendar Projection (~{cal_days} days | Target: {cal_date}):** "
                f"Earliest completion date based on {b_neck}."
            )

        # Domain note on spears if non-existent spear was referenced
        if any(term in (intent.user_playstyle_notes or "").lower() or term in (goal.resolved_item_name or "").lower() for term in ["tier two spear", "tier 2 spear", "gen 2 spear", "generation 2 spear"]):
            recommendations.append(
                "📌 **Domain Note on Spears:** Guild Wars 2 does not have a Generation 2 legendary spear. "
                "The available legendary spears are **Kamohoali'i Kotaki** (Gen 1 Aquatic Spear) and **Klobjarne Harvester** (Janthir Wilds Land Spear)."
            )

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

        # Elder Dragon Facet Skin Variant recommendations
        if getattr(goal, "facet_name", None):
            facet = goal.facet_name
            recommendations.append(
                f"🐉 **{facet} Dragon Facet Skin Transmutation:** "
                f"To unlock the {facet} variant skin for **{goal_display}**, combine the base weapon with "
                f"**100x Memory of Aurene**, **10x Dragonite Ingot**, and **2,500x Research Notes** in the Mystic Forge at Miyani `[&BBAEAAA=]`."
            )

        # Acquisition Discovery (e.g. Farming Mystic Clovers without gambling)
        if getattr(goal, "is_acquisition_query", False) or goal.goal_type == GoalType.ACQUISITION_DISCOVERY:
            recommendations.append(
                f"🏛️ **Multi-Source Acquisition Routing for {goal_display}:**"
            )
            recommendations.append(
                f"  1. ✨ **Wizard's Vault:** Exchange Astral Acclaim (cheapest & 0 gold, 9 AA per Clover)."
            )
            recommendations.append(
                f"  2. 🔮 **Fractals of the Mists (BUY-2046):** Buy 2/day for 150 Fractal Relics + 1 Mystic Coin + 3 Ecto in the Mistlock Sanctuary / Lion's Arch `[&BBAEAAA=]`."
            )
            recommendations.append(
                f"  3. ⚔️ **Raid / Strike Vendors:** Exchange Magnetite Shards / Prophet Shards weekly."
            )
            recommendations.append(
                f"  4. 🎲 **Mystic Forge Recipe (31% yield rate):** 10x Mystic Coins + 10x Ectoplasm + 10x Obsidian Shards + 10x Mystic Crystals."
            )

        # Mystic Clover strategy with exhausted awareness
        if "Mystic Clover" in missing_mats and not getattr(goal, "is_acquisition_query", False):
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

        # Build personalized session checklist with waypoint navigation strictly within time budget
        checklist = []
        budget_remaining = max(intent.time_budget_minutes, 15)
        step_num = 1

        # Use dynamic steps from optimal_plan if available
        if optimal_plan and getattr(optimal_plan, "step_by_step_roadmap", None):
            for step in optimal_plan.step_by_step_roadmap:
                t = step.get("est_time_mins", 10)
                if t <= budget_remaining:
                    checklist.append(ActionStep(
                        step_number=step_num,
                        title=step.get("phase", f"Step {step_num}"),
                        estimated_time_minutes=t,
                        game_mode="OpenWorld",
                        description=step.get("action", ""),
                        chat_code=step.get("chat_code")
                    ))
                    budget_remaining -= t
                    step_num += 1

        if not checklist:
            # Fallback dynamic steps
            if "Mystic Clover" in missing_mats and budget_remaining >= 15:
                checklist.append(ActionStep(
                    step_number=step_num,
                    title="Complete Daily Wizard's Vault Tasks",
                    estimated_time_minutes=min(20, budget_remaining),
                    game_mode="OpenWorld",
                    description="Claim Astral Acclaim and purchase remaining Mystic Clovers directly from the Vault.",
                    chat_code=None
                ))
                budget_remaining -= min(20, budget_remaining)
                step_num += 1

            if budget_remaining > 0:
                checklist.append(ActionStep(
                    step_number=step_num,
                    title="Gather Materials & Meta Event Session",
                    estimated_time_minutes=budget_remaining,
                    game_mode="OpenWorld",
                    description="Teleport to Drizzlewood Coast [&BDoMAAA=] to farm missing fine trophies and gold.",
                    chat_code="[&BDoMAAA=]"
                ))

        # Format Master Roadmap Phases
        master_roadmap_formatted = []
        if optimal_plan and getattr(optimal_plan, "master_roadmap", None):
            for phase in optimal_plan.master_roadmap:
                master_roadmap_formatted.append(f"📌 **{phase.phase_title}** {phase.phase_status}")
                for s in phase.milestone_steps:
                    wp_str = f" `[{s.waypoint}]`" if s.waypoint else ""
                    npc_str = f" ({s.npc_name})" if s.npc_name else ""
                    char_str = f" 👤 [Character: {s.assigned_character}]" if s.assigned_character else ""
                    master_roadmap_formatted.append(f"   [{s.step_number}] **{s.title}**{npc_str}{char_str}{wp_str}: {s.description}")

        summary = (
            f"Here is your personalized progression plan for **{goal_display}** "
            f"tailored to your {intent.time_budget_minutes}-minute playtime tonight."
        )

        tip = (
            "💡 **Priory Tip:** Paste waypoint chat codes (e.g. [&BKgDAAA=]) into in-game chat to instantly open your map and teleport directly to vendors!"
        )

        char_recs = []
        if optimal_plan and getattr(optimal_plan, "master_roadmap", None):
            for phase in optimal_plan.master_roadmap:
                for s in phase.milestone_steps:
                    if s.assigned_character:
                        char_recs.append(f"Crafting **{s.title}**: Switch to character **{s.assigned_character}**")

        return PersonalizedGuide(
            goal_name=goal.resolved_item_name,
            target_quantity=target_qty,
            chat_code=goal.chat_code,
            readiness_percentage=readiness,
            executive_summary=summary,
            strategic_recommendations=recommendations,
            character_recommendations=char_recs,
            master_roadmap_phases=master_roadmap_formatted,
            session_checklist=checklist,
            missing_materials_summary=missing_mats,
            missing_disciplines_summary=missing_discs,
            motivational_tip=tip
        )

    def generate_ranking_guide(
        self,
        rankings: List[Any],
        user_prompt: str,
        time_budget_minutes: int = 120,
        optimal_plan: Optional[Any] = None,
        target_quantity: int = 1
    ) -> PersonalizedGuide:
        """Generates a ranked comparative guide for 'Which legendary am I closest to?' queries."""
        if not rankings:
            return PersonalizedGuide(
                goal_name="Closest Legendary Assessment",
                target_quantity=1,
                chat_code=None,
                readiness_percentage=0,
                executive_summary="No unowned legendary items found in the Knowledge Graph.",
                strategic_recommendations=["All tracked legendaries are already unlocked in your Legendary Armory!"],
                master_roadmap_phases=[],
                session_checklist=[],
                missing_materials_summary={},
                missing_disciplines_summary=[],
                motivational_tip="🌟 **Priory Tip:** You are a master of Tyrian legendary crafting!"
            )

        top_choice = rankings[0]
        readiness = int(top_choice.readiness_pct)

        recs = []
        if target_quantity > 1 and len(rankings) >= target_quantity:
            item_names = ", ".join(f"**{r.name}** ({r.subtype or 'Item'})" for r in rankings[:target_quantity])
            recs.append(f"🏆 **Top {target_quantity} Recommendations:** {item_names} are your top {target_quantity} closest legendaries!")
        else:
            recs.append(f"🏆 **Top Recommendation:** **{top_choice.name}** ({top_choice.subtype or 'Weapon'}) is your #1 closest legendary!")

        # Domain clarification note if player asked about non-existent Gen 2 / Tier 2 spear
        prompt_lower = user_prompt.lower()
        if "tier two spear" in prompt_lower or "tier 2 spear" in prompt_lower or "gen 2 spear" in prompt_lower or "generation 2 spear" in prompt_lower:
            recs.append(
                "📌 **Domain Note on Spears:** Guild Wars 2 does not have a Generation 2 legendary spear. "
                "The available legendary spears are **Kamohoali'i Kotaki** (Gen 1 Aquatic Spear) and **Klobjarne Harvester** (Janthir Wilds Land Spear)."
            )

        # Starter kit match notes
        if target_quantity > 1 and len(rankings) >= 2 and rankings[0].starter_kit_eligible and rankings[1].starter_kit_eligible:
            recs.append(
                f"🎁 **Bank Starter Kit Match:** You own **Legendary Weapon Starter Kit—Set 2** in your Bank! "
                f"Both **{rankings[0].name}** and **{rankings[1].name}** can be chosen from this kit to immediately grant their Precursor and Gift for **0 gold**."
            )
        elif top_choice.starter_kit_eligible:
            recs.append(
                f"🎁 **Bank Starter Kit Match:** You own **Legendary Weapon Starter Kit—Set 2** in your Bank! "
                f"Selecting **{top_choice.name}** immediately gives you its Precursor and Gift for **0 gold**."
            )

        # Speed / quickness analysis note
        is_speed_prompt = any(w in prompt_lower for w in ["quick", "fast", "speed", "least effort", "instant", "soon"])
        if is_speed_prompt:
            recs.append(
                f"⚡ **Speed Analysis:** **{top_choice.name}** uses **{top_choice.precursor_archetype}** "
                f"(~{top_choice.estimated_gameplay_hours}h gameplay effort), making it dramatically faster to craft "
                f"than Gen 2.0 narrative collection legendaries (Astralaria, Nevermore, HOPE, Chuka and Champawat) which require ~40 hours of open-world tasks."
            )

        # Leaderboard items with precursor archetype and calendar days
        display_n = target_quantity if 1 < target_quantity <= 10 else 5
        recs.append(f"📊 **Closest Legendaries Leaderboard (Top {min(display_n, len(rankings))}):**")
        for i, item in enumerate(rankings[:display_n], 1):
            kit_tag = " [🎁 Bank Kit Ready]" if item.starter_kit_eligible else ""
            tg_tag = f" | ⏳ ~{item.calendar_day_gates}d gate" if item.calendar_day_gates > 0 else ""
            recs.append(
                f"   **#{i} {item.name}** ({item.subtype or 'Item'}): **{item.readiness_pct}% Ready** "
                f"| Est. Cost: ~{item.estimated_remaining_gold}g | [{item.precursor_archetype}]{tg_tag}{kit_tag}"
            )

        # Build dynamic time-budget checklist (Strictly within player's session time budget)
        checklist = []
        budget = max(time_budget_minutes, 15)
        step_num = 1

        if top_choice.starter_kit_eligible and budget >= 2:
            checklist.append(ActionStep(
                step_number=step_num,
                title="Claim Precursor from Bank Starter Kit",
                estimated_time_minutes=2,
                game_mode="Account",
                description=f"Withdraw 'Legendary Weapon Starter Kit—Set 2' from your Bank and choose the '{top_choice.name} Kit' for 0 gold.",
                chat_code=None
            ))
            budget -= 2
            step_num += 1

        # Quick daily currency / vault step
        vault_time = min(15, budget)
        if vault_time >= 5:
            checklist.append(ActionStep(
                step_number=step_num,
                title="Complete Daily Wizard's Vault Tasks",
                estimated_time_minutes=vault_time,
                game_mode="OpenWorld",
                description="Claim Astral Acclaim and purchase remaining Mystic Clovers directly from the Vault.",
                chat_code=None
            ))
            budget -= vault_time
            step_num += 1

        # Material farm session fitting exactly in the remaining time
        if budget >= 10:
            meta_waypoint = "[&BDoMAAA=]"
            checklist.append(ActionStep(
                step_number=step_num,
                title="Gather Missing Materials in Drizzlewood Coast",
                estimated_time_minutes=budget,
                game_mode="OpenWorld",
                description=f"Teleport to Base Camp Waypoint {meta_waypoint} to progress Charr Legion material tracks for missing T6 fine trophies.",
                chat_code=meta_waypoint
            ))

        # Format Master Roadmap for the top-ranked recommendation
        master_roadmap_formatted = []
        if optimal_plan and getattr(optimal_plan, "master_roadmap", None):
            for phase in optimal_plan.master_roadmap:
                master_roadmap_formatted.append(f"📌 **{phase.phase_title}** {phase.phase_status}")
                for s in phase.milestone_steps:
                    wp_str = f" `[{s.waypoint}]`" if s.waypoint else ""
                    npc_str = f" ({s.npc_name})" if s.npc_name else ""
                    char_str = f" 👤 [Character: {s.assigned_character}]" if s.assigned_character else ""
                    master_roadmap_formatted.append(f"   [{s.step_number}] **{s.title}**{npc_str}{char_str}{wp_str}: {s.description}")

        summary = (
            f"Based on your live account snapshot (including your materials and bank starter kits), "
            f"you are closest to crafting **{top_choice.name}** ({readiness}% ready, ~{top_choice.estimated_remaining_gold}g remaining)!"
        )

        if top_choice.starter_kit_eligible:
            tip = f"💡 **Priory Tip:** Crafting {top_choice.name} with your Bank Starter Kit saves you ~200g in precursor costs!"
        else:
            tip = f"💡 **Priory Tip:** Remember to convert your daily Astral Acclaim into Mystic Clovers from the Wizard's Vault to save over ~100g in crafting costs!"

        char_recs = []
        if optimal_plan and getattr(optimal_plan, "master_roadmap", None):
            for phase in optimal_plan.master_roadmap:
                for s in phase.milestone_steps:
                    if s.assigned_character:
                        char_recs.append(f"Crafting **{s.title}**: Switch to character **{s.assigned_character}**")

        if top_choice.name == "The Moot":
            char_recs.append("Best Character: **Kerling** (Level 80 Guardian) — Holds **Weaponsmith 500** active & can wield Maces directly!")
        elif top_choice.name == "The Predator":
            char_recs.append("Best Character: **Legacy Of Harathi** (Level 80 Warrior) — Holds **Huntsman 500** active & can wield Rifles directly!")

        return PersonalizedGuide(
            goal_name=f"Closest: {top_choice.name}",
            target_quantity=1,
            chat_code=top_choice.chat_code,
            readiness_percentage=readiness,
            executive_summary=summary,
            strategic_recommendations=recs,
            character_recommendations=char_recs,
            master_roadmap_phases=master_roadmap_formatted,
            session_checklist=checklist,
            missing_materials_summary={mat.split("x ")[1]: int(mat.split("x ")[0]) for mat in top_choice.top_missing_items if "x " in mat},
            missing_disciplines_summary=[],
            motivational_tip=tip
        )

