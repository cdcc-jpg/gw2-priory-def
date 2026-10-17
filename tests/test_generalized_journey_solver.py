"""Comprehensive unit tests for the Generalized Legendary Journey Solver.

Verifies ontology-driven resolution across:
- Gen 1: Twilight (30704), Sunrise (30703), Bolt (30699)
- Gen 2: Nevermore (71383)
- Gen 3: Aurene's Bite (96356)
- PathSolver.solve_journey_plan & _evaluate_precursor_buy_vs_craft
- PrioryAgentOrchestrator & GuideGenerator multi-weapon routing
"""

import unittest
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState, AccountDiffEngine
from engine.path_solver import PathSolver
from engine.twilight_journey_solver import (
    TwilightJourneySolver,
    LegendaryJourneySolver,
    TwilightJourneyPlan,
    LegendaryJourneyPlan,
    PlaySessionStep,
    solve_twilight_journey,
    solve_legendary_journey,
)
from agent.orchestrator import PrioryAgentOrchestrator
from agent.llm_client import RuleBasedMockLLMClient


class TestGeneralizedJourneySolver(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(cls.store)
        cls.path_solver = PathSolver(cls.store)
        cls.journey_solver = LegendaryJourneySolver(cls.store, cls.diff_engine, cls.path_solver)
        cls.orchestrator = PrioryAgentOrchestrator(
            graph_store=cls.store,
            llm_client=RuleBasedMockLLMClient(),
        )

    def test_aliases_and_backward_compatibility(self):
        """Verifies LegendaryJourneySolver and LegendaryJourneyPlan aliases and default 30704 behavior."""
        self.assertIs(LegendaryJourneySolver, TwilightJourneySolver)
        self.assertIs(LegendaryJourneyPlan, TwilightJourneyPlan)

        account = AccountState(
            materials={19675: 20},
            wallet={1: 2000000},
            characters=[{"name": "Kerling", "profession": "Guardian", "level": 80}],
            mount_types=["skyscale", "raptor"],
        )
        plan = solve_twilight_journey(account=account, store=self.store, time_budget_minutes=60)
        self.assertEqual(plan.target_item_id, 30704)
        self.assertEqual(plan.target_item_name, "Twilight")
        self.assertEqual(plan.generation, "GEN1")
        self.assertEqual(plan.precursor_id, 29185)
        self.assertEqual(plan.precursor_name, "Dusk")
        self.assertEqual(plan.required_clovers, 77)
        self.assertEqual(plan.required_t6_per_type, 250)
        self.assertEqual(plan.required_t6_total, 2000)
        self.assertEqual(len(plan.pillars), 4)
        self.assertEqual(len(plan.chapters), 4)
        self.assertEqual(plan.steps, plan.session_itinerary)

    def test_gen1_sunrise_and_bolt_ontology_resolution(self):
        """Verifies Gen 1 Sunrise (30703) and Bolt (30699) resolve precursors, gifts, and chapters dynamically."""
        account = AccountState(
            materials={19675: 10},
            wallet={1: 3000000, 68: 500},
            characters=[{"name": "Sara Loy", "profession": "Mesmer", "level": 80}],
            mount_types=["skyscale", "raptor"],
        )

        # 1. Sunrise (30703) -> Precursor Dawn (29184), Gift of Sunrise (19647)
        sunrise_plan = self.path_solver.solve_journey_plan(
            target_item_id=30703,
            account=account,
            time_budget_minutes=75,
        )
        self.assertEqual(sunrise_plan.target_item_id, 30703)
        self.assertEqual(sunrise_plan.target_item_name, "Sunrise")
        self.assertEqual(sunrise_plan.generation, "GEN1")
        self.assertEqual(sunrise_plan.precursor_id, 29184)
        self.assertEqual(sunrise_plan.precursor_name, "Dawn")
        self.assertEqual(sunrise_plan.tribute_gift_name, "Gift of Fortune")
        self.assertEqual(sunrise_plan.mastery_gift_name, "Gift of Mastery")
        self.assertEqual(sunrise_plan.specific_gift_name, "Gift of Sunrise")
        self.assertEqual(sunrise_plan.required_clovers, 77)
        self.assertEqual(sunrise_plan.required_t6_per_type, 250)
        self.assertEqual(sunrise_plan.required_t6_total, 2000)
        self.assertEqual(sunrise_plan.pillars[0].pillar_name, "Precursor: Dawn")
        self.assertEqual(sunrise_plan.pillars[3].pillar_name, "Gift of Sunrise")
        self.assertIn("Dawn", sunrise_plan.chapters[0].chapter_title)
        self.assertNotIn("Dusk", sunrise_plan.chapters[0].chapter_title)

        # 2. Bolt (30699) -> Precursor Zap (29167), Gift of Bolt (19655)
        bolt_plan = solve_legendary_journey(
            target_item_id=30699,
            account=account,
            store=self.store,
            time_budget_minutes=60,
        )
        self.assertEqual(bolt_plan.target_item_id, 30699)
        self.assertEqual(bolt_plan.target_item_name, "Bolt")
        self.assertEqual(bolt_plan.generation, "GEN1")
        self.assertEqual(bolt_plan.precursor_id, 29167)
        self.assertEqual(bolt_plan.precursor_name, "Zap")
        self.assertEqual(bolt_plan.specific_gift_name, "Gift of Bolt")
        self.assertEqual(bolt_plan.required_clovers, 77)
        self.assertEqual(bolt_plan.required_t6_total, 2000)
        self.assertEqual(bolt_plan.pillars[0].pillar_name, "Precursor: Zap")
        self.assertEqual(bolt_plan.pillars[3].pillar_name, "Gift of Bolt")

    def test_gen2_nevermore_ontology_resolution(self):
        """Verifies Gen 2 Nevermore (71383) resolves The Raven Staff (71384), Mystic Tribute, Maguuma Mastery, 77 clovers, and 1600 T6."""
        account = AccountState(
            materials={19675: 30},
            wallet={1: 1500000},
            characters=[{"name": "Skuta Rantakallio", "profession": "Ranger", "level": 80}],
            mount_types=["skyscale", "raptor"],
            expansion_access=["GuildWars2", "HeartOfThorns", "PathOfFire"],
        )

        nevermore_plan = self.journey_solver.solve_legendary_journey(
            target_item_id=71383,
            account=account,
            time_budget_minutes=90,
        )
        self.assertEqual(nevermore_plan.target_item_id, 71383)
        self.assertEqual(nevermore_plan.target_item_name, "Nevermore")
        self.assertEqual(nevermore_plan.generation, "GEN2")
        self.assertEqual(nevermore_plan.precursor_id, 71384)
        self.assertEqual(nevermore_plan.precursor_name, "The Raven Staff")
        self.assertEqual(nevermore_plan.tribute_gift_name, "Mystic Tribute")
        self.assertEqual(nevermore_plan.mastery_gift_name, "Gift of Maguuma Mastery")
        self.assertEqual(nevermore_plan.specific_gift_name, "Gift of Nevermore")
        self.assertEqual(nevermore_plan.required_clovers, 77)
        self.assertEqual(nevermore_plan.required_t6_per_type, 200)
        self.assertEqual(nevermore_plan.required_t6_total, 1600)

        # Verify Heart of Maguuma exploration regions
        region_names = [r.region_name for r in nevermore_plan.exploration_plan]
        self.assertIn("Verdant Brink", region_names)
        self.assertIn("Auric Basin", region_names)
        self.assertIn("Tangled Depths", region_names)
        self.assertIn("Dragon's Stand", region_names)

        # Verify Spiritwood daily time gate is detected
        self.assertTrue(
            any("Spiritwood" in (tg.get("name", "") if isinstance(tg, dict) else str(tg)) for tg in nevermore_plan.time_gates)
        )

        # Verify PathSolver._evaluate_precursor_buy_vs_craft recognizes account-bound Gen 2 precursor
        prec_eval = self.path_solver._evaluate_precursor_buy_vs_craft(71384, account_state=account)
        self.assertTrue(prec_eval["is_account_bound"])
        self.assertEqual(prec_eval["recommended_option"], "HOBBS_COLLECTION")

    def test_gen3_aurenes_bite_ontology_resolution(self):
        """Verifies Gen 3 Aurene's Bite (96356) resolves Dragon's Bite (96357), Draconic Tribute, Jade Mastery, 38 clovers, and 800 T6."""
        account = AccountState(
            materials={19675: 19},  # 19/38 clovers = 50%
            wallet={1: 2000000, 68: 1250},
            characters=[{"name": "Skuta Rantakallio", "profession": "Ranger", "level": 80}],
            mount_types=["skyscale", "raptor"],
            expansion_access=["GuildWars2", "EndOfDragons"],
        )

        aurene_plan = self.journey_solver.solve_legendary_journey(
            target_item_id=96356,
            account=account,
            time_budget_minutes=90,
        )
        self.assertEqual(aurene_plan.target_item_id, 96356)
        self.assertEqual(aurene_plan.target_item_name, "Aurene's Bite")
        self.assertEqual(aurene_plan.generation, "GEN3")
        self.assertEqual(aurene_plan.precursor_id, 96357)
        self.assertEqual(aurene_plan.precursor_name, "Dragon's Bite")
        self.assertEqual(aurene_plan.tribute_gift_name, "Draconic Tribute")
        self.assertEqual(aurene_plan.mastery_gift_name, "Gift of Jade Mastery")
        self.assertEqual(aurene_plan.specific_gift_name, "Gift of Aurene's Bite")
        self.assertEqual(aurene_plan.required_clovers, 38)
        self.assertEqual(aurene_plan.required_t6_per_type, 100)
        self.assertEqual(aurene_plan.required_t6_total, 800)

        # Verify Cantha exploration regions
        region_names = [r.region_name for r in aurene_plan.exploration_plan]
        self.assertIn("Seitung Province", region_names)
        self.assertIn("New Kaineng City", region_names)
        self.assertIn("The Echovald Wilds", region_names)
        self.assertIn("Dragon's End", region_names)

        # Verify weekly Antique Summoning Stone time gate is detected
        self.assertTrue(
            any("Antique Summoning Stone" in (tg.get("name", "") if isinstance(tg, dict) else str(tg)) for tg in aurene_plan.time_gates)
        )

    def test_excluded_modes_and_time_budget_constraints_across_weapons(self):
        """Verifies excluded_modes filtering and time_budget_minutes cap for non-Twilight weapons."""
        account = AccountState(
            materials={},
            wallet={1: 1000000},
            characters=[{"name": "Sara Loy", "profession": "Mesmer", "level": 80}],
            mount_types=["raptor"],
        )
        plan = self.journey_solver.solve_legendary_journey(
            target_item_id=30703,  # Sunrise
            account=account,
            time_budget_minutes=45,
            excluded_modes=["WvW", "Dungeon"],
        )
        total_mins = sum(step.estimated_minutes for step in plan.session_itinerary)
        self.assertLessEqual(total_mins, 45)
        for step in plan.session_itinerary:
            self.assertNotIn((step.game_mode or "").lower(), {"wvw", "dungeon"})

    def test_orchestrator_and_guide_generator_multi_weapon_routing(self):
        """Verifies PrioryAgentOrchestrator routes Gen 1 Sunrise, Gen 2 Nevermore, and Gen 3 Aurene's Bite through LegendaryJourneySolver."""
        account = AccountState(
            materials={19675: 15},
            wallet={1: 2500000},
            characters=[{"name": "Kerling", "profession": "Guardian", "level": 80}],
            mount_types=["skyscale", "raptor"],
            expansion_access=["GuildWars2", "HeartOfThorns", "PathOfFire", "EndOfDragons"],
        )

        # 1. Sunrise via Orchestrator
        sunrise_guide = self.orchestrator.run_pipeline(
            "I have 60 minutes tonight to work on Sunrise.",
            account_state=account,
        )
        self.assertEqual(sunrise_guide.goal_name, "Sunrise")
        self.assertIsNotNone(sunrise_guide.twilight_journey_plan)
        self.assertEqual(sunrise_guide.twilight_journey_plan.target_item_id, 30703)
        self.assertEqual(sunrise_guide.twilight_journey_plan.precursor_name, "Dawn")
        self.assertIn("Dawn", sunrise_guide.executive_summary)

        # 2. Nevermore via Orchestrator
        nevermore_guide = self.orchestrator.run_pipeline(
            "Help me craft Nevermore tonight in 90 minutes.",
            account_state=account,
        )
        self.assertEqual(nevermore_guide.goal_name, "Nevermore")
        self.assertIsNotNone(nevermore_guide.twilight_journey_plan)
        self.assertEqual(nevermore_guide.twilight_journey_plan.target_item_id, 71383)
        self.assertEqual(nevermore_guide.twilight_journey_plan.precursor_name, "The Raven Staff")
        self.assertIn("The Raven Staff", nevermore_guide.executive_summary)
        self.assertIn("Mystic Tribute", nevermore_guide.executive_summary)

        # 3. Aurene's Bite via GuideGenerator.generate_legendary_journey_guide
        aurene_plan = self.journey_solver.solve_legendary_journey(
            target_item_id=96356,
            account=account,
            time_budget_minutes=60,
        )
        aurene_guide = self.orchestrator.guide_generator.generate_legendary_journey_guide(
            journey_plan=aurene_plan,
            account_state=account,
        )
        self.assertEqual(aurene_guide.goal_name, "Aurene's Bite")
        self.assertIn("Dragon's Bite", aurene_guide.executive_summary)
        self.assertIn("Draconic Tribute", aurene_guide.executive_summary)


if __name__ == "__main__":
    unittest.main()
