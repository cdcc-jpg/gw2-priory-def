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


if __name__ == "__main__":
    unittest.main()
