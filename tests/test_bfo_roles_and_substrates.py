"""Unit and integration tests for BFO-Lite Foundations, Punned Game Roles, and Substrate Separation."""

import unittest
from pathlib import Path
import rdflib
from rdflib import Literal, Namespace, URIRef
import pyshacl

from engine.graph_store import PrioryGraphStore, PRIORY, ROLE
from engine.semantic_query import SemanticQueryService
from engine.account_diff import AccountDiffEngine, AccountState
from engine.path_solver import PathSolver

DEF_REPO = Path(__file__).parent.parent


class TestSHACLRoleAndSubstrateConstraints(unittest.TestCase):
    """Test Suite 1: SHACL Constraints for Game Roles and Storage Substrates."""

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()

        cls.role_shape_path = DEF_REPO / "ontology" / "shapes" / "role_shape.ttl"
        cls.priory_shacl_path = DEF_REPO / "ontology" / "priory_shacl.ttl"

        cls.role_shacl_graph = rdflib.Graph()
        cls.role_shacl_graph.parse(cls.role_shape_path, format="turtle")

        cls.combined_shacl_graph = rdflib.Graph()
        cls.combined_shacl_graph.parse(cls.role_shape_path, format="turtle")
        cls.combined_shacl_graph.parse(cls.priory_shacl_path, format="turtle")

    def test_main_graph_shacl_conformance(self):
        """Validates that the main RDF knowledge graph conforms to role_shape.ttl and priory_shacl.ttl."""
        conforms, results_graph, results_text = pyshacl.validate(
            self.store.graph,
            shacl_graph=self.combined_shacl_graph,
            inference="rdfs",
            abort_on_first=False
        )
        self.assertTrue(conforms, f"SHACL validation failed on main knowledge graph:\n{results_text}")

    def test_negative_validation_illegal_account_wallet_scalar(self):
        """Validates that illegal AccountWalletScalar individuals are rejected by role_shape.ttl."""
        # 1. Missing apiWalletId
        g1 = rdflib.Graph()
        g1.bind("priory", PRIORY)
        g1.bind("role", ROLE)
        illegal_wallet_1 = URIRef("https://priory.gw2/ref/currency/IllegalWalletMissingId")
        g1.add((illegal_wallet_1, rdflib.RDF.type, PRIORY.AccountWalletScalar))
        g1.add((illegal_wallet_1, PRIORY.isContainerized, Literal(False)))
        conforms_1, _, text_1 = pyshacl.validate(g1, shacl_graph=self.role_shacl_graph, inference="rdfs")
        self.assertFalse(conforms_1, "AccountWalletScalar missing apiWalletId must fail validation.")
        self.assertIn("AccountWalletScalar must declare exactly one integer apiWalletId", text_1)

        # 2. isContainerized set to true
        g2 = rdflib.Graph()
        g2.bind("priory", PRIORY)
        g2.bind("role", ROLE)
        illegal_wallet_2 = URIRef("https://priory.gw2/ref/currency/IllegalWalletContainerized")
        g2.add((illegal_wallet_2, rdflib.RDF.type, PRIORY.AccountWalletScalar))
        g2.add((illegal_wallet_2, PRIORY.apiWalletId, Literal(999)))
        g2.add((illegal_wallet_2, PRIORY.isContainerized, Literal(True)))
        conforms_2, _, text_2 = pyshacl.validate(g2, shacl_graph=self.role_shacl_graph, inference="rdfs")
        self.assertFalse(conforms_2, "AccountWalletScalar with isContainerized=true must fail validation.")
        self.assertIn("AccountWalletScalar isContainerized must be false", text_2)

        # 3. Playing role:SalvageTarget
        g3 = rdflib.Graph()
        g3.bind("priory", PRIORY)
        g3.bind("role", ROLE)
        illegal_wallet_3 = URIRef("https://priory.gw2/ref/currency/IllegalWalletSalvageRole")
        g3.add((illegal_wallet_3, rdflib.RDF.type, PRIORY.AccountWalletScalar))
        g3.add((illegal_wallet_3, PRIORY.apiWalletId, Literal(999)))
        g3.add((illegal_wallet_3, PRIORY.isContainerized, Literal(False)))
        g3.add((illegal_wallet_3, PRIORY.playsRole, ROLE.SalvageTarget))
        conforms_3, _, text_3 = pyshacl.validate(g3, shacl_graph=self.role_shacl_graph, inference="rdfs")
        self.assertFalse(conforms_3, "AccountWalletScalar playing SalvageTarget must fail validation.")
        self.assertIn("AccountWalletScalar cannot play SalvageTarget or MarketCommodity roles", text_3)

    def test_negative_validation_illegal_disjoint_roles(self):
        """Validates that an individual simultaneously playing JunkSell and EquippedGear is rejected."""
        g = rdflib.Graph()
        g.bind("priory", PRIORY)
        g.bind("role", ROLE)
        illegal_entity = URIRef("https://priory.gw2/id/item/IllegalJunkAndGear")
        g.add((illegal_entity, rdflib.RDF.type, PRIORY.Entity))
        g.add((illegal_entity, PRIORY.playsRole, ROLE.JunkSell))
        g.add((illegal_entity, PRIORY.playsRole, ROLE.EquippedGear))

        conforms, _, results_text = pyshacl.validate(g, shacl_graph=self.role_shacl_graph, inference="rdfs")
        self.assertFalse(conforms, "Entity playing both JunkSell and EquippedGear must violate RoleDisjointnessShape.")
        self.assertIn("An entity cannot simultaneously play both JunkSell and EquippedGear roles", results_text)


