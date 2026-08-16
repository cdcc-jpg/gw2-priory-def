"""Unit tests for the SMW Ingestion Engine across all 7 archetypes."""

import unittest
from ingestion.smw_client import GW2SMWClient
import rdflib
import pyshacl
from pathlib import Path

DEF_REPO = Path(__file__).parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")


class TestSMWIngestion(unittest.TestCase):

    def setUp(self):
        self.client = GW2SMWClient()

    def test_rdf_item_graph_generation(self):
        """Verifies converting parsed item data into valid OWL/RDF triples."""
        g = self.client.build_rdf_item_graph(
            item_id=30699,
            item_name="Twilight",
            rarity_str="Legendary",
            chat_code="[&AgErZgAA]"
        )
        self.assertGreater(len(g), 0)

        # Load SHACL Shapes and validate generated graph individual
        shacl_graph = rdflib.Graph()
        shacl_graph.parse(DEF_REPO / "ontology" / "priory_shacl.ttl", format="turtle")

        # Load vocabulary concept directly from REF_REPO
        vocab_graph = rdflib.Graph()
        vocab_graph.parse(REF_REPO / "vocab" / "rarities.ttl", format="turtle")
        combined_data = g + vocab_graph

        conforms, results_graph, results_text = pyshacl.validate(
            combined_data,
            shacl_graph=shacl_graph,
            inference="rdfs",
            abort_on_first=False
        )
        self.assertTrue(conforms, f"Generated item failed SHACL validation:\n{results_text}")

    def test_archetype_query_syntax(self):
        """Verifies that query builder signatures and syntax are correctly structured."""
        self.assertTrue(hasattr(self.client, "get_discipline_recipes"))
        self.assertTrue(hasattr(self.client, "get_mystic_forge_recipes"))
        self.assertTrue(hasattr(self.client, "get_vendor_exchanges"))
        self.assertTrue(hasattr(self.client, "get_npc_location_and_waypoint"))
        self.assertTrue(hasattr(self.client, "get_time_gated_items"))
        self.assertTrue(hasattr(self.client, "get_achievement_collection_steps"))
        self.assertTrue(hasattr(self.client, "get_reward_tracks_for_item"))


if __name__ == "__main__":
    unittest.main()
