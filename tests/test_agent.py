"""Unit tests for the Neuro-Symbolic Agent layer."""

import unittest
from pathlib import Path
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState, AccountDiffEngine
from agent.orchestrator import PrioryAgentOrchestrator
from agent.intent_parser import IntentParser, GoalType
from agent.llm_client import RuleBasedMockLLMClient
from engine.semantic_query import SemanticQueryService


class TestAgentPipeline(unittest.TestCase):

    def setUp(self):
        self.store = PrioryGraphStore()
        self.store.load_all()
        self.mock_llm = RuleBasedMockLLMClient()
        self.orchestrator = PrioryAgentOrchestrator(
            graph_store=self.store,
            llm_client=self.mock_llm
        )

    def test_intent_parsing(self):
        """Verifies parsing a player prompt into structured constraints."""
        service = SemanticQueryService(self.store)
        parser = IntentParser(service, self.mock_llm)

        prompt = "I want to craft Twilight tonight. I have 3 hours, but I hate WvW and have 400g."
        resolved_goal = parser.parse_intent(prompt)

        self.assertEqual(resolved_goal.resolved_item_name, "Twilight")
        self.assertEqual(resolved_goal.resolved_item_id, 30704)
        self.assertEqual(resolved_goal.intent.time_budget_minutes, 180)
        self.assertIn("WvW", resolved_goal.intent.excluded_game_modes)
        self.assertEqual(resolved_goal.intent.liquid_gold_budget, 400)

    def test_legendary_sigil_quantity_scaling_with_wallet_tokens(self):
        """Verifies parsing and scaling requirements for '2 Legendary Sigils' with owned Provisioner Tokens."""
        service = SemanticQueryService(self.store)
        parser = IntentParser(service, self.mock_llm)

        prompt = "I want to craft 2 legendary sigils tonight. I have 90 mins."
        resolved_goal = parser.parse_intent(prompt)

        self.assertEqual(resolved_goal.resolved_item_name, "Legendary Sigil")
        self.assertEqual(resolved_goal.resolved_item_id, 91505)
        self.assertEqual(resolved_goal.target_quantity, 2)

        # Player owns 20 Clovers (needs 30 * 2 = 60) and 440 Provisioner Tokens in wallet (needs 100)
        player_account = AccountState(
            materials={19675: 20},
            wallet={29: 440} # 440 Provisioner Tokens owned (Currency ID 29)!
        )
        diff_engine = AccountDiffEngine(self.store)
        report = diff_engine.compute_diff(91505, player_account, target_quantity=2)

        # 60 needed - 20 owned = 40 missing Clovers
        self.assertEqual(report.summary_missing_materials["Mystic Clover"], 40)
        # 10 * 75 * 2 = 1500 Lucent Crystals
        self.assertEqual(report.summary_missing_materials["Lucent Crystal"], 1500)
        # 75 * 2 = 150 of each symbol
        self.assertEqual(report.summary_missing_materials["Symbol of Control"], 150)
        # Gift of Craftsmanship is satisfied because wallet has 440 tokens (needs 100)
        self.assertNotIn("Gift of Craftsmanship", report.summary_missing_materials)

        # Full pipeline test
        guide = self.orchestrator.run_pipeline(prompt, player_account)
        # No daily provisioner task should be in the checklist
        provisioner_tasks = [s for s in guide.session_checklist if "Provisioner Barter Run" in s.title]
        self.assertEqual(len(provisioner_tasks), 0)

    def test_multi_turn_chat_session_with_vault_exhaustion(self):
        """Verifies multi-turn chat session where player notes Wizard's Vault is already completed."""
        player_account = AccountState(
            materials={19675: 20}, # 20 Clovers owned (needs 60)
            wallet={29: 440}       # 440 Provisioner tokens owned (needs 100)
        )
        session = self.orchestrator.create_session(account_state=player_account)

        # Turn 1: Prompt noting Vault clovers are already bought
        prompt = "I'm looking into crafting 2 leggy upgrades for weapons, sigils i think. I already bought the clovers from wizard vault."
        guide1 = session.send_message(prompt)

        self.assertEqual(guide1.goal_name, "Legendary Sigil")
        self.assertEqual(guide1.target_quantity, 2)
        # Should detect vault exhaustion and recommend alternative clover routes
        exhausted_rec = any("Exhausted" in r or "Fractal" in r for r in guide1.strategic_recommendations)
        self.assertTrue(exhausted_rec)

        # Turn 2: Follow-up question retaining the 2 Sigils context
        follow_up = "How much time should I spend tonight if I only have 60 mins?"
        guide2 = session.send_message(follow_up)

        self.assertEqual(guide2.goal_name, "Legendary Sigil")
        self.assertEqual(guide2.target_quantity, 2)
        self.assertGreater(len(guide2.session_checklist), 0)

    def test_orchestrator_end_to_end_sandwich(self):
        """Verifies complete Neuro-Symbolic Sandwich execution with player state diffing."""
        # Player owns Dusk in bank and 50 Clovers in material storage
        player_account = AccountState(
            materials={19675: 50}, # 50 Clovers (needs 77)
            bank={29185: 1},       # Dusk owned
            disciplines={"weaponsmith": 500}
        )

        user_prompt = "I have 2 hours to play tonight. Can you help me finish Twilight? I avoid WvW."
        guide = self.orchestrator.run_pipeline(user_prompt, player_account)

        self.assertEqual(guide.goal_name, "Twilight")
        self.assertGreater(len(guide.session_checklist), 0)

        # Strategic recommendations should reflect WvW exclusion and Clover alternatives
        wvw_rec = any("WvW" in r for r in guide.strategic_recommendations)
        self.assertTrue(wvw_rec)

        # Missing materials must reflect exact delta (27 Clovers missing, Dusk satisfied)
        self.assertEqual(guide.missing_materials_summary["Mystic Clover"], 27)
        self.assertNotIn("Dusk", guide.missing_materials_summary)

    def test_time_budget_constrained_session_planning(self):
        """Verifies session checklist respects 45-minute budget and includes domain clarification on spears."""
        player_account = AccountState(
            wallet={45: 2500, 23: 150, 3: 20} # 2500 Volatile Magic, 150 Spirit Shards, 20 Laurels
        )

        user_prompt = "I have 45 minutes tonight and want to work on crafting the tier two spear."
        guide = self.orchestrator.run_pipeline(user_prompt, player_account)

        self.assertGreater(len(guide.session_checklist), 0)
        total_time = sum(step.estimated_time_minutes for step in guide.session_checklist)
        self.assertLessEqual(total_time, 45)

        # Should include domain note on spears
        spear_note = any("Domain Note on Spears" in r or "spear" in r.lower() for r in guide.strategic_recommendations)
        self.assertTrue(spear_note)

    def test_t6_acquisition_solver_strategies(self):
        """Verifies PathSolver generates grounded T6 conversion strategies based on wallet currencies."""
        player_account = AccountState(
            wallet={45: 1000, 23: 50, 3: 15}
        )

        diff_report = self.orchestrator.diff_engine.compute_diff(
            goal_item_id=30699, # Twilight (needs T6 Powerful Blood, etc.)
            account=player_account
        )
        plan = self.orchestrator.solver.solve_optimal_path(
            diff_report=diff_report,
            account=player_account,
            time_budget_minutes=45
        )

        self.assertGreater(len(plan.t6_strategies), 0)
        self.assertTrue(any("Volatile Magic" in s for s in plan.t6_strategies))
        self.assertTrue(any("Mystic Forge" in s for s in plan.t6_strategies))
        self.assertTrue(any("Laurel" in s for s in plan.t6_strategies))

        # Check that roadmap adheres to 45 min budget
        total_roadmap_time = sum(s.get("est_time_mins", 0) for s in plan.step_by_step_roadmap)
        self.assertLessEqual(total_roadmap_time, 45)

    def test_intent_parser_wizards_vault_exhaustion_and_cheapest_gold(self):
        """Verifies intent parser and orchestrator set wizards_vault_exhausted=True and optimization_target='cheapest_gold'."""
        service = SemanticQueryService(self.store)
        parser = IntentParser(service, self.mock_llm)

        prompt = "What is the cheapest way to finish Twilight? I already bought the clovers from Wizard's Vault."
        resolved_goal = parser.parse_intent(prompt)

        self.assertEqual(resolved_goal.resolved_item_name, "Twilight")
        self.assertEqual(resolved_goal.resolved_item_id, 30704)
        self.assertTrue(resolved_goal.wizards_vault_exhausted)
        self.assertEqual(resolved_goal.optimization_target, "cheapest_gold")

        # Full pipeline test
        player_account = AccountState(
            materials={19675: 6, 19925: 71, 24310: 2},
            wallet={68: 1500, 1: 5000000},
            characters=[{"name": "Kerling", "profession": "Guardian", "level": 80}],
            mount_types=["raptor", "skyscale"],
            expansion_access=["GuildWars2", "PathOfFire", "SecretsOfTheObscure"]
        )
        guide = self.orchestrator.run_pipeline(prompt, player_account)
        self.assertEqual(guide.goal_name, "Twilight")
        self.assertGreater(len(guide.session_checklist), 0)

    def test_vip_lounge_and_convenience_callout_in_guide(self):
        """Verifies VIP lounge callout and convenience tools (Mistlock, Copper-Fed, Silver-Fed, Teleport to Friend) appear in guide."""
        player_account = AccountState(
            inventory={
                81664: 1,  # Mistlock Sanctuary Passkey [&AgEAPwEA]
                44602: 1,  # Copper-Fed Salvage-o-Matic [&AgE6rgAA]
                67027: 1,  # Silver-Fed Salvage-o-Matic [&AgHTBQEA]
                90335: 1,  # Recharging Teleport to Friend [&AgHfYAEA]
            },
            characters=[{"name": "Kerling", "profession": "Guardian", "level": 80, "crafting": [{"discipline": "Weaponsmith", "rating": 500}, {"discipline": "Armorsmith", "rating": 500}]}]
        )
        guide = self.orchestrator.run_pipeline("How do I get Twilight?", player_account)
        
        # 1. Strategic Recommendations Callout
        recs_text = " ".join(guide.strategic_recommendations)
        self.assertIn("Mistlock Sanctuary Passkey", recs_text)
        self.assertIn("[&AgEAPwEA]", recs_text)
        self.assertIn("Copper-Fed", recs_text)
        self.assertIn("[&AgE6rgAA]", recs_text)
        self.assertIn("Silver-Fed", recs_text)
        self.assertIn("[&AgHTBQEA]", recs_text)
        self.assertIn("Recharging Teleport to Friend", recs_text)
        self.assertIn("[&AgHfYAEA]", recs_text)

        # 2. Chapter 4 unified lounge workflow
        roadmap_text = " ".join(guide.master_roadmap_phases)
        self.assertIn("Mistlock Sanctuary", roadmap_text)
        self.assertIn("[&AgEAPwEA]", roadmap_text)

    def test_convenience_portfolio_and_bag_management_breakdown(self):
        """Verifies full Account Convenience & Utility Portfolio breakdown and bag management tips."""
        player_account = AccountState(
            inventory={
                81664: 1,  # Mistlock Sanctuary Passkey [&AgEAPwEA]
                97009: 1,  # Arborstone Portal Scroll [&AgHxegEA]
                84310: 1,  # Spearmarshal's Plea [&AgFpTwEA]
                67393: 1,  # Candy Corn Gobbler [&AgEZCgEA]
                73248: 1,  # Herta [&AgGgHAEA]
                86694: 1,  # Lucky Dog Harvesting Tool [&AgGyUgEA]
                44602: 1,  # Copper-Fed Salvage-o-Matic [&AgE6rgAA]
                90335: 1,  # Recharging Teleport to Friend [&AgHfYAEA]
            },
            characters=[{"name": "Kerling", "profession": "Guardian", "level": 80, "crafting": [{"discipline": "Weaponsmith", "rating": 500}, {"discipline": "Armorsmith", "rating": 500}]}]
        )
        guide = self.orchestrator.run_pipeline("How do I get Twilight?", player_account)

        recs_text = "\n".join(guide.strategic_recommendations)

        # 1. Portfolio Header & Categories
        self.assertIn("Account Convenience & Utility Portfolio", recs_text)
        self.assertIn("VIP Lounge Passes", recs_text)
        self.assertIn("Mistlock Sanctuary Passkey", recs_text)
        self.assertIn("[&AgEAPwEA]", recs_text)
        self.assertIn("Portal Tomes & Scrolls", recs_text)
        self.assertIn("Spearmarshal's Plea", recs_text)
        self.assertIn("[&AgFpTwEA]", recs_text)
        self.assertIn("Converters & Gobblers", recs_text)
        self.assertIn("Candy Corn Gobbler", recs_text)
        self.assertIn("[&AgEZCgEA]", recs_text)
        self.assertIn("Herta", recs_text)
        self.assertIn("Infinite Gathering Tools", recs_text)
        self.assertIn("Lucky Dog Harvesting Tool", recs_text)
        self.assertIn("[&AgGyUgEA]", recs_text)
        self.assertIn("Salvage & Utility Express", recs_text)
        self.assertIn("Copper-Fed Salvage-o-Matic", recs_text)
        self.assertIn("[&AgE6rgAA]", recs_text)

        # 2. Inventory & Bag Overflow Management
        self.assertIn("Inventory & Bag Overflow Management", recs_text)
        self.assertIn("Invisible Bag Staging", recs_text)
        self.assertIn("250-Stack Ingot Batching", recs_text)

    def test_four_pillar_staging_and_post_forge_decision_fork_rendering(self):
        """Verifies 4-Pillar Staging Checklist and Post-Forge Decision Fork rendering in Chapter 4 and Strategic Recommendations."""
        player_account = AccountState(
            characters=[{"name": "Kerling", "profession": "Guardian", "level": 80, "crafting": [{"discipline": "Weaponsmith", "rating": 500}, {"discipline": "Armorsmith", "rating": 500}]}],
            bank={81664: 1} # Mistlock Sanctuary Passkey
        )
        guide = self.orchestrator.run_pipeline("How do I get Twilight?", player_account)

        # 1. Verify 4-Pillar Staging Checklist in Chapter 4
        roadmap_text = "\n".join(guide.master_roadmap_phases)
        self.assertIn("4-Pillar Inventory Staging Checklist", roadmap_text)
        self.assertIn("Pillar 1: Dusk", roadmap_text)
        self.assertIn("[&AgEpZgAA]", roadmap_text)
        self.assertIn("Pillar 2: Gift of Twilight", roadmap_text)
        self.assertIn("[&AgHiEAAA]", roadmap_text)
        self.assertIn("Pillar 3: Gift of Mastery", roadmap_text)
        self.assertIn("[&AgHkEAAA]", roadmap_text)
        self.assertIn("Pillar 4: Gift of Fortune", roadmap_text)
        self.assertIn("[&AgHlEAAA]", roadmap_text)

        # 2. Verify Post-Forge Decision Fork in Chapter 4
        self.assertIn("Post-Forge Decision Fork", roadmap_text)
        self.assertIn("Path A: Legendary Armory Binding", roadmap_text)
        self.assertIn("Path B: The Eternity Commercial Arbitrage Loop", roadmap_text)
        self.assertIn("3,800g", roadmap_text)
        self.assertIn("3,230g net", roadmap_text)
        self.assertIn("Skin Retention Dynamics", roadmap_text)
        self.assertIn("Path C: Direct Trading Post Sale", roadmap_text)

        # 3. Verify Post-Forge Decision Fork in Strategic Recommendations
        recs_text = "\n".join(guide.strategic_recommendations)
        self.assertIn("Post-Forge Decision Fork", recs_text)
        self.assertIn("Option 1: Legendary Armory Binding", recs_text)
        self.assertIn("Option 2: Commercial Eternity Arbitrage", recs_text)
        self.assertIn("~3,800g Gross", recs_text)
        self.assertIn("~3,230g Net", recs_text)
        self.assertIn("Skin Retention Dynamic", recs_text)
        self.assertIn("Option 3: Direct Trading Post Sale", recs_text)

    def test_session_itinerary_parsing_and_orchestrator_dispatch(self):
        """Verifies parsing and orchestrator dispatch for SESSION_ITINERARY."""
        service = SemanticQueryService(self.store)
        parser = IntentParser(service, self.mock_llm)

        prompt = "What should I do tonight in 90 mins?"
        resolved_goal = parser.parse_intent(prompt)

        self.assertEqual(resolved_goal.goal_type, GoalType.SESSION_ITINERARY)
        self.assertEqual(resolved_goal.intent.time_budget_minutes, 90)

        # Pipeline dispatch test
        player_account = AccountState(
            materials={43772: 100},  # Quartz Crystals
            characters=[{"name": "Kerling", "profession": "Guardian", "level": 80, "crafting": [{"discipline": "Weaponsmith", "rating": 500}]}]
        )
        guide = self.orchestrator.run_pipeline(prompt, player_account)

        self.assertGreater(len(guide.session_checklist), 0)
        self.assertGreater(len(guide.strategic_recommendations), 0)
        total_time = sum(step.estimated_time_minutes for step in guide.session_checklist)
        self.assertLessEqual(total_time, 90)
        self.assertIn("utilization", guide.executive_summary.lower())
        # Check waypoint exists on scheduled tasks
        self.assertTrue(any(step.chat_code is not None for step in guide.session_checklist))

    def test_arbitrage_evaluation_parsing_and_orchestrator_dispatch(self):
        """Verifies parsing and orchestrator dispatch for ARBITRAGE_EVALUATION."""
        service = SemanticQueryService(self.store)
        parser = IntentParser(service, self.mock_llm)

        prompt = "Should I craft or buy Twilight?"
        resolved_goal = parser.parse_intent(prompt)

        self.assertEqual(resolved_goal.goal_type, GoalType.ARBITRAGE_EVALUATION)
        self.assertEqual(resolved_goal.resolved_item_name, "Twilight")
        self.assertEqual(resolved_goal.resolved_item_id, 30704)

        # Pipeline dispatch test with live Trading Post prices
        live_prices = {
            30704: {"sells": {"unit_price": 28500000}, "buys": {"unit_price": 23500000}},
            29185: {"sells": {"unit_price": 1800000}, "buys": {"unit_price": 1500000}},
        }
        guide = self.orchestrator.run_pipeline(prompt, AccountState(), live_tp_prices=live_prices)

        self.assertEqual(guide.goal_name, "Twilight")
        self.assertIn("Arbitrage Evaluation", guide.executive_summary)
        self.assertIn("Recommended Action", guide.executive_summary)
        self.assertGreater(len(guide.strategic_recommendations), 0)
        self.assertTrue(any("Precursor Strategy" in r for r in guide.strategic_recommendations))
        self.assertGreater(len(guide.session_checklist), 0)

    def test_prerequisite_audit_parsing_and_orchestrator_dispatch(self):
        """Verifies parsing and orchestrator dispatch for PREREQUISITE_AUDIT."""
        service = SemanticQueryService(self.store)
        parser = IntentParser(service, self.mock_llm)

        prompt = "Check my masteries for Nevermore"
        resolved_goal = parser.parse_intent(prompt)

        self.assertEqual(resolved_goal.goal_type, GoalType.PREREQUISITE_AUDIT)
        self.assertEqual(resolved_goal.resolved_item_name, "Nevermore")
        self.assertEqual(resolved_goal.resolved_item_id, 71383)

        # Pipeline dispatch test on account missing masteries
        player_account = AccountState(masteries={})
        guide = self.orchestrator.run_pipeline(prompt, player_account)

        self.assertEqual(guide.goal_name, "Nevermore")
        self.assertIn("Prerequisite Audit", guide.executive_summary)
        self.assertGreater(len(guide.strategic_recommendations), 0)
        # Check that masteries are flagged
        recs_text = " ".join(guide.strategic_recommendations)
        self.assertTrue("Mastery" in recs_text or "Masteries" in recs_text)
        self.assertGreater(len(guide.session_checklist), 0)
        self.assertTrue(any("Train Mastery" in step.title for step in guide.session_checklist))

    def test_currency_opportunity_cost_parsing_and_orchestrator_dispatch(self):
        """Verifies parsing and orchestrator dispatch for CURRENCY_OPPORTUNITY_COST."""
        service = SemanticQueryService(self.store)
        parser = IntentParser(service, self.mock_llm)

        prompt = "Best use of my Astral Acclaim"
        resolved_goal = parser.parse_intent(prompt)

        self.assertEqual(resolved_goal.goal_type, GoalType.CURRENCY_OPPORTUNITY_COST)
        self.assertEqual(resolved_goal.currency_name, "Astral Acclaim")
        self.assertIn(resolved_goal.currency_id, (63, 68))

        # Pipeline dispatch test
        player_account = AccountState(wallet={68: 800, 63: 800})
        guide = self.orchestrator.run_pipeline(prompt, player_account)

        self.assertEqual(guide.goal_name, "Astral Acclaim")
        self.assertIn("Opportunity Cost", guide.executive_summary)
        self.assertIn("Recommended disposition", guide.executive_summary)
        self.assertGreater(len(guide.strategic_recommendations), 0)
        self.assertTrue(any("Direct Exchange Value" in r for r in guide.strategic_recommendations))
        self.assertGreater(len(guide.session_checklist), 0)


if __name__ == "__main__":
    unittest.main()