class TestRoleDiscoveryAndAffordances(unittest.TestCase):
    """Test Suite 2: Dynamic Role Discovery and Economic Affordances."""

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.service = SemanticQueryService(cls.store)

    def test_currency_exchange_role_returns_both_substrates(self):
        """Verifies that role:CurrencyExchange discovery returns both wallet scalars and containerized tokens."""
        currency_items = self.service.find_items_by_role("role:CurrencyExchange")
        self.assertGreater(len(currency_items), 0, "Expected currency exchange items from graph.")

        substrates = {r["substrateType"] for r in currency_items}
        self.assertIn("priory:AccountWalletScalar", substrates)
        self.assertIn("priory:ContainerizedToken", substrates)

        wallet_scalars = [r for r in currency_items if r["substrateType"] == "priory:AccountWalletScalar"]
        container_tokens = [r for r in currency_items if r["substrateType"] == "priory:ContainerizedToken"]

        self.assertGreater(len(wallet_scalars), 0)
        self.assertGreater(len(container_tokens), 0)

        # Check expected wallet currencies (e.g. Astral Acclaim, Karma, Spirit Shard)
        wallet_names = {r["label"] for r in wallet_scalars if r.get("label")}
        self.assertTrue(any("Astral Acclaim" in name for name in wallet_names))

        # Check expected containerized barter/exchange tokens (e.g. Ectoplasm, Mystic Coin)
        container_ids = {r.get("gw2Id") for r in container_tokens if r.get("gw2Id") is not None}
        self.assertTrue(19721 in container_ids or 19976 in container_ids)

    def test_crafting_ingredient_and_precursor_roles(self):
        """Verifies role-based discovery for CraftingIngredient and Precursor roles."""
        craft_items = self.service.find_items_by_role("role:CraftingIngredient")
        self.assertGreater(len(craft_items), 0)
        craft_ids = {r.get("gw2Id") for r in craft_items if r.get("gw2Id") is not None}
        self.assertIn(19721, craft_ids, "Glob of Ectoplasm (19721) must play CraftingIngredient role.")

        precursors = self.service.find_items_by_role("role:Precursor")
        self.assertGreater(len(precursors), 0)
        precursor_ids = {r.get("gw2Id") for r in precursors if r.get("gw2Id") is not None}
        self.assertIn(30689, precursor_ids, "Dusk (30689) must play Precursor role.")

    def test_token_economic_affordances_ectoplasm(self):
        """Verifies economic affordance matrix for Glob of Ectoplasm (19721)."""
        affordances = self.service.get_token_economic_affordances(19721)

        self.assertEqual(affordances["item_id"], 19721)
        self.assertEqual(affordances["substrateType"], "priory:ContainerizedToken")
        self.assertTrue(affordances["isContainerized"])
        self.assertTrue(affordances["isSalvageable"])
        self.assertEqual(affordances["maxStackSize"], 250)

        roles = affordances["roles"]
        self.assertTrue(any("CraftingIngredient" in r for r in roles), f"Missing CraftingIngredient in {roles}")
        self.assertTrue(any("CurrencyExchange" in r for r in roles), f"Missing CurrencyExchange in {roles}")
        self.assertTrue(any("SalvageTarget" in r for r in roles), f"Missing SalvageTarget in {roles}")
        self.assertTrue(any("MarketCommodity" in r for r in roles), f"Missing MarketCommodity in {roles}")

    def test_manifested_gear_catalog(self):
        """Verifies manifested gear catalog contains weapons/armor while excluding pure ledger tokens."""
        catalog = self.service.get_manifested_gear_catalog()
        self.assertGreater(len(catalog), 0)
        catalog_ids = {r.get("gw2Id") for r in catalog if r.get("gw2Id") is not None}

        # Manifested gear must be present
        self.assertIn(30704, catalog_ids, "Twilight (30704) must be in manifested gear catalog.")
        self.assertIn(30689, catalog_ids, "Dusk (30689) must be in manifested gear catalog.")

        # Pure ledger tokens and components must be excluded
        self.assertNotIn(19675, catalog_ids, "Mystic Clover (19675) must be excluded from manifested gear.")
        self.assertNotIn(19677, catalog_ids, "Gift of Mastery (19677) must be excluded from manifested gear.")


