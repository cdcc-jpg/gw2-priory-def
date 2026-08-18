"""Unit tests for Currency-to-Material Optimization in PathSolver."""

import unittest
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine, AccountState
from engine.path_solver import PathSolver


class TestCurrencyOptimization(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(cls.store)
        cls.solver = PathSolver(cls.store)

    def test_volatile_magic_and_acclaim_recommendations(self):
        """Verifies that solver recommends Trophy Shipments when player has Volatile Magic and Astral Acclaim."""
        account = AccountState(
            materials={19721: 100},  # missing T6
            wallet={
                45: 5000,  # 5,000 Volatile Magic
                68: 500,   # 500 Astral Acclaim
                3: 50      # 50 Laurels
            }
        )
        report = self.diff_engine.compute_diff(goal_item_id=30704, account=account)  # The Moot
        plan = self.solver.solve_optimal_path(diff_report=report, account=account)

        # Check that T6 strategies contain Volatile Magic, Astral Acclaim, and Laurels
        strat_text = " ".join(plan.t6_strategies)
        self.assertIn("Volatile Magic Conversion", strat_text)
        self.assertIn("Wizard's Vault Acclaim", strat_text)
        self.assertIn("Laurel Merchant", strat_text)


if __name__ == "__main__":
    unittest.main()
