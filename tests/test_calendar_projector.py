"""Unit tests for Longitudinal Calendar Completion Projector in PathSolver."""

import unittest
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine, AccountState
from engine.path_solver import (
    PathSolver,
    ScheduledSessionTask,
    DailySessionItinerary,
    schedule_daily_session_itinerary
)


class TestCalendarProjector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(cls.store)
        cls.solver = PathSolver(cls.store)

    def test_daily_ascended_calendar_projection(self):
        """Verifies that missing 50 Provisioner Tokens projects 17 calendar days and a valid target date."""
        account = AccountState(
            materials={19721: 100}
        )
        report = self.diff_engine.compute_diff(goal_item_id=91505, account=account)  # Legendary Sigil (50 Provisioner Tokens)
        plan = self.solver.solve_optimal_path(diff_report=report, account=account)

        self.assertGreater(plan.estimated_completion_days, 0)
        self.assertEqual(plan.estimated_completion_days, 17)
        self.assertIsNotNone(plan.estimated_completion_date)
        self.assertIn("Provisioner Tokens", plan.primary_time_gate_bottleneck)

    def test_daily_session_dataclasses_structure(self):
        """Verifies ScheduledSessionTask and DailySessionItinerary dataclasses follow exact required schema."""
        task = ScheduledSessionTask(
            id="test_task",
            title="Test Task",
            category="QUARTZ_CHARGING",
            estimated_duration_minutes=2,
            waypoint_code="[&BPwCAAA=]",
            location_name="Krait Obelisk, Lion's Arch",
            instructions="Charge quartz at Place of Power",
            required_inputs={"item_id": 43772, "name": "Quartz Crystal", "count": 25},
            reward_output={"item_id": 43773, "name": "Charged Quartz Crystal", "count": 1},
            priority_weight=80.0,
            character_name="Kerling"
        )
        self.assertEqual(task.id, "test_task")
        self.assertEqual(task.category, "QUARTZ_CHARGING")
        self.assertEqual(task.estimated_duration_minutes, 2)
        self.assertEqual(task.waypoint_code, "[&BPwCAAA=]")
        self.assertEqual(task.character_name, "Kerling")

        itinerary = DailySessionItinerary(
            goal_item_id=30704,
            goal_name="Twilight",
            time_budget_minutes=90,
            total_scheduled_minutes=45,
            tasks=[task],
            time_utilization_pct=50.0,
            summary="Tonight's 45-minute session scheduled for Twilight"
        )
        self.assertEqual(itinerary.goal_item_id, 30704)
        self.assertEqual(itinerary.goal_name, "Twilight")
        self.assertEqual(itinerary.time_budget_minutes, 90)
        self.assertEqual(itinerary.total_scheduled_minutes, 45)
        self.assertEqual(itinerary.time_utilization_pct, 50.0)
        self.assertEqual(len(itinerary.tasks), 1)

    def test_schedule_daily_session_twilight_gen1_90min(self):
        """Verifies 90-minute session for Gen 1 (Twilight) prioritizes Anomaly & Clovers while excluding Leivas/Provisioners."""
        account = AccountState(
            characters=[{
                "name": "Kerling",
                "crafting": [{"discipline": "Weaponsmith", "rating": 500, "active": True}]
            }]
        )
        itinerary = self.solver.schedule_daily_session_itinerary(
            goal_item_id=30704,
            time_budget_minutes=90,
            account_state=account
        )
        self.assertEqual(itinerary.goal_item_id, 30704)
        self.assertEqual(itinerary.goal_name, "Twilight")
        self.assertEqual(itinerary.total_scheduled_minutes, 45)
        self.assertEqual(itinerary.time_utilization_pct, 50.0)
        self.assertEqual(len(itinerary.tasks), 4)

        categories = [t.category for t in itinerary.tasks]
        self.assertEqual(categories, ["QUARTZ_CHARGING", "DAILY_REFINEMENT", "WORLD_BOSS_ANOMALY", "DAILY_FRACTAL_CLOVERS"])
        self.assertNotIn("WEEKLY_LEIVAS", categories)
        self.assertNotIn("PROVISIONER_TOKEN", categories)

        # Verify waypoint codes
        quartz_task = next(t for t in itinerary.tasks if t.category == "QUARTZ_CHARGING")
        self.assertEqual(quartz_task.waypoint_code, "[&BPwCAAA=]")
        self.assertEqual(quartz_task.estimated_duration_minutes, 2)

        anomaly_task = next(t for t in itinerary.tasks if t.category == "WORLD_BOSS_ANOMALY")
        self.assertEqual(anomaly_task.estimated_duration_minutes, 10)
        self.assertIn("Mystic Coin", anomaly_task.reward_output["name"])

        # Character assignment for refinement
        refinement_task = next(t for t in itinerary.tasks if t.category == "DAILY_REFINEMENT")
        self.assertEqual(refinement_task.character_name, "Kerling")

    def test_schedule_daily_session_knapsack_30min_tight_budget(self):
        """Verifies knapsack priority scheduler selects high-value fast activities (15 min) over single 30m task."""
        account = AccountState()
        itinerary = self.solver.schedule_daily_session_itinerary(
            goal_item_id=30704,
            time_budget_minutes=30,
            account_state=account
        )
        self.assertLessEqual(itinerary.total_scheduled_minutes, 30)
        self.assertEqual(itinerary.total_scheduled_minutes, 15)
        self.assertEqual(itinerary.time_utilization_pct, 50.0)

        categories = [t.category for t in itinerary.tasks]
        self.assertIn("QUARTZ_CHARGING", categories)
        self.assertIn("DAILY_REFINEMENT", categories)
        self.assertIn("WORLD_BOSS_ANOMALY", categories)
        self.assertNotIn("DAILY_FRACTAL_CLOVERS", categories)

    def test_schedule_daily_session_nevermore_gen2_provisioner_tokens(self):
        """Verifies Gen 2 (Nevermore) schedules Provisioner Tokens (15 min) and respects logical ordering."""
        account = AccountState()
        itinerary = self.solver.schedule_daily_session_itinerary(
            goal_item_id=71383,
            time_budget_minutes=90,
            account_state=account
        )
        self.assertEqual(itinerary.goal_name, "Nevermore")
        self.assertEqual(itinerary.total_scheduled_minutes, 60)
        self.assertEqual(itinerary.time_utilization_pct, 66.7)

        categories = [t.category for t in itinerary.tasks]
        self.assertIn("PROVISIONER_TOKEN", categories)
        self.assertNotIn("WEEKLY_LEIVAS", categories)

        prov_task = next(t for t in itinerary.tasks if t.category == "PROVISIONER_TOKEN")
        self.assertEqual(prov_task.waypoint_code, "[&BAwEAAA=]")
        self.assertEqual(prov_task.estimated_duration_minutes, 15)

        # Logical order check
        self.assertEqual(categories, ["QUARTZ_CHARGING", "DAILY_REFINEMENT", "WORLD_BOSS_ANOMALY", "PROVISIONER_TOKEN", "DAILY_FRACTAL_CLOVERS"])

    def test_schedule_daily_session_aurenes_bite_gen3_leivas(self):
        """Verifies Gen 3 (Aurene's Bite) schedules Leivas ASS (5 min, [&BEEPAAA=]) and excludes Provisioner Tokens."""
        account = AccountState()
        itinerary = self.solver.schedule_daily_session_itinerary(
            goal_item_id=96356,
            time_budget_minutes=90,
            account_state=account
        )
        self.assertEqual(itinerary.goal_name, "Aurene's Bite")
        self.assertEqual(itinerary.total_scheduled_minutes, 50)
        self.assertEqual(itinerary.time_utilization_pct, 55.6)

        categories = [t.category for t in itinerary.tasks]
        self.assertIn("WEEKLY_LEIVAS", categories)
        self.assertNotIn("PROVISIONER_TOKEN", categories)

        leivas_task = next(t for t in itinerary.tasks if t.category == "WEEKLY_LEIVAS")
        self.assertEqual(leivas_task.waypoint_code, "[&BEEPAAA=]")
        self.assertEqual(leivas_task.estimated_duration_minutes, 5)

        # Logical order check
        self.assertEqual(categories, ["QUARTZ_CHARGING", "DAILY_REFINEMENT", "WORLD_BOSS_ANOMALY", "WEEKLY_LEIVAS", "DAILY_FRACTAL_CLOVERS"])

    def test_schedule_daily_session_filter_completed_tasks(self):
        """Verifies that activities already completed today (in daily_crafting or world_bosses) are filtered out."""
        account = AccountState(
            daily_crafting=["charged_quartz_crystal"],
            world_bosses=["ley_line_anomaly"]
        )
        itinerary = self.solver.schedule_daily_session_itinerary(
            goal_item_id=30704,
            time_budget_minutes=90,
            account_state=account
        )
        categories = [t.category for t in itinerary.tasks]
        self.assertNotIn("QUARTZ_CHARGING", categories)
        self.assertNotIn("WORLD_BOSS_ANOMALY", categories)
        self.assertIn("DAILY_REFINEMENT", categories)
        self.assertIn("DAILY_FRACTAL_CLOVERS", categories)
        self.assertEqual(itinerary.total_scheduled_minutes, 33)

    def test_schedule_daily_session_active_events_boost(self):
        """Verifies that active event timers boost activity priority weight."""
        account = AccountState()
        itinerary_normal = self.solver.schedule_daily_session_itinerary(
            goal_item_id=30704,
            time_budget_minutes=90,
            account_state=account
        )
        itinerary_active = self.solver.schedule_daily_session_itinerary(
            goal_item_id=30704,
            time_budget_minutes=90,
            account_state=account,
            active_events=["ley_line_anomaly"]
        )
        anomaly_normal = next(t for t in itinerary_normal.tasks if t.category == "WORLD_BOSS_ANOMALY")
        anomaly_active = next(t for t in itinerary_active.tasks if t.category == "WORLD_BOSS_ANOMALY")
        self.assertGreater(anomaly_active.priority_weight, anomaly_normal.priority_weight)

    def test_schedule_daily_session_obsidian_armor(self):
        """Verifies Obsidian Armor itinerary includes Wizard's Vault Astral Acclaim / Clovers and Provisioner Tokens."""
        account = AccountState()
        itinerary = self.solver.schedule_daily_session_itinerary(
            goal_item_id=101001,  # Obsidian Helm
            time_budget_minutes=90,
            account_state=account
        )
        self.assertIn("Obsidian", itinerary.goal_name)
        categories = [t.category for t in itinerary.tasks]
        self.assertIn("DAILY_FRACTAL_CLOVERS", categories)
        self.assertIn("PROVISIONER_TOKEN", categories)
        self.assertNotIn("WEEKLY_LEIVAS", categories)

    def test_module_level_schedule_daily_session_itinerary(self):
        """Verifies module-level schedule_daily_session_itinerary convenience function."""
        account = AccountState()
        itinerary = schedule_daily_session_itinerary(
            goal_item_id=30704,
            time_budget_minutes=60,
            account_state=account,
            graph_store=self.store
        )
        self.assertEqual(itinerary.goal_name, "Twilight")
        self.assertEqual(itinerary.total_scheduled_minutes, 45)
        self.assertEqual(itinerary.time_utilization_pct, 75.0)


if __name__ == "__main__":
    unittest.main()
