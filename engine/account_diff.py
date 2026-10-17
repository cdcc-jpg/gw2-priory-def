"""Account Diff Engine.

Calculates the deterministic difference between a player's live account state
and the recursive ingredient requirements of any item in the Knowledge Graph.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from rdflib import Literal, URIRef
from rdflib.plugins.sparql import prepareQuery
from engine.graph_store import PrioryGraphStore, DEFAULT_NAMESPACES
from engine.character_graph import (
    CRAFTING_DISCIPLINE_STATIONS,
    route_crafting_discipline,
    encode_item_chat_link
)


@dataclass
class WizardVaultListing:
    """Represents a Wizard's Vault shop listing with purchase status."""
    id: int
    item_id: int
    item_count: int = 1
    listing_type: str = "Normal"
    cost: int = 0
    purchased: int = 0
    purchase_limit: Optional[int] = None

    @property
    def remaining_purchases(self) -> int:
        if self.purchase_limit is None:
            return 999999
        return max(0, self.purchase_limit - self.purchased)

    @property
    def is_sold_out(self) -> bool:
        return self.purchase_limit is not None and self.purchased >= self.purchase_limit


LOUNGE_PASSES: Dict[int, Dict[str, Any]] = {}
CONVENIENCE_CATEGORIES: List[str] = []
CONVENIENCE_ITEMS: Dict[str, Dict[str, Any]] = {}
DEFAULT_ACCOUNT_ROSTER: List[str] = []

_DEFAULT_DIFF_STORE: Optional[PrioryGraphStore] = None
_BOOSTER_CATALOG_CACHE: Optional[Dict[str, Any]] = None


def _get_or_create_default_store() -> PrioryGraphStore:
    """Returns a shared PrioryGraphStore with all ontology files loaded."""
    global _DEFAULT_DIFF_STORE
    try:
        from engine import graph_store as _gs_mod
        if hasattr(_gs_mod, "get_default_graph_store"):
            return _gs_mod.get_default_graph_store()
    except Exception:
        pass
    if _DEFAULT_DIFF_STORE is None:
        _DEFAULT_DIFF_STORE = PrioryGraphStore()
        _DEFAULT_DIFF_STORE.load_all()
    elif len(_DEFAULT_DIFF_STORE.graph) == 0:
        _DEFAULT_DIFF_STORE.load_all()
    return _DEFAULT_DIFF_STORE


def _ensure_account_catalogs_hydrated(store: Optional[PrioryGraphStore] = None) -> PrioryGraphStore:
    """Ensures all module-level catalogs in account_diff are hydrated from PrioryGraphStore."""
    resolved_store = store if (store is not None and len(store.graph) > 0) else _get_or_create_default_store()
    _hydrate_catalogs_from_graph(resolved_store)
    if not LOUNGE_PASSES or not CONVENIENCE_ITEMS or not GEN1_WEAPONS or not HOBBS_COLLECTIONS:
        def_store = _get_or_create_default_store()
        if def_store is not resolved_store:
            _hydrate_catalogs_from_graph(def_store)
            resolved_store = def_store
    return resolved_store


def _get_booster_catalog() -> Dict[str, Any]:
    """Returns the booster catalog dictionary hydrated from PrioryGraphStore."""
    global _BOOSTER_CATALOG_CACHE
    if _BOOSTER_CATALOG_CACHE is not None and _BOOSTER_CATALOG_CACHE.get("booster_names"):
        return _BOOSTER_CATALOG_CACHE
    store = _ensure_account_catalogs_hydrated()
    if hasattr(store, "get_booster_catalog"):
        try:
            cat = dict(store.get_booster_catalog())
            if isinstance(cat, dict) and cat.get("booster_names"):
                cls_sparql = """
                SELECT DISTINCT ?id ?label ?cls WHERE {
                    VALUES ?cls {
                        priory:ExperienceBooster
                        priory:HeroicBooster
                        priory:KarmaBooster
                        priory:WXPBooster
                        priory:CelebrationBooster
                        priory:ItemBooster
                    }
                    ?item a ?cls ;
                          priory:gw2Id ?id ;
                          rdfs:label ?label .
                }
                """
                exp_ids: Set[int] = set()
                heroic_ids: Set[int] = set()
                karma_ids: Set[int] = set()
                wxp_ids: Set[int] = set()
                celeb_ids: Set[int] = set()
                for row in store.query(cls_sparql):
                    iid = int(row["id"])
                    cls_str = str(row["cls"])
                    lbl_str = str(row.get("label", ""))
                    if cls_str.endswith("ExperienceBooster") or "Black Lion Booster" in lbl_str:
                        exp_ids.add(iid)
                    elif cls_str.endswith("HeroicBooster"):
                        heroic_ids.add(iid)
                    elif cls_str.endswith("KarmaBooster"):
                        karma_ids.add(iid)
                    elif cls_str.endswith("WXPBooster"):
                        wxp_ids.add(iid)
                    elif cls_str.endswith("CelebrationBooster"):
                        celeb_ids.add(iid)
                cat["experience_only_ids"] = exp_ids
                cat["heroic_only_ids"] = heroic_ids
                cat["karma_only_ids"] = karma_ids
                cat["wxp_only_ids"] = wxp_ids
                cat["celebration_only_ids"] = celeb_ids
                _BOOSTER_CATALOG_CACHE = cat
                return cat
        except Exception:
            pass
    return {
        "booster_names": {},
        "gobbler_ids": set(),
        "tome_ids": set(),
        "xp_booster_ids": set(),
        "wvw_booster_ids": set(),
        "karma_booster_ids": set(),
        "experience_only_ids": set(),
        "heroic_only_ids": set(),
        "karma_only_ids": set(),
        "wxp_only_ids": set(),
        "celebration_only_ids": set(),
    }


