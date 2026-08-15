"""Top LLM: Natural Language Intent & Constraint Parser for Project Priory.

Translates freeform player prompts into structured goal objects, constraints,
and resolves entity names to canonical Knowledge Graph URIs with multi-turn session awareness.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from agent.llm_client import BaseLLMClient, get_default_llm_client
from engine.semantic_query import SemanticQueryService


class PlayerGoalIntent(BaseModel):
    """Structured intent and constraint parameters extracted from natural language."""
    goal_item_query: str = Field(description="The primary item, weapon, or sigil the player wishes to craft or obtain.")
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
    resolved_item_id: int
    resolved_item_name: str
    target_quantity: int = 1
    chat_code: Optional[str] = None


class IntentParser:
    """Parses player prompt into structured intent and links it to Knowledge Graph entities."""

    SYSTEM_PROMPT = (
        "You are an expert Guild Wars 2 goal analysis agent. "
        "Extract the player's primary crafting or acquisition goal, desired quantity (e.g. 1 or 2), time availability, "
        "game mode preferences/exclusions, budget, and any completed/exhausted sources (e.g. 'WizardVault' if they already bought vault clovers) from their message."
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
        """Parses player natural language prompt and resolves goal to a Knowledge Graph item."""
        full_prompt = user_prompt
        if conversation_context:
            full_prompt = f"Previous conversation context:\n{conversation_context}\n\nNew user message:\n{user_prompt}"

        # 1. Top LLM structured extraction
        intent: PlayerGoalIntent = self.llm.generate_structured(
            prompt=full_prompt,
            system_prompt=self.SYSTEM_PROMPT,
            schema=PlayerGoalIntent
        )

        # Retain previous target goal in follow-up queries if not explicitly changed
        goal_query = intent.goal_item_query
        if previous_goal and (not goal_query or goal_query.lower() in ["it", "that", "this", "upgrade", "weapon", "sigil"]):
            resolved_item_id = previous_goal.resolved_item_id
            resolved_item_name = previous_goal.resolved_item_name
            chat_code = previous_goal.chat_code
            target_quantity = intent.target_quantity if intent.target_quantity > 1 else previous_goal.target_quantity
        else:
            # 2. Semantic entity resolution in Knowledge Graph
            resolved_entities = self.semantic_service.resolve_entity_by_text(goal_query)
            if not resolved_entities:
                if previous_goal:
                    resolved_item_id = previous_goal.resolved_item_id
                    resolved_item_name = previous_goal.resolved_item_name
                    chat_code = previous_goal.chat_code
                else:
                    resolved_item_id = 30699 # Twilight
                    resolved_item_name = "Twilight"
                    chat_code = "[&AgErZgAA]"
            else:
                top_match = resolved_entities[0]
                resolved_item_id = top_match.get("gw2Id", 30699)
                resolved_item_name = top_match.get("label", intent.goal_item_query)
                chat_code = top_match.get("chatCode")
            target_quantity = intent.target_quantity

        return ResolvedGoal(
            intent=intent,
            resolved_item_id=resolved_item_id,
            resolved_item_name=resolved_item_name,
            target_quantity=target_quantity,
            chat_code=chat_code
        )
