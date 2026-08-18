"""Unit tests for Gen 3 Elder Dragon Skin Variants."""

import unittest
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine, AccountState


class TestGen3DragonVariants(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(cls.store)

    def test_zhaitan_variant_facet_and_recipe(self):
        """Verifies that Aurene's Bite (Zhaitan Variant) is modeled with Zhaitan facet and Mystic Forge recipe."""
        q = """
        SELECT ?facet ?recipe WHERE {
            ?variant <https://priory.gw2/def/gw2Id> 96001 ;
                     <https://priory.gw2/def/hasDragonFacet> ?facet ;
                     <https://priory.gw2/def/producedBy> ?recipe .
        }
        """
        res = self.store.query(q)
        self.assertEqual(len(res), 1)
        self.assertIn("ZhaitanFacet", str(res[0]["facet"]))
        self.assertIn("Recipe_AureneBite_Zhaitan", str(res[0]["recipe"]))

    def test_zhaitan_variant_diff(self):
        """Verifies that Aurene's Bite (Zhaitan Variant) computes diff with Memories of Aurene and Dragonite Ingots."""
        account = AccountState(
            materials={96221: 1}  # Base Aurene's Bite (96221) owned
        )
        report = self.diff_engine.compute_diff(goal_item_id=96001, account=account)
        self.assertEqual(report.goal_item_name, "Aurene's Bite (Zhaitan Variant)")
        self.assertFalse(report.is_fully_satisfied)
        self.assertIn("Memory of Aurene", report.summary_missing_materials)
        self.assertEqual(report.summary_missing_materials["Memory of Aurene"], 100)


if __name__ == "__main__":
    unittest.main()
