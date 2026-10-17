"""Tests for GW2SMWClient precursor collection queries and PrecursorCollectionIngestor RDF generation."""

from __future__ import annotations

from pathlib import Path
from typing import Dict
import tempfile

import owlready2
import pyshacl
import pytest
import rdflib
from rdflib import Namespace, RDF

from engine.account_diff import AccountDiffEngine, AccountState
from engine.graph_store import PrioryGraphStore
from ingestion.precursor_ingestor import (
    DEFAULT_MULTI_WEAPON_PRECURSORS,
    PrecursorCollectionIngestor,
)
from ingestion.smw_client import GW2SMWClient, ITEM, PRIORY, RECIPE

REPO_ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_DIR = REPO_ROOT / "ontology"
VOCAB_DIR = REPO_ROOT.parent / "gw2-priory-ref" / "vocab"


class TestSMWPrecursorClient:
    """Verifies GW2SMWClient precursor tier and achievement collection step methods."""

    def test_fetch_precursor_collection_tiers_gen1_and_gen2(self):
        client = GW2SMWClient(offline=True)

        dawn_tiers = client.fetch_precursor_collection_tiers("Dawn")
        assert len(dawn_tiers) == 3
        assert [t["item_id"] for t in dawn_tiers] == [71423, 73433, 29169]
        assert [t["collection_id"] for t in dawn_tiers] == [
            "col_dawn_vol1",
            "col_dawn_vol2",
            "col_dawn_vol3",
        ]
        assert dawn_tiers[-1]["legendary_item_id"] == 30703
        assert dawn_tiers[-1]["discipline"] == "Weaponsmith"
        assert dawn_tiers[-1]["required_rating"] == 500

        nevermore_tiers = client.fetch_precursor_collection_tiers("The Living Ravens")
        assert len(nevermore_tiers) == 4
        assert [t["item_id"] for t in nevermore_tiers] == [71385, 76363, 74678, 71436]
        assert [t["collection_id"] for t in nevermore_tiers] == [
            "col_nevermore_vol1",
            "col_nevermore_vol2",
            "col_nevermore_vol3",
            "col_nevermore_vol4",
        ]
        assert nevermore_tiers[-1]["legendary_item_id"] == 71383
        assert nevermore_tiers[-1]["discipline"] == "Artificer"

    @pytest.mark.anyio
    async def test_fetch_precursor_methods_support_async_await(self):
        client = GW2SMWClient(offline=True)
        zap_tiers = await client.fetch_precursor_collection_tiers("Bolt")
        assert len(zap_tiers) == 3
        assert zap_tiers[-1]["item_id"] == 29181

        steps = await client.fetch_collection_achievement_steps("Zap I: The Experimental Sword")
        assert len(steps) >= 3
        assert steps[0]["collection_id"] == "col_zap_vol1"
        assert steps[0]["unlocks_recipe_id"] == "craft_experimental_rapier"

    def test_fetch_collection_achievement_steps_with_mocked_smw_response(self, monkeypatch):
        client = GW2SMWClient(offline=False)
        mock_payload = {
            "query": {
                "results": {
                    "Dawn I: The Experimental Daysword": {
                        "printouts": {
                            "Has tier objective": [
                                {"fulltext": "Consult Grandmaster Hobbs"},
                                {"fulltext": "Collect Daysword Energy Core"},
                            ],
                            "Has collection item": [
                                {"fulltext": "Experimental Daysword Blade"},
                            ],
                        }
                    }
                }
            }
        }
        monkeypatch.setattr(client, "ask_query_sync", lambda q: mock_payload)
        steps = client.fetch_collection_achievement_steps("Dawn I: The Experimental Daysword")
        assert len(steps) == 2
        assert steps[0]["step_name"] == "Consult Grandmaster Hobbs"
        assert steps[0]["collection_id"] == "col_dawn_vol1"
        assert steps[0]["produces_item_id"] == 71423


@pytest.fixture(scope="module")
def graph_store() -> PrioryGraphStore:
    store = PrioryGraphStore()
    store.load_all()
    return store


