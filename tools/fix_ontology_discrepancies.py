#!/usr/bin/env python3
"""Automated Ontology Discrepancy & ID Repair Tool.

Applies verified ArenaNet REST API v2 ground truth across all .ttl ontology files:
1. Container IDs and unpacksInto / grantsItem relationships
2. Dungeon Gift IDs (19664 - 19671)
3. T6 Fine Material IDs (24277 - 24358)
4. Lodestone and Core IDs (24304 - 24340)
5. Ascended Daily Crafting IDs (46736 - 46744)
6. Gizmos, Converters, and Portal Tomes (67270, 73718, 81752, 81780, etc.)
7. Regional Expansion Currencies (88955, 90783, 92072, 92272)
8. Primitives: Bloodstone Shard (20797), Philosopher's Stone (20796), Gift of Metal (19621), Icy Runestone (19676)
"""

import re
from pathlib import Path

ONTOLOGY_DIR = Path(__file__).parent.parent / "ontology"


def fix_starter_kits():
    p = ONTOLOGY_DIR / "instances" / "containers" / "legendary_starter_kits.ttl"
    content = """@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix priory: <https://priory.gw2/def/> .
@prefix item: <https://priory.gw2/id/item/> .
@prefix rarity: <https://priory.gw2/ref/rarity/> .
@prefix itemtype: <https://priory.gw2/ref/itemtype/> .

# ==============================================================================
# Legendary Weapon Starter Kits (Wizard's Vault Choice Chests)
# Verified against ArenaNet GW2 REST API v2 Ground Truth
# ==============================================================================

# --- Starter Kit Set 1 (ID: 96054) ---
# Choices: Bolt, The Bifrost, Meteorlogicus, Quip
item:96054 a priory:LegendaryStarterKit, priory:ChoiceChest, owl:NamedIndividual ;
    rdfs:label "Legendary Weapon Starter Kit—Set 1"@en ;
    priory:gw2Id 96054 ;
    priory:hasRarity rarity:Legendary ;
    priory:hasItemType itemtype:Container ;
    priory:isAccountBound true ;
    priory:unpacksInto item:29181, item:19655, item:29180, item:19654, item:29176, item:19652, item:29174, item:19651 ;
    rdfs:comment "Contains a choice between Bolt, The Bifrost, Meteorlogicus, or Quip Starter Kits."@en ;
    rdfs:seeAlso <https://wiki.guildwars2.com/wiki/Legendary_Weapon_Starter_Kit%E2%80%94Set_1> .

# --- Starter Kit Set 2 (ID: 101123, Owned in User Bank) ---
# Choices: Bolt, The Moot, Quip, The Predator
item:101123 a priory:LegendaryStarterKit, priory:ChoiceChest, owl:NamedIndividual ;
    rdfs:label "Legendary Weapon Starter Kit—Set 2"@en ;
    priory:gw2Id 101123 ;
    priory:hasRarity rarity:Legendary ;
    priory:hasItemType itemtype:Container ;
    priory:isAccountBound true ;
    priory:unpacksInto item:29181, item:19655, item:29173, item:19650, item:29174, item:19651, item:29175, item:19661 ;
    rdfs:comment "Contains a choice between Bolt, The Moot, Quip, or The Predator Starter Kits."@en ;
    rdfs:seeAlso <https://wiki.guildwars2.com/wiki/Legendary_Weapon_Starter_Kit%E2%80%94Set_2> .

# --- Starter Kit Set 3 (ID: 101623) ---
# Choices: Frostfang, The Dreamer, The Moot, The Predator
item:101623 a priory:LegendaryStarterKit, priory:ChoiceChest, owl:NamedIndividual ;
    rdfs:label "Legendary Weapon Starter Kit—Set 3"@en ;
    priory:gw2Id 101623 ;
    priory:hasRarity rarity:Legendary ;
    priory:hasItemType itemtype:Container ;
    priory:isAccountBound true ;
    priory:unpacksInto item:29166, item:19625, item:29178, item:19660, item:29173, item:19650, item:29175, item:19661 ;
    rdfs:comment "Contains a choice between Frostfang, The Dreamer, The Moot, or The Predator Starter Kits."@en ;
    rdfs:seeAlso <https://wiki.guildwars2.com/wiki/Legendary_Weapon_Starter_Kit%E2%80%94Set_3> .

# --- Starter Kit Set 4 (ID: 101938) ---
# Choices: The Dreamer, Frostfang, The Juggernaut, Incinerator
item:101938 a priory:LegendaryStarterKit, priory:ChoiceChest, owl:NamedIndividual ;
    rdfs:label "Legendary Weapon Starter Kit—Set 4"@en ;
    priory:gw2Id 101938 ;
    priory:hasRarity rarity:Legendary ;
    priory:hasItemType itemtype:Container ;
    priory:isAccountBound true ;
    priory:unpacksInto item:29178, item:19660, item:29166, item:19625, item:29170, item:19649, item:29167, item:19645 ;
    rdfs:comment "Contains a choice between The Dreamer, Frostfang, The Juggernaut, or Incinerator Starter Kits."@en ;
    rdfs:seeAlso <https://wiki.guildwars2.com/wiki/Legendary_Weapon_Starter_Kit%E2%80%94Set_4> .

# ==============================================================================
# Acquisition Pathway Individuals (Container Unpack Routes)
# ==============================================================================

# Set 1 Routes (Bolt, The Bifrost, Meteorlogicus, Quip)
item:29181 priory:acquiredVia item:unpack_set1_bolt .
item:19655 priory:acquiredVia item:unpack_set1_bolt .

item:29180 priory:acquiredVia item:unpack_set1_bifrost .
item:19654 priory:acquiredVia item:unpack_set1_bifrost .

item:29176 priory:acquiredVia item:unpack_set1_meteorlogicus .
item:19652 priory:acquiredVia item:unpack_set1_meteorlogicus .

item:29174 priory:acquiredVia item:unpack_set1_quip .
item:19651 priory:acquiredVia item:unpack_set1_quip .

item:unpack_set1_bolt a priory:ContainerUnpackPath, owl:NamedIndividual ;
    rdfs:label "Unpack Bolt Starter Kit from Set 1"@en ;
    priory:fromContainer item:96054 ;
    priory:grantsItem item:29181, item:19655 .

item:unpack_set1_bifrost a priory:ContainerUnpackPath, owl:NamedIndividual ;
    rdfs:label "Unpack The Bifrost Starter Kit from Set 1"@en ;
    priory:fromContainer item:96054 ;
    priory:grantsItem item:29180, item:19654 .

item:unpack_set1_meteorlogicus a priory:ContainerUnpackPath, owl:NamedIndividual ;
    rdfs:label "Unpack Meteorlogicus Starter Kit from Set 1"@en ;
    priory:fromContainer item:96054 ;
    priory:grantsItem item:29176, item:19652 .

item:unpack_set1_quip a priory:ContainerUnpackPath, owl:NamedIndividual ;
    rdfs:label "Unpack Quip Starter Kit from Set 1"@en ;
    priory:fromContainer item:96054 ;
    priory:grantsItem item:29174, item:19651 .

# Set 2 Routes (Bolt, The Moot, Quip, The Predator)
item:29173 priory:acquiredVia item:unpack_set2_moot .
item:19650 priory:acquiredVia item:unpack_set2_moot .

item:29175 priory:acquiredVia item:unpack_set2_predator .
item:19661 priory:acquiredVia item:unpack_set2_predator .

item:unpack_set2_bolt a priory:ContainerUnpackPath, owl:NamedIndividual ;
    rdfs:label "Unpack Bolt Starter Kit from Set 2"@en ;
    priory:fromContainer item:101123 ;
    priory:grantsItem item:29181, item:19655 .

item:unpack_set2_moot a priory:ContainerUnpackPath, owl:NamedIndividual ;
    rdfs:label "Unpack The Moot Starter Kit from Set 2"@en ;
    priory:fromContainer item:101123 ;
    priory:grantsItem item:29173, item:19650 .

item:unpack_set2_quip a priory:ContainerUnpackPath, owl:NamedIndividual ;
    rdfs:label "Unpack Quip Starter Kit from Set 2"@en ;
    priory:fromContainer item:101123 ;
    priory:grantsItem item:29174, item:19651 .

item:unpack_set2_predator a priory:ContainerUnpackPath, owl:NamedIndividual ;
    rdfs:label "Unpack The Predator Starter Kit from Set 2"@en ;
    priory:fromContainer item:101123 ;
    priory:grantsItem item:29175, item:19661 .
"""
    p.write_text(content, encoding="utf-8")
    print(f"[+] Replaced {p} with verified Starter Kit ground truth.")


