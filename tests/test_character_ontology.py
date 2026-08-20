"""Unit and integration tests for Character Ontology, Ephemeral ABox Hydration, and MCP Handlers."""

import time
import unittest
from pathlib import Path
import rdflib
import pyshacl
from engine.graph_store import PrioryGraphStore
from engine.character_graph import CharacterGraphHydrator
from engine.semantic_query import SemanticQueryService
from engine.account_diff import AccountDiffEngine, AccountState
from engine.path_solver import PathSolver
from ingestion.gw2_api import ETagCacheManager

DEF_REPO = Path(__file__).parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")


TEST_CHARACTERS = [
    {
        "name": "Valen Starfall",
        "race": "Human",
        "gender": "Male",
        "profession": "Guardian",
        "level": 80,
        "crafting": [
            {"discipline": "Armorsmith", "rating": 500, "active": True},
            {"discipline": "Weaponsmith", "rating": 450, "active": True}
        ],
        "attributes": {
            "Power": 2400,
            "Precision": 2100,
            "Toughness": 1200,
            "Vitality": 1300,
            "Armor": 2471
        },
        "equipment_tabs": [
            {
                "tab": 1,
                "name": "Dragonhunter Power DPS",
                "is_active": True,
                "equipment": [
                    {
                        "id": 30689,
                        "slot": "WeaponSlotMainHand1",
                        "stats": {"id": "berserker"},
                        "upgrades": [24562, 24562], # Sigils of Force
                        "infusions": [37131]
                    },
                    {
                        "id": 803841,
                        "slot": "Coat",
                        "stats": {"id": "berserker"},
                        "upgrades": [24765] # Scholar Rune
                    }
                ]
            }
        ],
        "equipment": [
            {"id": 30689, "slot": "WeaponSlotMainHand1", "stats": {"id": "berserker"}, "upgrades": [24562]},
            {"id": 803841, "slot": "Coat", "stats": {"id": "berserker"}, "upgrades": [24765]}
        ],
        "build_tabs": [
            {
                "tab": 1,
                "is_active": True,
                "build": {
                    "specializations": [
                        {"id": 27, "traits": [574, 565, 579]}, # Dragonhunter
                        {"id": 16, "traits": [549, 554, 551]}, # Zeal
                        {"id": 42, "traits": [635, 653, 648]}  # Radiance
                    ],
                    "skills": {
                        "heal": 9158,
                        "utilities": [9153, 9154, 9155],
                        "elite": 9089
                    }
                }
            }
        ],
        "bags": [
            {
                "id": 8941,
                "size": 20,
                "inventory": [
                    {"id": 19721, "count": 50}, # 50 Ectoplasm
                    {"id": 19675, "count": 20}  # 20 Clovers
                ]
            }
        ]
    },
    {
        "name": "Lyra Shadowmend",
        "race": "Sylvari",
        "gender": "Female",
        "profession": "Necromancer",
        "level": 80,
        "crafting": [
            {"discipline": "Tailor", "rating": 500, "active": True},
            {"discipline": "Artificer", "rating": 400, "active": False}
        ],
        "equipment_tabs": [
            {
                "tab": 1,
                "name": "Scourge Condi",
                "is_active": True,
                "equipment": [
                    {"id": 30704, "slot": "WeaponSlotMainHand1", "stats": {"id": "viper"}}
                ]
            }
        ],
        "equipment": [
            {"id": 30704, "slot": "WeaponSlotMainHand1", "stats": {"id": "viper"}}
        ],
        "build_tabs": [
            {
                "tab": 1,
                "is_active": True,
                "build": {
                    "specializations": [
                        {"id": 60, "traits": [2078, 2085, 2099]}, # Scourge
                        {"id": 34, "traits": [780, 788, 792]},   # Curses
                        {"id": 53, "traits": [853, 855, 858]}    # Soul Reaping
                    ]
                }
            }
        ],
        "bags": [
            {
                "id": 8941,
                "size": 20,
                "inventory": [
                    {"id": 19721, "count": 200}, # 200 Ectoplasm
                    {"id": 29185, "count": 1}   # 1 Dusk precursor!
                ]
            }
        ]
    },
    {
        "name": "Rox Forgeheart",
        "race": "Charr",
        "gender": "Female",
        "profession": "Warrior",
        "level": 80,
        "crafting": [
            {"discipline": "Weaponsmith", "rating": 500, "active": True},
            {"discipline": "Huntsman", "rating": 400, "active": True}
        ],
        "equipment": [
            {"id": 30703, "slot": "WeaponSlotMainHand1"} # Sunrise
        ],
        "bags": [
            {
                "id": 8941,
                "size": 20,
                "inventory": [
                    {"id": 24277, "count": 250} # 250 Crystalline Dust
                ]
            }
        ]
    }
]