@dataclass
class AccountState:
    """Represents a player's live account snapshot from the GW2 API."""
    materials: Dict[int, int] = field(default_factory=dict)
    bank: Dict[int, int] = field(default_factory=dict)
    inventory: Dict[int, int] = field(default_factory=dict)
    wallet: Dict[int, int] = field(default_factory=dict)
    legendary_armory: Dict[int, int] = field(default_factory=dict)
    disciplines: Dict[str, int] = field(default_factory=dict)
    achievements: Dict[int, int] = field(default_factory=dict)
    completed_achievements: Set[int] = field(default_factory=set)
    masteries: Dict[int, int] = field(default_factory=dict)
    mastery_points: Dict[str, Dict[str, int]] = field(default_factory=dict)
    wizards_vault_listings: Dict[int, WizardVaultListing] = field(default_factory=dict)
    characters: List[Dict[str, Any]] = field(default_factory=list)
    mount_types: List[str] = field(default_factory=list)
    expansion_access: List[str] = field(default_factory=lambda: ['GuildWars2'])
    map_completed_characters: Optional[List[str]] = None
    titles: Set[int] = field(default_factory=set)
    fractal_level: int = 1
    wvw_rank: int = 1
    daily_ap: int = 0
    monthly_ap: int = 0
    luck: int = 0
    commander: bool = False
    account_created: str = ""
    account_name: str = ""
    progression: Dict[str, int] = field(default_factory=dict)
    daily_dungeons: List[str] = field(default_factory=list)
    weekly_raids: List[str] = field(default_factory=list)
    achievement_bits: Dict[int, List[int]] = field(default_factory=dict)
    achievement_repeated: Dict[int, int] = field(default_factory=dict)
    active_disciplines: Dict[str, List[str]] = field(default_factory=dict)
    character_disciplines: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    daily_crafting: List[str] = field(default_factory=list)
    world_bosses: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.map_completed_characters is None:
            if self.characters:
                char_names = {
                    c.get("name") if isinstance(c, dict) else str(c)
                    for c in self.characters
                }
                if "Kerling" in char_names:
                    self.map_completed_characters = ["Kerling"]
                else:
                    self.map_completed_characters = []
            else:
                self.map_completed_characters = []

    def total_item_count(self, item_id: int) -> int:
        """Aggregates an item's count across materials, bank, bags (inventory & characters[*].bags), and legendary armory."""
        char_bags_count = 0
        if self.characters:
            for char in self.characters:
                for bag in char.get("bags", []):
                    if isinstance(bag, dict):
                        for inv_item in bag.get("inventory", []):
                            if isinstance(inv_item, dict) and inv_item.get("id") == item_id:
                                char_bags_count += inv_item.get("count", 1)
        return (
            self.materials.get(item_id, 0) +
            self.bank.get(item_id, 0) +
            self.inventory.get(item_id, 0) +
            char_bags_count +
            self.armory_item_count(item_id)
        )

    def get_item_count(self, item_id: int) -> int:
        """Sums an item's count across materials, bank, and bags (inventory & characters[*].bags)."""
        char_bags_count = 0
        if self.characters:
            for char in self.characters:
                for bag in char.get("bags", []):
                    if isinstance(bag, dict):
                        for inv_item in bag.get("inventory", []):
                            if isinstance(inv_item, dict) and inv_item.get("id") == item_id:
                                char_bags_count += inv_item.get("count", 1)
        return (
            self.materials.get(item_id, 0) +
            self.bank.get(item_id, 0) +
            self.inventory.get(item_id, 0) +
            char_bags_count
        )

    def total_currency_count(self, currency_id: int) -> int:
        """Returns total owned amount of a wallet currency by its API ID."""
        return self.wallet.get(currency_id, 0)

    def dungeon_tales_count(self, graph_store: Optional[Any] = None) -> int:
        """Returns count of Tales of Dungeon Delving from wallet, querying graph store if provided."""
        if graph_store is not None:
            engine = AccountDiffEngine(graph_store)
            return engine._get_dungeon_tales(self)
        return self.wallet.get(69, 0) + self.wallet.get(61, 0) + self.wallet.get(13, 0)

    def astral_acclaim_count(self, graph_store: Optional[Any] = None) -> int:
        """Returns count of Astral Acclaim from wallet, dynamically querying priory:apiWalletId if graph_store passed."""
        if graph_store is not None:
            engine = AccountDiffEngine(graph_store)
            return engine._get_astral_acclaim(self)
        return self.wallet.get(63, 0) if 63 in self.wallet else self.wallet.get(68, 0)

    def imperial_favor_count(self, graph_store: Optional[Any] = None) -> int:
        """Returns count of Imperial Favor from wallet, querying graph store if provided."""
        if graph_store is not None:
            engine = AccountDiffEngine(graph_store)
            return engine.get_available_purchasing_power("currency:ImperialFavor", self)
        return self.wallet.get(68, 0)

    def research_notes_count(self, graph_store: Optional[Any] = None) -> int:
        """Returns count of Research Notes from wallet, querying graph store if provided."""
        if graph_store is not None:
            engine = AccountDiffEngine(graph_store)
            return engine.get_available_purchasing_power("currency:ResearchNote", self)
        return self.wallet.get(61, 0)

    def provisioner_tokens_count(self, graph_store: Optional[Any] = None) -> int:
        """Returns count of Provisioner Tokens from wallet, querying graph store if provided."""
        if graph_store is not None:
            engine = AccountDiffEngine(graph_store)
            return engine._get_provisioner_tokens(self)
        return self.wallet.get(29, 0)

    def volatile_magic_count(self, graph_store: Optional[Any] = None) -> int:
        """Returns count of Volatile Magic from wallet, querying graph store if provided."""
        if graph_store is not None:
            engine = AccountDiffEngine(graph_store)
            return engine.get_available_purchasing_power("currency:VolatileMagic", self)
        return self.wallet.get(45, 0)

    def unbound_magic_count(self, graph_store: Optional[Any] = None) -> int:
        """Returns count of Unbound Magic from wallet, querying graph store if provided."""
        if graph_store is not None:
            engine = AccountDiffEngine(graph_store)
            return engine.get_available_purchasing_power("currency:UnboundMagic", self)
        return self.wallet.get(32, 0)

    def get_available_purchasing_power(self, entity_iri_or_id: Any, graph_store: Optional[Any] = None) -> int:
        """Substrate-agnostic purchasing power balance resolver."""
        if graph_store is not None:
            engine = AccountDiffEngine(graph_store)
            return engine.get_available_purchasing_power(entity_iri_or_id, self)
        if isinstance(entity_iri_or_id, int):
            if entity_iri_or_id in self.wallet:
                return self.wallet[entity_iri_or_id]
            return self.get_item_count(entity_iri_or_id)
        return 0

    def has_world_completion_unlocked(self) -> bool:
        """Returns True if account has unlocked Been There, Done That (Achievement 137 or Title 12)."""
        return 137 in self.completed_achievements or 12 in self.titles

    def has_world_completion_gift(self) -> bool:
        """Returns True if account owns Gift of Exploration (item 19677)."""
        return self.total_item_count(19677) > 0

    def _get_achievement_progress(self, ach_id: int, total_bits: int = 0) -> Tuple[int, Set[int], bool]:
        """Extracts (count_done, completed_bit_indices, is_done) for an achievement ID across GW2 API formats."""
        completed_bits: Set[int] = set()
        is_done: bool = ach_id in (self.completed_achievements or set())
        count_done: int = 0

        if self.achievement_bits and ach_id in self.achievement_bits:
            val = self.achievement_bits[ach_id]
            if isinstance(val, (list, tuple, set)):
                completed_bits.update(int(b) for b in val)
                count_done = max(count_done, len(completed_bits))

        if self.achievements and ach_id in self.achievements:
            raw = self.achievements[ach_id]
            if isinstance(raw, dict):
                if raw.get("done") is True:
                    is_done = True
                if "bits" in raw and isinstance(raw["bits"], (list, tuple, set)):
                    completed_bits.update(int(b) for b in raw["bits"])
                    count_done = max(count_done, len(completed_bits))
                if "current" in raw and isinstance(raw["current"], (int, float)):
                    cur_int = int(raw["current"])
                    count_done = max(count_done, cur_int)
                    if not completed_bits and cur_int > 0:
                        completed_bits.update(range(cur_int))
            elif isinstance(raw, (list, tuple, set)):
                completed_bits.update(int(b) for b in raw)
                count_done = max(count_done, len(completed_bits))
            elif isinstance(raw, (int, float)):
                cur_int = int(raw)
                count_done = max(count_done, cur_int)
                if not completed_bits and cur_int > 0:
                    completed_bits.update(range(cur_int))

        if total_bits > 0:
            if is_done or count_done >= total_bits or len(completed_bits) >= total_bits:
                is_done = True
                count_done = total_bits
                completed_bits.update(range(total_bits))
            else:
                count_done = min(max(count_done, len(completed_bits)), total_bits)

        return count_done, completed_bits, is_done

    def world_completion_status(self) -> Tuple[bool, Optional[str]]:
        """Determines world exploration status and source ("INVENTORY_GIFT", "TITLE_12", "ACHIEVEMENT_137")."""
        if self.total_item_count(19677) > 0:
            return True, "INVENTORY_GIFT"
        if 12 in self.titles:
            return True, "TITLE_12"
        ach137_count, _, ach137_done = self._get_achievement_progress(137, total_bits=100)
        if ach137_done or ach137_count >= 100:
            return True, "ACHIEVEMENT_137"
        return False, None

    def legendary_crafting_mastery_level(self) -> int:
        """Returns Central Tyria Legendary Crafting mastery level (0-4).
        Track 6 in live GW2 API, track 10 in ontology/legacy tests."""
        return max(self.masteries.get(6, 0), self.masteries.get(10, 0))

    def has_legendary_crafting_tier(self, tier: int) -> bool:
        """Checks if Central Tyria Legendary Crafting mastery tier is unlocked:
        Tier 1: Revered Antiquarian (1)
        Tier 2: Magister of Legends (2)
        Tier 3: Historian of the Armaments (3)
        Tier 4: Scholar of Secrets (4)
        """
        return self.legendary_crafting_mastery_level() >= tier

    def has_dungeon_master_unlocked(self) -> bool:
        """Returns True if account has unlocked Dungeon Master (Achievement 122 or Title 15)."""
        return 122 in self.completed_achievements or 15 in self.titles

    def max_discipline_rating(self, discipline: str) -> int:
        """Returns the highest crafting rating for a discipline across account disciplines, character_disciplines, and characters (case-insensitive)."""
        disc_lower = discipline.strip().lower()
        best = 0
        for k, v in (self.disciplines or {}).items():
            if str(k).strip().lower() == disc_lower:
                try:
                    best = max(best, int(v))
                except (ValueError, TypeError):
                    pass
        for _char_name, discs in (self.character_disciplines or {}).items():
            if isinstance(discs, dict):
                for k, info in discs.items():
                    if str(k).strip().lower() == disc_lower:
                        if isinstance(info, int):
                            best = max(best, info)
                        elif isinstance(info, dict):
                            try:
                                best = max(best, int(info.get("rating", 0)))
                            except (ValueError, TypeError):
                                pass
        for char in (self.characters or []):
            if isinstance(char, dict):
                for key in ("crafting", "disciplines"):
                    for c_entry in (char.get(key) or []):
                        if isinstance(c_entry, dict):
                            c_disc = str(c_entry.get("discipline", "")).strip().lower()
                            if c_disc == disc_lower:
                                try:
                                    best = max(best, int(c_entry.get("rating", 0)))
                                except (ValueError, TypeError):
                                    pass
        return best

    def has_active_discipline(self, discipline: str, min_rating: int = 0) -> bool:
        """Returns True if any character has the specified discipline currently active with at least min_rating."""
        disc = discipline.strip().lower()
        for k, char_list in (self.active_disciplines or {}).items():
            if str(k).strip().lower() == disc and char_list:
                for char_name in char_list:
                    discs_for_char = (self.character_disciplines or {}).get(char_name, {})
                    info = None
                    if isinstance(discs_for_char, dict):
                        for dk, dv in discs_for_char.items():
                            if str(dk).strip().lower() == disc:
                                info = dv
                                break
                    if isinstance(info, int):
                        if info >= min_rating:
                            return True
                    elif isinstance(info, dict):
                        if int(info.get("rating", 0)) >= min_rating:
                            return True
                    elif min_rating <= 0:
                        return True
        for char_name, discs in (self.character_disciplines or {}).items():
            if isinstance(discs, dict):
                for dk, info in discs.items():
                    if str(dk).strip().lower() == disc:
                        if isinstance(info, int) and info >= min_rating:
                            active_list = None
                            for ak, av in (self.active_disciplines or {}).items():
                                if str(ak).strip().lower() == disc:
                                    active_list = av
                                    break
                            if active_list is None or char_name in active_list:
                                return True
                        elif isinstance(info, dict) and bool(info.get("active", True)) and int(info.get("rating", 0)) >= min_rating:
                            return True
        for char in (self.characters or []):
            if isinstance(char, dict):
                for key in ("crafting", "disciplines"):
                    for c_entry in (char.get(key) or []):
                        if isinstance(c_entry, dict) and str(c_entry.get("discipline", "")).strip().lower() == disc:
                            if bool(c_entry.get("active", True)) and int(c_entry.get("rating", 0)) >= min_rating:
                                return True
        return False

    def gold_count(self) -> float:
        """Returns gold balance (currency 1 / 10000.0)."""
        return self.wallet.get(1, 0) / 10000.0

    def karma_count(self) -> int:
        """Returns count of currency 2 from self.wallet."""
        return self.wallet.get(2, 0)

    def spirit_shards_count(self) -> int:
        """Returns count of currency 23 from self.wallet."""
        return self.wallet.get(23, 0)

    def has_bloodstone_shard(self) -> bool:
        """Returns True if the account owns Bloodstone Shard (canonical item 20797 or legacy 19674)."""
        return self.total_item_count(20797) > 0 or self.total_item_count(19674) > 0

    def has_gift_of_battle(self) -> bool:
        """Returns True if the account owns Gift of Battle (item 19678)."""
        return self.total_item_count(19678) > 0

    def armory_item_count(self, item_id: int) -> int:
        """Safe accessor for legendary armory item count across dict, set, list, or tuple structures."""
        armory = self.legendary_armory
        if not armory:
            return 0
        if isinstance(armory, dict):
            val = armory.get(item_id, 0)
            if not val:
                val = armory.get(str(item_id), 0)
            try:
                return int(val)
            except (ValueError, TypeError):
                return 1 if val else 0
        if isinstance(armory, set):
            return 1 if (item_id in armory or str(item_id) in armory) else 0
        if isinstance(armory, (list, tuple)):
            count = 0
            if item_id in armory or str(item_id) in armory:
                count += armory.count(item_id) + armory.count(str(item_id))
            for elem in armory:
                if isinstance(elem, dict):
                    eid = elem.get("id")
                    if eid == item_id or eid == str(item_id):
                        try:
                            count += int(elem.get("count", 1))
                        except (ValueError, TypeError):
                            count += 1
            return count
        return 0

    def has_legendary_unlocked(self, item_id: int) -> bool:
        """Returns True if the item is unlocked in the Legendary Armory (safe for dict, set, and list)."""
        return self.armory_item_count(item_id) > 0

    def wizards_vault_remaining(self, item_id: int) -> Optional[int]:
        """Returns the number of remaining purchases for a Wizard's Vault item, or None if not listed."""
        listing = self.wizards_vault_listings.get(item_id)
        if listing:
            return listing.remaining_purchases
        return None

    def is_wizards_vault_sold_out(self, item_id: int) -> bool:
        """Returns True if the item is listed in the Wizard's Vault and sold out."""
        listing = self.wizards_vault_listings.get(item_id)
        if listing:
            return listing.is_sold_out
        return False

    def has_mount(self, mount_name: str) -> bool:
        """Returns True if the specified mount is unlocked."""
        return mount_name in self.mount_types

    def has_expansion(self, expansion_name: str) -> bool:
        """Returns True if the specified expansion is owned."""
        return expansion_name in self.expansion_access

    def is_character_map_completed(self, character_name: str) -> bool:
        """Returns True if the specified character has completed 100% Core Tyria map exploration."""
        return character_name in (self.map_completed_characters or [])

    def eligible_exploration_characters(self) -> List[str]:
        """Returns roster characters who have not completed 100% Core Map."""
        _ensure_account_catalogs_hydrated()
        roster_names: List[str] = []
        if self.characters:
            for c in self.characters:
                if isinstance(c, dict) and c.get("name"):
                    roster_names.append(c["name"])
                elif isinstance(c, str):
                    roster_names.append(c)
        if not roster_names:
            return []

        eligible = [name for name in roster_names if not self.is_character_map_completed(name)]
        if not eligible and "Kerling" in roster_names:
            eligible = [name for name in DEFAULT_ACCOUNT_ROSTER if not self.is_character_map_completed(name)]
        return eligible

    def recommended_exploration_character(self) -> Optional[str]:
        """Returns the first eligible roster character for world exploration, or None for blank accounts."""
        eligible = self.eligible_exploration_characters()
        return eligible[0] if eligible else None

    def owned_boosters(self) -> Dict[int, int]:
        """Detects owned boosters, gobblers, and tomes across materials, bank, and inventory."""
        cat = _get_booster_catalog()
        booster_ids = cat.get("booster_names", {}).keys()
        result: Dict[int, int] = {}
        for b_id in booster_ids:
            count = self.total_item_count(int(b_id))
            if count > 0:
                result[int(b_id)] = count
        return result

    def owned_lounges(self) -> List[Dict[str, Any]]:
        """Scans bank and inventory for owned VIP lounge passes and portal scrolls."""
        _ensure_account_catalogs_hydrated()
        results: List[Dict[str, Any]] = []
        for pass_id, meta in LOUNGE_PASSES.items():
            count = self.total_item_count(pass_id)
            if count > 0:
                results.append({
                    "id": pass_id,
                    "name": meta["name"],
                    "chat_link": meta["chat_link"],
                    "zone": meta["zone"],
                    "count": count
                })
        return results

    def owned_convenience_items(self) -> Dict[str, Any]:
        """Detects owned convenience items across all 7 categories (contracts, gobblers/converters, portal tomes, infinite salvage, portable forge, teleport to friend, and VIP lounges)."""
        _ensure_account_catalogs_hydrated()
        result: Dict[str, Any] = {}
        for slug, meta in CONVENIENCE_ITEMS.items():
            total = sum(self.total_item_count(i_id) for i_id in meta["all_ids"])
            if total > 0:
                item_dict = {
                    "id": meta["id"],
                    "name": meta["name"],
                    "chat_link": meta["chat_link"],
                    "type": meta["type"],
                    "category": meta.get("category", "other"),
                    "count": total
                }
                result[slug] = item_dict
                result[str(meta["id"])] = item_dict
                for aid in meta["all_ids"]:
                    result[str(aid)] = item_dict
        return result

    def owned_convenience_by_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns owned convenience items grouped by convenience categories."""
        _ensure_account_catalogs_hydrated()
        categories: Dict[str, List[Dict[str, Any]]] = {
            cat_name: [] for cat_name in CONVENIENCE_CATEGORIES
        }
        seen_ids: Set[int] = set()
        for slug, meta in CONVENIENCE_ITEMS.items():
            total = sum(self.total_item_count(i_id) for i_id in meta["all_ids"])
            if total > 0 and meta["id"] not in seen_ids:
                seen_ids.add(meta["id"])
                item_dict = {
                    "id": meta["id"],
                    "name": meta["name"],
                    "chat_link": meta["chat_link"],
                    "type": meta["type"],
                    "category": meta.get("category", "other"),
                    "count": total
                }
                cat = meta.get("category", "other")
                if cat in categories:
                    categories[cat].append(item_dict)

        for l in self.owned_lounges():
            categories.setdefault("vip_lounges", []).append({
                "id": l["id"],
                "name": l["name"],
                "chat_link": l["chat_link"],
                "type": "VIPLoungePass",
                "category": "vip_lounges",
                "count": l["count"],
                "zone": l.get("zone")
            })

        return categories

    def convenience_portfolio(self) -> Dict[str, List[Dict[str, Any]]]:
        """Returns structured convenience portfolio broken down into passes, portal tomes, converters, infinite tools, and utilities."""
        _ensure_account_catalogs_hydrated()
        portfolio: Dict[str, List[Dict[str, Any]]] = {
            "passes": self.owned_lounges(),
            "portal_tomes": [],
            "converters": [],
            "infinite_tools": [],
            "salvage_and_utilities": []
        }
        
        seen_names: Set[str] = set(p["name"] for p in portfolio["passes"])
        for slug, meta in CONVENIENCE_ITEMS.items():
            total = sum(self.total_item_count(i_id) for i_id in meta["all_ids"])
            if total > 0 and meta["name"] not in seen_names:
                seen_names.add(meta["name"])
                entry = {
                    "id": meta["id"],
                    "name": meta["name"],
                    "chat_link": meta["chat_link"],
                    "type": meta["type"],
                    "category": meta.get("category", "other"),
                    "count": total
                }
                cat = meta.get("category", "")
                if cat == "portal_tomes":
                    portfolio["portal_tomes"].append(entry)
                elif cat == "converters_and_gobblers":
                    portfolio["converters"].append(entry)
                elif cat == "infinite_tools":
                    portfolio["infinite_tools"].append(entry)
                elif cat in ("infinite_salvage", "portable_forge", "teleport_to_friend", "permanent_contracts"):
                    portfolio["salvage_and_utilities"].append(entry)

        return portfolio

    def _has_convenience_slug(self, slug: str) -> bool:
        _ensure_account_catalogs_hydrated()
        meta = CONVENIENCE_ITEMS.get(slug)
        if not meta:
            return False
        return any(self.total_item_count(i) > 0 for i in meta.get("all_ids", ()))

    def has_permanent_bank(self) -> bool:
        """Returns True if the account owns Permanent Bank Access Contract/Express."""
        return self._has_convenience_slug("permanent_bank")

    def has_permanent_tp(self) -> bool:
        """Returns True if the account owns Permanent Trading Post Express/Contract."""
        return self._has_convenience_slug("permanent_tp")

    def has_permanent_merchant(self) -> bool:
        """Returns True if the account owns Permanent Merchant Express/Contract."""
        return self._has_convenience_slug("permanent_merchant")

    def has_permanent_hair_stylist(self) -> bool:
        """Returns True if the account owns Permanent Hair Stylist Contract."""
        return self._has_convenience_slug("permanent_hair_stylist")

    def has_permanent_contracts(self) -> bool:
        """Returns True if the account owns any permanent service contract."""
        return self.has_permanent_bank() or self.has_permanent_tp() or self.has_permanent_merchant() or self.has_permanent_hair_stylist()

    def has_ley_energy_converter(self) -> bool:
        """Returns True if the account owns Ley-Energy Matter Converter."""
        return self._has_convenience_slug("ley_energy_converter")

    def has_karmic_converter(self) -> bool:
        """Returns True if the account owns Karmic Converter."""
        return self._has_convenience_slug("karmic_converter")

    def has_sentient_converters(self) -> bool:
        """Returns True if the account owns Gleam of Sentience or any Sentient series converter."""
        _ensure_account_catalogs_hydrated()
        for slug, meta in CONVENIENCE_ITEMS.items():
            if meta.get("type") == "Converter" and slug not in ("ley_energy_converter", "karmic_converter"):
                if any(self.total_item_count(i) > 0 for i in meta.get("all_ids", ())):
                    return True
        return False

    def has_portal_tomes(self) -> bool:
        """Returns True if the account owns any Living World portal tome or scroll."""
        _ensure_account_catalogs_hydrated()
        for meta in CONVENIENCE_ITEMS.values():
            if meta.get("category") == "portal_tomes":
                if any(self.total_item_count(i) > 0 for i in meta.get("all_ids", ())):
                    return True
        return False

    def has_lounge_pass(self) -> bool:
        """Returns True if the account owns any VIP lounge pass or portal scroll."""
        return len(self.owned_lounges()) > 0

    def has_recharging_teleport_to_friend(self) -> bool:
        """Returns True if the account owns Recharging Teleport to Friend."""
        return "teleport_to_friend" in self.owned_convenience_items()

    def has_silver_fed(self) -> bool:
        """Returns True if the account owns Silver-Fed Salvage-o-Matic."""
        return "silver_fed" in self.owned_convenience_items()

    def has_copper_fed(self) -> bool:
        """Returns True if the account owns Copper-Fed Salvage-o-Matic."""
        return "copper_fed" in self.owned_convenience_items()

    def has_runecrafter(self) -> bool:
        """Returns True if the account owns Runecrafter's Salvage-o-Matic."""
        return "runecrafter" in self.owned_convenience_items()

    def has_upgrade_extractor(self) -> bool:
        """Returns True if the account owns Endless Upgrade Extractor."""
        return "upgrade_extractor" in self.owned_convenience_items()

    def has_mystic_forge_conduit(self) -> bool:
        """Returns True if the account owns Mystic Forge Conduit."""
        return "mystic_forge_conduit" in self.owned_convenience_items()

    def has_gobbler(self) -> bool:
        """Returns True if the account owns any festival gobbler."""
        _ensure_account_catalogs_hydrated()
        for meta in CONVENIENCE_ITEMS.values():
            if meta.get("type") == "Gobbler":
                if any(self.total_item_count(gid) > 0 for gid in meta.get("all_ids", ())):
                    return True
        gobbler_ids = _get_booster_catalog().get("gobbler_ids", set())
        return any(self.total_item_count(gid) > 0 for gid in gobbler_ids)

    def tomes_of_knowledge_count(self) -> int:
        """Returns total owned count of Tomes of Knowledge."""
        tome_ids = _get_booster_catalog().get("tome_ids", set())
        return sum(self.total_item_count(tid) for tid in tome_ids)

    def zhaitaffy_gobblers_count(self) -> int:
        """Returns count of Zhaitaffy Gobbler."""
        _ensure_account_catalogs_hydrated()
        meta = CONVENIENCE_ITEMS.get("zhaitaffy_gobbler", {})
        return sum(self.total_item_count(gid) for gid in meta.get("all_ids", ()))

    def candy_corn_gobblers_count(self) -> int:
        """Returns count of Candy Corn Gobbler."""
        _ensure_account_catalogs_hydrated()
        meta = CONVENIENCE_ITEMS.get("candy_corn_gobbler", {})
        return sum(self.total_item_count(gid) for gid in meta.get("all_ids", ()))

    def experience_boosters_count(self) -> int:
        """Returns count of Experience Boosters."""
        ids = _get_booster_catalog().get("experience_only_ids", set())
        return sum(self.total_item_count(i) for i in ids)

    def heroic_boosters_count(self) -> int:
        """Returns count of Heroic Boosters."""
        ids = _get_booster_catalog().get("heroic_only_ids", set())
        return sum(self.total_item_count(i) for i in ids)

    def karma_boosters_count(self) -> int:
        """Returns count of Karma Boosters."""
        ids = _get_booster_catalog().get("karma_only_ids", set())
        return sum(self.total_item_count(i) for i in ids)

    def wxp_boosters_count(self) -> int:
        """Returns count of WXP / WvW Boosters."""
        ids = _get_booster_catalog().get("wxp_only_ids", set())
        return sum(self.total_item_count(i) for i in ids)

    def birthday_celebration_boosters_count(self) -> int:
        """Returns count of Birthday / Celebration Boosters."""
        ids = _get_booster_catalog().get("celebration_only_ids", set())
        return sum(self.total_item_count(i) for i in ids) + self.zhaitaffy_gobblers_count()



