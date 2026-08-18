"""Neuro-Symbolic Sandwich Orchestrator for Project Priory.

Glues together:
1. Top LLM (IntentParser): Freeform Natural Language -> Structured Constraints & Goal with Session Memory
2. Symbolic Layer:
   - SemanticQueryService: Knowledge Graph reasoning & SKOS subsumption
   - AccountDiffEngine: Deterministic Graph Math & Delta Pruning
   - PathSolver: Multi-Criteria Gold/Time/Route Optimization with Exhausted Sources
3. Bottom LLM (GuideGenerator): Synthesizes grounded, actionable player guides with Waypoint navigation
"""

from __future__ import annotations
from typing import Optional, Dict, List, Any
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine, AccountState, AccountDiffReport
from engine.path_solver import PathSolver, OptimalCraftingPlan
from engine.semantic_query import SemanticQueryService
from engine.account_ranker import AccountRanker
from agent.llm_client import BaseLLMClient, get_default_llm_client
from agent.intent_parser import IntentParser, ResolvedGoal
from agent.guide_generator import GuideGenerator, PersonalizedGuide


class PrioryChatSession:
    """Stateful multi-turn conversation session."""

    def __init__(
        self,
        orchestrator: PrioryAgentOrchestrator,
        account_state: Optional[AccountState] = None
    ):
        self.orchestrator = orchestrator
        self.account_state = account_state or AccountState()
        self.last_goal: Optional[ResolvedGoal] = None
        self.history: List[Dict[str, str]] = []

    def send_message(
        self,
        user_prompt: str,
        live_tp_prices: Optional[Dict[int, float]] = None
    ) -> PersonalizedGuide:
        """Processes a follow-up user prompt with multi-turn session awareness."""
        # 1. Format conversation context
        context_str = None
        if self.history:
            context_str = "\n".join([f"{h['role']}: {h['content']}" for h in self.history[-4:]])

        # 2. Top LLM parses intent with previous goal memory
        from agent.intent_parser import GoalType
        resolved_goal: ResolvedGoal = self.orchestrator.intent_parser.parse_intent(
            user_prompt=user_prompt,
            previous_goal=self.last_goal,
            conversation_context=context_str
        )
        self.last_goal = resolved_goal

        # 3. Dynamic routing based on Top LLM's semantic GoalType classification
        if resolved_goal.goal_type == GoalType.COMPARATIVE_RANKING:
            is_speed = any(w in user_prompt.lower() for w in ["quick", "fast", "speed", "least effort", "instant", "soon"])

            requested_n = resolved_goal.target_quantity if resolved_goal.target_quantity > 1 else 5

            rankings = self.orchestrator.ranker.rank_all_legendaries(
                account=self.account_state,
                tp_prices=live_tp_prices,
                top_n=max(requested_n, 5),
                filter_query=resolved_goal.category_filter,
                prefer_speed=resolved_goal.prefer_speed
            )
            top_optimal_plan = None
            if rankings:
                top_diff = self.orchestrator.diff_engine.compute_diff(
                    goal_item_id=rankings[0].gw2_id,
                    account=self.account_state
                )
                top_optimal_plan = self.orchestrator.solver.solve_optimal_path(
                    diff_report=top_diff,
                    account=self.account_state,
                    tp_prices=live_tp_prices,
                    excluded_modes=resolved_goal.intent.excluded_game_modes,
                    exhausted_sources=resolved_goal.intent.exhausted_sources,
                    time_budget_minutes=resolved_goal.intent.time_budget_minutes
                )
            guide: PersonalizedGuide = self.orchestrator.guide_generator.generate_ranking_guide(
                rankings=rankings,
                user_prompt=user_prompt,
                time_budget_minutes=resolved_goal.intent.time_budget_minutes,
                optimal_plan=top_optimal_plan,
                target_quantity=resolved_goal.target_quantity
            )
            self.history.append({"role": "user", "content": user_prompt})
            self.history.append({"role": "assistant", "content": guide.executive_summary})
            return guide

        # 2. Deterministic Account Delta
        diff_report = self.orchestrator.diff_engine.compute_diff(
            goal_item_id=resolved_goal.resolved_item_id,
            account=self.account_state,
            target_quantity=resolved_goal.target_quantity
        )

        # 3. Path Solver Optimization (respecting exhausted sources and time budgets)
        optimal_plan = self.orchestrator.solver.solve_optimal_path(
            diff_report=diff_report,
            account=self.account_state,
            tp_prices=live_tp_prices,
            excluded_modes=resolved_goal.intent.excluded_game_modes,
            exhausted_sources=resolved_goal.intent.exhausted_sources,
            time_budget_minutes=resolved_goal.intent.time_budget_minutes
        )

        # 4. Semantic Subgraph Context Extraction
        semantic_context = self.orchestrator.semantic_service.get_item_semantic_context_for_llm(resolved_goal.resolved_item_id)

        # 5. Bottom LLM Guide Synthesis
        guide: PersonalizedGuide = self.orchestrator.guide_generator.generate_guide(
            goal=resolved_goal,
            diff_report=diff_report,
            semantic_context=semantic_context,
            optimal_plan=optimal_plan
        )

        # Save to history
        self.history.append({"role": "user", "content": user_prompt})
        self.history.append({"role": "assistant", "content": guide.executive_summary})

        return guide


class PrioryAgentOrchestrator:
    """The central Neuro-Symbolic Sandwich pipeline."""

    def __init__(
        self,
        graph_store: Optional[PrioryGraphStore] = None,
        llm_client: Optional[BaseLLMClient] = None
    ):
        self.store = graph_store or PrioryGraphStore()
        self.store.load_all()

        self.semantic_service = SemanticQueryService(self.store)
        self.diff_engine = AccountDiffEngine(self.store)
        self.ranker = AccountRanker(self.store, self.diff_engine)
        self.solver = PathSolver(self.store)
        self.llm = llm_client or get_default_llm_client()

        self.intent_parser = IntentParser(self.semantic_service, self.llm)
        self.guide_generator = GuideGenerator(self.llm)

    def create_session(self, account_state: Optional[AccountState] = None) -> PrioryChatSession:
        """Creates a stateful multi-turn chat session."""
        return PrioryChatSession(self, account_state)

    def run_pipeline(
        self,
        user_prompt: str,
        account_state: Optional[AccountState] = None,
        live_tp_prices: Optional[Dict[int, float]] = None
    ) -> PersonalizedGuide:
        """Executes a one-shot pipeline execution."""
        session = self.create_session(account_state)
        return session.send_message(user_prompt, live_tp_prices)
