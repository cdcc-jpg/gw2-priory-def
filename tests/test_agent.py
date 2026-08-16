"""Unit tests for the Neuro-Symbolic Agent layer."""

import unittest
from pathlib import Path
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState, AccountDiffEngine
from agent.orchestrator import PrioryAgentOrchestrator
from agent.intent_parser import IntentParser
from agent.llm_client import RuleBasedMockLLMClient
from engine.semantic_query import SemanticQueryService


class TestAgentPipeline(unittest.TestCase):

    def setUp(self):
        self.store = PrioryGraphStore()
        self.store.load_all()
        self.mock_llm = RuleBasedMockLLMClient()
        self.orchestrator = PrioryAgentOrchestrator(
            graph_store=self.store,
            llm_client=self.mock_llm
        )

    def test_intent_parsing(self):
        """Verifies parsing a player prompt into structured constraints."""
        service = SemanticQueryService(self.store)
        parser = IntentParser(service, self.mock_llm)

        prompt = "I want to craft Twilight tonight. I have 3 hours, but I hate WvW and have 400g."
        resolved_goal = parser.parse_intent(prompt)

        self.assertEqual(resolved_goal.resolved_item_name, "Twilight")
        self.assertEqual(resolved_goal.resolved_item_id, 30704)
        self.assertEqual(resolved_goal.intent.time_budget_minutes, 180)
        self.assertIn("WvW", resolved_goal.intent.excluded_game_modes)
        self.assertEqual(resolved_goal.intent.liquid_gold_budget, 400)

    def test_legendary_sigil_quantity_scaling_with_wallet_tokens(self):
        """Verifies parsing and scaling requirements for '2 Legendary Sigils' with owned Provisioner Tokens."""
        service = SemanticQueryService(self.store)
        parser = IntentParser(service, self.mock_llm)

        prompt = "I want to craft 2 legendary sigils tonight. I have 90 mins."
        resolved_goal = parser.parse_intent(prompt)

        self.assertEqual(resolved_goal.resolved_item_name, "Legendary Sigil")
        self.assertEqual(resolved_goal.resolved_item_id, 91505)
        self.assertEqual(resolved_goal.target_quantity, 2)

        # Player owns 20 Clovers (needs 30 * 2 = 60) and 440 Provisioner Tokens in wallet (needs 100)
        player_account = AccountState(
            materials={19675: 20},
            wallet={35: 440} # 440 Provisioner Tokens owned!
        )
        diff_engine = AccountDiffEngine(self.store)
        report = diff_engine.compute_diff(91505, player_account, target_quantity=2)

        # 60 needed - 20 owned = 40 missing Clovers
        self.assertEqual(report.summary_missing_materials["Mystic Clover"], 40)
        # 10 * 75 * 2 = 1500 Lucent Crystals
        self.assertEqual(report.summary_missing_materials["Pile of Lucent Crystal"], 1500)
        # 75 * 2 = 150 of each symbol
        self.assertEqual(report.summary_missing_materials["Symbol of Control"], 150)
        # Gift of Craftsmanship is satisfied because wallet has 440 tokens (needs 100)
        self.assertNotIn("Gift of Craftsmanship", report.summary_missing_materials)

        # Full pipeline test
        guide = self.orchestrator.run_pipeline(prompt, player_account)
        # No daily provisioner task should be in the checklist
        provisioner_tasks = [s for s in guide.session_checklist if "Provisioner Barter Run" in s.title]
        self.assertEqual(len(provisioner_tasks), 0)

    def test_multi_turn_chat_session_with_vault_exhaustion(self):
        """Verifies multi-turn chat session where player notes Wizard's Vault is already completed."""
        player_account = AccountState(
            materials={19675: 20}, # 20 Clovers owned (needs 60)
            wallet={35: 440}       # 440 Provisioner tokens owned (needs 100)
        )
        session = self.orchestrator.create_session(account_state=player_account)

        # Turn 1: Prompt noting Vault clovers are already bought
        prompt = "I'm looking into crafting 2 leggy upgrades for weapons, sigils i think. I already bought the clovers from wizard vault."
        guide1 = session.send_message(prompt)

        self.assertEqual(guide1.goal_name, "Legendary Sigil")
        self.assertEqual(guide1.target_quantity, 2)
        # Should detect vault exhaustion and recommend alternative clover routes
        exhausted_rec = any("Exhausted" in r or "Fractal" in r for r in guide1.strategic_recommendations)
        self.assertTrue(exhausted_rec)

        # Turn 2: Follow-up question retaining the 2 Sigils context
        follow_up = "How much time should I spend tonight if I only have 60 mins?"
        guide2 = session.send_message(follow_up)

        self.assertEqual(guide2.goal_name, "Legendary Sigil")
        self.assertEqual(guide2.target_quantity, 2)
        self.assertGreater(len(guide2.session_checklist), 0)

    def test_orchestrator_end_to_end_sandwich(self):
        """Verifies complete Neuro-Symbolic Sandwich execution with player state diffing."""
        # Player owns Dusk in bank and 50 Clovers in material storage
        player_account = AccountState(
            materials={19675: 50}, # 50 Clovers (needs 77)
            bank={29185: 1},       # Dusk owned
            disciplines={"weaponsmith": 500}
        )

        user_prompt = "I have 2 hours to play tonight. Can you help me finish Twilight? I avoid WvW."
        guide = self.orchestrator.run_pipeline(user_prompt, player_account)

        self.assertEqual(guide.goal_name, "Twilight")
        self.assertGreater(len(guide.session_checklist), 0)

        # Strategic recommendations should reflect WvW exclusion and Clover alternatives
        wvw_rec = any("WvW" in r for r in guide.strategic_recommendations)
        self.assertTrue(wvw_rec)

        # Missing materials must reflect exact delta (27 Clovers missing, Dusk satisfied)
        self.assertEqual(guide.missing_materials_summary["Mystic Clover"], 27)
        self.assertNotIn("Dusk", guide.missing_materials_summary)


if __name__ == "__main__":
    unittest.main()
