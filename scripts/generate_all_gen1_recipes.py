"""Generates complete OWL/RDF instance graphs for all 20 Generation 1 Legendary Weapons,
their precursor weapons, weapon-specific gifts, and Mystic Forge recipe DAGs.
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
    (30684, "Frostfang", "Axe", 29169, "Tooth of Frostfang", 19636, "Gift of Frostfang"),
    (30685, "Kudzu", "Longbow", 29171, "Leaf of Kudzu", 19646, "Gift of Kudzu"),
    (30686, "The Dreamer", "ShortBow", 29175, "The Lover", 19650, "Gift of The Dreamer"),
    (30687, "Incinerator", "Dagger", 29165, "Spark", 19637, "Gift of Incinerator"),
    (30688, "The Minstrel", "Focus", 29178, "The Bard", 19653, "Gift of Music"),
    (30690, "The Juggernaut", "Hammer", 29172, "The Colossus", 19647, "Gift of The Juggernaut"),
    (30691, "Kamohoali'i Kotaki", "Spear", 29183, "Carcharias", 19661, "Gift of the Deep"),
    (30692, "The Moot", "Mace", 29166, "The Energizer", 19642, "Gift of The Moot"),
    (30693, "Quip", "Pistol", 29168, "Chaos Gun", 19643, "Gift of Quip"),
    (30694, "The Predator", "Rifle", 29173, "The Hunter", 19648, "Gift of The Predator"),
    (30695, "Meteorlogicus", "Scepter", 29170, "Storm", 19645, "Gift of Weather"),
    (30696, "The Flameseeker Prophecies", "Shield", 29177, "The Chosen", 19652, "Gift of History"),
    (30697, "Frenzy", "HarpoonGun", 29181, "Rage", 19659, "Gift of Water"),
    (30698, "The Bifrost", "Staff", 29174, "The Legend", 19649, "Gift of The Bifrost"),
    (30699, "Bolt", "Sword", 29167, "Zap", 19641, "Gift of Bolt"),
    (30700, "Rodgort", "Torch", 29179, "Rodgort's Flame", 19654, "Gift of Rodgort"),
    (30701, "Kraitkin", "Trident", 29182, "Venom", 19660, "Gift of Souls"),
    (30702, "Howler", "Warhorn", 29180, "Howl", 19656, "Gift of Howler"),
    (30703, "Sunrise", "Greatsword", 29184, "Dawn", 19657, "Gift of Sunrise")
]

def generate_gen1_graph() -> rdflib.Graph:
    g = rdflib.Graph()
    g.bind("priory", PRIORY)
    g.bind("item", ITEM)
    g.bind("recipe", RECIPE)
    g.bind("rarity", RARITY)
    g.bind("weapon", WEAPON)
    g.bind("skos", SKOS)

    for w_id, w_name, w_type, p_id, p_name, g_id, g_name in GEN1_WEAPONS:
        clean_name = w_name.lower().replace(" ", "_").replace("'", "").replace("-", "_")
        w_uri = ITEM[str(w_id)]
        p_uri = ITEM[str(p_id)]
        g_uri = ITEM[str(g_id)]
        forge_w_uri = RECIPE[f"forge_{clean_name}"]

        # 1. Weapon Individual
        g.add((w_uri, RDF.type, PRIORY.LegendaryWeapon))
        g.add((w_uri, RDF.type, OWL.NamedIndividual))
        g.add((w_uri, RDFS.label, Literal(w_name, lang="en")))
        g.add((w_uri, PRIORY.gw2Id, Literal(w_id, datatype=XSD.integer)))
        g.add((w_uri, PRIORY.hasRarity, RARITY.Legendary))
        g.add((w_uri, PRIORY.hasWeaponType, WEAPON[w_type]))
        g.add((w_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))
        g.add((w_uri, PRIORY.producedBy, forge_w_uri))

        # Add SKOS altLabels for colloquial resolution
        g.add((w_uri, SKOS.altLabel, Literal(f"Gen 1 {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Gen One {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Generation 1 {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"Legendary {w_type}", lang="en")))
        g.add((w_uri, SKOS.altLabel, Literal(f"The Legendary {w_type}", lang="en")))

        # 2. Precursor Individual
        g.add((p_uri, RDF.type, PRIORY.PrecursorWeapon))
        g.add((p_uri, RDF.type, OWL.NamedIndividual))
        g.add((p_uri, RDFS.label, Literal(p_name, lang="en")))
        g.add((p_uri, PRIORY.gw2Id, Literal(p_id, datatype=XSD.integer)))
        g.add((p_uri, PRIORY.hasRarity, RARITY.Exotic))
        g.add((p_uri, PRIORY.hasWeaponType, WEAPON[w_type]))
        g.add((p_uri, PRIORY.isAccountBound, Literal(False, datatype=XSD.boolean)))

        # 3. Weapon Gift Individual
        g.add((g_uri, RDF.type, PRIORY.GiftItem))
        g.add((g_uri, RDF.type, OWL.NamedIndividual))
        g.add((g_uri, RDFS.label, Literal(g_name, lang="en")))
        g.add((g_uri, PRIORY.gw2Id, Literal(g_id, datatype=XSD.integer)))
        g.add((g_uri, PRIORY.hasRarity, RARITY.Legendary))
        g.add((g_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))

        # 4. Forge Recipe for Weapon
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
