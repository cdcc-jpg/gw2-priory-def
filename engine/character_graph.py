"""Ephemeral Character Graph Hydrator & Lifecycle Manager.

Transforms live Guild Wars 2 REST API `/v2/characters` JSON responses into
transient RDF Named Graphs (`<urn:priory:session:char:{name}>`) inside an in-memory
RDFLib Dataset with high performance (<2ms per character), per-character SHA-256
content diffing, and 120s TTL caching.
"""

from __future__ import annotations
import base64
import hashlib
import json
import time
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import rdflib
from rdflib import Dataset, Graph, Literal, Namespace, URIRef, BNode, RDF, XSD
from engine.graph_store import (
    PrioryGraphStore,
    PRIORY,
    CHARACTER,
    DISCIPLINE,
    PROFESSION,
    RACE,
    SLOT,
    ITEM
)

SESSION_GRAPH_PREFIX = "urn:priory:session:char:"

STAT_NAME_MAP = {
    "berserker": PRIORY.Berserker,
    "viper": PRIORY.Viper,
    "celestial": PRIORY.Celestial,
    "marauder": PRIORY.Marauder,
    "harrier": PRIORY.Harrier,
    "diviner": PRIORY.Diviner,
    "minstrel": PRIORY.Minstrel,
    "trailblazer": PRIORY.Trailblazer,
    "assassin": PRIORY.Assassin,
    "ritualist": PRIORY.Ritualist,
    "dragon": PRIORY.Dragon,
    "knight": PRIORY.Knight,
    "cavalier": PRIORY.Cavalier,
    "sinister": PRIORY.Sinister,
    "grieving": PRIORY.Grieving,
}