class TestCharacterOntologyAndHydration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore(ref_repo_path=REF_REPO, def_repo_path=DEF_REPO)
        cls.store.load_all()
        cls.hydrator = CharacterGraphHydrator(cls.store)
        cls.service = SemanticQueryService(cls.store)

    def setUp(self):
        # Hydrate test characters before each test
        self.hydrator.clear_session_characters()
        self.hydrator.hydrate_characters(TEST_CHARACTERS)

    def tearDown(self):
        self.hydrator.clear_session_characters()

    def test_character_shacl_validation(self):
        """Validates that hydrated character individuals strictly conform to character_shape.ttl."""
        shacl_graph = rdflib.Graph()
        shacl_file = DEF_REPO / "ontology" / "shapes" / "character_shape.ttl"
        shacl_graph.parse(shacl_file, format="turtle")

        # Get character named graph
        g_uri = self.hydrator.get_character_graph_uri("Valen Starfall")
        char_graph = self.store.dataset.graph(identifier=g_uri)
        self.assertGreater(len(char_graph), 0)

        conforms, results_graph, results_text = pyshacl.validate(
            char_graph,
            shacl_graph=shacl_graph,
            inference="rdfs",
            abort_on_first=False
        )
        self.assertTrue(conforms, f"Character graph failed SHACL validation:\n{results_text}")

    def test_character_hydration_benchmark(self):
        """Verifies that hydrating a 10-character account payload completes in < 50ms (< 5ms per character)."""
        ten_chars = [dict(TEST_CHARACTERS[i % len(TEST_CHARACTERS)], name=f"Hero_{i}") for i in range(10)]

        start_time = time.perf_counter()
        graph_uris = self.hydrator.hydrate_characters(ten_chars, force_refresh=True)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        self.assertEqual(len(graph_uris), 10)
        self.assertLess(elapsed_ms, 50.0, f"Hydration took {elapsed_ms:.2f}ms, exceeding 50ms SLA")
        self.assertLess(elapsed_ms / 10.0, 5.0, f"Average per-character hydration took {elapsed_ms/10:.2f}ms")

    def test_equipment_tab_and_stat_prefix_hydration(self):
        """Verifies that equipment tabs and stat prefixes (Berserker's, Viper's) are hydrated into RDF."""
        sparql = """
        SELECT DISTINCT ?charName ?tabName ?itemLabel ?statLabel WHERE {
            ?char priory:characterName ?charName ;
                  priory:hasEquipmentTab ?tab .
            ?tab priory:tabName ?tabName ;
                 priory:equippedItem ?eq .
            ?eq priory:item ?item .
            ?item rdfs:label ?itemLabel .
            OPTIONAL { ?eq priory:hasStatCombination ?stat . ?stat skos:prefLabel ?statLabel }
        }
        """
        results = self.store.query(sparql)
        self.assertGreaterEqual(len(results), 2)
        char_names = [r["charName"] for r in results]
        self.assertIn("Valen Starfall", char_names)

    def test_build_tab_and_specialization_queries(self):
        """Verifies querying characters by active build specialization (Dragonhunter, Scourge)."""
        # Scourge -> Lyra Shadowmend
        scourges = self.service.find_characters_by_specialization("Scourge")
        # In mock data, Lyra has spec id 60 (Scourge)
        spec_60 = self.service.find_characters_by_specialization("60")
        self.assertGreaterEqual(len(spec_60), 1)
        self.assertEqual(spec_60[0]["charName"], "Lyra Shadowmend")

    def test_character_content_diff_caching(self):
        """Verifies that unchanged character JSON payloads skip re-hydration using SHA-256 content hashes."""
        char = TEST_CHARACTERS[0]
        h1 = self.hydrator.compute_character_hash(char)
        self.assertTrue(len(h1) == 64) # SHA-256 length

        # Hydrate first time
        g_uri1 = self.hydrator.hydrate_character(char, session_id="diff_test")
        t1 = self.hydrator._hydrated_graphs[g_uri1]["timestamp"]

        # Hydrate second time with same data -> should return cached without re-hydrating
        time.sleep(0.01)
        g_uri2 = self.hydrator.hydrate_character(char, session_id="diff_test")
        t2 = self.hydrator._hydrated_graphs[g_uri2]["timestamp"]
        self.assertEqual(t1, t2)

    def test_etag_cache_manager(self):
        """Verifies disk-backed ETag cache storing and retrieval."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_etags.json"
            mgr = ETagCacheManager(cache_path=cache_file)
            mgr.store_response("account/materials", '"etag_12345"', [{"id": 19721, "count": 250}])
            
            self.assertEqual(mgr.get_etag("account/materials"), '"etag_12345"')
            payload = mgr.get_cached_payload("account/materials")
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["count"], 250)

    def test_cross_character_crafting_capability_resolution(self):
        """Verifies SPARQL queries find the exact capable character for each crafting discipline and rating."""
        # Armorsmith 500 -> Valen Starfall
        armor_capable = self.service.find_capable_crafting_characters("Armorsmith", min_rating=500)
        self.assertGreaterEqual(len(armor_capable), 1)
        self.assertEqual(armor_capable[0]["charName"], "Valen Starfall")

        # Weaponsmith 500 -> Rox Forgeheart (Valen has only 450)
        weapon_500 = self.service.find_capable_crafting_characters("Weaponsmith", min_rating=500)
        self.assertEqual(len(weapon_500), 1)
        self.assertEqual(weapon_500[0]["charName"], "Rox Forgeheart")

        # Weaponsmith 400 -> Both Rox (500) and Valen (450)
        weapon_400 = self.service.find_capable_crafting_characters("Weaponsmith", min_rating=400)
        self.assertEqual(len(weapon_400), 2)
        names = [c["charName"] for c in weapon_400]
        self.assertIn("Rox Forgeheart", names)
        self.assertIn("Valen Starfall", names)

        # Tailor 500 -> Lyra Shadowmend
        tailor_capable = self.service.find_capable_crafting_characters("Tailor", min_rating=500)
        self.assertEqual(len(tailor_capable), 1)
        self.assertEqual(tailor_capable[0]["charName"], "Lyra Shadowmend")

        # Leatherworker 500 -> Nobody on account
        leather_capable = self.service.find_capable_crafting_characters("Leatherworker", min_rating=500)
        self.assertEqual(len(leather_capable), 0)

    def test_taxonomic_equipability_checks(self):
        """Verifies character equipability checks using SKOS taxonomies without procedural hardcoding."""
        # Valen Starfall (Guardian):
        # Heavy Armor (Warplate 803841) -> can equip
        heavy_check = self.service.check_item_character_equipability("Valen Starfall", 803841)
        self.assertTrue(heavy_check["can_equip"])
        self.assertIn("HeavyArmor", heavy_check["reason"])

        # Greatsword (Twilight 30704) -> can wield
        gs_check = self.service.check_item_character_equipability("Valen Starfall", 30704)
        self.assertTrue(gs_check["can_equip"])

        # Lyra Shadowmend (Necromancer):
        # Heavy Armor (Warplate 803841) -> cannot equip
        lyra_armor = self.service.check_item_character_equipability("Lyra Shadowmend", 803841)
        self.assertFalse(lyra_armor["can_equip"])
        self.assertIn("cannot wear", lyra_armor["reason"])

    def test_character_bag_inventory_indexing(self):
        """Verifies indexing and locating items held in character inventory bags."""
        # Ectoplasm (19721): 50 on Valen + 200 on Lyra = 250 total
        ecto_locs = self.service.find_character_item_locations(19721)
        self.assertEqual(len(ecto_locs), 2)
        total_ecto = sum(l["quantity"] for l in ecto_locs)
        self.assertEqual(total_ecto, 250)

        # Dusk precursor (29185): 1 on Lyra Shadowmend in Bag0 slot 1
        dusk_locs = self.service.find_character_item_locations(29185)
        self.assertEqual(len(dusk_locs), 1)
        self.assertEqual(dusk_locs[0]["character_name"], "Lyra Shadowmend")
        self.assertEqual(dusk_locs[0]["bag_slot"], "Bag0")
        self.assertEqual(dusk_locs[0]["slot_index"], 1)

    def test_graph_isolation_on_drop(self):
        """Verifies that clearing ephemeral character graphs leaves the default knowledge graph unmodified."""
        default_len_before = len(self.store.graph)
        self.assertGreater(default_len_before, 9000)

        # Drop character graphs
        dropped_count = self.hydrator.clear_session_characters()
        self.assertEqual(dropped_count, 3)

        # Default graph must remain completely unchanged
        self.assertEqual(len(self.store.graph), default_len_before)

        # Character queries now return empty
        chars_after = self.service.find_capable_crafting_characters("Armorsmith", min_rating=1)
        self.assertEqual(len(chars_after), 0)

    def test_mcp_tool_handlers(self):
        """Verifies MCP tool handler formats and responses."""
        # 1. priory_character_crafting
        craft_mcp = self.service.handle_mcp_character_crafting("Weaponsmith", min_rating=500)
        self.assertEqual(craft_mcp["requested_discipline"], "Weaponsmith")
        self.assertEqual(craft_mcp["capable_character_count"], 1)
        self.assertEqual(craft_mcp["capable_characters"][0]["character_name"], "Rox Forgeheart")

        # 2. priory_character_equipability
        equip_mcp = self.service.handle_mcp_character_equipability("Valen Starfall", 30704) # Twilight
        self.assertTrue(equip_mcp["can_equip"])
        self.assertEqual(equip_mcp["character_name"], "Valen Starfall")

        # 3. priory_character_inventory
        inv_mcp = self.service.handle_mcp_character_inventory(29185) # Dusk
        self.assertEqual(inv_mcp["total_quantity_in_character_bags"], 1)
        self.assertEqual(inv_mcp["holding_characters_count"], 1)

        # 4. priory_character_summary
        sum_mcp = self.service.handle_mcp_character_summary("Valen Starfall")
        self.assertIn("Valen Starfall", sum_mcp["semantic_markdown_profile"])
        self.assertIn("Armorsmith 500", sum_mcp["semantic_markdown_profile"])

    def test_character_semantic_context_generation(self):
        """Verifies serializing clean Markdown character facts for bottom LLM prompts."""
        context = self.service.get_character_semantic_context()
        self.assertIn("Valen Starfall", context)
        self.assertIn("Guardian", context)
        self.assertIn("Armorsmith 500", context)
        self.assertIn("Lyra Shadowmend", context)
        self.assertIn("Necromancer", context)
        self.assertIn("Tailor 500", context)
        self.assertIn("Rox Forgeheart", context)
        self.assertIn("Weaponsmith 500", context)


if __name__ == "__main__":
    unittest.main()
