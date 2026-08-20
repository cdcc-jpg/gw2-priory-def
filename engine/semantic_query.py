"""Semantic Discovery & Concept Resolution Module for Project Priory.

Leverages W3C OWL and SKOS taxonomies to perform:
1. Taxonomic Subsumption Search (e.g., query by abstract parent categories like Two-Handed Weapons).
2. Polymorphic Acquisition Discovery (discovering all crafting, vendor, spatial waypoints, and reward track paths for any item).
3. Entity & Jargon Resolution (resolving chat codes, names, and aliases to canonical URIs).
4. Semantic Subgraph Context Extraction (providing grounded facts for LLM prompts).
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import rdflib
from rdflib import Literal, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery
from engine.graph_store import (
    PrioryGraphStore,
    PRIORY,
    PRIORY_REF,
    ITEM,
    RECIPE,
    CHARACTER,
    WEAPON,
    RARITY,
    DISCIPLINE,
    GAMEMODE,
    CURRENCY,
    ARMOR,
    SLOT,
    PROFESSION,
    RACE
)

SKOS = rdflib.SKOS
RDFS = rdflib.RDFS


class SemanticQueryService:
    """High-level semantic querying and conceptual discovery engine."""

    def __init__(self, graph_store: PrioryGraphStore):
        self.store = graph_store
        self.graph = graph_store.graph

    def find_items_by_taxonomy(
        self,
        broad_weapon_type: Optional[str] = None,
        rarity_tier: Optional[str] = None,
        discipline: Optional[str] = None,
        armor_weight: Optional[str] = None,
        equipment_slot: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Queries items using SKOS taxonomy hierarchies (taxonomic subsumption)."""
        filters = []
        if broad_weapon_type:
            filters.append(f"""
                ?item priory:hasWeaponType ?wt .
                FILTER (?wt = weapon:{broad_weapon_type} || EXISTS {{ ?wt skos:broader+ weapon:{broad_weapon_type} }})
            """)
        if rarity_tier:
            filters.append(f"""
                ?item priory:hasRarity ?r .
                FILTER (?r = rarity:{rarity_tier} || EXISTS {{ ?r skos:broader+ rarity:{rarity_tier} }})
            """)
        if discipline:
            filters.append(f"""
                ?item priory:producedBy ?recipe .
                ?recipe priory:requiresDiscipline discipline:{discipline} .
            """)
        if armor_weight:
            filters.append(f"""
                ?item priory:hasArmorWeight ?aw .
                FILTER (?aw = armor:{armor_weight} || EXISTS {{ ?aw skos:broader+ armor:{armor_weight} }})
            """)
        if equipment_slot:
            filters.append(f"""
                ?item priory:hasEquipmentSlot ?es .
                FILTER (?es = slot:{equipment_slot} || EXISTS {{ ?es skos:broader+ slot:{equipment_slot} }})
            """)

        filter_clause = "\n".join(filters)

        sparql = f"""
        SELECT DISTINCT ?item ?gw2Id ?label ?chatCode ?weaponType ?rarity ?armorWeight ?equipmentSlot WHERE {{
            ?item priory:gw2Id ?gw2Id ;
                  rdfs:label ?label .
            OPTIONAL {{ ?item priory:chatCode ?chatCode }}
            OPTIONAL {{ ?item priory:hasWeaponType ?weaponType }}
            OPTIONAL {{ ?item priory:hasArmorWeight ?armorWeight }}
            OPTIONAL {{ ?item priory:hasEquipmentSlot ?equipmentSlot }}
            OPTIONAL {{ ?item priory:hasRarity ?rarity }}
            {filter_clause}
        }}
        """
        return self.store.query(sparql)

    def discover_acquisition_paths(self, item_id: int) -> Dict[str, Any]:
        """Discovers all known acquisition methods and spatial waypoints for an item."""
        item_meta = self.store.get_item_by_id(item_id)
        if not item_meta:
            return {"error": f"Item with ID {item_id} not found in knowledge graph."}

        item_uri = URIRef(item_meta["item"])
        paths: Dict[str, List[Any]] = {
            "crafting_recipes": [],
            "vendor_exchanges": [],
            "reward_tracks": [],
            "achievement_collections": []
        }

        # 1. Discover Crafting Recipes
        craft_query = """
        SELECT ?recipe ?recipeLabel ?recipeType ?discipline ?rating ?outputQty WHERE {
            ?item priory:producedBy ?recipe .
            ?recipe a ?recipeType .
            OPTIONAL { ?recipe rdfs:label ?recipeLabel }
            OPTIONAL { ?recipe priory:outputQuantity ?outputQty }
            OPTIONAL { ?recipe priory:requiresDiscipline ?discipline }
            OPTIONAL { ?recipe priory:requiresRating ?rating }
            FILTER (?recipeType != owl:NamedIndividual)
        }
        """
        for r in self.store.query(craft_query, init_bindings={"item": item_uri}):
            rtype = str(r["recipeType"]).split("/")[-1].replace("priory:", "")
            recipe_info = {
                "recipe_uri": r["recipe"],
                "recipe_name": r.get("recipeLabel", "Unknown Recipe"),
                "recipe_type": rtype,
                "output_quantity": r.get("outputQty", 1),
                "discipline": str(r["discipline"]).split("/")[-1] if "discipline" in r else None,
                "required_rating": r.get("rating"),
                "ingredients": self.store.get_direct_recipe_ingredients(item_id)
            }
            paths["crafting_recipes"].append(recipe_info)

        # 2. Discover Vendor Exchanges & Alternative Sources with Spatial Navigation
        vendor_query = """
        SELECT ?path ?sourceType ?currency ?currencyLabel ?qty ?timeGateLabel ?gameModeLabel ?vendorNPC ?zoneName ?waypointName ?nearestWaypoint WHERE {
            { ?item priory:hasSubstituteSource ?path } UNION { ?item priory:acquiredVia ?path }
            ?path a ?sourceType .
            OPTIONAL {
                ?path priory:requiresCurrency ?currency .
                OPTIONAL { ?currency skos:prefLabel ?currencyLabel }
            }
            OPTIONAL { ?path priory:requiredQuantity ?qty }
            OPTIONAL { ?path priory:vendorNPC ?vendorNPC }
            OPTIONAL { ?path priory:zoneName ?zoneName }
            OPTIONAL { ?path priory:waypointName ?waypointName }
            OPTIONAL { ?path priory:nearestWaypoint ?nearestWaypoint }
            OPTIONAL {
                ?path priory:hasTimeGate ?tg .
                OPTIONAL { ?tg rdfs:label ?timeGateLabel }
            }
            OPTIONAL {
                ?path priory:hasGameMode ?gm .
                OPTIONAL { ?gm skos:prefLabel ?gameModeLabel }
            }
            FILTER (?sourceType != owl:NamedIndividual)
        }
        """
        for v in self.store.query(vendor_query, init_bindings={"item": item_uri}):
            stype = str(v["sourceType"]).split("/")[-1].replace("priory:", "")
            if "VendorExchange" in stype:
                curr_name = str(v.get("currency", "")).split("/")[-1]
                paths["vendor_exchanges"].append({
                    "currency": curr_name,
                    "currency_label": v.get("currencyLabel", curr_name),
                    "required_quantity": v.get("qty", 1),
                    "vendor_npc": v.get("vendorNPC"),
                    "zone_name": v.get("zoneName"),
                    "waypoint_name": v.get("waypointName"),
                    "nearest_waypoint": v.get("nearestWaypoint"),
                    "time_gate": v.get("timeGateLabel", None)
                })
            elif "RewardTrack" in stype:
                paths["reward_tracks"].append({
                    "game_mode": v.get("gameModeLabel", "WvW Reward Tracks")
                })
            elif "AchievementCollection" in stype:
                paths["achievement_collections"].append({
                    "description": "Achievement / Collection Journey"
                })

        return {
            "item_id": item_id,
            "item_name": item_meta["label"],
            "rarity": str(item_meta.get("rarity", "")).split("/")[-1],
            "chat_code": item_meta.get("chatCode"),
            "acquisition_paths": paths
        }

    def resolve_entity_by_text(self, search_text: str) -> List[Dict[str, Any]]:
        """Resolves freeform names, chat codes, or aliases to canonical item/concept URIs."""
        clean_search = search_text.strip().lower()

        # 1. Exact chat code match
        chat_query = """
        SELECT ?item ?gw2Id ?label ?chatCode WHERE {
            ?item priory:chatCode ?chatCode ;
                  priory:gw2Id ?gw2Id ;
                  rdfs:label ?label .
            FILTER (lcase(str(?chatCode)) = ?targetChat)
        }
        """
        res = self.store.query(chat_query, init_bindings={"targetChat": Literal(clean_search)})
        if res:
            return res

        # 2. Exact label & altLabel match (case-insensitive, with and without 'The ' prefix)
        exact_query = """
        SELECT DISTINCT ?item ?gw2Id ?label ?chatCode ?type WHERE {
            ?item priory:gw2Id ?gw2Id ;
                  rdfs:label ?label ;
                  a ?type .
            OPTIONAL { ?item priory:chatCode ?chatCode }
            OPTIONAL { ?item skos:altLabel ?alt }
            FILTER (
                lcase(str(?label)) = ?targetLabel || 
                lcase(str(?label)) = ?altLabel ||
                lcase(str(?alt)) = ?targetLabel ||
                lcase(str(?alt)) = ?altLabel
            )
            FILTER (?type != owl:NamedIndividual)
        } LIMIT 5
        """
        alt_label = f"the {clean_search}" if not clean_search.startswith("the ") else clean_search[4:]
        exact_res = self.store.query(exact_query, init_bindings={
            "targetLabel": Literal(clean_search),
            "altLabel": Literal(alt_label)
        })
        if exact_res:
            exact_res.sort(key=lambda x: (
                0 if any(k in str(x.get("type", "")) for k in ["LegendaryWeapon", "LegendaryArmor", "LegendaryTrinket", "LegendarySigil"]) else 1,
                len(x.get("label", ""))
            ))
            return exact_res

        # 3. Partial substring match on Items with gw2Id (checking both label and altLabel)
        item_query = """
        SELECT DISTINCT ?item ?gw2Id ?label ?chatCode ?type WHERE {
            ?item priory:gw2Id ?gw2Id ;
                  rdfs:label ?label ;
                  a ?type .
            OPTIONAL { ?item priory:chatCode ?chatCode }
            OPTIONAL { ?item skos:altLabel ?alt }
            FILTER (regex(str(?label), ?pattern, "i") || regex(str(?alt), ?pattern, "i"))
            FILTER (?type != owl:NamedIndividual)
        } LIMIT 15
        """
        items = self.store.query(item_query, init_bindings={"pattern": Literal(clean_search)})
        if items:
            items.sort(key=lambda x: (
                0 if any(k in str(x.get("type", "")) for k in ["LegendaryWeapon", "LegendaryArmor", "LegendaryTrinket", "LegendarySigil"]) else 1,
                len(x.get("label", ""))
            ))
            return items

        # 3b. Plural stemming fallback (e.g. "sigils" -> "sigil", "axes" -> "axe")
        stemmed = None
        if clean_search.endswith("ies"):
            stemmed = clean_search[:-3] + "y"
        elif clean_search.endswith("es"):
            stemmed = clean_search[:-2]
        elif clean_search.endswith("s"):
            stemmed = clean_search[:-1]

        if stemmed:
            stem_alt = f"the {stemmed}" if not stemmed.startswith("the ") else stemmed[4:]
            stem_res = self.store.query(exact_query, init_bindings={
                "targetLabel": Literal(stemmed),
                "altLabel": Literal(stem_alt)
            })
            if stem_res:
                return stem_res
            stem_items = self.store.query(item_query, init_bindings={"pattern": Literal(stemmed)})
            if stem_items:
                stem_items.sort(key=lambda x: (
                    0 if any(k in str(x.get("type", "")) for k in ["LegendaryWeapon", "LegendaryArmor", "LegendaryTrinket", "LegendarySigil"]) else 1,
                    len(x.get("label", ""))
                ))
                return stem_items

        # 4. Fallback to any entity with matching label
        label_query = """
        SELECT DISTINCT ?entity ?label ?type WHERE {
            ?entity rdfs:label ?label ;
                    a ?type .
            FILTER (regex(str(?label), ?pattern, "i"))
            FILTER (?type != owl:NamedIndividual)
        } LIMIT 10
        """
        return self.store.query(label_query, init_bindings={"pattern": Literal(clean_search)})

    def get_item_semantic_context_for_llm(self, item_id: int) -> str:
        """Extracts a self-describing, human-readable semantic summary graph for an LLM."""
        data = self.discover_acquisition_paths(item_id)
        if "error" in data:
            return f"Error: {data['error']}"

        lines = [
            f"### Semantic Entity: {data['item_name']} (GW2 ID: {data['item_id']})",
            f"* Rarity: {data['rarity']}",
            f"* Chat Code: {data['chat_code'] or 'N/A'}",
            "",
            "#### Direct Acquisition Pathways in Knowledge Graph:"
        ]

        if data["acquisition_paths"]["crafting_recipes"]:
            lines.append("- **Crafting Methods:**")
            for cr in data["acquisition_paths"]["crafting_recipes"]:
                disc_info = f" (Requires {cr['discipline']} {cr['required_rating']})" if cr['discipline'] else ""
                lines.append(f"  * Recipe: {cr['recipe_name']} [{cr['recipe_type']}]{disc_info}")
                for ing in cr["ingredients"]:
                    lines.append(f"    - Requires: {ing['quantity']}x {ing['ingredientLabel']} (ID: {ing['ingredientId']})")

        if data["acquisition_paths"]["vendor_exchanges"]:
            lines.append("- **Vendor Barter / Alternative Exchanges:**")
            for ve in data["acquisition_paths"]["vendor_exchanges"]:
                loc = f" [Location: {ve['vendor_npc']} at {ve['zone_name']} ({ve['waypoint_name']} {ve['nearest_waypoint']})]" if ve.get("nearest_waypoint") else ""
                tg = f" [Time Gate: {ve['time_gate']}]" if ve['time_gate'] else ""
                lines.append(f"  * Cost: {ve['required_quantity']}x {ve['currency_label']}{loc}{tg}")

        if data["acquisition_paths"]["reward_tracks"]:
            lines.append("- **Reward Track Sources:**")
            for rt in data["acquisition_paths"]["reward_tracks"]:
                lines.append(f"  * Mode: {rt['game_mode']}")

        return "\n".join(lines)

    def get_action_intent_vocabularies(self) -> Dict[str, Dict[str, Any]]:
        """Queries the graph dynamically for all acquisition path classes, their definitions, and altLabel synonyms."""
        sparql = """
        SELECT ?class ?label ?definition (GROUP_CONCAT(?alt; separator=", ") AS ?synonyms) WHERE {
            ?class rdfs:subClassOf* priory:AcquisitionPath ;
                   rdfs:label ?label .
            OPTIONAL { ?class skos:definition ?definition }
            OPTIONAL { ?class skos:altLabel ?alt }
        } GROUP BY ?class ?label ?definition
        """
        results = self.store.query(sparql)
        vocab = {}
        for r in results:
            class_name = r["class"].split("/")[-1].split("#")[-1]
            vocab[class_name] = {
                "label": r.get("label", class_name),
                "definition": r.get("definition", ""),
                "synonyms": [s.strip() for s in r.get("synonyms", "").split(",") if s.strip()]
            }
        return vocab

    # ==========================================================================
    # Ephemeral Character State Reasoning & Capability Queries
    # ==========================================================================

    def find_capable_crafting_characters(self, discipline: str, min_rating: int = 0) -> List[Dict[str, Any]]:
        """Queries which character(s) on the account satisfy a recipe's discipline and rating requirement."""
        clean_disc = discipline.strip().lower()
        sparql = """
        SELECT DISTINCT ?charUri ?charName ?charLevel ?profLabel ?discipline ?rating ?isActive WHERE {
            ?charUri a priory:Character ;
                     priory:characterName ?charName ;
                     priory:hasCraftingDiscipline ?cd .
            OPTIONAL { ?charUri priory:characterLevel ?charLevel }
            OPTIONAL { 
                ?charUri priory:hasProfession ?prof . 
                OPTIONAL { ?prof skos:prefLabel ?profLabel }
            }
            ?cd priory:discipline ?discipline ;
                priory:craftingRating ?rating .
            OPTIONAL { ?cd priory:isActive ?isActive }
            FILTER (?rating >= ?minRating)
            FILTER (LCASE(STRAFTER(STR(?discipline), "ref/discipline/")) = ?discLower || LCASE(STR(?discipline)) = ?discLower)
        } ORDER BY DESC(?isActive) DESC(?rating)
        """
        return self.store.query(sparql, init_bindings={"minRating": Literal(min_rating), "discLower": Literal(clean_disc)})

    def check_item_character_equipability(self, character_name: str, item_id: int) -> Dict[str, Any]:
        """Validates if a character can equip an item via SKOS weapon/armor taxonomies without hardcoding."""
        sparql = """
        SELECT DISTINCT ?charName ?profLabel ?itemLabel ?itemType ?armorWeight ?weaponType ?profArmor ?profWeapon WHERE {
            ?char a priory:Character ;
                  priory:characterName ?charName ;
                  priory:hasProfession ?prof .
            OPTIONAL { ?prof skos:prefLabel ?profLabel }
            ?item priory:gw2Id ?gw2Id ;
                  rdfs:label ?itemLabel .
            OPTIONAL { ?item a ?itemType . FILTER (?itemType != owl:NamedIndividual && ?itemType != priory:Item) }
            OPTIONAL { 
                { ?item priory:hasArmorWeight ?armorWeight }
                UNION { ?item a priory:HeavyArmor . BIND(armor:HeavyArmor AS ?armorWeight) }
                UNION { ?item a priory:MediumArmor . BIND(armor:MediumArmor AS ?armorWeight) }
                UNION { ?item a priory:LightArmor . BIND(armor:LightArmor AS ?armorWeight) }
            }
            OPTIONAL { ?item priory:hasWeaponType ?weaponType }
            OPTIONAL { 
                ?prof priory:usesArmorWeight ?profArmor .
                FILTER (?profArmor = ?armorWeight || EXISTS { ?armorWeight skos:broader+ ?profArmor } || EXISTS { ?armorWeight skos:exactMatch ?profArmor } || EXISTS { ?profArmor skos:exactMatch ?armorWeight })
            }
            OPTIONAL { 
                ?prof priory:canEquipWeaponType ?profWeapon .
                FILTER (?profWeapon = ?weaponType || EXISTS { ?weaponType skos:broader+ ?profWeapon } || EXISTS { ?weaponType skos:exactMatch ?profWeapon } || EXISTS { ?profWeapon skos:exactMatch ?weaponType })
            }
            FILTER (STR(?charName) = ?charNameStr)
        } LIMIT 1
        """
        res = self.store.query(sparql, init_bindings={"charNameStr": Literal(character_name), "gw2Id": Literal(item_id)})
        if not res:
            return {
                "character_name": character_name,
                "item_id": item_id,
                "can_equip": False,
                "reason": "Character or item not found in knowledge graph."
            }

        info = res[0]
        armor_wt = info.get("armorWeight")
        weapon_tp = info.get("weaponType")
        prof_armor = info.get("profArmor")
        prof_weapon = info.get("profWeapon")
        prof_name = info.get("profLabel", "Unknown Profession")
        item_name = info.get("itemLabel", f"Item {item_id}")

        if armor_wt:
            can_equip = bool(prof_armor)
            weight_name = str(armor_wt).split("/")[-1]
            reason = f"{prof_name} can wear {weight_name}" if can_equip else f"{prof_name} cannot wear {weight_name}"
        elif weapon_tp:
            can_equip = bool(prof_weapon)
            w_name = str(weapon_tp).split("/")[-1]
            reason = f"{prof_name} can wield {w_name}" if can_equip else f"{prof_name} cannot wield {w_name}"
        else:
            # Universal item (Trinket, Relic, Backpack, Upgrade)
            can_equip = True
            reason = f"Universal equipment equipable by {prof_name}"

        return {
            "character_name": character_name,
            "profession": prof_name,
            "item_id": item_id,
            "item_name": item_name,
            "can_equip": can_equip,
            "reason": reason
        }

    def find_character_item_locations(self, item_id: int) -> List[Dict[str, Any]]:
        """Queries which characters hold an item in their inventory bags and the exact slot."""
        sparql = """
        SELECT DISTINCT ?charName ?charLevel ?profLabel ?bagSlot ?slotIndex ?quantity WHERE {
            ?char a priory:Character ;
                  priory:characterName ?charName ;
                  priory:hasInventoryBag ?bag .
            OPTIONAL { ?char priory:characterLevel ?charLevel }
            OPTIONAL { ?char priory:hasProfession ?prof . ?prof skos:prefLabel ?profLabel }
            ?bag priory:inSlot ?bagSlot ;
                 priory:containsItem ?inv .
            ?inv priory:item ?item ;
                 priory:itemQuantity ?quantity .
            OPTIONAL { ?inv priory:slotIndex ?slotIndex }
            ?item priory:gw2Id ?gw2Id .
        } ORDER BY ?charName ?bagSlot ?slotIndex
        """
        results = self.store.query(sparql, init_bindings={"gw2Id": Literal(item_id)})
        locations = []
        for r in results:
            bag_name = str(r["bagSlot"]).split("/")[-1]
            locations.append({
                "character_name": r["charName"],
                "character_level": r.get("charLevel", 80),
                "profession": r.get("profLabel", "Unknown"),
                "bag_slot": bag_name,
                "slot_index": r.get("slotIndex", 0),
                "quantity": int(r.get("quantity", 1))
            })
        return locations

    def get_character_semantic_context(self, character_name: Optional[str] = None) -> str:
        """Serializes hydrated character knowledge into Markdown facts for LLM prompts sorted by playtime."""
        chars_query = """
        SELECT DISTINCT ?char ?charName ?charLevel ?profLabel ?raceLabel ?playtime ?created WHERE {
            ?char a priory:Character ;
                  priory:characterName ?charName ;
                  priory:hasProfession ?prof ;
                  priory:hasRace ?race .
            OPTIONAL { ?char priory:characterLevel ?charLevel }
            OPTIONAL { ?char priory:playtimeHours ?playtime }
            OPTIONAL { ?char priory:creationDate ?created }
            OPTIONAL { ?prof skos:prefLabel ?profLabel }
            OPTIONAL { ?race skos:prefLabel ?raceLabel }
        } ORDER BY DESC(?playtime)
        """
        chars = self.store.query(chars_query)
        if character_name:
            chars = [c for c in chars if str(c["charName"]).lower() == character_name.lower()]

        if not chars:
            return "No character profiles currently hydrated in knowledge graph."

        lines = ["### Account Character Profiles (Ephemeral Semantic Graph)"]
        for c in chars:
            c_uri = URIRef(c["char"])
            c_name = c["charName"]
            lvl = c.get("charLevel", 80)
            prof = c.get("profLabel", "Unknown Profession")
            race = c.get("raceLabel", "Unknown Race")
            pt = c.get("playtime")
            pt_str = f" | ⏱️ {pt} hours playtime" if pt is not None else ""
            lines.append(f"\n- **Character: {c_name}** (Level {lvl} {race} {prof}{pt_str})")

            # Crafting disciplines
            disc_query = """
            SELECT DISTINCT ?discipline ?rating ?isActive WHERE {
                ?char priory:hasCraftingDiscipline ?cd .
                ?cd priory:discipline ?discipline ;
                    priory:craftingRating ?rating .
                OPTIONAL { ?cd priory:isActive ?isActive }
            } ORDER BY DESC(?rating)
            """
            discs = self.store.query(disc_query, init_bindings={"char": c_uri})
            if discs:
                disc_strs = [
                    f"{str(d['discipline']).split('/')[-1]} {d['rating']}{' (Active)' if d.get('isActive') else ' (Inactive)'}"
                    for d in discs
                ]
                lines.append(f"  * **Crafting Disciplines:** {', '.join(disc_strs)}")

            # Equipped gear with stat combinations and upgrades
            gear_query = """
            SELECT DISTINCT ?slot ?itemLabel ?itemId ?statPrefix ?upgradeLabel WHERE {
                ?char priory:equippedItem ?eq .
                ?eq priory:inSlot ?slot ;
                    priory:item ?item .
                ?item priory:gw2Id ?itemId ;
                      rdfs:label ?itemLabel .
                OPTIONAL { ?eq priory:hasStatCombination ?stat . ?stat skos:prefLabel ?statPrefix }
                OPTIONAL { ?eq priory:slottedUpgrade ?upg . ?upg rdfs:label ?upgradeLabel }
            }
            """
            gear = self.store.query(gear_query, init_bindings={"char": c_uri})
            if gear:
                gear_items = []
                for g in gear[:8]:
                    prefix = f" [{g['statPrefix']}]" if g.get("statPrefix") else ""
                    upg = f" ({g['upgradeLabel']})" if g.get("upgradeLabel") else ""
                    gear_items.append(f"{str(g['slot']).split('/')[-1]}: {g['itemLabel']}{prefix}{upg}")
                lines.append(f"  * **Equipped Items:** {'; '.join(gear_items)}")

            # Active Build Specializations
            build_query = """
            SELECT DISTINCT ?tabIdx ?spec WHERE {
                ?char priory:hasBuildTab ?bt .
                ?bt priory:isActive true ;
                    priory:tabIndex ?tabIdx ;
                    priory:hasSpecializationSlot ?ss .
                ?ss priory:hasSpecialization ?spec .
            }
            """
            specs = self.store.query(build_query, init_bindings={"char": c_uri})
            if specs:
                spec_labels = [str(s["spec"]).split("/")[-1] for s in specs]
                lines.append(f"  * **Active Build Specializations:** {', '.join(spec_labels)}")

        return "\n".join(lines)

    def find_characters_by_specialization(self, spec_name: str) -> List[Dict[str, Any]]:
        """Finds all characters running a specific core or elite specialization in any build tab."""
        sparql = """
        SELECT DISTINCT ?charName ?charLevel ?profLabel ?tabIndex ?isActive WHERE {
            ?char a priory:Character ;
                  priory:characterName ?charName ;
                  priory:hasBuildTab ?bt .
            OPTIONAL { ?char priory:characterLevel ?charLevel }
            OPTIONAL { ?char priory:hasProfession ?prof . ?prof skos:prefLabel ?profLabel }
            ?bt priory:tabIndex ?tabIndex ;
                priory:hasSpecializationSlot ?ss .
            OPTIONAL { ?bt priory:isActive ?isActive }
            ?ss priory:hasSpecialization ?spec .
            FILTER (CONTAINS(LCASE(STR(?spec)), LCASE(?specQuery)))
        } ORDER BY ?charName ?tabIndex
        """
        return self.store.query(sparql, init_bindings={"specQuery": Literal(spec_name.lower())})

    def find_equipped_legendaries_across_characters(self) -> List[Dict[str, Any]]:
        """Locates all legendary items currently equipped on any character across the account."""
        sparql = """
        SELECT DISTINCT ?charName ?profLabel ?slotName ?itemLabel ?itemId WHERE {
            ?char a priory:Character ;
                  priory:characterName ?charName ;
                  priory:equippedItem ?eq .
            OPTIONAL { ?char priory:hasProfession ?prof . ?prof skos:prefLabel ?profLabel }
            ?eq priory:inSlot ?slot ;
                priory:item ?item .
            ?item a priory:LegendaryItem ;
                  priory:gw2Id ?itemId ;
                  rdfs:label ?itemLabel .
            BIND(STRAFTER(STR(?slot), "slot/") AS ?slotName)
        } ORDER BY ?charName ?slotName
        """
        return self.store.query(sparql)

    # ==========================================================================
    # MCP (Model Context Protocol) Tool Handlers
    # ==========================================================================

    def handle_mcp_character_crafting(self, discipline: str, min_rating: int = 0) -> Dict[str, Any]:
        """MCP Tool Handler: priory_character_crafting."""
        capable = self.find_capable_crafting_characters(discipline, min_rating)
        return {
            "requested_discipline": discipline,
            "min_rating": min_rating,
            "capable_character_count": len(capable),
            "capable_characters": [
                {
                    "character_name": c["charName"],
                    "character_level": c.get("charLevel", 80),
                    "profession": c.get("profLabel", "Unknown"),
                    "discipline": str(c["discipline"]).split("/")[-1],
                    "crafting_rating": c["rating"],
                    "is_active": c.get("isActive", True)
                }
                for c in capable
            ]
        }

    def handle_mcp_character_equipability(self, character_name: str, item_id: int) -> Dict[str, Any]:
        """MCP Tool Handler: priory_character_equipability."""
        return self.check_item_character_equipability(character_name, item_id)

    def handle_mcp_character_inventory(self, item_id: int) -> Dict[str, Any]:
        """MCP Tool Handler: priory_character_inventory."""
        locations = self.find_character_item_locations(item_id)
        total_held = sum(loc["quantity"] for loc in locations)
        return {
            "item_id": item_id,
            "total_quantity_in_character_bags": total_held,
            "holding_characters_count": len(set(loc["character_name"] for loc in locations)),
            "locations": locations
        }

    def handle_mcp_character_summary(self, character_name: Optional[str] = None) -> Dict[str, Any]:
        """MCP Tool Handler: priory_character_summary."""
        context = self.get_character_semantic_context(character_name)
        return {
            "character_name_filter": character_name,
            "semantic_markdown_profile": context
        }
