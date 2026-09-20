#!/usr/bin/env python3
"""Comprehensive final cleaner for all ontology discrepancies.

Cleans up:
1. Dust tiers in common_items.ttl (24272 - 24277)
2. Quartz crystals in time_gates_and_caps.ttl (43772 = Charged, 43773 = Normal)
3. Ascended daily items in ascended_and_daily_materials.ttl and time_gates_and_caps.ttl
4. Competitive armor items in competitive_armor_and_eternity_recipes.ttl
5. Twilight journey web action names mistakenly typed as item individuals
6. Lodestones & Cores in mystic_forge_transmutations.ttl
7. Regional expansion materials in regional_expansion_materials.ttl
"""

import re
from pathlib import Path

ONTOLOGY_DIR = Path(__file__).parent.parent / "ontology"


def clean_dust_tiers():
    p = ONTOLOGY_DIR / "instances" / "shared" / "common_items.ttl"
    c = p.read_text(encoding="utf-8")
    c = c.replace('rdfs:label "Pile of Shimmering Dust"@en', 'rdfs:label "Pile of Glittering Dust"@en')
    c = c.replace('rdfs:label "Pile of Radiant Dust"@en', 'rdfs:label "Pile of Shimmering Dust"@en')
    c = c.replace('rdfs:label "Pile of Luminous Dust"@en', 'rdfs:label "Pile of Radiant Dust"@en')
    c = c.replace('rdfs:label "Pile of Incandescent Dust"@en', 'rdfs:label "Pile of Luminous Dust"@en')
    p.write_text(c, encoding="utf-8")
    print(f"[+] Fixed dust tiers in {p}")


def clean_quartz_and_ascended():
    # 1. time_gates_and_caps.ttl
    p_time = ONTOLOGY_DIR / "instances" / "shared" / "time_gates_and_caps.ttl"
    if p_time.exists():
        c = p_time.read_text(encoding="utf-8")
        c = c.replace('item:43773', 'item:43772')  # Charged Quartz Crystal is 43772
        c = c.replace('priory:gw2Id 43773', 'priory:gw2Id 43772')
        c = c.replace('rdfs:label "Lump of Mithrilium"@en ;\n    priory:gw2Id 46736', 'rdfs:label "Spiritwood Plank"@en ;\n    priory:gw2Id 46736')
        c = c.replace('rdfs:label "Spool of Thick Elonian Cord"@en ;\n    priory:gw2Id 46742', 'rdfs:label "Lump of Mithrillium"@en ;\n    priory:gw2Id 46742')
        c = c.replace('rdfs:label "Spool of Silk Weaving Thread"@en ;\n    priory:gw2Id 46744', 'rdfs:label "Glob of Elder Spirit Residue"@en ;\n    priory:gw2Id 46744')
        p_time.write_text(c, encoding="utf-8")
        print(f"[+] Fixed time gates in {p_time}")

    # 2. ascended_and_daily_materials.ttl
    p_asc = ONTOLOGY_DIR / "instances" / "shared" / "ascended_and_daily_materials.ttl"
    if p_asc.exists():
        c = p_asc.read_text(encoding="utf-8")
        c = c.replace('rdfs:label "Lump of Mithrilium"@en ;\n    priory:gw2Id 46736', 'rdfs:label "Spiritwood Plank"@en ;\n    priory:gw2Id 46736')
        c = c.replace('rdfs:label "Spiritwood Plank"@en ;\n    priory:gw2Id 46739', 'rdfs:label "Elonian Leather Square"@en ;\n    priory:gw2Id 46739')
        c = c.replace('rdfs:label "Spool of Thick Elonian Cord"@en ;\n    priory:gw2Id 46742', 'rdfs:label "Lump of Mithrillium"@en ;\n    priory:gw2Id 46742')
        c = c.replace('rdfs:label "Elonian Leather Square"@en ;\n    priory:gw2Id 46740', 'rdfs:label "Spool of Thick Elonian Cord"@en ;\n    priory:gw2Id 46740')
        c = c.replace('rdfs:label "Spool of Silk Weaving Thread"@en ;\n    priory:gw2Id 46744', 'rdfs:label "Glob of Elder Spirit Residue"@en ;\n    priory:gw2Id 46744')
        p_asc.write_text(c, encoding="utf-8")
        print(f"[+] Fixed ascended materials in {p_asc}")


def clean_competitive_and_eternity():
    p = ONTOLOGY_DIR / "instances" / "recipes" / "competitive_armor_and_eternity_recipes.ttl"
    if p.exists():
        c = p.read_text(encoding="utf-8")
        # 71581 is Memory of Battle
        # 73248 is Stabilizing Matrix
        c = re.sub(r'item:73248\s+a\s+priory:CraftingMaterial[^\.]*\.', 'item:73248 a priory:CraftingMaterial, owl:NamedIndividual ;\n    rdfs:label "Stabilizing Matrix" ;\n    priory:gw2Id 73248 ;\n    priory:isAccountBound true .', c)
        c = re.sub(r'item:71581\s+a\s+priory:CraftingMaterial[^\.]*\.', 'item:71581 a priory:CraftingMaterial, owl:NamedIndividual ;\n    rdfs:label "Memory of Battle" ;\n    priory:gw2Id 71581 ;\n    priory:isAccountBound true .', c)
        # Fix 80332 mislabel
        c = c.replace('rdfs:label "Triumphant Hero\'s Mantle (Precursor)"@en ; priory:gw2Id 80332', 'rdfs:label "Jade Shard"@en ; priory:gw2Id 80332')
        p.write_text(c, encoding="utf-8")
        print(f"[+] Fixed competitive armor in {p}")


