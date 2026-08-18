"""Unit tests for Longitudinal Calendar Completion Projector in PathSolver."""

import unittest
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine, AccountState
from engine.path_solver import PathSolver


class TestCalendarProjector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(cls.store)
        cls.solver = PathSolver(cls.store)

    def test_daily_ascended_calendar_projection(self):
        """Verifies that missing 50 Provisioner Tokens projects 17 calendar days and a valid target date."""
        account = AccountState(
            materials={19721: 100}
        )
        report = self.diff_engine.compute_diff(goal_item_id=91505, account=account)  # Legendary Sigil (50 Provisioner Tokens)
        plan = self.solver.solve_optimal_path(diff_report=report, account=account)

        self.assertGreater(plan.estimated_completion_days, 0)
        self.assertEqual(plan.estimated_completion_days, 17)
        self.assertIsNotNone(plan.estimated_completion_date)
        self.assertIn("Provisioner Tokens", plan.primary_time_gate_bottleneck)


if __name__ == "__main__":
    unittest.main()
