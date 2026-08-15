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
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["label"], "Twilight")
        self.assertEqual(res[0]["gw2Id"], 30699)

    def test_semantic_context_generation_for_llm(self):
        """Verifies semantic subgraph serialization produces structured markdown facts."""
        context = self.service.get_item_semantic_context_for_llm(30699)
        self.assertIn("Semantic Entity: Twilight", context)
        self.assertIn("Forge Twilight", context)
        self.assertIn("Requires: 1x Dusk", context)
        self.assertIn("Requires: 1x Gift of Fortune", context)


if __name__ == "__main__":
    unittest.main()