class CharacterGraphHydrator:
    """Hydrates and manages ephemeral named graphs for player characters with per-character diffing."""

    def __init__(self, graph_store: PrioryGraphStore, ttl_seconds: int = 120):
        self.store = graph_store
        self.dataset: Dataset = graph_store.dataset
        self.ttl_seconds = ttl_seconds
        # Tracks {graph_uri: {"timestamp": float, "char_name": str, "session_id": str, "content_hash": str}}
        self._hydrated_graphs: Dict[URIRef, Dict[str, Any]] = {}

    def get_character_graph_uri(self, character_name: str, session_id: Optional[str] = None) -> URIRef:
        """Constructs canonical named graph URI for a character."""
        clean_name = urllib.parse.quote(character_name.replace(" ", "_"))
        if session_id:
            return URIRef(f"urn:priory:session:{session_id}:char:{clean_name}")
        return URIRef(f"{SESSION_GRAPH_PREFIX}{clean_name}")

    def get_character_individual_uri(self, character_name: str) -> URIRef:
        """Constructs canonical individual URI for a character entity."""
        clean_name = urllib.parse.quote(character_name.replace(" ", "_"))
        return URIRef(f"https://priory.gw2/id/character/{clean_name}")

    def compute_character_hash(self, char_data: Dict[str, Any]) -> str:
        """Computes deterministic SHA-256 fingerprint of character JSON state."""
        try:
            serialized = json.dumps(char_data, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        except Exception:
            return str(hash(str(char_data)))

    def _hydrate_equipped_item(self, g: Graph, parent_uri: URIRef, eq: Dict[str, Any], predicate: URIRef) -> None:
        """Hydrates a single equipped item with stats, infusions, upgrades, and skin."""
        eq_id = eq.get("id")
        eq_slot = eq.get("slot")
        if not eq_id or not eq_slot:
            return

        eq_node = BNode()
        g.add((eq_node, RDF.type, PRIORY.EquippedItem))
        g.add((eq_node, PRIORY.inSlot, SLOT[eq_slot]))
        g.add((eq_node, PRIORY.item, ITEM[str(eq_id)]))

        # Slotted Upgrades (Runes, Sigils, Relics)
        for upg_id in eq.get("upgrades", []):
            if upg_id:
                g.add((eq_node, PRIORY.slottedUpgrade, ITEM[str(upg_id)]))

        # Slotted Infusions
        for inf_id in eq.get("infusions", []):
            if inf_id:
                g.add((eq_node, PRIORY.slottedInfusion, ITEM[str(inf_id)]))

        # Stat Combination Prefix
        stats_obj = eq.get("stats")
        if isinstance(stats_obj, dict):
            # Check attribute names
            stat_name = stats_obj.get("id")
            if stat_name and str(stat_name).lower() in STAT_NAME_MAP:
                g.add((eq_node, PRIORY.hasStatCombination, STAT_NAME_MAP[str(stat_name).lower()]))

        # Binding status & skin
        binding = eq.get("binding")
        if binding:
            g.add((eq_node, PRIORY.bindingStatus, Literal(binding, datatype=XSD.string)))
        skin = eq.get("skin")
        if skin:
            g.add((eq_node, PRIORY.itemSkinId, Literal(int(skin), datatype=XSD.integer)))

        g.add((parent_uri, predicate, eq_node))

    def hydrate_character(
        self,
        char_data: Dict[str, Any],
        session_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> URIRef:
        """Hydrates a single character JSON payload into a transient named graph with diff caching."""
        name = char_data.get("name", "UnknownCharacter")
        graph_uri = self.get_character_graph_uri(name, session_id=session_id)
        now = time.time()
        content_hash = self.compute_character_hash(char_data)

        # Check content hash & TTL diff cache: if unchanged, skip re-hydration entirely!
        if not force_refresh and graph_uri in self._hydrated_graphs:
            cached_meta = self._hydrated_graphs[graph_uri]
            if cached_meta.get("content_hash") == content_hash:
                if (now - cached_meta["timestamp"]) < self.ttl_seconds:
                    return graph_uri

        # If already exists in dataset, drop old graph before rehydrating
        existing_graph = self.dataset.graph(identifier=graph_uri)
        if len(existing_graph) > 0:
            self.dataset.remove_graph(existing_graph)

        # Create or get dedicated named graph
        g = self.dataset.graph(identifier=graph_uri)
        char_uri = self.get_character_individual_uri(name)

        # 1. Base Character Individual & Datatype Properties
        g.add((char_uri, RDF.type, PRIORY.Character))
        g.add((char_uri, PRIORY.characterName, Literal(name, datatype=XSD.string)))
        level = int(char_data.get("level", 80))
        g.add((char_uri, PRIORY.characterLevel, Literal(level, datatype=XSD.integer)))

        # Playtime & Creation Timestamp
        age_sec = char_data.get("age", 0)
        age_hours = age_sec // 3600
        g.add((char_uri, PRIORY.playtimeHours, Literal(age_hours, datatype=XSD.integer)))
        if char_data.get("created"):
            g.add((char_uri, PRIORY.creationDate, Literal(char_data["created"][:10], datatype=XSD.string)))

        # 2. Race & Profession SKOS Concept Links
        race_str = char_data.get("race")
        if race_str:
            g.add((char_uri, PRIORY.hasRace, RACE[race_str]))

        prof_str = char_data.get("profession")
        if prof_str:
            g.add((char_uri, PRIORY.hasProfession, PROFESSION[prof_str]))

        # 3. Combat Attributes
        attrs = char_data.get("attributes", {})
        if attrs:
            attr_node = BNode()
            g.add((attr_node, RDF.type, PRIORY.CharacterAttributes))
            for k, val in attrs.items():
                k_lower = k.lower()
                if k_lower == "power":
                    g.add((attr_node, PRIORY.power, Literal(int(val), datatype=XSD.integer)))
                elif k_lower == "precision":
                    g.add((attr_node, PRIORY.precision, Literal(int(val), datatype=XSD.integer)))
                elif k_lower == "toughness":
                    g.add((attr_node, PRIORY.toughness, Literal(int(val), datatype=XSD.integer)))
                elif k_lower == "vitality":
                    g.add((attr_node, PRIORY.vitality, Literal(int(val), datatype=XSD.integer)))
                elif k_lower == "armor":
                    g.add((attr_node, PRIORY.armorRating, Literal(int(val), datatype=XSD.integer)))
            g.add((char_uri, PRIORY.hasAttributes, attr_node))

        # 4. Crafting Disciplines (Active & Inactive Ratings)
        for disc in char_data.get("crafting", []):
            d_name = disc.get("discipline")
            if not d_name:
                continue
            d_node = BNode()
            g.add((d_node, RDF.type, PRIORY.CharacterDiscipline))
            g.add((d_node, PRIORY.discipline, DISCIPLINE[d_name]))
            g.add((d_node, PRIORY.craftingRating, Literal(int(disc.get("rating", 0)), datatype=XSD.integer)))
            g.add((d_node, PRIORY.isActive, Literal(bool(disc.get("active", True)), datatype=XSD.boolean)))
            g.add((char_uri, PRIORY.hasCraftingDiscipline, d_node))

        # 5. Equipment Tabs & Active Gear Loadout
        eq_tabs = char_data.get("equipment_tabs", [])
        if eq_tabs:
            for tab in eq_tabs:
                tab_node = BNode()
                g.add((tab_node, RDF.type, PRIORY.EquipmentTab))
                t_idx = int(tab.get("tab", 1))
                g.add((tab_node, PRIORY.tabIndex, Literal(t_idx, datatype=XSD.integer)))
                g.add((tab_node, PRIORY.isActive, Literal(bool(tab.get("is_active", False)), datatype=XSD.boolean)))
                if tab.get("name"):
                    g.add((tab_node, PRIORY.tabName, Literal(tab["name"], datatype=XSD.string)))
                for eq in tab.get("equipment", []):
                    self._hydrate_equipped_item(g, tab_node, eq, PRIORY.equippedItem)
                g.add((char_uri, PRIORY.hasEquipmentTab, tab_node))

        # Active Equipped Gear (Direct equipment list)
        for eq in char_data.get("equipment", []):
            self._hydrate_equipped_item(g, char_uri, eq, PRIORY.equippedItem)

        # 6. Build Tabs & Specializations
        build_tabs = char_data.get("build_tabs", [])
        for b_tab in build_tabs:
            bt_node = BNode()
            g.add((bt_node, RDF.type, PRIORY.BuildTab))
            bt_idx = int(b_tab.get("tab", 1))
            g.add((bt_node, PRIORY.tabIndex, Literal(bt_idx, datatype=XSD.integer)))
            g.add((bt_node, PRIORY.isActive, Literal(bool(b_tab.get("is_active", False)), datatype=XSD.boolean)))
            
            build_data = b_tab.get("build", {})
            if build_data:
                # Specializations (3 slots)
                for spec in build_data.get("specializations", []):
                    if spec and spec.get("id"):
                        spec_node = BNode()
                        g.add((spec_node, RDF.type, PRIORY.SpecializationSlot))
                        spec_id = spec.get("id")
                        g.add((spec_node, PRIORY.hasSpecialization, URIRef(f"https://priory.gw2/ref/specialization/{spec_id}")))
                        traits = spec.get("traits", [])
                        if len(traits) > 0 and traits[0]:
                            g.add((spec_node, PRIORY.selectedMajorTrait1, Literal(int(traits[0]), datatype=XSD.integer)))
                        if len(traits) > 1 and traits[1]:
                            g.add((spec_node, PRIORY.selectedMajorTrait2, Literal(int(traits[1]), datatype=XSD.integer)))
                        if len(traits) > 2 and traits[2]:
                            g.add((spec_node, PRIORY.selectedMajorTrait3, Literal(int(traits[2]), datatype=XSD.integer)))
                        g.add((bt_node, PRIORY.hasSpecializationSlot, spec_node))

                # Slotted Skills
                skills = build_data.get("skills", {})
                if skills.get("heal"):
                    g.add((bt_node, PRIORY.healSkillId, Literal(int(skills["heal"]), datatype=XSD.integer)))
                utilities = skills.get("utilities", [])
                if len(utilities) > 0 and utilities[0]:
                    g.add((bt_node, PRIORY.utility1SkillId, Literal(int(utilities[0]), datatype=XSD.integer)))
                if len(utilities) > 1 and utilities[1]:
                    g.add((bt_node, PRIORY.utility2SkillId, Literal(int(utilities[1]), datatype=XSD.integer)))
                if len(utilities) > 2 and utilities[2]:
                    g.add((bt_node, PRIORY.utility3SkillId, Literal(int(utilities[2]), datatype=XSD.integer)))
                if skills.get("elite"):
                    g.add((bt_node, PRIORY.eliteSkillId, Literal(int(skills["elite"]), datatype=XSD.integer)))

            g.add((char_uri, PRIORY.hasBuildTab, bt_node))

        # 7. Inventory Bags & Contained Item Stacks
        for b_idx, bag in enumerate(char_data.get("bags", [])):
            if not bag:
                continue
            bag_node = BNode()
            g.add((bag_node, RDF.type, PRIORY.InventoryBag))
            g.add((bag_node, PRIORY.inSlot, SLOT[f"Bag{b_idx}"]))
            g.add((char_uri, PRIORY.hasInventoryBag, bag_node))

            for s_idx, inv in enumerate(bag.get("inventory", [])):
                if not inv or not inv.get("id"):
                    continue
                inv_node = BNode()
                g.add((inv_node, RDF.type, PRIORY.InventoryItem))
                g.add((inv_node, PRIORY.item, ITEM[str(inv["id"])]))
                g.add((inv_node, PRIORY.itemQuantity, Literal(int(inv.get("count", 1)), datatype=XSD.integer)))
                g.add((inv_node, PRIORY.slotIndex, Literal(s_idx, datatype=XSD.integer)))
                if inv.get("binding"):
                    g.add((inv_node, PRIORY.bindingStatus, Literal(inv["binding"], datatype=XSD.string)))
                g.add((bag_node, PRIORY.containsItem, inv_node))

        # Record cache metadata
        self._hydrated_graphs[graph_uri] = {
            "timestamp": now,
            "char_name": name,
            "session_id": session_id,
            "content_hash": content_hash
        }

        return graph_uri

    def hydrate_characters(
        self,
        characters_data: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        force_refresh: bool = False
    ) -> List[URIRef]:
        """Batch hydrates multiple character JSON objects into the dataset with diff skipping."""
        return [
            self.hydrate_character(c, session_id=session_id, force_refresh=force_refresh)
            for c in characters_data
        ]

    def clear_session_characters(self, session_id: Optional[str] = None) -> int:
        """Drops ephemeral named graphs from the dataset for a specific session or all sessions."""
        dropped = 0
        to_remove = []

        for graph_uri, meta in list(self._hydrated_graphs.items()):
            if session_id is None or meta.get("session_id") == session_id:
                graph = self.dataset.graph(identifier=graph_uri)
                self.dataset.remove_graph(graph)
                to_remove.append(graph_uri)
                dropped += 1

        for g_uri in to_remove:
            del self._hydrated_graphs[g_uri]

        return dropped

    def get_all_hydrated_character_graphs(self) -> List[URIRef]:
        """Returns list of currently active ephemeral character graph URIs."""
        return list(self._hydrated_graphs.keys())

    def route_crafting_discipline(
        self,
        discipline: str,
        required_rating: int,
        account_state: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Maps crafting requirements to specific characters with active licenses, avoiding 50 silver fees."""
        return route_crafting_discipline(discipline, required_rating, account_state=account_state, graph_store=self.store)


# ==============================================================================
# Canonical Crafting Stations & Discipline Routing
# ==============================================================================

CRAFTING_DISCIPLINE_STATIONS: Dict[str, Dict[str, Any]] = {
    "weaponsmith": {
        "station_name": "Weaponsmithing Station",
        "vendor_npc": "Master Craftsman Hobbs",
        "chat_link": "[&BBAEAAA=]",  # Trader's Forum Waypoint, Lion's Arch
        "zone": "Lion's Arch",
        "alternate_waypoint": "[&BKgDAAA=]",  # Memorial Waypoint, Black Citadel
    },
    "armorsmith": {
        "station_name": "Armorsmithing Station",
        "vendor_npc": "Master Armorsmith",
        "chat_link": "[&BBAEAAA=]",
        "zone": "Lion's Arch",
        "alternate_waypoint": "[&BKgDAAA=]",
    },
    "artificer": {
        "station_name": "Artificing Station",
        "vendor_npc": "Master Artificer",
        "chat_link": "[&BBAEAAA=]",
        "zone": "Lion's Arch",
        "alternate_waypoint": "[&BLcEAAA=]",  # Accountancy Waypoint, Rata Sum
    },
    "huntsman": {
        "station_name": "Huntsman's Station",
        "vendor_npc": "Master Huntsman",
        "chat_link": "[&BBAEAAA=]",
        "zone": "Lion's Arch",
        "alternate_waypoint": "[&BCkDAAA=]",  # Minister's Waypoint, Divinity's Reach
    },
    "tailor": {
        "station_name": "Tailoring Station",
        "vendor_npc": "Master Tailor",
        "chat_link": "[&BBAEAAA=]",
        "zone": "Lion's Arch",
        "alternate_waypoint": "[&BLcEAAA=]",
    },
    "leatherworker": {
        "station_name": "Leatherworking Station",
        "vendor_npc": "Master Leatherworker",
        "chat_link": "[&BBAEAAA=]",
        "zone": "Lion's Arch",
        "alternate_waypoint": "[&BCkDAAA=]",
    },
    "jeweler": {
        "station_name": "Jeweler's Station",
        "vendor_npc": "Master Jeweler",
        "chat_link": "[&BBAEAAA=]",
        "zone": "Lion's Arch",
        "alternate_waypoint": "[&BLcEAAA=]",
    },
    "chef": {
        "station_name": "Cooking Station",
        "vendor_npc": "Master Chef",
        "chat_link": "[&BBAEAAA=]",
        "zone": "Lion's Arch",
        "alternate_waypoint": "[&BKgDAAA=]",
    },
    "mystic_forge": {
        "station_name": "Mystic Forge",
        "vendor_npc": "Miyani",
        "chat_link": "[&BBAEAAA=]",
        "zone": "Lion's Arch",
        "alternate_waypoint": "[&DYEFAAA=]",  # Mistlock Observatory Waypoint
    }
}


def encode_item_chat_link(item_id: int, quantity: int = 1) -> str:
    """Generates authentic in-game chat link [&...] for any Guild Wars 2 item ID."""
    b0 = 0x02  # Item header
    b1 = min(255, max(1, quantity))
    b2 = item_id & 0xFF
    b3 = (item_id >> 8) & 0xFF
    b4 = (item_id >> 16) & 0xFF
    b5 = 0x00  # Null terminator
    b64 = base64.b64encode(bytes([b0, b1, b2, b3, b4, b5])).decode("ascii")
    return f"[&{b64}]"


def route_crafting_discipline(
    discipline: str,
    required_rating: int,
    account_state: Optional[Any] = None,
    graph_store: Optional[Any] = None
) -> Dict[str, Any]:
    """Multi-character discipline routing: maps crafting requirements to specific characters
    with active licenses (e.g. Kerling for Weaponsmith, Legacy Of Harathi for Artificer),
    avoiding 50 silver reactivation fees.
    """
    disc_lower = discipline.strip().lower()
    station = CRAFTING_DISCIPLINE_STATIONS.get(disc_lower, {
        "station_name": f"{disc_lower.title()} Station",
        "vendor_npc": f"Master {disc_lower.title()}",
        "chat_link": "[&BBAEAAA=]",
        "zone": "Lion's Arch",
        "alternate_waypoint": "[&BBAEAAA=]"
    })

    active_candidates: List[Dict[str, Any]] = []
    inactive_candidates: List[Dict[str, Any]] = []
    underleveled_candidates: List[Dict[str, Any]] = []

    # 1. Check account_state data structures
    if account_state is not None:
        if hasattr(account_state, "character_disciplines") and account_state.character_disciplines:
            for char_name, discs in account_state.character_disciplines.items():
                if disc_lower in discs:
                    info = discs[disc_lower]
                    r = int(info.get("rating", 0))
                    act = bool(info.get("active", True))
                    cand = {"name": char_name, "rating": r, "active": act}
                    if act and r >= required_rating:
                        active_candidates.append(cand)
                    elif not act and r >= required_rating:
                        inactive_candidates.append(cand)
                    elif r < required_rating:
                        underleveled_candidates.append(cand)

        if not active_candidates and not inactive_candidates and hasattr(account_state, "characters") and account_state.characters:
            for c in account_state.characters:
                c_name = c.get("name", "")
                for cd in c.get("crafting", []):
                    if cd.get("discipline", "").lower() == disc_lower:
                        r = int(cd.get("rating", 0))
                        act = bool(cd.get("active", True))
                        cand = {"name": c_name, "rating": r, "active": act}
                        if act and r >= required_rating:
                            if cand not in active_candidates:
                                active_candidates.append(cand)
                        elif not act and r >= required_rating:
                            if cand not in inactive_candidates:
                                inactive_candidates.append(cand)
                        elif r < required_rating:
                            if cand not in underleveled_candidates:
                                underleveled_candidates.append(cand)

    # 2. Check graph_store (SPARQL across hydrated ephemeral character named graphs)
    if graph_store is not None and (not active_candidates and not inactive_candidates):
        sparql = """
        SELECT DISTINCT ?charName ?rating ?isActive WHERE {
            ?char a priory:Character ;
                  priory:characterName ?charName ;
                  priory:hasCraftingDiscipline ?cd .
            ?cd priory:discipline ?discipline ;
                priory:craftingRating ?rating .
            OPTIONAL { ?cd priory:isActive ?isActive }
            FILTER (LCASE(STRAFTER(STR(?discipline), "ref/discipline/")) = ?discLower || LCASE(STR(?discipline)) = ?discLower)
        } ORDER BY DESC(?isActive) DESC(?rating)
        """
        res = graph_store.query(sparql, init_bindings={"discLower": Literal(disc_lower)})
        for row in res:
            c_name = str(row["charName"])
            r = int(row.get("rating", 0))
            act = str(row.get("isActive", "true")).lower() == "true"
            cand = {"name": c_name, "rating": r, "active": act}
            if act and r >= required_rating:
                if cand not in active_candidates:
                    active_candidates.append(cand)
            elif not act and r >= required_rating:
                if cand not in inactive_candidates:
                    inactive_candidates.append(cand)
            elif r < required_rating:
                if cand not in underleveled_candidates:
                    underleveled_candidates.append(cand)

    # 3. Formulate character routing decision
    if active_candidates:
        active_candidates.sort(key=lambda x: x["rating"], reverse=True)
        best = active_candidates[0]
        return {
            "discipline": disc_lower,
            "character": best["name"],
            "action": "ASSIGNED_ACTIVE",
            "current_rating": best["rating"],
            "required_rating": required_rating,
            "is_active": True,
            "reactivation_fee_copper": 0,
            "reactivation_fee_silver": 0,
            "waypoint": station["chat_link"],
            "station_name": station["station_name"],
            "vendor_npc": station["vendor_npc"],
            "warning": None,
            "recommendation": (
                f"Craft on {best['name']} (Active {disc_lower.title()} rating {best['rating']} >= {required_rating}) "
                f"at {station['station_name']} {station['chat_link']} with 0 copper reactivation fee."
            )
        }

    if inactive_candidates:
        inactive_candidates.sort(key=lambda x: x["rating"], reverse=True)
        best = inactive_candidates[0]
        fee_copper = min(5000, best["rating"] * 10)
        fee_silver = fee_copper // 100
        warning_msg = (
            f"⚠️ Inactive license on {best['name']} would incur a 50 silver reactivation fee "
            f"({fee_silver} silver / {fee_copper} copper) to swap back to active."
        )
        return {
            "discipline": disc_lower,
            "character": best["name"],
            "action": "ACTIVATE",
            "current_rating": best["rating"],
            "required_rating": required_rating,
            "is_active": False,
            "reactivation_fee_copper": fee_copper,
            "reactivation_fee_silver": fee_silver,
            "waypoint": station["chat_link"],
            "station_name": station["station_name"],
            "vendor_npc": station["vendor_npc"],
            "warning": warning_msg,
            "recommendation": (
                f"Activate inactive {disc_lower.title()} (rating {best['rating']}) on {best['name']} "
                f"at {station['station_name']} {station['chat_link']}. {warning_msg}"
            )
        }

    if underleveled_candidates:
        underleveled_candidates.sort(key=lambda x: x["rating"], reverse=True)
        best = underleveled_candidates[0]
        return {
            "discipline": disc_lower,
            "character": best["name"],
            "action": "LEVEL_UP",
            "current_rating": best["rating"],
            "required_rating": required_rating,
            "is_active": best["active"],
            "reactivation_fee_copper": 0 if best["active"] else min(5000, best["rating"] * 10),
            "reactivation_fee_silver": 0 if best["active"] else min(5000, best["rating"] * 10) // 100,
            "waypoint": station["chat_link"],
            "station_name": station["station_name"],
            "vendor_npc": station["vendor_npc"],
            "warning": None if best["active"] else f"⚠️ Inactive license on {best['name']} will incur reactivation fee.",
            "recommendation": f"Level up {disc_lower.title()} on {best['name']} from {best['rating']} to {required_rating} at {station['station_name']} {station['chat_link']}."
        }

    # Fallback to account.disciplines summary if characters list empty
    cur_r = 0
    if account_state is not None and hasattr(account_state, "disciplines"):
        cur_r = account_state.disciplines.get(disc_lower, 0)
    action = "LEVEL_UP" if cur_r > 0 else "TRAIN"
    return {
        "discipline": disc_lower,
        "character": None,
        "action": action,
        "current_rating": cur_r,
        "required_rating": required_rating,
        "is_active": False,
        "reactivation_fee_copper": 0,
        "reactivation_fee_silver": 0,
        "waypoint": station["chat_link"],
        "station_name": station["station_name"],
        "vendor_npc": station["vendor_npc"],
        "warning": None,
        "recommendation": f"{action.replace('_', ' ').title()} {disc_lower.title()} to rating {required_rating} at {station['station_name']} {station['chat_link']}."
    }


