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
    EXPLORATORY_DISCOVERY = "EXPLORATORY_DISCOVERY" # Exploratory search across the knowledge graph


class PlayerGoalIntent(BaseModel):
    """Structured intent and constraint parameters extracted from natural language by the Top LLM."""
    goal_type: GoalType = Field(
        default=GoalType.SPECIFIC_ITEM,
        description="The primary nature of the player's request: SPECIFIC_ITEM (if targeting a concrete named item), COMPARATIVE_RANKING (if asking what they are closest to, how far they are from a category/generation, seeking recommendations, or requesting a leaderboard), or EXPLORATORY_DISCOVERY."
    )
    target_item_name: Optional[str] = Field(
        default=None,
        description="The specific item name if the player specified one (e.g. 'Twilight', 'Aurene's Bite', 'The Moot', 'Legendary Sigil'). None if asking about a category/generation."
    )
    category_filter: Optional[str] = Field(
        default=None,
        description="Generation, expansion, slot, or weapon type facet if mentioned (e.g. 'Gen 1', 'Gen 2', 'Gen 3', 'Core', 'Heart of Thorns', 'Path of Fire', 'End of Dragons', 'Secrets of the Obscure', 'Janthir Wilds', 'Armor', 'Trinket', 'Upgrade', 'Spear', 'Greatsword')."
    )
    prefer_speed: bool = Field(
        default=False,
        description="Set to true if the player explicitly asks to craft quickly, fast, with least effort, or minimal time investment."
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
    category_filter: Optional[str] = None
    prefer_speed: bool = False
    target_quantity: int = 1
    chat_code: Optional[str] = None


class IntentParser:
    """Parses player prompt into structured intent and links it to Knowledge Graph entities."""

    SYSTEM_PROMPT = (
        "You are an expert Guild Wars 2 goal analysis and intent parsing agent for Project Priory.\n"
        "Your role is to understand the player's objective and classify it into structured parameters:\n\n"
        "1. goal_type:\n"
        "   - 'COMPARATIVE_RANKING': Select this whenever the player asks what they are closest to, how far/close they are from a generation/expansion/category, asks for recommendations, asks what to craft next, or asks about progress without naming a single specific item (e.g., 'How far am I to a Generation 3 legendary?', 'What legendary can I craft?', 'Which gen 2 am I closest to?', 'Where do I stand on legendary armor?').\n"
        "   - 'SPECIFIC_ITEM': Select this when the player targets a specific, concrete item (e.g., 'How do I craft Twilight?', 'Plan for Aurene's Bite', 'I want 2 Legendary Sigils', 'Craft The Moot').\n"
        "   - 'EXPLORATORY_DISCOVERY': Select this when the player wants to browse or find items with specific attributes.\n\n"
        "2. target_item_name: Name of the specific item if goal_type is SPECIFIC_ITEM, else null.\n"
        "3. category_filter: Any mentioned generation ('Gen 1', 'Gen 2', 'Gen 3'), expansion ('Heart of Thorns', 'Path of Fire', 'End of Dragons', 'Secrets of the Obscure', 'Janthir Wilds'), or category ('Armor', 'Trinket', 'Upgrade', 'Spear', 'Greatsword'), else null.\n"
        "4. prefer_speed: Set to true if the player wants a fast/quick recommendation, least effort, or lowest time investment (e.g. 'quickly', 'fast', 'fastest', 'least effort'), else false.\n"
        "5. target_quantity, time_budget_minutes, excluded_game_modes, preferred_game_modes, exhausted_sources, liquid_gold_budget."
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

        # Handle COMPARATIVE_RANKING queries directly without guessing specific item IDs
        if intent.goal_type == GoalType.COMPARATIVE_RANKING:
            return ResolvedGoal(
                intent=intent,
                goal_type=GoalType.COMPARATIVE_RANKING,
                category_filter=intent.category_filter,
                prefer_speed=intent.prefer_speed,
                target_quantity=intent.target_quantity
            )

        # Handle SPECIFIC_ITEM resolution
        item_query = intent.target_item_name
        if previous_goal and (not item_query or item_query.lower() in ["it", "that", "this", "upgrade", "weapon", "sigil"]):
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
                        target_quantity=intent.target_quantity
                    )
            target_quantity = intent.target_quantity

        return ResolvedGoal(
            intent=intent,
            goal_type=GoalType.SPECIFIC_ITEM,
            resolved_item_id=resolved_item_id,
            resolved_item_name=resolved_item_name,
            target_quantity=target_quantity,
            chat_code=chat_code
        )
