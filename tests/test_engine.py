"""Engine tests for GraphStore and AccountDiffEngine."""

import unittest
from pathlib import Path
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine, AccountState

DEF_REPO = Path(__file__).parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")


class TestEngine(unittest.TestCase):

    def setUp(self):
        self.store = PrioryGraphStore(ref_repo_path=REF_REPO, def_repo_path=DEF_REPO)
        triples_loaded = self.store.load_all()
        self.assertGreater(triples_loaded, 0)

    def test_twilight_direct_ingredients(self):
        """Verifies that Twilight has all 4 expected Gen 1 components."""
        ingredients = self.store.get_direct_recipe_ingredients(30699) # Twilight ID
        self.assertEqual(len(ingredients), 4)

        labels = {ing["ingredientLabel"] for ing in ingredients}
        self.assertIn("Dusk", labels)
        self.assertIn("Gift of Fortune", labels)
        self.assertIn("Gift of Mastery", labels)
        self.assertIn("Gift of Twilight", labels)

    def test_account_diff_engine_fresh_account(self):
        """Verifies diff report on a brand new account."""
        engine = AccountDiffEngine(self.store)
        fresh_account = AccountState()

        report = engine.compute_diff(30699, fresh_account)
        self.assertFalse(report.is_fully_satisfied)
        self.assertEqual(report.goal_item_name, "Twilight")

        # Should detect missing Weaponsmith and Armorsmith (needs 400)
        self.assertGreater(len(report.missing_disciplines), 0)
        weaponsmith_req = next((d for d in report.missing_disciplines if d["discipline"] == "weaponsmith"), None)
        self.assertIsNotNone(weaponsmith_req)
        self.assertEqual(weaponsmith_req["required_rating"], 400)

        # Should report missing leaf materials
        self.assertEqual(report.summary_missing_materials["Mystic Clover"], 77)
        self.assertEqual(report.summary_missing_materials["Glob of Ectoplasm"], 250)
        self.assertEqual(report.summary_missing_materials["Icy Runestone"], 100)
        self.assertEqual(report.summary_missing_materials["Dusk"], 1)
        self.assertEqual(report.summary_missing_materials["Mithril Ingot"], 100)
        self.assertEqual(report.summary_missing_materials["Orichalcum Ingot"], 350)
        self.assertEqual(report.summary_missing_materials["Onyx Lodestone"], 100)

    def test_account_diff_engine_partially_completed_account(self):
        """Verifies diff report on an account with owned precursor and clovers."""
        engine = AccountDiffEngine(self.store)
        account = AccountState(
            materials={
                19675: 50,  # 50 Mystic Clovers owned (needs 77)
                19721: 200, # 200 Ectoplasm owned (needs 250)
            },
            bank={
                29185: 1,   # Owns Dusk in bank!
            },
            disciplines={
                "weaponsmith": 500,
                "armorsmith": 500
            }
        )

        report = engine.compute_diff(30699, account)
        self.assertFalse(report.is_fully_satisfied)

        # Crafting discipline requirements are met!
        self.assertEqual(len(report.missing_disciplines), 0)

        # Remaining missing should be exact delta
        self.assertEqual(report.summary_missing_materials["Mystic Clover"], 27) # 77 - 50 = 27
        self.assertEqual(report.summary_missing_materials["Glob of Ectoplasm"], 50) # 250 - 200 = 50
        self.assertNotIn("Dusk", report.summary_missing_materials) # Dusk is owned!

    def test_multi_discipline_preference_selection(self):
        """Verifies that an account with Weaponsmith 500 automatically chooses Weaponsmith recipe."""
        engine = AccountDiffEngine(self.store)
        account = AccountState(
            disciplines={"weaponsmith": 500}
        )
        report = engine.compute_diff(91505, account, target_quantity=1) # Legendary Sigil (needs Mystic Motes)
        # Account has Weaponsmith 500, which satisfies Mystic Motes (requires 75)
        mote_disc_missing = [d for d in report.missing_disciplines if d["discipline"] in ["artificer", "huntsman"]]
        self.assertEqual(len(mote_disc_missing), 0)


if __name__ == "__main__":
    unittest.main()
