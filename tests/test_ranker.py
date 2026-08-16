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
    def test_gen2_ranking(self):
        """Verifies Gen 2 ranking accounts for owned Maguuma Mastery parts and dark arts shards."""
        account = AccountState(
            bank={71943: 1, 70698: 1}, # Gift of Tarir, Gift of the Jungle
            materials={46682: 356, 68063: 126, 86120: 3} # Crystalline Ore, Amalgamated Gemstone, Shard of the Dark Arts
        )
        rankings = self.ranker.rank_all_legendaries(account, top_n=5, filter_query="Gen 2")
        self.assertGreater(len(rankings), 0)
        self.assertTrue(all("Aurene" not in item.name for item in rankings))
        # Account owns Shard of the Dark Arts -> The Binding of Ipos should be boosted
        ipos = next((r for r in rankings if r.name == "The Binding of Ipos"), None)
        self.assertIsNotNone(ipos)
        self.assertGreater(ipos.readiness_pct, 15.0)

    def test_soto_obsidian_armor_ranking(self):
        """Verifies SotO Obsidian Armor ranking accounts for essences and stardust."""
        account = AccountState(
            materials={
                100114: 500, # Essence of Despair
                100414: 250, # Essence of Greed
                100852: 250, # Pinch of Stardust
            }
        )
        rankings = self.ranker.rank_all_legendaries(account, top_n=5, filter_query="SotO")
        self.assertGreater(len(rankings), 0)
        self.assertTrue(all("Obsidian" in item.name for item in rankings))
        self.assertGreater(rankings[0].readiness_pct, 20.0)

    def test_janthir_wilds_spear_ranking(self):
        """Verifies Janthir Wilds ranking accounts for Mursaat Obsidian Chunks."""
        account = AccountState(
            materials={
                103427: 250, # Mursaat Obsidian Chunk (100% of requirement!)
                103112: 250, # Titan Ore
            }
        )
        rankings = self.ranker.rank_all_legendaries(account, top_n=3, filter_query="Janthir")
        self.assertGreater(len(rankings), 0)
        self.assertEqual(rankings[0].name, "Klobjarne Harvester")
        self.assertGreater(rankings[0].readiness_pct, 30.0)


if __name__ == "__main__":
    unittest.main()