class TestPrecursorCollectionIngestor:
    """Verifies PrecursorCollectionIngestor RDF generation, PrioryGraphStore resolution, SHACL, and HermiT."""

    def test_scan_existing_constraints_detects_existing_produced_by(self):
        ingestor = PrecursorCollectionIngestor(offline=True)
        constraints = ingestor.scan_existing_ontology_constraints()
        # item:29185 (Dusk) has producedBy in dusk_precursor_collection.ttl
        assert 29185 in constraints["produced_by"]
        # item:74155 has producedBy in legendary_trinkets_and_upgrades.ttl
        assert 74155 in constraints["produced_by"]

    def test_generated_multi_weapon_precursor_collections_ttl_exists_and_parses(self):
        ttl_path = ONTOLOGY_DIR / "instances" / "shared" / "multi_weapon_precursor_collections.ttl"
        assert ttl_path.exists(), "multi_weapon_precursor_collections.ttl must exist"
        g = rdflib.Graph()
        g.parse(str(ttl_path), format="turtle")
        assert len(g) > 400

    @pytest.mark.parametrize(
        "precursor_name,precursor_id,legendary_id,expected_tiers,expected_discipline,expected_col_prefix",
        [
            ("Dawn", 29169, 30703, [71423, 73433, 29169], "Weaponsmith", "col_dawn_vol"),
            ("Zap", 29181, 30699, [76664, 76416, 29181], "Weaponsmith", "col_zap_vol"),
            ("The Legend", 29180, 30698, [74561, 73566, 29180], "Artificer", "col_the_legend_vol"),
            ("The Living Ravens", 71436, 71383, [71385, 76363, 74678, 71436], "Artificer", "col_nevermore_vol"),
            ("The Mechanism", 76688, 76158, [75948, 72094, 73194, 76688], "Weaponsmith", "col_astralaria_vol"),
            ("Prototype", 71950, 72713, [74155, 75209, 75657, 71950], "Huntsman", "col_hope_vol"),
        ],
    )
    def test_precursor_chain_triples_in_graph_store(
        self,
        graph_store: PrioryGraphStore,
        precursor_name: str,
        precursor_id: int,
        legendary_id: int,
        expected_tiers: list[int],
        expected_discipline: str,
        expected_col_prefix: str,
    ):
        g = graph_store.graph
        precursor_uri = ITEM[str(precursor_id)]
        legendary_uri = ITEM[str(legendary_id)]

        # Final precursor links to target Legendary via both isPrecursorOf and precursorTo
        assert (precursor_uri, PRIORY.isPrecursorOf, legendary_uri) in g
        assert (precursor_uri, PRIORY.precursorTo, legendary_uri) in g
        assert (precursor_uri, PRIORY.producedBy, None) in g

        # Verify each tier collection and recipe
        for idx, tier_item_id in enumerate(expected_tiers, start=1):
            tier_uri = ITEM[str(tier_item_id)]
            col_uri = PRIORY[f"{expected_col_prefix}{idx}"]
            assert (col_uri, RDF.type, PRIORY.AchievementCollectionPath) in g
            assert (tier_uri, PRIORY.acquiredVia, col_uri) in g
            assert (tier_uri, PRIORY.hasAcquisitionPath, col_uri) in g

            unlocked_recipes = list(g.objects(col_uri, PRIORY.unlocksRecipe))
            assert len(unlocked_recipes) == 1
            recipe_uri = unlocked_recipes[0]
            assert (recipe_uri, PRIORY.producesItem, tier_uri) in g
            assert (
                recipe_uri,
                PRIORY.requiresDiscipline,
                rdflib.URIRef(f"https://priory.gw2/ref/discipline/{expected_discipline}"),
            ) in g

            if idx > 1:
                prev_col_uri = PRIORY[f"{expected_col_prefix}{idx - 1}"]
                assert (col_uri, PRIORY.requiresCollection, prev_col_uri) in g

    @pytest.mark.parametrize(
        "precursor_id,expected_ascended_mat_name,expected_min_ascended_qty,expected_tiers_count",
        [
            (29169, "Deldrimor Steel Ingot", 90, 3),  # Dawn -> 90 Deldrimor Steel Ingots across 3 tiers
            (29181, "Deldrimor Steel Ingot", 75, 3),  # Zap -> 75 Deldrimor Steel Ingots across 3 tiers
            (29180, "Spiritwood Plank", 90, 3),       # The Legend -> 90 Spiritwood Planks across 3 tiers
            (71436, "Spiritwood Plank", 90, 4),       # The Living Ravens -> 90 Spiritwood Planks across 4 tiers
            (76688, "Deldrimor Steel Ingot", 90, 4),  # The Mechanism -> 90 Deldrimor Steel Ingots across 4 tiers
            (71950, "Deldrimor Steel Ingot", 80, 4),  # Prototype -> >=80 Deldrimor Steel Ingots across tiers
        ],
    )
    def test_account_diff_engine_resolves_multi_tier_precursor_chains(
        self,
        graph_store: PrioryGraphStore,
        precursor_id: int,
        expected_ascended_mat_name: str,
        expected_min_ascended_qty: int,
        expected_tiers_count: int,
    ):
        diff_engine = AccountDiffEngine(graph_store)
        empty_account = AccountState()

        report = diff_engine.compute_diff(
            goal_item_id=precursor_id,
            account=empty_account,
        )
        assert report.goal_item_id == precursor_id
        assert report.is_fully_satisfied is False
        assert len(report.root_node.sub_requirements) >= 3
        assert len(report.summary_missing_materials) > 0

        # Verify time-gated Ascended material aggregation across the multi-tier precursor chain
        assert expected_ascended_mat_name in report.summary_missing_materials, (
            f"Expected {expected_ascended_mat_name} in summary_missing_materials for {precursor_id}, "
            f"got {report.summary_missing_materials}"
        )
        assert report.summary_missing_materials[expected_ascended_mat_name] >= expected_min_ascended_qty
        assert any(
            node.item_id == 79418 and node.required_quantity == 100
            for node in report.root_node.sub_requirements
        )

    def test_shacl_and_hermit_consistency_with_precursor_collections(self):
        # 1. Build clean data graph and validate SHACL shapes across the entire knowledge graph
        data_graph = rdflib.Graph()
        if VOCAB_DIR.exists():
            for ttl_file in sorted(VOCAB_DIR.rglob("*.ttl")):
                data_graph.parse(str(ttl_file), format="turtle")
        for ttl_file in sorted(ONTOLOGY_DIR.rglob("*.ttl")):
            if "shacl" in ttl_file.name or "shapes" in str(ttl_file):
                continue
            data_graph.parse(str(ttl_file), format="turtle")

        shacl_graph = rdflib.Graph()
        shacl_graph.parse(str(ONTOLOGY_DIR / "priory_shacl.ttl"), format="turtle")
        for ttl_file in sorted((ONTOLOGY_DIR / "shapes").rglob("*.ttl")):
            shacl_graph.parse(str(ttl_file), format="turtle")

        conforms, _, results_text = pyshacl.validate(
            data_graph=data_graph,
            shacl_graph=shacl_graph,
            inference="rdfs",
            abort_on_first=False,
        )
        assert conforms, f"SHACL validation failed:\n{results_text}"

        # 2. Validate OWL 2 DL consistency with HermiT reasoner over TBox + Precursor Collection ABox
        hermit_graph = rdflib.Graph()
        tbox_and_precursor_files = [
            ONTOLOGY_DIR / "bfo_subset.ttl",
            ONTOLOGY_DIR / "priory_core.ttl",
            ONTOLOGY_DIR / "character.ttl",
            ONTOLOGY_DIR / "schemas" / "legendary_crafting_app.ttl",
            ONTOLOGY_DIR / "instances" / "shared" / "precursor_taxonomy.ttl",
            ONTOLOGY_DIR / "instances" / "shared" / "dusk_precursor_collection.ttl",
            ONTOLOGY_DIR / "instances" / "shared" / "multi_weapon_precursor_collections.ttl",
        ]
        for ttl_file in tbox_and_precursor_files:
            if ttl_file.exists():
                hermit_graph.parse(str(ttl_file), format="turtle")
        if VOCAB_DIR.exists():
            for ttl_file in sorted(VOCAB_DIR.rglob("*.ttl")):
                hermit_graph.parse(str(ttl_file), format="turtle")

        sh_ns = Namespace("http://www.w3.org/ns/shacl#")
        for s in list(hermit_graph.subjects(RDF.type, sh_ns.NodeShape)):
            for p, o in list(hermit_graph.predicate_objects(s)):
                hermit_graph.remove((s, p, o))
        for s, p, o in list(hermit_graph):
            if str(p).startswith(str(sh_ns)) or str(o).startswith(str(sh_ns)):
                hermit_graph.remove((s, p, o))

        with tempfile.NamedTemporaryFile(suffix=".owl", delete=False) as tmp:
            hermit_graph.serialize(destination=tmp.name, format="xml")
            tmp_path = tmp.name

        world = owlready2.World()
        onto = world.get_ontology(f"file://{tmp_path}").load()
        with onto:
            owlready2.sync_reasoner_hermit(world, infer_property_values=False)
        inconsistent = list(world.inconsistent_classes())
        assert len(inconsistent) == 0, f"HermiT found unsatisfiable classes: {inconsistent}"
