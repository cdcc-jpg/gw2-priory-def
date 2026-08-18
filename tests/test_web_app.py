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
            wallet={35: 440, 68: 250, 45: 5000, 23: 1200, 3: 150},
            legendary_armory={91505: 4},
            disciplines={"weaponsmith": 500}
        )
        web_module.app.config["TESTING"] = True
        cls.client = web_module.app.test_client()

    def test_index_page(self):
        """Verifies that the root index page renders successfully."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("PRIORY GRIMOIRE", html)
        self.assertIn("Account Essence Snapshot", html)

    def test_api_status(self):
        """Verifies that /api/status returns knowledge graph and wallet telemetry."""
        response = self.client.get("/api/status")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertEqual(data.get("status"), "ready")
        self.assertGreater(data.get("triples_loaded", 0), 9000)
        self.assertIn("wallet", data)
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


if __name__ == "__main__":
    unittest.main()