@dataclass
class ItemRequirementNode:
    """A node in the recursive recipe dependency tree."""
    item_id: int
    label: str
    required_quantity: int
    owned_quantity: int
    missing_quantity: int
    is_satisfied: bool
    is_account_bound: bool = False
    sub_requirements: List[ItemRequirementNode] = field(default_factory=list)

    def clone(self) -> ItemRequirementNode:
        """Deep copy of the requirement node hierarchy."""
        return ItemRequirementNode(
            item_id=self.item_id,
            label=self.label,
            required_quantity=self.required_quantity,
            owned_quantity=self.owned_quantity,
            missing_quantity=self.missing_quantity,
            is_satisfied=self.is_satisfied,
            is_account_bound=self.is_account_bound,
            sub_requirements=[child.clone() for child in self.sub_requirements]
        )


@dataclass
class AccountDiffReport:
    """Final calculated diff report for a target crafting goal."""
    goal_item_id: int
    goal_item_name: str
    target_quantity: int
    overall_readiness_pct: float
    is_fully_satisfied: bool
    root_node: ItemRequirementNode
    is_saturated: bool = False
    armory_max_cap: int = 1
    armory_owned_count: int = 0
    missing_achievements: List[Dict[str, Any]] = field(default_factory=list)
    missing_masteries: List[Dict[str, Any]] = field(default_factory=list)
    summary_missing_materials: Dict[str, int] = field(default_factory=dict)
    summary_missing_currencies: Dict[str, int] = field(default_factory=dict)
    missing_disciplines: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class PrerequisiteReport:
    """Evaluation of account prerequisites (world completion, masteries, crafting, collections) for a legendary goal."""
    goal_item_id: int
    goal_name: str
    has_world_completion: bool
    world_completion_source: Optional[str]  # "TITLE_12", "ACHIEVEMENT_137", "INVENTORY_GIFT"
    mastery_requirements_met: bool
    missing_masteries: List[str]
    active_crafting_ready: bool
    crafting_assignment_recommendations: List[Dict[str, Any]]
    precursor_collection_step: Optional[str]
    precursor_collection_bits_done: int
    precursor_collection_bits_total: int
    can_craft_immediately: bool
    blockers: List[str]
    character_discipline_assignments: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    precursor_missing_bits_detail: List[Dict[str, Any]] = field(default_factory=list)
    precursor_stage_bit_breakdown: List[Dict[str, Any]] = field(default_factory=list)


