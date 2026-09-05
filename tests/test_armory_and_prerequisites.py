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

    def test_world_completion_sources(self):
        """Verifies world completion sources: TITLE_12, ACHIEVEMENT_137, INVENTORY_GIFT."""
        # 1. Inventory Gift of Exploration
        account_gift = AccountState(inventory={19677: 1})
        rep_gift = self.diff_engine.verify_legendary_prerequisites(goal_item_id=30704, account_state=account_gift)
        self.assertTrue(rep_gift.has_world_completion)
        self.assertEqual(rep_gift.world_completion_source, "INVENTORY_GIFT")

        # 2. Title 12 ("Been there. Done that.")
        account_title = AccountState(titles={12})
        rep_title = self.diff_engine.verify_legendary_prerequisites(goal_item_id=30704, account_state=account_title)
        self.assertTrue(rep_title.has_world_completion)
        self.assertEqual(rep_title.world_completion_source, "TITLE_12")

        # 3. Achievement 137 ("Been There, Done That")
        account_ach = AccountState(completed_achievements={137})
        rep_ach = self.diff_engine.verify_legendary_prerequisites(goal_item_id=30704, account_state=account_ach)
        self.assertTrue(rep_ach.has_world_completion)
        self.assertEqual(rep_ach.world_completion_source, "ACHIEVEMENT_137")

        # 4. Neither present
        account_none = AccountState()
        rep_none = self.diff_engine.verify_legendary_prerequisites(goal_item_id=30704, account_state=account_none)
        self.assertFalse(rep_none.has_world_completion)
        self.assertIsNone(rep_none.world_completion_source)
        self.assertTrue(any("World Completion" in b for b in rep_none.blockers))

    def test_central_tyria_masteries_gen1_twilight(self):
        """Gen 1 (Twilight) requires Central Tyria Legendary Crafting Tier 3 (Historian of the Armaments)."""
        # Tier 0 masteries
        acc_t0 = AccountState(masteries={6: 0})
        rep_t0 = self.diff_engine.verify_legendary_prerequisites(30704, acc_t0)
        self.assertFalse(rep_t0.mastery_requirements_met)
        self.assertEqual(len(rep_t0.missing_masteries), 3)
        self.assertTrue(any("Revered Antiquarian" in m for m in rep_t0.missing_masteries))
        self.assertTrue(any("Magister of Legends" in m for m in rep_t0.missing_masteries))
        self.assertTrue(any("Historian of the Armaments" in m for m in rep_t0.missing_masteries))

        # Tier 1 masteries (Revered Antiquarian)
        acc_t1 = AccountState(masteries={6: 1})
        rep_t1 = self.diff_engine.verify_legendary_prerequisites(30704, acc_t1)
        self.assertFalse(rep_t1.mastery_requirements_met)
        self.assertEqual(len(rep_t1.missing_masteries), 2)
        self.assertTrue(any("Magister of Legends" in m for m in rep_t1.missing_masteries))
        self.assertTrue(any("Historian of the Armaments" in m for m in rep_t1.missing_masteries))

        # Tier 3 masteries (Historian of the Armaments) - Met!
        acc_t3 = AccountState(masteries={6: 3})
        rep_t3 = self.diff_engine.verify_legendary_prerequisites(30704, acc_t3)
        self.assertTrue(rep_t3.mastery_requirements_met)
        self.assertEqual(len(rep_t3.missing_masteries), 0)

        # Track 10 alias compatibility
        acc_t10 = AccountState(masteries={10: 3})
        rep_t10 = self.diff_engine.verify_legendary_prerequisites(30704, acc_t10)
        self.assertTrue(rep_t10.mastery_requirements_met)

    def test_central_tyria_masteries_gen2_nevermore(self):
        """Gen 2 (Nevermore) requires Central Tyria Legendary Crafting Tier 4 (Scholar of Secrets)."""
        acc_t3 = AccountState(masteries={6: 3, 1: 2, 2: 1, 3: 2})
        rep_t3 = self.diff_engine.verify_legendary_prerequisites(71383, acc_t3)
        self.assertFalse(rep_t3.mastery_requirements_met)
        self.assertTrue(any("Scholar of Secrets" in m for m in rep_t3.missing_masteries))

        acc_t4 = AccountState(masteries={6: 4, 1: 2, 2: 1, 3: 2})
        rep_t4 = self.diff_engine.verify_legendary_prerequisites(71383, acc_t4)
        self.assertTrue(rep_t4.mastery_requirements_met)

    def test_active_crafting_license_verification_and_recommendations(self):
        """Verifies active crafting detection across character alts and structured recommendations."""
        # 1. Active licenses satisfy requirement
        acc_active = AccountState(
            characters=[
                {
                    "name": "Kerling",
                    "crafting": [
                        {"discipline": "Weaponsmith", "rating": 500, "active": True},
                        {"discipline": "Armorsmith", "rating": 500, "active": True}
                    ]
                }
            ],
            active_disciplines={"weaponsmith": ["Kerling"], "armorsmith": ["Kerling"]},
            character_disciplines={
                "Kerling": {
                    "weaponsmith": {"rating": 500, "active": True},
                    "armorsmith": {"rating": 500, "active": True}
                }
            }
        )
        rep_active = self.diff_engine.verify_legendary_prerequisites(30704, acc_active)
        self.assertTrue(rep_active.active_crafting_ready)
        self.assertEqual(len(rep_active.crafting_assignment_recommendations), 0)

        # 2. Inactive license generates ACTIVATE recommendation
        acc_inactive = AccountState(
            characters=[
                {
                    "name": "Kerling",
                    "crafting": [
                        {"discipline": "Weaponsmith", "rating": 500, "active": False},
                        {"discipline": "Armorsmith", "rating": 500, "active": True}
                    ]
                }
            ],
            active_disciplines={"armorsmith": ["Kerling"]},
            character_disciplines={
                "Kerling": {
                    "weaponsmith": {"rating": 500, "active": False},
                    "armorsmith": {"rating": 500, "active": True}
                }
            }
        )
        rep_inactive = self.diff_engine.verify_legendary_prerequisites(30704, acc_inactive)
        self.assertFalse(rep_inactive.active_crafting_ready)
        recs = rep_inactive.crafting_assignment_recommendations
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["discipline"], "weaponsmith")
        self.assertEqual(recs[0]["action"], "ACTIVATE")
        self.assertEqual(recs[0]["character"], "Kerling")

        # 3. Underleveled license generates LEVEL_UP recommendation
        acc_under = AccountState(
            characters=[
                {
                    "name": "Kerling",
                    "crafting": [
                        {"discipline": "Weaponsmith", "rating": 400, "active": True},
                        {"discipline": "Armorsmith", "rating": 500, "active": True}
                    ]
                }
            ],
            active_disciplines={"weaponsmith": ["Kerling"], "armorsmith": ["Kerling"]},
            character_disciplines={
                "Kerling": {
                    "weaponsmith": {"rating": 400, "active": True},
                    "armorsmith": {"rating": 500, "active": True}
                }
            }
        )
        rep_under = self.diff_engine.verify_legendary_prerequisites(30704, acc_under)
        self.assertFalse(rep_under.active_crafting_ready)
        recs_under = rep_under.crafting_assignment_recommendations
        self.assertEqual(len(recs_under), 1)
        self.assertEqual(recs_under[0]["action"], "LEVEL_UP")
        self.assertEqual(recs_under[0]["current_rating"], 400)
        self.assertEqual(recs_under[0]["required_rating"], 500)

        # 4. Completely untrained discipline generates TRAIN recommendation
        acc_untrained = AccountState(
            characters=[{"name": "Aubefein", "crafting": []}],
            active_disciplines={},
            character_disciplines={"Aubefein": {}}
        )
        rep_untrained = self.diff_engine.verify_legendary_prerequisites(30704, acc_untrained)
        self.assertFalse(rep_untrained.active_crafting_ready)
        self.assertTrue(any(r["action"] == "TRAIN" and r["discipline"] == "weaponsmith" for r in rep_untrained.crafting_assignment_recommendations))

    def test_hobbs_precursor_collection_bitmask_progress(self):
        """Verifies bitmask analysis for Hobbs collections across Tiers 1, 2, 3, and Precursor Owned."""
        # 1. Tier 1 Dusk in progress with 8/15 bits
        acc_dusk1 = AccountState(
            achievement_bits={2420: [0, 1, 2, 3, 4, 5, 6, 7]}  # 8 bits done
        )
        rep_d1 = self.diff_engine.verify_legendary_prerequisites(30704, acc_dusk1)
        self.assertEqual(rep_d1.precursor_collection_step, "Dusk I: The Experimental Nightsword")
        self.assertEqual(rep_d1.precursor_collection_bits_done, 8)
        self.assertEqual(rep_d1.precursor_collection_bits_total, 15)

        # 2. Tier 1 completed, Tier 2 in progress with 5/16 bits
        acc_dusk2 = AccountState(
            completed_achievements={2420},
            achievement_bits={2184: [0, 1, 2, 3, 4]}  # 5 bits done
        )
        rep_d2 = self.diff_engine.verify_legendary_prerequisites(30704, acc_dusk2)
        self.assertEqual(rep_d2.precursor_collection_step, "Dusk II: The Perfected Nightsword")
        self.assertEqual(rep_d2.precursor_collection_bits_done, 5)
        self.assertEqual(rep_d2.precursor_collection_bits_total, 16)

        # 3. Tiers 1 and 2 completed, Tier 3 in progress with 12/30 bits
        acc_dusk3 = AccountState(
            completed_achievements={2420, 2184},
            achievement_bits={2183: list(range(12))}  # 12 bits done
        )
        rep_d3 = self.diff_engine.verify_legendary_prerequisites(30704, acc_dusk3)
        self.assertEqual(rep_d3.precursor_collection_step, "Dusk III: Dusk")
        self.assertEqual(rep_d3.precursor_collection_bits_done, 12)
        self.assertEqual(rep_d3.precursor_collection_bits_total, 30)

        # 4. All 3 tiers completed
        acc_done = AccountState(
            completed_achievements={2420, 2184, 2183}
        )
        rep_done = self.diff_engine.verify_legendary_prerequisites(30704, acc_done)
        self.assertEqual(rep_done.precursor_collection_step, "COMPLETED")
        self.assertEqual(rep_d3.precursor_collection_bits_total, 30)

        # 5. Precursor Dusk already in Bank (collection satisfied / not blocking)
        acc_owned = AccountState(
            bank={29185: 1}  # Dusk in bank!
        )
        rep_owned = self.diff_engine.verify_legendary_prerequisites(30704, acc_owned)
        self.assertEqual(rep_owned.precursor_collection_step, "COMPLETED")
        self.assertFalse(any("Precursor collection incomplete" in b for b in rep_owned.blockers))

        # 6. Alias achievement IDs (2379, 2382, 2380)
        acc_alias = AccountState(
            achievement_bits={2379: [0, 1, 2]}
        )
        rep_alias = self.diff_engine.verify_legendary_prerequisites(30704, acc_alias)
        self.assertEqual(rep_alias.precursor_collection_step, "Dusk I: The Experimental Nightsword")
        self.assertEqual(rep_alias.precursor_collection_bits_done, 3)

    def test_can_craft_immediately_fully_satisfied(self):
        """Account with all prerequisites met should have can_craft_immediately=True and 0 blockers."""
        acc_ready = AccountState(
            titles={12},  # World exploration unlocked
            masteries={6: 3},  # Central Tyria Legendary Crafting Tier 3
            bank={29185: 1},  # Owns Dusk in bank
            characters=[
                {
                    "name": "Kerling",
                    "crafting": [
                        {"discipline": "Weaponsmith", "rating": 500, "active": True},
                        {"discipline": "Armorsmith", "rating": 500, "active": True}
                    ]
                }
            ],
            active_disciplines={"weaponsmith": ["Kerling"], "armorsmith": ["Kerling"]},
            character_disciplines={
                "Kerling": {
                    "weaponsmith": {"rating": 500, "active": True},
                    "armorsmith": {"rating": 500, "active": True}
                }
            }
        )

        rep = self.diff_engine.verify_legendary_prerequisites(30704, acc_ready)
        self.assertTrue(rep.has_world_completion)
        self.assertEqual(rep.world_completion_source, "TITLE_12")
        self.assertTrue(rep.mastery_requirements_met)
        self.assertTrue(rep.active_crafting_ready)
        self.assertEqual(rep.precursor_collection_step, "COMPLETED")
        self.assertTrue(rep.can_craft_immediately)
        self.assertEqual(len(rep.blockers), 0)


if __name__ == "__main__":
    unittest.main()
