#!/usr/bin/env python3
"""Comprehensive Ground-Truth Repair Script for Project Priory Ontology.
Replaces all remaining fatal/invalid item IDs with canonical ArenaNet API v2 ground truth.
"""

import re
from pathlib import Path

ONTOLOGY_DIR = Path(__file__).parent.parent / "ontology"

def replace_in_file(path: Path, replacements: list):
    content = path.read_text(encoding="utf-8")
    original = content
    for old_pattern, new_text in replacements:
        if callable(new_text):
            content = re.sub(old_pattern, new_text, content)
        else:
            content = re.sub(old_pattern, new_text, content)
    if content != original:
        path.write_text(content, encoding="utf-8")
        print(f"[+] Updated: {path.relative_to(ONTOLOGY_DIR.parent)}")

def run_repairs():
    print("[*] Repairing remaining fatal discrepancies across ontology...")

    # 1. competitive_and_raid_currencies.ttl
    comp_curr = ONTOLOGY_DIR / "instances" / "shared" / "competitive_and_raid_currencies.ttl"
    if comp_curr.exists():
        content = comp_curr.read_text(encoding="utf-8")
        # Replace item:70543 (PvP League Ticket) with currency:30
        content = re.sub(r'item:70543\s+a\s+priory:CraftingMaterial', 'currency:30 a priory:Currency, skos:Concept', content)
        content = content.replace('item:70543', 'currency:30')
        # Replace item:81722 (Ascended Shard of Glory) with currency:33
        content = re.sub(r'item:81722\s+a\s+priory:CraftingMaterial', 'currency:33 a priory:Currency, skos:Concept', content)
        content = content.replace('item:81722', 'currency:33')
        # Replace item:73580 (Shard of Glory) with item:70820
        content = content.replace('item:73580', 'item:70820').replace('priory:gw2Id 73580', 'priory:gw2Id 70820')
        # Remove item:79803 (Star of Destiny)
        content = re.sub(r'item:79803\s+a\s+priory:CraftingMaterial[^.]+\.\n*', '', content)
        comp_curr.write_text(content, encoding="utf-8")
        print("[+] Fixed: competitive_and_raid_currencies.ttl")

    # 2. precursor_taxonomy.ttl (remove 79803, 82792, 86304, 90552, 91877 references)
    tax_file = ONTOLOGY_DIR / "instances" / "shared" / "precursor_taxonomy.ttl"
    if tax_file.exists():
        content = tax_file.read_text(encoding="utf-8")
        content = content.replace('item:79803', 'item:79570') # Endeavor
        content = content.replace('item:82792', 'item:81634') # Might of Arah
        content = content.replace('item:86304', 'item:89036') # The Cure
        content = content.replace('item:90552', 'item:90883') # Exitare
        content = content.replace('item:91877', 'item:87764') # Call of the Void
        tax_file.write_text(content, encoding="utf-8")
        print("[+] Fixed: precursor_taxonomy.ttl")

    # 3. dusk_precursor_collection.ttl
    dusk_file = ONTOLOGY_DIR / "instances" / "shared" / "dusk_precursor_collection.ttl"
    if dusk_file.exists():
        content = dusk_file.read_text(encoding="utf-8")
        content = content.replace('item:71850', 'item:75592').replace('priory:gw2Id 71850', 'priory:gw2Id 75592')
        content = content.replace('item:75037', 'item:73524').replace('priory:gw2Id 75037', 'priory:gw2Id 73524')
        content = content.replace('item:73618', 'item:75632').replace('priory:gw2Id 73618', 'priory:gw2Id 75632')
        content = content.replace('item:76081', 'item:75618').replace('priory:gw2Id 76081', 'priory:gw2Id 75618')
        content = content.replace('item:74483', 'item:73193').replace('priory:gw2Id 74483', 'priory:gw2Id 73193')
        content = content.replace('item:76377', 'item:76379').replace('priory:gw2Id 76377', 'priory:gw2Id 76379')
        content = content.replace('item:75878', 'item:73291').replace('priory:gw2Id 75878', 'priory:gw2Id 73291').replace('Mirror of the Night', 'Mirror')
        content = content.replace('item:74895', 'item:73411').replace('priory:gw2Id 74895', 'priory:gw2Id 73411')
        dusk_file.write_text(content, encoding="utf-8")
        print("[+] Fixed: dusk_precursor_collection.ttl")

    # 4. eternity_and_post_craft.ttl
    eternity_file = ONTOLOGY_DIR / "instances" / "shared" / "eternity_and_post_craft.ttl"
    if eternity_file.exists():
        content = eternity_file.read_text(encoding="utf-8")
        content = content.replace('item:67390', 'item:9574').replace('priory:gw2Id 67390', 'priory:gw2Id 9574')
        content = content.replace('item:8948', 'item:9574').replace('priory:gw2Id 8948', 'priory:gw2Id 9574')
        eternity_file.write_text(content, encoding="utf-8")
        print("[+] Fixed: eternity_and_post_craft.ttl")

    # 5. convenience_and_lounges.ttl
    conv_file = ONTOLOGY_DIR / "instances" / "shared" / "convenience_and_lounges.ttl"
    if conv_file.exists():
        content = conv_file.read_text(encoding="utf-8")
        content = content.replace('item:35727', 'item:70013').replace('priory:gw2Id 35727', 'priory:gw2Id 70013')
        conv_file.write_text(content, encoding="utf-8")
        print("[+] Fixed: convenience_and_lounges.ttl")

    # 6. legendary_sigil.ttl
    sigil_file = ONTOLOGY_DIR / "instances" / "legendary_sigil.ttl"
    if sigil_file.exists():
        content = sigil_file.read_text(encoding="utf-8")
        content = content.replace('item:89276', 'item:77451').replace('priory:gw2Id 89276', 'priory:gw2Id 77451')
        sigil_file.write_text(content, encoding="utf-8")
        print("[+] Fixed: legendary_sigil.ttl")

    # 7. regional_expansion_materials.ttl and legendary_milestone_vendors.ttl
    reg_file = ONTOLOGY_DIR / "instances" / "shared" / "regional_expansion_materials.ttl"
    if reg_file.exists():
        content = reg_file.read_text(encoding="utf-8")
        content = content.replace('item:100140', 'item:100798').replace('priory:gw2Id 100140', 'priory:gw2Id 100798')
        content = content.replace('item:82414', 'item:86036').replace('priory:gw2Id 82414', 'priory:gw2Id 86036') # Gift of Desert Mastery
        content = content.replace('item:82860', 'item:81861').replace('priory:gw2Id 82860', 'priory:gw2Id 81861') # Gift of Draconic Mastery
        reg_file.write_text(content, encoding="utf-8")
        print("[+] Fixed: regional_expansion_materials.ttl")

    vendor_file = ONTOLOGY_DIR / "instances" / "shared" / "legendary_milestone_vendors.ttl"
    if vendor_file.exists():
        content = vendor_file.read_text(encoding="utf-8")
        content = content.replace('item:100140', 'item:100798')
        vendor_file.write_text(content, encoding="utf-8")
        print("[+] Fixed: legendary_milestone_vendors.ttl")

    # 8. legendary_trinkets_and_upgrades.ttl
    trinket_file = ONTOLOGY_DIR / "instances" / "recipes" / "legendary_trinkets_and_upgrades.ttl"
    if trinket_file.exists():
        content = trinket_file.read_text(encoding="utf-8")
        # Warbringer: Warcry 81467, Gift of Warfare 81478, Gift of Conquering 81371
        content = content.replace('item:81464', 'item:81467').replace('priory:gw2Id 81464', 'priory:gw2Id 81467')
        content = content.replace('item:81463', 'item:81478').replace('priory:gw2Id 81463', 'priory:gw2Id 81478')
        content = content.replace('item:81465', 'item:81371').replace('priory:gw2Id 81465', 'priory:gw2Id 81371')
        # The Ascension: Gift of the Competitor 77509
        content = content.replace('item:78430', 'item:77509').replace('priory:gw2Id 78430', 'priory:gw2Id 77509')
        # Aurora: Spark of Sentience 81729, Gift of Draconic Mastery 81861
        content = content.replace('item:82449', 'item:81729').replace('priory:gw2Id 82449', 'priory:gw2Id 81729')
        content = content.replace('item:82860', 'item:81861').replace('priory:gw2Id 82860', 'priory:gw2Id 81861')
        # Transcendence: Slumbering Transcendence 92993
        content = content.replace('item:92993', 'item:92993')
        trinket_file.write_text(content, encoding="utf-8")
        print("[+] Fixed: legendary_trinkets_and_upgrades.ttl")

    # 9. competitive_armor_and_eternity_recipes.ttl (Star of Glory 83872)
    comp_rec = ONTOLOGY_DIR / "instances" / "recipes" / "competitive_armor_and_eternity_recipes.ttl"
    if comp_rec.exists():
        content = comp_rec.read_text(encoding="utf-8")
        content = content.replace('item:79103', 'item:83872').replace('priory:gw2Id 79103', 'priory:gw2Id 83872')
        comp_rec.write_text(content, encoding="utf-8")
        print("[+] Fixed: competitive_armor_and_eternity_recipes.ttl")

    # 10. gen3_legendary_recipes.ttl, gen3_aurene_weapons.ttl, gen3_dragon_variants.ttl
    gen3_rec = ONTOLOGY_DIR / "instances" / "recipes" / "gen3_legendary_recipes.ttl"
    if gen3_rec.exists():
        content = gen3_rec.read_text(encoding="utf-8")
        content = content.replace('item:96365', 'item:96330').replace('priory:gw2Id 96365', 'priory:gw2Id 96330') # Dragon's Wing
        content = content.replace('item:96519', 'item:96193').replace('priory:gw2Id 96519', 'priory:gw2Id 96193') # Dragon's Wisdom
        content = content.replace('item:96656', 'item:97691').replace('priory:gw2Id 96656', 'priory:gw2Id 97691') # Dragon's Scale
        content = content.replace('item:97086', 'item:96915').replace('priory:gw2Id 97086', 'priory:gw2Id 96915') # Dragon's Argument
        content = content.replace('item:96806', 'item:96993').replace('priory:gw2Id 96806', 'priory:gw2Id 96993') # Gift of Seitung Province
        content = content.replace('item:96805', 'item:95621').replace('priory:gw2Id 96805', 'priory:gw2Id 95621') # Gift of New Kaineng City (was Jade Fleet)
        gen3_rec.write_text(content, encoding="utf-8")
        print("[+] Fixed: gen3_legendary_recipes.ttl")

    aurene_file = ONTOLOGY_DIR / "instances" / "legendaries" / "gen3_aurene_weapons.ttl"
    if aurene_file.exists():
        content = aurene_file.read_text(encoding="utf-8")
        content = content.replace('item:96979', 'item:97102').replace('priory:gw2Id 96979', 'priory:gw2Id 97102') # Chunk of Pure Jade
        content = content.replace('item:96004', 'item:98707').replace('priory:gw2Id 96004', 'priory:gw2Id 98707') # Kralkatorrik's Insight Skin
        aurene_file.write_text(content, encoding="utf-8")
        print("[+] Fixed: gen3_aurene_weapons.ttl")

    variant_file = ONTOLOGY_DIR / "instances" / "legendaries" / "gen3_dragon_variants.ttl"
    if variant_file.exists():
        content = variant_file.read_text(encoding="utf-8")
        content = content.replace('item:96004', 'item:98707').replace('priory:gw2Id 96004', 'priory:gw2Id 98707')
        variant_file.write_text(content, encoding="utf-8")
        print("[+] Fixed: gen3_dragon_variants.ttl")

    # 11. gen2_legendary_recipes.ttl
    gen2_rec = ONTOLOGY_DIR / "instances" / "recipes" / "gen2_legendary_recipes.ttl"
    if gen2_rec.exists():
        content = gen2_rec.read_text(encoding="utf-8")
        # Eureka: Endeavor 79570, Shard 79445, Gift 79419
        content = content.replace('item:79803', 'item:79570').replace('priory:gw2Id 79803', 'priory:gw2Id 79570')
        content = content.replace('item:79804', 'item:79445').replace('priory:gw2Id 79804', 'priory:gw2Id 79445')
        # Shooshadoo: Friendship 79836, Shard 79784, Gift 79839
        content = content.replace('item:79561', 'item:79839').replace('priory:gw2Id 79561', 'priory:gw2Id 79839')
        content = content.replace('item:79564', 'item:79784').replace('priory:gw2Id 79564', 'priory:gw2Id 79784')
        # Sharur: Might of Arah 81634, Gift of Arah 81684, Shard of Arah 82069
        content = content.replace('item:82790', 'item:81684').replace('priory:gw2Id 82790', 'priory:gw2Id 81684') # Gift of Arah
        content = content.replace('item:82792', 'item:81634').replace('priory:gw2Id 82792', 'priory:gw2Id 81634') # Might of Arah
        content = content.replace('item:82793', 'item:82069').replace('priory:gw2Id 82793', 'priory:gw2Id 82069') # Shard of Arah
        # HMS Divinity: The Cure 89036, Gift of the Fleet 70797, Shard of Liturgy 81051
        content = content.replace('item:86302', 'item:70797').replace('priory:gw2Id 86302', 'priory:gw2Id 70797') # Gift of the Fleet
        content = content.replace('item:86304', 'item:89036').replace('priory:gw2Id 86304', 'priory:gw2Id 89036') # The Cure
        content = content.replace('item:86305', 'item:81051').replace('priory:gw2Id 86305', 'priory:gw2Id 81051') # Shard of Liturgy
        # Exordium: Exitare 90883, Gift of Exordium 90893, Shard of Exitare 90390
        content = content.replace('item:90550', 'item:90893').replace('priory:gw2Id 90550', 'priory:gw2Id 90893') # Gift of Exordium
        content = content.replace('item:90552', 'item:90883').replace('priory:gw2Id 90552', 'priory:gw2Id 90883') # Exitare
        # Verdarach: Call of the Void 87764, Shard 87711
        content = content.replace('item:91877', 'item:87764').replace('priory:gw2Id 91877', 'priory:gw2Id 87764') # Call of the Void
        # Shards
        content = content.replace('item:81745', 'item:81051').replace('priory:gw2Id 81745', 'priory:gw2Id 81051') # Shard of Liturgy
        content = content.replace('item:88957', 'item:88738').replace('priory:gw2Id 88957', 'priory:gw2Id 88738') # Shard of Tlehco
        content = content.replace('item:89856', 'item:81961').replace('priory:gw2Id 89856', 'priory:gw2Id 81961') # Shard of the Crown
        # Gifts
        content = content.replace('item:84088', 'item:85631').replace('priory:gw2Id 84088', 'priory:gw2Id 85631') # Gift of the Desert
        gen2_rec.write_text(content, encoding="utf-8")
        print("[+] Fixed: gen2_legendary_recipes.ttl")

    # 12. legendary_armor_recipes.ttl (remove fake Klobjarne Harvester)
    armor_rec = ONTOLOGY_DIR / "instances" / "recipes" / "legendary_armor_recipes.ttl"
    if armor_rec.exists():
        content = armor_rec.read_text(encoding="utf-8")
        # Remove item:103460, item:103427, recipe:forge_klobjarne_harvester, recipe:req_klobjarne_*
        content = re.sub(r'item:103427\s+a\s+owl:NamedIndividual[^\n]+\n\s+rdfs:label[^\n]+\n\s+priory:gw2Id\s+103427\s*\.\n*', '', content)
        content = re.sub(r'item:103460\s+a\s+owl:NamedIndividual[^\n]+\n[^\n]+\n[^\n]+\n[^\n]+\n\s+priory:gw2Id\s+103460[^\n]+\n[^\n]+\n[^\n]+\n\s+priory:producedBy\s+recipe:forge_klobjarne_harvester\s*\.\n*', '', content)
        content = re.sub(r'recipe:forge_klobjarne_harvester\s+a\s+priory:MysticForgeRecipe\s*;[^\.]+\.\n*', '', content)
        content = re.sub(r'recipe:req_klobjarne_\d+\s+a\s+priory:IngredientRequirement\s*;[^\.]+\.\n*', '', content)
        armor_rec.write_text(content, encoding="utf-8")
        print("[+] Fixed: legendary_armor_recipes.ttl")

    print("[+] All ground truth repairs executed successfully!")

if __name__ == "__main__":
    run_repairs()