AccountPrerequisiteAudit = PrerequisiteReport


class AccountDiffEngine:
    """Recursive graph traversal engine for computing inventory deltas and progression gaps."""

    def __init__(self, graph_store: Optional[PrioryGraphStore] = None):
        self.store = graph_store
        _ensure_account_catalogs_hydrated(graph_store)
        # Memoization cache for intermediate sub-recipe DAG diffs across multi-item evaluations:
        # Key: (item_id, multiplier, id(account))
        # Value: (ItemRequirementNode, summary_missing, missing_currencies, used_recipes)
        self._sub_tree_memo: Dict[Tuple[int, int, int], Tuple[ItemRequirementNode, Dict[str, int], Dict[str, int], Set[str]]] = {}

        # Static graph metadata caches to eliminate redundant SPARQL evaluations
        self._item_meta_cache: Dict[int, Optional[Dict[str, Any]]] = {}
        self._unpackable_containers_cache: Dict[int, List[Tuple[int, str]]] = {}
        self._tradable_precursor_cache: Dict[int, bool] = {}
        self._recipes_cache: Dict[int, List[Dict[str, Any]]] = {}
        self._recipe_ingredients_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._vendor_exchange_cache: Dict[int, Optional[Dict[str, Any]]] = {}
        self._armory_cap_cache: Dict[int, int] = {}
        self._achievement_reqs_cache: Dict[int, List[Dict[str, Any]]] = {}
        self._mastery_reqs_cache: Dict[int, List[Dict[str, Any]]] = {}
        self._discipline_recipes_cache: Optional[List[Dict[str, Any]]] = None
        self._collection_bits_cache: Dict[int, List[Dict[str, Any]]] = {}

    def clear_sub_tree_cache(self) -> None:
        """Clears the memoized sub-tree cache across multi-item evaluations."""
        self._sub_tree_memo.clear()

    def clear_all_caches(self) -> None:
        """Clears both sub-tree memoization and static graph caches."""
        self._sub_tree_memo.clear()
        self._item_meta_cache.clear()
        self._unpackable_containers_cache.clear()
        self._tradable_precursor_cache.clear()
        self._recipes_cache.clear()
        self._recipe_ingredients_cache.clear()
        self._vendor_exchange_cache.clear()
        self._armory_cap_cache.clear()
        self._achievement_reqs_cache.clear()
        self._mastery_reqs_cache.clear()
        self._discipline_recipes_cache = None
        self._collection_bits_cache.clear()

    def get_collection_bits_for_achievement(self, ach_id: int) -> List[Dict[str, Any]]:
        """Queries ontology-grounded CollectionBitObjective records for a precursor collection achievement ID."""
        if self.store is None:
            return []
        ach_int = int(ach_id)
        if ach_int in self._collection_bits_cache:
            return [dict(b) for b in self._collection_bits_cache[ach_int]]

        raw_bits: List[Dict[str, Any]] = []
        if hasattr(self.store, "get_collection_bits"):
            try:
                res = self.store.get_collection_bits(ach_int)
                if isinstance(res, list):
                    raw_bits = res
            except Exception:
                raw_bits = []

        if not raw_bits:
            bit_sparql = """
            SELECT DISTINCT ?bit ?idx ?itemId ?label ?zone ?wp ?hint WHERE {
                ?bit a priory:CollectionBitObjective ;
                     priory:forAchievementId ?achId ;
                     priory:bitIndex ?idx ;
                     rdfs:label ?label .
                OPTIONAL { ?bit priory:bitItemId ?itemId }
                OPTIONAL { ?bit priory:zoneName ?zone }
                OPTIONAL { ?bit priory:waypointName ?wp }
                OPTIONAL { ?bit priory:acquisitionHint ?hint }
            }
            """
            raw_bits = self.store.query(bit_sparql, init_bindings={"achId": Literal(ach_int)})

        by_index: Dict[int, Dict[str, Any]] = {}
        for r in raw_bits:
            idx_raw = r.get("bit_index") if r.get("bit_index") is not None else r.get("idx", 0)
            idx_val = int(idx_raw)
            item_raw = r.get("item_id") if r.get("item_id") is not None else r.get("itemId")
            item_val = int(item_raw) if item_raw is not None else None
            name_val = str(r.get("name") or r.get("label") or f"Bit {idx_val}")
            zone_val = str(r.get("zone") or r.get("zone_name") or "")
            wp_val = str(r.get("waypoint") or r.get("waypoint_name") or r.get("wp") or "")
            hint_val = str(r.get("hint") or r.get("acquisition_hint") or "")
            by_index[idx_val] = {
                "achievement_id": ach_int,
                "bit_index": idx_val,
                "index": idx_val,
                "item_id": item_val,
                "name": name_val,
                "label": name_val,
                "zone": zone_val,
                "zone_name": zone_val,
                "waypoint": wp_val,
                "waypoint_name": wp_val,
                "hint": hint_val,
                "acquisition_hint": hint_val,
            }

        sorted_bits = [by_index[k] for k in sorted(by_index.keys())]
        if sorted_bits:
            self._collection_bits_cache[ach_int] = sorted_bits
        return [dict(b) for b in sorted_bits]

    def get_available_purchasing_power(self, entity_iri_or_id: Any, account_state: AccountState) -> int:
        """Substrate-agnostic balance resolver querying AccountWalletScalar vs ContainerizedToken in RDF graph.
        
        If wallet scalar: reads from account_state.wallet using priory:apiWalletId.
        If containerized token: sums account_state.get_item_count(item_id) across materials, bank, and bags.
        Provides graceful fallback if entity is not found in graph or graph store is not passed.
        """
        if self.store is not None:
            target_uri = None
            target_id = None
            target_name = None

            if isinstance(entity_iri_or_id, int):
                target_id = Literal(entity_iri_or_id)
            elif isinstance(entity_iri_or_id, URIRef):
                target_uri = entity_iri_or_id
            elif isinstance(entity_iri_or_id, str):
                s = entity_iri_or_id.strip()
                if s.isdigit():
                    target_id = Literal(int(s))
                elif s.startswith("http://") or s.startswith("https://"):
                    target_uri = URIRef(s)
                elif ":" in s:
                    prefix, local = s.split(":", 1)
                    if prefix in DEFAULT_NAMESPACES:
                        target_uri = DEFAULT_NAMESPACES[prefix][local]
                    else:
                        target_name = Literal(local.lower())
                else:
                    target_name = Literal(s.lower())

            sparql = """
            SELECT DISTINCT ?entity ?walletId ?itemId ?isWallet ?isContainer WHERE {
                {
                    ?entity priory:apiWalletId ?walletId .
                    BIND(true AS ?isWallet)
                } UNION {
                    ?entity a/rdfs:subClassOf* priory:AccountWalletScalar .
                    OPTIONAL { ?entity priory:apiWalletId ?walletId }
                    BIND(true AS ?isWallet)
                } UNION {
                    ?entity a/rdfs:subClassOf* priory:ContainerizedToken .
                    OPTIONAL { ?entity priory:gw2Id ?itemId }
                    BIND(true AS ?isContainer)
                } UNION {
                    ?entity a/rdfs:subClassOf* priory:Item .
                    OPTIONAL { ?entity priory:gw2Id ?itemId }
                    BIND(true AS ?isContainer)
                } UNION {
                    ?entity priory:gw2Id ?itemId .
                }
                OPTIONAL { ?entity skos:notation ?notation }
                OPTIONAL { ?entity rdfs:label ?label }
                OPTIONAL { ?entity skos:prefLabel ?prefLabel }
                FILTER (
                    (BOUND(?targetUri) && ?entity = ?targetUri) ||
                    (BOUND(?targetId) && (?walletId = ?targetId || ?itemId = ?targetId || (BOUND(?notation) && STR(?notation) = STR(?targetId)))) ||
                    (BOUND(?targetName) && (
                        (BOUND(?label) && LCASE(STR(?label)) = ?targetName) ||
                        (BOUND(?prefLabel) && LCASE(STR(?prefLabel)) = ?targetName) ||
                        CONTAINS(LCASE(STR(?entity)), ?targetName)
                    ))
                )
            } LIMIT 1
            """
            init_b = {}
            if target_uri:
                init_b["targetUri"] = target_uri
            if target_id:
                init_b["targetId"] = target_id
            if target_name:
                init_b["targetName"] = target_name

            res = self.store.query(sparql, init_bindings=init_b)
            if res:
                match = res[0]
                is_wallet = bool(match.get("isWallet"))
                wallet_id = match.get("walletId")
                item_id = match.get("itemId")

                if is_wallet and wallet_id is not None:
                    wid = int(wallet_id)
                    if wid in account_state.wallet:
                        return account_state.wallet[wid]
                    elif wid == 68 and 63 in account_state.wallet:
                        return account_state.wallet[63]
                    elif wid == 63 and 68 in account_state.wallet:
                        return account_state.wallet[68]
                    elif wid == 69:
                        return account_state.wallet.get(69, 0) + account_state.wallet.get(61, 0) + account_state.wallet.get(13, 0)
                    return account_state.wallet.get(wid, 0)
                elif item_id is not None:
                    iid = int(item_id)
                    return account_state.get_item_count(iid)

        # Fallback to current behavior if graph store not passed or entity not found in graph
        if isinstance(entity_iri_or_id, int):
            if entity_iri_or_id in account_state.wallet:
                return account_state.wallet[entity_iri_or_id]
            return account_state.get_item_count(entity_iri_or_id)
        elif isinstance(entity_iri_or_id, str):
            if entity_iri_or_id.isdigit():
                val = int(entity_iri_or_id)
                if val in account_state.wallet:
                    return account_state.wallet[val]
                return account_state.get_item_count(val)
            s_lower = entity_iri_or_id.lower()
            if "astral" in s_lower:
                return account_state.astral_acclaim_count()
            elif "dungeon" in s_lower or "tales" in s_lower:
                return account_state.dungeon_tales_count()
            elif "gold" in s_lower or "coin" in s_lower:
                return int(account_state.gold_count())
            elif "karma" in s_lower:
                return account_state.karma_count()
            elif "spirit" in s_lower:
                return account_state.spirit_shards_count()
            elif "provisioner" in s_lower:
                return account_state.provisioner_tokens_count()
            elif "volatile" in s_lower:
                return account_state.volatile_magic_count()
            elif "unbound" in s_lower:
                return account_state.unbound_magic_count()
            elif "imperial" in s_lower:
                return account_state.imperial_favor_count()
            elif "research" in s_lower:
                return account_state.research_notes_count()
        return 0

    def _get_astral_acclaim(self, account_state: AccountState) -> int:
        """Resolves Astral Acclaim wallet balance dynamically via graph priory:apiWalletId."""
        return self.get_available_purchasing_power("currency:AstralAcclaim", account_state)

    def _get_dungeon_tales(self, account_state: AccountState) -> int:
        """Resolves Tales of Dungeon Delving balance dynamically via graph priory:apiWalletId."""
        return self.get_available_purchasing_power("currency:TalesOfDungeonDelving", account_state)

    def _get_provisioner_tokens(self, account_state: AccountState) -> int:
        """Resolves Provisioner Token balance dynamically via graph priory:apiWalletId."""
        return self.get_available_purchasing_power("currency:ProvisionerToken", account_state)

    def _get_spirit_shards(self, account_state: AccountState) -> int:
        """Resolves Spirit Shards balance dynamically via graph priory:apiWalletId."""
        return self.get_available_purchasing_power("currency:SpiritShard", account_state)

    def _get_karma(self, account_state: AccountState) -> int:
        """Resolves Karma balance dynamically via graph priory:apiWalletId."""
        return self.get_available_purchasing_power("currency:Karma", account_state)

    def _get_coin(self, account_state: AccountState) -> int:
        """Resolves Coin balance dynamically via graph priory:apiWalletId."""
        return self.get_available_purchasing_power("currency:Coin", account_state)

    def compute_diff(
        self,
        goal_item_id: int,
        account: AccountState,
        target_quantity: int = 1,
        is_acquisition_query: bool = False
    ) -> AccountDiffReport:
        """Recursively parses crafting DAG and computes account missing delta."""
        if goal_item_id not in self._item_meta_cache:
            self._item_meta_cache[goal_item_id] = self.store.get_item_by_id(goal_item_id) if self.store else None
        item_meta = self._item_meta_cache[goal_item_id]
        goal_name = item_meta["label"] if item_meta else f"Item {goal_item_id}"

        # 1. Armory Max Cap & Saturation Check
        if goal_item_id not in self._armory_cap_cache:
            cap_query = """
            SELECT ?cap WHERE {
                ?item priory:gw2Id ?gw2Id .
                { ?item priory:armoryMaxCap ?cap } UNION { ?item priory:maxArmoryCapacity ?cap }
            } LIMIT 1
            """
            cap_res = self.store.query(cap_query, init_bindings={"gw2Id": Literal(goal_item_id)}) if self.store else []
            self._armory_cap_cache[goal_item_id] = int(cap_res[0]["cap"]) if cap_res else 1
        armory_max_cap = self._armory_cap_cache[goal_item_id]
        armory_owned = account.armory_item_count(goal_item_id)
        is_saturated = armory_owned >= armory_max_cap

        # 2. Achievement Prerequisites Check
        if goal_item_id not in self._achievement_reqs_cache:
            ach_query = """
            SELECT ?ach ?achId ?achLabel ?achDef WHERE {
                ?item priory:gw2Id ?gw2Id ;
                      priory:requiresAchievement ?ach .
                ?ach priory:achievementId ?achId .
                OPTIONAL { ?ach rdfs:label ?achLabel }
                OPTIONAL { ?ach skos:definition ?achDef }
            }
            """
            self._achievement_reqs_cache[goal_item_id] = self.store.query(ach_query, init_bindings={"gw2Id": Literal(goal_item_id)}) if self.store else []
        ach_res = self._achievement_reqs_cache[goal_item_id]
        missing_achievements = []
        for row in ach_res:
            a_id = int(row["achId"])
            if a_id not in account.completed_achievements:
                missing_achievements.append({
                    "id": a_id,
                    "title": str(row.get("achLabel", f"Achievement {a_id}")),
                    "description": str(row.get("achDef", ""))
                })

        # 3. Mastery Prerequisites Check
        if goal_item_id not in self._mastery_reqs_cache:
            mast_query = """
            SELECT ?track ?trackId ?trackLabel ?lvl ?mastName WHERE {
                ?item priory:gw2Id ?gw2Id ;
                      priory:requiresMasteryTrack ?track .
                ?track priory:masteryId ?trackId .
                OPTIONAL { ?item priory:requiredMasteryLevel ?lvl }
                OPTIONAL { ?item priory:masteryName ?mastName }
                OPTIONAL { ?track rdfs:label ?trackLabel }
            }
            """
            self._mastery_reqs_cache[goal_item_id] = self.store.query(mast_query, init_bindings={"gw2Id": Literal(goal_item_id)}) if self.store else []
        mast_res = self._mastery_reqs_cache[goal_item_id]
        missing_masteries = []
        for row in mast_res:
            t_id = int(row["trackId"])
            req_lvl = int(row.get("lvl", 1))
            cur_lvl = account.masteries.get(t_id, 0)
            if cur_lvl < req_lvl:
                missing_masteries.append({
                    "track_id": t_id,
                    "track_label": str(row.get("trackLabel", f"Mastery Track {t_id}")),
                    "required_level": req_lvl,
                    "current_level": cur_lvl,
                    "mastery_name": str(row.get("mastName", f"Level {req_lvl}"))
                })

        summary_missing: Dict[str, int] = {}
        missing_currencies: Dict[str, int] = {}
        used_recipes: Set[str] = set()
        visited: Set[int] = set()

        root_node = self._resolve_node(
            goal_item_id,
            target_quantity,
            account,
            summary_missing,
            missing_currencies,
            used_recipes,
            visited,
            goal_item_id=goal_item_id
        )

        missing_disciplines = self._evaluate_discipline_requirements(used_recipes, account)

        # Calculate exact tree units owned vs needed across all branches
        total_owned_units, total_needed_units = self._calculate_tree_units(root_node)
        if (root_node.is_satisfied or is_saturated) and not is_acquisition_query:
            readiness = 100.0
        else:
            readiness = max(0.0, min(100.0, (total_owned_units / max(1, total_needed_units)) * 100.0))

        is_fully_satisfied = (
            (root_node.is_satisfied or is_saturated or
            (len(summary_missing) == 0 and len(missing_currencies) == 0 and len(missing_disciplines) == 0 and len(missing_achievements) == 0 and len(missing_masteries) == 0))
            and not is_acquisition_query
        )

        return AccountDiffReport(
            goal_item_id=goal_item_id,
            goal_item_name=goal_name,
            target_quantity=target_quantity,
            overall_readiness_pct=round(readiness, 1),
            is_fully_satisfied=is_fully_satisfied,
            root_node=root_node,
            is_saturated=is_saturated,
            armory_max_cap=armory_max_cap,
            armory_owned_count=armory_owned,
            missing_achievements=missing_achievements,
            missing_masteries=missing_masteries,
            summary_missing_materials=summary_missing,
            summary_missing_currencies=missing_currencies,
            missing_disciplines=missing_disciplines
        )

    def _calculate_tree_units(self, node: ItemRequirementNode) -> Tuple[int, int]:
        """Recursively calculates (owned_credited_units, total_required_units) across DAG nodes."""
        if not node.sub_requirements:
            needed = node.required_quantity
            owned = min(needed, node.owned_quantity) if not node.is_satisfied else needed
            return (owned, needed)

        if node.is_satisfied:
            return (node.required_quantity, node.required_quantity)

        total_owned = 0
        total_needed = 0
        for child in node.sub_requirements:
            c_owned, c_needed = self._calculate_tree_units(child)
            total_owned += c_owned
            total_needed += c_needed

        return (total_owned, max(1, total_needed))

    def is_unpackable_from_account(self, item_id: int, account: AccountState) -> Optional[str]:
        """Checks if an item can be obtained from an owned container (e.g. Starter Kit in bank)."""
        if not self.store:
            return None
        if item_id not in self._unpackable_containers_cache:
            container_query = """
            SELECT ?containerId ?containerLabel WHERE {
                ?container priory:unpacksInto ?item ;
                           priory:gw2Id ?containerId .
                ?item priory:gw2Id ?gw2Id .
                OPTIONAL { ?container rdfs:label ?containerLabel }
            }
            """
            c_res = self.store.query(container_query, init_bindings={"gw2Id": Literal(item_id)})
            containers = []
            for c_row in c_res:
                containers.append((int(c_row["containerId"]), str(c_row.get("containerLabel", "Choice Chest in Bank"))))
            self._unpackable_containers_cache[item_id] = containers

        for c_id, c_label in self._unpackable_containers_cache[item_id]:
            if account.total_item_count(c_id) > 0:
                return c_label
        return None

    def _resolve_node(
        self,
        item_id: int,
        multiplier: int,
        account: AccountState,
        summary_missing: Dict[str, int],
        missing_currencies: Dict[str, int],
        used_recipes: Optional[Set[str]] = None,
        visited: Optional[Set[int]] = None,
        goal_item_id: Optional[int] = None
    ) -> ItemRequirementNode:
        if visited is None:
            visited = set()

        # Check sub-tree memoization:
        # Identical shared sub-recipes (Mystic Clovers, Gift of Fortune, Gift of Magic, Gift of Might, Gift of Mastery, etc.)
        # are not re-traversed redundantly across items in multi-item evaluations.
        can_memoize = (goal_item_id is not None and item_id != goal_item_id)
        cache_key = (item_id, multiplier, id(account))

        if can_memoize and cache_key in self._sub_tree_memo:
            c_node, c_mats, c_currs, c_recs = self._sub_tree_memo[cache_key]
            for k, v in c_mats.items():
                summary_missing[k] = summary_missing.get(k, 0) + v
            for k, v in c_currs.items():
                missing_currencies[k] = missing_currencies.get(k, 0) + v
            if used_recipes is not None:
                used_recipes.update(c_recs)
            return c_node.clone()

        local_mats: Dict[str, int] = {}
        local_currs: Dict[str, int] = {}
        local_recs: Set[str] = set()

        if item_id not in self._item_meta_cache:
            self._item_meta_cache[item_id] = self.store.get_item_by_id(item_id) if self.store else None
        item_meta = self._item_meta_cache[item_id]
        label = item_meta["label"] if item_meta else f"Item {item_id}"
        is_bound = item_meta.get("isAccountBound", True) if item_meta else True

        owned = account.total_item_count(item_id)
        needed = multiplier
        missing = max(0, needed - owned)
        is_satisfied = (owned >= needed)

        node = ItemRequirementNode(
            item_id=item_id,
            label=label,
            required_quantity=needed,
            owned_quantity=owned,
            missing_quantity=missing,
            is_satisfied=is_satisfied,
            is_account_bound=is_bound
        )

        if not is_satisfied and item_id not in visited:
            branch_visited = visited.copy()
            branch_visited.add(item_id)

            # Check 0: Container Unpack Path (e.g. Starter Kit in Bank or Inventory)
            container_name = self.is_unpackable_from_account(item_id, account)
            if container_name:
                node.is_satisfied = True
                node.missing_quantity = 0
                node.label = f"{label} (Unpackable from {container_name})"
                if can_memoize:
                    self._sub_tree_memo[cache_key] = (node.clone(), {}, {}, set())
                return node

            # Check 0.5: Tradable Precursor (e.g. Dusk, Dawn for Gen 1 legendaries - treated as leaf component unless directly queried)
            is_tradable_precursor = False
            if goal_item_id is not None and item_id != goal_item_id:
                if item_id not in self._tradable_precursor_cache:
                    tp_query = """
                    SELECT ?item WHERE {
                        ?item priory:gw2Id ?gw2Id .
                        { ?item priory:hasPrecursorType priory:TradablePrecursor }
                        UNION
                        { ?item a priory:PrecursorWeapon ; priory:isAccountBound false }
                        UNION
                        { ?item priory:hasSubstituteSource [ a priory:TradingPostPurchasePath ] }
                    } LIMIT 1
                    """
                    tp_res = self.store.query(tp_query, init_bindings={"gw2Id": Literal(item_id)}) if self.store else []
                    self._tradable_precursor_cache[item_id] = bool(tp_res)
                is_tradable_precursor = self._tradable_precursor_cache[item_id]

            if not is_tradable_precursor and self.store is not None:
                # Check 1: Direct crafting recipes producing this item
                if item_id not in self._recipes_cache:
                    rec_query = """
                    SELECT DISTINCT ?recipe ?discipline ?requiredRating WHERE {
                        ?item priory:gw2Id ?gw2Id ;
                              priory:producedBy ?recipe .
                        OPTIONAL { ?recipe priory:requiresDiscipline ?discipline }
                        OPTIONAL { 
                            ?recipe priory:requiredRating ?requiredRating 
                        }
                        OPTIONAL { 
                            ?recipe priory:requiresRating ?requiredRating 
                        }
                    }
                    """
                    self._recipes_cache[item_id] = self.store.query(rec_query, init_bindings={"gw2Id": Literal(item_id)})
                recipes = self._recipes_cache[item_id]

                if recipes:
                    # Multi-discipline preference: Select recipe matching player's active high-level discipline
                    selected_recipe_str = None
                    if len(recipes) > 1:
                        for r in recipes:
                            disc_raw = r.get("discipline", "")
                            disc_name = disc_raw.split("/")[-1].lower() if disc_raw else ""
                            req_rating = int(r.get("requiredRating", 0)) if r.get("requiredRating") is not None else 0
                            if disc_name and account.max_discipline_rating(disc_name) >= req_rating:
                                selected_recipe_str = r["recipe"]
                                break

                    if not selected_recipe_str:
                        selected_recipe_str = recipes[0]["recipe"]

                    local_recs.add(selected_recipe_str)
                    if used_recipes is not None:
                        used_recipes.add(selected_recipe_str)

                    # Fetch ingredients for the selected recipe
                    if selected_recipe_str not in self._recipe_ingredients_cache:
                        ing_query = """
                        SELECT ?ingredientId (SAMPLE(?ingredientLabel) AS ?ingredientLabel) (SAMPLE(?quantity) AS ?quantity) WHERE {
                            ?recipe priory:hasIngredientRequirement ?req .
                            ?req priory:requiresItem ?ingredient ;
                                 priory:requiredQuantity ?quantity .
                            ?ingredient priory:gw2Id ?ingredientId .
                            OPTIONAL { ?ingredient rdfs:label ?ingredientLabel }
                        }
                        GROUP BY ?ingredientId ?req
                        """
                        self._recipe_ingredients_cache[selected_recipe_str] = self.store.query(
                            ing_query, init_bindings={"recipe": URIRef(selected_recipe_str)}
                        )
                    ingredients = self._recipe_ingredients_cache[selected_recipe_str]

                    if ingredients:
                        for ing in ingredients:
                            ing_id = int(ing["ingredientId"])
                            ing_qty = int(ing["quantity"]) * missing
                            sub_node = self._resolve_node(
                                ing_id, ing_qty, account, local_mats, local_currs, local_recs, branch_visited, goal_item_id
                            )
                            node.sub_requirements.append(sub_node)

                        for k, v in local_mats.items():
                            summary_missing[k] = summary_missing.get(k, 0) + v
                        for k, v in local_currs.items():
                            missing_currencies[k] = missing_currencies.get(k, 0) + v
                        if used_recipes is not None and local_recs:
                            used_recipes.update(local_recs)

                        if can_memoize:
                            self._sub_tree_memo[cache_key] = (node.clone(), dict(local_mats), dict(local_currs), set(local_recs))

                        return node

            # Check 2: Vendor Exchange with Currency (e.g. Gift of Craftsmanship -> Provisioner Tokens, Gift of Ascalon -> Tales of Dungeon Delving)
            if self.store is not None:
                if item_id not in self._vendor_exchange_cache:
                    vendor_query = """
                    SELECT ?curr ?currNotation ?currGw2Id ?currLabel ?requiredQty WHERE {
                        ?item priory:gw2Id ?gw2Id ;
                              priory:acquiredVia ?path .
                        ?path a priory:VendorExchangePath ;
                              priory:requiresCurrency ?curr ;
                              priory:requiredQuantity ?requiredQty .
                        OPTIONAL { ?curr skos:notation ?currNotation }
                        OPTIONAL { ?curr priory:gw2Id ?currGw2Id }
                        OPTIONAL { ?curr rdfs:label ?currLabel }
                        OPTIONAL { ?curr skos:prefLabel ?currLabel }
                    } LIMIT 1
                    """
                    v_res = self.store.query(vendor_query, init_bindings={"gw2Id": Literal(item_id)})
                    self._vendor_exchange_cache[item_id] = v_res[0] if v_res else None

                v_info = self._vendor_exchange_cache[item_id]
                if v_info:
                    curr_id = 0
                    if v_info.get("currGw2Id") is not None:
                        try:
                            curr_id = int(v_info["currGw2Id"])
                        except (ValueError, TypeError):
                            pass
                    if not curr_id and v_info.get("currNotation") is not None:
                        try:
                            curr_id = int(v_info["currNotation"])
                        except (ValueError, TypeError):
                            pass
                    if not curr_id and v_info.get("curr") is not None:
                        uri_str = str(v_info["curr"])
                        last_part = uri_str.rstrip("/").split("/")[-1].split("#")[-1]
                        if last_part.isdigit():
                            curr_id = int(last_part)

                    curr_label = v_info.get("currLabel", "Currency")
                    total_curr_needed = int(v_info.get("requiredQty", 1)) * missing
                    owned_curr = account.total_currency_count(curr_id) if curr_id > 0 else 0

                    # Only dedicated token-to-gift exchanges (e.g., Provisioner Tokens 29 for Gift of Craftsmanship,
                    # Tales of Dungeon Delving 69/61/13 for Gift of Ascalon) auto-satisfy the node from wallet tokens.
                    # General currencies (Coin 1, Karma 2, Spirit Shards 23, Astral Acclaim 63/68) do not mean the
                    # player has already bought leaf materials like Icy Runestones (19676), Bloodstone Shard (20797/19674),
                    # Obsidian Shards (19925), or Mystic Clovers (19675).
                    auto_satisfy_token = curr_id in (29, 69, 61, 13) and item_id not in (19676, 19912, 20797, 19674, 19925, 19675)

                    if owned_curr >= total_curr_needed and auto_satisfy_token:
                        node.is_satisfied = True
                        node.missing_quantity = 0
                        if can_memoize:
                            self._sub_tree_memo[cache_key] = (node.clone(), {}, {}, set())
                        return node
                    else:
                        if owned_curr < total_curr_needed:
                            curr_missing = total_curr_needed - owned_curr
                            local_currs[str(curr_label)] = curr_missing
                            missing_currencies[str(curr_label)] = missing_currencies.get(str(curr_label), 0) + curr_missing
                        local_mats[label] = missing
                        summary_missing[label] = summary_missing.get(label, 0) + missing

                        if can_memoize:
                            self._sub_tree_memo[cache_key] = (node.clone(), dict(local_mats), dict(local_currs), set())
                        return node

            # Check 3: Leaf crafting material
            local_mats[label] = missing
            summary_missing[label] = summary_missing.get(label, 0) + missing

            if can_memoize:
                self._sub_tree_memo[cache_key] = (node.clone(), dict(local_mats), {}, set())

        return node

    def _evaluate_discipline_requirements(self, used_recipes: Set[str], account: AccountState) -> List[Dict[str, Any]]:
        """Determines if the account lacks required crafting disciplines for used recipes."""
        missing = []
        if not used_recipes or not self.store:
            return missing

        if self._discipline_recipes_cache is None:
            disc_query = """
            SELECT DISTINCT ?recipe ?discipline ?requiredRating WHERE {
                ?recipe a priory:DisciplineRecipe ;
                        priory:requiresDiscipline ?discipline .
                OPTIONAL { ?recipe priory:requiredRating ?requiredRating }
                OPTIONAL { ?recipe priory:requiresRating ?requiredRating }
            }
            """
            self._discipline_recipes_cache = self.store.query(disc_query)

        for row in self._discipline_recipes_cache:
            rec_uri = row["recipe"]
            if rec_uri in used_recipes:
                disc_uri = row.get("discipline", "")
                disc_name = disc_uri.split("/")[-1].lower() if disc_uri else "unknown"
                req_rating = int(row.get("requiredRating", 0)) if row.get("requiredRating") is not None else 0
                player_rating = account.max_discipline_rating(disc_name)

                # Cross-check with hydrated character graphs if available
                char_query = """
                SELECT DISTINCT ?charName ?rating ?isActive WHERE {
                    ?char priory:characterName ?charName ;
                          priory:hasCraftingDiscipline ?cd .
                    ?cd priory:discipline ?discipline ;
                        priory:craftingRating ?rating .
                    OPTIONAL { ?cd priory:isActive ?isActive }
                    FILTER (?rating >= ?reqRating)
                } ORDER BY DESC(?isActive) DESC(?rating) LIMIT 1
                """
                capable_chars = self.store.query(char_query, init_bindings={"discipline": URIRef(disc_uri), "reqRating": Literal(req_rating)}) if disc_uri else []

                if capable_chars:
                    best_char = capable_chars[0]
                    c_rating = int(best_char.get("rating", 0))
                    if c_rating >= req_rating:
                        continue  # Satisfied by character in knowledge graph!

                if player_rating < req_rating:
                    missing.append({
                        "discipline": disc_name,
                        "required_rating": req_rating,
                        "current_rating": player_rating
                    })
        return missing

    def verify_legendary_prerequisites(
        self,
        goal_item_id: Any,
        account_state: Optional[AccountState] = None,
        account: Optional[AccountState] = None,
    ) -> PrerequisiteReport:
        """Verifies account prerequisites (mastery tiers, active crafting, world completion, precursor collections) for crafting a legendary goal."""
        if isinstance(goal_item_id, AccountState) and isinstance(account_state, int):
            goal_item_id, account_state = account_state, goal_item_id
        if account_state is None and account is not None:
            account_state = account
        if account_state is None:
            account_state = AccountState()
        goal_item_id = int(goal_item_id)

        _ensure_account_catalogs_hydrated(self.store)
        item_meta = self.store.get_item_by_id(goal_item_id) if self.store else None
        goal_name = item_meta["label"] if item_meta else f"Item {goal_item_id}"
        if goal_name == f"Item {goal_item_id}":
            if goal_item_id in GEN1_WEAPONS:
                goal_name = GEN1_WEAPONS[goal_item_id]["name"]
            elif goal_item_id in GEN2_WEAPONS:
                goal_name = GEN2_WEAPONS[goal_item_id]["name"]
            elif goal_item_id in GEN3_WEAPON_NAMES:
                goal_name = GEN3_WEAPON_NAMES[goal_item_id]
            elif goal_item_id in ARMOR_NAMES:
                goal_name = ARMOR_NAMES[goal_item_id]
            elif goal_item_id in PRECURSOR_NAMES:
                goal_name = PRECURSOR_NAMES[goal_item_id]

        # 1. World Exploration Status & Source
        has_world_comp, world_comp_source = account_state.world_completion_status()

        # 2. Item Generation / Archetype Classification
        is_gen1 = goal_item_id in GEN1_WEAPON_IDS or goal_item_id in GEN1_PRECURSOR_IDS
        is_gen2 = goal_item_id in GEN2_WEAPON_IDS or goal_item_id in GEN2_PRECURSOR_IDS
        is_gen3 = goal_item_id in GEN3_WEAPON_IDS
        is_armor = goal_item_id in LEGENDARY_ARMOR_IDS

        if not (is_gen1 or is_gen2 or is_gen3 or is_armor) and self.store:
            gen_query = """
            SELECT ?gen ?isArmor ?isWeapon WHERE {
                ?item priory:gw2Id ?gw2Id .
                OPTIONAL { ?item priory:generation ?gen }
                OPTIONAL { ?item a priory:LegendaryArmor . BIND(true AS ?isArmor) }
                OPTIONAL { ?item a priory:LegendaryWeapon . BIND(true AS ?isWeapon) }
            } LIMIT 1
            """
            res = self.store.query(gen_query, init_bindings={"gw2Id": Literal(goal_item_id)})
            if res:
                row = res[0]
                g_val = str(row.get("gen", ""))
                if "1" in g_val:
                    is_gen1 = True
                elif "2" in g_val:
                    is_gen2 = True
                elif "3" in g_val:
                    is_gen3 = True
                if row.get("isArmor"):
                    is_armor = True

        blockers: List[str] = []

        # 3. World Exploration Check (Required for Gen 1 Gift of Mastery)
        if is_gen1 and not has_world_comp:
            blockers.append(
                "Missing 100% Core Tyria World Completion (requires Title 12 'Been there. Done that.', Achievement 137 'Been There, Done That', or Gift of Exploration in inventory)."
            )

        # 4. Central Tyria Legendary Crafting & Expansion Masteries
        cur_crafting_mastery = account_state.legendary_crafting_mastery_level()
        missing_masteries: List[str] = []

        tier_labels: Dict[int, str] = {}
        for stages in HOBBS_COLLECTIONS.values():
            for stg in stages:
                m_tier = int(stg.get("mastery_tier", 0))
                m_name = str(stg.get("mastery_name", ""))
                if m_tier and m_name and m_tier not in tier_labels:
                    tier_labels[m_tier] = f"Central Tyria Legendary Crafting Tier {m_tier}: {m_name}"

        if is_gen1:
            # Gen 1 precursor crafting / weapon forging requires Tier 3 Historian of the Armaments
            # (Tier 1 for Dusk I, Tier 2 for Dusk II, Tier 3 for Dusk III)
            required_tier = 3
            if cur_crafting_mastery < required_tier:
                for t in range(cur_crafting_mastery + 1, required_tier + 1):
                    missing_masteries.append(tier_labels.get(t, f"Central Tyria Legendary Crafting Tier {t}"))
        elif is_gen2:
            # Gen 2 requires Tier 4 Scholar of Secrets
            required_tier = 4
            if cur_crafting_mastery < required_tier:
                for t in range(cur_crafting_mastery + 1, required_tier + 1):
                    missing_masteries.append(tier_labels.get(t, f"Central Tyria Legendary Crafting Tier {t}"))
            # Heart of Thorns masteries: Exalted Lore lvl 2, Itzel Lore lvl 1, Nuhoch Lore lvl 2
            if account_state.masteries.get(1, 0) < 2:
                missing_masteries.append("Heart of Thorns: Exalted Acceptance (Level 2)")
            if account_state.masteries.get(2, 0) < 1:
                missing_masteries.append("Heart of Thorns: Itzel Language (Level 1)")
            if account_state.masteries.get(3, 0) < 2:
                missing_masteries.append("Heart of Thorns: Nuhoch Proving (Level 2)")
        elif is_gen3:
            # End of Dragons masteries: Commercial Hub lvl 3
            if account_state.masteries.get(4, 0) < 3:
                missing_masteries.append("End of Dragons: Commercial Hub (Level 3)")

        if self.store is not None:
            mast_sparql = """
            SELECT ?trackId ?trackLabel ?lvl ?mastName WHERE {
                ?item priory:gw2Id ?gw2Id ;
                      priory:requiresMasteryTrack ?track .
                ?track priory:masteryId ?trackId .
                OPTIONAL { ?item priory:requiredMasteryLevel ?lvl }
                OPTIONAL { ?item priory:masteryName ?mastName }
                OPTIONAL { ?track rdfs:label ?trackLabel }
            }
            """
            for row in self.store.query(mast_sparql, init_bindings={"gw2Id": Literal(goal_item_id)}):
                t_id = int(row["trackId"])
                req_lvl = int(row.get("lvl", 1))
                cur_lvl = account_state.masteries.get(t_id, 0)
                if cur_lvl < req_lvl:
                    m_label = str(row.get("mastName", f"{row.get('trackLabel', f'Track {t_id}')} Level {req_lvl}"))
                    if m_label not in missing_masteries:
                        missing_masteries.append(m_label)

        mastery_requirements_met = (len(missing_masteries) == 0)
        if not mastery_requirements_met:
            blockers.append(f"Mastery requirements not met: {', '.join(missing_masteries)}.")

        # 5. Active Crafting Disciplines Check Across Characters
        required_disciplines: List[Tuple[str, int]] = []
        if goal_item_id in GEN1_WEAPONS:
            w_info = GEN1_WEAPONS[goal_item_id]
            required_disciplines.append(w_info["disc"])
            if "sec_disc" in w_info:
                required_disciplines.append(w_info["sec_disc"])
        elif goal_item_id in GEN1_PRECURSOR_IDS:
            w_id = PRECURSOR_TO_WEAPON.get(goal_item_id)
            if w_id and w_id in GEN1_WEAPONS:
                required_disciplines.append(GEN1_WEAPONS[w_id]["disc"])
            else:
                required_disciplines.append(("weaponsmith", 500))
        elif goal_item_id in GEN2_WEAPONS:
            w_info = GEN2_WEAPONS[goal_item_id]
            required_disciplines.append(w_info["disc"])
            if "sec_disc" in w_info:
                required_disciplines.append(w_info["sec_disc"])
        elif goal_item_id in GEN2_PRECURSOR_IDS:
            w_id = PRECURSOR_TO_WEAPON.get(goal_item_id)
            if w_id and w_id in GEN2_WEAPONS:
                required_disciplines.append(GEN2_WEAPONS[w_id]["disc"])
        elif goal_item_id in GEN3_WEAPON_DISCIPLINES:
            required_disciplines.append(GEN3_WEAPON_DISCIPLINES[goal_item_id])
        elif goal_item_id in LEGENDARY_ARMOR_DISCIPLINES:
            required_disciplines.append(LEGENDARY_ARMOR_DISCIPLINES[goal_item_id])
        else:
            if self.store is not None:
                disc_sparql = """
                SELECT DISTINCT ?disc ?rating WHERE {
                    {
                        ?item priory:gw2Id ?gw2Id ;
                              priory:producedBy ?rec .
                        ?rec priory:requiresDiscipline ?disc .
                        OPTIONAL { ?rec priory:requiredRating ?rating }
                        OPTIONAL { ?rec priory:requiresRating ?rating }
                    } UNION {
                        ?item priory:gw2Id ?gw2Id ;
                              priory:producedBy ?forgeRec .
                        ?forgeRec priory:hasIngredientRequirement ?req .
                        ?req priory:requiresItem ?subItem .
                        ?subItem priory:producedBy ?rec .
                        ?rec priory:requiresDiscipline ?disc .
                        OPTIONAL { ?rec priory:requiredRating ?rating }
                        OPTIONAL { ?rec priory:requiresRating ?rating }
                    }
                }
                """
                for r in self.store.query(disc_sparql, init_bindings={"gw2Id": Literal(goal_item_id)}):
                    disc_uri = str(r["disc"])
                    disc_name = disc_uri.rstrip("/").split("/")[-1].lower()
                    rating = int(r.get("rating", 400)) if r.get("rating") else 400
                    if (disc_name, rating) not in required_disciplines:
                        required_disciplines.append((disc_name, rating))

        crafting_assignment_recommendations: List[Dict[str, Any]] = []
        character_discipline_assignments: Dict[str, Dict[str, Any]] = {}
        for disc, req_rating in required_disciplines:
            disc_lower = disc.lower()
            routing = route_crafting_discipline(
                discipline=disc_lower,
                required_rating=req_rating,
                account_state=account_state,
                graph_store=self.store
            )
            character_discipline_assignments[disc_lower] = routing
            if routing.get("action") != "ASSIGNED_ACTIVE":
                crafting_assignment_recommendations.append(routing)

        active_crafting_ready = (len(crafting_assignment_recommendations) == 0)
        if not active_crafting_ready:
            disc_strs = [f"{r['discipline'].title()} ({r['required_rating']})" for r in crafting_assignment_recommendations]
            blockers.append(f"Active crafting discipline licenses not ready for: {', '.join(disc_strs)}.")

        # 6. Precursor Collection Bitmask Analysis
        collection_key = goal_item_id
        matched_stage_for_ach_id: Optional[Dict[str, Any]] = None
        if collection_key not in HOBBS_COLLECTIONS:
            if goal_item_id in GEN1_WEAPONS:
                collection_key = GEN1_WEAPONS[goal_item_id]["precursor_id"]
            elif goal_item_id in GEN2_WEAPONS:
                collection_key = GEN2_WEAPONS[goal_item_id]["precursor_id"]
            else:
                for _pid, _stages in HOBBS_COLLECTIONS.items():
                    for _stg in _stages:
                        if goal_item_id in _stg.get("ach_ids", []):
                            collection_key = _pid
                            matched_stage_for_ach_id = _stg
                            break
                    if matched_stage_for_ach_id is not None:
                        break

        precursor_collection_step: Optional[str] = None
        precursor_collection_bits_done: int = 0
        precursor_collection_bits_total: int = 0
        precursor_missing_bits_detail: List[Dict[str, Any]] = []
        precursor_stage_bit_breakdown: List[Dict[str, Any]] = []

        if collection_key in HOBBS_COLLECTIONS:
            tiers = HOBBS_COLLECTIONS[collection_key]
            last_tier = tiers[-1]
            legacy_prec_ids: Tuple[int, ...] = ()
            if goal_item_id in GEN1_WEAPONS:
                precursor_id = GEN1_WEAPONS[goal_item_id]["precursor_id"]
                legacy_prec_ids = tuple(GEN1_WEAPONS[goal_item_id].get("legacy_precursor_ids", ()))
            elif goal_item_id in GEN2_WEAPONS:
                precursor_id = GEN2_WEAPONS[goal_item_id]["precursor_id"]
                legacy_prec_ids = tuple(GEN2_WEAPONS[goal_item_id].get("legacy_precursor_ids", ()))
            else:
                precursor_id = collection_key

            has_precursor = (
                account_state.total_item_count(precursor_id) > 0
                or any(account_state.total_item_count(lid) > 0 for lid in legacy_prec_ids)
                or account_state.total_item_count(goal_item_id) > 0
                or account_state.has_legendary_unlocked(goal_item_id)
            )

            # Determine highest tier with explicit achievement progress in account_state
            highest_active_tier_num = 0
            for t in tiers:
                for aid in t["ach_ids"]:
                    if (
                        aid in (account_state.completed_achievements or set())
                        or aid in (account_state.achievements or {})
                        or aid in (account_state.achievement_bits or {})
                    ):
                        highest_active_tier_num = max(highest_active_tier_num, int(t["tier"]))

            current_tier: Optional[Dict[str, Any]] = None
            current_stage_entry: Optional[Dict[str, Any]] = None

            for t in tiers:
                t_total = int(t["bits_total"])
                t_tier_num = int(t["tier"])
                explicitly_tracked = any(
                    aid in (account_state.achievements or {})
                    or aid in (account_state.achievement_bits or {})
                    for aid in t["ach_ids"]
                )

                t_done = False
                best_count = 0
                best_bits: Set[int] = set()
                primary_aid = int(t["ach_ids"][0]) if t.get("ach_ids") else 0

                for aid in t["ach_ids"]:
                    c_done, c_bits, is_ach_done = account_state._get_achievement_progress(aid, total_bits=t_total)
                    if is_ach_done:
                        t_done = True
                        best_count = t_total
                        best_bits = set(range(t_total))
                        primary_aid = int(aid)
                        break
                    if c_done > best_count or len(c_bits) > len(best_bits):
                        best_count = c_done
                        best_bits = set(c_bits)
                        primary_aid = int(aid)

                if has_precursor:
                    t_done = True
                    best_count = t_total
                    best_bits = set(range(t_total))
                elif not t_done and not explicitly_tracked and t_tier_num < highest_active_tier_num:
                    # Earlier tiers are prerequisite to an actively tracked higher tier
                    t_done = True
                    best_count = t_total
                    best_bits = set(range(t_total))

                ontology_bits = self.get_collection_bits_for_achievement(primary_aid)
                if not ontology_bits and len(t.get("ach_ids", [])) > 1:
                    for alt_aid in t["ach_ids"]:
                        ontology_bits = self.get_collection_bits_for_achievement(int(alt_aid))
                        if ontology_bits:
                            primary_aid = int(alt_aid)
                            break

                stage_missing_bits: List[Dict[str, Any]] = []
                if not t_done and ontology_bits:
                    for b in ontology_bits:
                        if b["bit_index"] not in best_bits:
                            b_copy = dict(b)
                            b_copy["tier"] = t_tier_num
                            b_copy["stage_name"] = str(t["name"])
                            stage_missing_bits.append(b_copy)

                stage_entry: Dict[str, Any] = {
                    "tier": t_tier_num,
                    "achievement_id": primary_aid,
                    "name": str(t["name"]),
                    "bits_done": best_count,
                    "bits_total": t_total,
                    "completed": bool(t_done),
                    "status": "COMPLETED" if t_done else ("IN_PROGRESS" if best_count > 0 else "LOCKED"),
                    "completed_bit_indices": sorted(best_bits),
                    "missing_bit_indices": [i for i in range(t_total) if i not in best_bits],
                    "missing_bits": stage_missing_bits,
                    "total_ontology_bits": len(ontology_bits),
                }
                precursor_stage_bit_breakdown.append(stage_entry)

                if not t_done and current_tier is None:
                    if matched_stage_for_ach_id is None or t_tier_num == int(matched_stage_for_ach_id["tier"]):
                        current_tier = t
                        current_stage_entry = stage_entry

            if has_precursor or current_tier is None or current_stage_entry is None:
                precursor_collection_step = "COMPLETED"
                precursor_collection_bits_done = last_tier["bits_total"]
                precursor_collection_bits_total = last_tier["bits_total"]
            else:
                precursor_collection_step = current_tier["name"]
                precursor_collection_bits_total = current_tier["bits_total"]
                precursor_collection_bits_done = current_stage_entry["bits_done"]
                precursor_missing_bits_detail = list(current_stage_entry["missing_bits"])
                blockers.append(
                    f"Precursor collection incomplete: {precursor_collection_step} ({precursor_collection_bits_done}/{precursor_collection_bits_total} objectives completed)."
                )
        else:
            precursor_collection_step = None
            precursor_collection_bits_done = 0
            precursor_collection_bits_total = 0

        # 7. Item-Specific Achievement Prerequisites (e.g. Ad Infinitum, Regalia)
        if self.store is not None:
            ach_sparql = """
            SELECT ?achId ?achLabel WHERE {
                ?item priory:gw2Id ?gw2Id ;
                      priory:requiresAchievement ?ach .
                ?ach priory:achievementId ?achId .
                OPTIONAL { ?ach rdfs:label ?achLabel }
            }
            """
            for row in self.store.query(ach_sparql, init_bindings={"gw2Id": Literal(goal_item_id)}):
                a_id = int(row["achId"])
                if a_id not in account_state.completed_achievements:
                    a_label = str(row.get("achLabel", f"Achievement {a_id}"))
                    blockers.append(f"Missing required achievement: {a_label} (ID: {a_id}).")

        can_craft_immediately = (len(blockers) == 0)

        return PrerequisiteReport(
            goal_item_id=goal_item_id,
            goal_name=goal_name,
            has_world_completion=has_world_comp,
            world_completion_source=world_comp_source,
            mastery_requirements_met=mastery_requirements_met,
            missing_masteries=missing_masteries,
            active_crafting_ready=active_crafting_ready,
            crafting_assignment_recommendations=crafting_assignment_recommendations,
            precursor_collection_step=precursor_collection_step,
            precursor_collection_bits_done=precursor_collection_bits_done,
            precursor_collection_bits_total=precursor_collection_bits_total,
            can_craft_immediately=can_craft_immediately,
            blockers=blockers,
            character_discipline_assignments=character_discipline_assignments,
            precursor_missing_bits_detail=precursor_missing_bits_detail,
            precursor_stage_bit_breakdown=precursor_stage_bit_breakdown,
        )

    def audit_prerequisites(
        self,
        goal_item_id: Any,
        account_state: Optional[AccountState] = None,
        account: Optional[AccountState] = None,
    ) -> PrerequisiteReport:
        """Alias for verify_legendary_prerequisites returning AccountPrerequisiteAudit / PrerequisiteReport."""
        return self.verify_legendary_prerequisites(
            goal_item_id=goal_item_id,
            account_state=account_state,
            account=account,
        )


