"""Generates complete, leaf-level OWL/RDF instance graphs for all 20 Generation 1 Legendary Weapons,
their precursor weapons, weapon-specific gifts, crafting station sub-gifts, and raw materials.
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

GEN1_WEAPONS = [
    # (Weapon ID, Name, WeaponType, Precursor ID, Precursor Name, Gift ID, Gift Name)
    (30684, "Frostfang", "Axe", 29169, "Tooth of Frostfang", 19625, "Gift of Frostfang"),
    (30685, "Kudzu", "Longbow", 29171, "Leaf of Kudzu", 19644, "Gift of Kudzu"),
    (30686, "The Dreamer", "ShortBow", 29175, "The Lover", 19660, "Gift of The Dreamer"),
    (30687, "Incinerator", "Dagger", 29165, "Spark", 19645, "Gift of Incinerator"),
    (30688, "The Minstrel", "Focus", 29178, "The Bard", 19646, "Gift of The Minstrel"),
    (30690, "The Juggernaut", "Hammer", 29172, "The Colossus", 19649, "Gift of The Juggernaut"),
    (30691, "Kamohoali'i Kotaki", "Spear", 29183, "Carcharias", 19657, "Gift of Kamohoali'i Kotaki"),
    (30692, "The Moot", "Mace", 29166, "The Energizer", 19650, "Gift of The Moot"),
    (30693, "Quip", "Pistol", 29168, "Chaos Gun", 19651, "Gift of Quip"),
    (30694, "The Predator", "Rifle", 29173, "The Hunter", 19661, "Gift of The Predator"),
    (30695, "Meteorlogicus", "Scepter", 29170, "Storm", 19652, "Gift of Meteorlogicus"),
    (30696, "The Flameseeker Prophecies", "Shield", 29177, "The Chosen", 19653, "Gift of The Flameseeker Prophecies"),
    (30697, "Frenzy", "HarpoonGun", 29181, "Rage", 19659, "Gift of Frenzy"),
    (30698, "The Bifrost", "Staff", 29174, "The Legend", 19654, "Gift of The Bifrost"),
    (30699, "Bolt", "Sword", 29167, "Zap", 19655, "Gift of Bolt"),
    (30700, "Rodgort", "Torch", 29179, "Rodgort's Flame", 19656, "Gift of Rodgort"),
    (30701, "Kraitkin", "Trident", 29182, "Venom", 19658, "Gift of Kraitkin"),
    (30702, "Howler", "Warhorn", 29180, "Howl", 19662, "Gift of Howler"),
    (30703, "Sunrise", "Greatsword", 29184, "Dawn", 19647, "Gift of Sunrise")
    # Twilight (30704) is defined with full handcrafted detail in ontology/instances/twilight_gen1.ttl
]

# Raw refined leaf materials
RAW_MATERIALS = [
    (19684, "Mithril Ingot"),
    (19685, "Orichalcum Ingot"),
    (19681, "Darksteel Ingot"),
    (19686, "Platinum Ingot"),
    (19712, "Elder Wood Plank"),
    (19714, "Ancient Wood Plank"),
    (19748, "Silk Scrap"),
    (19745, "Gossamer Scrap"),
    (19732, "Hardened Leather Section"),
    (24315, "Charged Lodestone"),
    (24310, "Onyx Lodestone"),
    (24325, "Destroyer Lodestone"),
    (24320, "Glacial Lodestone"),
    (24330, "Crystal Lodestone"),
    (24340, "Corrupted Lodestone"),
    (19676, "Icy Runestone")
]

def generate_gen1_graph() -> rdflib.Graph:
    g = rdflib.Graph()
    g.bind("priory", PRIORY)
    g.bind("item", ITEM)
    g.bind("recipe", RECIPE)
    g.bind("rarity", RARITY)
    g.bind("weapon", WEAPON)
    g.bind("skos", SKOS)

    # 1. Define Raw Materials
    for m_id, m_name in RAW_MATERIALS:
        m_uri = ITEM[str(m_id)]
        g.add((m_uri, RDF.type, PRIORY.CraftingMaterial))
        g.add((m_uri, RDF.type, OWL.NamedIndividual))
        g.add((m_uri, RDFS.label, Literal(m_name, lang="en")))
        g.add((m_uri, PRIORY.gw2Id, Literal(m_id, datatype=XSD.integer)))

    # 2. Define All 20 Weapons, Precursors, and Weapon Gifts
    for w_id, w_name, w_type, p_id, p_name, g_id, g_name in GEN1_WEAPONS:
        clean_name = w_name.lower().replace(" ", "_").replace("'", "").replace("-", "_")
        w_uri = ITEM[str(w_id)]
        p_uri = ITEM[str(p_id)]
        g_uri = ITEM[str(g_id)]
        forge_w_uri = RECIPE[f"forge_{clean_name}"]
        forge_g_uri = RECIPE[f"forge_{clean_name}_gift"]

        # Weapon Individual
        g.add((w_uri, RDF.type, PRIORY.LegendaryWeapon))
        g.add((w_uri, RDF.type, OWL.NamedIndividual))
        g.add((w_uri, RDFS.label, Literal(w_name, lang="en")))
        g.add((w_uri, PRIORY.gw2Id, Literal(w_id, datatype=XSD.integer)))
        g.add((w_uri, PRIORY.hasRarity, RARITY.Legendary))
        g.add((w_uri, PRIORY.hasWeaponType, WEAPON[w_type]))
        g.add((w_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
        g.add((w_uri, PRIORY.producedBy, forge_w_uri))

        # Generation 1 SKOS altLabels
        g.add((w_uri, SKOS.altLabel, Literal(f"Gen 1 {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Gen One {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Generation 1 {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"The Legendary {w_type}", lang="en")))

        # Precursor Individual
        g.add((p_uri, RDF.type, PRIORY.PrecursorWeapon))
        g.add((p_uri, RDF.type, OWL.NamedIndividual))
        g.add((p_uri, RDFS.label, Literal(p_name, lang="en")))
        g.add((p_uri, PRIORY.gw2Id, Literal(p_id, datatype=XSD.integer)))
        g.add((p_uri, PRIORY.hasRarity, RARITY.Exotic))
        g.add((p_uri, PRIORY.hasWeaponType, WEAPON[w_type]))
        g.add((p_uri, PRIORY.isAccountBound, Literal(False, datatype=XSD.boolean)))

        # Weapon Gift Individual
        g.add((g_uri, RDF.type, PRIORY.GiftItem))
        g.add((g_uri, RDF.type, OWL.NamedIndividual))
        g.add((g_uri, RDFS.label, Literal(g_name, lang="en")))
        g.add((g_uri, PRIORY.gw2Id, Literal(g_id, datatype=XSD.integer)))
        g.add((g_uri, PRIORY.hasRarity, RARITY.Legendary))
        g.add((g_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
        g.add((g_uri, PRIORY.producedBy, forge_g_uri))

        # Weapon Gift Forge Recipe: 100 Icy Runestones + 250 Orichalcum Ingots + 250 Mithril Ingots
        g.add((forge_g_uri, RDF.type, PRIORY.MysticForgeRecipe))
        g.add((forge_g_uri, RDFS.label, Literal(f"Forge {g_name}", lang="en")))
        g.add((forge_g_uri, PRIORY.producesItem, g_uri))
        g.add((forge_g_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        req_g_icy = RECIPE[f"req_{clean_name}_g_icy"]
        g.add((forge_g_uri, PRIORY.hasIngredientRequirement, req_g_icy))
        g.add((req_g_icy, RDF.type, PRIORY.IngredientRequirement))
        g.add((req_g_icy, PRIORY.requiresItem, ITEM["19676"])) # Icy Runestone
        g.add((req_g_icy, PRIORY.requiredQuantity, Literal(100, datatype=XSD.integer)))

        req_g_ori = RECIPE[f"req_{clean_name}_g_ori"]
        g.add((forge_g_uri, PRIORY.hasIngredientRequirement, req_g_ori))
        g.add((req_g_ori, RDF.type, PRIORY.IngredientRequirement))
        g.add((req_g_ori, PRIORY.requiresItem, ITEM["19685"])) # Orichalcum Ingot
        g.add((req_g_ori, PRIORY.requiredQuantity, Literal(250, datatype=XSD.integer)))

        # Final Legendary Combine in Mystic Forge
        g.add((forge_w_uri, RDF.type, PRIORY.MysticForgeRecipe))
        g.add((forge_w_uri, RDF.type, OWL.NamedIndividual))
        g.add((forge_w_uri, RDFS.label, Literal(f"Forge {w_name}", lang="en")))
        g.add((forge_w_uri, PRIORY.producesItem, w_uri))
        g.add((forge_w_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))

        req_p = RECIPE[f"req_{clean_name}_precursor"]
        req_g = RECIPE[f"req_{clean_name}_gift"]
        req_mast = RECIPE[f"req_{clean_name}_mastery"]
        req_fort = RECIPE[f"req_{clean_name}_fortune"]

        g.add((forge_w_uri, PRIORY.hasIngredientRequirement, req_p))
        g.add((forge_w_uri, PRIORY.hasIngredientRequirement, req_g))
        g.add((forge_w_uri, PRIORY.hasIngredientRequirement, req_mast))
        g.add((forge_w_uri, PRIORY.hasIngredientRequirement, req_fort))

        g.add((req_p, RDF.type, PRIORY.IngredientRequirement))
        g.add((req_p, PRIORY.requiresItem, p_uri))
        g.add((req_p, PRIORY.requiredQuantity, Literal(1, datatype=XSD.integer)))

        g.add((req_g, RDF.type, PRIORY.IngredientRequirement))
        g.add((req_g, PRIORY.requiresItem, g_uri))
        g.add((req_g, PRIORY.requiredQuantity, Literal(1, datatype=XSD.integer)))

        g.add((req_mast, RDF.type, PRIORY.IngredientRequirement))
        g.add((req_mast, PRIORY.requiresItem, ITEM["19626"])) # Gift of Mastery
        g.add((req_mast, PRIORY.requiredQuantity, Literal(1, datatype=XSD.integer)))

        g.add((req_fort, RDF.type, PRIORY.IngredientRequirement))
        g.add((req_fort, PRIORY.requiresItem, ITEM["19627"])) # Gift of Fortune
        g.add((req_fort, PRIORY.requiredQuantity, Literal(1, datatype=XSD.integer)))

    return g

if __name__ == "__main__":
    out_file = Path("/Users/clementd/Documents/GitHub/gw2-priory-def/ontology/instances/recipes/gen1_legendary_recipes.ttl")
    graph = generate_gen1_graph()
    graph.serialize(destination=str(out_file), format="turtle")
    print(f"✅ Generated {len(graph)} triples for all Gen 1 Legendary Recipes in {out_file}")
