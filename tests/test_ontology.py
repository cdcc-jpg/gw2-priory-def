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
        for ttl in (REF_REPO / "vocab").rglob("*.ttl"):
            data_graph.parse(ttl, format="turtle")

        # 3. Load Instances
        for ttl in (DEF_REPO / "ontology" / "instances").glob("*.ttl"):
            data_graph.parse(ttl, format="turtle")
        boosters_ttl = DEF_REPO / "ontology" / "instances" / "shared" / "boosters_and_buffs.ttl"
        if boosters_ttl.exists():
            data_graph.parse(boosters_ttl, format="turtle")
        dusk_ttl = DEF_REPO / "ontology" / "instances" / "shared" / "dusk_precursor_collection.ttl"
        if dusk_ttl.exists():
            data_graph.parse(dusk_ttl, format="turtle")
        convenience_ttl = DEF_REPO / "ontology" / "instances" / "shared" / "convenience_and_lounges.ttl"
        if convenience_ttl.exists():
            data_graph.parse(convenience_ttl, format="turtle")
        eternity_ttl = DEF_REPO / "ontology" / "instances" / "shared" / "eternity_and_post_craft.ttl"
        if eternity_ttl.exists():
            data_graph.parse(eternity_ttl, format="turtle")
        regional_ttl = DEF_REPO / "ontology" / "instances" / "shared" / "regional_expansion_materials.ttl"
        if regional_ttl.exists():
            data_graph.parse(regional_ttl, format="turtle")
        vendors_ttl = DEF_REPO / "ontology" / "instances" / "shared" / "legendary_milestone_vendors.ttl"
        if vendors_ttl.exists():
            data_graph.parse(vendors_ttl, format="turtle")
        common_items_ttl = DEF_REPO / "ontology" / "instances" / "shared" / "common_items.ttl"
        if common_items_ttl.exists():
            data_graph.parse(common_items_ttl, format="turtle")
        base_comp_ttl = DEF_REPO / "ontology" / "instances" / "shared" / "legendary_base_components.ttl"
        if base_comp_ttl.exists():
            data_graph.parse(base_comp_ttl, format="turtle")

        # 4. Load SHACL Shapes
        shacl_graph = rdflib.Graph()
        shacl_graph.parse(DEF_REPO / "ontology" / "priory_shacl.ttl", format="turtle")
        for ttl in (DEF_REPO / "ontology" / "shapes").rglob("*.ttl"):
            shacl_graph.parse(ttl, format="turtle")

        # Validate
        conforms, results_graph, results_text = pyshacl.validate(
            data_graph,
            shacl_graph=shacl_graph,
            inference="rdfs",
            abort_on_first=False
        )

        self.assertTrue(conforms, f"SHACL validation failed:\n{results_text}")

    def test_vip_lounges_and_convenience_gizmos(self):
        """Validates all 7 categories of Master Convenience, VIP Lounges, Contracts, Converters, Tomes, and Upgrades."""
        g = rdflib.Graph()
        g.parse(DEF_REPO / "ontology" / "priory_core.ttl", format="turtle")
        g.parse(DEF_REPO / "ontology" / "instances" / "shared" / "convenience_and_lounges.ttl", format="turtle")

        PRIORY = rdflib.Namespace("https://priory.gw2/def/")
        ITEM = rdflib.Namespace("https://priory.gw2/id/item/")

        # 1. Category 1: VIP Lounge Passes (12 items)
        vip_passes = {
            81664: ("Mistlock Sanctuary Passkey", "[&AgEAPwEA]"),
            90011: ("Armistice Bastion Pass", "[&AgGbXwEA]"),
            98048: ("Thousand Seas Pavilion Pass", "[&AgEAfwEA]"),
            83457: ("Passkey to the Lily of the Elon", "[&AgEBRgEA]"),
            49149: ("Royal Terrace Pass", "[&AgH9vwAA]"),
            49449: ("Captain's Airship Pass", "[&AgEpwQAA]"),
            75479: ("Noble's Folly Pass", "[&AgHnJgEA]"),
            79500: ("Lava Lounge Pass", "[&AgGMNgEA]"),
            82791: ("Champion's Rest Pass", "[&AgFnQwEA]"),
            97009: ("Arborstone Portal Scroll", "[&AgHxegEA]"),
            100788: ("Wizard's Tower Teleportation Scroll", "[&AgG0iQEA]"),
            92055: ("Invitation to the Eye of the North", "[&AgH3ZwEA]"),
        }

        for gw2_id, (expected_label, expected_chat_link) in vip_passes.items():
            item_uri = ITEM[str(gw2_id)]
            self.assertIn((item_uri, rdflib.RDF.type, PRIORY.VIPLoungePass), g)
            self.assertIn((item_uri, PRIORY.gw2Id, rdflib.Literal(gw2_id)), g)
            self.assertIn((item_uri, rdflib.RDFS.label, rdflib.Literal(expected_label, lang="en")), g)
            self.assertIn((item_uri, PRIORY.chatCode, rdflib.Literal(expected_chat_link)), g)
            self.assertIn((item_uri, PRIORY.hasCraftingStations, rdflib.Literal(True)), g)
            self.assertIn((item_uri, PRIORY.hasMysticForge, rdflib.Literal(True)), g)
            self.assertIn((item_uri, PRIORY.hasBank, rdflib.Literal(True)), g)
            self.assertIn((item_uri, PRIORY.hasTradingPost, rdflib.Literal(True)), g)
            self.assertIn((item_uri, PRIORY.hasVendor, rdflib.Literal(True)), g)
            self.assertTrue((item_uri, PRIORY.hasInstantReturn, None) in g)

        # 2. Category 2: Infinite Salvage Tools (4 items)
        salvage_tools = {
            44602: ("Copper-Fed Salvage-o-Matic", "[&AgE6rgAA]", 3),
            67027: ("Silver-Fed Salvage-o-Matic", "[&AgHTBQEA]", 60),
            87400: ("Runecrafter's Salvage-o-Matic", "[&AgFoVQEA]", 30),
            93121: ("Endless Upgrade Extractor", "[&AgHxmwEA]", 0),
        }

        for gw2_id, (expected_label, expected_chat_link, cost) in salvage_tools.items():
            item_uri = ITEM[str(gw2_id)]
            self.assertIn((item_uri, rdflib.RDF.type, PRIORY.InfiniteSalvageItem), g)
            self.assertIn((item_uri, PRIORY.gw2Id, rdflib.Literal(gw2_id)), g)
            self.assertIn((item_uri, rdflib.RDFS.label, rdflib.Literal(expected_label, lang="en")), g)
            self.assertIn((item_uri, PRIORY.chatCode, rdflib.Literal(expected_chat_link)), g)
            self.assertIn((item_uri, PRIORY.salvageCostPerUse, rdflib.Literal(cost)), g)

        # 3. Category 3: Permanent Contracts (6 items)
        permanent_contracts = {
            35976: ("Permanent Bank Access Contract", "[&AgEgDAEA]"),
            35977: ("Permanent Black Lion Merchant Contract", "[&AgEhDAEA]"),
            35978: ("Permanent Trading Post Express Contract", "[&AgEiDAEA]"),
            35984: ("Permanent Hair Stylist Contract", "[&AgEoDAEA]"),
            84950: ("Permanent Tool Delivery Box", "[&AgH6SwEA]"),
            91876: ("Endless Repair Canister", "[&AgH0ZgEA]"),
        }

        for gw2_id, (expected_label, expected_chat_link) in permanent_contracts.items():
            item_uri = ITEM[str(gw2_id)]
            self.assertIn((item_uri, rdflib.RDF.type, PRIORY.PermanentContract), g)
            self.assertIn((item_uri, PRIORY.gw2Id, rdflib.Literal(gw2_id)), g)
            self.assertIn((item_uri, rdflib.RDFS.label, rdflib.Literal(expected_label, lang="en")), g)
            self.assertIn((item_uri, PRIORY.chatCode, rdflib.Literal(expected_chat_link)), g)

        # 4. Category 4: Converters & Gobblers (11 items)
        converters = {
            67393: ("Candy Corn Gobbler", "[&AgFBBwEA]"),
            67836: ("Zhaitaffy Gobbler", "[&AgFsCQEA]"),
            92585: ("Snowflake Gobbler", "[&AgGpaQEA]"),
            67280: ("Ley-Energy Matter Converter", "[&AgGgCgEA]"),
            66624: ("Karmic Converter", "[&AgHgAQEA]"),
            92209: ("Gleam of Sentience", "[&AgExaQEA]"),
            80087: ("Sentient Anomaly", "[&AgFnOAEA]"),
            79558: ("Sentient Aberration", "[&AgEmOwEA]"),
            81781: ("Sentient Seed", "[&AgFlPQEA]"),
            81120: ("Sentient Singularity", "[&AgHgPwEA]"),
            90002: ("Hlish Hiss", "[&AgHiXwEA]"),
        }

        for gw2_id, (expected_label, expected_chat_link) in converters.items():
            item_uri = ITEM[str(gw2_id)]
            self.assertIn((item_uri, rdflib.RDF.type, PRIORY.CurrencyConverter), g)
            self.assertIn((item_uri, PRIORY.gw2Id, rdflib.Literal(gw2_id)), g)
            self.assertIn((item_uri, rdflib.RDFS.label, rdflib.Literal(expected_label, lang="en")), g)
            self.assertIn((item_uri, PRIORY.chatCode, rdflib.Literal(expected_chat_link)), g)

        # 5. Category 5: Portal Tomes & Teleporters (6 items)
        portal_tomes = {
            80332: ("Living World Season 3 Portal Tome", "[&AgHMTgEA]"),
            87508: ("Living World Season 4 Portal Tome", "[&AgFUVQEA]"),
            92850: ("Icebrood Saga Portal Tome", "[&AgGiaQEA]"),
            90335: ("Recharging Teleport to Friend", "[&AgHfYAEA]"),
            79744: ("Exalted Portal Stone", "[&AgEwTgEA]"),
            20030: ("Hall of Monuments Portal Stone", "[&AgE+TgAA]"),
        }

        for gw2_id, (expected_label, expected_chat_link) in portal_tomes.items():
            item_uri = ITEM[str(gw2_id)]
            self.assertIn((item_uri, rdflib.RDF.type, PRIORY.PortalTome), g)
            self.assertIn((item_uri, PRIORY.gw2Id, rdflib.Literal(gw2_id)), g)
            self.assertIn((item_uri, rdflib.RDFS.label, rdflib.Literal(expected_label, lang="en")), g)
            self.assertIn((item_uri, PRIORY.chatCode, rdflib.Literal(expected_chat_link)), g)

        # 6. Category 6: Portable Mystic Forge (3 items)
        mystic_forge_items = {
            70010: ("Permanent Mystic Forge Conduit", "[&AgF6EQEA]"),
            35727: ("Mystic Forge Conduit", "[&AgG/IgAA]"),
            68093: ("Mystic Forge Node", "[&AgFdCgEA]"),
        }

        for gw2_id, (expected_label, expected_chat_link) in mystic_forge_items.items():
            item_uri = ITEM[str(gw2_id)]
            self.assertIn((item_uri, rdflib.RDF.type, PRIORY.ConvenienceGizmo), g)
            self.assertIn((item_uri, PRIORY.gw2Id, rdflib.Literal(gw2_id)), g)
            self.assertIn((item_uri, rdflib.RDFS.label, rdflib.Literal(expected_label, lang="en")), g)
            self.assertIn((item_uri, PRIORY.chatCode, rdflib.Literal(expected_chat_link)), g)
            self.assertIn((item_uri, PRIORY.hasMysticForge, rdflib.Literal(True)), g)

        # 7. Category 7: Account Storage Upgrades (3 items)
        storage_upgrades = {
            67071: ("Shared Inventory Slot", "[&AgH/BQEA]"),
            42932: ("Material Storage Expander", "[&AgG0pwAA]"),
            19995: ("Bank Tab Expansion", "[&AgEbTgAA]"),
        }

        for gw2_id, (expected_label, expected_chat_link) in storage_upgrades.items():
            item_uri = ITEM[str(gw2_id)]
            self.assertIn((item_uri, rdflib.RDF.type, PRIORY.AccountStorageUpgrade), g)
            self.assertIn((item_uri, PRIORY.gw2Id, rdflib.Literal(gw2_id)), g)
            self.assertIn((item_uri, rdflib.RDFS.label, rdflib.Literal(expected_label, lang="en")), g)
            self.assertIn((item_uri, PRIORY.chatCode, rdflib.Literal(expected_chat_link)), g)

    def test_eternity_and_post_craft_architecture(self):
        """Validates the Eternity Commercial Loop, Post-Forge Binding Architecture, and SafeStagingBag containers."""
        g = rdflib.Graph()
        g.parse(DEF_REPO / "ontology" / "priory_core.ttl", format="turtle")
        g.parse(DEF_REPO / "ontology" / "instances" / "shared" / "eternity_and_post_craft.ttl", format="turtle")

        PRIORY = rdflib.Namespace("https://priory.gw2/def/")
        ITEM = rdflib.Namespace("https://priory.gw2/id/item/")
        RECIPE = rdflib.Namespace("https://priory.gw2/id/recipe/")
        WEAPON = rdflib.Namespace("https://priory.gw2/ref/weapon/")
        RARITY = rdflib.Namespace("https://priory.gw2/ref/rarity/")

        # 1. Eternity (item:30689)
        eternity = ITEM["30689"]
        self.assertIn((eternity, rdflib.RDF.type, PRIORY.LegendaryWeapon), g)
        self.assertIn((eternity, PRIORY.gw2Id, rdflib.Literal(30689)), g)
        self.assertIn((eternity, rdflib.RDFS.label, rdflib.Literal("Eternity", lang="en")), g)
        self.assertIn((eternity, PRIORY.chatCode, rdflib.Literal("[&AgExZwAA]")), g)
        self.assertIn((eternity, PRIORY.hasRarity, RARITY.Legendary), g)
        self.assertIn((eternity, PRIORY.hasWeaponType, WEAPON.Greatsword), g)
        self.assertIn((eternity, PRIORY.isAccountBound, rdflib.Literal(False)), g)
        self.assertIn((eternity, PRIORY.producedBy, RECIPE.recipe_forge_eternity_unbound), g)
        self.assertIn((eternity, PRIORY.producedBy, RECIPE.recipe_forge_eternity_bound), g)

        # 2. Sunrise (item:30703)
        sunrise = ITEM["30703"]
        self.assertIn((sunrise, rdflib.RDF.type, PRIORY.LegendaryWeapon), g)
        self.assertIn((sunrise, PRIORY.gw2Id, rdflib.Literal(30703)), g)
        self.assertIn((sunrise, rdflib.RDFS.label, rdflib.Literal("Sunrise", lang="en")), g)
        self.assertIn((sunrise, PRIORY.chatCode, rdflib.Literal("[&AgEvZwAA]")), g)
        self.assertIn((sunrise, PRIORY.hasRarity, RARITY.Legendary), g)
        self.assertIn((sunrise, PRIORY.hasWeaponType, WEAPON.Greatsword), g)
        self.assertIn((sunrise, PRIORY.isAccountBound, rdflib.Literal(False)), g)

        # 3. Armory Memories (item:94875 & item:94917)
        mem_twilight = ITEM["94875"]
        self.assertIn((mem_twilight, rdflib.RDF.type, PRIORY.CraftingMaterial), g)
        self.assertIn((mem_twilight, PRIORY.gw2Id, rdflib.Literal(94875)), g)
        self.assertIn((mem_twilight, rdflib.RDFS.label, rdflib.Literal("Memory of Twilight", lang="en")), g)
        self.assertIn((mem_twilight, PRIORY.chatCode, rdflib.Literal("[&AgFucwEA]")), g)
        self.assertIn((mem_twilight, PRIORY.hasRarity, RARITY.Legendary), g)
        self.assertIn((mem_twilight, PRIORY.isAccountBound, rdflib.Literal(True)), g)

        mem_sunrise = ITEM["94917"]
        self.assertIn((mem_sunrise, rdflib.RDF.type, PRIORY.CraftingMaterial), g)
        self.assertIn((mem_sunrise, PRIORY.gw2Id, rdflib.Literal(94917)), g)
        self.assertIn((mem_sunrise, rdflib.RDFS.label, rdflib.Literal("Memory of Sunrise", lang="en")), g)
        self.assertIn((mem_sunrise, PRIORY.chatCode, rdflib.Literal("[&AgGdcwEA]")), g)
        self.assertIn((mem_sunrise, PRIORY.hasRarity, RARITY.Legendary), g)
        self.assertIn((mem_sunrise, PRIORY.isAccountBound, rdflib.Literal(True)), g)

        # 4. Unbound Forge Recipe
        rec_unbound = RECIPE.recipe_forge_eternity_unbound
        self.assertIn((rec_unbound, rdflib.RDF.type, PRIORY.MysticForgeRecipe), g)
        self.assertIn((rec_unbound, PRIORY.producesItem, eternity), g)
        self.assertIn((rec_unbound, PRIORY.outputQuantity, rdflib.Literal(1)), g)

        # 5. Bound Forge Recipe
        rec_bound = RECIPE.recipe_forge_eternity_bound
        self.assertIn((rec_bound, rdflib.RDF.type, PRIORY.MysticForgeRecipe), g)
        self.assertIn((rec_bound, PRIORY.producesItem, eternity), g)
        self.assertIn((rec_bound, PRIORY.outputQuantity, rdflib.Literal(1)), g)

        # 6. Safe Staging Bags & Safe Boxes (item:67390, 9594, 9584, 8948)
        safe_bags = {
            67390: ("20-Slot Invisible Bag", "[&AgG5VAAA]"),
            9594: ("20 Slot Safe Box", "[&AgF6JQAA]"),
            9584: ("20 Slot Invisible Pack", "[&AgFwJQAA]"),
            8948: ("20 Slot Invisible Bag", "[&AgH0IgAA]"),
        }
        for gw2_id, (expected_label, expected_chat_link) in safe_bags.items():
            bag_uri = ITEM[str(gw2_id)]
            self.assertIn((bag_uri, rdflib.RDF.type, PRIORY.SafeStagingBag), g)
            self.assertIn((bag_uri, PRIORY.gw2Id, rdflib.Literal(gw2_id)), g)
            self.assertIn((bag_uri, rdflib.RDFS.label, rdflib.Literal(expected_label, lang="en")), g)
            self.assertIn((bag_uri, PRIORY.chatCode, rdflib.Literal(expected_chat_link)), g)
            self.assertIn((bag_uri, PRIORY.bagSlots, rdflib.Literal(20)), g)

    def test_regional_expansion_leaf_gifts_and_vendors(self):
        """Validates the grounding of intermediate expansion leaf gifts to vendor exchanges, map currencies, and recipes."""
        g = rdflib.Graph()
        g.parse(DEF_REPO / "ontology" / "priory_core.ttl", format="turtle")
        for ttl in (DEF_REPO / "ontology" / "vocab").glob("*.ttl"):
            g.parse(ttl, format="turtle")
        g.parse(DEF_REPO / "ontology" / "instances" / "shared" / "regional_expansion_materials.ttl", format="turtle")
        g.parse(DEF_REPO / "ontology" / "instances" / "shared" / "legendary_milestone_vendors.ttl", format="turtle")
        g.parse(DEF_REPO / "ontology" / "instances" / "shared" / "legendary_base_components.ttl", format="turtle")

        PRIORY = rdflib.Namespace("https://priory.gw2/def/")
        ITEM = rdflib.Namespace("https://priory.gw2/id/item/")
        RECIPE = rdflib.Namespace("https://priory.gw2/id/recipe/")
        CURRENCY = rdflib.Namespace("https://priory.gw2/ref/currency/")

        # 1. Heart of Thorns Grounding
        fleet_gift = ITEM["70797"]
        vendor_fleet = ITEM["vendor_fleet"]
        self.assertIn((fleet_gift, PRIORY.acquiredVia, vendor_fleet), g)
        self.assertIn((vendor_fleet, rdflib.RDF.type, PRIORY.VendorExchangePath), g)
        self.assertIn((vendor_fleet, PRIORY.requiresCurrency, CURRENCY.AirshipPart), g)
        self.assertIn((vendor_fleet, PRIORY.requiredQuantity, rdflib.Literal(250)), g)
        self.assertIn((vendor_fleet, PRIORY.producesItem, fleet_gift), g)

        tarir_gift = ITEM["71943"]
        vendor_tarir = ITEM["vendor_tarir"]
        self.assertIn((tarir_gift, PRIORY.acquiredVia, vendor_tarir), g)
        self.assertIn((vendor_tarir, rdflib.RDF.type, PRIORY.VendorExchangePath), g)
        self.assertIn((vendor_tarir, PRIORY.requiresCurrency, CURRENCY.LumpOfAurillium), g)
        self.assertIn((vendor_tarir, PRIORY.requiredQuantity, rdflib.Literal(250)), g)
        self.assertIn((vendor_tarir, PRIORY.producesItem, tarir_gift), g)

        chak_gift = ITEM["74677"]
        vendor_chak = ITEM["vendor_chak"]
        self.assertIn((chak_gift, PRIORY.acquiredVia, vendor_chak), g)
        self.assertIn((vendor_chak, rdflib.RDF.type, PRIORY.VendorExchangePath), g)
        self.assertIn((vendor_chak, PRIORY.requiresCurrency, CURRENCY.LeyLineCrystal), g)
        self.assertIn((vendor_chak, PRIORY.requiredQuantity, rdflib.Literal(250)), g)
        self.assertIn((vendor_chak, PRIORY.producesItem, chak_gift), g)

        maguuma_gift = ITEM["75919"]
        maguuma_path = ITEM["path_maguuma_map_completion"]
        self.assertIn((maguuma_gift, PRIORY.acquiredVia, maguuma_path), g)
        self.assertIn((maguuma_path, rdflib.RDF.type, PRIORY.AchievementCollectionPath), g)

        # 2. Path of Fire Grounding
        desert_mastery = ITEM["82414"]
        forge_desert = RECIPE["forge_gift_of_desert_mastery"]
        self.assertIn((desert_mastery, PRIORY.producedBy, forge_desert), g)
        self.assertIn((forge_desert, rdflib.RDF.type, PRIORY.MysticForgeRecipe), g)

        pof_regional_gifts = [
            (ITEM["83694"], ITEM["vendor_oasis"], "Gift of the Oasis"),
            (ITEM["83008"], ITEM["vendor_highlands"], "Gift of the Highlands"),
            (ITEM["83471"], ITEM["vendor_riverlands"], "Gift of the Riverlands"),
            (ITEM["83416"], ITEM["vendor_desolation"], "Gift of the Desolation"),
        ]
        for gift_uri, vendor_uri, label in pof_regional_gifts:
            self.assertIn((gift_uri, PRIORY.acquiredVia, vendor_uri), g)
            self.assertIn((vendor_uri, rdflib.RDF.type, PRIORY.VendorExchangePath), g)
            self.assertIn((vendor_uri, PRIORY.requiresCurrency, CURRENCY.TradeContract), g)
            self.assertIn((vendor_uri, PRIORY.requiredQuantity, rdflib.Literal(250)), g)

        incense = ITEM["83318"]
        vendor_vabbi = ITEM["vendor_vabbi"]
        self.assertIn((incense, PRIORY.acquiredVia, vendor_vabbi), g)
        self.assertIn((vendor_vabbi, rdflib.RDF.type, PRIORY.VendorExchangePath), g)
        self.assertIn((vendor_vabbi, PRIORY.requiresCurrency, CURRENCY.ElegyMosaic), g)

        # 3. Secrets of the Obscure Grounding
        amnytas_gift = ITEM["100140"]
        lyhr_amnytas = ITEM["vendor_lyhr_amnytas"]
        self.assertIn((amnytas_gift, PRIORY.acquiredVia, ITEM["vendor_lyhr"]), g)
        self.assertIn((amnytas_gift, PRIORY.acquiredVia, lyhr_amnytas), g)
        self.assertIn((lyhr_amnytas, rdflib.RDF.type, PRIORY.VendorExchangePath), g)
        self.assertIn((lyhr_amnytas, PRIORY.requiresCurrency, CURRENCY.PinchOfStardust), g)
        self.assertIn((lyhr_amnytas, PRIORY.requiredQuantity, rdflib.Literal(250)), g)

        cosmos_gift = ITEM["100424"]
        lyhr_cosmos = ITEM["vendor_lyhr_cosmos"]
        self.assertIn((cosmos_gift, PRIORY.acquiredVia, ITEM["vendor_lyhr"]), g)
        self.assertIn((cosmos_gift, PRIORY.acquiredVia, lyhr_cosmos), g)
        self.assertIn((lyhr_cosmos, rdflib.RDF.type, PRIORY.VendorExchangePath), g)
        self.assertIn((lyhr_cosmos, PRIORY.requiresCurrency, CURRENCY.StaticCharge), g)
        self.assertIn((lyhr_cosmos, PRIORY.requiredQuantity, rdflib.Literal(250)), g)

        celestial_gift = ITEM["100063"]
        lyhr_celestial = ITEM["vendor_lyhr_celestial"]
        self.assertIn((celestial_gift, PRIORY.acquiredVia, ITEM["vendor_lyhr"]), g)
        self.assertIn((celestial_gift, PRIORY.acquiredVia, lyhr_celestial), g)
        self.assertIn((lyhr_celestial, rdflib.RDF.type, PRIORY.VendorExchangePath), g)
        self.assertIn((lyhr_celestial, PRIORY.requiresCurrency, CURRENCY.CaseOfCapturedLightning), g)
        self.assertIn((lyhr_celestial, PRIORY.requiredQuantity, rdflib.Literal(250)), g)

        # 4. Competitive Grounding
        mists_gift = ITEM["79549"]
        forge_mists = RECIPE["forge_gift_of_the_mists"]
        self.assertIn((mists_gift, PRIORY.producedBy, forge_mists), g)
        self.assertIn((forge_mists, rdflib.RDF.type, PRIORY.MysticForgeRecipe), g)


if __name__ == "__main__":
    unittest.main()


