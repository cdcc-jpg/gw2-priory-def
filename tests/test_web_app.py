"""Unit tests for Project Priory Flask Web GUI."""

import unittest
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock
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

    def setUp(self):
        self._orig_account = web_module.ACTIVE_ACCOUNT
        self._orig_env_key = os.environ.get("GW2_API_KEY")

    def tearDown(self):
        web_module.ACTIVE_ACCOUNT = self._orig_account
        if self._orig_env_key is not None:
            os.environ["GW2_API_KEY"] = self._orig_env_key
        else:
            os.environ.pop("GW2_API_KEY", None)

    def test_index_page(self):
        """Verifies that the root index page renders successfully with navigation tabs."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Priory Grimoire", html)
        self.assertIn("pages-spread", html)
        self.assertIn("tab-library", html)
        self.assertIn("tab-guide", html)
        self.assertIn("tab-recipe", html)
        self.assertIn("tab-plan", html)
        self.assertIn("tab-chapters-menu", html)
        self.assertIn("priory-side-drawer", html)
        self.assertIn("drawer-account-name", html)
        self.assertIn("drawer-api-key-masked", html)
        self.assertIn("drawer-api-key-input", html)
        self.assertIn("btn-toggle-key-visibility", html)
        self.assertIn("btn-apply-api-key", html)
        self.assertIn("btn-reset-api-key", html)
        self.assertIn("drawer-api-key-feedback", html)

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
        self.assertIn("account_name", data)
        self.assertEqual(data["account_name"], "Authenticated Scholar")

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

    def test_api_query_comparative_ranking_accessory(self):
        """Verifies that /api/query processes comparative inquiries like 'Which accessory can I get the fastest?'."""
        response = self.client.post(
            "/api/query",
            data=json.dumps({"query": "Which accessory can I get the fastest?"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data.get("success"))
        self.assertIn("guide", data)
        guide = data["guide"]
        self.assertTrue(guide["goal_name"].startswith("Closest Legendary Accessory:"))
        self.assertTrue("Aurora" in guide["goal_name"] or "Vision" in guide["goal_name"])
        # Verify that strategic recommendations include the leaderboard
        recs = guide.get("strategic_recommendations", [])
        self.assertTrue(any("Leaderboard" in r or "Aurora" in r or "Vision" in r for r in recs))

    @patch("web.app.GW2ApiClient")
    def test_api_account_refresh_custom_key(self, mock_client_cls):
        """Verifies POST /api/account/refresh switches to custom API key and returns updated snapshot."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.fetch_account_snapshot = AsyncMock(return_value=AccountState(
            account_name="Commander.5678",
            materials={19721: 100},
            wallet={1: 50000},
            legendary_armory={91505: 1}
        ))

        response = self.client.post(
            "/api/account/refresh",
            data=json.dumps({"api_key": "ABCDEF12-3456-7890-ABCD-EF1234567890"}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.get_data(as_text=True))
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("account_name"), "Commander.5678")
        self.assertEqual(data.get("materials_count"), 1)
        self.assertEqual(data.get("armory_count"), 1)
        self.assertEqual(data.get("wallet"), {"1": 50000} if "1" in data.get("wallet", {}) else {1: 50000})
        self.assertEqual(data.get("api_key_masked"), "ABCDEF...7890")
        self.assertEqual(web_module.ACTIVE_ACCOUNT.account_name, "Commander.5678")
        self.assertEqual(os.environ.get("GW2_API_KEY"), "ABCDEF12-3456-7890-ABCD-EF1234567890")

    @patch("web.app.get_live_account")
    def test_api_account_refresh_reset(self, mock_get_live):
        """Verifies POST /api/account/refresh with reset=True restores default key and state."""
        mock_get_live.return_value = AccountState(
            account_name="DefaultScholar.1234",
            materials={19675: 10},
            wallet={63: 100},
            legendary_armory={}
        )
        old_default = web_module.DEFAULT_GW2_API_KEY
        web_module.DEFAULT_GW2_API_KEY = "ORIGIN-1234-5678-90AB-CDEF12345678"
        try:
            response = self.client.post(
                "/api/account/refresh",
                data=json.dumps({"reset": True}),
                content_type="application/json"
            )
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.get_data(as_text=True))
            self.assertTrue(data.get("success"))
            self.assertTrue(data.get("reset"))
            self.assertEqual(data.get("account_name"), "DefaultScholar.1234")
            self.assertEqual(data.get("materials_count"), 1)
            self.assertEqual(data.get("armory_count"), 0)
            self.assertEqual(data.get("api_key_masked"), "ORIGIN...5678")
            self.assertEqual(os.environ.get("GW2_API_KEY"), "ORIGIN-1234-5678-90AB-CDEF12345678")
        finally:
            web_module.DEFAULT_GW2_API_KEY = old_default

    @patch("web.app.GW2ApiClient")
    def test_api_account_refresh_invalid_key(self, mock_client_cls):
        """Verifies POST /api/account/refresh handles invalid API key errors gracefully."""
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        from ingestion.gw2_api import InsufficientPermissionsError
        mock_instance.fetch_account_snapshot = AsyncMock(
            side_effect=InsufficientPermissionsError("Invalid API key: Unauthorized")
        )

        response = self.client.post(
            "/api/account/refresh",
            data=json.dumps({"api_key": "INVALID-KEY-0000"}),
            content_type="application/json"
        )
        self.assertIn(response.status_code, [400, 401, 500])
        data = json.loads(response.get_data(as_text=True))
        self.assertFalse(data.get("success"))
        self.assertIn("error", data)

    def test_api_account_refresh_empty_key(self):
        """Verifies POST /api/account/refresh rejects missing or empty key."""
        response = self.client.post(
            "/api/account/refresh",
            data=json.dumps({"api_key": "   "}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.get_data(as_text=True))
        self.assertFalse(data.get("success"))


if __name__ == "__main__":
    unittest.main()

