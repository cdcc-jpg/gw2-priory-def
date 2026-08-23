"""Tests for the Twilight Legendary Acquisition Journey logic."""

import unittest
from pathlib import Path
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState, AccountDiffEngine
from engine.twilight_journey_solver import TwilightJourneySolver, TwilightJourneyPlan

DEF_REPO = Path(__file__).parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")

class TestTwilightJourney(unittest.TestCase):

    def setUp(self):
        self.store = PrioryGraphStore(ref_repo_path=REF_REPO, def_repo_path=DEF_REPO)
        self.store.load_all()
        self.diff_engine = AccountDiffEngine(self.store)
        self.solver = TwilightJourneySolver(self.store)

    def test_twilight_journey_web_loaded(self):
        # 1. Verify that twilight_journey_web.ttl paths exist in the graph store
        
        # Check for Trading Post Purchase of Dusk
        query_tp = """
        SELECT ?path WHERE {
            ?path a priory:TradingPostPurchasePath ;
                  rdfs:label "Trading Post Purchase of Dusk" .
        }
        """
        res_tp = self.store.query(query_tp)
        self.assertGreater(len(res_tp), 0, "Dusk TP path not found in the graph store.")
        
        # Check for all target items equal to Dusk (29185)
        query_paths = """
        SELECT ?path WHERE {
            { ?path priory:targetItem <https://priory.gw2/id/item/29185> }
            UNION
            { ?path priory:producesItem <https://priory.gw2/id/item/29185> }
        }
        """
        res_paths = self.store.query(query_paths)
        self.assertGreaterEqual(len(res_paths), 4, "Expected at least 4 Dusk acquisition paths.")

    def test_mount_and_region_vocabs(self):
        # 2. Verify SKOS schemes for mounts and regions are queryable
        
        # Mount scheme check
        query_mount = """
        SELECT ?mount WHERE {
            ?mount a skos:Concept ;
                   skos:inScheme mount:MountScheme .
        }
        """
        res_mount = self.store.query(query_mount)
        self.assertGreater(len(res_mount), 0, "Mount scheme concepts not found.")
        
        # Core Tyria region check (ExplorationZone)
        query_zone = """
        SELECT ?zone WHERE {
            ?zone a priory:ExplorationZone ;
                  priory:zoneName "Kryta" .
        }
        """
        res_zone = self.store.query(query_zone)
        self.assertGreater(len(res_zone), 0, "Kryta exploration zone not found.")

    def test_account_state_mounts_and_expansions(self):
        # 3. Verify AccountState.has_mount() and AccountState.has_expansion()
        account = AccountState(
            mount_types=["raptor", "skyscale"],
            expansion_access=["GuildWars2", "PathOfFire", "EndOfDragons"]
        )
        self.assertTrue(account.has_mount("skyscale"))
        self.assertTrue(account.has_mount("raptor"))
        self.assertFalse(account.has_mount("griffon"))
        
        self.assertTrue(account.has_expansion("PathOfFire"))
        self.assertTrue(account.has_expansion("EndOfDragons"))
        self.assertFalse(account.has_expansion("HeartOfThorns"))

    def test_fresh_account_twilight_journey(self):
        # 4. Test TwilightJourneySolver on a fresh account
        account = AccountState()
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report, 
            account=account, 
            tp_prices={29185: 350.0}, 
            time_budget_minutes=120
        )
        
        self.assertIsInstance(plan, TwilightJourneyPlan)
        self.assertEqual(len(plan.pillars), 4, "Expected 4 pillars for Twilight.")
        
        # Fresh account readiness should be 0%
        self.assertEqual(plan.overall_readiness_pct, 0.0)
        
        # Fresh account has no expansions so we expect a warning about mounts
        self.assertGreater(len(plan.expansion_warnings), 0)
        
        # Session itinerary should be populated based on time budget
        self.assertGreater(len(plan.session_itinerary), 0)

    def test_advanced_account_twilight_journey(self):
        # 5. Test TwilightJourneySolver on an endgame account
        account = AccountState(
            materials={
                19675: 50,  # 50 Mystic Clovers
            },
            bank={
                29185: 1,   # Dusk
            },
            disciplines={
                "weaponsmith": 500
            },
            mount_types=["raptor", "skyscale"],
            expansion_access=["GuildWars2", "PathOfFire", "LivingWorldSeason4"]
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report, 
            account=account, 
            tp_prices={29185: 350.0}, 
            time_budget_minutes=120
        )
        
        # Precursor pillar should be 100% since Dusk is in the bank
        precursor_pillar = next((p for p in plan.pillars if p.pillar_name == "Precursor: Dusk"), None)
        self.assertIsNotNone(precursor_pillar)
        self.assertEqual(precursor_pillar.readiness_pct, 100.0)
        self.assertEqual(precursor_pillar.status, "COMPLETED")

        # Clovers should make fortune pillar partially complete
        fortune_pillar = next((p for p in plan.pillars if p.pillar_name == "Gift of Fortune"), None)
        self.assertIsNotNone(fortune_pillar)
        self.assertGreater(fortune_pillar.readiness_pct, 0.0)

    def test_session_time_budget_constraints(self):
        # 6. Verify session itinerary respects time budgets (30m, 60m, 120m)
        account = AccountState()
        diff_report = self.diff_engine.compute_diff(30704, account)
        
        for budget in [30, 60, 120]:
            plan = self.solver.build_journey_plan(
                diff_report=diff_report, 
                account=account, 
                time_budget_minutes=budget
            )
            total_time = sum(action.estimated_minutes for action in plan.session_itinerary)
            self.assertLessEqual(total_time, budget, f"Session itinerary exceeded {budget} minutes.")

    def test_precursor_triage_strategies(self):
        # 7. Verifies all 4 precursor strategies are returned and properly evaluated
        account = AccountState()
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report, 
            account=account, 
            tp_prices={29185: 350.0}
        )
        
        strategies = plan.precursor_strategies
        self.assertEqual(len(strategies), 4)
        
        strategy_names = [s.strategy_name for s in strategies]
        self.assertIn("Trading Post Direct Purchase", strategy_names)
        self.assertIn("Wizard's Vault Legendary Starter Kit", strategy_names)
        self.assertIn("Grandmaster Hobbs Collection (Dusk I, II, III)", strategy_names)
        self.assertIn("Mystic Forge Rare Greatsword Promotion", strategy_names)

    def test_shared_primitives_graph_loading(self):
        # 8. Verify that shared modular primitives are loaded in the RDF graph
        query_clover = """
        SELECT ?path WHERE {
            ?path a priory:VendorExchangePath ;
                  rdfs:label "Wizard's Vault Exchange for Mystic Clovers" .
        }
        """
        res_clover = self.store.query(query_clover)
        self.assertGreater(len(res_clover), 0, "Shared Clover exchange path not found in graph.")

        query_obsidian = """
        SELECT ?path WHERE {
            ?path a priory:VendorExchangePath ;
                  rdfs:label "Temple of Balthazar Karma Vendor" .
        }
        """
        res_obsidian = self.store.query(query_obsidian)
        self.assertGreater(len(res_obsidian), 0, "Shared Obsidian farming path not found in graph.")

        query_t6 = """
        SELECT ?path WHERE {
            ?path a priory:VendorExchangePath ;
                  rdfs:label "Volatile Magic Trophy Shipments" .
        }
        """
        res_t6 = self.store.query(query_t6)
        self.assertGreater(len(res_t6), 0, "Shared T6 conversion path not found in graph.")

    def test_booster_and_contested_temple_advice(self):
        # 9. Verify booster recommendations for WvW and LFG fallback for Temple of Balthazar
        account = AccountState()
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account,
            time_budget_minutes=180
        )
        
        # Check Mastery pillar actions for booster tips and contested temple workaround
        mastery_pillar = next((p for p in plan.pillars if p.pillar_name == "Gift of Mastery"), None)
        self.assertIsNotNone(mastery_pillar)

        action_descs = " ".join(a.action_description for a in mastery_pillar.recommended_actions)
        self.assertTrue("booster" in action_descs.lower() or "buff" in action_descs.lower(), "Expected booster advice for WvW track.")
        self.assertTrue("lfg" in action_descs.lower() or "contested" in action_descs.lower() or "taxi" in action_descs.lower(), "Expected contested temple workaround advice.")

    def test_multi_character_discipline_handoff(self):
        # 10. Verify character assignment and split discipline handoffs
        account = AccountState(
            characters=[
                {
                    "name": "Warrior Tank",
                    "crafting": [{"discipline": "Weaponsmith", "rating": 450, "active": True}]
                },
                {
                    "name": "Guardian Healer",
                    "crafting": [{"discipline": "Armorsmith", "rating": 500, "active": True}]
                }
            ]
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )

        rec_char = plan.recommended_character
        self.assertIsNotNone(rec_char)
        self.assertIn("Warrior Tank", rec_char)
        self.assertIn("Guardian Healer", rec_char)

    def test_four_chapter_master_journey(self):
        # 11. Verify 4-Chapter structure and wallet-aware triage
        account = AccountState(
            wallet={
                68: 1500,  # 1500 Astral Acclaim
                1: 5000000, # 500 Gold
                2: 2000000, # 2M Karma
                61: 600    # 600 Tales of Dungeon Delving
            }
        )
        self.assertEqual(account.astral_acclaim_count(), 1500)
        self.assertEqual(account.dungeon_tales_count(), 600)
        self.assertEqual(account.gold_count(), 500.0)
        self.assertEqual(account.karma_count(), 2000000)

        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account,
            tp_prices={29185: 350.0}
        )

        self.assertEqual(len(plan.chapters), 4, "Expected 4 chapters for Twilight Master Journey.")
        self.assertEqual(plan.chapters[0].chapter_number, 1)
        self.assertIn("Precursor", plan.chapters[0].chapter_title)
        self.assertEqual(plan.chapters[1].chapter_number, 2)
        self.assertIn("Expedition", plan.chapters[1].chapter_title)
        self.assertEqual(plan.chapters[2].chapter_number, 3)
        self.assertIn("Currencies", plan.chapters[2].chapter_title)
        self.assertEqual(plan.chapters[3].chapter_number, 4)
        self.assertIn("Forge", plan.chapters[3].chapter_title)

        # Chapter 1 should mention Wizard's Vault Astral Acclaim since player has 1500 AA
        ch1_actions = " ".join(a.action_description for a in plan.chapters[0].actions)
        self.assertTrue("wizard" in ch1_actions.lower() or "astral acclaim" in ch1_actions.lower() or "starter kit" in ch1_actions.lower())

    def test_chapter_1_hobbs_mastery_warning(self):
        # Account without enough Astral Acclaim (< 1200) or gold (< 320g)
        account = AccountState(
            wallet={68: 200, 1: 500000}, # 200 AA, 50g
            masteries={10: 1} # Central Tyria Legendary Crafting level 1 (needs 3)
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account,
            tp_prices={29185: 350.0}
        )
        ch1 = plan.chapters[0]
        self.assertEqual(ch1.chapter_number, 1)
        self.assertGreater(len(ch1.actions), 0)
        action = ch1.actions[0]
        self.assertIn("Hobbs", action.action_title)
        self.assertIn("Legendary Crafting", action.action_description)
        self.assertIn("1/3", action.action_description)

    def test_chapter_3_enriched_milestones(self):
        # Fresh account without WvW Gift of Battle, Bloodstone Shard, or T6 mats
        account = AccountState(
            wallet={23: 50} # 50 Spirit Shards (needs 200)
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account,
            tp_prices={24310: 0.45, 24309: 0.12}
        )
        ch3 = plan.chapters[2]
        self.assertEqual(ch3.chapter_number, 3)
        action_titles = [a.action_title for a in ch3.actions]
        action_descs = " ".join(a.action_description for a in ch3.actions)

        # 1. Gift of Battle milestone
        self.assertIn("Complete Gift of Battle WvW Reward Track", action_titles)
        self.assertTrue("4.5h" in action_descs and "8.0h" in action_descs)
        self.assertTrue("booster" in action_descs.lower())

        # 2. Bloodstone Shard / Spirit Shard milestone (< 200 SS)
        self.assertIn("Farm Spirit Shards for Bloodstone Shard", action_titles)

        # 3. Onyx Lodestone vs Core Forge Arbitrage
        self.assertIn("Onyx Lodestones vs Cores Mystic Forge Arbitrage", action_titles)
        self.assertTrue(("200" in action_descs and "100" in action_descs) or ("196" in action_descs and "98" in action_descs))

        # 4. Daily T6 Laurel & RIBA routine
        self.assertIn("Daily T6 Laurel Merchant & RIBA Routine", action_titles)
        self.assertTrue("laurel" in action_descs.lower() and "riba" in action_descs.lower())

        # Now test with 200+ Spirit Shards
        account_with_ss = AccountState(wallet={23: 200})
        plan_ss = self.solver.build_journey_plan(diff_report=diff_report, account=account_with_ss)
        ch3_ss_titles = [a.action_title for a in plan_ss.chapters[2].actions]
        self.assertIn("Purchase Bloodstone Shard from Miyani", ch3_ss_titles)

    def test_chapter_4_assigned_character_badges(self):
        # Account with dedicated crafter 'Kerling' (Weaponsmith 500, Armorsmith 500)
        account = AccountState(
            characters=[
                {
                    "name": "Kerling",
                    "crafting": [
                        {"discipline": "Weaponsmith", "rating": 500, "active": True},
                        {"discipline": "Armorsmith", "rating": 500, "active": True}
                    ]
                }
            ]
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )
        ch4 = plan.chapters[3]
        self.assertEqual(ch4.chapter_number, 4)
        self.assertGreater(len(ch4.actions), 0)

        for action in ch4.actions:
            self.assertEqual(action.assigned_character, "Kerling", f"Action {action.action_title} missing Kerling badge.")

    def test_chapter_1_hobbs_three_tiers_breakdown(self):
        """Verifies Chapter 1 details the 3 Hobbs tiers with Weaponsmith 450/500, Deldrimor steel, Gloom locations, and Mastery Tier 1-3."""
        account = AccountState(
            wallet={68: 100, 1: 100000}, # 100 AA, 10g
            masteries={10: 2} # Central Tyria Legendary Crafting level 2
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account,
            tp_prices={29185: 350.0}
        )
        ch1 = plan.chapters[0]
        self.assertEqual(ch1.chapter_number, 1)
        action = ch1.actions[0]
        desc = action.action_description

        # Verify Mastery Tiers 1-3
        self.assertIn("Legendary Crafting", desc)
        self.assertIn("Revered Antiquarian", desc)
        self.assertIn("Magister of Legends", desc)
        self.assertIn("Historian of the Armaments", desc)

        # Verify Weaponsmith 450 / 500
        self.assertIn("450", desc)
        self.assertIn("500", desc)

        # Verify Deldrimor steel
        self.assertIn("Deldrimor Steel", desc)

        # Verify Gloom locations
        self.assertIn("Gloom", desc)
        self.assertTrue("Fractals" in desc or "Tequatl" in desc or "Shadow Behemoth" in desc)

    def test_chapter_2_character_map_completion_and_dual_gifts(self):
        """Verifies Chapter 2 checks account characters, recommends primary mobility character with Skyscale, and highlights 2x Gifts of Exploration."""
        characters = [
            {"name": "Kerling", "profession": "Guardian", "level": 80},
            {"name": "Skuta Rantakallio", "profession": "Ranger", "level": 80},
            {"name": "Legacy Of Harathi", "profession": "Warrior", "level": 80},
            {"name": "Styrman", "profession": "Engineer", "level": 80},
            {"name": "Ksëne", "profession": "Necromancer", "level": 80},
            {"name": "Aubefein", "profession": "Elementalist", "level": 80},
            {"name": "Sara Loy", "profession": "Thief", "level": 80},
            {"name": "Flevkk", "profession": "Asura", "level": 80},
            {"name": "Like A Plastik Bag", "profession": "Mesmer", "level": 80},
            {"name": "Jaimelargent", "profession": "Thief", "level": 80},
            {"name": "Saladomatic", "profession": "Ranger", "level": 80}
        ]
        account = AccountState(
            characters=characters,
            mount_types=["raptor", "skyscale"],
            expansion_access=["GuildWars2", "PathOfFire", "SecretsOfTheObscure"]
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )
        ch2 = plan.chapters[1]
        self.assertEqual(ch2.chapter_number, 2)

        # Check overarching action
        map_action = ch2.actions[0]
        self.assertIn("Core Tyria Map Completion", map_action.action_title)
        self.assertIn("2x Gifts of Exploration", map_action.action_title)

        # Check primary mobility character and Skyscale recommendation
        desc = map_action.action_description
        self.assertIn("Skyscale", desc)
        self.assertIn("2x Gifts of Exploration", desc)
        self.assertIn("Twilight", desc)
        self.assertTrue("spare" in desc.lower() or "next gen 1" in desc.lower())

        # Check account roster awareness
        self.assertIn("11 characters", desc)
        self.assertIn("Kerling", desc)
        self.assertIn("Skuta Rantakallio", desc)

    def test_chapter_3_actual_owned_boosters_and_gobbler_telemetry(self):
        """Verifies Chapter 3 detects actual owned boosters/gobblers/tomes in bank and provides tailored activation instructions."""
        account = AccountState(
            bank={
                67836: 8,   # 8x Zhaitaffy Gobblers
                45003: 17,  # 17x Boosters
                19983: 315  # 315x Tomes of Knowledge
            },
            wallet={23: 50} # 50 Spirit Shards
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )
        ch3 = plan.chapters[2]
        self.assertEqual(ch3.chapter_number, 3)

        action_descs = " ".join(a.action_description for a in ch3.actions)

        # Check telemetry detection
        self.assertIn("67836", action_descs)
        self.assertIn("8x Zhaitaffy Gobbler", action_descs)
        self.assertIn("45003", action_descs)
        self.assertIn("17x Booster", action_descs)
        self.assertIn("19983", action_descs)
        self.assertIn("315x Tome of Knowledge", action_descs)

    def test_wizards_vault_exhaustion_suppression_and_cheapest_prioritization(self):
        """Verifies Wizard's Vault suppression, BUY-2046 clover priority, cost breakdowns, and 90-minute cheapest session plan."""
        account = AccountState(
            materials={
                19675: 6,   # 6 Clovers (needs 71)
                19925: 71,  # 71 Obsidian Shards (needs 179)
                24310: 2,   # 2 Onyx Lodestones (needs 98)
            },
            wallet={
                68: 1500,   # 1500 Astral Acclaim
                1: 5000000, # 500 Gold
            },
            characters=[
                {"name": "Kerling", "profession": "Guardian", "level": 80}
            ],
            mount_types=["raptor", "skyscale"],
            expansion_access=["GuildWars2", "PathOfFire", "SecretsOfTheObscure"]
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.solve_twilight_journey(
            diff_report=diff_report,
            account=account,
            tp_prices={29185: 141.0, 24310: 0.40, 24309: 0.10},
            time_budget_minutes=90,
            wizards_vault_exhausted=True,
            optimize_for_cost=True
        )

        # 1. Verify Precursor Strategies
        tp_strat = next((s for s in plan.precursor_strategies if s.strategy_name == "Trading Post Direct Purchase"), None)
        vault_strat = next((s for s in plan.precursor_strategies if s.strategy_name == "Wizard's Vault Legendary Starter Kit"), None)
        self.assertIsNotNone(tp_strat)
        self.assertTrue(tp_strat.is_recommended)
        self.assertIsNotNone(vault_strat)
        self.assertFalse(vault_strat.is_recommended)

        # 2. Verify Chapter 1 Precursor Decision (Dusk TP buy vs Hobbs breakdown)
        ch1 = plan.chapters[0]
        ch1_descs = " ".join(a.action_description for a in ch1.actions)
        self.assertIn("141", ch1_descs)
        self.assertIn("210", ch1_descs)
        self.assertTrue("cheaper" in ch1_descs.lower())
        self.assertNotIn("1200+ Astral Acclaim", ch1_descs)

        # 3. Verify Chapter 3 Currencies & Rituals (Clovers, Onyx Arbitrage, Balthazar Karma)
        ch3 = plan.chapters[2]
        ch3_descs = " ".join(a.action_description for a in ch3.actions)
        ch3_titles = [a.action_title for a in ch3.actions]

        # Suppress Astral Acclaim clovers in favor of BUY-2046 / Strike / Forge
        self.assertIn("BUY-2046", ch3_descs)
        self.assertIn("Mistlock Observatory", ch3_descs)
        self.assertIn("[&DYEFAAA=]", ch3_descs)
        self.assertIn("71", ch3_descs) # 71 needed clovers
        self.assertIn("19.6", ch3_descs) # 19.6g savings for Onyx promotion
        self.assertIn("98", ch3_descs) # 98 Onyx Lodestones
        self.assertIn("179", ch3_descs) # 179 Obsidian Shards
        self.assertIn("0 gold", ch3_descs) # 0 gold via Karma at Temple of Balthazar

        # 4. Verify 90-minute actionable session plan
        itinerary = plan.session_itinerary
        self.assertEqual(len(itinerary), 4)

        # [1] BUY-2046 Daily Clovers (~10 mins)
        self.assertEqual(itinerary[0].action_title, "BUY-2046 Daily Clovers (Mistlock Observatory [&DYEFAAA=])")
        self.assertEqual(itinerary[0].estimated_minutes, 10)
        self.assertEqual(itinerary[0].waypoint, "[&DYEFAAA=]")

        # [2] Ascalonian Catacombs dungeon run (~25 mins)
        self.assertEqual(itinerary[1].action_title, "Ascalonian Catacombs dungeon run for Tales of Dungeon Delving [&BIcBAAA=]")
        self.assertEqual(itinerary[1].estimated_minutes, 25)
        self.assertEqual(itinerary[1].waypoint, "[&BIcBAAA=]")

        # [3] Onyx Core Mystic Forge Promotion (~10 mins)
        self.assertEqual(itinerary[2].action_title, "Onyx Core Mystic Forge Promotion [&BBAEAAA=]")
        self.assertEqual(itinerary[2].estimated_minutes, 10)
        self.assertEqual(itinerary[2].waypoint, "[&BBAEAAA=]")

        # [4] Core Tyria Map Completion on Kerling with Skyscale (~45 mins)
        self.assertEqual(itinerary[3].action_title, "Core Tyria Map Completion on Kerling with Skyscale")
        self.assertEqual(itinerary[3].estimated_minutes, 45)
        self.assertEqual(itinerary[3].assigned_character, "Kerling")
        self.assertEqual(itinerary[3].recommended_mount, "Skyscale")

        total_session_minutes = sum(a.estimated_minutes for a in itinerary)
        self.assertEqual(total_session_minutes, 90)

    def test_chapter_4_vip_lounge_pass_unified_crafting(self):
        """Verifies Chapter 4 replaces separate city waypoints with unified VIP Lounge crafting when pass is owned."""
        account = AccountState(
            bank={
                81664: 1,  # Mistlock Sanctuary Passkey [&AgEAPwEA]
            },
            characters=[
                {
                    "name": "Kerling",
                    "crafting": [
                        {"discipline": "Weaponsmith", "rating": 500, "active": True},
                        {"discipline": "Armorsmith", "rating": 500, "active": True}
                    ]
                }
            ]
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )
        ch4 = plan.chapters[3]
        self.assertEqual(ch4.chapter_number, 4)
        
        # 1. Check VIP Lounge Pass Detection banner
        ch4_descs = " ".join(a.action_description for a in ch4.actions)
        self.assertIn("🌟 VIP Lounge Pass Detected: You own Mistlock Sanctuary Passkey [&AgEAPwEA]!", ch4_descs)
        self.assertIn("Weaponsmith 500 & Armorsmith 500 for Kerling", ch4_descs)
        self.assertIn("zero travel fees", ch4_descs)

        # 2. Check that all crafting & forging actions use the lounge chat link and zone
        for action in ch4.actions:
            self.assertEqual(action.waypoint, "[&AgEAPwEA]")
            self.assertEqual(action.zone_name, "Mistlock Sanctuary")
            self.assertEqual(action.assigned_character, "Kerling")

    def test_chapter_3_teleport_to_friend_and_silver_fed_salvage(self):
        """Verifies Chapter 3 mentions Recharging Teleport to Friend and Silver-Fed Salvage-o-Matic."""
        account = AccountState(
            bank={
                90335: 1,  # Recharging Teleport to Friend
                67027: 1,  # Silver-Fed Salvage-o-Matic
            },
            wallet={23: 50}  # 50 Spirit Shards
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )
        ch3 = plan.chapters[2]
        self.assertEqual(ch3.chapter_number, 3)
        ch3_descs = " ".join(a.action_description for a in ch3.actions)

        # 1. Teleport to Friend chat link and usage
        self.assertIn("Recharging Teleport to Friend", ch3_descs)
        self.assertIn("[&AgHfYAEA]", ch3_descs)
        self.assertTrue("taxi" in ch3_descs.lower() or "temple of balthazar" in ch3_descs.lower())

        # 2. Silver-Fed Salvage-o-Matic chat link and usage
        self.assertIn("Silver-Fed Salvage-o-Matic", ch3_descs)
        self.assertIn("[&AgHTBQEA]", ch3_descs)
        self.assertTrue("ectoplasm" in ch3_descs.lower() or "rare" in ch3_descs.lower())

    def test_chapter_4_permanent_contracts_anywhere_access(self):
        """Verifies Chapter 4 notes instant anywhere-access capability when Permanent Contracts are owned."""
        account = AccountState(
            bank={
                35976: 1,  # Permanent Bank Access Express [&AgGQjAAA]
                35978: 1,  # Permanent Trading Post Express [&AgGZjAAA]
                35977: 1,  # Permanent Merchant Express [&AgGJjAAA]
                35984: 1,  # Permanent Hair Stylist Contract [&AgG4XAAA]
            }
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )
        ch4 = plan.chapters[3]
        self.assertEqual(ch4.chapter_number, 4)
        ch4_descs = " ".join(a.action_description for a in ch4.actions)
        ch4_titles = [a.action_title for a in ch4.actions]

        self.assertIn("🌟 Permanent Contracts Detected (Instant Anywhere-Access)", ch4_titles)
        self.assertIn("Permanent Bank Access Express", ch4_descs)
        self.assertIn("[&AgGQjAAA]", ch4_descs)
        self.assertIn("Permanent Trading Post Express", ch4_descs)
        self.assertIn("[&AgGZjAAA]", ch4_descs)
        self.assertIn("Permanent Merchant Express", ch4_descs)
        self.assertIn("[&AgGJjAAA]", ch4_descs)
        self.assertIn("anywhere-access capability", ch4_descs)

    def test_chapter_3_ley_energy_converter_daily_checklist(self):
        """Verifies Chapter 3 adds daily converter checklist with free Obsidian Shards and HoT keys when Ley-Energy Converter is owned."""
        account = AccountState(
            bank={
                67280: 1,  # Ley-Energy Matter Converter [&AgGgCgEA]
                66624: 1,  # Karmic Converter [&AgEAfAEA]
            },
            wallet={23: 50}
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )
        ch3 = plan.chapters[2]
        self.assertEqual(ch3.chapter_number, 3)
        ch3_descs = " ".join(a.action_description for a in ch3.actions)
        ch3_titles = [a.action_title for a in ch3.actions]

        self.assertIn("🌟 Daily Converter Checklist (Free Obsidian Shards & Keys)", ch3_titles)
        self.assertIn("Ley-Energy Matter Converter", ch3_descs)
        self.assertIn("[&AgGgCgEA]", ch3_descs)
        self.assertIn("Tab 2", ch3_descs)
        self.assertIn("free Obsidian Shards", ch3_descs)
        self.assertTrue("machetes" in ch3_descs.lower() or "keys" in ch3_descs.lower())

    def test_chapter_4_invisible_bag_staging_and_stack_batching(self):
        """Verifies Chapter 4 incorporates Invisible Bag staging rules and 250-stack material storage batching recommendations."""
        account = AccountState()
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )
        ch4 = plan.chapters[3]
        self.assertEqual(ch4.chapter_number, 4)
        ch4_descs = " ".join(a.action_description for a in ch4.actions)
        ch4_titles = [a.action_title for a in ch4.actions]

        # 1. Action presence
        self.assertIn("🛡️ Material Staging: Invisible Bags & 250-Stack Batching", ch4_titles)

        # 2. Invisible Bag staging rules
        self.assertIn("Invisible Bag Staging Rules", ch4_descs)
        self.assertIn("Dusk", ch4_descs)
        self.assertIn("Deposit All Materials", ch4_descs)

        # 3. 250-stack batching recommendations
        self.assertIn("250-Stack Material Storage Batching", ch4_descs)
        self.assertIn("250-unit stacks", ch4_descs)

    def test_chapter_4_four_pillar_staging_checklist(self):
        """Verifies Chapter 4 contains the explicit 4-Pillar Inventory Staging Checklist before final assembly."""
        account = AccountState()
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )
        ch4 = plan.chapters[3]
        self.assertEqual(ch4.chapter_number, 4)
        
        # 1. Title verification
        ch4_titles = [a.action_title for a in ch4.actions]
        self.assertIn("📋 4-Pillar Inventory Staging Checklist", ch4_titles)

        # 2. Checklist items verification
        staging_action = next(a for a in ch4.actions if a.action_title == "📋 4-Pillar Inventory Staging Checklist")
        desc = staging_action.action_description
        self.assertIn("Pillar 1: Dusk", desc)
        self.assertIn("item:29185", desc)
        self.assertIn("Pillar 2: Gift of Twilight", desc)
        self.assertIn("GiftOfTwilight compound", desc)
        self.assertIn("Pillar 3: Gift of Mastery", desc)
        self.assertIn("Gift of Exploration", desc)
        self.assertIn("Gift of Battle", desc)
        self.assertIn("Bloodstone Shard", desc)
        self.assertIn("250 Obsidian Shards", desc)
        self.assertIn("Pillar 4: Gift of Fortune", desc)
        self.assertIn("77 Mystic Clovers", desc)
        self.assertIn("250 Ectos", desc)
        self.assertIn("Gift of Magic", desc)
        self.assertIn("Gift of Might", desc)

        # 3. Position check: Staging Checklist must be before Final Forge Assembly
        staging_idx = ch4_titles.index("📋 4-Pillar Inventory Staging Checklist")
        final_idx = ch4_titles.index("Final Forge Assembly")
        self.assertLess(staging_idx, final_idx)

    def test_chapter_4_post_forge_decision_fork(self):
        """Verifies Chapter 4 contains the Post-Forge Decision Fork with Path A, Path B, and Path C."""
        account = AccountState(
            characters=[
                {"name": "Kerling", "profession": "Guardian", "level": 80},
                {"name": "Skuta Rantakallio", "profession": "Ranger", "level": 80},
                {"name": "Legacy Of Harathi", "profession": "Warrior", "level": 80},
                {"name": "Styrman", "profession": "Engineer", "level": 80},
                {"name": "Ksëne", "profession": "Necromancer", "level": 80},
                {"name": "Aubefein", "profession": "Elementalist", "level": 80},
                {"name": "Sara Loy", "profession": "Thief", "level": 80},
                {"name": "Flevkk", "profession": "Asura", "level": 80},
                {"name": "Like A Plastik Bag", "profession": "Mesmer", "level": 80},
                {"name": "Jaimelargent", "profession": "Thief", "level": 80},
                {"name": "Saladomatic", "profession": "Ranger", "level": 80}
            ]
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        plan = self.solver.build_journey_plan(
            diff_report=diff_report,
            account=account
        )
        ch4 = plan.chapters[3]
        self.assertEqual(ch4.chapter_number, 4)

        # 1. Action presence
        ch4_titles = [a.action_title for a in ch4.actions]
        self.assertIn("🔮 Post-Forge Decision Fork (Armory Binding vs Eternity Arbitrage vs TP Sale)", ch4_titles)

        fork_action = next(a for a in ch4.actions if "Post-Forge Decision Fork" in a.action_title)
        desc = fork_action.action_description

        # 2. Path A verification
        self.assertIn("Path A: Legendary Armory Binding", desc)
        self.assertIn("all 11 characters", desc)
        self.assertIn("free stat swapping", desc)
        self.assertIn("Berserker, Viper, Celestial, Dragon", desc)
        self.assertIn("free sigil/infusion extraction", desc)

        # 3. Path B verification
        self.assertIn("Path B: The Eternity Commercial Arbitrage Loop", desc)
        self.assertIn("2nd Gift of Exploration", desc)
        self.assertIn("Sunrise", desc)
        self.assertIn("Eternity [&AgExZwAA]", desc)
        self.assertIn("3,800g", desc)
        self.assertIn("3,230g net", desc)
        self.assertIn("1,800g pure profit", desc)
        self.assertIn("Twilight and Sunrise skins", desc)

        # 4. Path C verification
        self.assertIn("Path C: Direct Trading Post Sale", desc)
        self.assertIn("1,900g TP listing", desc)
        self.assertIn("1,615g net cash", desc)

        # 5. Position check: Post-Forge Decision Fork must be after Final Forge Assembly
        final_idx = ch4_titles.index("Final Forge Assembly")
        fork_idx = ch4_titles.index("🔮 Post-Forge Decision Fork (Armory Binding vs Eternity Arbitrage vs TP Sale)")
        self.assertGreater(fork_idx, final_idx)


if __name__ == "__main__":
    unittest.main()



