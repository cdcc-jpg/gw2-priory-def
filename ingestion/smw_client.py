"""GW2 Semantic MediaWiki (SMW) Ingestion Engine for Project Priory.

Implements query builders, parsers, and RDF graph generation across all 7 Acquisition Archetypes:
1. Crafting & Discipline Recipes (DisciplineRecipe)
2. Mystic Forge Recipes (MysticForgeRecipe)
3. Vendor Currency Exchanges (VendorExchangePath)
4. Spatial Locations, NPCs & Waypoints (Spatial Navigation)
5. Daily/Weekly Time Gates (TimeGate)
6. Achievement & Precursor Collections (AchievementCollectionPath)
7. WvW & PvP Reward Tracks (RewardTrackPath)
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
import httpx
import rdflib
from rdflib import URIRef, Literal, Namespace, RDF, RDFS, OWL, XSD

PRIORY = Namespace("https://priory.gw2/def/")
ITEM = Namespace("https://priory.gw2/id/item/")
RECIPE = Namespace("https://priory.gw2/id/recipe/")
DISCIPLINE = Namespace("https://priory.gw2/ref/discipline/")
RARITY = Namespace("https://priory.gw2/ref/rarity/")
CURRENCY = Namespace("https://priory.gw2/ref/currency/")
GAMEMODE = Namespace("https://priory.gw2/ref/gamemode/")
ARMOR = Namespace("https://priory.gw2/ref/armor/")
SLOT = Namespace("https://priory.gw2/ref/slot/")
ITEMTYPE = Namespace("https://priory.gw2/ref/itemtype/")
WEAPON = Namespace("https://priory.gw2/ref/weapon/")


class GW2SMWClient:
    """Complete client for querying the GW2 Semantic MediaWiki across all 7 acquisition archetypes."""

    WIKI_API_URL = "https://wiki.guildwars2.com/api.php"

    def __init__(self):
        self.headers = {"User-Agent": "PriorySemanticIngestion/1.0 (Project Priory Knowledge Layer)"}

    async def ask_query(self, query_str: str) -> Dict[str, Any]:
        """Executes an arbitrary Semantic MediaWiki #ask query via the official MediaWiki API."""
        params = {
            "action": "ask",
            "format": "json",
            "query": query_str
        }
        async with httpx.AsyncClient(headers=self.headers, timeout=20.0) as client:
            resp = await client.get(self.WIKI_API_URL, params=params)
            resp.raise_for_status()
            return resp.json()

    # =========================================================================
    # Bulk Archetype: All Legendary Items & Equipment
    # =========================================================================
    async def get_all_legendaries(self) -> List[Dict[str, Any]]:
        """Queries SMW for all Legendary weapons, armor pieces, trinkets, runes, and relics."""
        categories = [
            "Category:Legendary weapons",
            "Category:Legendary armor",
            "Category:Legendary trinkets",
            "Category:Legendary backpacks",
            "Category:Legendary upgrade components",
            "Category:Legendary relics"
        ]
        cat_filter = " OR ".join(f"[[{c}]]" for c in categories)
        ask_query = (
            f"{cat_filter}[[Has game id::+]]"
            "|?Has game id|?Has canonical name|?Has item type|?Has weapon type"
            "|?Has armor weight|?Has equipment slot|?Has chat link|limit=500"
        )
        res = await self.ask_query(ask_query)
        raw_res = res.get("query", {}).get("results", {})
        results_dict = raw_res if isinstance(raw_res, dict) else {}
        results = []

        def safe_first(arr, default=None):
            return arr[0] if (isinstance(arr, list) and len(arr) > 0) else default

        for page_name, page_data in results_dict.items():
            po = page_data.get("printouts", {})
            item_ids = po.get("Has game id", [])
            if not item_ids:
                continue

            item_id = safe_first(item_ids)
            clean_name = safe_first(po.get("Has canonical name"), page_name)
            if isinstance(clean_name, dict):
                clean_name = clean_name.get("fulltext", page_name)

            # Strip wiki disambiguation e.g. "Aurora (trinket)" -> "Aurora"
            display_name = re.sub(r"\s*\([^)]*\)", "", str(clean_name)).strip()

            item_type = safe_first(po.get("Has item type"), "Item")
            item_type_str = item_type.get("fulltext", str(item_type)) if isinstance(item_type, dict) else str(item_type)

            weapon_type = safe_first(po.get("Has weapon type"))
            weapon_type_str = weapon_type.get("fulltext", str(weapon_type)) if isinstance(weapon_type, dict) else (str(weapon_type) if weapon_type else None)

            armor_weight = safe_first(po.get("Has armor weight"))
            armor_weight_str = armor_weight.get("fulltext", str(armor_weight)) if isinstance(armor_weight, dict) else (str(armor_weight) if armor_weight else None)

            slot_type = safe_first(po.get("Has equipment slot"))
            slot_type_str = slot_type.get("fulltext", str(slot_type)) if isinstance(slot_type, dict) else (str(slot_type) if slot_type else None)

            chat = safe_first(po.get("Has chat link"))

            results.append({
                "page_name": page_name,
                "item_id": int(item_id),
                "label": display_name,
                "wiki_url": f"https://wiki.guildwars2.com/wiki/{page_name.replace(' ', '_')}",
                "item_type": item_type_str,
                "weapon_type": weapon_type_str,
                "armor_weight": armor_weight_str,
                "equipment_slot": slot_type_str,
                "chat_code": chat
            })
        return results

    # =========================================================================
    # Archetype 1: Crafting & Discipline Recipes
    # =========================================================================
    async def get_discipline_recipes(self, item_name: str) -> List[Dict[str, Any]]:
        """Queries SMW for discipline crafting recipes producing an item."""
        ask_query = (
            f"[[Has canonical name::{item_name}]][[Requires discipline::+]]"
            f"|?Has item id|?Requires discipline|?Requires discipline rating|?Has recipe ingredient|?Has ingredient count|?Has output quantity"
        )
        res = await self.ask_query(ask_query)
        results = []
        for page_name, page_data in res.get("query", {}).get("results", {}).items():
            po = page_data.get("printouts", {})
            ingredients = []
            ing_names = [i.get("fulltext", str(i)) if isinstance(i, dict) else str(i) for i in po.get("Has recipe ingredient", [])]
            ing_counts = po.get("Has ingredient count", [])
            for idx, name in enumerate(ing_names):
                qty = ing_counts[idx] if idx < len(ing_counts) else 1
                ingredients.append({"item_name": name, "quantity": qty})

            disc = po.get("Requires discipline", [{}])[0]
            disc_name = disc.get("fulltext", str(disc)) if isinstance(disc, dict) else str(disc)
            rating = po.get("Requires discipline rating", [0])[0] if po.get("Requires discipline rating") else 0

            results.append({
                "source_page": page_name,
                "output_item": item_name,
                "output_quantity": po.get("Has output quantity", [1])[0] if po.get("Has output quantity") else 1,
                "discipline": disc_name,
                "required_rating": rating,
                "ingredients": ingredients
            })
        return results

    # =========================================================================
    # Archetype 2: Mystic Forge Recipes
    # =========================================================================
    async def get_mystic_forge_recipes(self, item_name: str) -> List[Dict[str, Any]]:
        """Queries SMW for Mystic Forge combinations producing an item."""
        ask_query = f"[[Has canonical name::{item_name}]][[Has recipe source::Mystic forge]]|?Has ingredient|?Has output quantity"
        res = await self.ask_query(ask_query)
        results = []
        for page_name, page_data in res.get("query", {}).get("results", {}).items():
            po = page_data.get("printouts", {})
            ingredients = []
            for ing_record in po.get("Has ingredient", []):
                ing_item = ing_record.get("fulltext", str(ing_record)) if isinstance(ing_record, dict) else str(ing_record)
                ingredients.append(ing_item)

            results.append({
                "source_page": page_name,
                "output_item": item_name,
                "output_quantity": po.get("Has output quantity", [1])[0] if po.get("Has output quantity") else 1,
                "ingredients": ingredients
            })
        return results

    # =========================================================================
    # Archetype 3: Vendor Currency Exchanges & Barter Tables
    # =========================================================================
    async def get_vendor_exchanges(self, item_name: str) -> List[Dict[str, Any]]:
        """Queries SMW for vendor tables selling a target item for currencies."""
        ask_query = f"[[Category:Vendor tables]][[Sells item::{item_name}]]|?Has vendor|?Has cost currency|?Has cost amount|?Has time gate"
        res = await self.ask_query(ask_query)
        results = []
        for page_name, page_data in res.get("query", {}).get("results", {}).items():
            po = page_data.get("printouts", {})
            vendor = po.get("Has vendor", ["Unknown Vendor"])[0]
            vendor_str = vendor.get("fulltext", str(vendor)) if isinstance(vendor, dict) else str(vendor)
            curr = po.get("Has cost currency", ["Coin"])[0]
            curr_str = curr.get("fulltext", str(curr)) if isinstance(curr, dict) else str(curr)
            amount = po.get("Has cost amount", [1])[0] if po.get("Has cost amount") else 1
            tg = po.get("Has time gate", [None])[0]

            results.append({
                "source_page": page_name,
                "item_name": item_name,
                "vendor_name": vendor_str,
                "cost_currency": curr_str,
                "cost_amount": amount,
                "time_gate": tg
            })
        return results

    # =========================================================================
    # Archetype 4: Spatial Locations, NPCs & Waypoints
    # =========================================================================
    async def get_npc_location_and_waypoint(self, npc_name: str) -> Dict[str, Any]:
        """Queries SMW for an NPC's map zone, coordinate, and nearest in-game waypoint chat code."""
        ask_query = f"[[{npc_name}]]|?Located in|?Has nearest waypoint|?Has chat link"
        res = await self.ask_query(ask_query)
        results = res.get("query", {}).get("results", {})
        if npc_name in results:
            po = results[npc_name].get("printouts", {})
            zone = po.get("Located in", ["Tyria"])[0]
            zone_str = zone.get("fulltext", str(zone)) if isinstance(zone, dict) else str(zone)
            wp = po.get("Has nearest waypoint", [None])[0]
            wp_str = wp.get("fulltext", str(wp)) if isinstance(wp, dict) else str(wp)
            chat = po.get("Has chat link", [None])[0]
            return {
                "npc_name": npc_name,
                "zone_name": zone_str,
                "waypoint_name": wp_str,
                "waypoint_chat_code": chat
            }
        return {"npc_name": npc_name, "zone_name": None, "waypoint_name": None, "waypoint_chat_code": None}

    # =========================================================================
    # Archetype 5: Daily/Weekly Time Gates & Cooldowns
    # =========================================================================
    async def get_time_gated_items(self) -> List[Dict[str, Any]]:
        """Queries SMW for all items governed by daily or weekly server reset cooldowns."""
        ask_query = "[[Category:Time gated recipes]]|?Has item id|?Has daily limit|?Requires discipline"
        res = await self.ask_query(ask_query)
        results = []
        for page_name, page_data in res.get("query", {}).get("results", {}).items():
            po = page_data.get("printouts", {})
            item_id = po.get("Has item id", [None])[0]
            limit = po.get("Has daily limit", [1])[0] if po.get("Has daily limit") else 1
            results.append({
                "item_name": page_name,
                "item_id": item_id,
                "daily_limit": limit,
                "time_gate_type": "Daily Server Reset"
            })
        return results

    # =========================================================================
    # Archetype 6: Achievement & Precursor Collections
    # =========================================================================
    async def get_achievement_collection_steps(self, collection_name: str) -> Dict[str, Any]:
        """Queries SMW for multi-tier achievement collections and prerequisite steps."""
        ask_query = f"[[Category:Achievements]][[Has canonical name::{collection_name}]]|?Has tier objective|?Has collection item|?Has prerequisite"
        res = await self.ask_query(ask_query)
        results = res.get("query", {}).get("results", {})
        if collection_name in results:
            po = results[collection_name].get("printouts", {})
            objectives = [o.get("fulltext", str(o)) if isinstance(o, dict) else str(o) for o in po.get("Has tier objective", [])]
            items = [i.get("fulltext", str(i)) if isinstance(i, dict) else str(i) for i in po.get("Has collection item", [])]
            return {
                "collection_name": collection_name,
                "objectives": objectives,
                "required_items": items
            }
        return {"collection_name": collection_name, "objectives": [], "required_items": []}

    # =========================================================================
    # Archetype 7: WvW & PvP Reward Tracks
    # =========================================================================
    async def get_reward_tracks_for_item(self, item_name: str) -> List[Dict[str, Any]]:
        """Queries SMW for competitive reward tracks that grant a given item."""
        ask_query = f"[[Category:Reward tracks]][[Has reward item::{item_name}]]|?Has game mode|?Has track tier"
        res = await self.ask_query(ask_query)
        results = []
        for page_name, page_data in res.get("query", {}).get("results", {}).items():
            po = page_data.get("printouts", {})
            gm = po.get("Has game mode", ["WvW"])[0]
            gm_str = gm.get("fulltext", str(gm)) if isinstance(gm, dict) else str(gm)
            results.append({
                "track_name": page_name,
                "item_name": item_name,
                "game_mode": gm_str
            })
        return results

    # =========================================================================
    # RDF Graph Generator
    # =========================================================================
    def build_rdf_item_graph(
        self,
        item_id: int,
        item_name: str,
        rarity_str: str = "Legendary",
        chat_code: Optional[str] = None,
        weapon_type: Optional[str] = None,
        armor_weight: Optional[str] = None,
        equipment_slot: Optional[str] = None,
        item_type: Optional[str] = None,
        wiki_url: Optional[str] = None
    ) -> rdflib.Graph:
        """Generates a W3C OWL 2 DL compliant RDF graph individual for an item."""
        g = rdflib.Graph()
        g.bind("priory", PRIORY)
        g.bind("item", ITEM)
        g.bind("rarity", RARITY)
        g.bind("weapon", WEAPON)
        g.bind("armor", ARMOR)
        g.bind("slot", SLOT)
        g.bind("itemtype", ITEMTYPE)

        item_uri = ITEM[str(item_id)]

        # Determine appropriate OWL class
        if rarity_str.lower() == "legendary":
            if weapon_type:
                g.add((item_uri, RDF.type, PRIORY.LegendaryWeapon))
            elif armor_weight:
                g.add((item_uri, RDF.type, PRIORY.LegendaryArmor))
            elif equipment_slot in ["Amulet", "Ring", "Accessory"]:
                g.add((item_uri, RDF.type, PRIORY.LegendaryTrinket))
            elif equipment_slot == "Back":
                g.add((item_uri, RDF.type, PRIORY.LegendaryBackpack))
            elif item_type == "UpgradeComponent":
                g.add((item_uri, RDF.type, PRIORY.LegendarySigil))
            else:
                g.add((item_uri, RDF.type, PRIORY.LegendaryItem))
        else:
            g.add((item_uri, RDF.type, PRIORY.Item))

        g.add((item_uri, RDFS.label, Literal(item_name, lang="en")))
        g.add((item_uri, PRIORY.gw2Id, Literal(item_id, datatype=XSD.integer)))
        g.add((item_uri, PRIORY.hasRarity, RARITY[rarity_str.capitalize()]))
        g.add((item_uri, PRIORY.isAccountBound, Literal(True, datatype=XSD.boolean)))

        def to_pascal_case(s: str) -> str:
            return "".join(word.capitalize() for word in re.split(r"[\s_-]+", s.strip())) if s else ""

        if chat_code:
            g.add((item_uri, PRIORY.chatCode, Literal(chat_code)))
        if weapon_type:
            g.add((item_uri, PRIORY.hasWeaponType, WEAPON[to_pascal_case(weapon_type)]))
            # Determine generation for legendary weapons
            gen = None
            if item_name.startswith("Aurene") or item_name in ["Ancora Bellum", "Ancora Pax"]:
                gen = 3
            elif item_name in [
                "Astralaria", "HOPE", "Nevermore", "Chuka and Champawat", "HMS Divinity",
                "Eureka", "The Shining Blade", "Xiuquatl", "Claw of the Khan-Ur", "Exordium",
                "Pharus", "Verdarach", "The Binding of Ipos", "Sharur", "Shooshadoo"
            ]:
                gen = 2
            elif item_id < 40000 and rarity_str.lower() == "legendary":
                gen = 1

            if gen:
                g.add((item_uri, rdflib.SKOS.altLabel, Literal(f"Gen {gen} {weapon_type}", lang="en")))
                g.add((item_uri, rdflib.SKOS.altLabel, Literal(f"Generation {gen} {weapon_type}", lang="en")))
                g.add((item_uri, rdflib.SKOS.altLabel, Literal(f"Gen {gen} Legendary {weapon_type}", lang="en")))
                word_gen = {1: "One", 2: "Two", 3: "Three"}.get(gen, "")
                if word_gen:
                    g.add((item_uri, rdflib.SKOS.altLabel, Literal(f"Gen {word_gen} {weapon_type}", lang="en")))
                    g.add((item_uri, rdflib.SKOS.altLabel, Literal(f"Generation {word_gen} {weapon_type}", lang="en")))

        if armor_weight:
            w_str = to_pascal_case(armor_weight).replace("Armor", "")
            g.add((item_uri, PRIORY.hasArmorWeight, ARMOR[f"{w_str}Armor"]))
        if equipment_slot:
            g.add((item_uri, PRIORY.hasEquipmentSlot, SLOT[to_pascal_case(equipment_slot)]))
        if item_type:
            g.add((item_uri, PRIORY.hasItemType, ITEMTYPE[to_pascal_case(item_type)]))
        if wiki_url:
            g.add((item_uri, RDFS.seeAlso, URIRef(wiki_url)))

        return g
