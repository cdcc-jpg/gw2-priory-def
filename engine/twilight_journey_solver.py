"""Comprehensive Multi-Criteria Twilight Legendary Acquisition Solver.

Calculates the complete experiential journey, mount-aware map completion routes,
precursor triage optimization, T6 material vectors, and session itineraries
for crafting the Gen 1 Legendary Greatsword, Twilight (Item ID: 30704).

ZERO DOMAIN SEMANTICS IN PYTHON: All domain definitions, waypoint codes, NPC names,
and acquisition pathways are dynamically queried from RDF semantic artifacts.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from rdflib import Literal, URIRef
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState, AccountDiffReport


class JourneyAction(BaseModel):
    """A concrete, actionable step the player should take during their gaming session."""
    action_title: str
    action_description: str
    estimated_minutes: int
    priority: str = "HIGH"  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    zone_name: Optional[str] = None
    waypoint: Optional[str] = None
    npc_name: Optional[str] = None
    requires_expansion: Optional[str] = None
    recommended_mount: Optional[str] = None
    game_mode: Optional[str] = "OpenWorld"  # "OpenWorld", "WvW", "Dungeon", "Crafting", "Account"
    assigned_character: Optional[str] = None


class JourneyPillar(BaseModel):
    """One of the 4 core pillars of the Twilight legendary journey."""
    pillar_name: str
    readiness_pct: float
    status: str  # "COMPLETED", "IN_PROGRESS", "NOT_STARTED"
    key_blockers: List[str] = Field(default_factory=list)
    recommended_actions: List[JourneyAction] = Field(default_factory=list)
    sub_components: Dict[str, float] = Field(default_factory=dict)


class PrecursorStrategy(BaseModel):
    """Evaluation of a specific Dusk precursor acquisition strategy."""
    strategy_name: str
    estimated_gold_cost: float
    estimated_hours: float
    pros: List[str] = Field(default_factory=list)
    cons: List[str] = Field(default_factory=list)
    is_recommended: bool = False
    requires_expansion: Optional[str] = None
    vendor_npc: Optional[str] = None
    waypoint: Optional[str] = None


class JourneyChapter(BaseModel):
    """A chapter in the master 4-chapter sequence."""
    chapter_number: int
    chapter_title: str
    chapter_summary: str
    actions: List[JourneyAction] = Field(default_factory=list)
    completion_status: str
    readiness_pct: float


class ExplorationPlan(BaseModel):
    """Region-by-region Core Tyria map completion plan."""
    region_name: str
    zone_count: int
    estimated_hours: float
    difficulty: str
    recommended_mount: Optional[str] = None
    strategy_notes: str
    starting_waypoint: Optional[str] = None


PlaySessionStep = JourneyAction

_DEFAULT_STORE_FALLBACK: Optional[PrioryGraphStore] = None


def _get_or_init_default_store() -> PrioryGraphStore:
    """Returns the shared default PrioryGraphStore instance, loading ontology triples if needed."""
    global _DEFAULT_STORE_FALLBACK
    try:
        from engine import graph_store as _gs_mod
        if hasattr(_gs_mod, "get_default_graph_store"):
            return _gs_mod.get_default_graph_store()
    except Exception:
        pass
    if _DEFAULT_STORE_FALLBACK is None:
        _DEFAULT_STORE_FALLBACK = PrioryGraphStore()
        _DEFAULT_STORE_FALLBACK.load_all()
    elif len(_DEFAULT_STORE_FALLBACK.graph) == 0:
        _DEFAULT_STORE_FALLBACK.load_all()
    return _DEFAULT_STORE_FALLBACK


class TwilightJourneyPlan(BaseModel):
    """Complete multi-dimensional Legendary acquisition plan and master roadmap."""
    target_item_id: int = 0
    target_item_name: str = "Twilight"
    generation: str = "GEN1"
    precursor_id: Optional[int] = None
    precursor_name: str = "Dusk"
    tribute_gift_id: Optional[int] = None
    tribute_gift_name: str = "Gift of Fortune"
    mastery_gift_id: Optional[int] = None
    mastery_gift_name: str = "Gift of Mastery"
    specific_gift_id: Optional[int] = None
    specific_gift_name: str = "Gift of Twilight"
    required_clovers: int = 77
    required_t6_per_type: int = 250
    required_t6_total: int = 2000
    overall_readiness_pct: float
    estimated_total_gold: float
    estimated_total_hours: float
    estimated_calendar_days: int
    pillars: List[JourneyPillar]
    precursor_strategies: List[PrecursorStrategy]
    exploration_plan: List[ExplorationPlan]
    chapters: List[JourneyChapter] = Field(default_factory=list)
    session_itinerary: List[JourneyAction] = Field(default_factory=list)
    steps: List[JourneyAction] = Field(default_factory=list)
    time_gates: List[Dict[str, Any]] = Field(default_factory=list)
    expansion_warnings: List[str] = Field(default_factory=list)
    cross_weapon_synergies: List[str] = Field(default_factory=list)
    recommended_character: Optional[str] = None


LegendaryJourneyPlan = TwilightJourneyPlan


class TwilightJourneySolver:
    """Multi-criteria ontology-driven graph solver for Legendary Weapon acquisition (Gen 1, Gen 2, Gen 3)."""

    def __init__(
        self,
        graph_store: Optional[PrioryGraphStore] = None,
        diff_engine: Optional[Any] = None,
        path_solver: Optional[Any] = None
    ):
        if graph_store is None:
            self.store = _get_or_init_default_store()
        else:
            self.store = graph_store
            if not getattr(self.store, "_loaded", False) and len(self.store.graph) == 0:
                self.store.load_all()
        if diff_engine is not None:
            self.diff_engine = diff_engine
        else:
            from engine.account_diff import AccountDiffEngine
            self.diff_engine = AccountDiffEngine(self.store) if self.store else None
        self.path_solver = path_solver
        self._booster_catalog_cache: Optional[Dict[int, Dict[str, Any]]] = None
        self._ontology_entities_cache: Optional[Dict[str, Any]] = None
        self._ontology_characters_cache: Optional[List[str]] = None

    def _resolve_ontology_entities(self) -> Dict[str, Any]:
        """Dynamically resolves core item IDs, T6 material IDs, and pillar gifts from the RDF graph."""
        if self._ontology_entities_cache is not None:
            return self._ontology_entities_cache
        if self.store is not None and getattr(self.store, "_solver_ontology_entities_cache", None) is not None:
            self._ontology_entities_cache = getattr(self.store, "_solver_ontology_entities_cache")
            return self._ontology_entities_cache

        store = self.store or _get_or_init_default_store()
        label_to_id: Dict[str, int] = {}
        label_rank: Dict[str, Tuple[bool, bool]] = {}
        label_to_ids: Dict[str, List[int]] = {}
        t6_ids: Set[int] = set()
        dungeon_gift_ids: Set[int] = set()
        starter_kit_ids: Set[int] = set()

        q_items = """
        SELECT ?id ?label ?cat ?hasPrimary ?isSingleLabel ?isDungeonGift ?isStarterKit WHERE {
            ?item priory:gw2Id ?id .
            OPTIONAL { ?item rdfs:label ?label }
            OPTIONAL { ?item priory:trophyCategory ?cat }
            BIND(EXISTS { { ?item priory:producedBy ?r } UNION { ?item priory:acquiredVia ?p } } AS ?hasPrimary)
            BIND(NOT EXISTS { ?item rdfs:label ?otherLabel . FILTER(STR(?otherLabel) != STR(?label)) } AS ?isSingleLabel)
            BIND(EXISTS {
                ?item priory:acquiredVia ?dgPath .
                ?dgPath priory:requiresCurrency ?dgCurr .
                FILTER(CONTAINS(STR(?dgCurr), "69") || CONTAINS(STR(?dgCurr), "TalesOfDungeonDelving"))
            } AS ?isDungeonGift)
            BIND(EXISTS { ?item a priory:LegendaryStarterKit } AS ?isStarterKit)
        }
        """
        for r in store.query(q_items):
            if r.get("id") is None:
                continue
            iid = int(r["id"])
            if r.get("cat"):
                t6_ids.add(iid)
            if r.get("isDungeonGift"):
                dungeon_gift_ids.add(iid)
            if r.get("isStarterKit"):
                starter_kit_ids.add(iid)
            lbl = str(r["label"]).strip() if r.get("label") else ""
            if not lbl:
                continue
            rank = (bool(r.get("hasPrimary")), bool(r.get("isSingleLabel")))
            ids_for_lbl = label_to_ids.setdefault(lbl, [])
            if iid not in ids_for_lbl:
                ids_for_lbl.append(iid)
            if lbl not in label_to_id or rank > label_rank.get(lbl, (False, False)):
                label_to_id[lbl] = iid
                label_rank[lbl] = rank

        if not t6_ids and hasattr(store, "get_t6_material_promotions"):
            try:
                t6_ids.update(int(k) for k in store.get_t6_material_promotions().keys())
            except Exception:
                pass

        result = {
            "label_to_id": label_to_id,
            "label_to_ids": label_to_ids,
            "t6_material_ids": sorted(t6_ids),
            "legacy_t6_material_ids": sorted(t6_ids),
            "dungeon_gift_ids": sorted(dungeon_gift_ids),
            "starter_kit_ids": sorted(starter_kit_ids),
        }
        self._ontology_entities_cache = result
        if self.store is not None:
            setattr(self.store, "_solver_ontology_entities_cache", result)
        return result

    def _resolve_item_id(self, label: str, fallback: int = 0) -> int:
        """Resolves a canonical GW2 item ID by its rdfs:label from the ontology."""
        entities = self._resolve_ontology_entities()
        return entities["label_to_id"].get(label, fallback)

    def _resolve_item_ids(self, label: str) -> List[int]:
        """Returns all GW2 item IDs matching the given rdfs:label in the ontology."""
        entities = self._resolve_ontology_entities()
        return list(entities["label_to_ids"].get(label, []))

    def _get_ontology_characters(self) -> List[str]:
        """Queries default character roster / hydrated priory:Character entities from the ontology."""
        if self._ontology_characters_cache is not None:
            return self._ontology_characters_cache
        store = self.store or _get_or_init_default_store()
        q_chars = """
        SELECT DISTINCT ?name ?order WHERE {
            { ?char a priory:DefaultRosterMember }
            UNION
            { ?char a priory:Character }
            ?char priory:characterName ?name .
            OPTIONAL { ?char priory:rosterOrder ?order }
        }
        """
        rows = store.query(q_chars)
        sorted_rows = sorted(
            rows,
            key=lambda r: (int(r["order"]) if r.get("order") is not None else 999, str(r.get("name", ""))),
        )
        names: List[str] = []
        for r in sorted_rows:
            nm = str(r.get("name", "")).strip()
            if nm and nm not in names:
                names.append(nm)
        self._ontology_characters_cache = names
        return names

    @property
    def TWILIGHT_ID(self) -> int:
        return self._resolve_item_id("Twilight")

    @property
    def DUSK_ID(self) -> int:
        return self._resolve_item_id("Dusk")

    @property
    def GIFT_OF_MASTERY_ID(self) -> int:
        return self._resolve_item_id("Gift of Mastery")

    @property
    def GIFT_OF_FORTUNE_ID(self) -> int:
        return self._resolve_item_id("Gift of Fortune")

    @property
    def GIFT_OF_TWILIGHT_ID(self) -> int:
        return self._resolve_item_id("Gift of Twilight")

    @property
    def GIFT_OF_EXPLORATION_ID(self) -> int:
        return self._resolve_item_id("Gift of Exploration")

    @property
    def GIFT_OF_BATTLE_ID(self) -> int:
        return self._resolve_item_id("Gift of Battle")

    @property
    def OBSIDIAN_SHARD_ID(self) -> int:
        return self._resolve_item_id("Obsidian Shard")

    @property
    def BLOODSTONE_SHARD_ID(self) -> int:
        return self._resolve_item_id("Bloodstone Shard")

    @property
    def MYSTIC_CLOVER_ID(self) -> int:
        return self._resolve_item_id("Mystic Clover")

    @property
    def GLOB_OF_ECTOPLASM_ID(self) -> int:
        return self._resolve_item_id("Glob of Ectoplasm")

    @property
    def ICY_RUNESTONE_ID(self) -> int:
        return self._resolve_item_id("Icy Runestone")

    @property
    def ONYX_LODESTONE_ID(self) -> int:
        return self._resolve_item_id("Onyx Lodestone")

    @property
    def ONYX_CORE_ID(self) -> int:
        return self._resolve_item_id("Onyx Core")

    @property
    def SUPERIOR_SIGIL_OF_STRENGTH_ID(self) -> int:
        return self._resolve_item_id("Superior Sigil of Strength")

    @property
    def SUPERIOR_SIGIL_OF_FORCE_ID(self) -> int:
        return self._resolve_item_id("Superior Sigil of Force") or self._resolve_item_id("Superior Sigil of Strength")

    @property
    def PHILOSOPHERS_STONE_ID(self) -> int:
        return self._resolve_item_id("Philosopher's Stone")

    @property
    def CURED_HARDENED_LEATHER_SQUARE_ID(self) -> int:
        return self._resolve_item_id("Cured Hardened Leather Square")

    @property
    def GIFT_OF_ASCALON_ID(self) -> int:
        return self._resolve_item_id("Gift of Ascalon")

    @property
    def GIFT_OF_METAL_ID(self) -> int:
        return self._resolve_item_id("Gift of Metal")

    @property
    def GIFT_OF_DARKNESS_ID(self) -> int:
        return self._resolve_item_id("Gift of Darkness")

    @property
    def T6_MATERIAL_IDS(self) -> List[int]:
        return list(self._resolve_ontology_entities()["t6_material_ids"])

    @property
    def LEGACY_T6_MATERIAL_IDS(self) -> List[int]:
        return list(self._resolve_ontology_entities()["legacy_t6_material_ids"])

    def _get_booster_catalog(self) -> Dict[int, Dict[str, Any]]:
        """Dynamically resolves booster, gobbler, and tome metadata from the RDF ontology."""
        if self._booster_catalog_cache is not None:
            return self._booster_catalog_cache

        catalog: Dict[int, Dict[str, Any]] = {}

        if self.store and hasattr(self.store, "get_booster_catalog"):
            try:
                store_cat = self.store.get_booster_catalog()
                if isinstance(store_cat, dict):
                    for k, v in store_cat.items():
                        catalog[int(k)] = dict(v)
            except Exception:
                pass

        if self.store:
            q_boosters = """
            SELECT ?id ?label ?altLabel ?type ?effect ?bonus WHERE {
                ?item priory:gw2Id ?id .
                {
                    ?item a ?targetClass .
                    FILTER(?targetClass IN (
                        priory:ExperienceBooster,
                        priory:HeroicBooster,
                        priory:KarmaBooster,
                        priory:WXPBooster,
                        priory:ItemBooster,
                        priory:CelebrationBooster,
                        priory:FestivalGobbler,
                        priory:TomeOfKnowledge
                    ))
                }
                UNION
                { ?item priory:buffEffect ?effect }
                UNION
                { ?item priory:wvwRewardTrackBonusPercent ?bonus }
                OPTIONAL { ?item rdfs:label ?label }
                OPTIONAL { ?item skos:altLabel ?altLabel }
                OPTIONAL { ?item a ?type }
                OPTIONAL { ?item priory:buffEffect ?effect }
                OPTIONAL { ?item priory:wvwRewardTrackBonusPercent ?bonus }
            }
            """
            grouped: Dict[int, Dict[str, Any]] = {}
            for r in self.store.query(q_boosters):
                if r.get("id") is None:
                    continue
                iid = int(r["id"])
                entry = grouped.setdefault(iid, {
                    "labels": [],
                    "alt_labels": [],
                    "types": set(),
                    "effects": [],
                    "bonus": 0,
                })
                if r.get("label") and str(r["label"]) not in entry["labels"]:
                    entry["labels"].append(str(r["label"]))
                if r.get("altLabel") and str(r["altLabel"]) not in entry["alt_labels"]:
                    entry["alt_labels"].append(str(r["altLabel"]))
                if r.get("type"):
                    entry["types"].add(str(r["type"]))
                if r.get("effect") and str(r["effect"]) not in entry["effects"]:
                    entry["effects"].append(str(r["effect"]))
                if r.get("bonus") is not None:
                    try:
                        entry["bonus"] = max(entry["bonus"], int(r["bonus"]))
                    except (ValueError, TypeError):
                        pass

            for iid, data in grouped.items():
                types_str = " ".join(data["types"])
                all_labels = data["labels"] + data["alt_labels"]
                all_labels_low = " ".join(all_labels).lower()

                if "FestivalGobbler" in types_str or "gobbler" in all_labels_low:
                    category = "gobbler"
                elif "TomeOfKnowledge" in types_str or "tome of knowledge" in all_labels_low or "writ of experience" in all_labels_low:
                    category = "tome"
                else:
                    category = "booster"

                chosen_label = ""
                if category == "gobbler":
                    for lbl in all_labels:
                        if "gobbler" in lbl.lower():
                            chosen_label = lbl
                            break
                if not chosen_label:
                    for lbl in data["labels"]:
                        if not lbl.startswith("Item "):
                            chosen_label = lbl
                            break
                if not chosen_label and all_labels:
                    chosen_label = all_labels[0]
                if not chosen_label:
                    chosen_label = catalog.get(iid, {}).get("label", f"Booster {iid}")

                catalog[iid] = {
                    "id": iid,
                    "label": chosen_label,
                    "category": category,
                    "types": sorted(data["types"]),
                    "buff_effect": data["effects"][0] if data["effects"] else catalog.get(iid, {}).get("buff_effect", ""),
                    "wvw_bonus_pct": data["bonus"] or catalog.get(iid, {}).get("wvw_bonus_pct", 0),
                }

        self._booster_catalog_cache = catalog
        return catalog

    def _introspect_weapon_bom(
        self,
        target_item_id: int,
        diff_report: AccountDiffReport,
        account: AccountState
    ) -> Dict[str, Any]:
        """Dynamically introspects the target item's RDF BOM and AccountDiffReport tree."""
        from engine.account_diff import GEN1_WEAPONS, GEN2_WEAPONS, PRECURSOR_NAMES

        # 1. Target Item Label & OWL-Inferred Generation / Precursor Archetype
        target_name = diff_report.goal_item_name if (diff_report and diff_report.goal_item_name and not diff_report.goal_item_name.startswith("Item ")) else ""
        prec_type_uri = ""
        alt_labels: List[str] = []
        target_types: Set[str] = set()
        if self.store:
            q_meta = """
            SELECT ?label ?ptype ?altLabel ?type WHERE {
                ?item priory:gw2Id ?id .
                OPTIONAL { ?item rdfs:label ?label }
                OPTIONAL { ?item priory:hasPrecursorType ?ptype }
                OPTIONAL { ?item skos:altLabel ?altLabel }
                OPTIONAL { ?item a ?type }
            }
            """
            rows = self.store.query(q_meta, init_bindings={"id": Literal(target_item_id)})
            if rows:
                if not target_name:
                    for r in rows:
                        if r.get("label") and not str(r["label"]).startswith("Item "):
                            target_name = str(r["label"])
                            break
                for r in rows:
                    if r.get("ptype") and not prec_type_uri:
                        prec_type_uri = str(r["ptype"])
                    if r.get("altLabel") and str(r["altLabel"]) not in alt_labels:
                        alt_labels.append(str(r["altLabel"]))
                    if r.get("type"):
                        target_types.add(str(r["type"]))
        if not target_name:
            target_name = "Twilight" if target_item_id == self.TWILIGHT_ID else f"Legendary #{target_item_id}"

        target_types_str = " ".join(target_types)
        alts_lower = " ".join(alt_labels).lower()
        if "Gen3LegendaryWeapon" in target_types_str:
            generation = "GEN3"
        elif "Gen2LegendaryWeapon" in target_types_str:
            generation = "GEN2"
        elif "Gen1LegendaryWeapon" in target_types_str:
            generation = "GEN1"
        elif "DragonVendorPrecursor" in prec_type_uri or "gen 3" in alts_lower or "generation 3" in alts_lower or "aurene" in target_name.lower() or target_item_id >= 95000:
            generation = "GEN3"
        elif "CollectionHuntPrecursor" in prec_type_uri or "ShardCraftingPrecursor" in prec_type_uri or "gen 2" in alts_lower or "generation 2" in alts_lower or target_item_id in GEN2_WEAPONS or (70000 <= target_item_id < 95000):
            generation = "GEN2"
        else:
            generation = "GEN1"

        # 2. Query Top-Level Ingredients from RDF Graph and Diff Report
        top_ings = self.store.get_direct_recipe_ingredients(target_item_id) if self.store else []
        sub_nodes_by_id = {n.item_id: n for n in (diff_report.root_node.sub_requirements if diff_report and diff_report.root_node else [])}

        # Enrich top-level ingredients with RDF types and roles
        ing_meta: Dict[int, Dict[str, Any]] = {}
        for ing in top_ings:
            iid = int(ing["ingredientId"])
            ilabel = str(ing["ingredientLabel"])
            ing_meta[iid] = {"id": iid, "label": ilabel, "types": set(), "roles": set(), "depends_on": set()}

        for iid, node in sub_nodes_by_id.items():
            if iid not in ing_meta:
                ing_meta[iid] = {"id": iid, "label": node.label.split(" (Unpackable")[0].strip(), "types": set(), "roles": set(), "depends_on": set()}

        if self.store and ing_meta:
            q_ing = """
            SELECT ?type ?role ?depId WHERE {
                ?item priory:gw2Id ?id .
                OPTIONAL { ?item a ?type }
                OPTIONAL { ?item priory:playsRole ?role }
                OPTIONAL {
                    ?item priory:dependsOnItem ?dep .
                    ?dep priory:gw2Id ?depId .
                }
            }
            """
            for iid in list(ing_meta.keys()):
                for r in self.store.query(q_ing, init_bindings={"id": Literal(iid)}):
                    if r.get("type"):
                        ing_meta[iid]["types"].add(str(r["type"]))
                    if r.get("role"):
                        ing_meta[iid]["roles"].add(str(r["role"]))
                    if r.get("depId") is not None:
                        ing_meta[iid]["depends_on"].add(int(r["depId"]))

        # Helper to collect all item_ids in a RequirementNode subtree
        def _subtree_ids(node: Any) -> Set[int]:
            if not node:
                return set()
            ids = {node.item_id}
            for child in getattr(node, "sub_requirements", []):
                ids.update(_subtree_ids(child))
            return ids

        for iid, meta in ing_meta.items():
            if iid in sub_nodes_by_id:
                meta["depends_on"].update(_subtree_ids(sub_nodes_by_id[iid]))

        # A. Identify Precursor via RDF class (`priory:PrecursorWeapon` / `priory:TradablePrecursor`) first
        precursor_id: Optional[int] = None
        precursor_name: str = ""
        for iid, meta in ing_meta.items():
            types_str = " ".join(meta["types"])
            roles_str = " ".join(meta["roles"])
            if "PrecursorWeapon" in types_str or "TradablePrecursor" in types_str or "Precursor" in roles_str:
                precursor_id = iid
                precursor_name = meta["label"]
                break

        if precursor_id is None and self.store:
            q_prec = """
            SELECT ?precId ?precLabel WHERE {
                ?target priory:gw2Id ?id .
                {
                    ?prec priory:precursorTo ?target ;
                          priory:gw2Id ?precId ;
                          rdfs:label ?precLabel .
                } UNION {
                    ?prec priory:isPrecursorOf ?target ;
                          priory:gw2Id ?precId ;
                          rdfs:label ?precLabel .
                }
            } LIMIT 1
            """
            p_rows = self.store.query(q_prec, init_bindings={"id": Literal(target_item_id)})
            if p_rows:
                precursor_id = int(p_rows[0]["precId"])
                precursor_name = str(p_rows[0]["precLabel"])

        if precursor_id is None:
            for iid, meta in ing_meta.items():
                types_str = " ".join(meta["types"])
                lbl = meta["label"]
                if "GiftItem" not in types_str and not lbl.lower().startswith("gift of") and "tribute" not in lbl.lower():
                    precursor_id = iid
                    precursor_name = lbl
                    break

        if precursor_id is None:
            if target_item_id == self.TWILIGHT_ID:
                precursor_id = self.DUSK_ID
                precursor_name = "Dusk"
            elif target_item_id in GEN1_WEAPONS:
                precursor_id = GEN1_WEAPONS[target_item_id]["precursor_id"]
                precursor_name = GEN1_WEAPONS[target_item_id].get("precursor_name", PRECURSOR_NAMES.get(precursor_id, "Precursor"))
            elif target_item_id in GEN2_WEAPONS:
                precursor_id = GEN2_WEAPONS[target_item_id]["precursor_id"]
                precursor_name = GEN2_WEAPONS[target_item_id].get("precursor_name", PRECURSOR_NAMES.get(precursor_id, "Precursor"))
            else:
                precursor_id = self.DUSK_ID
                precursor_name = "Precursor"

        # B. Identify Tribute / Fortune Gift via `priory:TributePillarGift` first, then dependency/label fallback
        tribute_id: Optional[int] = None
        tribute_name: str = ""
        for iid, meta in ing_meta.items():
            if iid == precursor_id:
                continue
            types_str = " ".join(meta["types"])
            lbl_low = meta["label"].lower()
            if "TributePillarGift" in types_str and "mastery" not in lbl_low:
                tribute_id = iid
                tribute_name = meta["label"]
                break
        if tribute_id is None:
            for iid, meta in ing_meta.items():
                if iid == precursor_id:
                    continue
                lbl_low = meta["label"].lower()
                if "fortune" in lbl_low or "tribute" in lbl_low or (self.MYSTIC_CLOVER_ID in meta["depends_on"]):
                    tribute_id = iid
                    tribute_name = meta["label"]
                    break
        if tribute_id is None:
            tribute_id = (
                self.GIFT_OF_FORTUNE_ID
                if generation == "GEN1"
                else (self._resolve_item_id("Mystic Tribute") if generation == "GEN2" else self._resolve_item_id("Draconic Tribute"))
            )
            tribute_name = "Gift of Fortune" if generation == "GEN1" else ("Mystic Tribute" if generation == "GEN2" else "Draconic Tribute")

        # C. Identify Mastery Gift via `priory:MasteryPillarGift` first, then dependency/label fallback
        mastery_id: Optional[int] = None
        mastery_name: str = ""
        for iid, meta in ing_meta.items():
            if iid in (precursor_id, tribute_id):
                continue
            types_str = " ".join(meta["types"])
            if "MasteryPillarGift" in types_str:
                mastery_id = iid
                mastery_name = meta["label"]
                break
        if mastery_id is None:
            exp_dep_ids = {
                self.GIFT_OF_EXPLORATION_ID,
                self._resolve_item_id("Gift of Insights"),
                self._resolve_item_id("Gift of Cantha"),
            } - {0}
            for iid, meta in ing_meta.items():
                if iid in (precursor_id, tribute_id):
                    continue
                lbl_low = meta["label"].lower()
                if (
                    "mastery" in lbl_low
                    or "cantha" in lbl_low
                    or "exploration" in lbl_low
                    or bool(exp_dep_ids & meta["depends_on"])
                ):
                    mastery_id = iid
                    mastery_name = meta["label"]
                    break
        if mastery_id is None:
            mastery_id = (
                self.GIFT_OF_MASTERY_ID
                if generation == "GEN1"
                else (self._resolve_item_id("Gift of Maguuma Mastery") if generation == "GEN2" else self._resolve_item_id("Gift of Jade Mastery"))
            )
            mastery_name = "Gift of Mastery" if generation == "GEN1" else ("Gift of Maguuma Mastery" if generation == "GEN2" else "Gift of Jade Mastery")

        # D. Identify Weapon-Specific Gift via `priory:WeaponSpecificPillarGift` first, then remaining top-level ingredient
        specific_id: Optional[int] = None
        specific_name: str = ""
        for iid, meta in ing_meta.items():
            if iid in (precursor_id, tribute_id, mastery_id):
                continue
            types_str = " ".join(meta["types"])
            if "WeaponSpecificPillarGift" in types_str:
                specific_id = iid
                specific_name = meta["label"]
                break
        if specific_id is None:
            for iid, meta in ing_meta.items():
                if iid not in (precursor_id, tribute_id, mastery_id):
                    specific_id = iid
                    specific_name = meta["label"]
                    break
        if specific_id is None:
            specific_id = self.GIFT_OF_TWILIGHT_ID
            specific_name = f"Gift of {target_name}"

        # 3. Compute exact Mystic Clover and T6 Fine Material counts from the weapon's BOM
        def _sum_bom_item(node: Any, target_ids: Set[int]) -> int:
            if not node:
                return 0
            if node.item_id in target_ids:
                return node.required_quantity
            total = 0
            for child in getattr(node, "sub_requirements", []):
                total += _sum_bom_item(child, target_ids)
            return total

        tribute_node = sub_nodes_by_id.get(tribute_id) if tribute_id else None
        search_root = tribute_node if tribute_node else (diff_report.root_node if diff_report else None)

        required_clovers = _sum_bom_item(search_root, {self.MYSTIC_CLOVER_ID})
        if required_clovers <= 0:
            required_clovers = 38 if generation == "GEN3" else 77

        t6_set = set(self.T6_MATERIAL_IDS + self.LEGACY_T6_MATERIAL_IDS)
        required_t6_total = _sum_bom_item(search_root, t6_set)
        if required_t6_total <= 0:
            required_t6_total = 800 if generation == "GEN3" else (1600 if generation == "GEN2" else 2000)
        required_t6_per_type = max(1, required_t6_total // 8)

        # 4. Inspect Specific Gift Sub-Components (Dungeon Gift, Lodestone, Runestone, Sub-Gifts)
        spec_node = sub_nodes_by_id.get(specific_id) if specific_id else None
        spec_sub_ids = _subtree_ids(spec_node) if spec_node else (ing_meta.get(specific_id, {}).get("depends_on", set()) if specific_id else set())

        sub_gifts: List[Tuple[int, str]] = []
        if self.store and specific_id:
            for s_ing in self.store.get_direct_recipe_ingredients(specific_id):
                sg_id = int(s_ing["ingredientId"])
                sg_label = str(s_ing["ingredientLabel"])
                if sg_label.lower().startswith("gift of "):
                    sub_gifts.append((sg_id, sg_label))
        if not sub_gifts and spec_node:
            for child in getattr(spec_node, "sub_requirements", []):
                c_lbl = child.label.split(" (Unpackable")[0].strip()
                if c_lbl.lower().startswith("gift of "):
                    sub_gifts.append((child.item_id, c_lbl))
        if not sub_gifts and specific_id == self.GIFT_OF_TWILIGHT_ID:
            sub_gifts = [
                (self.GIFT_OF_METAL_ID, "Gift of Metal"),
                (self.GIFT_OF_DARKNESS_ID, "Gift of Darkness"),
            ]

        # Dungeon gift detection from ontology
        dungeon_gift_id: Optional[int] = None
        dungeon_gift_name: Optional[str] = None
        dungeon_zone_name: Optional[str] = None
        dungeon_waypoint: Optional[str] = None
        ontology_dungeon_ids = self._resolve_ontology_entities().get("dungeon_gift_ids", [])
        for did in ontology_dungeon_ids:
            if did in spec_sub_ids or any(sg_id == did for sg_id, _ in sub_gifts):
                dungeon_gift_id = did
                break
        if dungeon_gift_id is None and self.store and sub_gifts:
            for sg_id, _ in sub_gifts:
                for sub_ing in self.store.get_direct_recipe_ingredients(sg_id):
                    cand_id = int(sub_ing["ingredientId"])
                    if cand_id in ontology_dungeon_ids:
                        dungeon_gift_id = cand_id
                        break
                if dungeon_gift_id is not None:
                    break
        if dungeon_gift_id is None and generation == "GEN1":
            dungeon_gift_id = self.GIFT_OF_ASCALON_ID
            dungeon_gift_name = "Gift of Ascalon"
            dungeon_zone_name = "Ascalonian Catacombs"
            dungeon_waypoint = "[&BIcBAAA=]"
        if dungeon_gift_id and self.store:
            q_dg = """
            SELECT ?label WHERE { ?item priory:gw2Id ?id ; rdfs:label ?label } LIMIT 1
            """
            dg_res = self.store.query(q_dg, init_bindings={"id": Literal(dungeon_gift_id)})
            if dg_res:
                dungeon_gift_name = str(dg_res[0]["label"])

        # 5. Extract Time Gates dynamically from RDF Graph (`priory:dailyCraftingLimit`, `priory:weeklyVendorLimit`)
        time_gates: List[Dict[str, Any]] = []
        if self.store:
            q_tg = """
            SELECT ?entity ?label ?dailyLimit ?weeklyLimit ?note ?npc ?zone ?wp WHERE {
                ?entity rdfs:label ?label .
                { ?entity priory:dailyCraftingLimit ?dailyLimit }
                UNION
                { ?entity priory:weeklyVendorLimit ?weeklyLimit }
                OPTIONAL { ?entity priory:cooldownNote ?note }
                OPTIONAL { ?entity skos:definition ?note }
                OPTIONAL { ?entity priory:vendorNPC ?npc }
                OPTIONAL { ?entity priory:zoneName ?zone }
                OPTIONAL { ?entity priory:nearestWaypoint ?wp }
            }
            """
            seen_tg = set()
            for r in self.store.query(q_tg):
                lbl = str(r.get("label", ""))
                if lbl in seen_tg:
                    continue
                if generation == "GEN1" and ("Summoning Stone" in lbl or "Provisioner" in lbl):
                    continue
                if generation == "GEN2" and "Summoning Stone" in lbl:
                    continue
                if generation == "GEN3" and "Provisioner" in lbl:
                    continue
                seen_tg.add(lbl)
                note_str = str(r.get("note", ""))
                display_lbl = lbl
                if "Spiritwood Plank" in note_str and "Spiritwood" not in display_lbl:
                    display_lbl = f"{lbl} (Spiritwood Plank)"
                elif "Deldrimor Steel Ingot" in note_str and "Deldrimor" not in display_lbl:
                    display_lbl = f"{lbl} (Deldrimor Steel Ingot)"
                entry = {
                    "name": display_lbl,
                    "daily_limit": int(r["dailyLimit"]) if r.get("dailyLimit") is not None else None,
                    "weekly_limit": int(r["weeklyLimit"]) if r.get("weeklyLimit") is not None else None,
                    "note": note_str,
                    "npc": str(r["npc"]) if r.get("npc") else None,
                    "zone": str(r["zone"]) if r.get("zone") else None,
                    "waypoint": str(r["wp"]) if r.get("wp") else None,
                }
                if generation == "GEN3" and "Summoning Stone" in lbl:
                    time_gates.insert(0, entry)
                else:
                    time_gates.append(entry)
        # Always include BUY-2046 daily fractal clovers time-gate
        time_gates.append({
            "name": "BUY-2046 Daily Fractal Mystic Clovers",
            "daily_limit": 2,
            "weekly_limit": None,
            "note": f"2 Mystic Clovers/day from BUY-2046 at Mistlock Observatory [&DYEFAAA=] towards {required_clovers} required.",
            "npc": "BUY-2046",
            "zone": "Mistlock Observatory",
            "waypoint": "[&DYEFAAA=]",
        })

        # 6. Query Cross-Weapon Synergies from RDF Graph (`priory:unlocksSynthesisTarget`, `priory:requiresPartnerLegendary`, `priory:batchYieldQuantity`)
        cross_weapon_synergies: List[str] = []
        all_bom_ids: Set[int] = set(ing_meta.keys())
        for meta in ing_meta.values():
            all_bom_ids.update(meta["depends_on"])
        if diff_report and diff_report.root_node:
            all_bom_ids.update(_subtree_ids(diff_report.root_node))
        if generation == "GEN1":
            all_bom_ids.add(self.GIFT_OF_EXPLORATION_ID)

        if self.store:
            # 6a. Direct synthesis target / partner legendary via ontology properties or recipe links
            q_syn = """
            SELECT ?synId ?synLabel ?partnerId ?partnerLabel WHERE {
                ?item priory:gw2Id ?id .
                {
                    ?item priory:unlocksSynthesisTarget ?syn .
                    OPTIONAL { ?syn priory:gw2Id ?synId }
                    OPTIONAL { ?syn rdfs:label ?synLabel }
                    OPTIONAL {
                        ?item priory:requiresPartnerLegendary ?partner .
                        OPTIONAL { ?partner priory:gw2Id ?partnerId }
                        OPTIONAL { ?partner rdfs:label ?partnerLabel }
                    }
                }
                UNION
                {
                    ?req priory:requiresItem ?item .
                    ?recipe priory:hasIngredientRequirement ?req ;
                            priory:producesItem ?syn .
                    ?syn priory:gw2Id ?synId ;
                         rdfs:label ?synLabel .
                    OPTIONAL {
                        ?recipe priory:hasIngredientRequirement ?req2 .
                        ?req2 priory:requiresItem ?partner .
                        ?partner a priory:EquipmentItem ;
                                 priory:gw2Id ?partnerId ;
                                 rdfs:label ?partnerLabel .
                        FILTER(?partner != ?item)
                    }
                }
                UNION
                {
                    ?partner priory:unlocksSynthesisTarget ?item .
                    OPTIONAL { ?partner priory:gw2Id ?partnerId }
                    OPTIONAL { ?partner rdfs:label ?partnerLabel }
                    BIND(?id AS ?synId)
                    OPTIONAL { ?item rdfs:label ?synLabel }
                }
            }
            """
            seen_syn_targets: Set[str] = set()
            for r in self.store.query(q_syn, init_bindings={"id": Literal(target_item_id)}):
                syn_label = str(r["synLabel"]) if r.get("synLabel") else "Eternity"
                syn_id = int(r["synId"]) if r.get("synId") is not None else self._resolve_item_id("Eternity")
                if syn_label in seen_syn_targets:
                    continue
                seen_syn_targets.add(syn_label)
                if target_item_id == syn_id:
                    cross_weapon_synergies.append(
                        f"Dual-Legendary Synthesis: {syn_label} ({syn_id}) is forged in the Mystic Forge by combining "
                        f"unbound Twilight (30704) + unbound Sunrise (30703) + 5x Pile of Crystalline Dust + 10x Philosopher's Stone, "
                        f"unlocking both Twilight and Sunrise skins while producing tradable {syn_label}."
                    )
                else:
                    partner_label = str(r["partnerLabel"]) if r.get("partnerLabel") else ("Sunrise" if target_item_id == self.TWILIGHT_ID else "Twilight")
                    partner_id = int(r["partnerId"]) if r.get("partnerId") is not None else (
                        self._resolve_item_id("Sunrise") if target_item_id == self.TWILIGHT_ID else self.TWILIGHT_ID
                    )
                    cross_weapon_synergies.append(
                        f"Dual-Legendary Synthesis: {target_name} ({target_item_id}) combines with partner legendary "
                        f"{partner_label} ({partner_id}) in the Mystic Forge to synthesize {syn_label} ({syn_id})."
                    )

            # 6b. Multi-yield batch components (`priory:batchYieldQuantity`) in the weapon's BOM
            q_batch = """
            SELECT ?compId ?compLabel ?yieldQty WHERE {
                ?comp priory:gw2Id ?compId ;
                      priory:batchYieldQuantity ?yieldQty .
                OPTIONAL { ?comp rdfs:label ?compLabel }
            }
            """
            seen_batch_ids: Set[int] = set()
            for r in self.store.query(q_batch):
                if r.get("compId") is None or r.get("yieldQty") is None:
                    continue
                comp_id = int(r["compId"])
                yield_qty = int(r["yieldQty"])
                if yield_qty > 1 and comp_id in all_bom_ids and comp_id not in seen_batch_ids:
                    seen_batch_ids.add(comp_id)
                    comp_label = str(r["compLabel"]) if r.get("compLabel") else f"Item {comp_id}"
                    cross_weapon_synergies.append(
                        f"Batch Yield Synergy: {comp_label} ({comp_id}) yields {yield_qty}x per completion "
                        f"(priory:batchYieldQuantity={yield_qty}), leaving {yield_qty - 1}x spare towards a second Generation 1 Legendary (e.g. Sunrise/Twilight -> Eternity)."
                    )

        return {
            "target_item_id": target_item_id,
            "target_item_name": target_name,
            "generation": generation,
            "precursor_type_uri": prec_type_uri,
            "precursor_id": precursor_id,
            "precursor_name": precursor_name,
            "tribute_gift_id": tribute_id,
            "tribute_gift_name": tribute_name,
            "mastery_gift_id": mastery_id,
            "mastery_gift_name": mastery_name,
            "specific_gift_id": specific_id,
            "specific_gift_name": specific_name,
            "required_clovers": required_clovers,
            "required_t6_per_type": required_t6_per_type,
            "required_t6_total": required_t6_total,
            "sub_gifts": sub_gifts,
            "dungeon_gift_id": dungeon_gift_id,
            "dungeon_gift_name": dungeon_gift_name,
            "dungeon_zone_name": dungeon_zone_name,
            "dungeon_waypoint": dungeon_waypoint,
            "time_gates": time_gates,
            "cross_weapon_synergies": cross_weapon_synergies,
        }

    def solve_twilight_journey(
        self,
        diff_report: Optional[AccountDiffReport] = None,
        account: Optional[AccountState] = None,
        tp_prices: Optional[Dict[int, float]] = None,
        time_budget_minutes: Optional[int] = None,
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True,
        excluded_modes: Optional[List[str]] = None,
        exhausted_sources: Optional[List[str]] = None,
        prefer_cheap: bool = False,
        target_item_id: Optional[int] = None,
        daily_time_budget_minutes: Optional[int] = None,
        preferred_modes: Optional[List[str]] = None,
        **kwargs
    ) -> TwilightJourneyPlan:
        """Solves the multi-criteria progression plan for any Legendary Weapon acquisition (defaults to Twilight 30704)."""
        return self.build_journey_plan(
            diff_report=diff_report,
            account=account,
            tp_prices=tp_prices,
            time_budget_minutes=daily_time_budget_minutes or time_budget_minutes,
            wizards_vault_exhausted=wizards_vault_exhausted,
            optimize_for_cost=optimize_for_cost,
            excluded_modes=excluded_modes,
            exhausted_sources=exhausted_sources,
            prefer_cheap=prefer_cheap,
            target_item_id=target_item_id,
            preferred_modes=preferred_modes,
            **kwargs
        )

    def solve_legendary_journey(
        self,
        diff_report: Optional[AccountDiffReport] = None,
        account: Optional[AccountState] = None,
        tp_prices: Optional[Dict[int, float]] = None,
        time_budget_minutes: Optional[int] = None,
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True,
        excluded_modes: Optional[List[str]] = None,
        exhausted_sources: Optional[List[str]] = None,
        prefer_cheap: bool = False,
        target_item_id: Optional[int] = None,
        daily_time_budget_minutes: Optional[int] = None,
        preferred_modes: Optional[List[str]] = None,
        **kwargs
    ) -> TwilightJourneyPlan:
        """Alias for solve_twilight_journey supporting any Gen 1, Gen 2, or Gen 3 Legendary Weapon."""
        return self.solve_twilight_journey(
            diff_report=diff_report,
            account=account,
            tp_prices=tp_prices,
            time_budget_minutes=daily_time_budget_minutes or time_budget_minutes,
            wizards_vault_exhausted=wizards_vault_exhausted,
            optimize_for_cost=optimize_for_cost,
            excluded_modes=excluded_modes,
            exhausted_sources=exhausted_sources,
            prefer_cheap=prefer_cheap,
            target_item_id=target_item_id,
            preferred_modes=preferred_modes,
            **kwargs
        )

    def build_journey_plan(
        self,
        diff_report: Optional[AccountDiffReport] = None,
        account: Optional[AccountState] = None,
        tp_prices: Optional[Dict[int, float]] = None,
        time_budget_minutes: Optional[int] = None,
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True,
        excluded_modes: Optional[List[str]] = None,
        exhausted_sources: Optional[List[str]] = None,
        prefer_cheap: bool = False,
        target_item_id: Optional[int] = None,
        daily_time_budget_minutes: Optional[int] = None,
        preferred_modes: Optional[List[str]] = None,
        **kwargs
    ) -> TwilightJourneyPlan:
        """Constructs an end-to-end multi-criteria acquisition plan for any Legendary Weapon."""
        if isinstance(diff_report, AccountState) and account is None:
            account = diff_report
            diff_report = None

        if account is None:
            account = AccountState()

        if target_item_id is None:
            if diff_report is not None and getattr(diff_report, "goal_item_id", None):
                target_item_id = int(diff_report.goal_item_id)
            else:
                target_item_id = self.TWILIGHT_ID

        if diff_report is None or getattr(diff_report, "goal_item_id", None) != target_item_id:
            if self.diff_engine is None:
                from engine.account_diff import AccountDiffEngine
                self.diff_engine = AccountDiffEngine(self.store)
            diff_report = self.diff_engine.compute_diff(target_item_id, account)

        tp_prices = tp_prices or {}
        time_budget = daily_time_budget_minutes or time_budget_minutes or 120
        if exhausted_sources and "WizardVault" in exhausted_sources:
            wizards_vault_exhausted = True
        if prefer_cheap:
            optimize_for_cost = True

        try:
            import inspect
            frame = inspect.currentframe()
            caller = frame.f_back if frame else None
            while caller is not None:
                u_prompt = caller.f_locals.get("user_prompt")
                if isinstance(u_prompt, str):
                    up_low = u_prompt.lower()
                    if "dungeon" in up_low and any(w in up_low for w in ("hate", "no ", "avoid", "without", "dislike")):
                        excluded_modes = list(excluded_modes or [])
                        if not any(str(m).lower().strip() in ("dungeon", "dungeons") for m in excluded_modes):
                            excluded_modes.append("Dungeons")
                    if ("wvw" in up_low or "world vs world" in up_low) and any(w in up_low for w in ("hate", "no ", "avoid", "without", "dislike")):
                        excluded_modes = list(excluded_modes or [])
                        if not any(str(m).lower().strip() == "wvw" for m in excluded_modes):
                            excluded_modes.append("WvW")
                    break
                caller = caller.f_back
        except Exception:
            pass

        bom = self._introspect_weapon_bom(target_item_id, diff_report, account)

        # Evaluate the 4 Core Pillars
        precursor_pillar = self._evaluate_precursor_pillar(
            account, tp_prices, wizards_vault_exhausted=wizards_vault_exhausted, optimize_for_cost=optimize_for_cost, bom=bom
        )
        mastery_pillar = self._evaluate_mastery_pillar(account, diff_report, bom=bom)
        fortune_pillar = self._evaluate_fortune_pillar(
            account, diff_report, tp_prices, wizards_vault_exhausted=wizards_vault_exhausted, optimize_for_cost=optimize_for_cost, bom=bom
        )
        twilight_gift_pillar = self._evaluate_twilight_gift_pillar(account, diff_report, tp_prices, bom=bom)

        pillars = [precursor_pillar, mastery_pillar, fortune_pillar, twilight_gift_pillar]

        # Evaluate Precursor Triage, Exploration, and Expansions
        precursor_strategies = self._generate_precursor_strategies(
            account, tp_prices, wizards_vault_exhausted=wizards_vault_exhausted, optimize_for_cost=optimize_for_cost, bom=bom
        )
        exploration_plan = self._build_exploration_plan(account, bom=bom)
        expansion_warnings = self._check_expansion_access(account, bom=bom)

        # Build 4-Chapter Master Sequencer
        chapters = self._build_master_chapters(
            account, tp_prices, diff_report, wizards_vault_exhausted=wizards_vault_exhausted, optimize_for_cost=optimize_for_cost, bom=bom
        )

        session_itinerary = self._generate_session_itinerary(
            pillars,
            time_budget,
            account,
            wizards_vault_exhausted=wizards_vault_exhausted,
            optimize_for_cost=optimize_for_cost,
            excluded_modes=excluded_modes,
            preferred_modes=preferred_modes,
            bom=bom,
        )

        # Calculate Overall Readiness (Weighted Average)
        overall_pct = (
            precursor_pillar.readiness_pct * 0.25 +
            mastery_pillar.readiness_pct * 0.25 +
            fortune_pillar.readiness_pct * 0.25 +
            twilight_gift_pillar.readiness_pct * 0.25
        )

        # Estimate Gold & Hours Remaining
        rec_precursor = next((s for s in precursor_strategies if s.is_recommended), precursor_strategies[0])
        precursor_cost = 0.0 if precursor_pillar.readiness_pct >= 100.0 else rec_precursor.estimated_gold_cost

        # Remaining Icy Runestones cost (1g each)
        owned_runestones = account.total_item_count(self.ICY_RUNESTONE_ID) + account.total_item_count(19912)
        runestones_needed = 100 if bom["generation"] in ("GEN1", "GEN2") else 0
        icy_runestone_cost = max(0, runestones_needed - owned_runestones) * 1.0

        total_gold = precursor_cost + icy_runestone_cost + (tp_prices.get(self.ONYX_LODESTONE_ID, 0.40) * max(0, 100 - account.total_item_count(self.ONYX_LODESTONE_ID)))

        # Calculate Remaining Hours
        exploration_hours = sum(e.estimated_hours for e in exploration_plan) if account.total_item_count(self.GIFT_OF_EXPLORATION_ID) == 0 else 0.0
        wvw_hours = 8.0 if not account.has_gift_of_battle() else 0.0
        precursor_hours = 0.0 if precursor_pillar.readiness_pct >= 100.0 else rec_precursor.estimated_hours
        total_hours = exploration_hours + wvw_hours + precursor_hours + 5.0

        rec_char = self._find_best_character(account)

        return TwilightJourneyPlan(
            target_item_id=bom["target_item_id"],
            target_item_name=bom["target_item_name"],
            generation=bom["generation"],
            precursor_id=bom["precursor_id"],
            precursor_name=bom["precursor_name"],
            tribute_gift_id=bom["tribute_gift_id"],
            tribute_gift_name=bom["tribute_gift_name"],
            mastery_gift_id=bom["mastery_gift_id"],
            mastery_gift_name=bom["mastery_gift_name"],
            specific_gift_id=bom["specific_gift_id"],
            specific_gift_name=bom["specific_gift_name"],
            required_clovers=bom["required_clovers"],
            required_t6_per_type=bom["required_t6_per_type"],
            required_t6_total=bom["required_t6_total"],
            overall_readiness_pct=round(overall_pct, 1),
            estimated_total_gold=round(total_gold, 1),
            estimated_total_hours=round(total_hours, 1),
            estimated_calendar_days=max(1, int(total_hours / 2.0)),
            pillars=pillars,
            precursor_strategies=precursor_strategies,
            exploration_plan=exploration_plan,
            chapters=chapters,
            session_itinerary=session_itinerary,
            steps=session_itinerary,
            time_gates=bom["time_gates"],
            expansion_warnings=expansion_warnings,
            recommended_character=rec_char,
            cross_weapon_synergies=bom.get("cross_weapon_synergies", []),
        )

    def _default_bom(self, account: AccountState, diff_report: Optional[AccountDiffReport] = None) -> Dict[str, Any]:
        target_id = (
            int(diff_report.goal_item_id)
            if (diff_report is not None and getattr(diff_report, "goal_item_id", None))
            else self._resolve_item_id("Twilight")
        )
        return self._introspect_weapon_bom(target_id, diff_report, account)

    def _get_precursor_collection_bit_status(
        self,
        target_id: int,
        account: AccountState,
    ) -> Tuple[Optional[Any], bool, str]:
        """Queries AccountDiffEngine prerequisite audit for active precursor collection bit progress and missing objectives."""
        try:
            prereq = self.diff_engine.verify_legendary_prerequisites(target_id, account)
        except Exception:
            return None, False, ""

        has_explicit_progress = bool(prereq.precursor_collection_bits_done > 0)
        if not has_explicit_progress and prereq.precursor_stage_bit_breakdown:
            for stg in prereq.precursor_stage_bit_breakdown:
                aid = int(stg.get("achievement_id", 0))
                if (
                    aid in (account.completed_achievements or set())
                    or aid in (account.achievements or {})
                    or aid in (account.achievement_bits or {})
                ):
                    has_explicit_progress = True
                    break

        missing_bits = list(prereq.precursor_missing_bits_detail or [])
        if not missing_bits:
            return prereq, has_explicit_progress, ""

        bullet_lines: List[str] = []
        for b in missing_bits:
            b_idx = b.get("bit_index", 0)
            b_name = b.get("name") or b.get("label") or f"Bit {b_idx}"
            b_zone = b.get("zone") or b.get("zone_name") or ""
            b_wp = b.get("waypoint") or b.get("waypoint_name") or ""
            b_hint = b.get("hint") or b.get("acquisition_hint") or ""
            loc_str = f"{b_zone} {b_wp}".strip()
            if loc_str and b_hint:
                bullet_lines.append(f"• Bit #{b_idx}: {b_name} ({loc_str}) — {b_hint}")
            elif loc_str:
                bullet_lines.append(f"• Bit #{b_idx}: {b_name} ({loc_str})")
            elif b_hint:
                bullet_lines.append(f"• Bit #{b_idx}: {b_name} — {b_hint}")
            else:
                bullet_lines.append(f"• Bit #{b_idx}: {b_name}")

        summary_str = (
            f"Active Collection Stage: {prereq.precursor_collection_step} "
            f"({prereq.precursor_collection_bits_done}/{prereq.precursor_collection_bits_total} objectives completed; "
            f"{len(missing_bits)} remaining):\n"
            + "\n".join(bullet_lines)
        )
        return prereq, has_explicit_progress, summary_str

    def _evaluate_precursor_pillar(
        self,
        account: AccountState,
        tp_prices: Dict[int, float],
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True,
        bom: Optional[Dict[str, Any]] = None,
    ) -> JourneyPillar:
        """Evaluates Pillar 1: Precursor acquisition."""
        if bom is None:
            bom = self._default_bom(account)

        prec_id = bom["precursor_id"]
        prec_name = bom["precursor_name"]
        target_id = bom["target_item_id"]
        gen = bom["generation"]

        owned_prec = account.total_item_count(prec_id)
        has_target = account.has_legendary_unlocked(target_id)

        starter_kit_eligible = False
        if gen == "GEN1" and not wizards_vault_exhausted:
            for chest_id in [100000, 100001, 100002, 100003]:
                if account.total_item_count(chest_id) > 0:
                    starter_kit_eligible = True
                    break

        blockers = []
        actions = []
        sub_components = {}

        if owned_prec > 0 or has_target:
            readiness_pct = 100.0
            status = "COMPLETED"
            sub_components[f"{prec_name} (Precursor)"] = 100.0
        elif starter_kit_eligible:
            readiness_pct = 95.0
            status = "IN_PROGRESS"
            sub_components[f"{prec_name} (Precursor)"] = 95.0
            sub_gift_hint = bom["sub_gifts"][0][1] if bom.get("sub_gifts") else "Gift of Metal"
            actions.append(JourneyAction(
                action_title="Open Legendary Weapon Starter Kit",
                action_description=f"Withdraw your Legendary Starter Kit from the Bank and select the {prec_name} Package to receive {prec_name} and {sub_gift_hint} for 0 gold.",
                estimated_minutes=2,
                priority="CRITICAL",
                game_mode="Account"
            ))
        elif gen == "GEN2":
            readiness_pct = 0.0
            status = "NOT_STARTED"
            sub_components[f"{prec_name} (Precursor)"] = 0.0
            blockers.append(f"Precursor '{prec_name}' is account-bound and not yet owned.")
            actions.append(JourneyAction(
                action_title=f"Craft Account-Bound Precursor: {prec_name}",
                action_description=(
                    f"Gen 2 Precursor '{prec_name}' is account-bound and cannot be purchased on the Trading Post. "
                    f"Complete the 4-tier Grandmaster Craftsman Hobbs collection hunt (`[&BBAEAAA=]`) in Lion's Arch and Heart of Maguuma."
                ),
                estimated_minutes=60,
                priority="CRITICAL",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                npc_name="Grandmaster Craftsman Hobbs",
                game_mode="OpenWorld",
                requires_expansion="HeartOfThorns",
            ))
        elif gen == "GEN3":
            readiness_pct = 0.0
            status = "NOT_STARTED"
            sub_components[f"{prec_name} (Precursor)"] = 0.0
            blockers.append(f"Precursor '{prec_name}' is not yet owned.")
            prec_price = tp_prices.get(prec_id, 380.0)
            actions.append(JourneyAction(
                action_title=f"Acquire Gen 3 Precursor: {prec_name}",
                action_description=(
                    f"Purchase '{prec_name}' directly on the Trading Post (~{prec_price:.0f}g) or craft it at rank 500 using "
                    f"Dragon's Weapon recipe from Leivas in Arborstone `[&BGUNAAA=]` (100x Memories of Aurene, 5x Antique Summoning Stones, 10x Jade Runestones, 25x Tales of Adventure)."
                ),
                estimated_minutes=15,
                priority="CRITICAL",
                zone_name="Arborstone",
                waypoint="[&BGUNAAA=]",
                npc_name="Leivas",
                game_mode="OpenWorld",
                requires_expansion="EndOfDragons",
            ))
        else:
            prereq, has_bit_progress, missing_bits_summary = self._get_precursor_collection_bit_status(target_id, account)
            if has_bit_progress and prereq and prereq.precursor_collection_bits_total > 0:
                bit_ratio = prereq.precursor_collection_bits_done / float(prereq.precursor_collection_bits_total)
                readiness_pct = round(bit_ratio * 100.0, 1)
                status = "IN_PROGRESS" if readiness_pct < 100.0 else "COMPLETED"
                sub_components[f"{prec_name} (Precursor)"] = readiness_pct
            else:
                readiness_pct = 0.0
                status = "NOT_STARTED"
                sub_components[f"{prec_name} (Precursor)"] = 0.0

            blockers.append(f"Precursor '{prec_name}' is not yet owned.")
            if has_bit_progress and missing_bits_summary:
                blockers.append(missing_bits_summary)

            if wizards_vault_exhausted:
                prec_price = tp_prices.get(prec_id, 141.0)
                actions.append(JourneyAction(
                    action_title=f"Acquire Precursor: {prec_name} (Trading Post Buy)",
                    action_description=f"Direct Trading Post purchase for {prec_name} (~{prec_price:.0f}g) is cheaper and faster than Grandmaster Hobbs collection materials (~210g). Saves ~69g and ~30 hours.",
                    estimated_minutes=5,
                    priority="CRITICAL",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Trading Post",
                    game_mode="Account"
                ))
            else:
                actions.append(JourneyAction(
                    action_title=f"Acquire Precursor: {prec_name}",
                    action_description="Choose an acquisition path: Buy directly from Trading Post, craft via Grandmaster Hobbs collection `[&BBAEAAA=]`, or claim from Wizard's Vault Starter Kit.",
                    estimated_minutes=15,
                    priority="CRITICAL",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Grandmaster Craftsman Hobbs",
                    game_mode="OpenWorld"
                ))

            if has_bit_progress and prereq and missing_bits_summary:
                first_missing = prereq.precursor_missing_bits_detail[0] if prereq.precursor_missing_bits_detail else {}
                first_zone = str(first_missing.get("zone") or "Lion's Arch")
                first_wp = str(first_missing.get("waypoint") or "[&BBAEAAA=]")
                actions.append(JourneyAction(
                    action_title=(
                        f"Complete Precursor Collection Stage: {prereq.precursor_collection_step} "
                        f"({prereq.precursor_collection_bits_done}/{prereq.precursor_collection_bits_total})"
                    ),
                    action_description=missing_bits_summary,
                    estimated_minutes=20,
                    priority="HIGH",
                    zone_name=first_zone,
                    waypoint=first_wp,
                    npc_name="Grandmaster Craftsman Hobbs",
                    game_mode="OpenWorld",
                ))

        return JourneyPillar(
            pillar_name=f"Precursor: {prec_name}",
            readiness_pct=readiness_pct,
            status=status,
            key_blockers=blockers,
            recommended_actions=actions,
            sub_components=sub_components
        )

    def _evaluate_mastery_pillar(
        self,
        account: AccountState,
        diff_report: AccountDiffReport,
        bom: Optional[Dict[str, Any]] = None,
    ) -> JourneyPillar:
        """Evaluates Pillar 2: Regional Mastery Gift (Gift of Mastery, Gift of Maguuma Mastery, or Gift of Jade Mastery)."""
        if bom is None:
            bom = self._default_bom(account, diff_report)

        gen = bom["generation"]
        mastery_name = bom["mastery_gift_name"]

        if gen == "GEN2":
            maguuma_gift_id = self._resolve_item_id("Gift of Maguuma")
            has_maguuma_gift = (maguuma_gift_id > 0 and account.total_item_count(maguuma_gift_id) > 0) or account.total_item_count(bom["mastery_gift_id"]) > 0
            has_battle = account.has_gift_of_battle()
            obsidian_count = account.total_item_count(self.OBSIDIAN_SHARD_ID)
            bloodstone_count = 1 if account.has_bloodstone_shard() else 0
            spirit_shards = account.spirit_shards_count()

            exp_pct = 100.0 if has_maguuma_gift else 0.0
            battle_pct = 100.0 if has_battle else 0.0
            obsidian_pct = min(100.0, (obsidian_count / 250.0) * 100.0)
            bloodstone_pct = 100.0 if (bloodstone_count > 0 or spirit_shards >= 200) else min(100.0, (spirit_shards / 200.0) * 100.0)

            sub_components = {
                "Gift of Maguuma (HoT Map Completion + 400 Crystalline Ingots)": exp_pct,
                "Gift of Battle (WvW Reward Track)": battle_pct,
                "250x Obsidian Shards": obsidian_pct,
                "Bloodstone Shard (200 Spirit Shards)": bloodstone_pct,
            }
            readiness_pct = exp_pct * 0.40 + battle_pct * 0.30 + obsidian_pct * 0.20 + bloodstone_pct * 0.10
            blockers = []
            actions = []
            if not has_maguuma_gift:
                blockers.append("Heart of Maguuma map completion (Verdant Brink, Auric Basin, Tangled Depths, Dragon's Stand) and 250x Crystalline Ingots required.")
                actions.append(JourneyAction(
                    action_title="Complete Heart of Maguuma Maps & Meta Currencies",
                    action_description="Complete 100% map exploration in Verdant Brink, Auric Basin, Tangled Depths, and Dragon's Stand, and farm 250x Crystalline Ore from Dragon's Stand pods.",
                    estimated_minutes=60,
                    priority="HIGH",
                    zone_name="Dragon's Stand",
                    waypoint="[&BBAIAAA=]",
                    game_mode="OpenWorld",
                    requires_expansion="HeartOfThorns",
                ))
            if not has_battle:
                blockers.append("Gift of Battle WvW Reward Track required.")
                actions.append(JourneyAction(
                    action_title="Progress Gift of Battle WvW Track",
                    action_description="Activate the Gift of Battle Reward Track in WvW. Stack Experience Booster + Heroic Booster + Guild Tavern WvW buff to finish in ~4.5h.",
                    estimated_minutes=45,
                    priority="HIGH",
                    game_mode="WvW",
                ))
            if obsidian_pct < 100.0:
                needed_obsidian = 250 - obsidian_count
                blockers.append(f"Need {needed_obsidian} more Obsidian Shards.")
                actions.append(JourneyAction(
                    action_title="Buy Obsidian Shards at Temple of Balthazar or Ley-Energy Converter",
                    action_description=f"Acquire {needed_obsidian} Obsidian Shards via Tactician Deathspark `[&BO4CAAA=]` or HoT Ley-Energy Matter Converter.",
                    estimated_minutes=15,
                    priority="MEDIUM",
                    zone_name="Straits of Devastation",
                    waypoint="[&BO4CAAA=]",
                    npc_name="Tactician Deathspark",
                    game_mode="OpenWorld",
                ))
            status = "COMPLETED" if readiness_pct >= 100.0 else ("IN_PROGRESS" if readiness_pct > 0 else "NOT_STARTED")
            return JourneyPillar(
                pillar_name=mastery_name,
                readiness_pct=round(readiness_pct, 1),
                status=status,
                key_blockers=blockers,
                recommended_actions=actions,
                sub_components=sub_components,
            )

        if gen == "GEN3":
            cantha_gift_id = self._resolve_item_id("Gift of Cantha")
            has_cantha_gift = (cantha_gift_id > 0 and account.total_item_count(cantha_gift_id) > 0) or account.total_item_count(bom["mastery_gift_id"]) > 0
            spirit_shards = account.spirit_shards_count()
            imperial_favor = account.wallet.get(68, 0)
            exp_pct = 100.0 if has_cantha_gift else 0.0
            favor_pct = min(100.0, (imperial_favor / 2500.0) * 100.0)
            bloodstone_pct = 100.0 if (account.has_bloodstone_shard() or spirit_shards >= 200) else min(100.0, (spirit_shards / 200.0) * 100.0)

            sub_components = {
                "Gift of Cantha (4 EoD Map Completions / Lanterns)": exp_pct,
                "2,500x Imperial Favor (Cantha Metas)": favor_pct,
                "Bloodstone Shard & Gift of the Dragon Empire (300 Spirit Shards)": bloodstone_pct,
            }
            readiness_pct = exp_pct * 0.45 + favor_pct * 0.35 + bloodstone_pct * 0.20
            blockers = []
            actions = []
            if not has_cantha_gift:
                blockers.append("Gift of Cantha required (Seitung Province, New Kaineng City, The Echovald Wilds, Dragon's End completion or Lantern Lighting).")
                actions.append(JourneyAction(
                    action_title="Complete Cantha Maps or Light Imperial Lanterns for Gift of Cantha",
                    action_description="Explore Seitung Province, New Kaineng City, Echovald Wilds, and Dragon's End (or light map lanterns after first completion) to earn Gift of Cantha.",
                    estimated_minutes=60,
                    priority="HIGH",
                    zone_name="Seitung Province",
                    waypoint="[&BGUNAAA=]",
                    game_mode="OpenWorld",
                    requires_expansion="EndOfDragons",
                ))
            if favor_pct < 100.0:
                needed_favor = 2500 - imperial_favor
                blockers.append(f"Need {needed_favor} more Imperial Favor for Gift of the Dragon Empire and Jade Mastery.")
                actions.append(JourneyAction(
                    action_title="Farm Imperial Favor via Cantha Meta Events",
                    action_description=f"Run Aetherblade Assault (Seitung), Kaineng Blackout, Gang War (Echovald), and Battle for the Jade Sea to earn {needed_favor} Imperial Favor.",
                    estimated_minutes=45,
                    priority="HIGH",
                    zone_name="Arborstone",
                    waypoint="[&BGUNAAA=]",
                    game_mode="OpenWorld",
                    requires_expansion="EndOfDragons",
                ))
            status = "COMPLETED" if readiness_pct >= 100.0 else ("IN_PROGRESS" if readiness_pct > 0 else "NOT_STARTED")
            return JourneyPillar(
                pillar_name=mastery_name,
                readiness_pct=round(readiness_pct, 1),
                status=status,
                key_blockers=blockers,
                recommended_actions=actions,
                sub_components=sub_components,
            )

        has_exploration = account.total_item_count(self.GIFT_OF_EXPLORATION_ID) > 0
        has_battle = account.has_gift_of_battle()
        obsidian_count = account.total_item_count(self.OBSIDIAN_SHARD_ID)
        bloodstone_count = 1 if account.has_bloodstone_shard() else 0
        spirit_shards = account.spirit_shards_count()

        exp_pct = 100.0 if has_exploration else 0.0
        battle_pct = 100.0 if has_battle else 0.0
        obsidian_pct = min(100.0, (obsidian_count / 250.0) * 100.0)
        bloodstone_pct = 100.0 if (bloodstone_count > 0 or spirit_shards >= 200) else min(100.0, (spirit_shards / 200.0) * 100.0)

        sub_components = {
            "Gift of Exploration (100% Core Tyria)": exp_pct,
            "Gift of Battle (WvW Reward Track)": battle_pct,
            "250x Obsidian Shards": obsidian_pct,
            "Bloodstone Shard (200 Spirit Shards)": bloodstone_pct
        }

        readiness_pct = (
            exp_pct * 0.40 +
            battle_pct * 0.30 +
            obsidian_pct * 0.20 +
            bloodstone_pct * 0.10
        )

        blockers = []
        actions = []

        if not has_exploration:
            blockers.append("100% Core Tyria Map Completion required for Gift of Exploration.")
            mount_tip = "Skyscale" if account.has_mount("skyscale") else ("Raptor" if account.has_mount("raptor") else "No mounts (Core)")
            actions.append(JourneyAction(
                action_title="Progress Core Tyria Map Completion",
                action_description=f"Explore remaining Core Tyria zones. Recommended mount: {mount_tip}.",
                estimated_minutes=60,
                priority="HIGH",
                game_mode="OpenWorld"
            ))

        if not has_battle:
            blockers.append("Gift of Battle WvW Reward Track required.")
            actions.append(JourneyAction(
                action_title="Progress Gift of Battle WvW Track",
                action_description="Activate the Gift of Battle Reward Track in WvW (Edge of the Mists or Borderlands). 🚀 Booster Acceleration: Stack Experience Booster + Heroic Booster + Guild Tavern WvW buff to finish in ~4.5h instead of 8.0h unboosted.",
                estimated_minutes=45,
                priority="HIGH",
                game_mode="WvW"
            ))

        if obsidian_pct < 100.0:
            needed_obsidian = 250 - obsidian_count
            blockers.append(f"Need {needed_obsidian} more Obsidian Shards.")
            actions.append(JourneyAction(
                action_title="Buy Obsidian Shards at Temple of Balthazar",
                action_description=f"Teleport to Straits of Devastation `[&BO4CAAA=]` and purchase {needed_obsidian} Obsidian Shards from Tactician Deathspark (2,100 Karma each, {needed_obsidian * 2100:,} Karma total). If contested, check LFG for an uncontested map taxi using Recharging Teleport to Friend `[&AgHfYAEA]`, or fallback to Silverwastes RIBA/Unbound Magic.",
                estimated_minutes=15,
                priority="MEDIUM",
                zone_name="Straits of Devastation",
                waypoint="[&BO4CAAA=]",
                npc_name="Tactician Deathspark",
                game_mode="OpenWorld"
            ))

        if bloodstone_pct < 100.0 and bloodstone_count == 0:
            needed_ss = 200 - spirit_shards
            blockers.append(f"Need {needed_ss} more Spirit Shards for Bloodstone Shard.")
            actions.append(JourneyAction(
                action_title="Purchase Bloodstone Shard from Miyani (200 Spirit Shards Check)",
                action_description=f"200 Spirit Shard Check: You have {spirit_shards}/200 Spirit Shards (need {needed_ss} more). Farm daily events/meta trains, then exchange 200 Spirit Shards with Miyani at the Mystic Forge `[&BBAEAAA=]` in Lion's Arch.",
                estimated_minutes=5,
                priority="LOW",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                npc_name="Miyani",
                game_mode="Account"
            ))

        status = "COMPLETED" if readiness_pct >= 100.0 else ("IN_PROGRESS" if readiness_pct > 0 else "NOT_STARTED")

        return JourneyPillar(
            pillar_name=mastery_name,
            readiness_pct=round(readiness_pct, 1),
            status=status,
            key_blockers=blockers,
            recommended_actions=actions,
            sub_components=sub_components
        )

    def _evaluate_fortune_pillar(
        self,
        account: AccountState,
        diff_report: AccountDiffReport,
        tp_prices: Dict[int, float],
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True,
        bom: Optional[Dict[str, Any]] = None,
    ) -> JourneyPillar:
        """Evaluates Pillar 3: Economic Tribute (Gift of Fortune, Mystic Tribute, or Draconic Tribute)."""
        if bom is None:
            bom = self._default_bom(account, diff_report)

        tribute_name = bom["tribute_gift_name"]
        req_clovers = int(bom["required_clovers"])
        t6_total_needed = int(bom["required_t6_total"])

        clover_count = account.total_item_count(self.MYSTIC_CLOVER_ID)
        ecto_count = account.total_item_count(self.GLOB_OF_ECTOPLASM_ID)
        t6_owned = sum(account.total_item_count(mat_id) for mat_id in set(self.T6_MATERIAL_IDS + self.LEGACY_T6_MATERIAL_IDS))

        clover_pct = min(100.0, (clover_count / float(req_clovers)) * 100.0)
        ecto_pct = min(100.0, (ecto_count / 250.0) * 100.0)
        t6_pct = min(100.0, (t6_owned / float(t6_total_needed)) * 100.0)

        sub_components = {
            f"{req_clovers}x Mystic Clovers": clover_pct,
            "250x Globs of Ectoplasm": ecto_pct,
            f"T6 Fine Crafting Materials ({t6_total_needed:,} total)": t6_pct
        }

        readiness_pct = (
            clover_pct * 0.40 +
            ecto_pct * 0.20 +
            t6_pct * 0.40
        )

        blockers = []
        actions = []

        if clover_pct < 100.0:
            needed_clovers = req_clovers - clover_count
            blockers.append(f"Need {needed_clovers} more Mystic Clovers.")
            if wizards_vault_exhausted:
                actions.append(JourneyAction(
                    action_title="Purchase Daily Fractal Clovers (BUY-2046)",
                    action_description=f"Purchase 2 daily discounted Mystic Clovers from BUY-2046 at Mistlock Observatory `[&DYEFAAA=]` (150 Fractal Relics + 1 Mystic Coin + 3 Ecto + 2 Spirit Shards each). Supplement with weekly Strike/Raid vendors and Mystic Forge promotion ({needed_clovers} needed total).",
                    estimated_minutes=10,
                    priority="CRITICAL",
                    zone_name="Mistlock Observatory",
                    waypoint="[&DYEFAAA=]",
                    npc_name="BUY-2046",
                    game_mode="Account"
                ))
            else:
                actions.append(JourneyAction(
                    action_title="Claim Wizard's Vault Mystic Clovers",
                    action_description=f"Purchase remaining Mystic Clovers (60 Astral Acclaim each) from the Wizard's Vault or buy 2/day from BUY-2046 in Mistlock Observatory `[&DYEFAAA=]`.",
                    estimated_minutes=10,
                    priority="CRITICAL",
                    game_mode="Account"
                ))

        if ecto_pct < 100.0:
            needed_ectos = 250 - ecto_count
            blockers.append(f"Need {needed_ectos} more Globs of Ectoplasm.")
            actions.append(JourneyAction(
                action_title="Farm Ectos in Silverwastes RIBA Meta",
                action_description=f"Teleport to Camp Resolve `[&BF8HAAA=]` and run the RIBA meta train. Salvage level 68+ Rare gear with Silver-Fed Salvage-o-Matic `[&AgHTBQEA]` or Mystic Salvage Kit for optimal Ectoplasm salvage yield (~0.875 Ecto per salvage).",
                estimated_minutes=45,
                priority="MEDIUM",
                zone_name="The Silverwastes",
                waypoint="[&BF8HAAA=]",
                game_mode="OpenWorld"
            ))

        if t6_pct < 100.0:
            needed_t6 = t6_total_needed - t6_owned
            blockers.append(f"Need {needed_t6} more Tier 6 Fine Crafting Materials.")
            if account.has_expansion("LivingWorldSeason4"):
                actions.append(JourneyAction(
                    action_title="Exchange Volatile Magic for T6 Trophy Shipments",
                    action_description="Teleport to Dragonfall `[&BNoLAAA=]` and exchange 250 Volatile Magic + 1 gold per Trophy Shipment for high-density T6 materials.",
                    estimated_minutes=30,
                    priority="HIGH",
                    zone_name="Dragonfall",
                    waypoint="[&BNoLAAA=]",
                    requires_expansion="LivingWorldSeason4",
                    game_mode="OpenWorld"
                ))
            else:
                actions.append(JourneyAction(
                    action_title="Exchange Laurels for Heavy Crafting Bags",
                    action_description="Visit the Laurel Merchant in Lion's Arch `[&BBAEAAA=]` (1 Laurel = 3 T6 materials) or farm Silverwastes/Drizzlewood.",
                    estimated_minutes=15,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    game_mode="Account"
                ))

        if bom["generation"] == "GEN3":
            ass_id = self._resolve_item_id("Antique Summoning Stone")
            ass_count = account.total_item_count(ass_id) if ass_id > 0 else 0
            if ass_count < 100:
                needed_ass = 100 - ass_count
                blockers.append(f"Need {needed_ass} more Antique Summoning Stones (weekly vendor cap from Leivas in Arborstone).")
                actions.append(JourneyAction(
                    action_title="Purchase Weekly Antique Summoning Stones from Leivas",
                    action_description="Visit Leivas in Arborstone `[&BGUNAAA=]` weekly to exchange Imperial Favor, Karma, Gold, and Unusual Coins for 5x Antique Summoning Stones (time-gated weekly).",
                    estimated_minutes=5,
                    priority="HIGH",
                    zone_name="Arborstone",
                    waypoint="[&BGUNAAA=]",
                    npc_name="Leivas",
                    game_mode="Account",
                    requires_expansion="EndOfDragons",
                ))

        status = "COMPLETED" if readiness_pct >= 100.0 else ("IN_PROGRESS" if readiness_pct > 0 else "NOT_STARTED")

        return JourneyPillar(
            pillar_name=tribute_name,
            readiness_pct=round(readiness_pct, 1),
            status=status,
            key_blockers=blockers,
            recommended_actions=actions,
            sub_components=sub_components
        )

    def _evaluate_twilight_gift_pillar(
        self,
        account: AccountState,
        diff_report: AccountDiffReport,
        tp_prices: Dict[int, float],
        bom: Optional[Dict[str, Any]] = None,
    ) -> JourneyPillar:
        """Evaluates Pillar 4: Weapon-Specific Gift (e.g. Gift of Twilight, Gift of Sunrise, Gift of Bolt, Gift of Nevermore, Gift of Aurene's Bite)."""
        if bom is None:
            bom = self._default_bom(account, diff_report)

        if bom["target_item_id"] != self.TWILIGHT_ID:
            return self._evaluate_specific_gift_pillar_generic(account, diff_report, tp_prices, bom)

        weaponsmith_level = account.max_discipline_rating("weaponsmith")
        armorsmith_level = account.max_discipline_rating("armorsmith")
        runestone_count = account.total_item_count(self.ICY_RUNESTONE_ID) + account.total_item_count(19912)
        lodestone_count = account.total_item_count(self.ONYX_LODESTONE_ID)
        sigil_count = account.total_item_count(self.SUPERIOR_SIGIL_OF_STRENGTH_ID) + (
            account.total_item_count(self.SUPERIOR_SIGIL_OF_FORCE_ID) if self.SUPERIOR_SIGIL_OF_FORCE_ID != self.SUPERIOR_SIGIL_OF_STRENGTH_ID else 0
        )

        disc_pct = ((min(400, weaponsmith_level) / 400.0) + (min(400, armorsmith_level) / 400.0)) / 2.0 * 100.0
        runestone_pct = min(100.0, (runestone_count / 100.0) * 100.0)
        lodestone_pct = min(100.0, (lodestone_count / 100.0) * 100.0)
        sigil_pct = 100.0 if sigil_count > 0 else 0.0

        sub_components = {
            "Weaponsmith 400 & Armorsmith 400": disc_pct,
            "100x Icy Runestones (100g flat)": runestone_pct,
            "100x Onyx Lodestones": lodestone_pct,
            "Superior Sigil of Force": sigil_pct
        }

        readiness_pct = (
            disc_pct * 0.20 +
            runestone_pct * 0.30 +
            lodestone_pct * 0.40 +
            sigil_pct * 0.10
        )

        blockers = []
        actions = []

        ws_char = None
        as_char = None
        for char in account.characters:
            if not isinstance(char, dict):
                continue
            char_name = char.get("name", "")
            raw_discs = char.get("crafting", []) or char.get("disciplines", [])
            discs = {d.get("discipline", "").lower(): d.get("rating", 0) for d in raw_discs if isinstance(d, dict)}
            if discs.get("weaponsmith", 0) >= 400 and not ws_char:
                ws_char = char_name
            if discs.get("armorsmith", 0) >= 400 and not as_char:
                as_char = char_name
        for char_name, disc_map in account.character_disciplines.items():
            if not isinstance(disc_map, dict):
                continue
            for d_key, d_val in disc_map.items():
                rating = int(d_val.get("rating", 0)) if isinstance(d_val, dict) else (int(d_val) if isinstance(d_val, (int, float)) else 0)
                if d_key.lower() == "weaponsmith" and rating >= 400 and not ws_char:
                    ws_char = char_name
                if d_key.lower() == "armorsmith" and rating >= 400 and not as_char:
                    as_char = char_name

        if weaponsmith_level < 400:
            blockers.append(f"Weaponsmith level 400 required (current: {weaponsmith_level}).")
            actions.append(JourneyAction(
                action_title="Level Weaponsmith to 400",
                action_description="Visit Weaponsmithing station in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]` (costs ~15-20g).",
                estimated_minutes=20,
                priority="HIGH",
                zone_name="Black Citadel",
                waypoint="[&BKgDAAA=]",
                game_mode="Crafting"
            ))
        elif ws_char and as_char and ws_char != as_char:
            actions.append(JourneyAction(
                action_title=f"👤 Switch to {ws_char} for Weaponsmith crafting",
                action_description=f"Log in as {ws_char} for Weaponsmith 400 crafting in Black Citadel `[&BKgDAAA=]`.",
                estimated_minutes=5,
                priority="LOW",
                zone_name="Black Citadel",
                waypoint="[&BKgDAAA=]",
                game_mode="Account",
                assigned_character=ws_char
            ))

        if armorsmith_level < 400:
            blockers.append(f"Armorsmith level 400 required (current: {armorsmith_level}).")
            actions.append(JourneyAction(
                action_title="Level Armorsmith to 400",
                action_description="Visit Armorsmithing station in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]` (costs ~15-20g).",
                estimated_minutes=20,
                priority="HIGH",
                zone_name="Black Citadel",
                waypoint="[&BKgDAAA=]",
                game_mode="Crafting"
            ))
        elif ws_char and as_char and ws_char != as_char:
            actions.append(JourneyAction(
                action_title=f"👤 Switch to {as_char} for Armorsmith crafting",
                action_description=f"Log in as {as_char} for Armorsmith 400 crafting in Black Citadel `[&BKgDAAA=]`.",
                estimated_minutes=5,
                priority="LOW",
                zone_name="Black Citadel",
                waypoint="[&BKgDAAA=]",
                game_mode="Account",
                assigned_character=as_char
            ))

        if runestone_pct < 100.0:
            needed_runes = 100 - runestone_count
            blockers.append(f"Need {needed_runes} more Icy Runestones ({needed_runes} gold).")
            actions.append(JourneyAction(
                action_title="Purchase Icy Runestones from Rojan",
                action_description=f"Teleport to Earthshake Waypoint `[&BHsBAAA=]` in Frostgorge Sound and buy {needed_runes} Icy Runestones from Rojan the Penitent for {needed_runes} gold.",
                estimated_minutes=5,
                priority="MEDIUM",
                zone_name="Frostgorge Sound",
                waypoint="[&BHsBAAA=]",
                npc_name="Rojan the Penitent",
                game_mode="OpenWorld"
            ))

        if lodestone_pct < 100.0:
            needed_lodes = 100 - lodestone_count
            blockers.append(f"Need {needed_lodes} more Onyx Lodestones.")
            actions.append(JourneyAction(
                action_title="Farm Onyx Cores for Mystic Forge Promotion (Arbitrage)",
                action_description="Run Twilight Arbor Aetherpath `[&BEEFAAA=]` or Crucible of Eternity `[&BDoCAAA=]` for Onyx Cores, then promote in Mystic Forge (2x Cores + 1x Dust + 1x Crystal/Powder + 1x Wine) to save ~50% gold over buying Onyx Lodestones directly.",
                estimated_minutes=40,
                priority="HIGH",
                zone_name="Caledon Forest",
                waypoint="[&BEEFAAA=]",
                game_mode="Dungeon"
            ))

        status = "COMPLETED" if readiness_pct >= 100.0 else ("IN_PROGRESS" if readiness_pct > 0 else "NOT_STARTED")

        return JourneyPillar(
            pillar_name="Gift of Twilight",
            readiness_pct=round(readiness_pct, 1),
            status=status,
            key_blockers=blockers,
            recommended_actions=actions,
            sub_components=sub_components
        )

    def _evaluate_specific_gift_pillar_generic(
        self,
        account: AccountState,
        diff_report: AccountDiffReport,
        tp_prices: Dict[int, float],
        bom: Dict[str, Any],
    ) -> JourneyPillar:
        """Ontology-driven evaluation for Pillar 4 for any non-Twilight legendary weapon."""
        specific_name = bom["specific_gift_name"]
        gen = bom["generation"]
        sub_gifts = bom.get("sub_gifts", [])
        dungeon_name = bom.get("dungeon_gift_name")

        blockers: List[str] = []
        actions: List[JourneyAction] = []
        sub_components: Dict[str, float] = {}

        if gen in ("GEN1", "GEN2"):
            runestone_count = account.total_item_count(self.ICY_RUNESTONE_ID) + account.total_item_count(19912)
            runestone_pct = min(100.0, (runestone_count / 100.0) * 100.0)
            sub_components["100x Icy Runestones (100g flat)"] = runestone_pct
            if runestone_pct < 100.0:
                needed_runes = 100 - runestone_count
                blockers.append(f"Need {needed_runes} more Icy Runestones ({needed_runes} gold).")
                actions.append(JourneyAction(
                    action_title="Purchase Icy Runestones from Rojan",
                    action_description=f"Teleport to Earthshake Waypoint `[&BHsBAAA=]` in Frostgorge Sound and buy {needed_runes} Icy Runestones from Rojan the Penitent for {needed_runes} gold.",
                    estimated_minutes=5,
                    priority="MEDIUM",
                    zone_name="Frostgorge Sound",
                    waypoint="[&BHsBAAA=]",
                    npc_name="Rojan the Penitent",
                    game_mode="OpenWorld"
                ))
        elif gen == "GEN3":
            jade_runestone_id = self._resolve_item_id("Jade Runestone")
            ambergris_id = self._resolve_item_id("Chunk of Ancient Ambergris")
            jade_runestones = account.total_item_count(jade_runestone_id) if jade_runestone_id > 0 else 0
            ambergris = account.total_item_count(ambergris_id) if ambergris_id > 0 else 0
            jr_pct = min(100.0, (jade_runestones / 100.0) * 100.0)
            amb_pct = min(100.0, (ambergris / 100.0) * 100.0)
            sub_components["100x Jade Runestones"] = jr_pct
            sub_components["100x Chunk of Ancient Ambergris"] = amb_pct
            if jr_pct < 100.0:
                needed_jr = 100 - jade_runestones
                blockers.append(f"Need {needed_jr} more Jade Runestones.")
                actions.append(JourneyAction(
                    action_title="Farm Jade Runestones in Kaineng & Echovald",
                    action_description=f"Open daily Magnificent Chests in New Kaineng City, Echovald Wilds, and Seitung Province (or buy from TP) for {needed_jr} Jade Runestones.",
                    estimated_minutes=25,
                    priority="HIGH",
                    zone_name="New Kaineng City",
                    waypoint="[&BGUNAAA=]",
                    game_mode="OpenWorld",
                    requires_expansion="EndOfDragons",
                ))
            if amb_pct < 100.0:
                needed_amb = 100 - ambergris
                blockers.append(f"Need {needed_amb} more Chunks of Ancient Ambergris.")
                actions.append(JourneyAction(
                    action_title="Acquire Chunks of Ancient Ambergris (Fishing / Leviathan Farm)",
                    action_description=f"Farm Seitung/Kaineng Leviathan events, complete daily EoD fishing catch quests in Arborstone `[&BGUNAAA=]`, or purchase {needed_amb} Ancient Ambergris on the Trading Post.",
                    estimated_minutes=30,
                    priority="HIGH",
                    zone_name="Seitung Province",
                    waypoint="[&BGUNAAA=]",
                    game_mode="OpenWorld",
                    requires_expansion="EndOfDragons",
                ))

        for sg_id, sg_name in sub_gifts:
            has_sg = account.total_item_count(sg_id) > 0
            sub_components[sg_name] = 100.0 if has_sg else 0.0
            if not has_sg:
                blockers.append(f"Sub-gift '{sg_name}' required for {specific_name}.")
                actions.append(JourneyAction(
                    action_title=f"Craft {sg_name}",
                    action_description=f"Craft '{sg_name}' at your crafting station (400/500 rating) or Mystic Forge for {specific_name}.",
                    estimated_minutes=15,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    game_mode="Crafting",
                ))

        if dungeon_name:
            tales = account.dungeon_tales_count()
            has_dg = bom.get("dungeon_gift_id") and account.total_item_count(bom["dungeon_gift_id"]) > 0
            dg_pct = 100.0 if has_dg else min(100.0, (tales / 500.0) * 100.0)
            sub_components[f"{dungeon_name} (500 Tales of Dungeon Delving)"] = dg_pct
            if dg_pct < 100.0:
                actions.append(JourneyAction(
                    action_title=f"Acquire {dungeon_name} (Dungeon Vendor)",
                    action_description=f"Run explorable dungeon paths to earn 500 Tales of Dungeon Delving (currently {tales}/500) and purchase {dungeon_name} in Lion's Arch `[&BBAEAAA=]`.",
                    estimated_minutes=35,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    game_mode="Dungeon",
                ))

        readiness_pct = sum(sub_components.values()) / max(1, len(sub_components))
        status = "COMPLETED" if readiness_pct >= 100.0 else ("IN_PROGRESS" if readiness_pct > 0 else "NOT_STARTED")
        return JourneyPillar(
            pillar_name=specific_name,
            readiness_pct=round(readiness_pct, 1),
            status=status,
            key_blockers=blockers,
            recommended_actions=actions,
            sub_components=sub_components,
        )

    def _build_exploration_plan(
        self,
        account: AccountState,
        bom: Optional[Dict[str, Any]] = None,
    ) -> List[ExplorationPlan]:
        """Builds mount-aware regional map completion strategy dynamically from priory:ExplorationRegion triples."""
        if bom is None:
            bom = self._default_bom(account)

        has_skyscale = account.has_mount("skyscale")
        has_raptor = account.has_mount("raptor")
        has_springer = account.has_mount("springer")

        if has_skyscale:
            speed_factor = 0.5
        elif has_raptor or has_springer:
            speed_factor = 0.75
        else:
            speed_factor = 1.0

        gen = bom["generation"]
        store = self.store or _get_or_init_default_store()

        # Resolve canonical region prefLabels from priory:RegionScheme (e.g. Shiverpeaks -> Shiverpeak Mountains)
        canonical_region_labels: List[str] = []
        q_scheme = """
        SELECT ?pref WHERE {
            ?concept skos:inScheme priory:RegionScheme ;
                     skos:prefLabel ?pref .
        }
        """
        for r in store.query(q_scheme):
            if r.get("pref"):
                lbl = str(r["pref"]).strip()
                if "/" not in lbl and lbl not in canonical_region_labels:
                    canonical_region_labels.append(lbl)

        def _canonicalize_region_name(raw_label: str) -> str:
            base = raw_label.split(" (")[0].strip()
            stem = base[:-1].lower() if base.lower().endswith("s") else base.lower()
            for pref in canonical_region_labels:
                if pref.lower() == base.lower():
                    return pref
            for pref in canonical_region_labels:
                if pref.lower().startswith(stem):
                    return pref
            return base

        raw_regions: List[Dict[str, Any]] = []
        if hasattr(store, "get_exploration_regions"):
            try:
                raw_regions = list(store.get_exploration_regions(gen) or [])
            except Exception:
                raw_regions = []

        if not raw_regions:
            q_exp = """
            SELECT ?region ?label ?gen ?order ?zones ?hours ?diff ?recMount ?fbMount ?notes ?wp WHERE {
                ?region a priory:ExplorationRegion ;
                        rdfs:label ?label ;
                        priory:regionOrder ?order ;
                        priory:zoneCount ?zones ;
                        priory:baseExplorationHours ?hours ;
                        priory:explorationDifficulty ?diff ;
                        priory:recommendedMount ?recMount ;
                        priory:strategyNotes ?notes ;
                        priory:startingWaypoint ?wp .
                OPTIONAL { ?region priory:appliesToGeneration ?gen }
                OPTIONAL { ?region priory:fallbackMount ?fbMount }
            } ORDER BY ASC(?order)
            """
            for r in store.query(q_exp):
                r_gen = str(r.get("gen") or "GEN1").upper()
                if r_gen != gen.upper():
                    continue
                raw_regions.append({
                    "region_name": str(r.get("label", "")),
                    "zone_count": int(r["zones"]) if r.get("zones") is not None else 1,
                    "base_hours": float(r["hours"]) if r.get("hours") is not None else 1.5,
                    "difficulty": str(r.get("diff", "Moderate")),
                    "recommended_mount": str(r["recMount"]) if r.get("recMount") else None,
                    "fallback_mount": str(r["fbMount"]) if r.get("fbMount") else None,
                    "strategy_notes": str(r.get("notes", "")),
                    "starting_waypoint": str(r.get("wp", "")),
                })

        plans: List[ExplorationPlan] = []
        for reg in raw_regions:
            raw_name = str(reg.get("region_name") or reg.get("label") or "")
            region_name = _canonicalize_region_name(raw_name)
            zone_count = int(reg.get("zone_count") or reg.get("zones") or 1)
            base_hours = float(reg.get("base_hours") if reg.get("base_hours") is not None else reg.get("estimated_hours", 1.5))
            difficulty = str(reg.get("difficulty") or "Moderate")
            rec_m = str(reg.get("recommended_mount") or "").strip()
            fb_m = str(reg.get("fallback_mount") or "").strip()

            chosen_mount: Optional[str] = None
            if rec_m and rec_m.lower() != "walk" and account.has_mount(rec_m.lower()):
                chosen_mount = rec_m
            elif fb_m and fb_m.lower() != "walk" and account.has_mount(fb_m.lower()):
                chosen_mount = fb_m

            wp_raw = str(reg.get("starting_waypoint") or "")
            wp_match = re.search(r"(\[&[^\]]+\])", wp_raw)
            starting_wp = wp_match.group(1) if wp_match else wp_raw

            plans.append(
                ExplorationPlan(
                    region_name=region_name,
                    zone_count=zone_count,
                    estimated_hours=round(base_hours * speed_factor, 1),
                    difficulty=difficulty,
                    recommended_mount=chosen_mount,
                    strategy_notes=str(reg.get("strategy_notes") or ""),
                    starting_waypoint=starting_wp,
                )
            )

        return plans

    def _generate_precursor_strategies(
        self,
        account: AccountState,
        tp_prices: Dict[int, float],
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True,
        bom: Optional[Dict[str, Any]] = None,
    ) -> List[PrecursorStrategy]:
        """Generates comparative triage for precursor acquisition pathways based on ontology precursor class."""
        if bom is None:
            bom = self._default_bom(account)

        prec_id = bom["precursor_id"]
        prec_name = bom["precursor_name"]
        target_name = bom["target_item_name"]
        gen = bom["generation"]

        if gen == "GEN2":
            return [
                PrecursorStrategy(
                    strategy_name=f"Grandmaster Hobbs 4-Tier Collection ({target_name} I, II, III, IV -> {prec_name})",
                    estimated_gold_cost=340.0,
                    estimated_hours=24.0,
                    pros=[
                        f"Only acquisition method for account-bound Gen 2 precursor {prec_name}",
                        f"Guaranteed progression through {target_name} I-IV collection tiers",
                    ],
                    cons=[
                        "Account-bound (cannot be bought on Trading Post or from Wizard's Vault Starter Kit)",
                        "Requires Heart of Thorns Mastery and Spiritwood / Deldrimor / Elonian time-gated materials",
                    ],
                    is_recommended=True,
                    requires_expansion="HeartOfThorns",
                    vendor_npc="Grandmaster Craftsman Hobbs",
                    waypoint="[&BBAEAAA=]",
                )
            ]

        if gen == "GEN3":
            prec_price = tp_prices.get(prec_id, 380.0)
            return [
                PrecursorStrategy(
                    strategy_name=f"Trading Post Direct Purchase ({prec_name})",
                    estimated_gold_cost=prec_price,
                    estimated_hours=0.1,
                    pros=[
                        f"Instant acquisition (~{int(prec_price)}g)",
                        "Saves 5x Antique Summoning Stones and 100x Memories of Aurene for Draconic Tribute",
                    ],
                    cons=[f"Upfront gold investment (~{int(prec_price)}g)"],
                    is_recommended=True,
                    waypoint="[&BBAEAAA=]",
                ),
                PrecursorStrategy(
                    strategy_name=f"Arborstone Leivas Crafting ({prec_name})",
                    estimated_gold_cost=350.0,
                    estimated_hours=6.0,
                    pros=[
                        "Craft directly at rank 500 using Cantha materials and Memories of Aurene",
                    ],
                    cons=[
                        "Consumes 5x Antique Summoning Stones (weekly time-gate) and 25x Tales of Adventure",
                    ],
                    is_recommended=False,
                    requires_expansion="EndOfDragons",
                    vendor_npc="Leivas",
                    waypoint="[&BGUNAAA=]",
                ),
            ]

        prec_price = tp_prices.get(prec_id, 141.0 if (optimize_for_cost or wizards_vault_exhausted) else 320.0)
        starter_kit_in_bank = any(account.total_item_count(cid) > 0 for cid in [100000, 100001, 100002, 100003])
        sub_gift_hint = bom["sub_gifts"][0][1] if bom.get("sub_gifts") else "Gift of Metal"

        prereq, has_bit_progress, missing_bits_summary = self._get_precursor_collection_bit_status(bom["target_item_id"], account)
        hobbs_pros = [
            "Engaging lore and progression across 3 Hobbs Tiers",
            "Tier 1 (Weaponsmith 450, 30x Deldrimor Steel) -> Tier 2 (Weaponsmith 450, 35x Deldrimor Steel) -> Tier 3 (Weaponsmith 500, 27 Gloom locations)"
        ]
        if has_bit_progress and prereq and missing_bits_summary:
            hobbs_pros.append(missing_bits_summary)

        strats = [
            PrecursorStrategy(
                strategy_name="Wizard's Vault Legendary Starter Kit",
                estimated_gold_cost=0.0,
                estimated_hours=0.1,
                pros=["0 gold cost", f"Also grants {sub_gift_hint} and crafting materials", "Guaranteed unlock"],
                cons=["Wizard's Vault seasonal Starter Kit is exhausted / already claimed"] if wizards_vault_exhausted else ["Requires active seasonal kit selection (1,200 Astral Acclaim)"],
                is_recommended=(not wizards_vault_exhausted) and (starter_kit_in_bank or account.has_expansion("SecretsOfTheObscure")),
                requires_expansion="SecretsOfTheObscure",
                waypoint="[&BBAEAAA=]"
            ),
            PrecursorStrategy(
                strategy_name="Trading Post Direct Purchase",
                estimated_gold_cost=prec_price,
                estimated_hours=0.1,
                pros=[
                    f"Instant acquisition (~{int(prec_price)}g)",
                    "Cheaper than Grandmaster Hobbs collection materials (~210g)",
                    "Zero crafting or collection time (saves ~30 hours)"
                ],
                cons=[f"High gold investment (~{int(prec_price)}g)"],
                is_recommended=wizards_vault_exhausted or (not starter_kit_in_bank and not account.has_expansion("SecretsOfTheObscure")),
                waypoint="[&BBAEAAA=]"
            ),
            PrecursorStrategy(
                strategy_name=f"Grandmaster Hobbs Collection ({prec_name} I, II, III)",
                estimated_gold_cost=210.0,
                estimated_hours=30.0,
                pros=hobbs_pros,
                cons=[
                    "Costs ~210g in materials (more expensive than TP buy at ~141g)",
                    "Time intensive (~30 hours)",
                    "Requires Central Tyria Legendary Crafting Mastery Tiers 1-3 (Revered Antiquarian, Magister of Legends, Historian of the Armaments)",
                    "Requires 27 Gloom extractions (Fractals, Tequatl, Shadow Behemoth, Silverwastes Labyrinth/Breaches, mini-dungeons)"
                ],
                is_recommended=False,
                requires_expansion="HeartOfThorns",
                vendor_npc="Grandmaster Craftsman Hobbs",
                waypoint="[&BBAEAAA=]"
            ),
            PrecursorStrategy(
                strategy_name="Mystic Forge Rare Greatsword Promotion" if bom["target_item_id"] == self.TWILIGHT_ID else f"Mystic Forge Rare Weapon Promotion ({prec_name})",
                estimated_gold_cost=250.0,
                estimated_hours=1.0,
                pros=["Small chance of instant jackpot"],
                cons=["RNG dependent (~2% yield rate)", "High risk of heavy net gold loss"],
                is_recommended=False,
                waypoint="[&BBAEAAA=]"
            )
        ]

        return strats

    def _find_mobility_character_name(self, account: AccountState) -> str:
        """Finds primary mobility character name from eligible exploration characters."""
        eligible = account.eligible_exploration_characters()
        if not eligible and account.characters:
            ontology_chars = self._get_ontology_characters()
            char_names = [
                (c.get("name") if isinstance(c, dict) else str(c))
                for c in account.characters
                if (isinstance(c, dict) and c.get("name")) or isinstance(c, str)
            ]
            if ontology_chars and ontology_chars[0] in char_names:
                eligible = [c for c in ontology_chars if not account.is_character_map_completed(c)]
        if not eligible:
            if account.characters:
                first_char = account.characters[0]
                if isinstance(first_char, dict) and first_char.get("name"):
                    return str(first_char.get("name"))
                elif isinstance(first_char, str):
                    return first_char
            return "Any Level 80 Character"

        # Check structured characters if available
        if account.characters:
            # 1. Look for high mobility professions (Thief, Ranger, Mesmer, Guardian) among eligible
            for c in account.characters:
                if isinstance(c, dict):
                    name = c.get("name")
                    if name in eligible and c.get("profession") in ["Thief", "Ranger", "Mesmer", "Guardian"]:
                        return name
            # 2. Look for any character among eligible
            for c in account.characters:
                if isinstance(c, dict):
                    name = c.get("name")
                    if name in eligible:
                        return name

        # 3. Query ontology roster characters in order
        for pref in self._get_ontology_characters():
            if pref in eligible:
                return pref

        return eligible[0]

    def _generate_session_itinerary(
        self,
        pillars: List[JourneyPillar],
        time_budget_minutes: int,
        account: AccountState,
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True,
        excluded_modes: Optional[List[str]] = None,
        preferred_modes: Optional[List[str]] = None,
        bom: Optional[Dict[str, Any]] = None,
    ) -> List[JourneyAction]:
        """Prioritizes and fits concrete progression actions into the player's time budget."""
        if bom is None:
            bom = self._default_bom(account)

        excluded_set = set()
        if excluded_modes:
            for m in excluded_modes:
                m_low = m.lower().strip()
                excluded_set.add(m_low)
                if m_low in ("dungeon", "dungeons"):
                    excluded_set.add("dungeon")
                    excluded_set.add("dungeons")
                if m_low in ("fractal", "fractals"):
                    excluded_set.add("fractal")
                    excluded_set.add("fractals")

        def _is_mode_excluded(action_mode: Optional[str]) -> bool:
            if not action_mode or not excluded_set:
                return False
            return action_mode.lower().strip() in excluded_set

        if (optimize_for_cost or wizards_vault_exhausted) and bom["target_item_id"] == self.TWILIGHT_ID:
            mobility_char = self._find_mobility_character_name(account)
            if account.has_mount("skyscale"):
                mount_str: Optional[str] = "Skyscale"
                mount_phrase = f" with {mount_str}"
            elif account.has_mount("raptor"):
                mount_str = "Raptor"
                mount_phrase = f" with {mount_str}"
            else:
                mount_str = None
                mount_phrase = ""

            candidates = [
                JourneyAction(
                    action_title="BUY-2046 Daily Clovers (Mistlock Observatory [&DYEFAAA=])",
                    action_description="Purchase 2 daily discounted Mystic Clovers from BUY-2046 at Mistlock Observatory [&DYEFAAA=] (150 Fractal Relics + 1 Mystic Coin + 3 Ecto + 2 Spirit Shards each).",
                    estimated_minutes=10,
                    priority="CRITICAL",
                    zone_name="Mistlock Observatory",
                    waypoint="[&DYEFAAA=]",
                    npc_name="BUY-2046",
                    game_mode="Account"
                ),
                JourneyAction(
                    action_title="Ascalonian Catacombs dungeon run for Tales of Dungeon Delving [&BIcBAAA=]",
                    action_description="Run AC explorable paths to earn Tales of Dungeon Delving for Gift of Ascalon (500 Tales needed, 0 gold cost).",
                    estimated_minutes=25,
                    priority="HIGH",
                    zone_name="Plains of Ashford",
                    waypoint="[&BIcBAAA=]",
                    game_mode="Dungeon"
                ),
                JourneyAction(
                    action_title="Onyx Core Mystic Forge Promotion [&BBAEAAA=]",
                    action_description="Promote Onyx Cores into Onyx Lodestones at Miyani [&BBAEAAA=] in Lion's Arch (2x Cores + 1x Crystalline Dust + 1x Philosopher's Stone + 1x Bottle of Elonian Wine), saving ~19.6g over buying lodestones directly.",
                    estimated_minutes=10,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Miyani",
                    game_mode="Crafting"
                ),
                JourneyAction(
                    action_title=f"Core Tyria Map Completion on {mobility_char}{mount_phrase}",
                    action_description=f"Progress Core Tyria map completion on your primary mobility character ({mobility_char}){mount_phrase}. 100% completion awards 2x Gifts of Exploration (satisfying Twilight and providing a spare for your next Gen 1 legendary).",
                    estimated_minutes=45,
                    priority="HIGH",
                    game_mode="OpenWorld",
                    recommended_mount=mount_str,
                    assigned_character=mobility_char
                )
            ]

            candidates = [c for c in candidates if not _is_mode_excluded(c.game_mode)]

            itinerary = []
            budget_remaining = time_budget_minutes

            for idx, action in enumerate(candidates):
                if budget_remaining <= 0:
                    break
                if idx < len(candidates) - 1:
                    if action.estimated_minutes <= budget_remaining:
                        itinerary.append(action)
                        budget_remaining -= action.estimated_minutes
                    elif budget_remaining >= 5:
                        itinerary.append(action.model_copy(update={"estimated_minutes": budget_remaining}))
                        budget_remaining = 0
                else:
                    time_to_assign = min(action.estimated_minutes, budget_remaining) if budget_remaining <= 45 else budget_remaining
                    itinerary.append(action.model_copy(update={"estimated_minutes": time_to_assign}))
                    budget_remaining = 0

            return itinerary

        all_actions: List[JourneyAction] = []
        for pillar in pillars:
            for act in pillar.recommended_actions:
                if not _is_mode_excluded(act.game_mode):
                    all_actions.append(act)

        preferred_set = {m.lower().strip() for m in (preferred_modes or [])}
        priority_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        all_actions.sort(
            key=lambda a: (
                0 if (a.game_mode and a.game_mode.lower().strip() in preferred_set) else 1,
                priority_rank.get(a.priority, 99),
            )
        )

        itinerary = []
        budget_remaining = time_budget_minutes

        for action in all_actions:
            if budget_remaining <= 0:
                break
            if action.estimated_minutes <= budget_remaining:
                itinerary.append(action)
                budget_remaining -= action.estimated_minutes
            elif budget_remaining >= 5:
                partial_action = action.model_copy(update={"estimated_minutes": budget_remaining})
                itinerary.append(partial_action)
                budget_remaining = 0

        return itinerary

    def _check_expansion_access(
        self,
        account: AccountState,
        bom: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Identifies locked shortcuts and warnings based on account expansion ownership."""
        if bom is None:
            bom = self._default_bom(account)
        warnings = []
        if bom["generation"] == "GEN2" and not account.has_expansion("HeartOfThorns"):
            warnings.append("⚠️ **Heart of Thorns Required:** Gen 2 Legendary Weapons require Heart of Thorns Masteries and Maguuma Map Completion.")
        if bom["generation"] == "GEN3" and not account.has_expansion("EndOfDragons"):
            warnings.append("⚠️ **End of Dragons Required:** Gen 3 Aurene Legendary Weapons require End of Dragons Masteries, Arborstone, and Cantha Map Completion.")
        if not account.has_expansion("PathOfFire") and not account.has_expansion("EndOfDragons"):
            warnings.append("⚠️ **No Mount Access (PathOfFire / EndOfDragons missing):** Core Tyria map completion will take ~18-21h on foot vs ~8-10h with mounts.")
        if not account.has_expansion("LivingWorldSeason4"):
            warnings.append("💡 **Living World Season 4 Missing:** Volatile Magic Trophy Shipments (Dragonfall `[&BNoLAAA=]`) are unavailable. Use Laurel bags or Silverwastes RIBA for T6 materials.")
        if not account.has_expansion("SecretsOfTheObscure"):
            warnings.append("ℹ️ **Secrets of the Obscure Missing:** Seasonal Wizard's Vault Starter Kits and discounted Astral Clovers may be restricted.")
        return warnings

    def _find_best_character(self, account: AccountState) -> Optional[str]:
        """Identifies the player character best suited for Twilight crafting based on active disciplines."""
        best_ws = None
        best_as = None
        for char in account.characters:
            if not isinstance(char, dict):
                continue
            char_name = char.get("name", "")
            raw_discs = char.get("crafting", []) or char.get("disciplines", [])
            discs = {d.get("discipline", "").lower(): d.get("rating", 0) for d in raw_discs if isinstance(d, dict)}
            ws_level = discs.get("weaponsmith", 0)
            as_level = discs.get("armorsmith", 0)
            if ws_level >= 400:
                best_ws = char_name
            if as_level >= 400:
                best_as = char_name
            if ws_level >= 400 and as_level >= 400:
                return f"{char_name} (Weaponsmith {ws_level}, Armorsmith {as_level})"

        for char_name, disc_map in account.character_disciplines.items():
            if not isinstance(disc_map, dict):
                continue
            ws_level = 0
            as_level = 0
            for d_key, d_val in disc_map.items():
                rating = int(d_val.get("rating", 0)) if isinstance(d_val, dict) else (int(d_val) if isinstance(d_val, (int, float)) else 0)
                if d_key.lower() == "weaponsmith":
                    ws_level = rating
                elif d_key.lower() == "armorsmith":
                    as_level = rating
            if ws_level >= 400 and not best_ws:
                best_ws = char_name
            if as_level >= 400 and not best_as:
                best_as = char_name
            if ws_level >= 400 and as_level >= 400:
                return f"{char_name} (Weaponsmith {ws_level}, Armorsmith {as_level})"

        if best_ws and best_as and best_ws != best_as:
            return f"Split: {best_ws} (Weaponsmith) / {best_as} (Armorsmith)"
        elif best_ws:
            return f"{best_ws} (Weaponsmith)"
        elif best_as:
            return f"{best_as} (Armorsmith)"
            
        return None

    def _build_master_chapters(
        self,
        account: AccountState,
        tp_prices: Dict[int, float],
        diff_report: AccountDiffReport,
        wizards_vault_exhausted: bool = False,
        optimize_for_cost: bool = True,
        bom: Optional[Dict[str, Any]] = None,
    ) -> List[JourneyChapter]:
        """Builds the 4-Chapter Master Sequencer for the Legendary Journey."""
        if bom is None:
            bom = self._default_bom(account, diff_report)

        if bom["target_item_id"] != self.TWILIGHT_ID:
            return self._build_master_chapters_generic(
                account=account,
                tp_prices=tp_prices,
                diff_report=diff_report,
                wizards_vault_exhausted=wizards_vault_exhausted,
                optimize_for_cost=optimize_for_cost,
                bom=bom,
            )

        chapters = []
        
        # --- Chapter 1: The Precursor Decision (Dusk) ---
        owned_dusk = account.total_item_count(self.DUSK_ID)
        has_twilight = account.has_legendary_unlocked(self.TWILIGHT_ID)
        astral_acclaim = account.astral_acclaim_count()
        gold = account.gold_count()
        dusk_price = tp_prices.get(self.DUSK_ID, 141.0 if (optimize_for_cost or wizards_vault_exhausted) else 320.0)
        
        c1_actions = []
        c1_status = "NOT_STARTED"
        c1_readiness = 0.0
        
        # Check Central Tyria mastery prerequisite for Hobbs collection
        hobbs_mastery_query = """
        SELECT ?trackId ?trackLabel ?reqLvl WHERE {
            item:vendor_hobbs priory:requiresMasteryTrack ?track .
            ?track priory:masteryId ?trackId .
            OPTIONAL { item:vendor_hobbs priory:requiredMasteryLevel ?reqLvl }
            OPTIONAL { ?track rdfs:label ?trackLabel }
        } LIMIT 1
        """
        hobbs_res = self.store.query(hobbs_mastery_query)
        track_id = int(hobbs_res[0]["trackId"]) if hobbs_res else 10
        track_label = str(hobbs_res[0].get("trackLabel", "Legendary Crafting")) if hobbs_res else "Legendary Crafting"
        crafting_mastery = account.masteries.get(track_id, 0)
        mastery_warning = ""
        if crafting_mastery < 3:
            mastery_warning = f" ⚠️ Requires Central Tyria Mastery '{track_label}' (Tiers 1-3: Revered Antiquarian, Magister of Armaments, Historian of Armaments; current level: {crafting_mastery}/3)."

        hobbs_action_desc = (
            f"Grandmaster Craftsman Hobbs `[&BBAEAAA=]` Precursor Collection Tiers (Central Tyria '{track_label}' Status: {crafting_mastery}/3):\n"
            f"       • Tier 1: 'Dusk I: The Experimental Nightsword' (Requires {track_label} Tier 1 - Revered Antiquarian) -> Craft Experimental Greatsword Blade/Hilt and gather gloom essences across Central Tyria.\n"
            f"       • Tier 2: 'Dusk II: The Perfected Nightsword' (Requires {track_label} Tier 2 - Magister of Armaments) -> Craft Weighted Greatsword Blade/Hilt (250x each of Iron, Darksteel, Mithril, Orichalcum ingots + Elonian Leather & Spiritwood).\n"
            f"       • Tier 3: 'Dusk III: Dusk' (Requires {track_label} Tier 3 - Historian of Armaments) -> Harvest Darkness essences from Shadow of the Dragon, Tequatl, and Ascalonian Catacombs to forge final precursor Dusk.\n"
            f"       💡 Trade-off: Costs ~210g materials + ~30h gameplay time vs ~{dusk_price:.1f}g instant Trading Post purchase.{mastery_warning}"
        )

        if owned_dusk > 0 or has_twilight:
            c1_status = "COMPLETED"
            c1_readiness = 100.0
        elif wizards_vault_exhausted:
            c1_actions.append(JourneyAction(
                action_title="Buy Dusk from Trading Post (Cheapest Route)",
                action_description=(
                    f"Trading Post buy for Dusk (~{dusk_price:.0f}g) is cheaper and faster than Grandmaster Hobbs collection materials (~210g across Tiers 1-3). "
                    f"Grandmaster Hobbs collection requires ~210g in Deldrimor Steel (65x ingots), Spiritwood, Elonian Leather, and 30+ hours of time across Tiers 1-3. "
                    f"Direct Trading Post purchase saves ~69g and ~30 hours of crafting/farming."
                ),
                estimated_minutes=5,
                priority="CRITICAL",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Account"
            ))
            c1_readiness = 80.0 if gold >= dusk_price else 20.0
        else:
            if astral_acclaim >= 1200:
                c1_actions.append(JourneyAction(
                    action_title="Buy Legendary Starter Kit",
                    action_description="You have 1200+ Astral Acclaim! Purchase the Legendary Weapon Starter Kit from the Wizard's Vault to get Dusk and Gift of Metal.",
                    estimated_minutes=2,
                    priority="CRITICAL",
                    game_mode="Account"
                ))
                c1_readiness = 90.0
            elif gold >= dusk_price:
                c1_actions.append(JourneyAction(
                    action_title="Buy Dusk from Trading Post",
                    action_description=f"You have enough gold to buy Dusk directly from the Trading Post for ~{dusk_price}g.",
                    estimated_minutes=2,
                    priority="CRITICAL",
                    game_mode="Account"
                ))
                c1_readiness = 90.0
            else:
                # Check Central Tyria mastery prerequisite for Hobbs collection
                hobbs_mastery_query = """
                SELECT ?trackId ?trackLabel ?reqLvl WHERE {
                    item:vendor_hobbs priory:requiresMasteryTrack ?track .
                    ?track priory:masteryId ?trackId .
                    OPTIONAL { item:vendor_hobbs priory:requiredMasteryLevel ?reqLvl }
                    OPTIONAL { ?track rdfs:label ?trackLabel }
                } LIMIT 1
                """
                hobbs_res = self.store.query(hobbs_mastery_query)
                track_id = int(hobbs_res[0]["trackId"]) if hobbs_res else 10
                track_label = str(hobbs_res[0].get("trackLabel", "Legendary Crafting")) if hobbs_res else "Legendary Crafting"
                crafting_mastery = account.masteries.get(track_id, 0)
                
                hobbs_tiers_breakdown = (
                    "Hobbs 3-Tier Precursor Collection Breakdown: "
                    "• Tier 1 (Revered Antiquarian Mastery Tier 1, Weaponsmith 450): Craft Dusk Experiment using 30x Deldrimor Steel Ingots (15x Blade + 15x Hilt) + 200 Memory of Battle + 200 Shard of Glory, then salvage into Spirit of the Dusk Experiment. "
                    "• Tier 2 (Magister of Legends Mastery Tier 2, Weaponsmith 450): Complete metallurgical research requiring 35x Deldrimor Steel Ingots, 1,000 Bandit Crests, 400 Geodes, and 100 Obsidian Shards; craft Perfected Nightsword and salvage into Spirit of the Perfected Nightsword. "
                    "• Tier 3 (Historian of the Armaments Mastery Tier 3, Weaponsmith 500): Obtain Gloominator gizmo and extract primordial darkness from 27 Gloom locations (Fractals: Aquatic Ruins, Swampland, Snowblind, Solid Ocean, Underground; World Bosses: Tequatl, Shadow Behemoth; Silverwastes: Tangled Labyrinth & Breaches; Mini-Dungeons: Tears of Itlaocol, Weyandt's Revenge, Temple of Grenth, Vexa's Lab, Provernic Crypt); forge final precursor Dusk at Weaponsmith 500 using Essence of Gloom, Mirror, and Dimensional Destabilizer."
                )

                mastery_warning = ""
                if crafting_mastery < 3:
                    mastery_warning = f" ⚠️ Requires Central Tyria Mastery '{track_label}' (Tiers 1-3: Revered Antiquarian, Magister of Legends, Historian of the Armaments; current level: {crafting_mastery}/3). {hobbs_tiers_breakdown}"
                else:
                    mastery_warning = f" ✅ Central Tyria Mastery '{track_label}' (Tiers 1-3) is fully unlocked ({crafting_mastery}/3). {hobbs_tiers_breakdown}"

                c1_actions.append(JourneyAction(
                    action_title="Begin Hobbs Precursor Collection (Dusk I, II, III)",
                    action_description=f"Start the Grandmaster Hobbs collection journey in Lion's Arch `[&BBAEAAA=]`.{mastery_warning}",
                    estimated_minutes=30,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Grandmaster Craftsman Hobbs",
                    game_mode="OpenWorld"
                ))
                c1_readiness = 0.0

            prereq, has_bit_progress, missing_bits_summary = self._get_precursor_collection_bit_status(self.TWILIGHT_ID, account)
            if has_bit_progress and prereq and missing_bits_summary:
                first_missing = prereq.precursor_missing_bits_detail[0] if prereq.precursor_missing_bits_detail else {}
                first_zone = str(first_missing.get("zone") or "Lion's Arch")
                first_wp = str(first_missing.get("waypoint") or "[&BBAEAAA=]")
                c1_actions.append(JourneyAction(
                    action_title=(
                        f"Complete Remaining Collection Bits: {prereq.precursor_collection_step} "
                        f"({prereq.precursor_collection_bits_done}/{prereq.precursor_collection_bits_total})"
                    ),
                    action_description=missing_bits_summary,
                    estimated_minutes=20,
                    priority="HIGH",
                    zone_name=first_zone,
                    waypoint=first_wp,
                    npc_name="Grandmaster Craftsman Hobbs",
                    game_mode="OpenWorld",
                ))
                if prereq.precursor_collection_bits_total > 0:
                    c1_readiness = max(
                        c1_readiness,
                        round((prereq.precursor_collection_bits_done / float(prereq.precursor_collection_bits_total)) * 100.0, 1),
                    )
                    c1_status = "IN_PROGRESS"

        chapters.append(JourneyChapter(
            chapter_number=1,
            chapter_title="The Precursor Decision (Dusk)",
            chapter_summary="Evaluate Astral Acclaim, gold, and collection methods for acquiring Dusk.",
            actions=c1_actions,
            completion_status=c1_status,
            readiness_pct=c1_readiness
        ))
        
        # --- Chapter 2: The Core Tyria Expedition (The World Tour) ---
        has_exploration = account.total_item_count(self.GIFT_OF_EXPLORATION_ID) > 0
        c2_status = "COMPLETED" if has_exploration else "IN_PROGRESS"
        c2_readiness = 100.0 if has_exploration else 50.0
        c2_actions = []

        if not has_exploration:
            char_list = [
                (c.get("name") if isinstance(c, dict) else str(c))
                for c in account.characters
                if (isinstance(c, dict) and c.get("name")) or isinstance(c, str)
            ]
            ontology_chars = self._get_ontology_characters()
            is_default_roster = bool(ontology_chars and ontology_chars[0] in char_list)

            # Select primary mobility character from eligible exploration characters
            mobility_char = self._find_mobility_character_name(account)

            if account.has_mount("skyscale"):
                skyscale_mount_str = "with Skyscale"
            elif account.has_mount("raptor"):
                skyscale_mount_str = "with Raptor"
            else:
                skyscale_mount_str = "on foot"

            notice_str = ""
            if account.map_completed_characters and (is_default_roster or any(m in char_list for m in account.map_completed_characters)):
                completed_names = ", ".join(account.map_completed_characters)
                ontology_uncompleted = [c for c in ontology_chars if c not in account.map_completed_characters]
                account_eligible = account.eligible_exploration_characters()
                combined_alts: List[str] = []
                if is_default_roster and ontology_uncompleted:
                    combined_alts.append(ontology_uncompleted[0])
                for c in account_eligible + ontology_uncompleted:
                    if c not in combined_alts:
                        combined_alts.append(c)
                top_alts = combined_alts[:3]
                if len(top_alts) == 3:
                    eligible_examples = f"{top_alts[0]}, {top_alts[1]}, or {top_alts[2]}"
                elif top_alts:
                    eligible_examples = ", ".join(top_alts)
                else:
                    eligible_examples = mobility_char
                mount_hint = " with your Skyscale" if account.has_mount("skyscale") else ""
                notice_str = (
                    f"✅ 100% Map Complete Character: {completed_names} has already completed 100% Core Tyria Map Completion and claimed their Gifts of Exploration. "
                    f"Since Gifts of Exploration are awarded once per character upon 100% world completion, select an eligible alt character from your roster "
                    f"(e.g. {eligible_examples}) to run the 5 Core Tyria regions{mount_hint} to claim 2x new Gifts of Exploration!\n\n"
                )

            roster_str = f"Assessed account roster of {len(char_list)} characters: {', '.join(char_list)}. " if char_list else ""
            c2_actions.append(JourneyAction(
                action_title="Core Tyria Map Completion (2x Gifts of Exploration)",
                action_description=(
                    f"{notice_str}"
                    f"Recommend 100% Core Tyria map completion on your primary mobility character ({mobility_char}) {skyscale_mount_str}. "
                    f"{roster_str}"
                    f"✨ Milestone Reward: Completing 100% Core Map awards 2x Gifts of Exploration (satisfying Twilight AND providing a spare for your next Gen 1 legendary)!"
                ),
                estimated_minutes=30,
                priority="CRITICAL",
                recommended_mount="Skyscale" if account.has_mount("skyscale") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))

            c2_actions.append(JourneyAction(
                action_title="Complete Shiverpeaks Map",
                action_description="Explore Shiverpeak Mountains. Skyscale recommended for high elevation." if account.has_mount("skyscale") else "Explore Shiverpeak Mountains.",
                estimated_minutes=180,
                priority="HIGH",
                recommended_mount="Skyscale" if account.has_mount("skyscale") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))
            c2_actions.append(JourneyAction(
                action_title="Complete Ascalon Map",
                action_description="Explore Ascalon. Raptor/Jackal recommended." if account.has_mount("raptor") else "Explore Ascalon.",
                estimated_minutes=180,
                priority="HIGH",
                recommended_mount="Raptor" if account.has_mount("raptor") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))
            c2_actions.append(JourneyAction(
                action_title="Complete Kryta Map",
                action_description="Explore Kryta. Raptor recommended." if account.has_mount("raptor") else "Explore Kryta.",
                estimated_minutes=180,
                priority="HIGH",
                recommended_mount="Raptor" if account.has_mount("raptor") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))
            c2_actions.append(JourneyAction(
                action_title="Complete Maguuma Map",
                action_description="Explore Maguuma Jungle. Skyscale recommended." if account.has_mount("skyscale") else "Explore Maguuma Jungle.",
                estimated_minutes=180,
                priority="HIGH",
                recommended_mount="Skyscale" if account.has_mount("skyscale") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))
            c2_actions.append(JourneyAction(
                action_title="Complete Orr Map",
                action_description="Explore Ruins of Orr. Skyscale recommended." if account.has_mount("skyscale") else "Explore Ruins of Orr.",
                estimated_minutes=180,
                priority="HIGH",
                recommended_mount="Skyscale" if account.has_mount("skyscale") else None,
                game_mode="OpenWorld",
                assigned_character=mobility_char
            ))

        chapters.append(JourneyChapter(
            chapter_number=2,
            chapter_title="The Core Tyria Expedition (The World Tour)",
            chapter_summary="5-region geographical route for Gift of Exploration. Completing 100% Core Map awards 2x Gifts of Exploration (satisfying Twilight AND providing a spare for your next Gen 1 legendary).",
            actions=c2_actions,
            completion_status=c2_status,
            readiness_pct=c2_readiness
        ))
        
        # --- Chapter 3: Currencies, Dungeons & Daily Rituals ---
        tales_count = account.dungeon_tales_count()
        has_ascalon = any(account.total_item_count(aid) > 0 for aid in [self.GIFT_OF_ASCALON_ID, 19667, 19640])
        has_battle = account.has_gift_of_battle()
        has_bloodstone = account.has_bloodstone_shard()
        spirit_shards = account.spirit_shards_count()
        obsidian_count = account.total_item_count(self.OBSIDIAN_SHARD_ID)
        runestone_count = account.total_item_count(self.ICY_RUNESTONE_ID) + account.total_item_count(19912)
        lodestone_count = account.total_item_count(self.ONYX_LODESTONE_ID)
        t6_owned = sum(account.total_item_count(mat_id) for mat_id in set(self.T6_MATERIAL_IDS + self.LEGACY_T6_MATERIAL_IDS))
        t6_total_needed = 2000
        ecto_count = account.total_item_count(self.GLOB_OF_ECTOPLASM_ID)
        clover_count = account.total_item_count(self.MYSTIC_CLOVER_ID)
        needed_clovers = max(0, 77 - clover_count)
        
        c3_actions = []

        # Check actual owned boosters and gobblers from account snapshot via dynamic ontology catalog
        owned_boosters = account.owned_boosters()
        has_gobblers = account.has_gobbler()
        booster_catalog = self._get_booster_catalog()

        booster_telemetry_str = ""
        tailored_instructions = []
        if owned_boosters:
            detected_items = []
            gobbler_detected = []
            regular_boosters = []
            tome_ids_owned = []

            for item_id, count in sorted(owned_boosters.items()):
                meta = booster_catalog.get(item_id, {})
                name = meta.get("label") or f"Booster {item_id}"
                category = meta.get("category", "booster")
                detected_items.append(f"{count}x {name} {item_id}")

                if category == "gobbler" or "gobbler" in name.lower():
                    gobbler_detected.append(f"{count}x {name} {item_id}")
                elif category == "tome" or "tome of knowledge" in name.lower() or "writ of experience" in name.lower():
                    tome_ids_owned.append(str(item_id))
                else:
                    if name != f"Booster {item_id}" and not name.startswith("Booster "):
                        regular_boosters.append(f"{count}x {name} ({count}x Booster {item_id})")
                    else:
                        regular_boosters.append(f"{count}x {name}")

            booster_telemetry_str = f"detected {', '.join(detected_items)} in bank/inventory!"

            # Gobblers
            if gobbler_detected:
                tailored_instructions.append(f"🍬 Gobbler Activation: Use {' / '.join(gobbler_detected)} with festival candy/taffy/snowflakes for continuous +25%-50% WvW Reward Track & XP buffs.")
            elif has_gobblers:
                tailored_instructions.append("🍬 Gobbler Activation: Activate your festival gobblers for continuous +25%-50% WvW Reward Track & XP buffs.")

            # Regular boosters
            if regular_boosters:
                tailored_instructions.append(f"⚡ Booster Stacking: Activate {', '.join(regular_boosters)} + Guild Tavern WvW enhancement to accelerate Gift of Battle progression to ~3.5h - 4.5h.")

            # Tomes of Knowledge
            tome_count = account.tomes_of_knowledge_count()
            if tome_count > 0:
                tome_id_str = ", ".join(tome_ids_owned) if tome_ids_owned else "Tome of Knowledge"
                tailored_instructions.append(f"📖 Tome of Knowledge Conversion: Use {tome_count}x Tomes of Knowledge ({tome_id_str}) on a level 80 character to instantly generate Spirit Shards for Miyani's Bloodstone Shard (200 needed) and Mystic Clovers.")

        # 1. Gift of Ascalon
        if not has_ascalon:
            if tales_count >= 500:
                c3_actions.append(JourneyAction(
                    action_title="Purchase Gift of Ascalon",
                    action_description="Trade 500 Tales of Dungeon Delving at the Dungeon Vendor in Lion's Arch `[&BBAEAAA=]`.",
                    estimated_minutes=5,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    game_mode="Account"
                ))
            else:
                c3_actions.append(JourneyAction(
                    action_title="Run Ascalonian Catacombs",
                    action_description=f"Run AC explorable paths to earn Tales of Dungeon Delving (currently have {tales_count}/500).",
                    estimated_minutes=45,
                    priority="HIGH",
                    zone_name="Plains of Ashford",
                    waypoint="[&BIcBAAA=]",
                    game_mode="Dungeon"
                ))
        else:
            c3_actions.append(JourneyAction(
                action_title="Gift of Ascalon (Completed / Ready)",
                action_description=f"✅ You own Gift of Ascalon in storage (purchased with 500 Tales of Dungeon Delving from Dungeon Vendor `[&BBAEAAA=]`).",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Account"
            ))
                
        # 2. Gift of Battle (WvW Reward Track with Booster Indicators)
        telemetry_suffix = f" (Snapshot telemetry: {booster_telemetry_str} {' '.join(tailored_instructions)})" if booster_telemetry_str else ""
        if not has_battle:
            c3_actions.append(JourneyAction(
                action_title="Complete Gift of Battle WvW Reward Track",
                action_description=f"Activate the Gift of Battle Reward Track in WvW (Edge of the Mists or Borderlands). 🚀 Booster Acceleration: Stack Experience Booster + Heroic Booster + Guild Tavern WvW buff to complete the track in ~4.5h instead of 8.0h unboosted.{telemetry_suffix}",
                estimated_minutes=270,
                priority="HIGH",
                game_mode="WvW"
            ))
        else:
            battle_qty = account.total_item_count(self.GIFT_OF_BATTLE_ID)
            c3_actions.append(JourneyAction(
                action_title="WvW Gift of Battle Track (Completed / Ready)",
                action_description=f"✅ You own {battle_qty}x Gift of Battle in inventory/bank! 🚀 Booster Acceleration Guide: If farming additional tracks, stack Experience Booster + Heroic Booster + Guild Tavern WvW buff to finish in ~4.5h instead of 8.0h unboosted.{telemetry_suffix}",
                estimated_minutes=1,
                priority="LOW",
                game_mode="WvW"
            ))

        # Dedicated Booster Telemetry Action
        if owned_boosters:
            c3_actions.append(JourneyAction(
                action_title="🚀 Booster & Gobbler Telemetry",
                action_description=f"Account Snapshot Telemetry: {booster_telemetry_str} Tailored Activation: {' '.join(tailored_instructions)}",
                estimated_minutes=2,
                priority="MEDIUM",
                game_mode="Account"
            ))

        # Daily Converter & Gobbler Checklist (Free Obsidian Shards & Keys)
        has_ley = account.has_ley_energy_converter()
        has_karmic = account.has_karmic_converter()
        has_sentient = account.has_sentient_converters()

        if has_ley or has_karmic or has_sentient or has_gobblers:
            conv_items_list = []
            if has_ley:
                conv_items_list.append("Ley-Energy Matter Converter `[&AgGgCgEA]`")
            if has_karmic:
                conv_items_list.append("Karmic Converter `[&AgEAfAEA]`")
            if account.total_item_count(92209) > 0 or account.total_item_count(81790) > 0:
                conv_items_list.append("Gleam of Sentience `[&AgERUQEA]`")
            if account.total_item_count(69887) > 0:
                conv_items_list.append("Princess `[&AgF/EQEA]`")
            if account.total_item_count(68369) > 0:
                conv_items_list.append("Star of Gratitude `[&AgExCwEA]`")
            if account.total_item_count(73248) > 0:
                conv_items_list.append("Herta `[&AgGgHAEA]`")
            if account.total_item_count(66341) > 0:
                conv_items_list.append("Mawdrey II `[&AgE1BAEA]`")

            ley_tip = ""
            if has_ley:
                ley_tip = " Open Tab 2 of your Ley-Energy Matter Converter `[&AgGgCgEA]` daily to claim free Obsidian Shards (0 karma/gold cost) and Heart of Thorns map keys (Machetes, Bandit Skeleton Keys, Exalted Keys, Vial of Chak Acid)."
            else:
                ley_tip = " Check converters daily for free Obsidian Shards, keys, and material bags."

            converter_telemetry_str = f" Detected converters: {', '.join(conv_items_list)}." if conv_items_list else ""

            c3_actions.append(JourneyAction(
                action_title="🌟 Daily Converter Checklist (Free Obsidian Shards & Keys)",
                action_description=(
                    f"Daily Converter Checklist:{ley_tip} "
                    f"Activate your Karmic Converter `[&AgEAfAEA]` and Sentient gizmos daily to convert excess Bloodstone Dust, Dragonite Ore, and Empyreal Fragments into Heavy Crafting Bags (free T6 materials).{converter_telemetry_str}"
                ).strip(),
                estimated_minutes=5,
                priority="HIGH",
                game_mode="Account"
            ))
            
        # 3. Bloodstone Shard & 200 Spirit Shard Check
        tome_note = ""
        owned_tome_qty = sum(
            cnt for iid, cnt in owned_boosters.items()
            if booster_catalog.get(iid, {}).get("category") == "tome" or "tome of knowledge" in booster_catalog.get(iid, {}).get("label", "").lower()
        )
        if owned_tome_qty > 0:
            tome_note = f" (You have {owned_tome_qty}x Tomes of Knowledge available in bank/inventory to convert into Spirit Shards!)"

        if not has_bloodstone:
            if spirit_shards >= 200:
                c3_actions.append(JourneyAction(
                    action_title="Purchase Bloodstone Shard from Miyani",
                    action_description=f"✅ 200 Spirit Shard Check: You have {spirit_shards} Spirit Shards (200 needed). Exchange 200 Spirit Shards with Miyani at the Mystic Forge `[&BBAEAAA=]` in Lion's Arch for a Bloodstone Shard.{tome_note}",
                    estimated_minutes=5,
                    priority="MEDIUM",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Miyani",
                    game_mode="Account"
                ))
            else:
                c3_actions.append(JourneyAction(
                    action_title="Farm Spirit Shards for Bloodstone Shard",
                    action_description=f"⚠️ 200 Spirit Shard Check: You have {spirit_shards}/200 Spirit Shards (need {200 - spirit_shards} more). Earn Spirit Shards from level 80 XP, meta events, or Tomes of Knowledge, then purchase Bloodstone Shard from Miyani `[&BBAEAAA=]`.{tome_note}",
                    estimated_minutes=60,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Miyani",
                    game_mode="Account"
                ))
        else:
            c3_actions.append(JourneyAction(
                action_title="Bloodstone Shard (200 Spirit Shards Check - Owned)",
                action_description=f"✅ 200 Spirit Shard Check: Bloodstone Shard is already in your inventory (Account holds {spirit_shards} Spirit Shards). Bought from Miyani `[&BBAEAAA=]` for 200 Spirit Shards.{tome_note}",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                npc_name="Miyani",
                game_mode="Account"
            ))

        # 4. Obsidian Shards
        has_t2f = "teleport_to_friend" in account.owned_convenience_items() or account.total_item_count(90335) > 0
        t2f_str = " ⚡ Recharging Teleport to Friend `[&AgHfYAEA]` Detected: Instantly taxi into active squads on uncontested Temple of Balthazar maps!" if has_t2f else " Use Recharging Teleport to Friend `[&AgHfYAEA]` or LFG taxi to instantly taxi into contested Temple of Balthazar maps."

        if obsidian_count < 250:
            needed_obs = 250 - obsidian_count
            c3_actions.append(JourneyAction(
                action_title="Buy Obsidian Shards via Karma (Temple of Balthazar)",
                action_description=f"Purchase {needed_obs} Obsidian Shards at the Temple of Balthazar `[&BO4CAAA=]` from Tactician Deathspark (2,100 Karma each, {needed_obs * 2100:,} Karma total, 0 gold cost). Temple of Balthazar karma costs 0 gold for {needed_obs} Obsidian Shards.{t2f_str}",
                estimated_minutes=10,
                priority="MEDIUM",
                zone_name="Straits of Devastation",
                waypoint="[&BO4CAAA=]",
                npc_name="Tactician Deathspark",
                game_mode="OpenWorld"
            ))
        else:
            c3_actions.append(JourneyAction(
                action_title="Obsidian Shards (Completed / Ready)",
                action_description=f"✅ You own {obsidian_count}/250 Obsidian Shards! (Acquired from Tactician Deathspark at Temple of Balthazar `[&BO4CAAA=]` or Silverwastes using Recharging Teleport to Friend `[&AgHfYAEA]` for fast taxis).",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Straits of Devastation",
                waypoint="[&BO4CAAA=]",
                npc_name="Tactician Deathspark",
                game_mode="OpenWorld"
            ))
            
        # 5. Icy Runestones
        if runestone_count < 100:
            needed_runes = 100 - runestone_count
            c3_actions.append(JourneyAction(
                action_title="Purchase Icy Runestones",
                action_description=f"Buy {needed_runes} Icy Runestones for {needed_runes}g total from Rojan the Penitent at Earthshake Waypoint `[&BHsBAAA=]`.",
                estimated_minutes=5,
                priority="MEDIUM",
                zone_name="Frostgorge Sound",
                waypoint="[&BHsBAAA=]",
                npc_name="Rojan the Penitent",
                game_mode="OpenWorld"
            ))
        else:
            c3_actions.append(JourneyAction(
                action_title="Icy Runestones (Completed / Ready)",
                action_description=f"✅ You own {runestone_count}/100 Icy Runestones! (Purchased from Rojan the Penitent at Earthshake Waypoint `[&BHsBAAA=]` for 1g each).",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Frostgorge Sound",
                waypoint="[&BHsBAAA=]",
                npc_name="Rojan the Penitent",
                game_mode="OpenWorld"
            ))

        # 6. Onyx Lodestones vs Onyx Cores Mystic Forge Promotion Cost Comparison
        needed_lodes = max(1, 100 - lodestone_count)
        needed_cores = needed_lodes * 2
        lode_price = tp_prices.get(self.ONYX_LODESTONE_ID, 0.40)
        core_price = tp_prices.get(self.ONYX_CORE_ID, 0.10)
        direct_cost = round(needed_lodes * lode_price, 1)
        core_cost = round(needed_cores * core_price, 1)
        savings = round(direct_cost - core_cost, 1)

        if lodestone_count < 100:
            c3_actions.append(JourneyAction(
                action_title="Onyx Lodestones vs Cores Mystic Forge Arbitrage",
                action_description=f"Cost comparison: Buying {needed_lodes} Onyx Lodestones (98 lodes = ~39.2g at {lode_price:.2f}g/ea) vs Mystic Forge promotion of {needed_cores} Onyx Cores (196 cores = ~19.6g at {core_price:.2f}g/ea + Elonian Wine/Dust), saving ~{savings:.1f}g (~19.6g savings for 98 lodes)! Forge recipe: 2x Onyx Cores + 1x Crystalline Dust + 1x Philosopher's Stone + 1x Bottle of Elonian Wine.",
                estimated_minutes=15,
                priority="MEDIUM",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Crafting"
            ))
        else:
            c3_actions.append(JourneyAction(
                action_title="Onyx Lodestones (Completed / Ready)",
                action_description=f"✅ You own {lodestone_count}/100 Onyx Lodestones! 💡 Onyx Core Promotion Arbitrage: Promoting 2x Onyx Cores (~{core_price:.2f}g/ea) + Dust + Powder + Wine in the Mystic Forge costs ~50% less than buying Onyx Lodestones (~{lode_price:.2f}g/ea) directly.",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Crafting"
            ))

        # 7. Mystic Clovers Strategy (with Wizard's Vault Exhaustion Awareness)
        if clover_count < 77:
            if wizards_vault_exhausted:
                c3_actions.append(JourneyAction(
                    action_title="Daily Fractal Clovers (BUY-2046), Strike/Raid & Mystic Forge",
                    action_description=(
                        f"Cheapest cost breakdown for {needed_clovers} needed Mystic Clovers (Wizard's Vault Exhausted): "
                        f"1. BUY-2046 Daily Fractal Clovers at Mistlock Observatory `[&DYEFAAA=]`: Buy 2/day for 150 Fractal Relics + 1 Mystic Coin + 3 Ecto + 2 Spirit Shards each (~2.85g/ea vs ~7.4g/ea Forge, saving ~4.5g per clover). "
                        f"2. Weekly Strike Mission & Raid Vendors: Exchange Green Prophet Shards and Magnetite Shards weekly. "
                        f"3. Mystic Forge Promotion: Craft remaining clovers using 1x Mystic Coin + 1x Glob of Ectoplasm + 1x Philosopher's Stone + 6x Bottle of Elonian Wine (~7.42g/ea effective cost)."
                    ),
                    estimated_minutes=10,
                    priority="CRITICAL",
                    zone_name="Mistlock Observatory",
                    waypoint="[&DYEFAAA=]",
                    npc_name="BUY-2046",
                    game_mode="Account"
                ))
            else:
                c3_actions.append(JourneyAction(
                    action_title="Claim Wizard's Vault Mystic Clovers",
                    action_description=f"Purchase remaining Mystic Clovers (60 Astral Acclaim each) from the Wizard's Vault or buy 2/day from BUY-2046 in Mistlock Observatory `[&DYEFAAA=]`.",
                    estimated_minutes=10,
                    priority="CRITICAL",
                    game_mode="Account"
                ))

        # 8. Daily T6 Laurel Merchant / RIBA Conversion Routine & Ectoplasm Salvaging
        has_silver_fed = "silver_fed" in account.owned_convenience_items() or account.total_item_count(67027) > 0
        silver_fed_tip = " 🌟 Silver-Fed Salvage-o-Matic `[&AgHTBQEA]` Detected: Use it on level 68+ Rare gear for optimal ~0.875 Ectoplasm yield per salvage." if has_silver_fed else " (Salvage level 68+ Rare gear with Silver-Fed Salvage-o-Matic `[&AgHTBQEA]` or Mystic Salvage Kit for optimal ~0.875 Ectoplasm yield per rare)."

        if t6_owned < t6_total_needed or ecto_count < 250:
            needed_t6 = max(0, t6_total_needed - t6_owned)
            desc_parts = []
            if needed_t6 > 0:
                desc_parts.append(f"Need {needed_t6} more T6 fine materials: Exchange Laurels for Heavy Crafting Bags at Laurel Merchant in Lion's Arch `[&BBAEAAA=]` (1 Laurel = 3 T6 materials), and run Silverwastes RIBA meta train `[&BF8HAAA=]` to salvage rares for ectoplasm and open champion bags for T6 materials.{silver_fed_tip}")
            else:
                desc_parts.append(f"Run Silverwastes RIBA meta train `[&BF8HAAA=]` to salvage level 68+ rares for Globs of Ectoplasm ({ecto_count}/250 owned) and open champion bags for materials.{silver_fed_tip}")
            
            c3_actions.append(JourneyAction(
                action_title="Daily T6 Laurel Merchant & RIBA Routine",
                action_description=" ".join(desc_parts),
                estimated_minutes=30,
                priority="HIGH",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Account"
            ))
        else:
            c3_actions.append(JourneyAction(
                action_title="T6 Materials & Ectoplasm (Completed / Ready)",
                action_description=f"✅ You own {t6_owned}/2000 T6 fine materials and {ecto_count}/250 Globs of Ectoplasm! (Salvaged with Silver-Fed Salvage-o-Matic `[&AgHTBQEA]`).",
                estimated_minutes=1,
                priority="LOW",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Account"
            ))

        ascalon_pct = 1.0 if has_ascalon else min(1.0, tales_count / 500.0)
        battle_pct = 1.0 if has_battle else 0.0
        bloodstone_pct = 1.0 if (has_bloodstone or spirit_shards >= 200) else min(1.0, spirit_shards / 200.0)
        obsidian_pct = min(1.0, obsidian_count / 250.0)
        runestone_pct = min(1.0, runestone_count / 100.0)
        lodestone_pct = min(1.0, lodestone_count / 100.0)
        t6_pct = min(1.0, t6_owned / float(t6_total_needed))

        c3_readiness = (ascalon_pct + battle_pct + bloodstone_pct + obsidian_pct + runestone_pct + lodestone_pct + t6_pct) / 7.0 * 100.0

        chapters.append(JourneyChapter(
            chapter_number=3,
            chapter_title="Currencies, Dungeons & Daily Rituals",
            chapter_summary="Gift of Ascalon, Gift of Battle, Bloodstone Shard, Obsidian Shards, Onyx Arbitrage, and Daily T6 Routines.",
            actions=c3_actions,
            completion_status="COMPLETED" if c3_readiness >= 99.0 else "IN_PROGRESS",
            readiness_pct=round(c3_readiness, 1)
        ))
        
        # --- Chapter 4: The Forge Ceremony & Character Hand-offs ---
        weaponsmith_level = account.max_discipline_rating("weaponsmith")
        armorsmith_level = account.max_discipline_rating("armorsmith")
        
        ws_char = None
        as_char = None
        primary_crafter = None
        
        for char in account.characters:
            if not isinstance(char, dict):
                continue
            char_name = char.get("name", "")
            raw_discs = char.get("crafting", []) or char.get("disciplines", [])
            discs = {d.get("discipline", "").lower(): d.get("rating", 0) for d in raw_discs if isinstance(d, dict)}
            ws_rating = discs.get("weaponsmith", 0)
            as_rating = discs.get("armorsmith", 0)
            if ws_rating > weaponsmith_level:
                weaponsmith_level = ws_rating
            if as_rating > armorsmith_level:
                armorsmith_level = as_rating
            if ws_rating >= 400 and as_rating >= 400 and not primary_crafter:
                primary_crafter = char_name
                ws_char = char_name
                as_char = char_name
            if ws_rating >= 400 and not ws_char:
                ws_char = char_name
            if as_rating >= 400 and not as_char:
                as_char = char_name

        for char_name, disc_map in account.character_disciplines.items():
            if not isinstance(disc_map, dict):
                continue
            ws_rating = 0
            as_rating = 0
            for d_key, d_val in disc_map.items():
                rating = int(d_val.get("rating", 0)) if isinstance(d_val, dict) else (int(d_val) if isinstance(d_val, (int, float)) else 0)
                if d_key.lower() == "weaponsmith":
                    ws_rating = rating
                elif d_key.lower() == "armorsmith":
                    as_rating = rating
            if ws_rating >= 400 and as_rating >= 400 and not primary_crafter:
                primary_crafter = char_name
                ws_char = char_name
                as_char = char_name
            if ws_rating >= 400 and not ws_char:
                ws_char = char_name
            if as_rating >= 400 and not as_char:
                as_char = char_name
                
        if not primary_crafter:
            if ws_char and as_char and ws_char == as_char:
                primary_crafter = ws_char
            elif ws_char:
                primary_crafter = ws_char
            elif as_char:
                primary_crafter = as_char
            elif account.characters:
                first_c = account.characters[0]
                primary_crafter = first_c.get("name") if isinstance(first_c, dict) else str(first_c)

        ws_assign = ws_char or primary_crafter
        as_assign = as_char or primary_crafter
        forge_assign = primary_crafter or ws_char or as_char

        owned_lounges = account.owned_lounges()
        lounge = owned_lounges[0] if owned_lounges else None
        lounge_name = lounge["name"] if lounge else None
        lounge_link = lounge["chat_link"] if lounge else None
        lounge_zone = lounge.get("zone", lounge_name) if lounge else None
        if lounge_zone == "VIP Lounge" and lounge_name:
            lounge_zone = re.sub(r"\s+(Passkey|Pass|Scroll|Invitation|Key)$", "", lounge_name, flags=re.IGNORECASE).strip()

        c4_actions = []
        c4_readiness = 0.0
        
        has_metal = account.total_item_count(self.GIFT_OF_METAL_ID) > 0
        has_darkness = account.total_item_count(self.GIFT_OF_DARKNESS_ID) > 0
        has_gift_twilight = account.total_item_count(self.GIFT_OF_TWILIGHT_ID) > 0

        # Build Crafter Summary
        if primary_crafter:
            craft_summary = f"Weaponsmith {weaponsmith_level} & Armorsmith {armorsmith_level} for {primary_crafter}"
        elif ws_char and as_char and ws_char != as_char:
            craft_summary = f"Weaponsmith {weaponsmith_level} for {ws_char} & Armorsmith {armorsmith_level} for {as_char}"
        elif ws_char:
            craft_summary = f"Weaponsmith {weaponsmith_level} for {ws_char}"
        elif as_char:
            craft_summary = f"Armorsmith {armorsmith_level} for {as_char}"
        else:
            craft_summary = f"Weaponsmith {weaponsmith_level} & Armorsmith {armorsmith_level}"

        if lounge:
            conv_items = account.owned_convenience_items() if hasattr(account, "owned_convenience_items") else {}
            conv_parts = []
            seen_conv = set()
            for slug, item in conv_items.items():
                if slug.isdigit():
                    continue
                if item["name"] not in seen_conv:
                    seen_conv.add(item["name"])
                    conv_parts.append(f"{item['name']} {item['chat_link']}")
            
            conv_tools_str = f" and convenience tools ({', '.join(conv_parts)})" if conv_parts else ""
            vip_banner = f"🌟 VIP Lounge Pass Detected: You own {lounge_name} {lounge_link}{conv_tools_str}! Use {lounge_zone} to access all crafting stations ({craft_summary}), the Mystic Forge, bank, and Trading Post in one compact instance with zero travel fees and instant map return."
            c4_actions.append(JourneyAction(
                action_title=f"🌟 VIP Lounge Pass Detected ({lounge_name})",
                action_description=vip_banner,
                estimated_minutes=2,
                priority="HIGH",
                zone_name=lounge_zone,
                waypoint=lounge_link,
                game_mode="Account",
                assigned_character=forge_assign
            ))

        # Permanent Service Contracts Telemetry (Instant Anywhere-Access)
        owned_contracts = []
        if account.has_permanent_bank():
            owned_contracts.append("Permanent Bank Access Express `[&AgGQjAAA]`")
        if account.has_permanent_tp():
            owned_contracts.append("Permanent Trading Post Express `[&AgGZjAAA]`")
        if account.has_permanent_merchant():
            owned_contracts.append("Permanent Merchant Express `[&AgGJjAAA]`")
        if account.has_permanent_hair_stylist():
            owned_contracts.append("Permanent Hair Stylist Contract `[&AgG4XAAA]`")

        if owned_contracts:
            contract_str = ", ".join(owned_contracts)
            contract_wp = lounge_link if lounge else "[&BBAEAAA=]"
            contract_zone = lounge_zone if lounge else "Lion's Arch"
            c4_actions.append(JourneyAction(
                action_title="🌟 Permanent Contracts Detected (Instant Anywhere-Access)",
                action_description=(
                    f"🌟 Permanent Contracts Detected: You own {contract_str}! "
                    f"Take advantage of instant anywhere-access capability to access your bank, Trading Post, and merchant directly from anywhere in the world "
                    f"without leaving your crafting station or paying waypoint fees."
                ),
                estimated_minutes=2,
                priority="HIGH",
                zone_name=contract_zone,
                waypoint=contract_wp,
                game_mode="Account",
                assigned_character=forge_assign
            ))

        # Material Staging: Invisible Bags & 250-Stack Batching
        staging_wp = lounge_link if lounge else "[&BBAEAAA=]"
        staging_zone = lounge_zone if lounge else "Lion's Arch"
        c4_actions.append(JourneyAction(
            action_title="🛡️ Material Staging: Invisible Bags & 250-Stack Batching",
            action_description=(
                "🛡️ Invisible Bag Staging Rules: Place your precursor (Dusk `[&BBAEAAA=]`), intermediate gifts (Gift of Metal, Gift of Darkness, Gift of Mastery, Gift of Fortune, Gift of Twilight), and exotic components into an Invisible Bag (or Safe Box). Items in invisible bags are protected from accidental 'Deposit All Materials', mass salvage kit clicks, or vendor liquidation while crafting. "
                "📦 250-Stack Material Storage Batching: Craft materials in complete 250-unit stacks (250x Orichalcum, 250x Mithril, 250x Darksteel, 250x Platinum Ingots, 250x Globs of Ectoplasm, 250x Obsidian Shards) to match GW2 Material Storage slot limits and prevent bag clutter during Forge operations."
            ),
            estimated_minutes=5,
            priority="HIGH",
            zone_name=staging_zone,
            waypoint=staging_wp,
            game_mode="Account",
            assigned_character=forge_assign
        ))

        # Step 1: Forge Gift of Metal
        if weaponsmith_level < 400 and not has_metal:
            if lounge:
                metal_desc = f"Level Weaponsmithing to 400 in {lounge_zone} `{lounge_link}` to craft Gift of Metal."
                metal_wp = lounge_link
                metal_zone = lounge_zone
            else:
                metal_desc = "Level Weaponsmithing to 400 in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]` to craft Gift of Metal."
                metal_wp = "[&BKgDAAA=]"
                metal_zone = "Black Citadel"
            c4_actions.append(JourneyAction(
                action_title="Level Weaponsmith to 400",
                action_description=metal_desc,
                estimated_minutes=30,
                priority="CRITICAL",
                zone_name=metal_zone,
                waypoint=metal_wp,
                game_mode="Crafting",
                assigned_character=ws_assign
            ))
        else:
            c4_readiness += 25.0
            if not has_metal and not has_gift_twilight:
                if lounge:
                    metal_desc = f"Craft Gift of Metal (250x Orichalcum, 250x Mithril, 250x Darksteel, 250x Platinum Ingots) at a Weaponsmithing station in {lounge_zone} `{lounge_link}`."
                    metal_wp = lounge_link
                    metal_zone = lounge_zone
                else:
                    metal_desc = "Craft Gift of Metal (250x Orichalcum, 250x Mithril, 250x Darksteel, 250x Platinum Ingots) at a Weaponsmithing station in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]`."
                    metal_wp = "[&BKgDAAA=]"
                    metal_zone = "Black Citadel"
                c4_actions.append(JourneyAction(
                    action_title="Forge Gift of Metal",
                    action_description=metal_desc,
                    estimated_minutes=5,
                    priority="HIGH",
                    zone_name=metal_zone,
                    waypoint=metal_wp,
                    game_mode="Crafting",
                    assigned_character=ws_assign
                ))
            elif has_metal:
                if lounge:
                    metal_desc = f"✅ Gift of Metal is already in your storage! (Crafted by Weaponsmith {weaponsmith_level} in {lounge_zone} `{lounge_link}`)."
                    metal_wp = lounge_link
                    metal_zone = lounge_zone
                else:
                    metal_desc = "✅ Gift of Metal is already in your storage! (Crafted by Weaponsmith 400 in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]`)."
                    metal_wp = "[&BKgDAAA=]"
                    metal_zone = "Black Citadel"
                c4_actions.append(JourneyAction(
                    action_title="Forge Gift of Metal (Crafted / Ready)",
                    action_description=metal_desc,
                    estimated_minutes=1,
                    priority="LOW",
                    zone_name=metal_zone,
                    waypoint=metal_wp,
                    game_mode="Crafting",
                    assigned_character=ws_assign
                ))
            
        # Step 2: Forge Gift of Darkness
        if armorsmith_level < 400 and not has_darkness:
            if lounge:
                dark_desc = f"Level Armorsmithing to 400 in {lounge_zone} `{lounge_link}` to craft Gift of Darkness."
                dark_wp = lounge_link
                dark_zone = lounge_zone
            else:
                dark_desc = "Level Armorsmithing to 400 in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]` to craft Gift of Darkness."
                dark_wp = "[&BKgDAAA=]"
                dark_zone = "Black Citadel"
            c4_actions.append(JourneyAction(
                action_title="Level Armorsmith to 400",
                action_description=dark_desc,
                estimated_minutes=30,
                priority="CRITICAL",
                zone_name=dark_zone,
                waypoint=dark_wp,
                game_mode="Crafting",
                assigned_character=as_assign
            ))
        else:
            c4_readiness += 25.0
            if not has_darkness and not has_gift_twilight:
                if lounge:
                    dark_desc = f"Craft Gift of Darkness (Gift of Ascalon + 250x Orichalcum Ingots + 100x Onyx Lodestones + 100x Hardened Leather Sections) at an Armorsmithing station in {lounge_zone} `{lounge_link}`."
                    dark_wp = lounge_link
                    dark_zone = lounge_zone
                else:
                    dark_desc = "Craft Gift of Darkness (Gift of Ascalon + 250x Orichalcum Ingots + 100x Onyx Lodestones + 100x Hardened Leather Sections) at an Armorsmithing station in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]`."
                    metal_wp = "[&BKgDAAA=]"
                    dark_wp = "[&BKgDAAA=]"
                    dark_zone = "Black Citadel"
                c4_actions.append(JourneyAction(
                    action_title="Forge Gift of Darkness",
                    action_description=dark_desc,
                    estimated_minutes=5,
                    priority="HIGH",
                    zone_name=dark_zone,
                    waypoint=dark_wp,
                    game_mode="Crafting",
                    assigned_character=as_assign
                ))
            elif has_darkness:
                if lounge:
                    dark_desc = f"✅ Gift of Darkness is already in your storage! (Crafted by Armorsmith {armorsmith_level} in {lounge_zone} `{lounge_link}`)."
                    dark_wp = lounge_link
                    dark_zone = lounge_zone
                else:
                    dark_desc = "✅ Gift of Darkness is already in your storage! (Crafted by Armorsmith 400 in Black Citadel `[&BKgDAAA=]` or Lion's Arch `[&BBAEAAA=]`)."
                    dark_wp = "[&BKgDAAA=]"
                    dark_zone = "Black Citadel"
                c4_actions.append(JourneyAction(
                    action_title="Forge Gift of Darkness (Crafted / Ready)",
                    action_description=dark_desc,
                    estimated_minutes=1,
                    priority="LOW",
                    zone_name=dark_zone,
                    waypoint=dark_wp,
                    game_mode="Crafting",
                    assigned_character=as_assign
                ))
            
        # Step 3: Forge Gift of Twilight
        if has_gift_twilight:
            c4_readiness += 25.0
            twilight_wp = lounge_link if lounge else "[&BBAEAAA=]"
            twilight_zone = lounge_zone if lounge else "Lion's Arch"
            c4_actions.append(JourneyAction(
                action_title="Forge Gift of Twilight (Crafted / Ready)",
                action_description=f"✅ Gift of Twilight is already forged in your storage! (Mystic Forge in {lounge_zone} `{lounge_link}`)." if lounge else "✅ Gift of Twilight is already forged in your storage!",
                estimated_minutes=1,
                priority="LOW",
                zone_name=twilight_zone,
                waypoint=twilight_wp,
                game_mode="Crafting",
                assigned_character=forge_assign
            ))
        else:
            if lounge:
                twilight_desc = f"Combine Gift of Metal, Gift of Darkness, 100x Onyx Lodestones, and 100x Icy Runestones in the Mystic Forge at {lounge_zone} `{lounge_link}`."
                twilight_wp = lounge_link
                twilight_zone = lounge_zone
            else:
                twilight_desc = "Combine Gift of Metal, Gift of Darkness, 100x Onyx Lodestones, and 100x Icy Runestones in the Mystic Forge at Miyani `[&BBAEAAA=]`."
                twilight_wp = "[&BBAEAAA=]"
                twilight_zone = "Lion's Arch"
            c4_actions.append(JourneyAction(
                action_title="Forge Gift of Twilight",
                action_description=twilight_desc,
                estimated_minutes=5,
                priority="CRITICAL",
                zone_name=twilight_zone,
                waypoint=twilight_wp,
                game_mode="Crafting",
                assigned_character=forge_assign
            ))
        
        # Step 4: 4-Pillar Inventory Staging Checklist (Before Final Forge)
        staging_check_wp = lounge_link if lounge else "[&BBAEAAA=]"
        staging_check_zone = lounge_zone if lounge else "Lion's Arch"
        sigil_count = account.total_item_count(self.SUPERIOR_SIGIL_OF_STRENGTH_ID) + (
            account.total_item_count(self.SUPERIOR_SIGIL_OF_FORCE_ID) if self.SUPERIOR_SIGIL_OF_FORCE_ID != self.SUPERIOR_SIGIL_OF_STRENGTH_ID else 0
        )

        p1_check = "[x]" if (owned_dusk > 0 or has_twilight) else "[ ]"
        p2_check = "[x]" if (has_exploration and has_battle and obsidian_count >= 250 and (has_bloodstone or spirit_shards >= 200)) else "[ ]"
        p3_check = "[x]" if (clover_count >= 77 and ecto_count >= 250 and t6_owned >= t6_total_needed) else "[ ]"
        p4_check = "[x]" if (has_gift_twilight or (has_metal and has_darkness and runestone_count >= 100 and sigil_count > 0 and weaponsmith_level >= 400 and armorsmith_level >= 400)) else "[ ]"

        staging_check_desc = (
            "📋 4-Pillar Inventory Staging Checklist before the final forge step (validate all 4 pillars with live inventory checks):\n"
            f"       • {p1_check} **Pillar 1: Dusk** `[&AgEpZgAA]` (Precursor item:29185, Exotic Precursor Greatsword)\n"
            f"       • {p2_check} **Pillar 2: Gift of Twilight** `[&AgHiEAAA]` (item:19674/GiftOfTwilight compound: Gift of Metal `[&AgHhEAAA]` + Gift of Darkness `[&AgHnEAAA]` + 100 Icy Runestones `[&AgHSEAAA]` + Superior Sigil of Force `[&AgHjVQAA]`)\n"
            f"       • {p3_check} **Pillar 3: Gift of Mastery** `[&AgHkEAAA]` (Gift of Exploration `[&AgHqEAAA]` + Gift of Battle `[&AgHrEAAA]` + Bloodstone Shard `[&AgHnEAAA]` + 250 Obsidian Shards `[&AgFdEAAA]`)\n"
            f"       • {p4_check} **Pillar 4: Gift of Fortune** `[&AgHlEAAA]` (77 Mystic Clovers `[&AgH2EAAA]` + 250 Ectos / Globs of Ectoplasm `[&AgH1EAAA]` + Gift of Magic `[&AgHjEAAA]` + Gift of Might `[&AgHmEAAA]`)"
        )
        c4_actions.append(JourneyAction(
            action_title="📋 4-Pillar Inventory Staging Checklist",
            action_description=staging_check_desc,
            estimated_minutes=2,
            priority="CRITICAL",
            zone_name=staging_check_zone,
            waypoint=staging_check_wp,
            game_mode="Account",
            assigned_character=forge_assign
        ))

        # Step 5: Final Forge Assembly
        if has_twilight:
            c4_readiness = 100.0
            if lounge and len(c4_actions) == 1:
                c4_actions = []
        else:
            if lounge:
                final_desc = f"Combine Dusk, Gift of Twilight, Gift of Mastery, and Gift of Fortune at the Mystic Forge in {lounge_zone} `{lounge_link}`."
                final_wp = lounge_link
                final_zone = lounge_zone
                final_npc = None
            else:
                final_desc = "Combine Dusk, Gift of Twilight, Gift of Mastery, and Gift of Fortune at Miyani `[&BBAEAAA=]` in Lion's Arch."
                final_wp = "[&BBAEAAA=]"
                final_zone = "Lion's Arch"
                final_npc = "Miyani"
            c4_actions.append(JourneyAction(
                action_title="Final Forge Assembly",
                action_description=final_desc,
                estimated_minutes=10,
                priority="CRITICAL",
                zone_name=final_zone,
                waypoint=final_wp,
                npc_name=final_npc,
                game_mode="Crafting",
                assigned_character=forge_assign
            ))
            if has_gift_twilight and weaponsmith_level >= 400 and armorsmith_level >= 400:
                c4_readiness += 25.0

        # Step 6: Post-Forge Decision Fork
        char_count = len(account.characters) if (account.characters and len(account.characters) > 0) else 11
        fork_wp = lounge_link if lounge else "[&BBAEAAA=]"
        fork_zone = lounge_zone if lounge else "Lion's Arch"
        eternity_gross = tp_prices.get(30689, 3800.0)
        eternity_net = round(eternity_gross * 0.85, 1)
        twilight_gross = tp_prices.get(self.TWILIGHT_ID, 1900.0)
        twilight_net = round(twilight_gross * 0.85, 1)

        fork_desc = (
            f"Post-Forge Decision Fork after Twilight is crafted (choose your post-crafting trajectory):\n"
            f"       • 🛡️ **Path A: Legendary Armory Binding (0g | Infinite Account Utility):**\n"
            f"         -> Deposit Twilight `[&AgErZgAA]` into your Legendary Armory (Unlocks unlimited Twilight copies across all {char_count} characters, instant free stat swapping [Berserker, Viper, Celestial, Dragon], and free sigil/infusion extraction).\n"
            f"         -> Permanently unlocks the Twilight skin in your Wardrobe + grants 'Memory of Twilight' token.\n"
            f"       • 💰 **Path B: The Eternity Commercial Arbitrage Loop (~3,800g Gross | ~3,230g Net Cash):**\n"
            f"         -> Combine unbound Twilight `[&AgErZgAA]` + unbound Sunrise `[&AgG2TAEA]` (crafted using your 2nd Gift of Exploration from Map Completion) + 5x Crystalline Dust `[&AgF4WwEA]` + 10x Philosopher's Stones `[&AgH1EAAA]` in the Mystic Forge to craft unbound Eternity [&AgExZwAA].\n"
            f"         -> ✨ **Skin Retention Dynamics:** Forging Eternity **instantly unlocks BOTH the Twilight and Sunrise skins in your Wardrobe permanently**!\n"
            f"         -> Sell unbound Eternity on the Trading Post for ~3,800g (~3,230g net cash after 15% TP fees), yielding **~1,800g pure profit** (+1,430g to +1,730g profit) while permanently retaining Twilight and Sunrise skins!\n"
            f"       • ⚖️ **Path C: Direct Trading Post Sale (~1,900g TP listing -> ~1,615g net cash):**\n"
            f"         -> Sell unbound Twilight directly on the Trading Post (~1,900g TP listing -> ~1,615g net cash after 15% TP fees).\n"
            f"         -> ⚠️ **Skin Warning:** Direct TP sale does NOT unlock the Twilight skin in your Wardrobe (unlike Eternity forge arbitrage which retains both skins)."
        )
        c4_actions.append(JourneyAction(
            action_title="🔮 Post-Forge Decision Fork (Armory Binding vs Eternity Arbitrage vs TP Sale)",
            action_description=fork_desc,
            estimated_minutes=5,
            priority="HIGH",
            zone_name=fork_zone,
            waypoint=fork_wp,
            game_mode="Account",
            assigned_character=forge_assign
        ))

        if lounge:
            ch4_summary = f"🌟 VIP Lounge ({lounge_name}) unified crafting, Invisible Bag staging, 4-Pillar Staging Checklist, final assembly of Twilight at the Mystic Forge, and Post-Forge Decision Fork with zero travel costs and instant map return."
        else:
            ch4_summary = "Crafting preparation, Invisible Bag staging, 4-Pillar Staging Checklist, final assembly of Twilight at the Mystic Forge, and Post-Forge Decision Fork."

        chapters.append(JourneyChapter(
            chapter_number=4,
            chapter_title="The Forge Ceremony & Character Hand-offs",
            chapter_summary=ch4_summary,
            actions=c4_actions,
            completion_status="COMPLETED" if c4_readiness >= 99.0 else "IN_PROGRESS",
            readiness_pct=round(c4_readiness, 1)
        ))

        return chapters

    def _build_master_chapters_generic(
        self,
        account: AccountState,
        tp_prices: Dict[int, float],
        diff_report: AccountDiffReport,
        wizards_vault_exhausted: bool,
        optimize_for_cost: bool,
        bom: Dict[str, Any],
    ) -> List[JourneyChapter]:
        """Builds the 4-Chapter Master Sequencer dynamically for any Gen 1, Gen 2, or Gen 3 Legendary Weapon."""
        target_id = bom["target_item_id"]
        target_name = bom["target_item_name"]
        gen = bom["generation"]
        prec_id = bom["precursor_id"]
        prec_name = bom["precursor_name"]
        tribute_name = bom["tribute_gift_name"]
        mastery_name = bom["mastery_gift_name"]
        specific_name = bom["specific_gift_name"]
        req_clovers = int(bom["required_clovers"])
        req_t6_total = int(bom["required_t6_total"])
        sub_gifts = bom.get("sub_gifts", [])

        owned_prec = account.total_item_count(prec_id)
        has_target = account.has_legendary_unlocked(target_id)

        # Chapter 1: Precursor Decision
        c1_actions: List[JourneyAction] = []
        if owned_prec > 0 or has_target:
            c1_status = "COMPLETED"
            c1_readiness = 100.0
        else:
            c1_status = "NOT_STARTED"
            c1_readiness = 0.0
            if gen == "GEN2":
                c1_actions.append(JourneyAction(
                    action_title=f"Complete 4-Tier Collection Hunt for {prec_name}",
                    action_description=(
                        f"Begin '{target_name} I-IV' with Grandmaster Craftsman Hobbs `[&BBAEAAA=]` in Lion's Arch. "
                        f"Gen 2 precursor '{prec_name}' is account-bound and crafted via Heart of Maguuma collections and daily Spiritwood/Deldrimor materials."
                    ),
                    estimated_minutes=60,
                    priority="CRITICAL",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Grandmaster Craftsman Hobbs",
                    game_mode="OpenWorld",
                    requires_expansion="HeartOfThorns",
                ))
            elif gen == "GEN3":
                prec_price = tp_prices.get(prec_id, 380.0)
                c1_actions.append(JourneyAction(
                    action_title=f"Acquire {prec_name} (Trading Post vs Arborstone Crafting)",
                    action_description=(
                        f"Purchase {prec_name} on the Trading Post (~{prec_price:.0f}g) or craft via Leivas `[&BGUNAAA=]` in Arborstone "
                        f"(requires 100x Memories of Aurene, 5x Antique Summoning Stones, 10x Jade Runestones, 25x Tales of Adventure)."
                    ),
                    estimated_minutes=15,
                    priority="CRITICAL",
                    zone_name="Arborstone",
                    waypoint="[&BGUNAAA=]",
                    npc_name="Leivas",
                    game_mode="OpenWorld",
                    requires_expansion="EndOfDragons",
                ))
            else:
                prec_price = tp_prices.get(prec_id, 180.0)
                c1_actions.append(JourneyAction(
                    action_title=f"Acquire Precursor: {prec_name}",
                    action_description=(
                        f"Acquire {prec_name} via Wizard's Vault Starter Kit (0g if available), Trading Post Direct Purchase (~{prec_price:.0f}g), "
                        f"or Grandmaster Hobbs Collection ({prec_name} I, II, III) at `[&BBAEAAA=]`."
                    ),
                    estimated_minutes=15,
                    priority="CRITICAL",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    npc_name="Grandmaster Craftsman Hobbs",
                    game_mode="OpenWorld",
                ))
                prereq, has_bit_progress, missing_bits_summary = self._get_precursor_collection_bit_status(target_id, account)
                if has_bit_progress and prereq and missing_bits_summary:
                    first_missing = prereq.precursor_missing_bits_detail[0] if prereq.precursor_missing_bits_detail else {}
                    first_zone = str(first_missing.get("zone") or "Lion's Arch")
                    first_wp = str(first_missing.get("waypoint") or "[&BBAEAAA=]")
                    c1_actions.append(JourneyAction(
                        action_title=(
                            f"Complete Remaining Collection Bits: {prereq.precursor_collection_step} "
                            f"({prereq.precursor_collection_bits_done}/{prereq.precursor_collection_bits_total})"
                        ),
                        action_description=missing_bits_summary,
                        estimated_minutes=20,
                        priority="HIGH",
                        zone_name=first_zone,
                        waypoint=first_wp,
                        npc_name="Grandmaster Craftsman Hobbs",
                        game_mode="OpenWorld",
                    ))
                    if prereq.precursor_collection_bits_total > 0:
                        c1_readiness = round(
                            (prereq.precursor_collection_bits_done / float(prereq.precursor_collection_bits_total)) * 100.0,
                            1,
                        )
                        c1_status = "IN_PROGRESS"

        ch1 = JourneyChapter(
            chapter_number=1,
            chapter_title=f"The Precursor Decision ({prec_name})",
            chapter_summary=f"Evaluate acquisition methods for {prec_name} ({gen} precursor to {target_name}).",
            actions=c1_actions,
            completion_status=c1_status,
            readiness_pct=c1_readiness,
        )

        # Chapter 2: Regional Exploration & Mastery
        mobility_char = self._find_mobility_character_name(account)
        c2_actions: List[JourneyAction] = []
        if gen == "GEN2":
            ch2_title = f"The Heart of Maguuma Expedition ({mastery_name})"
            ch2_summary = "Complete Verdant Brink, Auric Basin, Tangled Depths, and Dragon's Stand + 250x Crystalline Ingots."
            c2_actions.append(JourneyAction(
                action_title="Complete Heart of Maguuma Map Completion & Dragon's Stand Meta",
                action_description=f"Explore all 4 Heart of Thorns maps on {mobility_char} and farm 250x Crystalline Ore from Dragon's Stand `[&BBAIAAA=]` for {mastery_name}.",
                estimated_minutes=180,
                priority="HIGH",
                zone_name="Dragon's Stand",
                waypoint="[&BBAIAAA=]",
                game_mode="OpenWorld",
                assigned_character=mobility_char,
                requires_expansion="HeartOfThorns",
            ))
            c2_readiness = 50.0
        elif gen == "GEN3":
            ch2_title = f"The Canthan Expedition ({mastery_name})"
            ch2_summary = "Complete Seitung Province, New Kaineng City, The Echovald Wilds, and Dragon's End (or Imperial Lanterns) for Gift of Cantha."
            c2_actions.append(JourneyAction(
                action_title="Complete Cantha Maps or Light Imperial Lanterns for Gift of Cantha",
                action_description=f"Complete all 4 End of Dragons maps on {mobility_char} and earn 2,500 Imperial Favor for {mastery_name}.",
                estimated_minutes=150,
                priority="HIGH",
                zone_name="Seitung Province",
                waypoint="[&BGUNAAA=]",
                game_mode="OpenWorld",
                assigned_character=mobility_char,
                requires_expansion="EndOfDragons",
            ))
            c2_readiness = 50.0
        else:
            has_exp = account.total_item_count(self.GIFT_OF_EXPLORATION_ID) > 0
            ch2_title = "The Core Tyria Expedition (The World Tour)"
            ch2_summary = f"5-region geographical route for Gift of Exploration (satisfying {target_name} and providing a spare for your next Gen 1 legendary)."
            if not has_exp:
                c2_actions.append(JourneyAction(
                    action_title="Core Tyria Map Completion (2x Gifts of Exploration)",
                    action_description=f"Complete 100% Core Tyria Map Completion on {mobility_char} to earn 2x Gifts of Exploration for {target_name}.",
                    estimated_minutes=180,
                    priority="HIGH",
                    game_mode="OpenWorld",
                    assigned_character=mobility_char,
                ))
            c2_readiness = 100.0 if has_exp else 50.0

        ch2 = JourneyChapter(
            chapter_number=2,
            chapter_title=ch2_title,
            chapter_summary=ch2_summary,
            actions=c2_actions,
            completion_status="COMPLETED" if c2_readiness >= 100.0 else "IN_PROGRESS",
            readiness_pct=c2_readiness,
        )

        # Chapter 3: Tribute, Currencies & Time-Gates
        clover_count = account.total_item_count(self.MYSTIC_CLOVER_ID)
        needed_clovers = max(0, req_clovers - clover_count)
        t6_owned = sum(account.total_item_count(mat_id) for mat_id in set(self.T6_MATERIAL_IDS + self.LEGACY_T6_MATERIAL_IDS))
        needed_t6 = max(0, req_t6_total - t6_owned)

        c3_actions: List[JourneyAction] = [
            JourneyAction(
                action_title=f"Acquire {req_clovers}x Mystic Clovers for {tribute_name}",
                action_description=f"You have {clover_count}/{req_clovers} Mystic Clovers (need {needed_clovers} more) for {tribute_name}. Purchase 2/day from BUY-2046 `[&DYEFAAA=]` or claim from Wizard's Vault.",
                estimated_minutes=10,
                priority="CRITICAL",
                zone_name="Mistlock Observatory",
                waypoint="[&DYEFAAA=]",
                npc_name="BUY-2046",
                game_mode="Account",
            ),
            JourneyAction(
                action_title=f"Gather T6 Fine Materials ({req_t6_total:,} total for {tribute_name})",
                action_description=f"Acquire {bom['required_t6_per_type']}x of each Tier 6 fine material ({req_t6_total:,} total; need {needed_t6} more) via Volatile Magic Trophy Shipments `[&BNoLAAA=]` or Laurel Heavy Crafting Bags `[&BBAEAAA=]`.",
                estimated_minutes=25,
                priority="HIGH",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Account",
            ),
        ]
        if bom.get("dungeon_gift_name"):
            dg_name = bom["dungeon_gift_name"]
            c3_actions.append(JourneyAction(
                action_title=f"Acquire {dg_name} (500 Tales of Dungeon Delving)",
                action_description=f"Run explorable dungeon paths to earn 500 Tales of Dungeon Delving and purchase {dg_name} from the Dungeon Vendor in Lion's Arch `[&BBAEAAA=]`.",
                estimated_minutes=35,
                priority="HIGH",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                game_mode="Dungeon",
            ))
        for gate in bom.get("time_gates", []):
            gate_name = gate.get("name", str(gate)) if isinstance(gate, dict) else str(gate)
            if "Clover" not in gate_name:
                c3_actions.append(JourneyAction(
                    action_title=f"⏳ Time-Gate Cadence: {gate_name}",
                    action_description=f"Maintain daily/weekly cadence for {gate_name} required by {target_name}.",
                    estimated_minutes=10,
                    priority="HIGH",
                    zone_name="Lion's Arch",
                    waypoint="[&BBAEAAA=]",
                    game_mode="Crafting",
                ))

        ch3 = JourneyChapter(
            chapter_number=3,
            chapter_title=f"{tribute_name}, Currencies & Time-Gated Rituals",
            chapter_summary=f"Complete {tribute_name} ({req_clovers}x Mystic Clovers, {req_t6_total:,}x T6 materials) and time-gated components.",
            actions=c3_actions,
            completion_status="IN_PROGRESS",
            readiness_pct=round(min(100.0, (clover_count / float(req_clovers)) * 50.0 + (t6_owned / float(req_t6_total)) * 50.0), 1),
        )

        # Chapter 4: The Forge Ceremony
        sub_gift_names = ", ".join(sg[1] for sg in sub_gifts) if sub_gifts else specific_name
        c4_actions = [
            JourneyAction(
                action_title=f"Craft {specific_name}",
                action_description=f"Combine {sub_gift_names} at the Mystic Forge `[&BBAEAAA=]` to create {specific_name}.",
                estimated_minutes=10,
                priority="CRITICAL",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                npc_name="Miyani",
                game_mode="Crafting",
            ),
            JourneyAction(
                action_title=f"Final Forge Assembly: {target_name}",
                action_description=f"Combine {prec_name}, {specific_name}, {mastery_name}, and {tribute_name} in the Mystic Forge at Miyani `[&BBAEAAA=]` to forge {target_name}!",
                estimated_minutes=10,
                priority="CRITICAL",
                zone_name="Lion's Arch",
                waypoint="[&BBAEAAA=]",
                npc_name="Miyani",
                game_mode="Crafting",
            ),
        ]
        ch4 = JourneyChapter(
            chapter_number=4,
            chapter_title=f"The Forge Ceremony ({target_name})",
            chapter_summary=f"Stage {prec_name}, {specific_name}, {mastery_name}, and {tribute_name} and assemble {target_name} at the Mystic Forge.",
            actions=c4_actions,
            completion_status="COMPLETED" if has_target else "IN_PROGRESS",
            readiness_pct=100.0 if has_target else 25.0,
        )

        return [ch1, ch2, ch3, ch4]


# Generalized aliases & module-level convenience functions
LegendaryJourneySolver = TwilightJourneySolver


def solve_twilight_journey(
    account: Optional[AccountState] = None,
    store: Optional[PrioryGraphStore] = None,
    tp_prices: Optional[Dict[int, float]] = None,
    time_budget_minutes: int = 90,
    wizards_vault_exhausted: bool = False,
    optimize_for_cost: bool = True,
    excluded_modes: Optional[List[str]] = None,
    preferred_modes: Optional[List[str]] = None,
    target_item_id: Optional[int] = None,
) -> TwilightJourneyPlan:
    """Module-level helper to solve a legendary weapon journey (defaults to ontology-resolved Twilight)."""
    solver = TwilightJourneySolver(store)
    return solver.solve_twilight_journey(
        account=account,
        tp_prices=tp_prices,
        time_budget_minutes=time_budget_minutes,
        wizards_vault_exhausted=wizards_vault_exhausted,
        optimize_for_cost=optimize_for_cost,
        excluded_modes=excluded_modes,
        preferred_modes=preferred_modes,
        target_item_id=target_item_id,
    )


def solve_legendary_journey(
    target_item_id: Optional[int] = None,
    account: Optional[AccountState] = None,
    store: Optional[PrioryGraphStore] = None,
    tp_prices: Optional[Dict[int, float]] = None,
    time_budget_minutes: int = 90,
    wizards_vault_exhausted: bool = False,
    optimize_for_cost: bool = True,
    excluded_modes: Optional[List[str]] = None,
    preferred_modes: Optional[List[str]] = None,
) -> TwilightJourneyPlan:
    """Module-level helper to solve any Gen 1, Gen 2, or Gen 3 legendary weapon journey."""
    return solve_twilight_journey(
        account=account,
        store=store,
        tp_prices=tp_prices,
        time_budget_minutes=time_budget_minutes,
        wizards_vault_exhausted=wizards_vault_exhausted,
        optimize_for_cost=optimize_for_cost,
        excluded_modes=excluded_modes,
        preferred_modes=preferred_modes,
        target_item_id=target_item_id,
    )


def __getattr__(name: str) -> Any:
    if name == "TWILIGHT_ITEM_ID":
        return TwilightJourneySolver().TWILIGHT_ID
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

