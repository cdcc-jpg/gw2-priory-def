"""Unit tests for AccountRanker and Closest Legendary recommendation."""

import unittest
from pathlib import Path
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState
from engine.account_ranker import AccountRanker
from agent.orchestrator import PrioryAgentOrchestrator
from agent.llm_client import RuleBasedMockLLMClient

DEF_REPO = Path(__file__).parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")


class TestAccountRanker(unittest.TestCase):

    def setUp(self):
        self.store = PrioryGraphStore(ref_repo_path=REF_REPO, def_repo_path=DEF_REPO)
        self.store.load_all()
        self.ranker = AccountRanker(self.store)

    def test_bank_starter_kit_prioritization(self):
        """Verifies that an account with Legendary Starter Kit Set 2 ranks Set 2 weapons at the top."""
        # Account has Starter Kit Set 2 in bank (grants choice of Moot, Predator, Quip, Meteorlogicus)
        account = AccountState(
            bank={101123: 1}, # Starter Kit Set 2
            materials={19721: 50, 19675: 20}
        )

        rankings = self.ranker.rank_all_legendaries(account, top_n=4)
        self.assertGreater(len(rankings), 0)

        # Top 4 items must all be starter kit eligible
        for item in rankings[:4]:
            self.assertTrue(item.starter_kit_eligible)
            self.assertIn(item.name, ["The Moot", "The Predator", "Quip", "Meteorlogicus"])
            self.assertGreaterEqual(item.readiness_pct, 50.0)

    def test_orchestrator_closest_legendary_query(self):
        """Verifies that asking 'Which legendary am I closest to crafting?' returns a ranking guide."""
        mock_llm = RuleBasedMockLLMClient()
        orchestrator = PrioryAgentOrchestrator(graph_store=self.store, llm_client=mock_llm)

        account = AccountState(
            bank={101123: 1}, # Starter Kit Set 2
            materials={19721: 50}
        )

        session = orchestrator.create_session(account_state=account)
        guide = session.send_message("Which legendary am I closest to crafting?")

        self.assertIn("Closest", guide.goal_name)
        self.assertGreater(len(guide.strategic_recommendations), 0)
        self.assertTrue(any("Leaderboard" in r or "Top Recommendation" in r for r in guide.strategic_recommendations))
        self.assertGreater(len(guide.session_checklist), 0)


if __name__ == "__main__":
    unittest.main()