class TestSubstrateAgnosticPurchasingPower(unittest.TestCase):
    """Test Suite 3: Substrate-Agnostic Balance Resolution."""

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.engine = AccountDiffEngine(graph_store=cls.store)

    def test_astral_acclaim_wallet_scalar_resolution(self):
        """Verifies that Astral Acclaim resolves unlocated balance from account_state.wallet[68]."""
        account = AccountState(
            wallet={68: 1350, 1: 500000},
            materials={},
            bank={},
            characters=[]
        )
        # Query by integer wallet ID
        balance_by_id = self.engine.get_available_purchasing_power(68, account)
        self.assertEqual(balance_by_id, 1350)

        # Query by prefixed IRI
        balance_by_iri = self.engine.get_available_purchasing_power("currency:AstralAcclaim", account)
        self.assertEqual(balance_by_iri, 1350)

    def test_ectoplasm_containerized_token_aggregation(self):
        """Verifies that Ectoplasm balance aggregates across materials, bank, and character inventory bags."""
        account = AccountState(
            wallet={1: 100000},
            materials={19721: 150},
            bank={19721: 60},
            characters=[
                {
                    "name": "MuleCharacter",
                    "bags": [
                        {
                            "inventory": [
                                {"id": 19721, "count": 40}
                            ]
                        }
                    ]
                }
            ]
        )
        # Total expected: 150 (materials) + 60 (bank) + 40 (bags) = 250
        balance_by_id = self.engine.get_available_purchasing_power(19721, account)
        self.assertEqual(balance_by_id, 250)

        balance_by_iri = self.engine.get_available_purchasing_power("item:19721", account)
        self.assertEqual(balance_by_iri, 250)


class TestCrossRoleOpportunityCost(unittest.TestCase):
    """Test Suite 4: Multi-Role Opportunity Cost Optimization."""

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.solver = PathSolver(graph_store=cls.store)

    def test_higher_tp_price_recommends_sell_on_tp(self):
        """Verifies that when TP net price dominates, the recommendation is SELL_ON_TP."""
        # 10 units: TP sell price = 1000 -> liquidation = 10 * 1000 * 0.85 = 8500
        # Salvage value = 10 * 500 = 5000, Direct value = 10 * 300 = 3000
        res = self.solver.evaluate_cross_role_opportunity_cost(
            item_id=19721,
            quantity=10,
            tp_sell_unit_price=1000,
            salvage_expected_unit_value=500,
            direct_exchange_unit_value=300.0
        )
        self.assertEqual(res["optimal_role_disposition"], "SELL_ON_TP")
        self.assertAlmostEqual(res["tp_liquidation_value"], 8500.0)
        self.assertAlmostEqual(res["salvage_liquidation_value"], 5000.0)
        self.assertAlmostEqual(res["direct_exchange_value"], 3000.0)

    def test_higher_salvage_yield_recommends_salvage(self):
        """Verifies that when salvage yield dominates, the recommendation is SALVAGE."""
        # 10 units: Salvage value = 10 * 1200 = 12000
        # TP sell price = 1000 -> liquidation = 8500, Direct value = 10 * 400 = 4000
        res = self.solver.evaluate_cross_role_opportunity_cost(
            item_id=19721,
            quantity=10,
            tp_sell_unit_price=1000,
            salvage_expected_unit_value=1200,
            direct_exchange_unit_value=400.0
        )
        self.assertEqual(res["optimal_role_disposition"], "SALVAGE")
        self.assertAlmostEqual(res["salvage_liquidation_value"], 12000.0)

    def test_higher_currency_yield_recommends_spend_as_currency(self):
        """Verifies that when direct currency yield dominates, the recommendation is SPEND_AS_CURRENCY."""
        # 10 units: Direct value = 10 * 1500 = 15000
        # TP sell price = 1000 -> liquidation = 8500, Salvage value = 10 * 900 = 9000
        res = self.solver.evaluate_cross_role_opportunity_cost(
            item_id=19721,
            quantity=10,
            tp_sell_unit_price=1000,
            salvage_expected_unit_value=900,
            direct_exchange_unit_value=1500.0
        )
        self.assertEqual(res["optimal_role_disposition"], "SPEND_AS_CURRENCY")
        self.assertAlmostEqual(res["direct_exchange_value"], 15000.0)


if __name__ == "__main__":
    unittest.main()
