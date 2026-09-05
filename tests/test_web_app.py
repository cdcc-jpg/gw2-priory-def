"""Unit tests for Project Priory Flask Web GUI."""

import unittest
import json
import web.app as web_module
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState
from agent.orchestrator import PrioryAgentOrchestrator
from agent.llm_client import RuleBasedMockLLMClient


class TestPrioryWebApp(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        store = PrioryGraphStore()
        store.load_all()
        llm = RuleBasedMockLLMClient()
        web_module.GRAPH_STORE = store
        web_module.ORCHESTRATOR = PrioryAgentOrchestrator(graph_store=store, llm_client=llm)
        web_module.ACTIVE_ACCOUNT = AccountState(
            materials={19675: 50, 19721: 180},
            bank={29185: 1},
            wallet={29: 440, 63: 250, 45: 5000, 23: 1200, 3: 150},
            legendary_armory={91505: 4},
            disciplines={"weaponsmith": 500}
        )
        web_module.app.config["TESTING"] = True
        cls.client = web_module.app.test_client()

    def test_index_page(self):
        """Verifies that the root index page renders successfully with navigation tabs."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Priory Grimoire", html)
        self.assertIn("pages-spread", html)
        self.assertIn("tab-planner", html)
        self.assertIn("tab-arbitrage", html)
        self.assertIn("tab-prereqs", html)

    def test_grimoire_3d_page(self):
        """Verifies that the Next-Gen WebGL 3D Grimoire page renders successfully."""
        response = self.client.get("/3d")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("The Priory Grimoire", html)
        self.assertIn("webgl-container", html)
        self.assertIn("grimoire_3d.js", html)

    def test_api_status(self):
        """Verifies that /api/status returns knowledge graph and wallet telemetry with live canonical IDs (AA: 63, Prov: 29)."""
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data.get("status"), "ready")
        self.assertGreater(data.get("triples_loaded", 0), 9000)
        self.assertIn("wallet", data)
        self.assertEqual(data["wallet"]["astral_acclaim"], 250)
        self.assertEqual(data["wallet"]["provisioner_tokens"], 440)
        self.assertIn("llm_provider", data)

    def test_api_query_empty(self):
        """Verifies that /api/query returns 400 on empty input."""
        response = self.client.post(
            "/api/query",
            data=json.dumps({"query": ""}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_api_query_progression(self):
        """Verifies that /api/query processes a crafting query into a structured guide."""
        response = self.client.post(
            "/api/query",
            data=json.dumps({"query": "How do I craft Twilight?"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data.get("success"))
        self.assertIn("guide", data)
        guide = data["guide"]
        self.assertEqual(guide["goal_name"], "Twilight")
        self.assertGreater(guide["readiness_percentage"], 0)
        self.assertGreater(len(guide["session_checklist"]), 0)

    def test_api_solver_itinerary(self):
        """Verifies POST /api/solver/itinerary computes 0/1 knapsack itinerary."""
        response = self.client.post(
            "/api/solver/itinerary",
            data=json.dumps({"time_budget_minutes": 60, "goal_item_id": 30704}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data.get("success"))
        self.assertIn("itinerary", data)
        itin = data["itinerary"]
        self.assertEqual(itin["goal_item_id"], 30704)
        self.assertEqual(itin["goal_name"], "Twilight")
        self.assertEqual(itin["time_budget_minutes"], 60)
        self.assertGreater(len(itin["tasks"]), 0)

    def test_api_solver_arbitrage(self):
        """Verifies POST /api/solver/arbitrage computes buy vs craft vs vault matrix."""
        response = self.client.post(
            "/api/solver/arbitrage",
            data=json.dumps({"goal_item_id": 30704}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data.get("success"))
        self.assertIn("arbitrage", data)
        arb = data["arbitrage"]
        self.assertEqual(arb["goal_item_id"], 30704)
        self.assertIn(arb["recommended_action"], ["CRAFT_FOR_SELF", "CRAFT_FOR_PROFIT", "BUY_FINISHED_DIRECT"])
        self.assertIn("net_sell_if_sold", arb)
        self.assertIn("profit_margin_if_sold", arb)
        self.assertIn("precursor_strategy", arb)

    def test_api_solver_prerequisites(self):
        """Verifies POST /api/solver/prerequisites audits account masteries and readiness."""
        response = self.client.post(
            "/api/solver/prerequisites",
            data=json.dumps({"goal_item_id": 30704}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data.get("success"))
        self.assertIn("prerequisites", data)
        prereqs = data["prerequisites"]
        self.assertEqual(prereqs["goal_item_id"], 30704)
        self.assertIn("can_craft_immediately", prereqs)
        self.assertIn("has_world_completion", prereqs)

    def test_api_solver_opportunity_cost(self):
        """Verifies POST /api/solver/opportunity-cost evaluates currency trade-offs."""
        response = self.client.post(
            "/api/solver/opportunity-cost",
            data=json.dumps({"currency_id": 63, "quantity": 100}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data.get("success"))
        self.assertIn("opportunity_cost", data)
        opp = data["opportunity_cost"]
        self.assertEqual(opp["item_id"], 63)
        self.assertIn("optimal_role_disposition", opp)


if __name__ == "__main__":
    unittest.main()
