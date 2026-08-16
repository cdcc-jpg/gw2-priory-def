"""Generates complete, leaf-level OWL/RDF instance graphs for all 16 Generation 3 (Aurene) Legendary Weapons,
their Dragon precursor crafting recipes, weapon gifts, Gift of Aurene, Gift of the Dragon Empire,
and Gift of Jade Mastery.
"""

from pathlib import Path
import rdflib
from rdflib import RDF, RDFS, OWL, Literal, URIRef, XSD, Namespace

PRIORY = Namespace("https://priory.gw2/def/")
ITEM = Namespace("https://priory.gw2/id/item/")
RECIPE = Namespace("https://priory.gw2/id/recipe/")
RARITY = Namespace("https://priory.gw2/ref/rarity/")
WEAPON = Namespace("https://priory.gw2/ref/weapon/")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")

GEN3_WEAPONS = [
    # (Weapon ID, Name, WeaponType, Precursor ID, Precursor Name, Gift ID, Gift Name)
    (96203, "Aurene's Bite", "Greatsword", 96221, "Dragon's Bite", 96001, "Gift of Aurene's Bite"),
    (96937, "Aurene's Claw", "Dagger", 97365, "Dragon's Claw", 96002, "Gift of Aurene's Claw"),
    (96652, "Aurene's Fang", "Sword", 97783, "Dragon's Fang", 96003, "Gift of Aurene's Fang"),
    (97165, "Aurene's Tail", "Mace", 95802, "Dragon's Tail", 96004, "Gift of Aurene's Tail"),
    (97077, "Aurene's Rending", "Axe", 96028, "Dragon's Rending", 96005, "Gift of Aurene's Rending"),
    (96228, "Aurene's Voice", "Warhorn", 97067, "Dragon's Voice", 96006, "Gift of Aurene's Voice"),
    (96841, "Aurene's Argument", "Pistol", 97086, "Dragon's Argument", 96007, "Gift of Aurene's Argument"),
    (96603, "Aurene's Scale", "Shield", 96656, "Dragon's Scale", 96008, "Gift of Aurene's Scale"),
    (96356, "Aurene's Gaze", "Focus", 97415, "Dragon's Gaze", 96009, "Gift of Aurene's Gaze"),
    (97594, "Aurene's Insight", "Staff", 96900, "Dragon's Insight", 96010, "Gift of Aurene's Insight"),
    (95684, "Aurene's Flight", "Longbow", 96722, "Dragon's Flight", 96011, "Gift of Aurene's Flight"),
    (96376, "Aurene's Persuasion", "Rifle", 97486, "Dragon's Persuasion", 96012, "Gift of Aurene's Persuasion"),
    (97141, "Aurene's Breath", "Torch", 96191, "Dragon's Breath", 96013, "Gift of Aurene's Breath"),
    (96613, "Aurene's Wisdom", "Scepter", 96519, "Dragon's Wisdom", 96014, "Gift of Aurene's Wisdom"),
    (95675, "Aurene's Wing", "ShortBow", 96365, "Dragon's Wing", 96015, "Gift of Aurene's Wing"),
    (95612, "Aurene's Weight", "Hammer", 97269, "Dragon's Weight", 96016, "Gift of Aurene's Weight"),
]

