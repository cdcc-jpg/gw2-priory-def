"""Unit tests for WvW & PvP Competitive Legendary Armors and Eternity."""

import unittest
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine, AccountState
from engine.path_solver import PathSolver


class TestCompetitiveArmorsAndEternity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(cls.store)
        cls.solver = PathSolver(cls.store)

    def test_eternity_diff_and_ingredients(self):
        """Verifies that Eternity recipe decomposes into Sunrise, Twilight, Crystalline Dust, and Philosopher's Stones."""
        account = AccountState(
            materials={24277: 5, 20799: 10}  # Dust and Stones owned, missing Sunrise and Twilight
        )
        report = self.diff_engine.compute_diff(goal_item_id=30689, account=account)
        self.assertEqual(report.goal_item_name, "Eternity")
        self.assertFalse(report.is_fully_satisfied)
        sub_labels = [s.label for s in report.root_node.sub_requirements]
        self.assertIn("Sunrise", sub_labels)
        self.assertIn("Twilight", sub_labels)

    def test_wvw_legendary_armor_diff(self):
        """Verifies that Triumphant Hero's Warplate computes diff with Memories of Battle and competitive gifts."""
        account = AccountState(
            materials={73248: 100}  # 100 Memories of Battle
        )
        report = self.diff_engine.compute_diff(goal_item_id=803841, account=account)
        self.assertEqual(report.goal_item_name, "Triumphant Hero's Warplate")
        self.assertFalse(report.is_fully_satisfied)
        self.assertIn("Memory of Battle", report.summary_missing_materials)

    def test_pvp_legendary_armor_diff(self):
        """Verifies that Ardent Glorious Breastplate computes diff with Ascended Shards of Glory and Star of Glory."""
        account = AccountState(
            materials={79895: 200}  # 200 Ascended Shards of Glory
        )
        report = self.diff_engine.compute_diff(goal_item_id=806121, account=account)
        self.assertEqual(report.goal_item_name, "Ardent Glorious Breastplate")
        self.assertFalse(report.is_fully_satisfied)
        self.assertIn("Ascended Shard of Glory", report.summary_missing_materials)
        self.assertEqual(report.summary_missing_materials["Ascended Shard of Glory"], 200)  # 400 - 200 owned


if __name__ == "__main__":
    unittest.main()
