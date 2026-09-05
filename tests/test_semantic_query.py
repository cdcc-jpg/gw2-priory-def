"""Unit tests for SemanticQueryService."""

import unittest
from pathlib import Path
from engine.graph_store import PrioryGraphStore
from engine.semantic_query import SemanticQueryService

DEF_REPO = Path(__file__).parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")


class TestSemanticQuery(unittest.TestCase):

    def setUp(self):
        self.store = PrioryGraphStore(ref_repo_path=REF_REPO, def_repo_path=DEF_REPO)
        self.store.load_all()
        self.service = SemanticQueryService(self.store)

    def test_taxonomic_subsumption_search(self):
        """Verifies querying for parent category 'TwoHandedWeapon' discovers 'Twilight' (Greatsword)."""
        items = self.service.find_items_by_taxonomy(
            broad_weapon_type="TwoHandedWeapon",
            rarity_tier="Legendary"
        )
        self.assertGreater(len(items), 0)
        labels = [item["label"] for item in items]
        self.assertIn("Twilight", labels)

    def test_polymorphic_acquisition_discovery_mystic_clover(self):
        """Verifies discovering multiple non-crafting acquisition sources for Mystic Clovers."""
        clover_paths = self.service.discover_acquisition_paths(19675) # Mystic Clover ID
        self.assertEqual(clover_paths["item_name"], "Mystic Clover")

        paths = clover_paths["acquisition_paths"]
        # Should discover Astral Acclaim vendor exchange
        currencies = [ve["currency"] for ve in paths["vendor_exchanges"]]
        self.assertIn("AstralAcclaim", currencies)

        # Should discover Fractal Relic exchange with time gate
        fractal_entry = next((ve for ve in paths["vendor_exchanges"] if ve["currency"] == "FractalRelic"), None)
        self.assertIsNotNone(fractal_entry)
        self.assertEqual(fractal_entry["time_gate"], "2 per day")

        # Should discover WvW reward tracks
        self.assertGreater(len(paths["reward_tracks"]), 0)

    def test_entity_resolution_by_chat_code(self):
        """Verifies resolving in-game chat link code to canonical entity."""
        res = self.service.resolve_entity_by_text("[&AgErZgAA]")
        self.assertGreaterEqual(len(res), 1)
        self.assertEqual(res[0]["label"], "Twilight")

    def test_semantic_context_generation_for_llm(self):
        """Verifies semantic subgraph serialization produces structured markdown facts."""
        service = SemanticQueryService(self.store)
        context = service.get_item_semantic_context_for_llm(30704) # Twilight

        self.assertIn("Semantic Entity: Twilight", context)
        self.assertIn("Legendary", context)
        self.assertIn("Requires: 1x Dusk", context)
        self.assertIn("Requires: 1x Gift of Fortune", context)

    def test_dynamic_action_intent_vocabularies(self):
        """Verifies dynamic extraction of acquisition classes and altLabel action verbs from graph."""
        actions = self.service.get_action_intent_vocabularies()
        self.assertGreater(len(actions), 0)
        self.assertIn("CraftingPath", actions)
        self.assertIn("craft", actions["CraftingPath"]["synonyms"])
        self.assertIn("VendorExchangePath", actions)
        self.assertIn("buy", actions["VendorExchangePath"]["synonyms"])

    def test_find_items_by_role_and_subsumption(self):
        """Verifies resolving items playing roles using both prefixed and bare identifiers with subsumption."""
        # 1. Prefixed role:CurrencyExchange
        currencies = self.service.find_items_by_role("role:CurrencyExchange")
        self.assertGreater(len(currencies), 0)
        labels = [c["label"] for c in currencies]
        self.assertIn("Astral Acclaim", labels)
        self.assertIn("Coin", labels)

        aa = next(c for c in currencies if c["label"] == "Astral Acclaim")
        self.assertEqual(aa["substrateType"], "priory:AccountWalletScalar")
        self.assertEqual(aa["gw2Id"], 68)

        # 2. Bare role identifier "CurrencyExchange"
        bare_currencies = self.service.find_items_by_role("CurrencyExchange")
        self.assertEqual(len(currencies), len(bare_currencies))

        # 3. EquippedGear role
        gear_items = self.service.find_items_by_role("role:EquippedGear")
        self.assertGreater(len(gear_items), 0)
        gear_labels = [g["label"] for g in gear_items]
        self.assertIn("Twilight", gear_labels)
        twilight_match = next(g for g in gear_items if g["label"] == "Twilight")
        self.assertEqual(twilight_match["substrateType"], "priory:ContainerizedToken")
        self.assertEqual(twilight_match["gw2Id"], 30704)

    def test_get_token_economic_affordances(self):
        """Verifies economic profile of items including substrate, roles, containerization, salvage, trade, and stack size."""
        # 1. Containerized Gear Item: Twilight (30704)
        twilight_profile = self.service.get_token_economic_affordances(30704)
        self.assertEqual(twilight_profile["label"], "Twilight")
        self.assertEqual(twilight_profile["substrate"], "priory:ContainerizedToken")
        self.assertTrue(twilight_profile["isContainerized"])
        self.assertFalse(twilight_profile["isTradeable"])  # Account bound
        self.assertEqual(twilight_profile["maxStackSize"], 250)
        self.assertTrue(any("EquippedGear" in r for r in twilight_profile["roles"]))

        # 2. Account Wallet Scalar: Coin (1)
        coin_profile = self.service.get_token_economic_affordances(1)
        self.assertEqual(coin_profile["label"], "Coin")
        self.assertEqual(coin_profile["substrate"], "priory:AccountWalletScalar")
        self.assertFalse(coin_profile["isContainerized"])
        self.assertFalse(coin_profile["isSalvageable"])
        self.assertFalse(coin_profile["isTradeable"])
        self.assertEqual(coin_profile["maxStackSize"], 0)
        self.assertTrue(any("CurrencyExchange" in r for r in coin_profile["roles"]))

    def test_get_manifested_gear_catalog(self):
        """Verifies manifested gear catalog excludes pure ledger tokens and contains equipment."""
        catalog = self.service.get_manifested_gear_catalog()
        self.assertGreater(len(catalog), 50)

        labels = {item["label"] for item in catalog}
        self.assertIn("Twilight", labels)
        self.assertIn("Eternity", labels)
        self.assertIn("Sunrise", labels)

        # Ensure pure ledger tokens / currencies / crafting materials are excluded
        self.assertNotIn("Coin", labels)
        self.assertNotIn("Astral Acclaim", labels)
        self.assertNotIn("Spirit Shard", labels)
        self.assertNotIn("Glob of Ectoplasm", labels)


if __name__ == "__main__":
    unittest.main()