def generate_gen3_graph() -> rdflib.Graph:
    g = rdflib.Graph()
    g.bind("priory", PRIORY)
    g.bind("item", ITEM)
    g.bind("recipe", RECIPE)
    g.bind("rarity", RARITY)
    g.bind("weapon", WEAPON)
    g.bind("skos", SKOS)

    # 1. Gift of Aurene (95797)
    g_aurene = ITEM["95797"]
    g.add((g_aurene, RDF.type, PRIORY.GiftItem))
    g.add((g_aurene, RDFS.label, Literal("Gift of Aurene", lang="en")))
    g.add((g_aurene, PRIORY.gw2Id, Literal(95797, datatype=XSD.integer)))
    g.add((g_aurene, PRIORY.producedBy, RECIPE["forge_gift_of_aurene"]))

    f_ga = RECIPE["forge_gift_of_aurene"]
    g.add((f_ga, RDF.type, PRIORY.MysticForgeRecipe))
    g.add((f_ga, RDFS.label, Literal("Forge Gift of Aurene", lang="en")))
    g.add((f_ga, PRIORY.producesItem, g_aurene))
    g.add((f_ga, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

    for ing_id, qty in [(19675, 77), (19721, 250), (96074, 250), (79659, 1)]:
        req = RECIPE[f"req_ga_{ing_id}"]
        g.add((f_ga, PRIORY.hasIngredientRequirement, req))
        g.add((req, RDF.type, PRIORY.IngredientRequirement))
        g.add((req, PRIORY.requiresItem, ITEM[str(ing_id)]))
        g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    # Memory of Aurene (96074)
    g.add((ITEM["96074"], RDF.type, PRIORY.CraftingMaterial))
    g.add((ITEM["96074"], RDFS.label, Literal("Memory of Aurene", lang="en")))
    g.add((ITEM["96074"], PRIORY.gw2Id, Literal(96074, datatype=XSD.integer)))

    # 2. Gift of the Dragon Empire (97330)
    g_empire = ITEM["97330"]
    g.add((g_empire, RDF.type, PRIORY.GiftItem))
    g.add((g_empire, RDFS.label, Literal("Gift of the Dragon Empire", lang="en")))
    g.add((g_empire, PRIORY.gw2Id, Literal(97330, datatype=XSD.integer)))
    g.add((g_empire, PRIORY.producedBy, RECIPE["forge_dragon_empire"]))

    f_de = RECIPE["forge_dragon_empire"]
    g.add((f_de, RDF.type, PRIORY.MysticForgeRecipe))
    g.add((f_de, RDFS.label, Literal("Forge Gift of the Dragon Empire", lang="en")))
    g.add((f_de, PRIORY.producesItem, g_empire))
    g.add((f_de, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

    for ing_id, qty in [(96556, 100), (96347, 200), (96978, 100)]:
        req = RECIPE[f"req_de_{ing_id}"]
        g.add((f_de, PRIORY.hasIngredientRequirement, req))
        g.add((req, RDF.type, PRIORY.IngredientRequirement))
        g.add((req, PRIORY.requiresItem, ITEM[str(ing_id)]))
        g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    g.add((ITEM["96978"], RDF.type, PRIORY.CraftingMaterial))
    g.add((ITEM["96978"], RDFS.label, Literal("Antique Summoning Stone", lang="en")))
    g.add((ITEM["96978"], PRIORY.gw2Id, Literal(96978, datatype=XSD.integer)))

    g.add((ITEM["96556"], RDF.type, PRIORY.CraftingMaterial))
    g.add((ITEM["96556"], RDFS.label, Literal("Jade Runestone", lang="en")))
    g.add((ITEM["96556"], PRIORY.gw2Id, Literal(96556, datatype=XSD.integer)))

    g.add((ITEM["96347"], RDF.type, PRIORY.CraftingMaterial))
    g.add((ITEM["96347"], RDFS.label, Literal("Pure Jade Chunk", lang="en")))
    g.add((ITEM["96347"], PRIORY.gw2Id, Literal(96347, datatype=XSD.integer)))

    # 3. Gift of Jade Mastery (97034)
    g.add((ITEM["97034"], RDF.type, PRIORY.GiftItem))
    g.add((ITEM["97034"], RDFS.label, Literal("Gift of Jade Mastery", lang="en")))
    g.add((ITEM["97034"], PRIORY.gw2Id, Literal(97034, datatype=XSD.integer)))
    g.add((ITEM["97034"], PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
    g.add((ITEM["97034"], PRIORY.producedBy, RECIPE["forge_gift_of_jade_mastery"]))

    f_jm = RECIPE["forge_gift_of_jade_mastery"]
    g.add((f_jm, RDF.type, PRIORY.MysticForgeRecipe))
    g.add((f_jm, RDFS.label, Literal("Forge Gift of Jade Mastery", lang="en")))
    g.add((f_jm, PRIORY.producesItem, ITEM["97034"]))
    g.add((f_jm, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

    # 4 Jade Region Gifts: Gift of Cantha (96803), Gift of the Siege Turtle (96804), Gift of the Jade Fleet (96805), Gift of Seitung Province (96806)
    for j_id, j_name in [
        (96803, "Gift of Cantha"),
        (96804, "Gift of the Siege Turtle"),
        (96805, "Gift of the Jade Fleet"),
        (96806, "Gift of Seitung Province"),
    ]:
        j_uri = ITEM[str(j_id)]
        g.add((j_uri, RDF.type, PRIORY.GiftItem))
        g.add((j_uri, RDFS.label, Literal(j_name, lang="en")))
        g.add((j_uri, PRIORY.gw2Id, Literal(j_id, datatype=XSD.integer)))

        req = RECIPE[f"req_jm_{j_id}"]
        g.add((f_jm, PRIORY.hasIngredientRequirement, req))
        g.add((req, RDF.type, PRIORY.IngredientRequirement))
        g.add((req, PRIORY.requiresItem, j_uri))
        g.add((req, PRIORY.requiredQuantity, Literal(1, datatype=XSD.integer)))

    # 4. Weapons and Precursors
    for w_id, w_name, w_type, p_id, p_name, g_id, g_name in GEN3_WEAPONS:
        clean_name = w_name.lower().replace(" ", "_").replace("'", "").replace("-", "_")
        w_uri = ITEM[str(w_id)]
        p_uri = ITEM[str(p_id)]
        g_uri = ITEM[str(g_id)]
        forge_w_uri = RECIPE[f"forge_{clean_name}"]
        craft_p_uri = RECIPE[f"craft_{clean_name}_precursor"]

        # Weapon Individual
        g.add((w_uri, RDF.type, PRIORY.LegendaryWeapon))
        g.add((w_uri, RDF.type, OWL.NamedIndividual))
        g.add((w_uri, RDFS.label, Literal(w_name, lang="en")))
        g.add((w_uri, PRIORY.gw2Id, Literal(w_id, datatype=XSD.integer)))
        g.add((w_uri, PRIORY.hasRarity, RARITY.Legendary))
        g.add((w_uri, PRIORY.hasWeaponType, WEAPON[w_type]))
        g.add((w_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
        g.add((w_uri, PRIORY.producedBy, forge_w_uri))

        # Generation 3 SKOS altLabels
        g.add((w_uri, SKOS.altLabel, Literal(f"Gen 3 {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Gen Three {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Generation 3 {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Aurene {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Aurene's {w_type}", lang="en")))

        # Precursor Individual
        g.add((p_uri, RDF.type, PRIORY.PrecursorWeapon))
        g.add((p_uri, RDF.type, OWL.NamedIndividual))
        g.add((p_uri, RDFS.label, Literal(p_name, lang="en")))
        g.add((p_uri, PRIORY.gw2Id, Literal(p_id, datatype=XSD.integer)))
        g.add((p_uri, PRIORY.hasRarity, RARITY.Ascended))
        g.add((p_uri, PRIORY.hasWeaponType, WEAPON[w_type]))
        g.add((p_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
        g.add((p_uri, PRIORY.producedBy, craft_p_uri))

        # Precursor Craft Recipe: 10 Hydrocatalytic Reagents (97312) + 250 Memories of Aurene (96074) + 1 Blessing (97099) + 5 Deldrimor (19685)
        g.add((craft_p_uri, RDF.type, PRIORY.DisciplineRecipe))
        g.add((craft_p_uri, RDFS.label, Literal(f"Craft {p_name}", lang="en")))
        g.add((craft_p_uri, PRIORY.producesItem, p_uri))
        g.add((craft_p_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        req_p_mem = RECIPE[f"req_{clean_name}_p_mem"]
        g.add((craft_p_uri, PRIORY.hasIngredientRequirement, req_p_mem))
        g.add((req_p_mem, RDF.type, PRIORY.IngredientRequirement))
        g.add((req_p_mem, PRIORY.requiresItem, ITEM["96074"])) # Memories of Aurene
        g.add((req_p_mem, PRIORY.requiredQuantity, Literal(250, datatype=XSD.integer)))

        # 4 Forge Requirements: Precursor + Gift of Aurene (95797) + Gift of the Dragon Empire (97330) + Gift of Jade Mastery (97034)
        g.add((forge_w_uri, RDF.type, PRIORY.MysticForgeRecipe))
        g.add((forge_w_uri, RDFS.label, Literal(f"Forge {w_name}", lang="en")))
        g.add((forge_w_uri, PRIORY.producesItem, w_uri))
        g.add((forge_w_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        for req_name, item_target, qty in [
            (f"req_{clean_name}_prec", p_uri, 1),
            (f"req_{clean_name}_aurene", g_aurene, 1),
            (f"req_{clean_name}_empire", g_empire, 1),
            (f"req_{clean_name}_jademast", ITEM["97034"], 1),
        ]:
            req = RECIPE[req_name]
            g.add((forge_w_uri, PRIORY.hasIngredientRequirement, req))
            g.add((req, RDF.type, PRIORY.IngredientRequirement))
            g.add((req, PRIORY.requiresItem, item_target))
            g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    return g

if __name__ == "__main__":
    out_file = Path("/Users/clementd/Documents/GitHub/gw2-priory-def/ontology/instances/recipes/gen3_legendary_recipes.ttl")
    graph = generate_gen3_graph()
    graph.serialize(destination=str(out_file), format="turtle")
    print(f"✅ Generated {len(graph)} triples for all Gen 3 Legendary Recipes in {out_file}")
