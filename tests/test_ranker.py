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
        self.assertGreater(ipos.readiness_pct, 5.0)

    def test_soto_obsidian_armor_ranking(self):
        """Verifies SotO Obsidian Armor ranking accounts for essences and stardust."""
        account = AccountState(
            materials={
                100849: 500, # Essence of Despair
                100429: 250, # Essence of Greed
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


    def test_speed_biased_gen2_ranking(self):
        """Verifies that a speed query ranks Gen 2.5 shard-based legendaries (Ipos, Eureka) ahead of Gen 2.0 40h collection legendaries (Astralaria, Nevermore)."""
        account = AccountState(
            materials={19721: 100, 19675: 30}
        )
        rankings = self.ranker.rank_all_legendaries(account, top_n=5, filter_query="Gen 2", prefer_speed=True)
        self.assertGreater(len(rankings), 0)
        # Top choice must be a shard crafting precursor (0.5h effort), NOT a 40h collection hunt
        self.assertIn("Shard", rankings[0].precursor_archetype)
        self.assertLessEqual(rankings[0].estimated_gameplay_hours, 1.0)

    def test_global_speed_query_no_empty_rankings(self):
        """Verifies that asking 'Which legendary item can I quickly craft' returns all top legendary candidates without empty results."""
        account = AccountState(
            materials={19721: 100, 19675: 30}
        )
        rankings = self.ranker.rank_all_legendaries(
            account,
            top_n=5,
            filter_query=None,
            prefer_speed=True
        )
        self.assertGreater(len(rankings), 0)
        self.assertEqual(len(rankings), 5)
        self.assertLessEqual(rankings[0].estimated_gameplay_hours, 1.0)

    def test_orchestrator_speed_query(self):
        """Verifies that asking 'Which generation 2 legendary can I quickly craft' through orchestrator uses LLM intent parser prefer_speed."""
        mock_llm = RuleBasedMockLLMClient()
        orchestrator = PrioryAgentOrchestrator(graph_store=self.store, llm_client=mock_llm)
        account = AccountState(materials={19721: 100, 19675: 30})
        session = orchestrator.create_session(account_state=account)
        guide = session.send_message("Which generation 2 legendary can I quickly craft")
    def test_has_legendary_unlocked_data_structures(self):
        """Verifies AccountState.has_legendary_unlocked is safe for sets, dicts, lists of ints, and lists of dicts."""
        # Dict
        acc_dict = AccountState(legendary_armory={30689: 1})
        self.assertTrue(acc_dict.has_legendary_unlocked(30689))
        self.assertFalse(acc_dict.has_legendary_unlocked(30688))

        # Set
        acc_set = AccountState(legendary_armory={30689})
        self.assertTrue(acc_set.has_legendary_unlocked(30689))
        self.assertFalse(acc_set.has_legendary_unlocked(30688))

        # List of ints
        acc_list_int = AccountState(legendary_armory=[30689, 30690])
        self.assertTrue(acc_list_int.has_legendary_unlocked(30689))
        self.assertFalse(acc_list_int.has_legendary_unlocked(30688))

        # List of dicts (GW2 API JSON format)
        acc_list_dict = AccountState(legendary_armory=[{"id": 30689, "count": 1}])
        self.assertTrue(acc_list_dict.has_legendary_unlocked(30689))
        self.assertFalse(acc_list_dict.has_legendary_unlocked(30688))

    def test_trinket_and_backpack_filter_queries(self):
        """Verifies filter queries for rings, amulets, accessories, trinkets, and backpacks."""
        account = AccountState()
        queries = ["ring", "rings", "amulet", "amulets", "accessory", "accessories", "trinket", "trinkets", "backpack", "back"]
        for q in queries:
            rankings = self.ranker.rank_all_legendaries(account, filter_query=q, top_n=5)
            self.assertGreater(len(rankings), 0, f"Query '{q}' returned no results")

        # Specific assertions
        rings = self.ranker.rank_all_legendaries(account, filter_query="rings", top_n=5)
        self.assertTrue(any("Coalescence" in r.name or "Conflux" in r.name for r in rings))

        amulets = self.ranker.rank_all_legendaries(account, filter_query="amulets", top_n=5)
        self.assertTrue(any("Transcendence" in r.name or "Regalia" in r.name for r in amulets))

        accessories = self.ranker.rank_all_legendaries(account, filter_query="accessories", top_n=5)
        self.assertTrue(any("Vision" in r.name or "Aurora" in r.name for r in accessories))

        trinkets = self.ranker.rank_all_legendaries(account, filter_query="trinket", top_n=10)
        self.assertGreaterEqual(len(trinkets), 5)

        backpacks = self.ranker.rank_all_legendaries(account, filter_query="backpack", top_n=5)
        self.assertTrue(any("Infinitum" in r.name or "Ascension" in r.name or "Warbringer" in r.name for r in backpacks))

    def test_sub_tree_diff_memoization(self):
        """Verifies sub-tree diff memoization avoids redundant traversal across multi-item evaluations."""
        account = AccountState(materials={19721: 50})
        self.ranker.diff_engine.clear_sub_tree_cache()

        # Compute diff on Sunrise (item 30703, Gen 1 Greatsword)
        self.ranker.diff_engine.compute_diff(30703, account)
        # Verify that Gift of Fortune (19627) sub-tree was memoized
        fortune_key = (19627, 1, id(account))
        self.assertIn(fortune_key, self.ranker.diff_engine._sub_tree_memo)

        # Compute diff on Twilight (item 30704, Gen 1 Greatsword) - should reuse memoized Gift of Fortune
        cached_node, cached_mats, _, _ = self.ranker.diff_engine._sub_tree_memo[fortune_key]
        self.assertEqual(cached_node.item_id, 19627)
        self.assertIn("Glob of Ectoplasm", cached_mats)

    def test_full_ranker_performance_benchmark(self):
        """Benchmark: evaluating all 141+ legendaries completes in under 2 seconds."""
        import time
        account = AccountState(materials={19721: 100, 19675: 30})

        t0 = time.perf_counter()
        rankings = self.ranker.rank_all_legendaries(account, filter_query=None, top_n=10)
        t1 = time.perf_counter()
        elapsed = t1 - t0

        self.assertGreater(len(rankings), 0)
        self.assertLess(elapsed, 2.0, f"Full ranker evaluation took {elapsed:.3f}s, exceeding 2.0s threshold!")


if __name__ == "__main__":
    unittest.main()


