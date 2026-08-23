"""Tests for Armory Max Caps, Achievement Prerequisites, and Mastery Tracking."""

import unittest
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState, AccountDiffEngine
from engine.path_solver import PathSolver


class TestArmoryAndPrerequisites(unittest.TestCase):
    """Verifies domain completeness rules for armory saturation, achievements, and masteries."""

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(graph_store=cls.store)
        cls.solver = PathSolver(graph_store=cls.store)

    def test_armory_saturation_sigil(self):
        """Account with 4 Legendary Sigils should be marked as saturated."""
        account = AccountState(
            legendary_armory={91505: 4}  # 4x Legendary Sigil
        )
        report = self.diff_engine.compute_diff(goal_item_id=91505, account=account, target_quantity=1)
        self.assertTrue(report.is_saturated)
        self.assertEqual(report.armory_max_cap, 4)
        self.assertEqual(report.armory_owned_count, 4)
        self.assertEqual(report.overall_readiness_pct, 100.0)

    def test_armory_not_saturated_when_under_cap(self):
        """Account with 2 Legendary Sigils should have 2 remaining capacity."""
        account = AccountState(
            legendary_armory={91505: 2}  # 2x Legendary Sigil
        )
        report = self.diff_engine.compute_diff(goal_item_id=91505, account=account, target_quantity=1)
        self.assertFalse(report.is_saturated)
        self.assertEqual(report.armory_max_cap, 4)
        self.assertEqual(report.armory_owned_count, 2)

    def test_prismatic_regalia_achievement_prerequisite(self):
        """Prismatic Champion's Regalia requires Seasons of the Dragons (ach 5900)."""
        account = AccountState(completed_achievements=set())
        report = self.diff_engine.compute_diff(goal_item_id=95380, account=account, target_quantity=1)
        self.assertTrue(any(a["id"] == 5900 for a in report.missing_achievements))

        # Account with completed achievement
        account_completed = AccountState(completed_achievements={5900})
        report_done = self.diff_engine.compute_diff(goal_item_id=95380, account=account_completed, target_quantity=1)
        self.assertFalse(any(a["id"] == 5900 for a in report_done.missing_achievements))

    def test_ad_infinitum_achievement_prerequisite(self):
        """Ad Infinitum requires Ad Infinitum IV (ach 2451)."""
        account = AccountState(completed_achievements=set())
        report = self.diff_engine.compute_diff(goal_item_id=77474, account=account, target_quantity=1)
        self.assertTrue(any(a["id"] == 2451 for a in report.missing_achievements))


if __name__ == "__main__":
    unittest.main()
