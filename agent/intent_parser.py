"""Top LLM: Natural Language Intent & Constraint Parser for Project Priory.

Translates freeform player prompts into structured goal objects, constraints,
and resolves entity names to canonical Knowledge Graph URIs with multi-turn session awareness.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from agent.llm_client import BaseLLMClient, get_default_llm_client
from engine.semantic_query import SemanticQueryService


class GoalType(str, Enum):
    """Semantic classification of player intent."""
    SPECIFIC_ITEM = "SPECIFIC_ITEM"              # Targeting a specific item (e.g. 'Twilight', 'Aurene's Bite', '2 Legendary Sigils')
    COMPARATIVE_RANKING = "COMPARATIVE_RANKING"  # Comparative query (e.g. 'What am I closest to?', 'How far am I to a Gen 3?', 'What should I craft?')
    ACQUISITION_DISCOVERY = "ACQUISITION_DISCOVERY" # Inquiring how to farm/acquire materials/currencies (e.g. 'How do I farm Mystic Clovers?')
    EXPLORATORY_DISCOVERY = "EXPLORATORY_DISCOVERY" # Exploratory search across the knowledge graph
    SESSION_ITINERARY = "SESSION_ITINERARY"        # Time-budgeted session planning / playtime routine (e.g. 'What should I do tonight in 90 mins?')
    ARBITRAGE_EVALUATION = "ARBITRAGE_EVALUATION"  # Buy vs craft arbitrage and market decision (e.g. 'Should I craft or buy Twilight?')
    PREREQUISITE_AUDIT = "PREREQUISITE_AUDIT"      # Account prerequisites, masteries, world completion (e.g. 'Check my masteries for Nevermore')
    CURRENCY_OPPORTUNITY_COST = "CURRENCY_OPPORTUNITY_COST" # Cross-role currency opportunity cost (e.g. 'Best use of my Astral Acclaim')


class PlayerGoalIntent(BaseModel):
    """Structured intent and constraint parameters extracted from natural language by the Top LLM."""
    goal_type: GoalType = Field(
        default=GoalType.SPECIFIC_ITEM,
        description="The primary nature of the player's request: SPECIFIC_ITEM, COMPARATIVE_RANKING, ACQUISITION_DISCOVERY, EXPLORATORY_DISCOVERY, SESSION_ITINERARY, ARBITRAGE_EVALUATION, PREREQUISITE_AUDIT, or CURRENCY_OPPORTUNITY_COST."
    )
    target_item_name: Optional[str] = Field(
        default=None,
        description="The specific item name if the player specified one (e.g. 'Twilight', 'Aurene's Bite', 'The Moot', 'Mystic Clover', 'Legendary Sigil', 'Nevermore')."
    )
    currency_name: Optional[str] = Field(
        default=None,
        description="The specific currency or liquid material name if mentioned (e.g. 'Astral Acclaim', 'Mystic Clover', 'Spirit Shard', 'Laurel')."
    )
    currency_id: Optional[int] = Field(
        default=None,
        description="Resolved or extracted currency ID (e.g. 68 for Astral Acclaim, 23 for Spirit Shard)."
    )
    is_acquisition_query: bool = Field(
        default=False,
        description="Set to true if the player is asking how to farm, collect, or acquire materials/currencies rather than crafting a final legendary end-product."
    )
    facet_name: Optional[str] = Field(
        default=None,
        description="Elder dragon facet variant if mentioned (e.g. 'Zhaitan', 'Mordremoth', 'Kralkatorrik', 'Primordus', 'Jormag', 'Soo-Won')."
    )
    category_filter: Optional[str] = Field(
        default=None,
        description="Generation, expansion, slot, or weapon type facet if mentioned (e.g. 'Gen 1', 'Gen 2', 'Gen 3', 'Core', 'Heart of Thorns', 'Path of Fire', 'End of Dragons', 'Secrets of the Obscure', 'Janthir Wilds', 'Armor', 'Trinket', 'Upgrade', 'Spear', 'Greatsword')."
    )
    prefer_speed: bool = Field(
        default=False,
        description="Set to true if the player explicitly asks to craft quickly, fast, with least effort, or minimal time investment."
    )
    prefer_cheap: bool = Field(
        default=False,
        description="Set to true if the player explicitly asks for the cheapest way, lowest cost, or most cost-effective path (e.g. 'cheapest', 'least gold', 'save gold')."
    )
    wizards_vault_exhausted: bool = Field(
        default=False,
        description="Set to true if Wizard's Vault items (clovers, starter kits, astral acclaim) are bought, exhausted, or completed."
    )
    optimization_target: Optional[str] = Field(
        default=None,
        description="Target optimization strategy: 'cheapest_gold', 'fastest_time', etc."
    )
    target_quantity: int = Field(default=1, description="The desired number of items (e.g. 1, 2, 4).")
    time_budget_minutes: int = Field(default=120, description="Available playtime in minutes.")
    excluded_game_modes: List[str] = Field(default_factory=list, description="Game modes to avoid (e.g. WvW, PvP, Raids).")
    preferred_game_modes: List[str] = Field(default_factory=list, description="Preferred game modes (e.g. OpenWorld, Fractals).")
    exhausted_sources: List[str] = Field(default_factory=list, description="Sources already completed/exhausted by the player (e.g. WizardVault, Provisioners).")
    liquid_gold_budget: Optional[int] = Field(default=None, description="Available liquid gold budget in gold coins.")
    user_playstyle_notes: Optional[str] = Field(default=None, description="Additional context or notes about player style.")


class ResolvedGoal(BaseModel):
    """Player intent coupled with resolved Knowledge Graph identity."""
    intent: PlayerGoalIntent
    goal_type: GoalType = GoalType.SPECIFIC_ITEM
    resolved_item_id: Optional[int] = None
    resolved_item_name: Optional[str] = None
    currency_name: Optional[str] = None
    currency_id: Optional[int] = None
    time_budget_minutes: int = 120
    category_filter: Optional[str] = None
    is_acquisition_query: bool = False
    facet_name: Optional[str] = None
    prefer_speed: bool = False
    prefer_cheap: bool = False
    wizards_vault_exhausted: bool = False
    optimization_target: Optional[str] = None
    target_quantity: int = 1
    chat_code: Optional[str] = None


class IntentParser:
    """Parses player prompt into structured intent and links it to Knowledge Graph entities."""

    SYSTEM_PROMPT = (
        "You are an expert Guild Wars 2 goal analysis and intent parsing agent for Project Priory.\n"
        "Your role is to understand the player's objective and classify it into structured parameters:\n\n"
        "1. goal_type:\n"
        "   - 'COMPARATIVE_RANKING': Select this whenever the player asks what they are closest to, how far/close they are from a generation/expansion/category, asks for recommendations, asks what to craft next, or asks about progress without naming a single specific item (e.g., 'How far am I to a Generation 3 legendary?', 'What legendary can I craft?', 'Which gen 2 am I closest to?', 'Where do I stand on legendary armor?').\n"
        "   - 'SPECIFIC_ITEM': Select this when the player targets a specific, concrete item to craft (e.g., 'How do I craft Twilight?', 'Plan for Aurene's Bite', 'I want 2 Legendary Sigils', 'Craft The Moot').\n"
        "   - 'SESSION_ITINERARY': Select this when the player asks for a daily session schedule, playtime routine, or time-budgeted itinerary (e.g., 'What should I do tonight in 90 mins?', 'Plan my daily session for 60 minutes', 'Session itinerary for Twilight', 'Daily knapsack routine').\n"
        "   - 'ARBITRAGE_EVALUATION': Select this when the player asks whether to buy vs craft an item, asks about market arbitrage, or asks if it is cheaper to buy or profitable to craft (e.g., 'Should I craft or buy Twilight?', 'Buy vs craft Dusk', 'Is it cheaper to buy or craft?', 'Arbitrage evaluation for The Moot').\n"
        "   - 'PREREQUISITE_AUDIT': Select this when the player asks to check prerequisites, mastery requirements, crafting readiness, or precursor collections (e.g., 'Check my masteries for Nevermore', 'Am I ready to craft Twilight?', 'Check prerequisites for Bolt', 'Can I craft Aurene's Bite?').\n"
        "   - 'CURRENCY_OPPORTUNITY_COST': Select this when the player asks about the best use of a currency or material, opportunity cost, or comparative conversion value (e.g., 'Best use of my Astral Acclaim', 'Opportunity cost of Mystic Clovers', 'Spend Astral Acclaim', 'Clovers or gold?').\n"
        "   - 'ACQUISITION_DISCOVERY': Select this when the player is asking how to farm, collect, or acquire materials/currencies.\n"
        "   - 'EXPLORATORY_DISCOVERY': Select this when the player wants to browse or find items with specific attributes.\n\n"
        "2. target_item_name: Name of the specific item or target if mentioned, else null.\n"
        "3. currency_name: Name of currency or liquid material mentioned (e.g. 'Astral Acclaim', 'Mystic Clover', 'Spirit Shard', 'Laurel'), else null.\n"
        "4. category_filter: Any mentioned generation ('Gen 1', 'Gen 2', 'Gen 3'), expansion, or category, else null.\n"
        "5. prefer_speed: Set to true if the player wants a fast/quick recommendation, least effort, or lowest time investment, else false.\n"
        "6. wizards_vault_exhausted: Set to true if Wizard's Vault clovers or starter kit are bought, exhausted, or completed.\n"
        "7. optimization_target: Set to 'cheapest_gold' if user asks for cheapest route or if vault is exhausted.\n"
        "8. target_quantity, time_budget_minutes, excluded_game_modes, preferred_game_modes, exhausted_sources, liquid_gold_budget."
    )

    def __init__(self, semantic_query_service: SemanticQueryService, llm_client: Optional[BaseLLMClient] = None):
        self.semantic_service = semantic_query_service
        self.llm = llm_client or get_default_llm_client()

    def parse_intent(
        self,
        user_prompt: str,
        previous_goal: Optional[ResolvedGoal] = None,
        conversation_context: Optional[str] = None
    ) -> ResolvedGoal:
        """Parses player natural language prompt and resolves goal to Knowledge Graph entities or ranking facets."""
        full_prompt = user_prompt
        if conversation_context:
            full_prompt = f"Previous conversation context:\n{conversation_context}\n\nNew user message:\n{user_prompt}"

        # 1. Top LLM structured extraction
        intent: PlayerGoalIntent = self.llm.generate_structured(
            prompt=full_prompt,
            system_prompt=self.SYSTEM_PROMPT,
            schema=PlayerGoalIntent
        )

        p_lower = user_prompt.lower()
        c_lower = (conversation_context or "").lower()
        combined_text = f"{p_lower} {c_lower}"

        vault_exhausted = (
            intent.wizards_vault_exhausted
            or "WizardVault" in intent.exhausted_sources
            or ("vault" in combined_text and any(k in combined_text for k in ["bought", "exhausted", "completed", "claimed", "done", "finished"]))
            or "already bought" in combined_text
        )

        is_cheapest = (
            intent.optimization_target == "cheapest_gold"
            or intent.prefer_cheap
            or any(k in combined_text for k in ["cheapest", "cheapest route", "cheapest path", "lowest cost", "cheapest gold", "minimum gold", "save gold", "cheapest cost"])
        )

        opt_target = "cheapest_gold" if (is_cheapest or vault_exhausted or intent.optimization_target == "cheapest_gold") else intent.optimization_target
        if is_cheapest or vault_exhausted:
            intent.wizards_vault_exhausted = vault_exhausted or is_cheapest
            intent.optimization_target = opt_target

        # Heuristic classification fallback if LLM defaulted to SPECIFIC_ITEM (evaluated on current prompt)
        is_arbitrage = any(k in p_lower for k in [
            "buy vs craft", "craft or buy", "arbitrage", "cheaper to buy",
            "profitable to craft", "craft vs buy", "buy or craft",
            "cheaper to craft", "should i craft or buy", "should i buy or craft"
        ])
        is_prerequisite = any(k in p_lower for k in [
            "prerequisite", "prerequisites", "mastery", "masteries",
            "am i ready", "can i craft", "collection unlocked", "ready to craft"
        ])
        is_opportunity_cost = any(k in p_lower for k in [
            "best use of", "opportunity cost", "spend astral acclaim",
            "clovers or gold", "clover or gold", "how should i spend",
            "where should i spend", "spend my laurels", "best way to spend"
        ])
        is_session = any(k in p_lower for k in [
            "session", "itinerary", "routine", "playtime", "knapsack", "schedule"
        ]) or any(k in p_lower for k in [
            "what should i do tonight", "what to do tonight", "what can i do tonight",
            "what should i do in", "what to do in"
        ]) or ("what should i do" in p_lower and any(t in p_lower for t in ["tonight", "today", "mins", "minutes", "hour"]))

        if intent.goal_type == GoalType.SPECIFIC_ITEM:
            if is_arbitrage:
                intent.goal_type = GoalType.ARBITRAGE_EVALUATION
            elif is_prerequisite:
                intent.goal_type = GoalType.PREREQUISITE_AUDIT
            elif is_opportunity_cost:
                intent.goal_type = GoalType.CURRENCY_OPPORTUNITY_COST
            elif is_session:
                intent.goal_type = GoalType.SESSION_ITINERARY

        # Handle SESSION_ITINERARY queries
        if intent.goal_type == GoalType.SESSION_ITINERARY:
            item_query = intent.target_item_name
            resolved_item_id = None
            resolved_item_name = None
            chat_code = None
            if item_query:
                resolved_entities = self.semantic_service.resolve_entity_by_text(item_query)
                if resolved_entities:
                    top_match = resolved_entities[0]
                    resolved_item_id = top_match.get("gw2Id")
                    resolved_item_name = top_match.get("label", item_query)
                    chat_code = top_match.get("chatCode")
            elif previous_goal and previous_goal.resolved_item_id:
                resolved_item_id = previous_goal.resolved_item_id
                resolved_item_name = previous_goal.resolved_item_name
                chat_code = previous_goal.chat_code
            if resolved_item_id is None:
                resolved_item_id = 30704
                resolved_item_name = "Twilight"

            return ResolvedGoal(
                intent=intent,
                goal_type=GoalType.SESSION_ITINERARY,
                resolved_item_id=resolved_item_id,
                resolved_item_name=resolved_item_name,
                chat_code=chat_code,
                time_budget_minutes=intent.time_budget_minutes,
                target_quantity=intent.target_quantity
            )

        # Handle ARBITRAGE_EVALUATION queries
        if intent.goal_type == GoalType.ARBITRAGE_EVALUATION:
            item_query = intent.target_item_name or user_prompt
            resolved_entities = self.semantic_service.resolve_entity_by_text(item_query)
            resolved_item_id = None
            resolved_item_name = None
            chat_code = None
            if resolved_entities:
                top_match = resolved_entities[0]
                resolved_item_id = top_match.get("gw2Id")
                resolved_item_name = top_match.get("label", item_query)
                chat_code = top_match.get("chatCode")
            elif previous_goal and previous_goal.resolved_item_id:
                resolved_item_id = previous_goal.resolved_item_id
                resolved_item_name = previous_goal.resolved_item_name
                chat_code = previous_goal.chat_code
            else:
                resolved_item_id = 30704
                resolved_item_name = "Twilight"

            return ResolvedGoal(
                intent=intent,
                goal_type=GoalType.ARBITRAGE_EVALUATION,
                resolved_item_id=resolved_item_id,
                resolved_item_name=resolved_item_name,
                chat_code=chat_code,
                target_quantity=intent.target_quantity
            )

        # Handle PREREQUISITE_AUDIT queries
        if intent.goal_type == GoalType.PREREQUISITE_AUDIT:
            item_query = intent.target_item_name or user_prompt
            resolved_entities = self.semantic_service.resolve_entity_by_text(item_query)
            resolved_item_id = None
            resolved_item_name = None
            chat_code = None
            if resolved_entities:
                top_match = resolved_entities[0]
                resolved_item_id = top_match.get("gw2Id")
                resolved_item_name = top_match.get("label", item_query)
                chat_code = top_match.get("chatCode")
            elif previous_goal and previous_goal.resolved_item_id:
                resolved_item_id = previous_goal.resolved_item_id
                resolved_item_name = previous_goal.resolved_item_name
                chat_code = previous_goal.chat_code
            else:
                resolved_item_id = 30704
                resolved_item_name = "Twilight"

            return ResolvedGoal(
                intent=intent,
                goal_type=GoalType.PREREQUISITE_AUDIT,
                resolved_item_id=resolved_item_id,
                resolved_item_name=resolved_item_name,
                chat_code=chat_code,
                target_quantity=intent.target_quantity
            )

        # Handle CURRENCY_OPPORTUNITY_COST queries
        if intent.goal_type == GoalType.CURRENCY_OPPORTUNITY_COST:
            curr_query = intent.currency_name or intent.target_item_name or user_prompt
            resolved_entities = self.semantic_service.resolve_entity_by_text(curr_query)
            curr_id = intent.currency_id
            curr_name = intent.currency_name
            chat_code = None
            if resolved_entities:
                top_match = resolved_entities[0]
                curr_id = curr_id or top_match.get("gw2Id")
                curr_name = curr_name or top_match.get("label")
                chat_code = top_match.get("chatCode")
            if curr_id is None:
                if "astral" in combined_text:
                    curr_id = 68
                    curr_name = "Astral Acclaim"
                elif "clover" in combined_text:
                    curr_id = 19675
                    curr_name = "Mystic Clover"
                elif "ecto" in combined_text:
                    curr_id = 19721
                    curr_name = "Glob of Ectoplasm"
                else:
                    curr_id = 68
                    curr_name = "Astral Acclaim"

            return ResolvedGoal(
                intent=intent,
                goal_type=GoalType.CURRENCY_OPPORTUNITY_COST,
                resolved_item_id=curr_id,
                resolved_item_name=curr_name,
                currency_id=curr_id,
                currency_name=curr_name,
                chat_code=chat_code,
                target_quantity=intent.target_quantity
            )

        # Handle COMPARATIVE_RANKING queries directly without guessing specific item IDs
        if intent.goal_type == GoalType.COMPARATIVE_RANKING:
            return ResolvedGoal(
                intent=intent,
                goal_type=GoalType.COMPARATIVE_RANKING,
                category_filter=intent.category_filter,
                prefer_speed=intent.prefer_speed,
                prefer_cheap=intent.prefer_cheap or is_cheapest,
                wizards_vault_exhausted=intent.wizards_vault_exhausted,
                optimization_target=intent.optimization_target,
                target_quantity=intent.target_quantity
            )

        # Handle SPECIFIC_ITEM resolution
        item_query = intent.target_item_name
        is_referencing_previous = (
            previous_goal is not None and (
                not item_query
                or item_query.lower() in ["it", "that", "this", "upgrade", "weapon", "sigil", "legendary sigil", "legendary rune"]
                or (previous_goal.resolved_item_name and item_query.lower() == previous_goal.resolved_item_name.lower())
                or (previous_goal.resolved_item_name and any(w in item_query.lower() for w in ["upgrade", "sigil", "weapon"]))
            )
        )
        if is_referencing_previous:
            resolved_item_id = previous_goal.resolved_item_id
            resolved_item_name = previous_goal.resolved_item_name
            chat_code = previous_goal.chat_code
            target_quantity = intent.target_quantity if intent.target_quantity > 1 else previous_goal.target_quantity
        else:
            resolved_entities = self.semantic_service.resolve_entity_by_text(item_query or user_prompt)
            if resolved_entities:
                top_match = resolved_entities[0]
                resolved_item_id = top_match.get("gw2Id")
                resolved_item_name = top_match.get("label", item_query)
                chat_code = top_match.get("chatCode")
            else:
                if previous_goal and previous_goal.resolved_item_id:
                    resolved_item_id = previous_goal.resolved_item_id
                    resolved_item_name = previous_goal.resolved_item_name
                    chat_code = previous_goal.chat_code
                else:
                    # Fallback to comparative ranking if entity is unrecognized or broad category
                    return ResolvedGoal(
                        intent=intent,
                        goal_type=GoalType.COMPARATIVE_RANKING,
                        category_filter=intent.category_filter or item_query,
                        prefer_cheap=intent.prefer_cheap or is_cheapest,
                        wizards_vault_exhausted=intent.wizards_vault_exhausted,
                        optimization_target=intent.optimization_target,
                        target_quantity=intent.target_quantity
                    )
            target_quantity = intent.target_quantity

        return ResolvedGoal(
            intent=intent,
            goal_type=intent.goal_type,
            resolved_item_id=resolved_item_id,
            resolved_item_name=resolved_item_name,
            category_filter=intent.category_filter,
            is_acquisition_query=intent.is_acquisition_query or intent.goal_type == GoalType.ACQUISITION_DISCOVERY,
            facet_name=intent.facet_name,
            prefer_speed=intent.prefer_speed,
            prefer_cheap=intent.prefer_cheap or is_cheapest,
            wizards_vault_exhausted=intent.wizards_vault_exhausted,
            optimization_target=intent.optimization_target,
            target_quantity=target_quantity,
            chat_code=chat_code
        )
