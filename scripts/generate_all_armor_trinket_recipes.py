"""Generates complete OWL/RDF instance graphs for Legendary Armor, Trinkets, Backpacks,
and Upgrades (Legendary Rune, Legendary Relic).
"""

from pathlib import Path
import rdflib
from rdflib import RDF, RDFS, OWL, Literal, URIRef, XSD, Namespace

PRIORY = Namespace("https://priory.gw2/def/")
ITEM = Namespace("https://priory.gw2/id/item/")
RECIPE = Namespace("https://priory.gw2/id/recipe/")
RARITY = Namespace("https://priory.gw2/ref/rarity/")
SLOT = Namespace("https://priory.gw2/ref/slot/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

TRINKETS_AND_UPGRADES = [
    # (Item ID, Name, Type, Slot)
    (81908, "Aurora", "Trinket", "Accessory"),
    (91234, "Vision", "Trinket", "Accessory"),
    (91048, "Coalescence", "Trinket", "Ring"),
    (92991, "Conflux", "Trinket", "Ring"),
    (92946, "Transcendence", "Trinket", "Amulet"),
    (95380, "Prismatic Champion's Regalia", "Trinket", "Amulet"),
    (77474, "Ad Infinitum", "Backpack", "Backpack"),
    (78430, "The Ascension", "Backpack", "Backpack"),
    (81706, "Warbringer", "Backpack", "Backpack"),
    (91536, "Legendary Rune", "Upgrade", "Rune"),
    (101582, "Legendary Relic", "Upgrade", "Relic"),
]

def generate_armor_and_trinkets_graph() -> rdflib.Graph:
    g = rdflib.Graph()
    g.bind("priory", PRIORY)
    g.bind("item", ITEM)
    g.bind("recipe", RECIPE)
    g.bind("rarity", RARITY)
    g.bind("slot", SLOT)
    g.bind("skos", SKOS)

    # 1. Provisioner Token (Currency 35 / Item 43775)
    g.add((ITEM["43775"], RDF.type, PRIORY.CraftingMaterial))
    g.add((ITEM["43775"], RDFS.label, Literal("Provisioner Token", lang="en")))
    g.add((ITEM["43775"], PRIORY.gw2Id, Literal(43775, datatype=XSD.integer)))

    # 2. Legendary Insight (77700)
    g.add((ITEM["77700"], RDF.type, PRIORY.CraftingMaterial))
    g.add((ITEM["77700"], RDFS.label, Literal("Legendary Insight", lang="en")))
    g.add((ITEM["77700"], PRIORY.gw2Id, Literal(77700, datatype=XSD.integer)))

    # 3. Add Trinkets & Upgrades
    for item_id, name, item_cat, slot_name in TRINKETS_AND_UPGRADES:
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

        # Forge Recipe
        g.add((forge_uri, RDF.type, PRIORY.MysticForgeRecipe))
        g.add((forge_uri, RDFS.label, Literal(f"Forge {name}", lang="en")))
        g.add((forge_uri, PRIORY.producesItem, item_uri))
        g.add((forge_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        # Standard requirements: 77 Clovers (19675), 250 Ectos (19721)
        for ing_id, qty in [(19675, 77), (19721, 250)]:
            req = RECIPE[f"req_{clean_name}_{ing_id}"]
            g.add((forge_uri, PRIORY.hasIngredientRequirement, req))
            g.add((req, RDF.type, PRIORY.IngredientRequirement))
            g.add((req, PRIORY.requiresItem, ITEM[str(ing_id)]))
            g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    return g

if __name__ == "__main__":
    out_file = Path("/Users/clementd/Documents/GitHub/gw2-priory-def/ontology/instances/recipes/legendary_trinkets_and_upgrades.ttl")
    graph = generate_armor_and_trinkets_graph()
    graph.serialize(destination=str(out_file), format="turtle")
    print(f"✅ Generated {len(graph)} triples for Legendary Trinkets and Upgrades in {out_file}")