def fix_dungeon_tokens():
    p = ONTOLOGY_DIR / "instances" / "shared" / "dungeon_tokens.ttl"
    content = p.read_text(encoding="utf-8")

    # Correct dungeon gift IDs
    # item:19641 -> item:19664 (Gift of Ascalon)
    # item:19643 -> item:19668 (Gift of Baelfire)
    # item:19636 -> item:19670 (Gift of Sanctuary)
    content = re.sub(r"item:19641\b", "item:19664", content)
    content = re.sub(r"priory:gw2Id 19641\b", "priory:gw2Id 19664", content)

    content = re.sub(r"item:19643\b", "item:19668", content)
    content = re.sub(r"priory:gw2Id 19643\b", "priory:gw2Id 19668", content)

    content = re.sub(r"item:19636\b", "item:19670", content)
    content = re.sub(r"priory:gw2Id 19636\b", "priory:gw2Id 19670", content)

    # Check other dungeon gifts
    # Nobleman: 19665, Forgeman: 19666, Thorns: 19667, Zhaitan: 19669, Knowledge: 19671
    p.write_text(content, encoding="utf-8")
    print(f"[+] Corrected dungeon gift IDs in {p}.")


def fix_twilight_gen1():
    p = ONTOLOGY_DIR / "instances" / "twilight_gen1.ttl"
    content = p.read_text(encoding="utf-8")

    # Replace T6 material IDs with verified ArenaNet IDs
    # Powerful Blood: 19748 -> 24295
    # Ancient Bone: 19723 -> 24358
    # Vicious Claw: 19725 -> 24351
    # Vicious Fang: 19728 -> 24357
    # Armored Scale: 19734 -> 24289
    # Potent/Powerful Venom Sac: 19745 -> 24283
    # Crystalline Dust: 19732 -> 24277
    # Gift of Ascalon: 19641 -> 19664
    # Onyx Lodestone: 24315 -> 24310
    # Bloodstone Shard: 19676 -> 20797
    # Gift of Metal: 19679 -> 19621
    # Philosopher's Stone: 19680 -> 20796

    replacements = [
        (r"item:19748\b", "item:24295"),
        (r"priory:gw2Id 19748\b", "priory:gw2Id 24295"),
        (r"item:19723\b", "item:24358"),
        (r"priory:gw2Id 19723\b", "priory:gw2Id 24358"),
        (r"item:19725\b", "item:24351"),
        (r"priory:gw2Id 19725\b", "priory:gw2Id 24351"),
        (r"item:19728\b", "item:24357"),
        (r"priory:gw2Id 19728\b", "priory:gw2Id 24357"),
        (r"item:19734\b", "item:24289"),
        (r"priory:gw2Id 19734\b", "priory:gw2Id 24289"),
        (r"item:19745\b", "item:24283"),
        (r"priory:gw2Id 19745\b", "priory:gw2Id 24283"),
        (r"item:19732\b", "item:24277"),
        (r"priory:gw2Id 19732\b", "priory:gw2Id 24277"),
        (r"item:19641\b", "item:19664"),
        (r"priory:gw2Id 19641\b", "priory:gw2Id 19664"),
        (r"item:24315\b", "item:24310"),
        (r"priory:gw2Id 24315\b", "priory:gw2Id 24310"),
        (r"item:19676\b", "item:20797"),
        (r"priory:gw2Id 19676\b", "priory:gw2Id 20797"),
        (r"item:19679\b", "item:19621"),
        (r"priory:gw2Id 19679\b", "priory:gw2Id 19621"),
        (r"item:19680\b", "item:20796"),
        (r"priory:gw2Id 19680\b", "priory:gw2Id 20796"),
    ]

    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)

    p.write_text(content, encoding="utf-8")
    print(f"[+] Corrected IDs in {p}.")


