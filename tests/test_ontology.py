"""Ontology and SHACL validation test suite for Project Priory."""

import unittest
from pathlib import Path
import rdflib
import pyshacl

DEF_REPO = Path(__file__).parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")


class TestOntologyAndSHACL(unittest.TestCase):

    def test_ontology_and_shacl_conformance(self):
        """Validates that all ontology schemas, reference vocabularies, and instances conform to SHACL shapes."""
        data_graph = rdflib.Graph()

        # 1. Load Core & Character Schemas
        data_graph.parse(DEF_REPO / "ontology" / "priory_core.ttl", format="turtle")
        char_schema = DEF_REPO / "ontology" / "character.ttl"
        if char_schema.exists():
            data_graph.parse(char_schema, format="turtle")

        # 2. Load Reference Vocabularies from gw2-priory-ref
        for ttl in (REF_REPO / "vocab").glob("*.ttl"):
            data_graph.parse(ttl, format="turtle")

        # 3. Load Instances
        for ttl in (DEF_REPO / "ontology" / "instances").glob("*.ttl"):
            data_graph.parse(ttl, format="turtle")

        # 4. Load SHACL Shapes
        shacl_graph = rdflib.Graph()
        shacl_graph.parse(DEF_REPO / "ontology" / "priory_shacl.ttl", format="turtle")
        for ttl in (DEF_REPO / "ontology" / "shapes").glob("*.ttl"):
            shacl_graph.parse(ttl, format="turtle")

        # Validate
        conforms, results_graph, results_text = pyshacl.validate(
            data_graph,
            shacl_graph=shacl_graph,
            inference="rdfs",
            abort_on_first=False
        )

        self.assertTrue(conforms, f"SHACL validation failed:\n{results_text}")


if __name__ == "__main__":
    unittest.main()
