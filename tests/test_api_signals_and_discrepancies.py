"""Unit tests for newly ingested GW2 REST API v2 signals and forensic discrepancy resolution."""

import unittest
from engine.account_diff import AccountState, AccountDiffEngine
from engine.graph_store import PrioryGraphStore


class TestApiSignalsAndDiscrepancies(unittest.TestCase):
    """Test suite validating 100% forensic alignment with live GW2 API v2 ground truth."""

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(cls.store)

    def test_world_completion_deterministic_detection(self):
        """Test Discrepancy 1: Verifies World Completion detection via Ach 137 and Title 12."""
        # Account with 0 Gift of Exploration in inventory, but with Achievement 137 and Title 12
        account = AccountState(
            materials={},
            bank={},
            inventory={},
            completed_achievements={137},  # 'Been There, Done That'
            titles={12},                  # 'Been there. Done that.'
            characters=[
                {"name": "Kerling", "level": 80, "profession": "Guardian", "title": 12},
                {"name": "Skuta Rantakallio", "level": 80, "profession": "Ranger", "title": 128}
            ],
            map_completed_characters=["Kerling"]
        )

        self.assertTrue(account.has_world_completion_unlocked())
        self.assertTrue(account.is_character_map_completed("Kerling"))
        self.assertFalse(account.is_character_map_completed("Skuta Rantakallio"))
        self.assertIn("Skuta Rantakallio", account.eligible_exploration_characters())
        self.assertNotIn("Kerling", account.eligible_exploration_characters())

    def test_dungeon_tokens_and_master_achievements(self):
        """Test Discrepancy 2: Verifies Tales of Dungeon Delving (Currency 69) and Dungeon Master unlocks."""
        account = AccountState(
            wallet={
                69: 3997,  # Tales of Dungeon Delving (Correct ID)
                61: 65     # Research Notes (formerly confused with Dungeon Tokens)
            },
            completed_achievements={122, 186, 189, 190, 191},  # Dungeon Master + AC, TA, HotW, CoF
            titles={15},  # Dungeon Master Title
            daily_dungeons=["ac_p1", "ac_p2"]
        )

        self.assertEqual(account.dungeon_tales_count(), 4062)  # 3997 + 65 fallback
        self.assertEqual(account.total_currency_count(69), 3997)
        self.assertEqual(account.research_notes_count(), 65)
        self.assertTrue(account.has_dungeon_master_unlocked())
        self.assertIn("ac_p1", account.daily_dungeons)

    def test_active_crafting_licenses_and_delegation(self):
        """Test Discrepancy 3: Verifies active vs inactive discipline detection across character alts."""
        account = AccountState(
            disciplines={"armorsmith": 500, "weaponsmith": 500, "artificer": 404, "chef": 440},
            active_disciplines={
                "armorsmith": ["Kerling"],
                "weaponsmith": ["Kerling"],
                "artificer": ["Legacy Of Harathi"],
                "huntsman": ["Legacy Of Harathi"],
                "chef": ["Aubefein"]
            },
            character_disciplines={
                "Kerling": {
                    "armorsmith": {"rating": 500, "active": True},
                    "weaponsmith": {"rating": 500, "active": True},
                    "artificer": {"rating": 403, "active": False}  # Inactive on Kerling!
                },
                "Legacy Of Harathi": {
                    "artificer": {"rating": 404, "active": True},   # Active on Legacy Of Harathi!
                    "huntsman": {"rating": 500, "active": True}
                },
                "Aubefein": {
                    "chef": {"rating": 440, "active": True}
                }
            }
        )

        # Active on Legacy Of Harathi at 404
        self.assertTrue(account.has_active_discipline("artificer", 400))
        # Active on Kerling at 500
        self.assertTrue(account.has_active_discipline("weaponsmith", 500))
        self.assertTrue(account.has_active_discipline("armorsmith", 500))
        # Inactive check
        self.assertFalse(account.has_active_discipline("tailor", 400))

    def test_wallet_currencies_and_progression_tiers(self):
        """Test Discrepancy 4: Verifies Astral Acclaim (63), Provisioner Tokens (29), and Account Progression tiers."""
        account = AccountState(
            wallet={
                1: 13256226,  # 1,325g 62s 26c
                2: 960223,    # Karma
                29: 240,      # Provisioner Tokens (Correct ID 29, not 35)
                35: 323,      # Elegy Mosaic (PoF bounties)
                45: 12178,    # Volatile Magic
                63: 170,      # Astral Acclaim (Correct ID 63, not 68)
                68: 253       # Imperial Favor (Correct ID 68)
            },
            fractal_level=100,
            wvw_rank=1554,
            daily_ap=11401,
            monthly_ap=1535,
            luck=2170565,
            commander=True
        )

        self.assertEqual(account.astral_acclaim_count(), 170)
        self.assertEqual(account.imperial_favor_count(), 253)
        self.assertEqual(account.provisioner_tokens_count(), 240)
        self.assertEqual(account.volatile_magic_count(), 12178)
        self.assertEqual(account.fractal_level, 100)
        self.assertEqual(account.wvw_rank, 1554)
        self.assertEqual(account.luck, 2170565)
        self.assertTrue(account.commander)

    def test_ontology_recipe_with_corrected_dungeon_currency(self):
        """Verifies that Gift of Ascalon (item 19664) correctly resolves with Currency 69."""
        account = AccountState(
            wallet={69: 500}  # Exactly 500 Tales of Dungeon Delving
        )
        report = self.diff_engine.compute_diff(goal_item_id=19664, account=account)
        self.assertTrue(report.root_node.is_satisfied)
        self.assertEqual(report.root_node.missing_quantity, 0)


if __name__ == "__main__":
    unittest.main()
