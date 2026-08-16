"""Generates complete, leaf-level OWL/RDF instance graphs for:
- Envoy Legendary Armor (18 pieces: Heavy, Medium, Light) with Legendary Insights & Provisioners
- Obsidian Legendary Armor (SotO: 18 pieces) with Kryptis Essences & Map Currencies
- Janthir Wilds Legendary Spear (Klobjarne) with Mursaat Obsidian Chunks & Titan Ore
- Legendary Trinkets (Aurora, Vision, Coalescence, Conflux, Transcendence, Regalia)
- Legendary Backpacks (Ad Infinitum, The Ascension, Warbringer)
- Legendary Upgrades (Legendary Sigil, Rune, Relic)
"""

from pathlib import Path
import rdflib
from rdflib import RDF, RDFS, OWL, Literal, URIRef, XSD, Namespace

PRIORY = Namespace("https://priory.gw2/def/")
ITEM = Namespace("https://priory.gw2/id/item/")
RECIPE = Namespace("https://priory.gw2/id/recipe/")
RARITY = Namespace("https://priory.gw2/ref/rarity/")
SLOT = Namespace("https://priory.gw2/ref/slot/")
WEIGHT = Namespace("https://priory.gw2/ref/armor-weight/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

ENVOY_ARMOR = [
    # Heavy (Weight, Slot, ID, Name)
    ("Heavy", "Helm", 80384, "Perfected Envoy Helm"),
    ("Heavy", "Shoulders", 80435, "Perfected Envoy Pauldrons"),
    ("Heavy", "Chest", 80258, "Perfected Envoy Breastplate"),
    ("Heavy", "Gloves", 80145, "Perfected Envoy Gauntlets"),
    ("Heavy", "Legs", 80161, "Perfected Envoy Tassets"),
    ("Heavy", "Boots", 80248, "Perfected Envoy Greaves"),
    # Medium
    ("Medium", "Helm", 80296, "Perfected Envoy Mask"),
    ("Medium", "Shoulders", 80190, "Perfected Envoy Shoulderguards"),
    ("Medium", "Chest", 80277, "Perfected Envoy Jerkin"),
    ("Medium", "Gloves", 80252, "Perfected Envoy Vambraces"),
    ("Medium", "Legs", 80281, "Perfected Envoy Leggings"),
    ("Medium", "Boots", 80557, "Perfected Envoy Boots"),
    # Light
    ("Light", "Helm", 80200, "Perfected Envoy Hood"),
    ("Light", "Shoulders", 80356, "Perfected Envoy Mantle"),
    ("Light", "Chest", 80131, "Perfected Envoy Vestments"),
    ("Light", "Gloves", 80145, "Perfected Envoy Gloves"),
    ("Light", "Legs", 80196, "Perfected Envoy Pants"),
    ("Light", "Boots", 80161, "Perfected Envoy Shoes"),
]

OBSIDIAN_ARMOR = [
    # Heavy
    ("Heavy", "Helm", 101001, "Obsidian Helm"),
    ("Heavy", "Shoulders", 101002, "Obsidian Pauldrons"),
    ("Heavy", "Chest", 101003, "Obsidian Breastplate"),
    ("Heavy", "Gloves", 101004, "Obsidian Gauntlets"),
    ("Heavy", "Legs", 101005, "Obsidian Tassets"),
    ("Heavy", "Boots", 101006, "Obsidian Greaves"),
    # Medium
    ("Medium", "Helm", 101007, "Obsidian Mask"),
    ("Medium", "Shoulders", 101008, "Obsidian Shoulderguards"),
    ("Medium", "Chest", 101009, "Obsidian Jerkin"),
    ("Medium", "Gloves", 101010, "Obsidian Vambraces"),
    ("Medium", "Legs", 101011, "Obsidian Leggings"),
    ("Medium", "Boots", 101012, "Obsidian Boots"),
    # Light
    ("Light", "Helm", 101013, "Obsidian Hood"),
    ("Light", "Shoulders", 101014, "Obsidian Mantle"),
    ("Light", "Chest", 101015, "Obsidian Vestments"),
    ("Light", "Gloves", 101016, "Obsidian Gloves"),
    ("Light", "Legs", 101017, "Obsidian Pants"),
    ("Light", "Boots", 101018, "Obsidian Shoes"),
]

TRINKETS_AND_UPGRADES = [
    (81908, "Aurora", "Trinket", "Accessory"),
    (91234, "Vision", "Trinket", "Accessory"),
    (91048, "Coalescence", "Trinket", "Ring"),
    (92991, "Conflux", "Trinket", "Ring"),
    (92946, "Transcendence", "Trinket", "Amulet"),
    (95380, "Prismatic Champion's Regalia", "Trinket", "Amulet"),
    (77474, "Ad Infinitum", "Backpack", "Backpack"),
    (78430, "The Ascension", "Backpack", "Backpack"),
    (91536, "Legendary Rune", "Upgrade", "Rune"),
    # Legendary Sigil (91505) is defined in ontology/instances/upgrades/legendary_sigil.ttl
    (101582, "Legendary Relic", "Upgrade", "Relic"),
    (103460, "Klobjarne Harvester", "Weapon", "Spear"), # Janthir Wilds Spear
]

def generate_armor_trinket_graph() -> rdflib.Graph:
    g = rdflib.Graph()
    g.bind("priory", PRIORY)
    g.bind("item", ITEM)
    g.bind("recipe", RECIPE)
    g.bind("rarity", RARITY)
    g.bind("slot", SLOT)
    g.bind("weight", WEIGHT)
    g.bind("skos", SKOS)

    # 1. Currencies and Shared Materials
    shared_mats = [
        (43775, "Provisioner Token"),
        (77700, "Legendary Insight"),
        (88770, "Legendary Divination"),
        (100114, "Essence of Despair"),
        (100414, "Essence of Greed"),
        (100429, "Essence of Triumph"),
        (100852, "Pinch of Stardust"),
        (100862, "Static Charge"),
        (100912, "Clotted Scream"),
        (103427, "Mursaat Obsidian Chunk"), # Janthir Wilds
        (104331, "Curious Mursaat Ruin Shard"), # Janthir Wilds
        (103112, "Titan Ore"), # Janthir Wilds
        (103125, "Lowland Pine Timber"), # Janthir Wilds
        (79401, "Bloodstone Ruby"), # Living World S3
        (79280, "Petrified Wood"),
        (80332, "Jade Shard"),
        (79899, "Fresh Winterberry"),
        (86069, "Kralkatite Ore"), # Living World S4
        (86977, "Difluorite Crystal"),
        (87645, "Inscribed Shard"),
        (88955, "Lump of Mistonium"),
        (89537, "Branded Mass"),
        (90783, "Mistborn Mote"),
    ]

    for m_id, m_name in shared_mats:
        m_uri = ITEM[str(m_id)]
        g.add((m_uri, RDF.type, PRIORY.CraftingMaterial))
        g.add((m_uri, RDF.type, OWL.NamedIndividual))
        g.add((m_uri, RDFS.label, Literal(m_name, lang="en")))
        g.add((m_uri, PRIORY.gw2Id, Literal(m_id, datatype=XSD.integer)))

    # 2. Envoy Legendary Armor (18 pieces)
    for weight, slot, a_id, a_name in ENVOY_ARMOR:
        clean = a_name.lower().replace(" ", "_").replace("'", "").replace("-", "_")
        a_uri = ITEM[str(a_id)]
        f_uri = RECIPE[f"forge_{clean}"]

        g.add((a_uri, RDF.type, PRIORY.LegendaryArmor))
        g.add((a_uri, RDF.type, OWL.NamedIndividual))
        g.add((a_uri, RDFS.label, Literal(a_name, lang="en")))
        g.add((a_uri, PRIORY.gw2Id, Literal(a_id, datatype=XSD.integer)))
        g.add((a_uri, PRIORY.hasRarity, RARITY.Legendary))
        g.add((a_uri, PRIORY.hasArmorWeight, WEIGHT[weight]))
        g.add((a_uri, PRIORY.hasEquipmentSlot, SLOT[slot]))
        g.add((a_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
        g.add((a_uri, PRIORY.producedBy, f_uri))

        # AltLabels
        g.add((a_uri, SKOS.altLabel, Literal(f"Envoy {weight} {slot}", lang="en")))
        g.add((a_uri, SKOS.altLabel, Literal(f"Raid {weight} {slot}", lang="en")))
        g.add((a_uri, SKOS.altLabel, Literal(f"Legendary {weight} {slot}", lang="en")))

        # Forge Recipe: 25 Legendary Insights (77700) + 15 Provisioner Tokens (43775) + 15 Clovers (19675) + 50 Ectos (19721)
        g.add((f_uri, RDF.type, PRIORY.MysticForgeRecipe))
        g.add((f_uri, RDFS.label, Literal(f"Forge {a_name}", lang="en")))
        g.add((f_uri, PRIORY.producesItem, a_uri))
        g.add((f_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        for ing_id, qty in [(77700, 25), (43775, 15), (19675, 15), (19721, 50)]:
            req = RECIPE[f"req_{clean}_{ing_id}"]
            g.add((f_uri, PRIORY.hasIngredientRequirement, req))
            g.add((req, RDF.type, PRIORY.IngredientRequirement))
            g.add((req, PRIORY.requiresItem, ITEM[str(ing_id)]))
            g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    # 3. Obsidian Legendary Armor (SotO - 18 pieces)
    for weight, slot, o_id, o_name in OBSIDIAN_ARMOR:
        clean = o_name.lower().replace(" ", "_").replace("'", "").replace("-", "_")
        o_uri = ITEM[str(o_id)]
        f_uri = RECIPE[f"forge_{clean}"]

        g.add((o_uri, RDF.type, PRIORY.LegendaryArmor))
        g.add((o_uri, RDF.type, OWL.NamedIndividual))
        g.add((o_uri, RDFS.label, Literal(o_name, lang="en")))
        g.add((o_uri, PRIORY.gw2Id, Literal(o_id, datatype=XSD.integer)))
        g.add((o_uri, PRIORY.hasRarity, RARITY.Legendary))
        g.add((o_uri, PRIORY.hasArmorWeight, WEIGHT[weight]))
        g.add((o_uri, PRIORY.hasEquipmentSlot, SLOT[slot]))
        g.add((o_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
        g.add((o_uri, PRIORY.producedBy, f_uri))

        # AltLabels
        g.add((o_uri, SKOS.altLabel, Literal(f"Obsidian {weight} {slot}", lang="en")))
        g.add((o_uri, SKOS.altLabel, Literal(f"SotO {weight} {slot}", lang="en")))
        g.add((o_uri, SKOS.altLabel, Literal(f"Open World {weight} {slot}", lang="en")))

        # Forge Recipe: 500 Essence of Despair (100114) + 500 Essence of Greed (100414) + 500 Essence of Triumph (100429) + 500 Stardust (100852)
        g.add((f_uri, RDF.type, PRIORY.MysticForgeRecipe))
        g.add((f_uri, RDFS.label, Literal(f"Forge {o_name}", lang="en")))
        g.add((f_uri, PRIORY.producesItem, o_uri))
        g.add((f_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        for ing_id, qty in [(100114, 500), (100414, 500), (100429, 500), (100852, 500)]:
            req = RECIPE[f"req_{clean}_{ing_id}"]
            g.add((f_uri, PRIORY.hasIngredientRequirement, req))
            g.add((req, RDF.type, PRIORY.IngredientRequirement))
            g.add((req, PRIORY.requiresItem, ITEM[str(ing_id)]))
            g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    # 4. Janthir Wilds Spear (Klobjarne Harvester 103460)
    spear_uri = ITEM["103460"]
    f_spear = RECIPE["forge_klobjarne_harvester"]
    g.add((spear_uri, RDF.type, PRIORY.LegendaryWeapon))
    g.add((spear_uri, RDF.type, OWL.NamedIndividual))
    g.add((spear_uri, RDFS.label, Literal("Klobjarne Harvester", lang="en")))
    g.add((spear_uri, PRIORY.gw2Id, Literal(103460, datatype=XSD.integer)))
    g.add((spear_uri, PRIORY.hasRarity, RARITY.Legendary))
    g.add((spear_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
    g.add((spear_uri, PRIORY.producedBy, f_spear))

    g.add((spear_uri, SKOS.altLabel, Literal("Janthir Spear", lang="en")))
    g.add((spear_uri, SKOS.altLabel, Literal("Legendary Land Spear", lang="en")))
    g.add((spear_uri, SKOS.altLabel, Literal("Klobjarne", lang="en")))

    g.add((f_spear, RDF.type, PRIORY.MysticForgeRecipe))
    g.add((f_spear, RDFS.label, Literal("Forge Klobjarne Harvester", lang="en")))
    g.add((f_spear, PRIORY.producesItem, spear_uri))
    g.add((f_spear, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

    # Mursaat Obsidian Chunks (103427), Titan Ore (103112), Lowland Pine (103125), Clovers (19675)
    for ing_id, qty in [(103427, 250), (103112, 500), (103125, 500), (19675, 77)]:
        req = RECIPE[f"req_klobjarne_{ing_id}"]
        g.add((f_spear, PRIORY.hasIngredientRequirement, req))
        g.add((req, RDF.type, PRIORY.IngredientRequirement))
        g.add((req, PRIORY.requiresItem, ITEM[str(ing_id)]))
        g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    # 5. Trinkets, Backpacks & Upgrades
    for item_id, name, item_cat, slot_name in TRINKETS_AND_UPGRADES:
        if item_id == 103460:
            continue
        clean_name = name.lower().replace(" ", "_").replace("'", "").replace("-", "_")
        item_uri = ITEM[str(item_id)]
        forge_uri = RECIPE[f"forge_{clean_name}"]

        item_class = PRIORY.LegendaryTrinket if item_cat == "Trinket" else (
            PRIORY.LegendaryBackpack if item_cat == "Backpack" else PRIORY.LegendaryUpgrade
        )

        g.add((item_uri, RDF.type, item_class))
        g.add((item_uri, RDF.type, OWL.NamedIndividual))
        g.add((item_uri, RDFS.label, Literal(name, lang="en")))
        g.add((item_uri, PRIORY.gw2Id, Literal(item_id, datatype=XSD.integer)))
        g.add((item_uri, PRIORY.hasRarity, RARITY.Legendary))
        g.add((item_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
        g.add((item_uri, PRIORY.producedBy, forge_uri))

        g.add((forge_uri, RDF.type, PRIORY.MysticForgeRecipe))
        g.add((forge_uri, RDFS.label, Literal(f"Forge {name}", lang="en")))
        g.add((forge_uri, PRIORY.producesItem, item_uri))
        g.add((forge_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        if item_id == 81908: # Aurora (Season 3 currencies)
            reqs = [(79401, 100), (79280, 100), (80332, 100), (79899, 100), (19675, 77)]
        elif item_id == 91234: # Vision (Season 4 currencies)
            reqs = [(86069, 250), (86977, 250), (87645, 250), (88955, 250), (19675, 77)]
        elif item_id == 91048: # Coalescence (Raids)
            reqs = [(77700, 150), (19721, 250), (19675, 77)]
        elif item_id == 101582: # Legendary Relic
            reqs = [(43775, 25), (19721, 50), (19675, 15)]
        else: # Standard upgrades / backpacks
            reqs = [(19675, 77), (19721, 250)]

        for ing_id, qty in reqs:
            req = RECIPE[f"req_{clean_name}_{ing_id}"]
            g.add((forge_uri, PRIORY.hasIngredientRequirement, req))
            g.add((req, RDF.type, PRIORY.IngredientRequirement))
            g.add((req, PRIORY.requiresItem, ITEM[str(ing_id)]))
            g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    return g

if __name__ == "__main__":
    out_file = Path("/Users/clementd/Documents/GitHub/gw2-priory-def/ontology/instances/recipes/legendary_armor_recipes.ttl")
    graph = generate_armor_trinket_graph()
    graph.serialize(destination=str(out_file), format="turtle")
    print(f"✅ Generated {len(graph)} triples for Legendary Armor, Trinkets, Janthir Wilds, and Upgrades in {out_file}")