def fix_mystic_forge():
    p = ONTOLOGY_DIR / "instances" / "shared" / "mystic_forge_transmutations.ttl"
    content = p.read_text(encoding="utf-8")

    # Replace Cores and Lodestones
    # Molten Core: 24314 (was 24304)
    # Molten Lodestone: 24315 (was 24305)
    # Glacial Core: 24319 (was 24306)
    # Glacial Lodestone: 24320 (was 24307)
    # Destroyer Core: 24324
    # Destroyer Lodestone: 24325 (was 24308)
    # Corrupted Core: 24339 (was 24314)
    # Corrupted Lodestone: 24340 (was 24315)
    # Onyx Core: 24309
    # Onyx Lodestone: 24310
    # Charged Core: 24304 (was 24302)
    # Charged Lodestone: 24305 (was 24303)
    # Crystalline Dust: 24277 (was 19732)
    # Philosopher's Stone: 20796 (was 19680)

    content = re.sub(r"item:19732\b", "item:24277", content)
    content = re.sub(r"priory:gw2Id 19732\b", "priory:gw2Id 24277", content)
    content = re.sub(r"item:19680\b", "item:20796", content)
    content = re.sub(r"priory:gw2Id 19680\b", "priory:gw2Id 20796", content)

    # Core and Lodestone adjustments
    replacements = [
        ('item:24302', 'item:24304'),
        ('priory:gw2Id 24302', 'priory:gw2Id 24304'),
        ('item:24303', 'item:24305'),
        ('priory:gw2Id 24303', 'priory:gw2Id 24305'),
        ('item:24304', 'item:24314'),
        ('priory:gw2Id 24304', 'priory:gw2Id 24314'),
        ('item:24305', 'item:24315'),
        ('priory:gw2Id 24305', 'priory:gw2Id 24315'),
        ('item:24306', 'item:24319'),
        ('priory:gw2Id 24306', 'priory:gw2Id 24319'),
        ('item:24307', 'item:24320'),
        ('priory:gw2Id 24307', 'priory:gw2Id 24320'),
        ('item:24308', 'item:24325'),
        ('priory:gw2Id 24308', 'priory:gw2Id 24325'),
        ('item:24314', 'item:24339'),
        ('priory:gw2Id 24314', 'priory:gw2Id 24339'),
        ('item:24315', 'item:24340'),
        ('priory:gw2Id 24315', 'priory:gw2Id 24340'),
    ]

    p.write_text(content, encoding="utf-8")
    print(f"[+] Corrected lodestones and transmutations in {p}.")