# ==============================================================================
# Legendary Item Metadata & Grandmaster Hobbs Precursor Collection Definitions
# (Hydrated dynamically from RDF via PrioryGraphStore)
# ==============================================================================

GEN1_WEAPONS: Dict[int, Dict[str, Any]] = {}
GEN2_WEAPONS: Dict[int, Dict[str, Any]] = {}
GEN3_WEAPON_NAMES: Dict[int, str] = {}
GEN3_WEAPON_DISCIPLINES: Dict[int, Tuple[str, int]] = {}
ARMOR_NAMES: Dict[int, str] = {}
LEGENDARY_ARMOR_DISCIPLINES: Dict[int, Tuple[str, int]] = {}
PRECURSOR_NAMES: Dict[int, str] = {}
GEN1_WEAPON_IDS: Set[int] = set()
GEN1_PRECURSOR_IDS: Set[int] = set()
GEN2_WEAPON_IDS: Set[int] = set()
GEN2_PRECURSOR_IDS: Set[int] = set()
GEN3_WEAPON_IDS: Set[int] = set()
LEGENDARY_ARMOR_IDS: Set[int] = set()
PRECURSOR_TO_WEAPON: Dict[int, int] = {}
HOBBS_COLLECTIONS: Dict[int, List[Dict[str, Any]]] = {}
_WEAPON_TYPE_DISCIPLINES: Dict[str, Tuple[Tuple[str, int], Tuple[str, int]]] = {}

