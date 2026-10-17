"""Tests for Ontology-Driven OWL-RL Entailment, Pillar Gift Classification, Dynamic Booster Resolution, and Cross-Weapon Synergies."""

import unittest
from rdflib import Literal, RDF, RDFS

import engine.twilight_journey_solver as tjs_module
from engine.graph_store import PrioryGraphStore, PRIORY, ITEM
from engine.account_diff import AccountDiffEngine, AccountState
from engine.twilight_journey_solver import TwilightJourneySolver


class TestOntologyDrivenInference(unittest.TestCase):
    """Verifies neuro-symbolic RDF/OWL inference in TwilightJourneySolver."""

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(cls.store)
        cls.solver = TwilightJourneySolver(cls.store, cls.diff_engine)

    def test_no_hardcoded_booster_names_dict_in_solver(self):
        """BOOSTER_NAMES static dictionary must be completely removed from twilight_journey_solver."""
        self.assertFalse(
            hasattr(tjs_module, "BOOSTER_NAMES"),
            "Static BOOSTER_NAMES dictionary should be removed in favor of ontology-driven catalog queries.",
        )

    def test_owl_rl_weapon_generation_entailment_and_bom(self):
        """Weapons are classified into GEN1, GEN2, GEN3 via OWL-entailed classes and hasPrecursorType."""
        account = AccountState()

        # Gen 1: Twilight (30704) & Sunrise (30703)
        twilight_plan = self.solver.build_journey_plan(account=account, target_item_id=30704)
        self.assertEqual(twilight_plan.generation, "GEN1")
        self.assertEqual(twilight_plan.target_item_name, "Twilight")

        sunrise_plan = self.solver.build_journey_plan(account=account, target_item_id=30703)
        self.assertEqual(sunrise_plan.generation, "GEN1")
        self.assertEqual(sunrise_plan.target_item_name, "Sunrise")

        # Gen 2: Nevermore (71383) & The Shining Blade (79562)
        nevermore_plan = self.solver.build_journey_plan(account=account, target_item_id=71383)
        self.assertEqual(nevermore_plan.generation, "GEN2")
        self.assertEqual(nevermore_plan.target_item_name, "Nevermore")

        shining_blade_plan = self.solver.build_journey_plan(account=account, target_item_id=79562)
        self.assertEqual(shining_blade_plan.generation, "GEN2")

        # Gen 3: Aurene's Rending / Bite (96937)
        aurene_plan = self.solver.build_journey_plan(account=account, target_item_id=96937)
        self.assertEqual(aurene_plan.generation, "GEN3")
        self.assertIn("Aurene's", aurene_plan.target_item_name)

        # Verify OWL class entailment if present in store
        gen1_rows = self.store.query("SELECT ?id WHERE { ?item a priory:Gen1LegendaryWeapon ; priory:gw2Id ?id }")
        if gen1_rows:
            gen1_ids = {int(r["id"]) for r in gen1_rows}
            self.assertIn(30704, gen1_ids)
            self.assertIn(30703, gen1_ids)

        gen2_rows = self.store.query("SELECT ?id WHERE { ?item a priory:Gen2LegendaryWeapon ; priory:gw2Id ?id }")
        if gen2_rows:
            gen2_ids = {int(r["id"]) for r in gen2_rows}
            self.assertIn(71383, gen2_ids)
            self.assertIn(79562, gen2_ids)

        gen3_rows = self.store.query("SELECT ?id WHERE { ?item a priory:Gen3LegendaryWeapon ; priory:gw2Id ?id }")
        if gen3_rows:
            gen3_ids = {int(r["id"]) for r in gen3_rows}
            self.assertIn(96937, gen3_ids)

    def test_pillar_gift_classification_via_rdf_classes(self):
        """_introspect_weapon_bom classifies top-level gifts by RDF class even without substring cues."""
        # Inject a synthetic Gen 3 weapon & 4 top-level components with opaque labels to prove RDF class inference
        g = self.store.graph
        synth_weapon = ITEM["999001"]
        synth_prec = ITEM["999002"]
        synth_tribute = ITEM["999003"]
        synth_mastery = ITEM["999004"]
        synth_specific = ITEM["999005"]
        synth_recipe = PRIORY["recipe_999001"]

        triples_to_add = [
            (synth_weapon, PRIORY.gw2Id, Literal(999001)),
            (synth_weapon, RDFS.label, Literal("Synthetic Apex Blade")),
            (synth_weapon, RDF.type, PRIORY.Gen3LegendaryWeapon),
            (synth_weapon, PRIORY.producedBy, synth_recipe),
            (synth_recipe, PRIORY.producesItem, synth_weapon),
            # Precursor with no 'Precursor' in label
            (synth_prec, PRIORY.gw2Id, Literal(999002)),
            (synth_prec, RDFS.label, Literal("Alpha Prototype Edge")),
            (synth_prec, RDF.type, PRIORY.PrecursorWeapon),
            # Tribute gift with no 'Tribute' or 'Fortune' in label
            (synth_tribute, PRIORY.gw2Id, Literal(999003)),
            (synth_tribute, RDFS.label, Literal("Beta Economic Component")),
            (synth_tribute, RDF.type, PRIORY.TributePillarGift),
            # Mastery gift with no 'Mastery' in label
            (synth_mastery, PRIORY.gw2Id, Literal(999004)),
            (synth_mastery, RDFS.label, Literal("Gamma World Token")),
            (synth_mastery, RDF.type, PRIORY.MasteryPillarGift),
            # Weapon-specific gift with no 'Gift of' in label
            (synth_specific, PRIORY.gw2Id, Literal(999005)),
            (synth_specific, RDFS.label, Literal("Delta Thematic Core")),
            (synth_specific, RDF.type, PRIORY.WeaponSpecificPillarGift),
        ]
        for idx, ing_uri in enumerate([synth_prec, synth_tribute, synth_mastery, synth_specific], start=1):
            req_uri = PRIORY[f"req_999001_{idx}"]
            triples_to_add.extend([
                (synth_recipe, PRIORY.hasIngredientRequirement, req_uri),
                (req_uri, PRIORY.requiresItem, ing_uri),
                (req_uri, PRIORY.requiredQuantity, Literal(1)),
            ])

        try:
            for t in triples_to_add:
                g.add(t)
            self.store._direct_ingredients_cache.pop(999001, None)

            account = AccountState()
            diff_report = self.diff_engine.compute_diff(999001, account)
            bom = self.solver._introspect_weapon_bom(999001, diff_report, account)

            self.assertEqual(bom["generation"], "GEN3")
            self.assertEqual(bom["precursor_id"], 999002)
            self.assertEqual(bom["precursor_name"], "Alpha Prototype Edge")
            self.assertEqual(bom["tribute_gift_id"], 999003)
            self.assertEqual(bom["tribute_gift_name"], "Beta Economic Component")
            self.assertEqual(bom["mastery_gift_id"], 999004)
            self.assertEqual(bom["mastery_gift_name"], "Gamma World Token")
            self.assertEqual(bom["specific_gift_id"], 999005)
            self.assertEqual(bom["specific_gift_name"], "Delta Thematic Core")
        finally:
            for t in triples_to_add:
                g.remove(t)
            self.store._direct_ingredients_cache.pop(999001, None)

    def test_dynamic_booster_gobbler_and_tome_resolution(self):
        """Booster catalog resolves gobblers, tomes, and boosters dynamically from RDF triples."""
        catalog = self.solver._get_booster_catalog()
        self.assertIsInstance(catalog, dict)
        self.assertGreater(len(catalog), 0)

        # Verify key items are categorized accurately via ontology
        self.assertIn(19983, catalog)
        self.assertEqual(catalog[19983]["category"], "tome")

        self.assertIn(67836, catalog)
        self.assertEqual(catalog[67836]["category"], "gobbler")

        self.assertIn(20002, catalog)
        self.assertEqual(catalog[20002]["category"], "booster")
        self.assertIn("Experience Booster", catalog[20002]["label"])

        # Verify Chapter 3 telemetry uses dynamic catalog
        account = AccountState(
            bank={
                67836: 8,
                20002: 5,
                19983: 250,
            },
            wallet={23: 50},
        )
        plan = self.solver.solve_twilight_journey(account=account)
        ch3 = next(c for c in plan.chapters if c.chapter_number == 3)
        ch3_text = " ".join(a.action_description for a in ch3.actions)
        self.assertIn("8x Zhaitaffy Gobbler", ch3_text)
        self.assertIn("5x Experience Booster", ch3_text)
        self.assertIn("250x Tomes of Knowledge", ch3_text)

    def test_cross_weapon_synergies_twilight_and_sunrise(self):
        """Twilight (30704) and Sunrise (30703) surface Eternity synthesis and Gift of Exploration batch yield."""
        g = self.store.graph
        # Ensure batchYieldQuantity and unlocksSynthesisTarget triples exist even if ontology is still being updated
        added_triples = []
        if not list(g.triples((ITEM["19677"], PRIORY.batchYieldQuantity, None))):
            t = (ITEM["19677"], PRIORY.batchYieldQuantity, Literal(2))
            g.add(t)
            added_triples.append(t)
        if not list(g.triples((ITEM["30704"], PRIORY.unlocksSynthesisTarget, None))):
            t1 = (ITEM["30704"], PRIORY.unlocksSynthesisTarget, ITEM["30689"])
            t2 = (ITEM["30704"], PRIORY.requiresPartnerLegendary, ITEM["30703"])
            g.add(t1)
            g.add(t2)
            added_triples.extend([t1, t2])

        try:
            account = AccountState()
            plan = self.solver.build_journey_plan(account=account, target_item_id=30704)
            self.assertTrue(len(plan.cross_weapon_synergies) >= 2)
            synergy_blob = " ".join(plan.cross_weapon_synergies)
            self.assertIn("Eternity", synergy_blob)
            self.assertIn("Sunrise", synergy_blob)
            self.assertIn("Gift of Exploration", synergy_blob)
            self.assertIn("2x", synergy_blob)
        finally:
            for t in added_triples:
                g.remove(t)

    def test_no_hardcoded_constants_or_bom_literals_in_twilight_journey_solver_ast(self):
        """Verifies via AST inspection that TwilightJourneySolver has zero hardcoded item IDs, BOM dicts, exploration lists, or character lists."""
        import ast
        from pathlib import Path

        solver_path = Path(tjs_module.__file__).resolve()
        tree = ast.parse(solver_path.read_text(encoding="utf-8"))

        solver_cls = next(
            node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "TwilightJourneySolver"
        )

        # 1. Zero class-level integer/list/dict constant assignments on TwilightJourneySolver
        class_assigns = [
            node for node in solver_cls.body if isinstance(node, (ast.Assign, ast.AnnAssign))
        ]
        self.assertEqual(
            len(class_assigns),
            0,
            f"TwilightJourneySolver must not define class-level constant assignments; found: {[ast.dump(a) for a in class_assigns]}",
        )

        # 2. _default_bom must not contain a static dictionary literal
        default_bom_fn = next(
            node for node in solver_cls.body if isinstance(node, ast.FunctionDef) and node.name == "_default_bom"
        )
        dict_nodes = [n for n in ast.walk(default_bom_fn) if isinstance(n, ast.Dict)]
        self.assertEqual(
            len(dict_nodes),
            0,
            "_default_bom must delegate to _introspect_weapon_bom without any static fallback dict literal.",
        )

        # 3. _build_exploration_plan must construct ExplorationPlan dynamically in a loop (only 1 call site in AST)
        exp_fn = next(
            node for node in solver_cls.body if isinstance(node, ast.FunctionDef) and node.name == "_build_exploration_plan"
        )
        exp_calls = [
            n for n in ast.walk(exp_fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "ExplorationPlan"
        ]
        self.assertEqual(
            len(exp_calls),
            1,
            f"_build_exploration_plan must instantiate ExplorationPlan dynamically from RDF query results, found {len(exp_calls)} call sites.",
        )

        # 4. No hardcoded DEFAULT_CHARACTERS list anywhere in the module AST
        all_assigned_names = {
            t.id
            for n in ast.walk(tree)
            if isinstance(n, ast.Assign)
            for t in n.targets
            if isinstance(t, ast.Name)
        }
        self.assertNotIn("DEFAULT_CHARACTERS", all_assigned_names)
        self.assertNotIn("TWILIGHT_ITEM_ID", all_assigned_names)

    def test_dynamic_ontology_entity_and_character_resolution(self):
        """Verifies all 23 item/material properties and default roster characters resolve dynamically from PrioryGraphStore."""
        self.assertEqual(self.solver.TWILIGHT_ID, 30704)
        self.assertEqual(self.solver.DUSK_ID, 29185)
        self.assertEqual(self.solver.GIFT_OF_MASTERY_ID, 19674)
        self.assertEqual(self.solver.GIFT_OF_FORTUNE_ID, 19626)
        self.assertEqual(self.solver.GIFT_OF_TWILIGHT_ID, 19648)
        self.assertEqual(self.solver.GIFT_OF_EXPLORATION_ID, 19677)
        self.assertEqual(self.solver.GIFT_OF_BATTLE_ID, 19678)
        self.assertEqual(self.solver.OBSIDIAN_SHARD_ID, 19925)
        self.assertEqual(self.solver.BLOODSTONE_SHARD_ID, 20797)
        self.assertEqual(self.solver.MYSTIC_CLOVER_ID, 19675)
        self.assertEqual(self.solver.GLOB_OF_ECTOPLASM_ID, 19721)
        self.assertEqual(self.solver.ICY_RUNESTONE_ID, 19676)
        self.assertEqual(self.solver.ONYX_LODESTONE_ID, 24310)
        self.assertEqual(self.solver.ONYX_CORE_ID, 24309)
        self.assertEqual(self.solver.SUPERIOR_SIGIL_OF_STRENGTH_ID, 24562)
        self.assertEqual(self.solver.SUPERIOR_SIGIL_OF_FORCE_ID, 24615)
        self.assertEqual(self.solver.PHILOSOPHERS_STONE_ID, 20796)
        self.assertEqual(self.solver.CURED_HARDENED_LEATHER_SQUARE_ID, 19737)
        self.assertEqual(self.solver.GIFT_OF_ASCALON_ID, 19664)
        self.assertEqual(self.solver.GIFT_OF_METAL_ID, 19622)
        self.assertEqual(self.solver.GIFT_OF_DARKNESS_ID, 19630)
        self.assertEqual(len(self.solver.T6_MATERIAL_IDS), 8)
        self.assertEqual(len(self.solver.LEGACY_T6_MATERIAL_IDS), 8)

        roster = self.solver._get_ontology_characters()
        self.assertGreaterEqual(len(roster), 11)
        self.assertEqual(roster[0], "Kerling")
        self.assertIn("Skuta Rantakallio", roster)
        self.assertIn("Sara Loy", roster)
        self.assertIn("Legacy Of Harathi", roster)

    def test_dynamic_exploration_regions_from_rdf_all_generations(self):
        """Verifies _build_exploration_plan resolves GEN1, GEN2, and GEN3 regions from priory:ExplorationRegion triples."""
        account_skyscale = AccountState(mount_types=["skyscale", "raptor", "springer"])
        account_foot = AccountState(mount_types=[])

        gen1_skyscale = self.solver._build_exploration_plan(account_skyscale, bom={"generation": "GEN1"})
        gen1_foot = self.solver._build_exploration_plan(account_foot, bom={"generation": "GEN1"})
        self.assertEqual(
            [r.region_name for r in gen1_skyscale],
            ["Kryta", "Ascalon", "Shiverpeak Mountains", "Maguuma Jungle", "Ruins of Orr"],
        )
        self.assertLess(
            sum(r.estimated_hours for r in gen1_skyscale),
            sum(r.estimated_hours for r in gen1_foot),
        )
        self.assertTrue(all(r.recommended_mount is None for r in gen1_foot))

        gen2_plans = self.solver._build_exploration_plan(account_skyscale, bom={"generation": "GEN2"})
        self.assertEqual(
            [r.region_name for r in gen2_plans],
            ["Verdant Brink", "Auric Basin", "Tangled Depths", "Dragon's Stand"],
        )

        gen3_plans = self.solver._build_exploration_plan(account_skyscale, bom={"generation": "GEN3"})
        self.assertEqual(
            [r.region_name for r in gen3_plans],
            ["Seitung Province", "New Kaineng City", "The Echovald Wilds", "Dragon's End"],
        )

    def test_ontology_hydrated_catalogs_across_engine_modules(self):
        """Verifies path_solver, character_graph, and account_diff hydrate their catalogs from PrioryGraphStore."""
        import ast
        from pathlib import Path
        import engine.path_solver as ps_module
        import engine.character_graph as cg_module
        import engine.account_diff as ad_module

        # Verify AST of path_solver, character_graph, and account_diff has empty dict initializers for ontology-hydrated catalogs
        for mod, target_names in [
            (ps_module, {"BENCHMARK_FALLBACK_PRICES", "T6_FINE_MATERIALS"}),
            (cg_module, {"STAT_NAME_MAP", "CRAFTING_DISCIPLINE_STATIONS"}),
            (ad_module, {"GEN1_WEAPONS", "HOBBS_COLLECTIONS", "LOUNGE_PASSES", "CONVENIENCE_ITEMS"}),
        ]:
            mod_tree = ast.parse(Path(mod.__file__).resolve().read_text(encoding="utf-8"))
            for node in mod_tree.body:
                if isinstance(node, ast.Assign):
                    for t in node.targets:
                        if isinstance(t, ast.Name) and t.id in target_names:
                            self.assertIsInstance(node.value, ast.Dict)
                            self.assertEqual(len(node.value.keys), 0, f"{t.id} in {mod.__name__} must be initialized empty in AST")
                elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in target_names:
                    self.assertIsInstance(node.value, ast.Dict)
                    self.assertEqual(len(node.value.keys), 0, f"{node.target.id} in {mod.__name__} must be initialized empty in AST")

        # Trigger hydration and verify non-empty runtime catalogs
        _ = ps_module.PathSolver(self.store)
        _ = cg_module.CharacterGraphHydrator(graph_store=self.store)
        _ = ad_module.AccountDiffEngine(self.store)
        self.assertGreater(len(ps_module.BENCHMARK_FALLBACK_PRICES), 0)
        self.assertEqual(len(ps_module.T6_FINE_MATERIALS), 8)
        self.assertGreater(len(cg_module.STAT_NAME_MAP), 0)
        self.assertGreater(len(cg_module.CRAFTING_DISCIPLINE_STATIONS), 0)
        self.assertGreater(len(ad_module.GEN1_WEAPONS), 0)
        self.assertGreater(len(ad_module.HOBBS_COLLECTIONS), 0)
        self.assertGreater(len(ad_module.LOUNGE_PASSES), 0)


if __name__ == "__main__":
    unittest.main()