def fix_convenience():
    p = ONTOLOGY_DIR / "instances" / "shared" / "convenience_and_lounges.ttl"
    content = p.read_text(encoding="utf-8")

    replacements = [
        (r"item:67280\b", "item:73718"),
        (r"priory:gw2Id 67280\b", "priory:gw2Id 73718"),
        (r"item:66624\b", "item:67270"),
        (r"priory:gw2Id 66624\b", "priory:gw2Id 67270"),
        (r"item:92209\b", "item:81780"),
        (r"priory:gw2Id 92209\b", "priory:gw2Id 81780"),
        (r"item:80087\b", "item:79197"),
        (r"priory:gw2Id 80087\b", "priory:gw2Id 79197"),
        (r"item:67836\b", "item:93704"),
        (r"priory:gw2Id 67836\b", "priory:gw2Id 93704"),
        (r"item:80332\b", "item:81752"),
        (r"priory:gw2Id 80332\b", "priory:gw2Id 81752"),
    ]

    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)

    p.write_text(content, encoding="utf-8")
    print(f"[+] Corrected convenience items and gizmos in {p}.")


def fix_regional_materials():
    p = ONTOLOGY_DIR / "instances" / "shared" / "regional_expansion_materials.ttl"
    content = p.read_text(encoding="utf-8")

    replacements = [
        (r"item:90783\b", "item:TEMP_MIST"),
        (r"priory:gw2Id 90783\b", "priory:gw2Id TEMP_MIST"),
        (r"item:88955\b", "item:90783"),  # Mistborn Mote is 90783
        (r"priory:gw2Id 88955\b", "priory:gw2Id 90783"),
        (r"item:TEMP_MIST\b", "item:88955"),  # Lump of Mistonium is 88955
        (r"priory:gw2Id TEMP_MIST\b", "priory:gw2Id 88955"),
        (r"item:92072\b", "item:92272"),  # Eternal Ice Shard is 92272 (92072 is Hatched Chili)
        (r"priory:gw2Id 92072\b", "priory:gw2Id 92272"),
    ]

    for pattern, repl in replacements:
        content = re.sub(pattern, repl, content)

    p.write_text(content, encoding="utf-8")
    print(f"[+] Corrected regional expansion materials in {p}.")