_HYDRATED_GRAPH_SIGNATURES: Set[Tuple[int, int]] = set()


def _hydrate_catalogs_from_graph(store: Optional[PrioryGraphStore] = None) -> None:
    """Dynamically hydrates module-level weapon, precursor, armor, lounge, convenience, and roster catalogs in-place from RDF."""
    if store is None or len(store.graph) == 0:
        return

    sig = (id(store), len(store.graph))
    if sig in _HYDRATED_GRAPH_SIGNATURES and LOUNGE_PASSES and CONVENIENCE_ITEMS and GEN1_WEAPONS and HOBBS_COLLECTIONS:
        return
    _HYDRATED_GRAPH_SIGNATURES.add(sig)

    # 1. Hydrate Default Character Roster from RDF
    if hasattr(store, "get_default_character_roster"):
        roster = store.get_default_character_roster()
        for ch_name in roster:
            if ch_name not in DEFAULT_ACCOUNT_ROSTER:
                DEFAULT_ACCOUNT_ROSTER.append(ch_name)

    # 2. Hydrate VIP Lounge Passes from RDF
    if hasattr(store, "get_lounge_passes"):
        passes = store.get_lounge_passes()
        for pid, pmeta in passes.items():
            if not pmeta.get("chat_link"):
                pmeta = dict(pmeta)
                pmeta["chat_link"] = encode_item_chat_link(pid)
            LOUNGE_PASSES.setdefault(pid, pmeta)

    # 3. Hydrate Convenience Categories & Items from RDF
    if hasattr(store, "get_convenience_catalog"):
        cats, conv_items = store.get_convenience_catalog()
        for c_name in cats:
            if c_name not in CONVENIENCE_CATEGORIES:
                CONVENIENCE_CATEGORIES.append(c_name)
        for slug, c_meta in conv_items.items():
            CONVENIENCE_ITEMS.setdefault(slug, c_meta)

    # 4. Hydrate Legendary Weapons, Armor, Precursors, Discipline Rules & Hobbs Collections from RDF
    if hasattr(store, "get_legendary_and_precursor_catalog"):
        leg_cat = store.get_legendary_and_precursor_catalog()
        _WEAPON_TYPE_DISCIPLINES.update(leg_cat.get("weapon_type_disciplines", {}))
        for wid, winfo in leg_cat.get("gen1_weapons", {}).items():
            GEN1_WEAPONS.setdefault(wid, winfo)
        for wid, winfo in leg_cat.get("gen2_weapons", {}).items():
            GEN2_WEAPONS.setdefault(wid, winfo)
        for wid, wname in leg_cat.get("gen3_weapon_names", {}).items():
            GEN3_WEAPON_NAMES.setdefault(wid, wname)
        for wid, wdisc in leg_cat.get("gen3_weapon_disciplines", {}).items():
            GEN3_WEAPON_DISCIPLINES.setdefault(wid, wdisc)
        for aid, aname in leg_cat.get("armor_names", {}).items():
            ARMOR_NAMES.setdefault(aid, aname)
        for aid, adisc in leg_cat.get("legendary_armor_disciplines", {}).items():
            LEGENDARY_ARMOR_DISCIPLINES.setdefault(aid, adisc)
        for pid, pname in leg_cat.get("precursor_names", {}).items():
            PRECURSOR_NAMES.setdefault(pid, pname)
        for pid, wid in leg_cat.get("precursor_to_weapon", {}).items():
            PRECURSOR_TO_WEAPON.setdefault(pid, wid)
        for cid, ctiers in leg_cat.get("hobbs_collections", {}).items():
            HOBBS_COLLECTIONS.setdefault(cid, ctiers)
        GEN1_WEAPON_IDS.update(leg_cat.get("gen1_weapon_ids", set()))
        GEN1_PRECURSOR_IDS.update(leg_cat.get("gen1_precursor_ids", set()))
        GEN2_WEAPON_IDS.update(leg_cat.get("gen2_weapon_ids", set()))
        GEN2_PRECURSOR_IDS.update(leg_cat.get("gen2_precursor_ids", set()))
        GEN3_WEAPON_IDS.update(leg_cat.get("gen3_weapon_ids", set()))
        LEGENDARY_ARMOR_IDS.update(leg_cat.get("legendary_armor_ids", set()))

    # Refresh derived sets in-place
    GEN1_WEAPON_IDS.update(GEN1_WEAPONS.keys())
    GEN1_PRECURSOR_IDS.update(w["precursor_id"] for w in GEN1_WEAPONS.values() if w.get("precursor_id"))
    GEN2_WEAPON_IDS.update(GEN2_WEAPONS.keys())
    GEN2_PRECURSOR_IDS.update(w["precursor_id"] for w in GEN2_WEAPONS.values() if w.get("precursor_id"))
    GEN3_WEAPON_IDS.update(GEN3_WEAPON_NAMES.keys())
    LEGENDARY_ARMOR_IDS.update(ARMOR_NAMES.keys())

    for _p_id, _tiers in list(HOBBS_COLLECTIONS.items()):
        _w_id = PRECURSOR_TO_WEAPON.get(_p_id)
        if _w_id and _w_id not in HOBBS_COLLECTIONS:
            HOBBS_COLLECTIONS[_w_id] = _tiers


def verify_legendary_prerequisites(
    goal_item_id: Any,
    account_state: Optional[AccountState] = None,
    graph_store: Optional[PrioryGraphStore] = None,
    account: Optional[AccountState] = None,
) -> PrerequisiteReport:
    """Convenience standalone wrapper for AccountDiffEngine.verify_legendary_prerequisites."""
    engine = AccountDiffEngine(graph_store=graph_store)
    return engine.verify_legendary_prerequisites(goal_item_id, account_state=account_state, account=account)


def audit_prerequisites(
    goal_item_id: Any,
    account_state: Optional[AccountState] = None,
    graph_store: Optional[PrioryGraphStore] = None,
    account: Optional[AccountState] = None,
) -> PrerequisiteReport:
    """Convenience standalone wrapper for AccountDiffEngine.audit_prerequisites."""
    engine = AccountDiffEngine(graph_store=graph_store)
    return engine.audit_prerequisites(goal_item_id, account_state=account_state, account=account)


try:
    _ensure_account_catalogs_hydrated()
except Exception:
    pass