def clean_regional_materials():
    p = ONTOLOGY_DIR / "instances" / "shared" / "regional_expansion_materials.ttl"
    if p.exists():
        c = p.read_text(encoding="utf-8")
        c = c.replace('rdfs:label "Mistonium"@en ;\n    priory:gw2Id 88955', 'rdfs:label "Lump of Mistonium"@en ;\n    priory:gw2Id 88955')
        c = c.replace('rdfs:label "Mistborn Mote"@en ;\n    priory:gw2Id 90783', 'rdfs:label "Mistborn Mote"@en ;\n    priory:gw2Id 90783')
        p.write_text(c, encoding="utf-8")
        print(f"[+] Fixed regional materials in {p}")


def clean_twilight_web():
    p = ONTOLOGY_DIR / "instances" / "twilight_journey_web.ttl"
    if p.exists():
        c = p.read_text(encoding="utf-8")
        # Remove erroneous duplicate item triples that put action descriptions into item labels
        c = re.sub(r'item:19721\s+a\s+priory:GiftItem[^\.]*\.', '', c)
        c = re.sub(r'item:19678\s+a\s+priory:GiftItem[^\.]*\.', '', c)
        p.write_text(c, encoding="utf-8")
        print(f"[+] Cleaned twilight web in {p}")


def clean_lodestones():
    p = ONTOLOGY_DIR / "instances" / "shared" / "mystic_forge_transmutations.ttl"
    if p.exists():
        c = p.read_text(encoding="utf-8")
        # Ensure clean alignment of Cores and Lodestones
        c = c.replace('rdfs:label "Corrupted Lodestone"@en ;\n    priory:gw2Id 24315', 'rdfs:label "Molten Lodestone"@en ;\n    priory:gw2Id 24315')
        c = c.replace('rdfs:label "Molten Core"@en ;\n    priory:gw2Id 24304', 'rdfs:label "Charged Core"@en ;\n    priory:gw2Id 24304')
        c = c.replace('rdfs:label "Molten Lodestone"@en ;\n    priory:gw2Id 24305', 'rdfs:label "Charged Lodestone"@en ;\n    priory:gw2Id 24305')
        c = c.replace('rdfs:label "Glacial Core"@en ;\n    priory:gw2Id 24306', 'rdfs:label "Onyx Sliver"@en ;\n    priory:gw2Id 24306')
        c = c.replace('rdfs:label "Glacial Lodestone"@en ;\n    priory:gw2Id 24307', 'rdfs:label "Onyx Fragment"@en ;\n    priory:gw2Id 24307')
        c = c.replace('rdfs:label "Destroyer Lodestone"@en ;\n    priory:gw2Id 24308', 'rdfs:label "Onyx Shard"@en ;\n    priory:gw2Id 24308')
        c = c.replace('rdfs:label "Charged Core"@en ;\n    priory:gw2Id 24302', 'rdfs:label "Charged Fragment"@en ;\n    priory:gw2Id 24302')
        c = c.replace('rdfs:label "Charged Lodestone"@en ;\n    priory:gw2Id 24303', 'rdfs:label "Charged Shard"@en ;\n    priory:gw2Id 24303')
        c = c.replace('rdfs:label "Corrupted Core"@en ;\n    priory:gw2Id 24314', 'rdfs:label "Molten Core"@en ;\n    priory:gw2Id 24314')
        p.write_text(c, encoding="utf-8")
        print(f"[+] Fixed lodestones in {p}")


def clean_refinements():
    p = ONTOLOGY_DIR / "instances" / "shared" / "common_material_refinements.ttl"
    if p.exists():
        c = p.read_text(encoding="utf-8")
        c = c.replace('rdfs:label "Rawhide Leather Section"@en ;\n    priory:gw2Id 19738', 'rdfs:label "Stretched Rawhide Leather Square"@en ;\n    priory:gw2Id 19738')
        c = c.replace('rdfs:label "Cotton Scrap"@en ;\n    priory:gw2Id 19740', 'rdfs:label "Bolt of Wool"@en ;\n    priory:gw2Id 19740')
        p.write_text(c, encoding="utf-8")
        print(f"[+] Fixed refinements in {p}")


def clean_sigils():
    p = ONTOLOGY_DIR / "instances" / "legendary_sigil.ttl"
    if p.exists():
        c = p.read_text(encoding="utf-8")
        c = c.replace('rdfs:label "Lucent Mote"@en ;\n    priory:gw2Id 89182', 'rdfs:label "Symbol of Pain"@en ;\n    priory:gw2Id 89182')
        p.write_text(c, encoding="utf-8")
        print(f"[+] Fixed sigil in {p}")

    p2 = ONTOLOGY_DIR / "instances" / "shared" / "motes_charms_symbols_and_upgrades.ttl"
    if p2.exists():
        c2 = p2.read_text(encoding="utf-8")
        c2 = c2.replace('rdfs:label "Lucent Mote"@en ;\n    priory:gw2Id 89182', 'rdfs:label "Symbol of Pain"@en ;\n    priory:gw2Id 89182')
        p2.write_text(c2, encoding="utf-8")
        print(f"[+] Fixed motes in {p2}")


if __name__ == "__main__":
    print("[*] Running final comprehensive ontology cleanup...")
    clean_dust_tiers()
    clean_quartz_and_ascended()
    clean_competitive_and_eternity()
    clean_regional_materials()
    clean_twilight_web()
    clean_lodestones()
    clean_refinements()
    clean_sigils()
    print("[+] Done.")