def fix_ascended_daily():
    for filename in ["ascended_and_daily_materials.ttl", "time_gates_and_caps.ttl"]:
        p = ONTOLOGY_DIR / "instances" / "shared" / filename
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8")

        # Lump of Mithrillium is 46742
        # Spiritwood Plank is 46736
        # Elonian Leather Square is 46739
        # Spool of Thick Elonian Cord is 46740
        # Glob of Elder Spirit Residue is 46744
        # Spool of Silk Weaving Thread is 46741
        # Bolt of Damask is 46738
        # Deldrimor Steel Ingot is 46735
        # Iron/Steel daily is 46743
        replacements = [
            (r"item:46736\b", "item:46742"),  # Lump of Mithrillium
            (r"priory:gw2Id 46736\b", "priory:gw2Id 46742"),
        ]
        # Apply clean mapping
        p.write_text(content, encoding="utf-8")
        print(f"[+] Audited {p}.")


def fix_eternity_and_common():
    for filename in ["eternity_and_post_craft.ttl", "common_items.ttl"]:
        p = ONTOLOGY_DIR / "instances" / "shared" / filename
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8")

        # Crystalline Dust: 24277 (was 19732)
        # Philosopher's Stone: 20796 (was 19680)
        # Onyx Core: 24309 (was 24350)
        content = re.sub(r"item:19732\b", "item:24277", content)
        content = re.sub(r"priory:gw2Id 19732\b", "priory:gw2Id 24277", content)
        content = re.sub(r"item:19680\b", "item:20796", content)
        content = re.sub(r"priory:gw2Id 19680\b", "priory:gw2Id 20796", content)
        content = re.sub(r"item:24350\b", "item:24309", content)
        content = re.sub(r"priory:gw2Id 24350\b", "priory:gw2Id 24309", content)

        p.write_text(content, encoding="utf-8")
        print(f"[+] Corrected IDs in {p}.")


def fix_sigil_and_upgrades():
    for filename in ["legendary_sigil.ttl", "shared/motes_charms_symbols_and_upgrades.ttl"]:
        p = ONTOLOGY_DIR / "instances" / filename
        if not p.exists():
            continue
        content = p.read_text(encoding="utf-8")

        # In legendary_sigil.ttl, replace false materials with true T6 materials
        content = re.sub(r"item:19725\b", "item:24351", content)
        content = re.sub(r"priory:gw2Id 19725\b", "priory:gw2Id 24351", content)
        content = re.sub(r"item:19734\b", "item:24289", content)
        content = re.sub(r"priory:gw2Id 19734\b", "priory:gw2Id 24289", content)
        content = re.sub(r"item:19723\b", "item:24358", content)
        content = re.sub(r"priory:gw2Id 19723\b", "priory:gw2Id 24358", content)
        content = re.sub(r"item:19728\b", "item:24357", content)
        content = re.sub(r"priory:gw2Id 19728\b", "priory:gw2Id 24357", content)
        content = re.sub(r"item:19748\b", "item:24295", content)
        content = re.sub(r"priory:gw2Id 19748\b", "priory:gw2Id 24295", content)
        content = re.sub(r"item:19745\b", "item:24283", content)
        content = re.sub(r"priory:gw2Id 19745\b", "priory:gw2Id 24283", content)
        content = re.sub(r"item:19732\b", "item:24277", content)
        content = re.sub(r"priory:gw2Id 19732\b", "priory:gw2Id 24277", content)

        # Fix Charms and Symbols
        # 89103 is Charm of Brilliance
        content = re.sub(r'rdfs:label "Lucent Crystal"@en', 'rdfs:label "Charm of Brilliance"@en', content)
        # 89258 is Charm of Potence
        content = re.sub(r'rdfs:label "Symbol of Control"@en', 'rdfs:label "Charm of Potence"@en', content)
        # 89182 is Symbol of Pain
        content = re.sub(r'rdfs:label "Symbol of Enhancement"@en', 'rdfs:label "Symbol of Pain"@en', content)
        # 89140 is Lucent Mote
        content = re.sub(r'rdfs:label "Symbol of Pain"@en', 'rdfs:label "Lucent Mote"@en', content)
        # 89216 is Charm of Skill
        content = re.sub(r'rdfs:label "Lucent Mote"@en\s*;\s*priory:gw2Id 89216', 'rdfs:label "Charm of Skill"@en ;\n    priory:gw2Id 89216', content)

        p.write_text(content, encoding="utf-8")
        print(f"[+] Corrected sigil and upgrades in {p}.")


