"""Engine tests for GraphStore and AccountDiffEngine."""

import unittest
from pathlib import Path
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine, AccountState
from engine.path_solver import (
    PathSolver,
    ScheduledSessionTask,
    DailySessionItinerary,
    schedule_daily_session_itinerary
)

DEF_REPO = Path(__file__).parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")


class TestEngine(unittest.TestCase):

    def setUp(self):
        self.store = PrioryGraphStore(ref_repo_path=REF_REPO, def_repo_path=DEF_REPO)
        triples_loaded = self.store.load_all()
        self.assertGreater(triples_loaded, 0)

    def test_twilight_direct_ingredients(self):
        """Verifies that Twilight has all 4 expected Gen 1 components."""
        ingredients = self.store.get_direct_recipe_ingredients(30704) # Twilight ID
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

        report = engine.compute_diff(30704, fresh_account)
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
        self.assertEqual(report.summary_missing_materials["Mithril Ingot"], 250)
        self.assertEqual(report.summary_missing_materials["Orichalcum Ingot"], 500)
        self.assertTrue("Onyx Lodestone" in report.summary_missing_materials or "Onyx Core" in report.summary_missing_materials)

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

    def test_account_state_domain_helpers(self):
        """Verifies spirit_shards_count, has_bloodstone_shard, and has_gift_of_battle."""
        account = AccountState(
            wallet={23: 250},
            materials={19674: 1},
            inventory={19678: 1}
        )
        self.assertEqual(account.spirit_shards_count(), 250)
        self.assertTrue(account.has_bloodstone_shard())
        self.assertTrue(account.has_gift_of_battle())

        empty_account = AccountState()
        self.assertEqual(empty_account.spirit_shards_count(), 0)
        self.assertFalse(empty_account.has_bloodstone_shard())
        self.assertFalse(empty_account.has_gift_of_battle())

    def test_account_state_booster_and_gobbler_detection(self):
        """Verifies owned_boosters and has_gobbler detection across bank and inventory."""
        account = AccountState(
            bank={
                67836: 8,   # 8x Zhaitaffy Gobblers
                45003: 17,  # 17x Boosters
                19983: 315, # 315x Tomes of Knowledge
                2059: 5     # 5x Experience Boosters
            },
            inventory={
                42970: 3,   # 3x Heroic Boosters
                79523: 1    # 1x Snowflake Gobbler
            }
        )
        boosters = account.owned_boosters()
        self.assertEqual(boosters[67836], 8)
        self.assertEqual(boosters[45003], 17)
        self.assertEqual(boosters[19983], 315)
        self.assertEqual(boosters[2059], 5)
        self.assertEqual(boosters[42970], 3)
        self.assertEqual(boosters[79523], 1)
        self.assertNotIn(67037, boosters)

        self.assertTrue(account.has_gobbler())

        candy_account = AccountState(inventory={67037: 1})
        self.assertTrue(candy_account.has_gobbler())

        empty_account = AccountState()
        self.assertEqual(empty_account.owned_boosters(), {})
        self.assertFalse(empty_account.has_gobbler())

    def test_account_state_lounge_passes_and_convenience_items(self):
        """Verifies owned_lounges() and owned_convenience_items() detection across bank and inventory."""
        account = AccountState(
            bank={
                81664: 1,  # Mistlock Sanctuary Passkey
                90011: 1,  # Armistice Bastion Pass
                44602: 1,  # Copper-Fed Salvage-o-Matic
                67027: 1,  # Silver-Fed Salvage-o-Matic
                90335: 1,  # Recharging Teleport to Friend
            },
            inventory={
                98048: 1,  # Thousand Seas Pavilion Pass
                49149: 1,  # Royal Terrace Pass
                97009: 1,  # Arborstone Portal Scroll
                67393: 1,  # Candy Corn Gobbler
                92585: 1,  # Snowflake Gobbler
                70010: 1,  # Mystic Forge Conduit
            }
        )

        # 1. Verify owned lounges
        lounges = account.owned_lounges()
        self.assertEqual(len(lounges), 5)
        lounge_ids = {l["id"] for l in lounges}
        self.assertIn(81664, lounge_ids)
        self.assertIn(90011, lounge_ids)
        self.assertIn(98048, lounge_ids)
        self.assertIn(49149, lounge_ids)
        self.assertIn(97009, lounge_ids)

        mistlock = next(l for l in lounges if l["id"] == 81664)
        self.assertEqual(mistlock["name"], "Mistlock Sanctuary Passkey")
        self.assertEqual(mistlock["chat_link"], "[&AgEAPwEA]")
        self.assertTrue(account.has_lounge_pass())

        # 2. Verify owned convenience items
        conv = account.owned_convenience_items()
        self.assertIn("copper_fed", conv)
        self.assertIn("silver_fed", conv)
        self.assertIn("candy_corn_gobbler", conv)
        self.assertIn("snowflake_gobbler", conv)
        self.assertIn("teleport_to_friend", conv)
        self.assertIn("mystic_forge_conduit", conv)

        self.assertEqual(conv["copper_fed"]["chat_link"], "[&AgE6rgAA]")
        self.assertEqual(conv["silver_fed"]["chat_link"], "[&AgHTBQEA]")
        self.assertEqual(conv["teleport_to_friend"]["chat_link"], "[&AgHfYAEA]")
        self.assertEqual(conv["mystic_forge_conduit"]["chat_link"], "[&AgE6EQEA]")

        self.assertTrue(account.has_copper_fed())
        self.assertTrue(account.has_silver_fed())
        self.assertTrue(account.has_recharging_teleport_to_friend())
        self.assertTrue(account.has_mystic_forge_conduit())

        empty = AccountState()
        self.assertEqual(empty.owned_lounges(), [])
        self.assertEqual(empty.owned_convenience_items(), {})
        self.assertFalse(empty.has_lounge_pass())
        self.assertFalse(empty.has_copper_fed())
        self.assertFalse(empty.has_silver_fed())
        self.assertFalse(empty.has_recharging_teleport_to_friend())
        self.assertFalse(empty.has_mystic_forge_conduit())

    def test_account_state_all_seven_convenience_categories(self):
        """Verifies scanning and categorization across all 7 convenience categories."""
        account = AccountState(
            bank={
                # 1. permanent_contracts
                35976: 1,  # Permanent Bank Access Express
                35978: 1,  # Permanent Trading Post Express
                35977: 1,  # Permanent Merchant Express
                35984: 1,  # Permanent Hair Stylist Contract
                # 2. converters_and_gobblers
                67280: 1,  # Ley-Energy Matter Converter
                66624: 1,  # Karmic Converter
                92209: 1,  # Gleam of Sentience
                79895: 1,  # Sentient Aberration
                69887: 1,  # Princess
                68369: 1,  # Star of Gratitude
                # 3. portal_tomes
                80332: 1,  # LWS3 Portal Tome
                87508: 1,  # LWS4 Portal Tome
                92850: 1,  # IBS Portal Tome
                100788: 1, # Wizard's Tower Teleportation Scroll
                # 4. infinite_salvage
                44602: 1,  # Copper-Fed
                67027: 1,  # Silver-Fed
                87400: 1,  # Runecrafter's
                93121: 1,  # Endless Upgrade Extractor
                # 5. portable_forge
                70010: 1,  # Mystic Forge Conduit
                # 6. teleport_to_friend
                90335: 1,  # Recharging Teleport to Friend
                # 7. vip_lounges
                81664: 1,  # Mistlock Sanctuary Passkey
            }
        )

        # 1. Verify helper methods
        self.assertTrue(account.has_permanent_bank())
        self.assertTrue(account.has_permanent_tp())
        self.assertTrue(account.has_permanent_merchant())
        self.assertTrue(account.has_permanent_hair_stylist())
        self.assertTrue(account.has_permanent_contracts())
        self.assertTrue(account.has_ley_energy_converter())
        self.assertTrue(account.has_karmic_converter())
        self.assertTrue(account.has_sentient_converters())
        self.assertTrue(account.has_portal_tomes())
        self.assertTrue(account.has_runecrafter())
        self.assertTrue(account.has_upgrade_extractor())
        self.assertTrue(account.has_copper_fed())
        self.assertTrue(account.has_silver_fed())
        self.assertTrue(account.has_mystic_forge_conduit())
        self.assertTrue(account.has_recharging_teleport_to_friend())
        self.assertTrue(account.has_lounge_pass())

        # 2. Verify categorized scanner
        by_cat = account.owned_convenience_by_category()
        self.assertIn("permanent_contracts", by_cat)
        self.assertIn("converters_and_gobblers", by_cat)
        self.assertIn("portal_tomes", by_cat)
        self.assertIn("infinite_salvage", by_cat)
        self.assertIn("portable_forge", by_cat)
        self.assertIn("teleport_to_friend", by_cat)
        self.assertIn("vip_lounges", by_cat)

        self.assertEqual(len(by_cat["permanent_contracts"]), 4)
        self.assertEqual(len(by_cat["infinite_salvage"]), 4)
        self.assertEqual(len(by_cat["portal_tomes"]), 4)
        self.assertEqual(len(by_cat["portable_forge"]), 1)
        self.assertEqual(len(by_cat["teleport_to_friend"]), 1)
        self.assertEqual(len(by_cat["vip_lounges"]), 2)
        self.assertGreaterEqual(len(by_cat["converters_and_gobblers"]), 6)

    def test_account_state_map_completion_tracking(self):
        """Verifies default map_completed_characters, is_character_map_completed, and eligible_exploration_characters."""
        # 1. Default account state
        default_account = AccountState()
        self.assertEqual(default_account.map_completed_characters, ["Kerling"])
        self.assertTrue(default_account.is_character_map_completed("Kerling"))
        self.assertFalse(default_account.is_character_map_completed("Skuta Rantakallio"))
        
        eligible_default = default_account.eligible_exploration_characters()
        self.assertNotIn("Kerling", eligible_default)
        self.assertIn("Skuta Rantakallio", eligible_default)
        self.assertIn("Sara Loy", eligible_default)
        self.assertIn("Legacy Of Harathi", eligible_default)

        # 2. Account with explicit character roster
        custom_account = AccountState(
            characters=[
                {"name": "Kerling", "profession": "Guardian", "level": 80},
                {"name": "Sara Loy", "profession": "Thief", "level": 80},
                {"name": "Styrman", "profession": "Engineer", "level": 80}
            ],
            map_completed_characters=["Kerling", "Sara Loy"]
        )
        self.assertTrue(custom_account.is_character_map_completed("Kerling"))
        self.assertTrue(custom_account.is_character_map_completed("Sara Loy"))
        self.assertFalse(custom_account.is_character_map_completed("Styrman"))

        eligible_custom = custom_account.eligible_exploration_characters()
        self.assertEqual(eligible_custom, ["Styrman"])

        # 3. Account with only map-completed characters falls back to eligible default alts
        completed_only_account = AccountState(
            characters=[
                {"name": "Kerling", "profession": "Guardian", "level": 80}
            ],
            map_completed_characters=["Kerling"]
        )
        eligible_completed = completed_only_account.eligible_exploration_characters()
        self.assertNotIn("Kerling", eligible_completed)
        self.assertIn("Skuta Rantakallio", eligible_completed)
        self.assertIn("Sara Loy", eligible_completed)

    def test_substrate_agnostic_purchasing_power_and_currency_methods(self):
        """Verifies get_available_purchasing_power across wallet scalars and containerized tokens."""
        engine = AccountDiffEngine(self.store)
        account = AccountState(
            wallet={
                68: 550,   # Astral Acclaim
                29: 45,    # Provisioner Tokens
                23: 120,   # Spirit Shards
                69: 300    # Tales of Dungeon Delving
            },
            materials={
                19675: 40  # Mystic Clovers
            },
            bank={
                19675: 15  # Mystic Clovers
            },
            inventory={
                19675: 5   # Mystic Clovers
            }
        )

        # 1. Wallet currency resolution via URI, name, and apiWalletId
        self.assertEqual(engine.get_available_purchasing_power("currency:AstralAcclaim", account), 550)
        self.assertEqual(engine._get_astral_acclaim(account), 550)
        self.assertEqual(engine._get_provisioner_tokens(account), 45)
        self.assertEqual(engine._get_spirit_shards(account), 120)
        self.assertEqual(engine._get_dungeon_tales(account), 300)

        # 2. Containerized token (Mystic Clover 19675) across materials, bank, bags
        clover_balance = engine.get_available_purchasing_power(19675, account)
        self.assertEqual(clover_balance, 60)  # 40 + 15 + 5 = 60
        self.assertEqual(account.get_item_count(19675), 60)

        # 3. Graceful fallback when graph store is None
        fallback_engine = AccountDiffEngine(None)
        self.assertEqual(fallback_engine._get_astral_acclaim(account), 550)
        self.assertEqual(fallback_engine.get_available_purchasing_power(19675, account), 60)

    def test_cross_role_opportunity_cost_evaluation(self):
        """Verifies multi-role opportunity cost calculations and optimal role recommendation."""
        solver = PathSolver(self.store)

        # Case 1: TP Liquidation exceeds salvage and currency -> SELL_ON_TP
        tp_lead = solver.evaluate_cross_role_opportunity_cost(
            item_id=19721,  # Glob of Ectoplasm (Tradeable, salvageable)
            quantity=100,
            tp_sell_unit_price=100,
            salvage_expected_unit_value=50
        )
        self.assertEqual(tp_lead["optimal_role_disposition"], "SELL_ON_TP")
        self.assertEqual(tp_lead["tp_liquidation_value"], 100 * 100 * 0.85)
        self.assertEqual(tp_lead["salvage_liquidation_value"], 5000)

        # Case 2: Salvage liquidation exceeds TP (after 15% fee) -> SALVAGE
        salvage_lead = solver.evaluate_cross_role_opportunity_cost(
            item_id=19721,
            quantity=100,
            tp_sell_unit_price=100,
            salvage_expected_unit_value=90
        )
        self.assertEqual(salvage_lead["optimal_role_disposition"], "SALVAGE")
        self.assertEqual(salvage_lead["salvage_liquidation_value"], 9000)
        self.assertEqual(salvage_lead["tp_liquidation_value"], 8500)

        # Case 3: Direct currency exchange exceeds liquidation -> SPEND_AS_CURRENCY
        currency_lead = solver.evaluate_cross_role_opportunity_cost(
            item_id=68,
            quantity=50,
            tp_sell_unit_price=0,
            salvage_expected_unit_value=0,
            direct_exchange_unit_value=2.0
        )
        self.assertEqual(currency_lead["optimal_role_disposition"], "SPEND_AS_CURRENCY")
        self.assertEqual(currency_lead["direct_exchange_value"], 100.0)

        # Case 4: Zero liquidation value or crafting ingredient hold -> HOLD_AS_CRAFTING_MAT
        craft_hold = solver.evaluate_cross_role_opportunity_cost(
            item_id=19721,
            quantity=100,
            tp_sell_unit_price=0,
            salvage_expected_unit_value=0
        )
        self.assertEqual(craft_hold["optimal_role_disposition"], "HOLD_AS_CRAFTING_MAT")

    def test_daily_session_itinerary_knapsack_scheduling(self):
        """Verifies PathSolver.schedule_daily_session_itinerary computes optimal daily itinerary."""
        solver = PathSolver(self.store)
        account = AccountState(
            characters=[{
                "name": "Kerling",
                "crafting": [{"discipline": "Weaponsmith", "rating": 500, "active": True}]
            }]
        )
        itinerary = solver.schedule_daily_session_itinerary(
            goal_item_id=30704,  # Twilight
            time_budget_minutes=90,
            account_state=account
        )
        self.assertIsInstance(itinerary, DailySessionItinerary)
        self.assertEqual(itinerary.goal_name, "Twilight")
        self.assertEqual(itinerary.total_scheduled_minutes, 45)
        self.assertEqual(itinerary.time_utilization_pct, 50.0)

        # Check tasks and order
        task_categories = [t.category for t in itinerary.tasks]
        self.assertEqual(task_categories, [
            "QUARTZ_CHARGING",
            "DAILY_REFINEMENT",
            "WORLD_BOSS_ANOMALY",
            "DAILY_FRACTAL_CLOVERS"
        ])

        # Waypoint validation
        quartz = itinerary.tasks[0]
        self.assertEqual(quartz.waypoint_code, "[&BPwCAAA=]")
        self.assertEqual(quartz.estimated_duration_minutes, 2)
        self.assertEqual(quartz.required_inputs["count"], 25)

        refinement = itinerary.tasks[1]
        self.assertEqual(refinement.estimated_duration_minutes, 3)
        self.assertEqual(refinement.character_name, "Kerling")

        anomaly = itinerary.tasks[2]
        self.assertEqual(anomaly.waypoint_code, "[&BEoCAAA=]")
        self.assertEqual(anomaly.estimated_duration_minutes, 10)
        self.assertEqual(anomaly.reward_output["name"], "Mystic Coin")

        fractals = itinerary.tasks[3]
        self.assertEqual(fractals.estimated_duration_minutes, 30)
        self.assertEqual(fractals.reward_output["name"], "Mystic Clover")


if __name__ == "__main__":
    unittest.main()




