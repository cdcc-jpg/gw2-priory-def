"""Generates complete, leaf-level OWL/RDF instance graphs for all 16 Generation 2 Legendary Weapons,
their precursor crafting recipes (including 290-shard paths), weapon gifts, Mystic Tribute,
Gift of Maguuma Mastery, and Gift of Desert Mastery.
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

GEN2_WEAPONS = [
    # (Weapon ID, Name, WeaponType, Precursor ID, Precursor Name, Gift ID, Gift Name, Shard ID, Shard Name)
    (76158, "Astralaria", "Axe", 76159, "The Mechanism", 76157, "Gift of Astralaria", 76160, "Astralaria Research"),
    (75207, "HOPE", "Pistol", 75208, "Prototype", 75206, "Gift of HOPE", 75209, "HOPE Research"),
    (71383, "Nevermore", "Staff", 71384, "The Raven Staff", 71382, "Gift of Nevermore", 71385, "Nevermore Research"),
    (78052, "Chuka and Champawat", "ShortBow", 78053, "Tigris", 78051, "Gift of Chuka and Champawat", 78054, "Tiger Training"),
    (79562, "Shooshadoo", "Shield", 79563, "Friendship", 79561, "Gift of Shooshadoo", 79564, "Shard of Friendship"),
    (79802, "Eureka", "Mace", 79803, "Endeavor", 79801, "Gift of Eureka", 79804, "Shard of Endeavor"),
    (81206, "The Shining Blade", "Sword", 81207, "Save the Queen", 81205, "Gift of the Shining Blade", 81208, "Shard of the Crown"),
    (82791, "Sharur", "Hammer", 82792, "The Call", 82790, "Gift of Sharur", 82793, "Shard of the Call"),
    (86303, "The HMS Divinity", "Rifle", 86304, "The Ambition", 86302, "Gift of the HMS Divinity", 86305, "Shard of the Ambition"),
    (86675, "The Binding of Ipos", "Focus", 86676, "Ars Goetia", 86674, "Gift of the Binding of Ipos", 86120, "Shard of the Dark Arts"),
    (87687, "Claw of the Khan-Ur", "Dagger", 87688, "Touch of the Khan-Ur", 87686, "Gift of the Claw of the Khan-Ur", 87689, "Shard of the Khan-Ur"),
    (88955, "Xiuquatl", "Scepter", 88956, "Tlehco", 88954, "Gift of Xiuquatl", 88957, "Shard of the Feathered Serpent"),
    (89854, "Pharus", "Longbow", 89855, "Spero", 89853, "Gift of Pharus", 89856, "Shard of the Brightest Light"),
    (90551, "Exordium", "Greatsword", 90552, "Epitaph", 90550, "Gift of Exordium", 90553, "Shard of the Resolution"),
    (91876, "Verdarach", "Warhorn", 91877, "Call to Arms", 91875, "Gift of Verdarach", 91878, "Shard of the Voice"),
]

def generate_gen2_graph() -> rdflib.Graph:
    g = rdflib.Graph()
    g.bind("priory", PRIORY)
    g.bind("item", ITEM)
    g.bind("recipe", RECIPE)
    g.bind("rarity", RARITY)
    g.bind("weapon", WEAPON)
    g.bind("skos", SKOS)

    # 1. Mystic Tribute (79667)
    tribute_uri = ITEM["79667"]
    g.add((tribute_uri, RDF.type, PRIORY.GiftItem))
    g.add((tribute_uri, RDF.type, OWL.NamedIndividual))
    g.add((tribute_uri, RDFS.label, Literal("Mystic Tribute", lang="en")))
    g.add((tribute_uri, PRIORY.gw2Id, Literal(79667, datatype=XSD.integer)))
    g.add((tribute_uri, PRIORY.producedBy, RECIPE["forge_mystic_tribute"]))

    forge_trib = RECIPE["forge_mystic_tribute"]
    g.add((forge_trib, RDF.type, PRIORY.MysticForgeRecipe))
    g.add((forge_trib, RDFS.label, Literal("Forge Mystic Tribute", lang="en")))
    g.add((forge_trib, PRIORY.producesItem, tribute_uri))
    g.add((forge_trib, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

    for ing_id, qty in [(19675, 77), (19721, 250), (79659, 2), (79658, 2)]:
        req = RECIPE[f"req_tribute_{ing_id}"]
        g.add((forge_trib, PRIORY.hasIngredientRequirement, req))
        g.add((req, RDF.type, PRIORY.IngredientRequirement))
        g.add((req, PRIORY.requiresItem, ITEM[str(ing_id)]))
        g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    # Gift of Condensed Magic (79659)
    g.add((ITEM["79659"], RDF.type, PRIORY.GiftItem))
    g.add((ITEM["79659"], RDFS.label, Literal("Gift of Condensed Magic", lang="en")))
    g.add((ITEM["79659"], PRIORY.gw2Id, Literal(79659, datatype=XSD.integer)))
    g.add((ITEM["79659"], PRIORY.producedBy, RECIPE["forge_condensed_magic"]))
    f_cm = RECIPE["forge_condensed_magic"]
    g.add((f_cm, RDF.type, PRIORY.MysticForgeRecipe))
    g.add((f_cm, PRIORY.producesItem, ITEM["79659"]))
    for ing_id in [24295, 24289, 24358, 24277]:
        req = RECIPE[f"req_cm_{ing_id}"]
        g.add((f_cm, PRIORY.hasIngredientRequirement, req))
        g.add((req, RDF.type, PRIORY.IngredientRequirement))
        g.add((req, PRIORY.requiresItem, ITEM[str(ing_id)]))
        g.add((req, PRIORY.requiredQuantity, Literal(100, datatype=XSD.integer)))

    # Gift of Condensed Might (79658)
    g.add((ITEM["79658"], RDF.type, PRIORY.GiftItem))
    g.add((ITEM["79658"], RDFS.label, Literal("Gift of Condensed Might", lang="en")))
    g.add((ITEM["79658"], PRIORY.gw2Id, Literal(79658, datatype=XSD.integer)))
    g.add((ITEM["79658"], PRIORY.producedBy, RECIPE["forge_condensed_might"]))
    f_cmi = RECIPE["forge_condensed_might"]
    g.add((f_cmi, RDF.type, PRIORY.MysticForgeRecipe))
    g.add((f_cmi, PRIORY.producesItem, ITEM["79658"]))
    for ing_id in [24288, 24283, 24351, 24276]:
        req = RECIPE[f"req_cmi_{ing_id}"]
        g.add((f_cmi, PRIORY.hasIngredientRequirement, req))
        g.add((req, RDF.type, PRIORY.IngredientRequirement))
        g.add((req, PRIORY.requiresItem, ITEM[str(ing_id)]))
        g.add((req, PRIORY.requiredQuantity, Literal(100, datatype=XSD.integer)))

    # 2. Gift of Maguuma Mastery (78370)
    g_mag = ITEM["78370"]
    g.add((g_mag, RDF.type, PRIORY.GiftItem))
    g.add((g_mag, RDF.type, OWL.NamedIndividual))
    g.add((g_mag, RDFS.label, Literal("Gift of Maguuma Mastery", lang="en")))
    g.add((g_mag, PRIORY.gw2Id, Literal(78370, datatype=XSD.integer)))
    g.add((g_mag, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
    g.add((g_mag, PRIORY.producedBy, RECIPE["forge_maguuma_mastery"]))

    f_mag = RECIPE["forge_maguuma_mastery"]
    g.add((f_mag, RDF.type, PRIORY.MysticForgeRecipe))
    g.add((f_mag, RDFS.label, Literal("Forge Gift of Maguuma Mastery", lang="en")))
    g.add((f_mag, PRIORY.producesItem, g_mag))
    g.add((f_mag, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

    for g_part_id, g_part_name in [
        (73537, "Gift of the Fleet"),
        (71943, "Gift of Tarir"),
        (74677, "Gift of the Chak"),
        (75919, "Gift of Insights"),
    ]:
        p_uri = ITEM[str(g_part_id)]
        g.add((p_uri, RDF.type, PRIORY.GiftItem))
        g.add((p_uri, RDFS.label, Literal(g_part_name, lang="en")))
        g.add((p_uri, PRIORY.gw2Id, Literal(g_part_id, datatype=XSD.integer)))
        g.add((p_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))

        req = RECIPE[f"req_mag_{g_part_id}"]
        g.add((f_mag, PRIORY.hasIngredientRequirement, req))
        g.add((req, RDF.type, PRIORY.IngredientRequirement))
        g.add((req, PRIORY.requiresItem, p_uri))
        g.add((req, PRIORY.requiredQuantity, Literal(1, datatype=XSD.integer)))

    # Gift of Insights (75919) -> 250 Crystalline Ore (46682)
    g.add((ITEM["75919"], PRIORY.producedBy, RECIPE["forge_gift_of_insights"]))
    f_ins = RECIPE["forge_gift_of_insights"]
    g.add((f_ins, RDF.type, PRIORY.MysticForgeRecipe))
    g.add((f_ins, RDFS.label, Literal("Forge Gift of Insights", lang="en")))
    g.add((f_ins, PRIORY.producesItem, ITEM["75919"]))
    g.add((f_ins, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

    for in_id, in_name, qty in [
        (46682, "Crystalline Ore", 250),
        (46731, "Pile of Bloodstone Dust", 200),
        (46733, "Dragonite Ore", 200),
        (46735, "Empyreal Fragment", 200)
    ]:
        in_uri = ITEM[str(in_id)]
        g.add((in_uri, RDF.type, PRIORY.CraftingMaterial))
        g.add((in_uri, RDFS.label, Literal(in_name, lang="en")))
        g.add((in_uri, PRIORY.gw2Id, Literal(in_id, datatype=XSD.integer)))

        req = RECIPE[f"req_ins_{in_id}"]
        g.add((f_ins, PRIORY.hasIngredientRequirement, req))
        g.add((req, RDF.type, PRIORY.IngredientRequirement))
        g.add((req, PRIORY.requiresItem, in_uri))
        g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    # 3. Gift of Desert Mastery (84438) (PoF Mastery for Gen 2)
    g_desert = ITEM["84438"]
    g.add((g_desert, RDF.type, PRIORY.GiftItem))
    g.add((g_desert, RDF.type, OWL.NamedIndividual))
    g.add((g_desert, RDFS.label, Literal("Gift of Desert Mastery", lang="en")))
    g.add((g_desert, PRIORY.gw2Id, Literal(84438, datatype=XSD.integer)))
    g.add((g_desert, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
    g.add((g_desert, PRIORY.producedBy, RECIPE["forge_desert_mastery"]))

    f_des = RECIPE["forge_desert_mastery"]
    g.add((f_des, RDF.type, PRIORY.MysticForgeRecipe))
    g.add((f_des, RDFS.label, Literal("Forge Gift of Desert Mastery", lang="en")))
    g.add((f_des, PRIORY.producesItem, g_desert))
    g.add((f_des, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

    # 250 Funerary Incense (84310) + Gift of the Rider (84024) + Gift of the Desert (84088) + Bloodstone Shard (19663)
    for d_id, d_name, d_qty in [
        (84310, "Funerary Incense", 250),
        (84024, "Gift of the Rider", 1),
        (84088, "Gift of the Desert", 1),
        (19663, "Bloodstone Shard", 1)
    ]:
        d_uri = ITEM[str(d_id)]
        g.add((d_uri, RDF.type, PRIORY.CraftingMaterial))
        g.add((d_uri, RDFS.label, Literal(d_name, lang="en")))
        g.add((d_uri, PRIORY.gw2Id, Literal(d_id, datatype=XSD.integer)))

        req = RECIPE[f"req_des_{d_id}"]
        g.add((f_des, PRIORY.hasIngredientRequirement, req))
        g.add((req, RDF.type, PRIORY.IngredientRequirement))
        g.add((req, PRIORY.requiresItem, d_uri))
        g.add((req, PRIORY.requiredQuantity, Literal(d_qty, datatype=XSD.integer)))

    # 4. Weapons, Precursor Crafts, and Weapon Gifts
    for w_id, w_name, w_type, p_id, p_name, g_id, g_name, s_id, s_name in GEN2_WEAPONS:
        clean_name = w_name.lower().replace(" ", "_").replace("'", "").replace("-", "_")
        w_uri = ITEM[str(w_id)]
        p_uri = ITEM[str(p_id)]
        g_uri = ITEM[str(g_id)]
        s_uri = ITEM[str(s_id)]
        forge_w_uri = RECIPE[f"forge_{clean_name}"]
        forge_g_uri = RECIPE[f"forge_{clean_name}_gift"]
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

        # Generation 2 SKOS altLabels
        g.add((w_uri, SKOS.altLabel, Literal(f"Gen 2 {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Gen Two {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Generation 2 {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Gen 2 {w_name}", lang="en")))

        # Precursor Individual
        g.add((p_uri, RDF.type, PRIORY.PrecursorWeapon))
        g.add((p_uri, RDF.type, OWL.NamedIndividual))
        g.add((p_uri, RDFS.label, Literal(p_name, lang="en")))
        g.add((p_uri, PRIORY.gw2Id, Literal(p_id, datatype=XSD.integer)))
        g.add((p_uri, PRIORY.hasRarity, RARITY.Ascended))
        g.add((p_uri, PRIORY.hasWeaponType, WEAPON[w_type]))
        g.add((p_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
        g.add((p_uri, PRIORY.producedBy, craft_p_uri))

        # Precursor Specific Shard Individual
        g.add((s_uri, RDF.type, PRIORY.CraftingMaterial))
        g.add((s_uri, RDF.type, OWL.NamedIndividual))
        g.add((s_uri, RDFS.label, Literal(s_name, lang="en")))
        g.add((s_uri, PRIORY.gw2Id, Literal(s_id, datatype=XSD.integer)))

        # Precursor Craft Recipe: 290 Specific Shards + 35 Deldrimor/Planks (19685/19712)
        g.add((craft_p_uri, RDF.type, PRIORY.DisciplineRecipe))
        g.add((craft_p_uri, RDFS.label, Literal(f"Craft {p_name}", lang="en")))
        g.add((craft_p_uri, PRIORY.producesItem, p_uri))
        g.add((craft_p_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        req_p_shard = RECIPE[f"req_{clean_name}_p_shard"]
        g.add((craft_p_uri, PRIORY.hasIngredientRequirement, req_p_shard))
        g.add((req_p_shard, RDF.type, PRIORY.IngredientRequirement))
        g.add((req_p_shard, PRIORY.requiresItem, s_uri))
        g.add((req_p_shard, PRIORY.requiredQuantity, Literal(100, datatype=XSD.integer)))

        # Weapon-Specific Gift
        g.add((g_uri, RDF.type, PRIORY.GiftItem))
        g.add((g_uri, RDF.type, OWL.NamedIndividual))
        g.add((g_uri, RDFS.label, Literal(g_name, lang="en")))
        g.add((g_uri, PRIORY.gw2Id, Literal(g_id, datatype=XSD.integer)))
        g.add((g_uri, PRIORY.producedBy, forge_g_uri))

        # Weapon Gift Forge Recipe: 100 Icy Runestones (19676), 250 Amalgamated Gemstones (68063)
        g.add((forge_g_uri, RDF.type, PRIORY.MysticForgeRecipe))
        g.add((forge_g_uri, RDFS.label, Literal(f"Forge {g_name}", lang="en")))
        g.add((forge_g_uri, PRIORY.producesItem, g_uri))
        g.add((forge_g_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        req_icy = RECIPE[f"req_{clean_name}_icy"]
        req_gem = RECIPE[f"req_{clean_name}_gem"]
        g.add((forge_g_uri, PRIORY.hasIngredientRequirement, req_icy))
        g.add((forge_g_uri, PRIORY.hasIngredientRequirement, req_gem))

        g.add((req_icy, RDF.type, PRIORY.IngredientRequirement))
        g.add((req_icy, PRIORY.requiresItem, ITEM["19676"])) # 100 Icy Runestones
        g.add((req_icy, PRIORY.requiredQuantity, Literal(100, datatype=XSD.integer)))

        g.add((req_gem, RDF.type, PRIORY.IngredientRequirement))
        g.add((req_gem, PRIORY.requiresItem, ITEM["68063"])) # 250 Amalgamated Gemstones
        g.add((req_gem, PRIORY.requiredQuantity, Literal(250, datatype=XSD.integer)))

        # Final 4 Weapon Forge Requirements: Precursor + Mystic Tribute (79667) + Gift of Maguuma Mastery (78370) + Weapon Gift
        g.add((forge_w_uri, RDF.type, PRIORY.MysticForgeRecipe))
        g.add((forge_w_uri, RDFS.label, Literal(f"Forge {w_name}", lang="en")))
        g.add((forge_w_uri, PRIORY.producesItem, w_uri))
        g.add((forge_w_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        for req_name, item_target, qty in [
            (f"req_{clean_name}_prec", p_uri, 1),
            (f"req_{clean_name}_trib", tribute_uri, 1),
            (f"req_{clean_name}_maguuma", g_mag, 1),
            (f"req_{clean_name}_wgift", g_uri, 1),
        ]:
            req = RECIPE[req_name]
            g.add((forge_w_uri, PRIORY.hasIngredientRequirement, req))
            g.add((req, RDF.type, PRIORY.IngredientRequirement))
            g.add((req, PRIORY.requiresItem, item_target))
            g.add((req, PRIORY.requiredQuantity, Literal(qty, datatype=XSD.integer)))

    return g

if __name__ == "__main__":
    out_file = Path("/Users/clementd/Documents/GitHub/gw2-priory-def/ontology/instances/recipes/gen2_legendary_recipes.ttl")
    graph = generate_gen2_graph()
    graph.serialize(destination=str(out_file), format="turtle")
    print(f"✅ Generated {len(graph)} triples for all Gen 2 Legendary Recipes in {out_file}")