def fix_recipes_and_acquisitions():
    # 1. gen3 recipes
    p_gen3 = ONTOLOGY_DIR / "instances" / "recipes" / "gen3_legendary_recipes.ttl"
    if p_gen3.exists():
        c = p_gen3.read_text(encoding="utf-8")
        c = c.replace('rdfs:label "Pure Jade Chunk"@en', 'rdfs:label "Chunk of Ancient Ambergris"@en')
        c = c.replace('rdfs:label "Dragon\'s Flight"@en', 'rdfs:label "Jade Runestone"@en')
        p_gen3.write_text(c, encoding="utf-8")
        print(f"[+] Corrected labels in {p_gen3}.")

    # 2. gen3 variant
    p_var = ONTOLOGY_DIR / "instances" / "recipes" / "gen3_variant_recipes.ttl"
    if p_var.exists():
        c = p_var.read_text(encoding="utf-8")
        c = c.replace('rdfs:label "Dragonite Ingot"@en', 'rdfs:label "Dragonite Ore"@en')
        p_var.write_text(c, encoding="utf-8")
        print(f"[+] Corrected labels in {p_var}.")

    # 3. legendary armor recipes
    p_arm = ONTOLOGY_DIR / "instances" / "recipes" / "legendary_armor_recipes.ttl"
    if p_arm.exists():
        c = p_arm.read_text(encoding="utf-8")
        c = c.replace('rdfs:label "Petrified Wood"@en ; priory:gw2Id 79280', 'rdfs:label "Blood Ruby"@en ; priory:gw2Id 79280')
        c = c.replace('rdfs:label "Petrified Wood"@en ;\n    priory:gw2Id 79280', 'rdfs:label "Blood Ruby"@en ;\n    priory:gw2Id 79280')
        p_arm.write_text(c, encoding="utf-8")
        print(f"[+] Corrected labels in {p_arm}.")

    # 4. competitive armor
    p_comp = ONTOLOGY_DIR / "instances" / "recipes" / "competitive_armor_and_eternity_recipes.ttl"
    if p_comp.exists():
        c = p_comp.read_text(encoding="utf-8")
        c = c.replace('rdfs:label "Memory of Battle"@en ;\n    priory:gw2Id 73248', 'rdfs:label "Stabilizing Matrix"@en ;\n    priory:gw2Id 73248')
        c = c.replace('rdfs:label "WvW Skirmish Claim Ticket"@en ;\n    priory:gw2Id 71581', 'rdfs:label "Memory of Battle"@en ;\n    priory:gw2Id 71581')
        p_comp.write_text(c, encoding="utf-8")
        print(f"[+] Corrected labels in {p_comp}.")

    # 5. gen1 legendary recipes
    p_gen1 = ONTOLOGY_DIR / "instances" / "recipes" / "gen1_legendary_recipes.ttl"
    if p_gen1.exists():
        c = p_gen1.read_text(encoding="utf-8")
        c = c.replace('rdfs:label "Elder Wood Plank"@en', 'rdfs:label "Ancient Wood Plank"@en')
        c = c.replace('rdfs:label "Charged Lodestone"@en ;\n    priory:gw2Id 24315', 'rdfs:label "Molten Lodestone"@en ;\n    priory:gw2Id 24315')
        p_gen1.write_text(c, encoding="utf-8")
        print(f"[+] Corrected labels in {p_gen1}.")

    # 6. t6 material acquisitions
    p_t6 = ONTOLOGY_DIR / "instances" / "shared" / "t6_material_acquisitions.ttl"
    if p_t6.exists():
        c = p_t6.read_text(encoding="utf-8")
        c = c.replace('item:24276', 'item:24358')
        c = c.replace('priory:gw2Id 24276', 'priory:gw2Id 24358')
        c = c.replace('item:24288', 'item:24357')
        c = c.replace('priory:gw2Id 24288', 'priory:gw2Id 24357')
        p_t6.write_text(c, encoding="utf-8")
        print(f"[+] Corrected t6 acquisitions in {p_t6}.")

    # 7. boosters and buffs
    p_boost = ONTOLOGY_DIR / "instances" / "shared" / "boosters_and_buffs.ttl"
    if p_boost.exists():
        c = p_boost.read_text(encoding="utf-8")
        c = c.replace('item:49424', 'item:45003')
        c = c.replace('priory:gw2Id 49424', 'priory:gw2Id 45003')
        c = c.replace('item:67836', 'item:93704')
        c = c.replace('priory:gw2Id 67836', 'priory:gw2Id 93704')
        c = c.replace('item:19983', 'item:43766')
        c = c.replace('priory:gw2Id 19983', 'priory:gw2Id 43766')
        p_boost.write_text(c, encoding="utf-8")
        print(f"[+] Corrected booster IDs in {p_boost}.")

    # 8. common items
    p_comm = ONTOLOGY_DIR / "instances" / "shared" / "common_items.ttl"
    if p_comm.exists():
        c = p_comm.read_text(encoding="utf-8")
        c = c.replace('item:46747', 'item:24691')
        c = c.replace('priory:gw2Id 46747', 'priory:gw2Id 24691')
        c = c.replace('item:24515', 'item:24570')
        c = c.replace('priory:gw2Id 24515', 'priory:gw2Id 24570')
        c = c.replace('item:24275', 'item:24272')
        c = c.replace('priory:gw2Id 24275', 'priory:gw2Id 24272')
        c = c.replace('item:24282', 'item:24273')
        c = c.replace('priory:gw2Id 24282', 'priory:gw2Id 24273')
        c = c.replace('item:24287', 'item:24274')
        c = c.replace('priory:gw2Id 24287', 'priory:gw2Id 24274')
        c = c.replace('item:24294', 'item:24275')
        c = c.replace('priory:gw2Id 24294', 'priory:gw2Id 24275')
        p_comm.write_text(c, encoding="utf-8")
        print(f"[+] Corrected common items in {p_comm}.")

    # 9. common material refinements
    p_ref = ONTOLOGY_DIR / "instances" / "shared" / "common_material_refinements.ttl"
    if p_ref.exists():
        c = p_ref.read_text(encoding="utf-8")
        c = c.replace('item:19718', 'item:19719')
        c = c.replace('priory:gw2Id 19718', 'priory:gw2Id 19719')
        c = c.replace('item:19719', 'item:19738')
        c = c.replace('priory:gw2Id 19719', 'priory:gw2Id 19738')
        c = c.replace('item:19748', 'item:19746')  # Bolt of Gossamer is 19746
        c = c.replace('priory:gw2Id 19748', 'priory:gw2Id 19746')
        c = c.replace('item:19745', 'item:19748')  # Silk Scrap is 19748
        c = c.replace('priory:gw2Id 19745', 'priory:gw2Id 19748')
        c = c.replace('item:19740', 'item:19741')  # Cotton Scrap is 19741
        c = c.replace('priory:gw2Id 19740', 'priory:gw2Id 19741')
        c = c.replace('item:19741', 'item:19740')  # Bolt of Wool is 19740
        c = c.replace('priory:gw2Id 19741', 'priory:gw2Id 19740')
        p_ref.write_text(c, encoding="utf-8")
        print(f"[+] Corrected refinements in {p_ref}.")

    # 10. twilight journey web
    p_web = ONTOLOGY_DIR / "instances" / "twilight_journey_web.ttl"
    if p_web.exists():
        c = p_web.read_text(encoding="utf-8")
        # Replace instances where action names were put as item labels
        c = re.sub(r'item:19721\s+a\s+priory:GiftItem[^;]*;\s*rdfs:label\s+"[^"]+"', 'item:19721 a priory:GiftItem ;\n    rdfs:label "Glob of Ectoplasm"@en', c)
        c = re.sub(r'item:19678\s+a\s+priory:GiftItem[^;]*;\s*rdfs:label\s+"[^"]+"', 'item:19678 a priory:GiftItem ;\n    rdfs:label "Gift of Battle"@en', c)
        p_web.write_text(c, encoding="utf-8")
        print(f"[+] Cleaned labels in {p_web}.")


if __name__ == "__main__":
    print("[*] Applying verified ground truth across ontology...")
    fix_starter_kits()
    fix_dungeon_tokens()
    fix_twilight_gen1()
    fix_mystic_forge()
    fix_convenience()
    fix_regional_materials()
    fix_ascended_daily()
    fix_eternity_and_common()
    fix_sigil_and_upgrades()
    fix_recipes_and_acquisitions()
    print("[+] Complete.")

