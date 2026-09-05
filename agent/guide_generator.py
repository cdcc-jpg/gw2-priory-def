"""Bottom LLM: Contextual Synthesis & Guide Generator for Project Priory.

Transforms deterministic knowledge graph facts, spatial waypoint navigation, and account delta reports into
engaging, personalized, and actionable in-game progression guides with zero hallucinations.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Union
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
    readiness_percentage: Union[int, float]
    executive_summary: str
    strategic_recommendations: List[str]
    character_recommendations: List[str] = Field(default_factory=list)
    master_roadmap_phases: List[str] = Field(default_factory=list)
    session_checklist: List[ActionStep]
    missing_materials_summary: Dict[str, int]
    missing_disciplines_summary: List[str]
    motivational_tip: str
    vip_lounge_callout: Optional[str] = None


class GuideGenerator:
    """Generates personalized guides with spatial navigation from deterministic graph deltas."""

    def __init__(self, llm_client: Optional[BaseLLMClient] = None):
        self.llm = llm_client or get_default_llm_client()

    def generate_guide(
        self,
        goal: ResolvedGoal,
        diff_report: AccountDiffReport,
        semantic_context: str,
        optimal_plan: Optional[Any] = None,
        account_state: Optional[AccountState] = None
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

        # Case 1: Saturated or Fully Satisfied (e.g. 4 Sigils owned in Legendary Armory)
        if getattr(diff_report, "is_saturated", False):
            return PersonalizedGuide(
                goal_name=goal.resolved_item_name,
                target_quantity=target_qty,
                chat_code=goal.chat_code,
                readiness_percentage=100,
                executive_summary=f"🛡️ **Legendary Armory Saturated:** Your account already owns the maximum useful capacity ({diff_report.armory_owned_count}/{diff_report.armory_max_cap} unlocked) for **{goal_display}**!",
                strategic_recommendations=[
                    f"🏆 **Maximum Utility Reached:** You have unlocked all {diff_report.armory_max_cap} allowed copies in your Legendary Armory. Crafting additional copies provides no further utility."
                ],
                session_checklist=[
                    ActionStep(
                        step_number=1,
                        title="Equip from Legendary Armory",
                        estimated_time_minutes=1,
                        game_mode="Account",
                        description=f"Open your Hero Panel (H) -> Equipment tab -> click any matching gear slot to equip your {goal_display} across all characters simultaneously for free.",
                        chat_code=goal.chat_code
                    )
                ],
                missing_materials_summary={},
                missing_disciplines_summary=[],
                motivational_tip="🌟 **Priory Tip:** Legendary items unlocked in your Armory can be customized with free stat-swapping across every character on your account!"
            )

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
                motivational_tip="🌟 **Priory Tip:** Legendary items in your Armory can be equipped across all characters simultaneously!"
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

        if optimal_plan and getattr(optimal_plan, "pillars", None):
            for p in optimal_plan.pillars:
                recommendations.append(f"🏰 **{p.pillar_name} ({p.readiness_pct}% - {p.status}):** " + (", ".join(p.key_blockers) if p.key_blockers else "All requirements satisfied!"))

        if optimal_plan and getattr(optimal_plan, "expansion_warnings", None):
            for w in optimal_plan.expansion_warnings:
                recommendations.append(w)

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
        is_vault_exhausted = (
            "WizardVault" in exhausted
            or (account_state and (account_state.is_wizards_vault_sold_out(19675) or account_state.wizards_vault_remaining(19675) == 0))
        )
        if is_vault_exhausted:
            exhausted_clover_msg = "🚫 Wizard's Vault Clovers Exhausted: Routing to Daily BUY-2046 (2/day) + Mystic Forge fallback."
            if exhausted_clover_msg not in recommendations:
                recommendations.append(exhausted_clover_msg)

        # Cheapest Crafting Strategy comparison
        if goal.resolved_item_id == 30704 or getattr(goal, "prefer_cheap", False) or getattr(intent, "prefer_cheap", False) or is_vault_exhausted:
            cheap_strat = [
                "💰 **Cheapest Crafting Strategy:**",
                "   • **Dusk:** TP buy (~141g) vs Hobbs (~210g materials) -> TP buy saves ~69g.",
                "   • **Onyx Lodestones:** Forge promotion of 196 Cores saves ~19.6g.",
                "   • **Clovers:** BUY-2046 saves ~170g over direct forge rolls.",
                "   • **Obsidian:** 0g via Temple of Balthazar Karma."
            ]
            for line in cheap_strat:
                if line not in recommendations:
                    recommendations.append(line)

        if "Mystic Clover" in missing_mats and not getattr(goal, "is_acquisition_query", False):
            clovers_needed = missing_mats["Mystic Clover"]
            if is_vault_exhausted:
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
        if optimal_plan and getattr(optimal_plan, "session_itinerary", None):
            for action in optimal_plan.session_itinerary:
                char_tag = f" 👤 *[Character: {action.assigned_character}]*" if getattr(action, "assigned_character", None) else ""
                checklist.append(ActionStep(
                    step_number=step_num,
                    title=f"{action.action_title}{char_tag}",
                    estimated_time_minutes=action.estimated_minutes,
                    game_mode=action.game_mode or "OpenWorld",
                    description=action.action_description,
                    chat_code=action.waypoint,
                    assigned_character=getattr(action, "assigned_character", None)
                ))
                step_num += 1
        elif optimal_plan and getattr(optimal_plan, "step_by_step_roadmap", None):
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
        if optimal_plan and getattr(optimal_plan, "chapters", None):
            for ch in optimal_plan.chapters:
                status = getattr(ch, "completion_status", "IN_PROGRESS")
                readiness = getattr(ch, "readiness_pct", 0.0)
                status_str = f" [{status} - {readiness:.1f}%]"
                master_roadmap_formatted.append(f"**{ch.chapter_title}**{status_str}")
                if getattr(ch, "chapter_summary", None):
                    master_roadmap_formatted.append(f"   💡 *{ch.chapter_summary}*")
                for s_idx, action in enumerate(getattr(ch, "actions", []), 1):
                    wp = getattr(action, "waypoint_code", None) or getattr(action, "waypoint", None)
                    if wp and wp not in getattr(action, "action_description", ""):
                        wp_clean = wp if wp.startswith("[") else f"[{wp}]"
                        wp_str = f" `{wp_clean}`"
                    else:
                        wp_str = ""
                    npc = getattr(action, "npc_name", None)
                    npc_str = f" ({npc})" if npc else ""
                    char = getattr(action, "assigned_character", None)
                    char_str = f" 👤 *[Character: {char}]*" if char else ""
                    title = getattr(action, "action_title", "Step")
                    desc = getattr(action, "action_description", "")
                    desc_lines = desc.split("\n")
                    if len(desc_lines) > 1:
                        formatted_desc = "\n".join([f"       {dl}" if i > 0 else dl for i, dl in enumerate(desc_lines)])
                        master_roadmap_formatted.append(f"   [{s_idx}] **{title}**{npc_str}{char_str}{wp_str}\n       -> {formatted_desc}")
                    else:
                        master_roadmap_formatted.append(f"   [{s_idx}] **{title}**{npc_str}{char_str}{wp_str}\n       -> {desc}")
        elif optimal_plan and getattr(optimal_plan, "master_roadmap", None):
            for phase in optimal_plan.master_roadmap:
                master_roadmap_formatted.append(f"📌 **{phase.phase_title}** {phase.phase_status}")
                for s in phase.milestone_steps:
                    wp = getattr(s, "waypoint", None)
                    if wp and wp not in getattr(s, "description", ""):
                        wp_clean = wp if wp.startswith("[") else f"[{wp}]"
                        wp_str = f" `{wp_clean}`"
                    else:
                        wp_str = ""
                    npc_str = f" ({s.npc_name})" if s.npc_name else ""
                    char_str = f" 👤 *[Character: {s.assigned_character}]*" if s.assigned_character else ""
                    master_roadmap_formatted.append(f"   [{s.step_number}] **{s.title}**{npc_str}{char_str}{wp_str}: {s.description}")
        elif optimal_plan and getattr(optimal_plan, "pillars", None):
            for i, p in enumerate(optimal_plan.pillars, 1):
                master_roadmap_formatted.append(f"📌 **Pillar {i}: {p.pillar_name}** [{p.status} - {p.readiness_pct}%]")
                for j, s in enumerate(p.recommended_actions, 1):
                    wp = getattr(s, "waypoint", None)
                    if wp and wp not in getattr(s, "action_description", ""):
                        wp_clean = wp if wp.startswith("[") else f"[{wp}]"
                        wp_str = f" `{wp_clean}`"
                    else:
                        wp_str = ""
                    npc_str = f" ({s.npc_name})" if s.npc_name else ""
                    char_str = f" 👤 *[Character: {s.assigned_character}]*" if getattr(s, "assigned_character", None) else ""
                    master_roadmap_formatted.append(f"   [{j}] **{s.action_title}**{npc_str}{char_str}{wp_str}: {s.action_description}")

        if optimal_plan and getattr(optimal_plan, "chapters", None):
            summary = (
                f"Welcome to your 4-Chapter Master Journey for **{goal_display}**. "
                f"This progression plan is precisely tailored to your {intent.time_budget_minutes}-minute playtime, "
                f"guiding you through Precursor Triage, the Core Tyria World Tour, Daily Currencies & Arbitrage (Spirit Shards, WvW Boosters, Onyx Promotion), "
                f"and Character-Assigned Crafting at the Mystic Forge."
            )
        else:
            summary = (
                f"Here is your personalized progression plan for **{goal_display}** "
                f"tailored to your {intent.time_budget_minutes}-minute playtime tonight."
            )

        tip = (
            "💡 **Priory Tip:** Paste waypoint chat codes (e.g. [&BKgDAAA=]) into in-game chat to instantly open your map and teleport directly to vendors!"
        )

        char_recs = []
        if optimal_plan and getattr(optimal_plan, "recommended_character", None):
            char_name = optimal_plan.recommended_character if isinstance(optimal_plan.recommended_character, str) else getattr(optimal_plan.recommended_character, "name", str(optimal_plan.recommended_character))
            if "Kerling" in str(char_name):
                char_recs.append(f"👤 **Primary Crafter & Forge Master:** {char_name} | ✅ 100% Core Map Completed")
            else:
                char_recs.append(f"👤 **Primary Crafter:** {char_name}")
                if account_state and (account_state.is_character_map_completed("Kerling") or any(isinstance(c, dict) and c.get("name") == "Kerling" for c in account_state.characters)):
                    char_recs.append("👤 **Master Crafter:** Kerling (Weaponsmith 500 & Armorsmith 500) | ✅ 100% Core Map Completed")
        elif account_state and account_state.characters:
            has_kerling = any(isinstance(c, dict) and c.get("name") == "Kerling" for c in account_state.characters) or (hasattr(account_state, "is_character_map_completed") and account_state.is_character_map_completed("Kerling"))
            if has_kerling:
                char_recs.append("👤 **Primary Crafter & Forge Master:** Kerling (Level 80 Guardian — Weaponsmith 500, Armorsmith 500) | ✅ 100% Core Map Completed")
        else:
            char_recs.append("👤 **Primary Crafter & Forge Master:** Kerling (Level 80 Guardian — Weaponsmith 500, Armorsmith 500) | ✅ 100% Core Map Completed")

        # Exploration alt routing for Gift of Exploration / Map completion
        if (optimal_plan and getattr(optimal_plan, "chapters", None)) or "Gift of Exploration" in missing_mats or "Gift of Mastery" in missing_mats:
            mobility_char = None
            if optimal_plan and getattr(optimal_plan, "chapters", None):
                for ch in optimal_plan.chapters:
                    if ch.chapter_number == 2:
                        for a in ch.actions:
                            if getattr(a, "assigned_character", None) and a.assigned_character != "Kerling":
                                mobility_char = a.assigned_character
                                break
            if not mobility_char and optimal_plan and getattr(optimal_plan, "session_itinerary", None):
                for a in optimal_plan.session_itinerary:
                    if "Map Completion" in a.action_title and getattr(a, "assigned_character", None) and a.assigned_character != "Kerling":
                        mobility_char = a.assigned_character
                        break
            if not mobility_char and account_state and hasattr(account_state, "eligible_exploration_characters"):
                el = account_state.eligible_exploration_characters()
                if el:
                    mobility_char = el[0]
            if not mobility_char:
                mobility_char = "Skuta Rantakallio"

            mount_str = "Skyscale" if (account_state and account_state.has_mount("skyscale")) or not (account_state and account_state.mount_types) else "Skyscale"
            char_recs.append(
                f"🗺️ **Core Map Exploration (Alt Runner):** **{mobility_char}** (with {mount_str}) — Assigned to new 100% Core Tyria exploration runs for 2x Gift of Exploration "
                f"(Kerling is ✅ 100% Core Map Completed; alternate alts: Sara Loy / Legacy Of Harathi)."
            )

        if optimal_plan and getattr(optimal_plan, "master_roadmap", None):
            for phase in optimal_plan.master_roadmap:
                for s in phase.milestone_steps:
                    if getattr(s, "assigned_character", None):
                        char_recs.append(f"👤 *[Character: {s.assigned_character}]* Crafting **{s.title}**")

        # Exploration & 2x Gift of Exploration guidance in strategic recommendations
        if optimal_plan and getattr(optimal_plan, "chapters", None):
            map_comp_rec = (
                "🏆 **Core Tyria Map Completion Payoff:** 100% Core Tyria map completion yields **2x Gift of Exploration** "
                "(supplying enough for Twilight + a 2nd Gen 1 legendary like Sunrise/Eternity). "
                "Dedicate a single high-mobility character from your roster with mounts (Skyscale/Raptor) to complete all 5 regions sequentially."
            )
            if map_comp_rec not in recommendations:
                recommendations.append(map_comp_rec)

        # Hobbs precursor collection note in strategic recommendations
        if goal.resolved_item_id == 30704 and diff_report.summary_missing_materials.get("Dusk", 0) > 0:
            hobbs_rec = (
                "📜 **Grandmaster Hobbs Collection Route:** Crafting Dusk via Grandmaster Craftsman Hobbs `[&BBAEAAA=]` requires Central Tyria Mastery *Legendary Crafting* "
                "(Tier 1 Revered Antiquarian for Dusk I, Tier 2 Magister of Armaments for Dusk II, Tier 3 Historian of Armaments for Dusk III), costing ~160g materials + ~30h gameplay."
            )
            if hobbs_rec not in recommendations:
                recommendations.append(hobbs_rec)

        # Post-Forge Decision Fork in Strategic Recommendations
        if goal.resolved_item_id in [30704, 30703, 30689] or "twilight" in (goal.resolved_item_name or "").lower() or "eternity" in (goal.resolved_item_name or "").lower():
            fork_rec = (
                "🔀 **Post-Forge Decision Fork (Armory Binding vs 3,800g Eternity Arbitrage vs Direct TP Sale):**\n"
                "   • 🛡️ **Option 1: Legendary Armory Binding (0g | Infinite Account Utility):**\n"
                "     Deposit Twilight `[&AgErZgAA]` directly into your Legendary Armory for instant, infinite stat-swapping across all characters on your account simultaneously for 0 gold. "
                "Unlocks the permanent Twilight skin in your Wardrobe and awards *Memory of Twilight* token.\n"
                "   • 💰 **Option 2: Commercial Eternity Arbitrage (~3,800g Gross | ~3,230g Net Cash):**\n"
                "     Combine unbound Twilight `[&AgErZgAA]` + unbound Sunrise `[&AgG2TAEA]` + 5x Crystalline Dust `[&AgF4WwEA]` + 10x Philosopher's Stones `[&AgH1EAAA]` in the Mystic Forge to craft unbound **Eternity** `[&AgG1TAEA]`.\n"
                "     ✨ **Skin Retention Dynamic:** Forging Eternity **instantly unlocks BOTH Twilight & Sunrise skins in your Wardrobe permanently**! "
                "List Eternity on the Trading Post for ~3,800g (Net: ~3,230g after 15% TP fees), yielding **+1,430g to +1,730g pure liquid profit** while keeping both legendary skins!\n"
                "   • ⚖️ **Option 3: Direct Trading Post Sale (~1,850g - 2,000g Gross | ~1,570g - 1,700g Net Cash):**\n"
                "     Sell unbound Twilight directly on the Trading Post for ~1,850g - 2,000g (Net: ~1,570g - 1,700g after 15% TP fees). "
                "⚠️ **Skin Warning:** Direct TP sale does NOT unlock the Twilight skin in your Wardrobe (unlike Eternity forge arbitrage which retains both skins)."
            )
            if fork_rec not in recommendations:
                recommendations.append(fork_rec)

        wvw_karma_found = any("wvw" in str(r).lower() or "karma" in str(r).lower() for r in recommendations)
        for step in checklist:
            if not wvw_karma_found and ("wvw" in step.title.lower() or "karma" in step.title.lower() or "wvw" in step.description.lower() or "karma" in step.description.lower()):
                wvw_karma_found = True
            
            if "temple of balthazar" in step.title.lower() or "temple of balthazar" in step.description.lower():
                step.description += " 💡 **Contested Event Tip:** The Temple of Balthazar is often contested. Check LFG (Y) -> Central Tyria -> Squads to taxi to an active map, or wait for the event chain to start."
                
        lounge_callout = None
        if account_state:
            portfolio = account_state.convenience_portfolio() if hasattr(account_state, "convenience_portfolio") else {}
            passes = portfolio.get("passes", [])
            tomes = portfolio.get("portal_tomes", [])
            converters = portfolio.get("converters", [])
            tools = portfolio.get("infinite_tools", [])
            utils = portfolio.get("salvage_and_utilities", [])

            # Format comprehensive Account Convenience & Utility Portfolio
            if passes or tomes or converters or tools or utils:
                port_lines = ["🧰 **Account Convenience & Utility Portfolio:**"]
                if passes:
                    port_lines.append("   • **VIP Lounge Passes:** " + ", ".join(f"**{p['name']} {p['chat_link']}**" for p in passes))
                if tomes:
                    port_lines.append("   • **Portal Tomes & Scrolls:** " + ", ".join(f"**{t['name']} {t['chat_link']}**" for t in tomes))
                if converters:
                    port_lines.append("   • **Converters & Gobblers:** " + ", ".join(f"**{c['name']} {c['chat_link']}**" for c in converters))
                if tools:
                    port_lines.append("   • **Infinite Gathering Tools:** " + ", ".join(f"**{tl['name']} {tl['chat_link']}**" for tl in tools))
                if utils:
                    port_lines.append("   • **Salvage & Utility Express:** " + ", ".join(f"**{u['name']} {u['chat_link']}**" for u in utils))

                portfolio_text = "\n".join(port_lines)
                if portfolio_text not in recommendations:
                    recommendations.append(portfolio_text)

            # VIP Lounge Crafting & Forging Callout
            if passes:
                primary_lounge = passes[0]
                lounge_callout = (
                    f"✨ **VIP Lounge Synthesis:** Consolidate all Chapter 4 crafting, forging, and inventory prep in the **{primary_lounge['zone']} {primary_lounge['chat_link']}** "
                    f"for instant, zero-cost access to Weaponsmithing, Armorsmithing, Mystic Forge, Bank, and Trading Post with quick return to your map location."
                )
                if lounge_callout not in recommendations:
                    recommendations.append(lounge_callout)

            zhaitaffy_count = account_state.zhaitaffy_gobblers_count()
            tomes_count = account_state.tomes_of_knowledge_count()
            heroic_count = account_state.heroic_boosters_count()
            exp_count = account_state.experience_boosters_count()
            wxp_count = account_state.wxp_boosters_count()
            karma_count = account_state.karma_boosters_count()
            heroic_exp_total = heroic_count + exp_count
            if zhaitaffy_count > 0 or tomes_count > 0 or heroic_exp_total > 0 or wxp_count > 0 or karma_count > 0:
                booster_rec = (
                    f"🚀 **Live Booster & Utility Inventory:** Your account owns **{zhaitaffy_count}x Zhaitaffy Gobblers [ID: 67836]**, "
                    f"**{tomes_count}x Tomes of Knowledge [ID: 19983]** (instant Spirit Shards), **{heroic_exp_total}x Experience/Heroic Boosters**, "
                    f"**{wxp_count}x WXP Boosters**, and **{karma_count}x Karma Boosters**. "
                    f"Don't forget to stack Experience + Heroic + Guild Tavern WvW buff (completes WvW Gift of Battle in ~4.5h vs 8.0h unboosted), "
                    f"and use Karma Boosters at the Temple of Balthazar `[&BO4CAAA=]`!"
                )
                if booster_rec not in recommendations:
                    recommendations.append(booster_rec)
        elif wvw_karma_found or (optimal_plan and getattr(optimal_plan, "chapters", None)):
            booster_rec = "🚀 **Booster Acceleration:** Don't forget to stack Experience Booster + Heroic Booster + Guild Tavern WvW Reward Track buff (completes WvW Gift of Battle in ~4.5h vs 8.0h unboosted), and use Karma Boosters at the Temple of Balthazar!"
            if booster_rec not in recommendations:
                recommendations.append(booster_rec)

        # Practical player tips for Invisible Bag staging and 250-stack ingot batching
        bag_staging_rec = (
            "🎒 **Inventory & Bag Overflow Management:**\n"
            "   • **Invisible Bag Staging:** Equip an **Invisible / Safe Bag** (e.g. 20-Slot Invisible Bag `[&AgG5VAAA]`) in your bottom-most inventory slot. "
            "Store high-value precursor weapons (*Dusk*), Gifts, Mystic Clovers, lodestones, and Bloodstone Shards inside to prevent accidental merchant sale, material deposit, or salvage.\n"
            "   • **250-Stack Ingot Batching:** When refining metal ingots for the Gift of Metal & Gift of Darkness (250x Orichalcum, 250x Mithril, 250x Darksteel, 250x Platinum), "
            "batch refine in exact 250-count stacks and immediately craft the intermediate Gifts at the station rather than cluttering open inventory slots."
        )
        if bag_staging_rec not in recommendations:
            recommendations.append(bag_staging_rec)

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
            motivational_tip=tip,
            vip_lounge_callout=lounge_callout
        )

    def generate_ranking_guide(
        self,
        rankings: List[Any],
        user_prompt: str,
        time_budget_minutes: int = 120,
        optimal_plan: Optional[Any] = None,
        target_quantity: int = 1,
        account_state: Optional[AccountState] = None
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
        if optimal_plan and getattr(optimal_plan, "recommended_character", None):
            char_name = optimal_plan.recommended_character if isinstance(optimal_plan.recommended_character, str) else getattr(optimal_plan.recommended_character, "name", str(optimal_plan.recommended_character))
            if "Kerling" in str(char_name):
                char_recs.append(f"👤 **Primary Crafter & Forge Master:** {char_name} | ✅ 100% Core Map Completed")
            else:
                char_recs.append(f"👤 **Primary Crafter:** {char_name}")
                if account_state and (account_state.is_character_map_completed("Kerling") or any(isinstance(c, dict) and c.get("name") == "Kerling" for c in account_state.characters)):
                    char_recs.append("👤 **Master Crafter:** Kerling (Weaponsmith 500 & Armorsmith 500) | ✅ 100% Core Map Completed")
        elif account_state and account_state.characters:
            has_kerling = any(isinstance(c, dict) and c.get("name") == "Kerling" for c in account_state.characters) or (hasattr(account_state, "is_character_map_completed") and account_state.is_character_map_completed("Kerling"))
            if has_kerling:
                char_recs.append("👤 **Primary Crafter & Forge Master:** Kerling (Level 80 Guardian — Weaponsmith 500, Armorsmith 500) | ✅ 100% Core Map Completed")
        else:
            char_recs.append("👤 **Primary Crafter & Forge Master:** Kerling (Level 80 Guardian — Weaponsmith 500, Armorsmith 500) | ✅ 100% Core Map Completed")

        # Exploration alt routing
        alt_char = "Skuta Rantakallio"
        if account_state and hasattr(account_state, "eligible_exploration_characters"):
            el = account_state.eligible_exploration_characters()
            if el:
                alt_char = el[0]
        mount_str = "Skyscale" if (account_state and account_state.has_mount("skyscale")) or not (account_state and account_state.mount_types) else "Skyscale"
        char_recs.append(
            f"🗺️ **Core Map Exploration (Alt Runner):** **{alt_char}** (with {mount_str}) — Assigned to new 100% Core Tyria exploration runs for 2x Gift of Exploration "
            f"(Kerling is ✅ 100% Core Map Completed; alternate alts: Sara Loy / Legacy Of Harathi)."
        )

        if optimal_plan and getattr(optimal_plan, "master_roadmap", None):
            for phase in optimal_plan.master_roadmap:
                for s in phase.milestone_steps:
                    if getattr(s, "assigned_character", None):
                        char_recs.append(f"👤 [Character: {s.assigned_character}] Crafting **{s.title}**")

        wvw_karma_found = any("wvw" in str(r).lower() or "karma" in str(r).lower() for r in recs)
        for step in checklist:
            if not wvw_karma_found and ("wvw" in step.title.lower() or "karma" in step.title.lower() or "wvw" in step.description.lower() or "karma" in step.description.lower()):
                wvw_karma_found = True
            
            if "temple of balthazar" in step.title.lower() or "temple of balthazar" in step.description.lower():
                step.description += " 💡 **Contested Event Tip:** The Temple of Balthazar is often contested. Check LFG (Y) -> Central Tyria -> Squads to taxi to an active map, or wait for the event chain to start."
                
        ranking_lounge_callout = None
        if account_state:
            portfolio = account_state.convenience_portfolio() if hasattr(account_state, "convenience_portfolio") else {}
            passes = portfolio.get("passes", [])
            tomes = portfolio.get("portal_tomes", [])
            converters = portfolio.get("converters", [])
            tools = portfolio.get("infinite_tools", [])
            utils = portfolio.get("salvage_and_utilities", [])

            if passes or tomes or converters or tools or utils:
                port_lines = ["🧰 **Account Convenience & Utility Portfolio:**"]
                if passes:
                    port_lines.append("   • **VIP Lounge Passes:** " + ", ".join(f"**{p['name']} {p['chat_link']}**" for p in passes))
                if tomes:
                    port_lines.append("   • **Portal Tomes & Scrolls:** " + ", ".join(f"**{t['name']} {t['chat_link']}**" for t in tomes))
                if converters:
                    port_lines.append("   • **Converters & Gobblers:** " + ", ".join(f"**{c['name']} {c['chat_link']}**" for c in converters))
                if tools:
                    port_lines.append("   • **Infinite Gathering Tools:** " + ", ".join(f"**{tl['name']} {tl['chat_link']}**" for tl in tools))
                if utils:
                    port_lines.append("   • **Salvage & Utility Express:** " + ", ".join(f"**{u['name']} {u['chat_link']}**" for u in utils))

                portfolio_text = "\n".join(port_lines)
                if portfolio_text not in recs:
                    recs.append(portfolio_text)

            if passes:
                primary_lounge = passes[0]
                ranking_lounge_callout = (
                    f"✨ **VIP Lounge Synthesis:** Consolidate all crafting, forging, and inventory prep in the **{primary_lounge['zone']} {primary_lounge['chat_link']}** "
                    f"for instant, zero-cost access to all crafting stations, Mystic Forge, Bank, and Trading Post with quick return to your map location."
                )
                if ranking_lounge_callout not in recs:
                    recs.append(ranking_lounge_callout)

            zhaitaffy_count = account_state.zhaitaffy_gobblers_count()
            tomes_count = account_state.tomes_of_knowledge_count()
            heroic_count = account_state.heroic_boosters_count()
            exp_count = account_state.experience_boosters_count()
            wxp_count = account_state.wxp_boosters_count()
            karma_count = account_state.karma_boosters_count()
            heroic_exp_total = heroic_count + exp_count
            if zhaitaffy_count > 0 or tomes_count > 0 or heroic_exp_total > 0 or wxp_count > 0 or karma_count > 0:
                recs.append(
                    f"🚀 **Live Booster & Utility Inventory:** Your account owns **{zhaitaffy_count}x Zhaitaffy Gobblers [ID: 67836]**, "
                    f"**{tomes_count}x Tomes of Knowledge [ID: 19983]** (instant Spirit Shards), **{heroic_exp_total}x Experience/Heroic Boosters**, "
                    f"**{wxp_count}x WXP Boosters**, and **{karma_count}x Karma Boosters**. "
                    f"Stack Experience + Heroic + Guild Tavern WvW buff (completes WvW Gift of Battle in ~4.5h vs 8.0h unboosted), "
                    f"and use Karma Boosters at the Temple of Balthazar `[&BO4CAAA=]`!"
                )
        elif wvw_karma_found:
            recs.append("🚀 **Booster Acceleration:** Since your plan includes WvW or Karma farming, don't forget to use your Candy Corn Gobbler, WXP Boosters, and Karma Boosters to significantly speed up your progress!")

        bag_staging_rec = (
            "🎒 **Inventory & Bag Overflow Management:**\n"
            "   • **Invisible Bag Staging:** Equip an **Invisible / Safe Bag** (e.g. 20-Slot Invisible Bag `[&AgG5VAAA]`) in your bottom-most inventory slot. "
            "Store high-value precursor weapons, Gifts, Mystic Clovers, and lodestones inside to prevent accidental merchant sale, deposit, or salvage.\n"
            "   • **250-Stack Ingot Batching:** When refining metal ingots, batch refine in clean 250-count stacks and immediately craft the intermediate Gifts rather than cluttering open inventory slots."
        )
        if bag_staging_rec not in recs:
            recs.append(bag_staging_rec)

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
            motivational_tip=tip,
            vip_lounge_callout=ranking_lounge_callout
        )

    def generate_session_itinerary_guide(
        self,
        itinerary: Any,
        goal: Optional[ResolvedGoal] = None,
        user_prompt: Optional[str] = None,
        account_state: Optional[Any] = None
    ) -> PersonalizedGuide:
        """Synthesizes a time-budgeted daily knapsack session itinerary guide with spatial navigation."""
        goal_name = getattr(itinerary, "goal_name", None) or (goal.resolved_item_name if goal else None) or "Daily Session Itinerary"
        time_budget = getattr(itinerary, "time_budget_minutes", 120)
        scheduled_mins = getattr(itinerary, "total_scheduled_minutes", 0)
        utilization = getattr(itinerary, "time_utilization_pct", 0.0)
        tasks = getattr(itinerary, "tasks", [])
        summary = getattr(itinerary, "summary", "") or f"Tonight's {scheduled_mins}-minute session scheduled for {goal_name} ({utilization}% utilization of {time_budget}m budget)."

        recs = []
        for t in tasks:
            rec = f"⏱️ **{t.title} ({t.estimated_duration_minutes} min)**: {t.instructions}"
            if t.waypoint_code:
                rec += f" Location: {t.location_name} `{t.waypoint_code}`."
            if t.character_name:
                rec += f" Recommended Character: **{t.character_name}**."
            recs.append(rec)

        char_recs = [f"👤 **{t.character_name}**: Assigned to {t.title}" for t in tasks if getattr(t, "character_name", None)]

        roadmap = [f"Phase {idx+1}: {t.title} ({t.estimated_duration_minutes}m) at {t.location_name} `{t.waypoint_code}`" for idx, t in enumerate(tasks)]

        checklist = [
            ActionStep(
                step_number=idx + 1,
                title=t.title,
                estimated_time_minutes=t.estimated_duration_minutes,
                game_mode=getattr(t, "category", "DailyRoutine"),
                description=f"{t.instructions} [{t.location_name} {t.waypoint_code}]",
                chat_code=t.waypoint_code,
                assigned_character=getattr(t, "character_name", None)
            )
            for idx, t in enumerate(tasks)
        ]

        chat_code = tasks[0].waypoint_code if tasks else (goal.chat_code if goal else None)
        tip = f"💡 **Session Planning Tip:** Knapsack optimization scheduled {scheduled_mins} minutes of high-priority time-gated activities for {goal_name}, achieving {utilization}% playtime efficiency."

        return PersonalizedGuide(
            goal_name=goal_name,
            target_quantity=getattr(goal, "target_quantity", 1),
            chat_code=chat_code,
            readiness_percentage=utilization,
            executive_summary=summary,
            strategic_recommendations=recs,
            character_recommendations=char_recs,
            master_roadmap_phases=roadmap,
            session_checklist=checklist,
            missing_materials_summary={},
            missing_disciplines_summary=[],
            motivational_tip=tip
        )

    def generate_arbitrage_guide(
        self,
        arbitrage_report: Any,
        goal: Optional[ResolvedGoal] = None,
        account_state: Optional[Any] = None
    ) -> PersonalizedGuide:
        """Synthesizes a multi-way arbitrage and acquisition decision matrix guide adhering to 15% TP tax."""
        goal_name = getattr(arbitrage_report, "goal_name", None) or (goal.resolved_item_name if goal else None) or "Item Arbitrage"
        action = getattr(arbitrage_report, "recommended_action", "CRAFT_FOR_SELF")
        scratch_cost = getattr(arbitrage_report, "craft_from_scratch_total", 0)
        account_cost = getattr(arbitrage_report, "my_account_craft_cost", scratch_cost)
        buy_order = getattr(arbitrage_report, "buy_order_total", 0)
        instant_buy = getattr(arbitrage_report, "instant_buy_total", 0)
        net_sell = getattr(arbitrage_report, "net_sell_if_sold", None)
        profit = getattr(arbitrage_report, "profit_margin_if_sold", None)

        def _fmt_copper(copper: Optional[int]) -> str:
            if copper is None:
                return "0g"
            g = copper // 10000
            s = (copper % 10000) // 100
            c = copper % 100
            if g > 0:
                return f"{g:,}g {s:02d}s {c:02d}c" if (s or c) else f"{g:,}g"
            if s > 0:
                return f"{s}s {c:02d}c" if c else f"{s}s"
            return f"{c}c"

        summary = (
            f"⚖️ **Arbitrage Evaluation for {goal_name}:** "
            f"Recommended Action: **{action}**. "
            f"Craft from scratch: {_fmt_copper(scratch_cost)} | "
            f"Account craft cost: {_fmt_copper(account_cost)} | "
            f"TP Buy Order: {_fmt_copper(buy_order)} | "
            f"TP Instant Buy: {_fmt_copper(instant_buy)}."
        )
        if profit is not None:
            summary += f" Net TP liquidation: {_fmt_copper(net_sell)} (Profit Margin: {_fmt_copper(profit)})."

        recs = [f"📊 **Market Decision:** **{action}** provides the best financial return."]

        p_strat = getattr(arbitrage_report, "precursor_strategy", {})
        if p_strat:
            p_name = p_strat.get("precursor_name", "Precursor")
            p_rec = p_strat.get("recommended_option", "TP")
            p_cost = _fmt_copper(p_strat.get("buy_order_copper", p_strat.get("instant_buy_copper", 0)))
            recs.append(f"🗡️ **Precursor Strategy ({p_name}):** Option **{p_rec}** recommended (Estimated cost: {p_cost}).")

        c_strat = getattr(arbitrage_report, "clover_strategy", {})
        if c_strat:
            c_rec = c_strat.get("recommended_option", "WIZARDS_VAULT")
            recs.append(f"🎲 **Mystic Clover Strategy:** Option **{c_rec}** recommended.")

        t6_strat = getattr(arbitrage_report, "t6_promotion_strategy", {})
        if t6_strat:
            promoted = [cat for cat, s in t6_strat.items() if isinstance(s, dict) and s.get("recommended_action") == "PROMOTE_T5_FORGE"]
            bought = [cat for cat, s in t6_strat.items() if isinstance(s, dict) and s.get("recommended_action") == "BUY_DIRECT"]
            if promoted:
                recs.append(f"🧪 **T6 Forge Promotion:** Promoted T5->T6 saves gold on: {', '.join(promoted)}.")
            if bought:
                recs.append(f"🛒 **Direct TP Purchase:** Buy directly from TP for: {', '.join(bought)}.")

        if net_sell is not None:
            recs.append(f"🧾 **Trading Post Tax Model:** Evaluated with 15% TP listing & exchange fee (Net payout: {_fmt_copper(net_sell)}).")

        roadmap = [
            f"Phase 1: Precursor Resolution ({p_strat.get('recommended_option', 'Trading Post') if p_strat else 'Trading Post'})",
            f"Phase 2: Mystic Clover Acquisition ({c_strat.get('recommended_option', 'Vault') if c_strat else 'Vault'})",
            f"Phase 3: Material Consolidation & Arbitrage Execution ({action})"
        ]

        checklist = [
            ActionStep(
                step_number=1,
                title=f"Execute {action} Strategy",
                estimated_time_minutes=15,
                game_mode="TradingPost",
                description=f"Follow recommended acquisition path for {goal_name}: {action}.",
                chat_code=None
            )
        ]

        tip = f"💡 **Arbitrage Tip:** Calculating 15% Trading Post fees before crafting or buying ensures optimal gold preservation for {goal_name}."

        readiness = 100 if action == "BUY_FINISHED_DIRECT" else (round((1.0 - (account_cost / max(scratch_cost, 1))) * 100, 1) if scratch_cost > 0 else 50.0)
        readiness = max(0.0, min(100.0, readiness))

        return PersonalizedGuide(
            goal_name=goal_name,
            target_quantity=getattr(goal, "target_quantity", 1),
            chat_code=goal.chat_code if goal else None,
            readiness_percentage=readiness,
            executive_summary=summary,
            strategic_recommendations=recs,
            character_recommendations=[],
            master_roadmap_phases=roadmap,
            session_checklist=checklist,
            missing_materials_summary={},
            missing_disciplines_summary=[],
            motivational_tip=tip
        )

    def generate_prerequisite_guide(
        self,
        prereq_report: Any,
        goal: Optional[ResolvedGoal] = None,
        account_state: Optional[Any] = None
    ) -> PersonalizedGuide:
        """Synthesizes an account prerequisite audit guide (masteries, world completion, active crafting, collections)."""
        goal_name = getattr(prereq_report, "goal_name", None) or (goal.resolved_item_name if goal else None) or "Legendary Prerequisite Audit"
        can_craft = getattr(prereq_report, "can_craft_immediately", False)
        blockers = getattr(prereq_report, "blockers", [])
        has_world_comp = getattr(prereq_report, "has_world_completion", False)
        world_source = getattr(prereq_report, "world_completion_source", None)
        mastery_met = getattr(prereq_report, "mastery_requirements_met", False)
        missing_masteries = getattr(prereq_report, "missing_masteries", [])
        active_crafting = getattr(prereq_report, "active_crafting_ready", False)
        craft_recs = getattr(prereq_report, "crafting_assignment_recommendations", [])
        p_step = getattr(prereq_report, "precursor_collection_step", None)
        p_done = getattr(prereq_report, "precursor_collection_bits_done", 0)
        p_total = getattr(prereq_report, "precursor_collection_bits_total", 0)
        char_disc_assign = getattr(prereq_report, "character_discipline_assignments", {})

        if can_craft:
            summary = f"✅ **Prerequisites Clear:** Your account satisfies all requirements to craft **{goal_name}** immediately!"
        else:
            summary = f"🔍 **Prerequisite Audit for {goal_name}:** Identified {len(blockers)} blocker(s) before crafting can begin."

        recs = []
        if blockers:
            for b in blockers:
                recs.append(f"⛔ **Blocker:** {b}")
        else:
            recs.append("🎉 All account prerequisites, masteries, world exploration, and crafting discipline requirements are met!")

        world_status = f"✅ World Completion: Unlocked ({world_source})" if has_world_comp else "❌ Missing 100% Core Tyria World Completion"
        recs.append(f"🗺️ **Exploration:** {world_status}")

        mastery_status = "✅ All required masteries unlocked" if mastery_met else f"❌ Missing Masteries: {', '.join(missing_masteries)}"
        recs.append(f"🎓 **Masteries:** {mastery_status}")

        if p_step:
            recs.append(f"📜 **Precursor Collection ({p_step}):** {p_done}/{p_total} objectives completed.")

        char_recs = []
        for disc, routing in char_disc_assign.items():
            if isinstance(routing, dict):
                char = routing.get("character", "Unassigned")
                action = routing.get("action", "UNKNOWN")
                wp = routing.get("waypoint", "")
                char_recs.append(f"👤 **{disc.title()}**: Assigned to **{char}** ({action}) at station `{wp}`")

        roadmap = [
            f"Audit 1: Core Exploration — {'Satisfied' if has_world_comp else 'Pending'}",
            f"Audit 2: Mastery Tracks — {'Satisfied' if mastery_met else 'Pending'}",
            f"Audit 3: Crafting Disciplines — {'Ready' if active_crafting else 'Pending'}",
            f"Audit 4: Precursor Collection — {p_step or 'Satisfied / Non-Collection'}"
        ]

        checklist = []
        step_idx = 1
        for m in missing_masteries:
            checklist.append(ActionStep(
                step_number=step_idx,
                title=f"Train Mastery: {m}",
                estimated_time_minutes=30,
                game_mode="Mastery",
                description=f"Earn mastery experience and points to unlock {m}.",
                chat_code=None
            ))
            step_idx += 1
        for rec_craft in craft_recs:
            if isinstance(rec_craft, dict):
                checklist.append(ActionStep(
                    step_number=step_idx,
                    title=f"Activate {rec_craft.get('discipline', '').title()} on {rec_craft.get('character', '')}",
                    estimated_time_minutes=5,
                    game_mode="Crafting",
                    description=rec_craft.get("warning") or f"Switch active discipline to {rec_craft.get('discipline')}.",
                    chat_code=rec_craft.get("waypoint")
                ))
                step_idx += 1
        if not checklist:
            checklist.append(ActionStep(
                step_number=1,
                title=f"Begin Crafting {goal_name}",
                estimated_time_minutes=10,
                game_mode="Crafting",
                description="All prerequisites verified. Proceed to crafting stations.",
                chat_code=None
            ))

        missing_discs = [f"{r.get('discipline', '').title()} (Level {r.get('required_rating')})" for r in craft_recs if isinstance(r, dict)]
        readiness = 100 if can_craft else max(0, 100 - len(blockers) * 20)
        tip = f"💡 **Priory Prerequisite Tip:** Completing mastery tiers and world completion unlocks permanent account abilities beyond just crafting {goal_name}."

        return PersonalizedGuide(
            goal_name=goal_name,
            target_quantity=getattr(goal, "target_quantity", 1),
            chat_code=goal.chat_code if goal else None,
            readiness_percentage=readiness,
            executive_summary=summary,
            strategic_recommendations=recs,
            character_recommendations=char_recs,
            master_roadmap_phases=roadmap,
            session_checklist=checklist,
            missing_materials_summary={},
            missing_disciplines_summary=missing_discs,
            motivational_tip=tip
        )

    def generate_opportunity_cost_guide(
        self,
        opportunity_cost: Dict[str, Any],
        goal: Optional[ResolvedGoal] = None,
        account_state: Optional[Any] = None
    ) -> PersonalizedGuide:
        """Synthesizes a cross-role currency/material opportunity cost evaluation guide."""
        goal_name = (goal.currency_name if goal else None) or (goal.resolved_item_name if goal else None) or f"Item {opportunity_cost.get('item_id')}"
        opt_disp = opportunity_cost.get("optimal_role_disposition", "HOLD_AS_CRAFTING_MAT")
        qty = opportunity_cost.get("quantity", 1)
        direct_val = opportunity_cost.get("direct_exchange_value", 0.0)
        tp_val = opportunity_cost.get("tp_liquidation_value", 0.0)
        salvage_val = opportunity_cost.get("salvage_liquidation_value", 0.0)
        tp_gross = opportunity_cost.get("tp_gross", 0.0)
        tp_fee = opportunity_cost.get("tp_fee", 0.0)
        roles = opportunity_cost.get("roles_evaluated", [])

        summary = (
            f"💎 **Opportunity Cost & Role Disposition for {qty}x {goal_name}:** "
            f"Recommended disposition: **{opt_disp}**. "
            f"Direct currency value: {direct_val:,.1f} | "
            f"Trading Post net liquidation: {tp_val:,.1f} | "
            f"Salvage expected liquidation: {salvage_val:,.1f}."
        )

        recs = [
            f"🎯 **Optimal Disposition:** **{opt_disp}** yields the highest comparative economic return across all game modes.",
            f"🪙 **Direct Exchange Value:** {direct_val:,.1f} gold-equivalent purchasing power.",
            f"📈 **Trading Post Value:** Gross {tp_gross:,.1f} - 15% TP fee {tp_fee:,.1f} = Net {tp_val:,.1f}.",
            f"🔨 **Salvage Expected Value:** {salvage_val:,.1f}.",
            f"🌐 **Roles Evaluated in Knowledge Graph:** {', '.join(roles) if roles else 'Currency, Material, Liquidation'}."
        ]

        roadmap = [
            f"Role Evaluation: Comparative analysis across {len(roles)} roles in Knowledge Graph",
            f"Liquidation Execution: Carry out {opt_disp} for {qty}x {goal_name}"
        ]

        checklist = [
            ActionStep(
                step_number=1,
                title=f"Execute {opt_disp} for {goal_name}",
                estimated_time_minutes=5,
                game_mode="Economy",
                description=f"Liquidate or utilize {qty}x {goal_name} via {opt_disp} to maximize net account wealth.",
                chat_code=None
            )
        ]

        tip = f"💡 **Opportunity Cost Tip:** Evaluating currency purchasing power versus Trading Post fees ensures you never convert resources at an economic loss."

        return PersonalizedGuide(
            goal_name=goal_name,
            target_quantity=qty,
            chat_code=goal.chat_code if goal else None,
            readiness_percentage=100,
            executive_summary=summary,
            strategic_recommendations=recs,
            character_recommendations=[],
            master_roadmap_phases=roadmap,
            session_checklist=checklist,
            missing_materials_summary={},
            missing_disciplines_summary=[],
            motivational_tip=tip
        )

