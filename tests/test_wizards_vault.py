"""Unit tests for Wizard's Vault shop listing ingestion and sold-out detection."""

import unittest
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine, AccountState, WizardVaultListing
from engine.path_solver import PathSolver


class TestWizardsVault(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(cls.store)
        cls.solver = PathSolver(cls.store)

    def test_wizards_vault_listing_properties(self):
        """Verifies remaining purchases and is_sold_out properties."""
        available_listing = WizardVaultListing(
            id=22, item_id=19675, cost=9, purchased=5, purchase_limit=20
        )
        self.assertEqual(available_listing.remaining_purchases, 15)
        self.assertFalse(available_listing.is_sold_out)

        sold_out_listing = WizardVaultListing(
            id=22, item_id=19675, cost=9, purchased=20, purchase_limit=20
        )
        self.assertEqual(sold_out_listing.remaining_purchases, 0)
        self.assertTrue(sold_out_listing.is_sold_out)

    def test_account_state_wizards_vault_helpers(self):
        """Verifies AccountState lookup methods for Wizard's Vault items."""
        account = AccountState(
            wizards_vault_listings={
                19675: WizardVaultListing(id=22, item_id=19675, cost=9, purchased=20, purchase_limit=20)
            }
        )
        self.assertTrue(account.is_wizards_vault_sold_out(19675))
        self.assertEqual(account.wizards_vault_remaining(19675), 0)
        self.assertFalse(account.is_wizards_vault_sold_out(99999))
        self.assertIsNone(account.wizards_vault_remaining(99999))

    def test_solver_fallback_when_vault_clovers_sold_out(self):
        """Verifies that PathSolver skips Wizard's Vault when clovers are sold out and recommends Fractals/Forge."""
        # Account with 20/20 Clovers purchased (sold out)
        account = AccountState(
            materials={19721: 100},
            wallet={68: 500},  # 500 Astral Acclaim
            wizards_vault_listings={
                19675: WizardVaultListing(id=22, item_id=19675, cost=9, purchased=20, purchase_limit=20)
            }
        )
        report = self.diff_engine.compute_diff(goal_item_id=30704, account=account)  # Twilight
        plan = self.solver.solve_optimal_path(diff_report=report, account=account)

        # Wizard's Vault shouldn't be the recommended clover strategy since it's sold out
        vault_clover_strat = next((c for c in plan.clover_strategy if "Wizard" in c.source_name), None)
        self.assertIsNone(vault_clover_strat)

        # BUY-2046 Fractal should be recommended instead
        fractal_strat = next((c for c in plan.clover_strategy if "Fractal" in c.source_name), None)
        self.assertIsNotNone(fractal_strat)
        self.assertTrue(fractal_strat.recommended)

        # T6 strat should mention Clovers are sold out
        t6_text = " ".join(plan.t6_strategies)
        self.assertIn("sold out", t6_text)


if __name__ == "__main__":
    unittest.main()
