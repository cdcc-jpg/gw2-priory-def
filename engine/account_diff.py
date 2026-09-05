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


LOUNGE_PASSES: Dict[int, Dict[str, Any]] = {
    81664: {"name": "Mistlock Sanctuary Passkey", "chat_link": "[&AgEAPwEA]", "zone": "Mistlock Sanctuary"},
    81665: {"name": "Mistlock Sanctuary Passkey (2 Weeks)", "chat_link": "[&AgEBPwEA]", "zone": "Mistlock Sanctuary"},
    90011: {"name": "Armistice Bastion Pass", "chat_link": "[&AgHrXwEA]", "zone": "Armistice Bastion"},
    90012: {"name": "Armistice Bastion Pass (2 Weeks)", "chat_link": "[&AgHsXwEA]", "zone": "Armistice Bastion"},
    98048: {"name": "Thousand Seas Pavilion Pass", "chat_link": "[&AgGgcAEA]", "zone": "Thousand Seas Pavilion"},
    98049: {"name": "Thousand Seas Pavilion Pass (2 Weeks)", "chat_link": "[&AgGhcAEA]", "zone": "Thousand Seas Pavilion"},
    49149: {"name": "Royal Terrace Pass", "chat_link": "[&AgEVwAAA]", "zone": "Divinity's Reach"},
    49148: {"name": "Royal Terrace Pass (2 Weeks)", "chat_link": "[&AgEUwAAA]", "zone": "Divinity's Reach"},
    97009: {"name": "Arborstone Portal Scroll", "chat_link": "[&AgHxegEA]", "zone": "Arborstone"},
    83457: {"name": "Passkey to the Lily of the Elon", "chat_link": "[&AgEBRgEA]", "zone": "Crystal Oasis"},
    87498: {"name": "Invitation to 'Lily of the Elon'", "chat_link": "[&AgH6VwEA]", "zone": "Crystal Oasis"},
    87499: {"name": "Invitation to 'Lily of the Elon' (2 Weeks)", "chat_link": "[&AgH7VwEA]", "zone": "Crystal Oasis"},
    79500: {"name": "Lava Lounge Pass", "chat_link": "[&AgGMNgEA]", "zone": "Ember Bay"},
    79501: {"name": "Lava Lounge Pass (2 Weeks)", "chat_link": "[&AgEtNwEA]", "zone": "Ember Bay"},
    82791: {"name": "Champion's Rest Pass", "chat_link": "[&AgFnQwEA]", "zone": "Heart of the Mists"},
    88385: {"name": "Champion's Rest Pass", "chat_link": "[&AgGBWQEA]", "zone": "Heart of the Mists"},
    88386: {"name": "Champion's Rest Pass (2 Weeks)", "chat_link": "[&AgGCWQEA]", "zone": "Heart of the Mists"},
    86634: {"name": "Captain's Airship Pass", "chat_link": "[&AgGqUgEA]", "zone": "Gendarran Fields"},
    86635: {"name": "Captain's Airship Pass (2 Weeks)", "chat_link": "[&AgGrUgEA]", "zone": "Gendarran Fields"},
    92055: {"name": "Eye of the North Portal Stone", "chat_link": "[&AgFnZwEA]", "zone": "Eye of the North"},
    95430: {"name": "Wizard's Tower Portal Scroll", "chat_link": "[&AgFmfwEA]", "zone": "Wizard's Tower"},
    100788: {"name": "Wizard's Tower Teleportation Scroll", "chat_link": "[&AgG0iQEA]", "zone": "Wizard's Tower"}
}


CONVENIENCE_CATEGORIES: List[str] = [
    "permanent_contracts",
    "converters_and_gobblers",
    "portal_tomes",
    "infinite_tools",
    "infinite_salvage",
    "portable_forge",
    "teleport_to_friend",
    "vip_lounges"
]


CONVENIENCE_ITEMS: Dict[str, Dict[str, Any]] = {
    # 1. Permanent Contracts
    "permanent_bank": {
        "id": 35976,
        "all_ids": [35976, 35978, 35984, 49308],
        "name": "Permanent Bank Access Express",
        "chat_link": "[&AgGQjAAA]",
        "type": "PermanentContract",
        "category": "permanent_contracts"
    },
    "permanent_tp": {
        "id": 35978,
        "all_ids": [35978, 35976, 35986, 35987],
        "name": "Permanent Trading Post Express",
        "chat_link": "[&AgGZjAAA]",
        "type": "PermanentContract",
        "category": "permanent_contracts"
    },
    "permanent_merchant": {
        "id": 35977,
        "all_ids": [35977, 35985],
        "name": "Permanent Merchant Express",
        "chat_link": "[&AgGJjAAA]",
        "type": "PermanentContract",
        "category": "permanent_contracts"
    },
    "permanent_hair_stylist": {
        "id": 35984,
        "all_ids": [35984, 35988, 36173],
        "name": "Permanent Hair Stylist Contract",
        "chat_link": "[&AgG4XAAA]",
        "type": "PermanentContract",
        "category": "permanent_contracts"
    },

    # 2. Converters & Gobblers
    "candy_corn_gobbler": {
        "id": 67393,
        "all_ids": [67393, 67037, 67040],
        "name": "Candy Corn Gobbler",
        "chat_link": "[&AgEZCgEA]",
        "type": "Gobbler",
        "category": "converters_and_gobblers"
    },
    "zhaitaffy_gobbler": {
        "id": 67836,
        "all_ids": [67836],
        "name": "Zhaitaffy Gobbler",
        "chat_link": "[&AgFs/QAA]",
        "type": "Gobbler",
        "category": "converters_and_gobblers"
    },
    "snowflake_gobbler": {
        "id": 92585,
        "all_ids": [92585, 79523, 86675],
        "name": "Snowflake Gobbler",
        "chat_link": "[&AgHpZQEA]",
        "type": "Gobbler",
        "category": "converters_and_gobblers"
    },
    "ley_energy_converter": {
        "id": 67280,
        "all_ids": [67280, 69949],
        "name": "Ley-Energy Matter Converter",
        "chat_link": "[&AgGgCgEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },
    "karmic_converter": {
        "id": 66624,
        "all_ids": [66624, 67038],
        "name": "Karmic Converter",
        "chat_link": "[&AgEAfAEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },
    "gleam_of_sentience": {
        "id": 92209,
        "all_ids": [92209, 81790],
        "name": "Gleam of Sentience",
        "chat_link": "[&AgERUQEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },
    "sentient_aberration": {
        "id": 79895,
        "all_ids": [79895],
        "name": "Sentient Aberration",
        "chat_link": "[&AgFnNQEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },
    "sentient_anomaly": {
        "id": 82418,
        "all_ids": [82418],
        "name": "Sentient Anomaly",
        "chat_link": "[&AgGyPQEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },
    "sentient_oddity": {
        "id": 80894,
        "all_ids": [80894],
        "name": "Sentient Oddity",
        "chat_link": "[&AgH+OQEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },
    "sentient_seed": {
        "id": 81700,
        "all_ids": [81700],
        "name": "Sentient Seed",
        "chat_link": "[&AgEkPgEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },
    "princess": {
        "id": 69887,
        "all_ids": [69887],
        "name": "Princess",
        "chat_link": "[&AgF/EQEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },
    "star_of_gratitude": {
        "id": 68369,
        "all_ids": [68369],
        "name": "Star of Gratitude",
        "chat_link": "[&AgExCwEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },
    "herta": {
        "id": 73248,
        "all_ids": [73248],
        "name": "Herta",
        "chat_link": "[&AgGgHAEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },
    "mawdrey_2": {
        "id": 66341,
        "all_ids": [66341],
        "name": "Mawdrey II",
        "chat_link": "[&AgE1BAEA]",
        "type": "Converter",
        "category": "converters_and_gobblers"
    },

    # 3. Portal Tomes & Teleporters
    "lws3_portal_tome": {
        "id": 80332,
        "all_ids": [80332, 79899, 82449, 82512],
        "name": "Living World Season 3 Portal Tome",
        "chat_link": "[&AgFsOQEA]",
        "type": "PortalTome",
        "category": "portal_tomes"
    },
    "lws4_portal_tome": {
        "id": 87508,
        "all_ids": [87508, 86586, 87509],
        "name": "Living World Season 4 Portal Tome",
        "chat_link": "[&AgF4VQEA]",
        "type": "PortalTome",
        "category": "portal_tomes"
    },
    "ibs_portal_tome": {
        "id": 92850,
        "all_ids": [92850, 92272, 92782, 92783],
        "name": "Icebrood Saga Portal Tome",
        "chat_link": "[&AgGyZwEA]",
        "type": "PortalTome",
        "category": "portal_tomes"
    },
    "arborstone_portal_scroll": {
        "id": 97009,
        "all_ids": [97009],
        "name": "Arborstone Portal Scroll",
        "chat_link": "[&AgHxegEA]",
        "type": "PortalTome",
        "category": "portal_tomes"
    },
    "wizards_tower_portal_scroll": {
        "id": 100788,
        "all_ids": [100788, 95430],
        "name": "Wizard's Tower Teleportation Scroll",
        "chat_link": "[&AgG0iQEA]",
        "type": "PortalTome",
        "category": "portal_tomes"
    },
    "spearmarshals_plea": {
        "id": 84310,
        "all_ids": [84310],
        "name": "Spearmarshal's Plea",
        "chat_link": "[&AgFpTwEA]",
        "type": "PortalDevice",
        "category": "portal_tomes"
    },
    "world_boss_portal_device": {
        "id": 87504,
        "all_ids": [87504],
        "name": "World Boss Portal Device",
        "chat_link": "[&AgHwVwEA]",
        "type": "PortalDevice",
        "category": "portal_tomes"
    },
    "maguuma_portal_device": {
        "id": 90022,
        "all_ids": [90022],
        "name": "Maguuma Pact Operation Portal Device",
        "chat_link": "[&AgFwXwEA]",
        "type": "PortalDevice",
        "category": "portal_tomes"
    },
    "eye_of_the_north_portal_stone": {
        "id": 92055,
        "all_ids": [92055],
        "name": "Eye of the North Portal Stone",
        "chat_link": "[&AgFnZwEA]",
        "type": "PortalTome",
        "category": "portal_tomes"
    },

    # 4. Infinite Gathering Tools
    "lucky_dog_harvesting_tool": {
        "id": 86694,
        "all_ids": [86694],
        "name": "Lucky Dog Harvesting Tool",
        "chat_link": "[&AgGyUgEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "volatile_magic_harvesting_tool": {
        "id": 87435,
        "all_ids": [87435],
        "name": "Volatile Magic Harvesting Tool",
        "chat_link": "[&AgFuVwEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "volatile_magic_mining_pick": {
        "id": 87434,
        "all_ids": [87434],
        "name": "Volatile Magic Mining Pick",
        "chat_link": "[&AgFrVwEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "volatile_magic_logging_axe": {
        "id": 87433,
        "all_ids": [87433],
        "name": "Volatile Magic Logging Axe",
        "chat_link": "[&AgFqVwEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "unbound_magic_harvesting_tool": {
        "id": 80234,
        "all_ids": [80234],
        "name": "Unbound Magic Harvesting Tool",
        "chat_link": "[&AgGqOQEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "unbound_magic_mining_pick": {
        "id": 80235,
        "all_ids": [80235],
        "name": "Unbound Magic Mining Pick",
        "chat_link": "[&AgGrOQEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "unbound_magic_logging_axe": {
        "id": 80236,
        "all_ids": [80236],
        "name": "Unbound Magic Logging Axe",
        "chat_link": "[&AgGsOQEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "skyscale_harvesting_tool": {
        "id": 92842,
        "all_ids": [92842],
        "name": "Skyscale Harvesting Tool",
        "chat_link": "[&AgG6ZQEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "skyscale_mining_pick": {
        "id": 92841,
        "all_ids": [92841],
        "name": "Skyscale Mining Pick",
        "chat_link": "[&AgG5ZQEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "skyscale_logging_axe": {
        "id": 92840,
        "all_ids": [92840],
        "name": "Skyscale Logging Axe",
        "chat_link": "[&AgG4ZQEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "cosmic_harvesting_tool": {
        "id": 87405,
        "all_ids": [87405],
        "name": "Infinite Cosmic Harvesting Tool",
        "chat_link": "[&AgFlVQEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "cosmic_mining_pick": {
        "id": 87372,
        "all_ids": [87372],
        "name": "Infinite Cosmic Mining Pick",
        "chat_link": "[&AgFkVQEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "cosmic_logging_axe": {
        "id": 87371,
        "all_ids": [87371],
        "name": "Infinite Cosmic Logging Axe",
        "chat_link": "[&AgFjVQEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "choya_mining_pick": {
        "id": 86938,
        "all_ids": [86938],
        "name": "Choya Mining Pick",
        "chat_link": "[&AgHKUwEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "choya_harvesting_sickle": {
        "id": 86939,
        "all_ids": [86939],
        "name": "Choya Harvesting Sickle",
        "chat_link": "[&AgHLUwEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "choya_logging_axe": {
        "id": 86940,
        "all_ids": [86940],
        "name": "Choya Logging Axe",
        "chat_link": "[&AgHMUwEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "consortium_sickle": {
        "id": 48932,
        "all_ids": [48932],
        "name": "Consortium Harvesting Sickle",
        "chat_link": "[&AgF0vwAA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "molten_pick": {
        "id": 48931,
        "all_ids": [48931],
        "name": "Molten Alliance Mining Pick",
        "chat_link": "[&AgFzvwAA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "chop_it_all_axe": {
        "id": 48933,
        "all_ids": [48933],
        "name": "Chop-It-All Logging Axe",
        "chat_link": "[&AgF1vwAA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "watchwork_pick": {
        "id": 47897,
        "all_ids": [47897],
        "name": "Watchwork Mining Pick",
        "chat_link": "[&AgFpnQAA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "tireless_harvesting_minion": {
        "id": 49298,
        "all_ids": [49298],
        "name": "Tireless Harvesting Minion",
        "chat_link": "[&AgEqwAAA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "tireless_logging_minion": {
        "id": 49297,
        "all_ids": [49297],
        "name": "Tireless Logging Minion",
        "chat_link": "[&AgEpwAAA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "bone_pick": {
        "id": 49296,
        "all_ids": [49296],
        "name": "Bone Pick",
        "chat_link": "[&AgEowAAA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "fused_molten_sickle": {
        "id": 49299,
        "all_ids": [49299],
        "name": "Fused Molten Sickle",
        "chat_link": "[&AgErwAAA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "fused_molten_logging_axe": {
        "id": 49300,
        "all_ids": [49300],
        "name": "Fused Molten Logging Axe",
        "chat_link": "[&AgEswAAA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "glitter_bomb_harvesting_tool": {
        "id": 78949,
        "all_ids": [78949],
        "name": "Glitter Bomb Harvesting Tool",
        "chat_link": "[&AgGVNAEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "solar_insect_tool": {
        "id": 84698,
        "all_ids": [84698],
        "name": "Solar Insect Gathering Tool",
        "chat_link": "[&AgGqTgEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "mad_scientist_mining": {
        "id": 67032,
        "all_ids": [67032],
        "name": "Mad Scientist Mining Tool",
        "chat_link": "[&AgHYBgEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "mad_scientist_harvesting": {
        "id": 67034,
        "all_ids": [67034],
        "name": "Mad Scientist Harvesting Tool",
        "chat_link": "[&AgHaBgEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "mad_scientist_logging": {
        "id": 67033,
        "all_ids": [67033],
        "name": "Mad Scientist Logging Tool",
        "chat_link": "[&AgHZBgEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "firefly_mining_flute": {
        "id": 81472,
        "all_ids": [81472],
        "name": "Firefly Mining Flute",
        "chat_link": "[&AgHAOgEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "butterfly_harvesting_flute": {
        "id": 81473,
        "all_ids": [81473],
        "name": "Butterfly Harvesting Flute",
        "chat_link": "[&AgHBOgEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },
    "swarm_logging_flute": {
        "id": 81471,
        "all_ids": [81471],
        "name": "Swarm Logging Flute",
        "chat_link": "[&AgG/OgEA]",
        "type": "GatheringTool",
        "category": "infinite_tools"
    },

    # 4. Infinite Salvage
    "copper_fed": {
        "id": 44602,
        "all_ids": [44602],
        "name": "Copper-Fed Salvage-o-Matic",
        "chat_link": "[&AgE6rgAA]",
        "type": "SalvageKit",
        "category": "infinite_salvage"
    },
    "silver_fed": {
        "id": 67027,
        "all_ids": [67027],
        "name": "Silver-Fed Salvage-o-Matic",
        "chat_link": "[&AgHTBQEA]",
        "type": "SalvageKit",
        "category": "infinite_salvage"
    },
    "runecrafter": {
        "id": 87400,
        "all_ids": [87400],
        "name": "Runecrafter's Salvage-o-Matic",
        "chat_link": "[&AgFoVQEA]",
        "type": "SalvageKit",
        "category": "infinite_salvage"
    },
    "upgrade_extractor": {
        "id": 93121,
        "all_ids": [93121, 93120, 93122],
        "name": "Endless Upgrade Extractor",
        "chat_link": "[&AgHpWgEA]",
        "type": "SalvageKit",
        "category": "infinite_salvage"
    },

    # 5. Portable Forge
    "mystic_forge_conduit": {
        "id": 70010,
        "all_ids": [70010, 35727, 36014, 36013, 36012, 36011],
        "name": "Mystic Forge Conduit",
        "chat_link": "[&AgE6EQEA]",
        "type": "MysticForge",
        "category": "portable_forge"
    },

    # 6. Teleport to Friend
    "teleport_to_friend": {
        "id": 90335,
        "all_ids": [90335],
        "name": "Recharging Teleport to Friend",
        "chat_link": "[&AgHfYAEA]",
        "type": "Teleport",
        "category": "teleport_to_friend"
    }
}


DEFAULT_ACCOUNT_ROSTER: List[str] = [
    'Kerling', 'Skuta Rantakallio', 'Legacy Of Harathi', 'Styrman',
    'Ksëne', 'Aubefein', 'Sara Loy', 'Flevkk', 'Like A Plastik Bag',
    'Jaimelargent', 'Saladomatic'
]


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
    map_completed_characters: List[str] = field(default_factory=lambda: ['Kerling'])
    titles: Set[int] = field(default_factory=set)
    fractal_level: int = 1
    wvw_rank: int = 1
    daily_ap: int = 0
    monthly_ap: int = 0
    luck: int = 0
    commander: bool = False
    account_created: str = ""
    progression: Dict[str, int] = field(default_factory=dict)
    daily_dungeons: List[str] = field(default_factory=list)
    weekly_raids: List[str] = field(default_factory=list)
    achievement_bits: Dict[int, List[int]] = field(default_factory=dict)
    achievement_repeated: Dict[int, int] = field(default_factory=dict)
    active_disciplines: Dict[str, List[str]] = field(default_factory=dict)
    character_disciplines: Dict[str, Dict[str, Dict[str, Any]]] = field(default_factory=dict)
    daily_crafting: List[str] = field(default_factory=list)
    world_bosses: List[str] = field(default_factory=list)

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
            self.legendary_armory.get(item_id, 0)
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

    def world_completion_status(self) -> Tuple[bool, Optional[str]]:
        """Determines world exploration status and source ("INVENTORY_GIFT", "TITLE_12", "ACHIEVEMENT_137")."""
        if self.total_item_count(19677) > 0:
            return True, "INVENTORY_GIFT"
        if 12 in self.titles:
            return True, "TITLE_12"
        if 137 in self.completed_achievements or self.achievements.get(137, 0) >= 100:
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

    def has_active_discipline(self, discipline: str, min_rating: int = 0) -> bool:
        """Returns True if any character has the specified discipline currently active with at least min_rating."""
        disc = discipline.lower()
        if disc in self.active_disciplines:
            for char_name in self.active_disciplines[disc]:
                info = self.character_disciplines.get(char_name, {}).get(disc, {})
                if info.get("rating", 0) >= min_rating:
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
        """Returns True if the account owns Bloodstone Shard (item 19674)."""
        return self.total_item_count(19674) > 0

    def has_gift_of_battle(self) -> bool:
        """Returns True if the account owns Gift of Battle (item 19678)."""
        return self.total_item_count(19678) > 0

    def has_legendary_unlocked(self, item_id: int) -> bool:
        """Returns True if the item is unlocked in the Legendary Armory."""
        return self.legendary_armory.get(item_id, 0) > 0

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
        return character_name in self.map_completed_characters

    def eligible_exploration_characters(self) -> List[str]:
        """Returns roster characters who have not completed 100% Core Map."""
        roster_names: List[str] = []
        if self.characters:
            for c in self.characters:
                if isinstance(c, dict) and c.get("name"):
                    roster_names.append(c["name"])
                elif isinstance(c, str):
                    roster_names.append(c)
        if not roster_names:
            roster_names = list(DEFAULT_ACCOUNT_ROSTER)

        eligible = [name for name in roster_names if not self.is_character_map_completed(name)]
        if not eligible:
            eligible = [name for name in DEFAULT_ACCOUNT_ROSTER if not self.is_character_map_completed(name)]
        return eligible

    def owned_boosters(self) -> Dict[int, int]:
        """Detects owned boosters, gobblers, and tomes across materials, bank, and inventory."""
        booster_ids = [
            67836, 67037, 67040, 79523, 86675, 19983, 43766,
            19997, 20002, 41819, 8417, 78954, 20005, 41818, 67500, 67501,
            20001, 8419, 41821, 92843, 43499, 45056, 45060, 43485,
            45003, 45037, 45038, 77749, 20003, 41820, 78955, 2059, 42970, 49424, 45005
        ]
        result = {}
        for b_id in booster_ids:
            count = self.total_item_count(b_id)
            if count > 0:
                result[b_id] = count
        return result

    def owned_lounges(self) -> List[Dict[str, Any]]:
        """Scans bank and inventory for owned VIP lounge passes and portal scrolls."""
        results = []
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
        categories: Dict[str, List[Dict[str, Any]]] = {
            "permanent_contracts": [],
            "converters_and_gobblers": [],
            "portal_tomes": [],
            "infinite_tools": [],
            "infinite_salvage": [],
            "portable_forge": [],
            "teleport_to_friend": [],
            "vip_lounges": []
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
            categories["vip_lounges"].append({
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

    def has_permanent_bank(self) -> bool:
        """Returns True if the account owns Permanent Bank Access Contract/Express (IDs 35976, 35978, 35984, 49308)."""
        return any(self.total_item_count(i) > 0 for i in [35976, 35978, 35984, 49308])

    def has_permanent_tp(self) -> bool:
        """Returns True if the account owns Permanent Trading Post Express/Contract (IDs 35978, 35976, 35986, 35987)."""
        return any(self.total_item_count(i) > 0 for i in [35978, 35976, 35986, 35987])

    def has_permanent_merchant(self) -> bool:
        """Returns True if the account owns Permanent Merchant Express/Contract (IDs 35977, 35985)."""
        return any(self.total_item_count(i) > 0 for i in [35977, 35985])

    def has_permanent_hair_stylist(self) -> bool:
        """Returns True if the account owns Permanent Hair Stylist Contract (IDs 35984, 35988, 36173)."""
        return any(self.total_item_count(i) > 0 for i in [35984, 35988, 36173])

    def has_permanent_contracts(self) -> bool:
        """Returns True if the account owns any permanent service contract."""
        return self.has_permanent_bank() or self.has_permanent_tp() or self.has_permanent_merchant() or self.has_permanent_hair_stylist()

    def has_ley_energy_converter(self) -> bool:
        """Returns True if the account owns Ley-Energy Matter Converter (IDs 67280, 69949)."""
        return any(self.total_item_count(i) > 0 for i in [67280, 69949])

    def has_karmic_converter(self) -> bool:
        """Returns True if the account owns Karmic Converter (IDs 66624, 67038)."""
        return any(self.total_item_count(i) > 0 for i in [66624, 67038])

    def has_sentient_converters(self) -> bool:
        """Returns True if the account owns Gleam of Sentience or any Sentient series converter."""
        sentient_ids = [92209, 81790, 79895, 82418, 80894, 81700, 66341, 69887, 68369, 73248]
        return any(self.total_item_count(i) > 0 for i in sentient_ids)

    def has_portal_tomes(self) -> bool:
        """Returns True if the account owns any Living World portal tome or scroll."""
        tome_ids = [80332, 79899, 87508, 86586, 92850, 92272, 97009, 100788, 95430]
        return any(self.total_item_count(i) > 0 for i in tome_ids)

    def has_lounge_pass(self) -> bool:
        """Returns True if the account owns any VIP lounge pass or portal scroll."""
        return len(self.owned_lounges()) > 0

    def has_recharging_teleport_to_friend(self) -> bool:
        """Returns True if the account owns Recharging Teleport to Friend (90335)."""
        return "teleport_to_friend" in self.owned_convenience_items()

    def has_silver_fed(self) -> bool:
        """Returns True if the account owns Silver-Fed Salvage-o-Matic (67027)."""
        return "silver_fed" in self.owned_convenience_items()

    def has_copper_fed(self) -> bool:
        """Returns True if the account owns Copper-Fed Salvage-o-Matic (44602)."""
        return "copper_fed" in self.owned_convenience_items()

    def has_runecrafter(self) -> bool:
        """Returns True if the account owns Runecrafter's Salvage-o-Matic (87400)."""
        return "runecrafter" in self.owned_convenience_items()

    def has_upgrade_extractor(self) -> bool:
        """Returns True if the account owns Endless Upgrade Extractor (93121)."""
        return "upgrade_extractor" in self.owned_convenience_items()

    def has_mystic_forge_conduit(self) -> bool:
        """Returns True if the account owns Mystic Forge Conduit (70010 / 36014 / 35727)."""
        return "mystic_forge_conduit" in self.owned_convenience_items()

    def has_gobbler(self) -> bool:
        """Returns True if the account owns Zhaitaffy Gobbler (67836), Candy Corn Gobbler (67037/67040/67393), or Snowflake Gobbler (79523/86675/92585)."""
        gobbler_ids = [67836, 67037, 67040, 67393, 79523, 86675, 92585]
        return any(self.total_item_count(gid) > 0 for gid in gobbler_ids)

    def tomes_of_knowledge_count(self) -> int:
        """Returns total owned count of Tomes of Knowledge (IDs 19983 and 43766)."""
        return self.total_item_count(19983) + self.total_item_count(43766)

    def zhaitaffy_gobblers_count(self) -> int:
        """Returns count of Zhaitaffy Gobbler (ID 67836)."""
        return self.total_item_count(67836)

    def candy_corn_gobblers_count(self) -> int:
        """Returns count of Candy Corn Gobbler (ID 67037 / 67040 / 67393)."""
        return self.total_item_count(67037) + self.total_item_count(67040) + self.total_item_count(67393)

    def experience_boosters_count(self) -> int:
        """Returns count of Experience Boosters."""
        return sum(self.total_item_count(i) for i in [19997, 20002, 41819, 8417, 78954])

    def heroic_boosters_count(self) -> int:
        """Returns count of Heroic Boosters."""
        return sum(self.total_item_count(i) for i in [20005, 41818, 67500, 67501])

    def karma_boosters_count(self) -> int:
        """Returns count of Karma Boosters."""
        return sum(self.total_item_count(i) for i in [20001, 8419, 41821, 92843])

    def wxp_boosters_count(self) -> int:
        """Returns count of WXP / WvW Boosters."""
        return sum(self.total_item_count(i) for i in [43499, 45056, 45060, 43485])

    def birthday_celebration_boosters_count(self) -> int:
        """Returns count of Birthday / Celebration Boosters."""
        return sum(self.total_item_count(i) for i in [45003, 45037, 45038, 77749, 67836])


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


class AccountDiffEngine:
    """Recursive graph traversal engine for computing inventory deltas and progression gaps."""

    def __init__(self, graph_store: Optional[PrioryGraphStore] = None):
        self.store = graph_store

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
        item_meta = self.store.get_item_by_id(goal_item_id)
        goal_name = item_meta["label"] if item_meta else f"Item {goal_item_id}"

        # 1. Armory Max Cap & Saturation Check
        cap_query = """
        SELECT ?cap WHERE {
            ?item priory:gw2Id ?gw2Id .
            { ?item priory:armoryMaxCap ?cap } UNION { ?item priory:maxArmoryCapacity ?cap }
        } LIMIT 1
        """
        cap_res = self.store.query(cap_query, init_bindings={"gw2Id": Literal(goal_item_id)})
        armory_max_cap = int(cap_res[0]["cap"]) if cap_res else 1
        armory_owned = account.legendary_armory.get(goal_item_id, 0)
        is_saturated = armory_owned >= armory_max_cap

        # 2. Achievement Prerequisites Check
        ach_query = """
        SELECT ?ach ?achId ?achLabel ?achDef WHERE {
            ?item priory:gw2Id ?gw2Id ;
                  priory:requiresAchievement ?ach .
            ?ach priory:achievementId ?achId .
            OPTIONAL { ?ach rdfs:label ?achLabel }
            OPTIONAL { ?ach skos:definition ?achDef }
        }
        """
        ach_res = self.store.query(ach_query, init_bindings={"gw2Id": Literal(goal_item_id)})
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
        mast_res = self.store.query(mast_query, init_bindings={"gw2Id": Literal(goal_item_id)})
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
        container_query = """
        SELECT ?containerId ?containerLabel WHERE {
            ?container priory:unpacksInto ?item ;
                       priory:gw2Id ?containerId .
            ?item priory:gw2Id ?gw2Id .
            OPTIONAL { ?container rdfs:label ?containerLabel }
        }
        """
        c_res = self.store.query(container_query, init_bindings={"gw2Id": Literal(item_id)})
        for c_row in c_res:
            c_id = int(c_row["containerId"])
            if account.total_item_count(c_id) > 0:
                return c_row.get("containerLabel", "Choice Chest in Bank")
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

        item_meta = self.store.get_item_by_id(item_id)
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
                return node

            # Check 0.5: Tradable Precursor (e.g. Dusk, Dawn for Gen 1 legendaries - treated as leaf component unless directly queried)
            is_tradable_precursor = False
            if goal_item_id is not None and item_id != goal_item_id:
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
                tp_res = self.store.query(tp_query, init_bindings={"gw2Id": Literal(item_id)})
                if tp_res:
                    is_tradable_precursor = True

            if not is_tradable_precursor:
                # Check 1: Direct crafting recipes producing this item
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
                recipes = self.store.query(rec_query, init_bindings={"gw2Id": Literal(item_id)})

                if recipes:
                    # Multi-discipline preference: Select recipe matching player's active high-level discipline
                    selected_recipe_str = None
                    if len(recipes) > 1 and account.disciplines:
                        for r in recipes:
                            disc_raw = r.get("discipline", "")
                            disc_name = disc_raw.split("/")[-1].lower() if disc_raw else ""
                            req_rating = int(r.get("requiredRating", 0)) if r.get("requiredRating") is not None else 0
                            if disc_name and account.disciplines.get(disc_name, 0) >= req_rating:
                                selected_recipe_str = r["recipe"]
                                break

                    if not selected_recipe_str:
                        selected_recipe_str = recipes[0]["recipe"]

                    if used_recipes is not None:
                        used_recipes.add(selected_recipe_str)

                    # Fetch ingredients for the selected recipe
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
                    ingredients = self.store.query(ing_query, init_bindings={"recipe": URIRef(selected_recipe_str)})
                    if ingredients:
                        for ing in ingredients:
                            ing_id = int(ing["ingredientId"])
                            ing_qty = int(ing["quantity"]) * missing
                            sub_node = self._resolve_node(
                                ing_id, ing_qty, account, summary_missing, missing_currencies, used_recipes, branch_visited, goal_item_id
                            )
                            node.sub_requirements.append(sub_node)
                        return node

            # Check 2: Vendor Exchange with Currency (e.g. Gift of Craftsmanship -> Provisioner Tokens, Gift of Ascalon -> Tales of Dungeon Delving)
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
            if v_res:
                v_info = v_res[0]
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

                if owned_curr >= total_curr_needed:
                    node.is_satisfied = True
                    node.missing_quantity = 0
                    return node
                else:
                    curr_missing = total_curr_needed - owned_curr
                    missing_currencies[str(curr_label)] = missing_currencies.get(str(curr_label), 0) + curr_missing
                    summary_missing[label] = summary_missing.get(label, 0) + missing
                    return node

            # Check 3: Leaf crafting material
            summary_missing[label] = summary_missing.get(label, 0) + missing

        return node

    def _evaluate_discipline_requirements(self, used_recipes: Set[str], account: AccountState) -> List[Dict[str, Any]]:
        """Determines if the account lacks required crafting disciplines for used recipes."""
        missing = []
        if not used_recipes:
            return missing

        disc_query = """
        SELECT DISTINCT ?recipe ?discipline ?requiredRating WHERE {
            ?recipe a priory:DisciplineRecipe ;
                    priory:requiresDiscipline ?discipline .
            OPTIONAL { ?recipe priory:requiredRating ?requiredRating }
            OPTIONAL { ?recipe priory:requiresRating ?requiredRating }
        }
        """
        for row in self.store.query(disc_query):
            rec_uri = row["recipe"]
            if rec_uri in used_recipes:
                disc_uri = row.get("discipline", "")
                disc_name = disc_uri.split("/")[-1].lower() if disc_uri else "unknown"
                req_rating = int(row.get("requiredRating", 0)) if row.get("requiredRating") is not None else 0
                player_rating = account.disciplines.get(disc_name, 0)

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

    def verify_legendary_prerequisites(self, goal_item_id: int, account_state: AccountState) -> PrerequisiteReport:
        """Verifies account prerequisites (mastery tiers, active crafting, world completion, precursor collections) for crafting a legendary goal."""
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

        if is_gen1:
            # Gen 1 precursor crafting / weapon forging requires Tier 3 Historian of the Armaments
            # (Tier 1 for Dusk I, Tier 2 for Dusk II, Tier 3 for Dusk III)
            required_tier = 3
            if cur_crafting_mastery < required_tier:
                tier_labels = {
                    1: "Central Tyria Legendary Crafting Tier 1: Revered Antiquarian",
                    2: "Central Tyria Legendary Crafting Tier 2: Magister of Legends",
                    3: "Central Tyria Legendary Crafting Tier 3: Historian of the Armaments",
                }
                for t in range(cur_crafting_mastery + 1, required_tier + 1):
                    missing_masteries.append(tier_labels[t])
        elif is_gen2:
            # Gen 2 requires Tier 4 Scholar of Secrets
            required_tier = 4
            if cur_crafting_mastery < required_tier:
                tier_labels = {
                    1: "Central Tyria Legendary Crafting Tier 1: Revered Antiquarian",
                    2: "Central Tyria Legendary Crafting Tier 2: Magister of Legends",
                    3: "Central Tyria Legendary Crafting Tier 3: Historian of the Armaments",
                    4: "Central Tyria Legendary Crafting Tier 4: Scholar of Secrets",
                }
                for t in range(cur_crafting_mastery + 1, required_tier + 1):
                    missing_masteries.append(tier_labels[t])
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
        if collection_key not in HOBBS_COLLECTIONS:
            if goal_item_id in GEN1_WEAPONS:
                collection_key = GEN1_WEAPONS[goal_item_id]["precursor_id"]
            elif goal_item_id in GEN2_WEAPONS:
                collection_key = GEN2_WEAPONS[goal_item_id]["precursor_id"]

        precursor_collection_step: Optional[str] = None
        precursor_collection_bits_done: int = 0
        precursor_collection_bits_total: int = 0

        if collection_key in HOBBS_COLLECTIONS:
            tiers = HOBBS_COLLECTIONS[collection_key]
            last_tier = tiers[-1]
            if goal_item_id in GEN1_WEAPONS:
                precursor_id = GEN1_WEAPONS[goal_item_id]["precursor_id"]
            elif goal_item_id in GEN2_WEAPONS:
                precursor_id = GEN2_WEAPONS[goal_item_id]["precursor_id"]
            else:
                precursor_id = collection_key

            has_precursor = (
                account_state.total_item_count(precursor_id) > 0
                or account_state.total_item_count(goal_item_id) > 0
                or account_state.has_legendary_unlocked(goal_item_id)
            )

            if has_precursor:
                precursor_collection_step = "COMPLETED"
                precursor_collection_bits_done = last_tier["bits_total"]
                precursor_collection_bits_total = last_tier["bits_total"]
            else:
                current_tier = None
                for t in tiers:
                    t_done = False
                    for aid in t["ach_ids"]:
                        if aid in account_state.completed_achievements:
                            t_done = True
                            break
                        if account_state.achievements.get(aid, 0) >= t["bits_total"]:
                            t_done = True
                            break
                    if not t_done:
                        current_tier = t
                        break

                if current_tier is None:
                    precursor_collection_step = "COMPLETED"
                    precursor_collection_bits_done = last_tier["bits_total"]
                    precursor_collection_bits_total = last_tier["bits_total"]
                else:
                    precursor_collection_step = current_tier["name"]
                    precursor_collection_bits_total = current_tier["bits_total"]
                    bits_done = 0
                    for aid in current_tier["ach_ids"]:
                        if aid in account_state.achievement_bits:
                            bits_done = max(bits_done, len(account_state.achievement_bits[aid]))
                        if aid in account_state.achievements:
                            bits_done = max(bits_done, account_state.achievements[aid])
                    precursor_collection_bits_done = min(bits_done, precursor_collection_bits_total)
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
            character_discipline_assignments=character_discipline_assignments
        )


# ==============================================================================
# Legendary Item Metadata & Grandmaster Hobbs Precursor Collection Definitions
# ==============================================================================

GEN1_WEAPONS: Dict[int, Dict[str, Any]] = {
    30704: {"name": "Twilight", "precursor_id": 29185, "precursor_name": "Dusk", "type": "Greatsword", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    30703: {"name": "Sunrise", "precursor_id": 29184, "precursor_name": "Dawn", "type": "Greatsword", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    30689: {"name": "Eternity", "precursor_id": 30704, "precursor_name": "Twilight", "type": "Greatsword", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    30699: {"name": "Bolt", "precursor_id": 29167, "precursor_name": "Zap", "type": "Sword", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    30684: {"name": "Frostfang", "precursor_id": 29169, "precursor_name": "Tooth of Frostfang", "type": "Axe", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    30687: {"name": "Incinerator", "precursor_id": 29165, "precursor_name": "Spark", "type": "Dagger", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    30690: {"name": "The Juggernaut", "precursor_id": 29172, "precursor_name": "The Colossus", "type": "Hammer", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    30692: {"name": "The Moot", "precursor_id": 29166, "precursor_name": "The Energizer", "type": "Mace", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    30696: {"name": "The Flameseeker Prophecies", "precursor_id": 29177, "precursor_name": "The Chosen", "type": "Shield", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    30691: {"name": "Kamohoali'i Kotaki", "precursor_id": 29183, "precursor_name": "Carcharias", "type": "Spear", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    30685: {"name": "Kudzu", "precursor_id": 29171, "precursor_name": "Leaf of Kudzu", "type": "Longbow", "disc": ("huntsman", 500), "sec_disc": ("leatherworker", 400)},
    30686: {"name": "The Dreamer", "precursor_id": 29175, "precursor_name": "The Lover", "type": "ShortBow", "disc": ("huntsman", 500), "sec_disc": ("leatherworker", 400)},
    30694: {"name": "The Predator", "precursor_id": 29173, "precursor_name": "The Hunter", "type": "Rifle", "disc": ("huntsman", 500), "sec_disc": ("weaponsmith", 400)},
    30693: {"name": "Quip", "precursor_id": 29168, "precursor_name": "Chaos Gun", "type": "Pistol", "disc": ("huntsman", 500), "sec_disc": ("weaponsmith", 400)},
    30700: {"name": "Rodgort", "precursor_id": 29179, "precursor_name": "Rodgort's Flame", "type": "Torch", "disc": ("huntsman", 500), "sec_disc": ("leatherworker", 400)},
    30702: {"name": "Howler", "precursor_id": 29180, "precursor_name": "Howl", "type": "Warhorn", "disc": ("huntsman", 500), "sec_disc": ("leatherworker", 400)},
    30697: {"name": "Frenzy", "precursor_id": 29181, "precursor_name": "Rage", "type": "HarpoonGun", "disc": ("huntsman", 500), "sec_disc": ("weaponsmith", 400)},
    30698: {"name": "The Bifrost", "precursor_id": 29174, "precursor_name": "The Legend", "type": "Staff", "disc": ("artificer", 500), "sec_disc": ("tailor", 400)},
    30695: {"name": "Meteorlogicus", "precursor_id": 29170, "precursor_name": "Storm", "type": "Scepter", "disc": ("artificer", 500), "sec_disc": ("tailor", 400)},
    30688: {"name": "The Minstrel", "precursor_id": 29178, "precursor_name": "The Bard", "type": "Focus", "disc": ("artificer", 500), "sec_disc": ("tailor", 400)},
    30701: {"name": "Kraitkin", "precursor_id": 29182, "precursor_name": "Venom", "type": "Trident", "disc": ("artificer", 500), "sec_disc": ("tailor", 400)},
}

GEN2_WEAPONS: Dict[int, Dict[str, Any]] = {
    71383: {"name": "Nevermore", "precursor_id": 71384, "precursor_name": "The Raven Staff", "type": "Staff", "disc": ("artificer", 500), "sec_disc": ("tailor", 400)},
    76158: {"name": "Astralaria", "precursor_id": 76159, "precursor_name": "The Mechanism", "type": "Axe", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    75207: {"name": "HOPE", "precursor_id": 75208, "precursor_name": "Prototype", "type": "Pistol", "disc": ("huntsman", 500), "sec_disc": ("weaponsmith", 400)},
    78052: {"name": "Chuka and Champawat", "precursor_id": 78053, "precursor_name": "Tigris", "type": "ShortBow", "disc": ("huntsman", 500), "sec_disc": ("leatherworker", 400)},
    79562: {"name": "Shooshadoo", "precursor_id": 79563, "precursor_name": "Friendship", "type": "Shield", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    79802: {"name": "Eureka", "precursor_id": 79803, "precursor_name": "Endeavor", "type": "Mace", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    81206: {"name": "The Shining Blade", "precursor_id": 81207, "precursor_name": "Save the Queen", "type": "Sword", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    82791: {"name": "Sharur", "precursor_id": 82792, "precursor_name": "The Call", "type": "Hammer", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    86303: {"name": "The HMS Divinity", "precursor_id": 86304, "precursor_name": "The Ambition", "type": "Rifle", "disc": ("huntsman", 500), "sec_disc": ("weaponsmith", 400)},
    86675: {"name": "The Binding of Ipos", "precursor_id": 86676, "precursor_name": "Ars Goetia", "type": "Focus", "disc": ("artificer", 500), "sec_disc": ("tailor", 400)},
    87687: {"name": "Claw of the Khan-Ur", "precursor_id": 87688, "precursor_name": "Touch of the Khan-Ur", "type": "Dagger", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    88955: {"name": "Xiuquatl", "precursor_id": 88956, "precursor_name": "Tlehco", "type": "Scepter", "disc": ("artificer", 500), "sec_disc": ("tailor", 400)},
    89854: {"name": "Pharus", "precursor_id": 89855, "precursor_name": "Spero", "type": "Longbow", "disc": ("huntsman", 500), "sec_disc": ("leatherworker", 400)},
    90551: {"name": "Exordium", "precursor_id": 90552, "precursor_name": "Epitaph", "type": "Greatsword", "disc": ("weaponsmith", 500), "sec_disc": ("armorsmith", 400)},
    91876: {"name": "Verdarach", "precursor_id": 91877, "precursor_name": "Call to Arms", "type": "Warhorn", "disc": ("huntsman", 500), "sec_disc": ("leatherworker", 400)},
}

GEN3_WEAPON_NAMES: Dict[int, str] = {
    96203: "Aurene's Bite", 96937: "Aurene's Claw", 96652: "Aurene's Fang", 97165: "Aurene's Tail",
    97077: "Aurene's Rending", 96228: "Aurene's Voice", 96841: "Aurene's Argument", 96603: "Aurene's Scale",
    96356: "Aurene's Gaze", 97594: "Aurene's Insight", 95684: "Aurene's Flight", 96376: "Aurene's Persuasion",
    97141: "Aurene's Breath", 96613: "Aurene's Wisdom", 95675: "Aurene's Wing", 95612: "Aurene's Weight"
}

GEN3_WEAPON_DISCIPLINES: Dict[int, Tuple[str, int]] = {
    96203: ("weaponsmith", 500), 96937: ("weaponsmith", 500), 96652: ("weaponsmith", 500), 97165: ("weaponsmith", 500),
    97077: ("weaponsmith", 500), 96228: ("huntsman", 500), 96841: ("huntsman", 500), 96603: ("weaponsmith", 500),
    96356: ("artificer", 500), 97594: ("artificer", 500), 95684: ("huntsman", 500), 96376: ("huntsman", 500),
    97141: ("huntsman", 500), 96613: ("artificer", 500), 95675: ("huntsman", 500), 95612: ("weaponsmith", 500)
}

ARMOR_NAMES: Dict[int, str] = {
    80384: "Perfected Envoy Helm", 80435: "Perfected Envoy Pauldrons", 80258: "Perfected Envoy Breastplate",
    80145: "Perfected Envoy Gauntlets", 80161: "Perfected Envoy Tassets", 80248: "Perfected Envoy Greaves",
    80296: "Perfected Envoy Mask", 80190: "Perfected Envoy Shoulderguards", 80277: "Perfected Envoy Jerkin",
    80252: "Perfected Envoy Vambraces", 80281: "Perfected Envoy Leggings", 80557: "Perfected Envoy Boots",
    80200: "Perfected Envoy Hood", 80356: "Perfected Envoy Mantle", 80131: "Perfected Envoy Vestments",
    80196: "Perfected Envoy Pants",
    101001: "Obsidian Helm", 101002: "Obsidian Pauldrons", 101003: "Obsidian Breastplate",
    101004: "Obsidian Gauntlets", 101005: "Obsidian Tassets", 101006: "Obsidian Greaves",
    101007: "Obsidian Mask", 101008: "Obsidian Shoulderguards", 101009: "Obsidian Jerkin",
    101010: "Obsidian Vambraces", 101011: "Obsidian Leggings", 101012: "Obsidian Boots"
}

LEGENDARY_ARMOR_DISCIPLINES: Dict[int, Tuple[str, int]] = {
    # Heavy -> Armorsmith 500
    80384: ("armorsmith", 500), 80435: ("armorsmith", 500), 80258: ("armorsmith", 500),
    80145: ("armorsmith", 500), 80161: ("armorsmith", 500), 80248: ("armorsmith", 500),
    101001: ("armorsmith", 500), 101002: ("armorsmith", 500), 101003: ("armorsmith", 500),
    101004: ("armorsmith", 500), 101005: ("armorsmith", 500), 101006: ("armorsmith", 500),
    # Medium -> Leatherworker 500
    80296: ("leatherworker", 500), 80190: ("leatherworker", 500), 80277: ("leatherworker", 500),
    80252: ("leatherworker", 500), 80281: ("leatherworker", 500), 80557: ("leatherworker", 500),
    101007: ("leatherworker", 500), 101008: ("leatherworker", 500), 101009: ("leatherworker", 500),
    101010: ("leatherworker", 500), 101011: ("leatherworker", 500), 101012: ("leatherworker", 500),
    # Light -> Tailor 500
    80200: ("tailor", 500), 80356: ("tailor", 500), 80131: ("tailor", 500),
    80196: ("tailor", 500)
}

PRECURSOR_NAMES: Dict[int, str] = {
    29185: "Dusk", 29184: "Dawn", 29167: "Zap", 29169: "Tooth of Frostfang", 29171: "Leaf of Kudzu",
    29175: "The Lover", 29165: "Spark", 29178: "The Bard", 29172: "The Colossus", 29166: "The Energizer",
    29177: "The Chosen", 29183: "Carcharias", 29168: "Chaos Gun", 29173: "The Hunter", 29170: "Storm",
    29181: "Rage", 29174: "The Legend", 29179: "Rodgort's Flame", 29182: "Venom", 29180: "Howl",
    71384: "The Raven Staff", 76159: "The Mechanism", 75208: "Prototype", 78053: "Tigris"
}

GEN1_WEAPON_IDS: Set[int] = set(GEN1_WEAPONS.keys())
GEN1_PRECURSOR_IDS: Set[int] = {w["precursor_id"] for w in GEN1_WEAPONS.values()}
GEN2_WEAPON_IDS: Set[int] = set(GEN2_WEAPONS.keys())
GEN2_PRECURSOR_IDS: Set[int] = {w["precursor_id"] for w in GEN2_WEAPONS.values()}
GEN3_WEAPON_IDS: Set[int] = set(GEN3_WEAPON_NAMES.keys())
LEGENDARY_ARMOR_IDS: Set[int] = set(ARMOR_NAMES.keys())

PRECURSOR_TO_WEAPON: Dict[int, int] = {}
for _w_id, _w_info in GEN1_WEAPONS.items():
    PRECURSOR_TO_WEAPON[_w_info["precursor_id"]] = _w_id
for _w_id, _w_info in GEN2_WEAPONS.items():
    PRECURSOR_TO_WEAPON[_w_info["precursor_id"]] = _w_id

HOBBS_COLLECTIONS: Dict[int, List[Dict[str, Any]]] = {
    29185: [
        {"tier": 1, "name": "Dusk I: The Experimental Nightsword", "ach_ids": [2420, 2379], "bits_total": 15, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Dusk II: The Perfected Nightsword", "ach_ids": [2184, 2455, 2382], "bits_total": 16, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Dusk III: Dusk", "ach_ids": [2183, 2380], "bits_total": 30, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29184: [
        {"tier": 1, "name": "Sunrise I: The Experimental Daysword", "ach_ids": [2253], "bits_total": 15, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Sunrise II: The Perfected Daysword", "ach_ids": [2278], "bits_total": 16, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Sunrise III: Dawn", "ach_ids": [2630], "bits_total": 35, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29167: [
        {"tier": 1, "name": "Bolt I: The Experimental Sword", "ach_ids": [2355], "bits_total": 21, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Bolt II: The Perfected Sword", "ach_ids": [2356], "bits_total": 13, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Bolt III: Zap", "ach_ids": [2480], "bits_total": 30, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29169: [
        {"tier": 1, "name": "Frostfang I: The Experimental Axe", "ach_ids": [2478], "bits_total": 15, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Frostfang II: The Perfected Axe", "ach_ids": [2606], "bits_total": 12, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Frostfang III: Tooth of Frostfang", "ach_ids": [2393], "bits_total": 34, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29171: [
        {"tier": 1, "name": "Kudzu I: The Experimental Longbow", "ach_ids": [2193], "bits_total": 13, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Kudzu II: The Perfected Longbow", "ach_ids": [2311], "bits_total": 16, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Kudzu III: Leaf of Kudzu", "ach_ids": [2383], "bits_total": 29, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29175: [
        {"tier": 1, "name": "The Dreamer I: The Experimental Short Bow", "ach_ids": [2481], "bits_total": 14, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "The Dreamer II: The Perfected Short Bow", "ach_ids": [2610], "bits_total": 16, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "The Dreamer III: The Lover", "ach_ids": [2428], "bits_total": 30, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29165: [
        {"tier": 1, "name": "Incinerator I: The Experimental Dagger", "ach_ids": [2564], "bits_total": 18, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Incinerator II: The Perfected Dagger", "ach_ids": [2458], "bits_total": 15, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Incinerator III: Spark", "ach_ids": [2502], "bits_total": 24, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29178: [
        {"tier": 1, "name": "The Minstrel I: The Experimental Focus", "ach_ids": [2313], "bits_total": 15, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "The Minstrel II: The Perfected Focus", "ach_ids": [2213], "bits_total": 12, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "The Minstrel III: The Bard", "ach_ids": [2242], "bits_total": 33, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29172: [
        {"tier": 1, "name": "The Juggernaut I: The Experimental Hammer", "ach_ids": [2438], "bits_total": 32, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "The Juggernaut II: The Perfected Hammer", "ach_ids": [2241], "bits_total": 16, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "The Juggernaut III: The Colossus", "ach_ids": [2468], "bits_total": 32, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29166: [
        {"tier": 1, "name": "The Moot I: The Experimental Mace", "ach_ids": [2177], "bits_total": 14, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "The Moot II: The Perfected Mace", "ach_ids": [2291], "bits_total": 14, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "The Moot III: The Energizer", "ach_ids": [2374], "bits_total": 35, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29168: [
        {"tier": 1, "name": "Quip I: The Experimental Pistol", "ach_ids": [2389], "bits_total": 16, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Quip II: The Perfected Pistol", "ach_ids": [2498], "bits_total": 13, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Quip III: Chaos Gun", "ach_ids": [2524], "bits_total": 35, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29173: [
        {"tier": 1, "name": "The Predator I: The Experimental Rifle", "ach_ids": [2534], "bits_total": 17, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "The Predator II: The Perfected Rifle", "ach_ids": [2503], "bits_total": 14, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "The Predator III: The Hunter", "ach_ids": [2280], "bits_total": 24, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29170: [
        {"tier": 1, "name": "Meteorlogicus I: The Experimental Scepter", "ach_ids": [2441], "bits_total": 15, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Meteorlogicus II: The Perfected Scepter", "ach_ids": [2391], "bits_total": 11, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Meteorlogicus III: Storm", "ach_ids": [2449], "bits_total": 29, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29177: [
        {"tier": 1, "name": "The Flameseeker Prophecies I: The Experimental Shield", "ach_ids": [2479], "bits_total": 14, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "The Flameseeker Prophecies II: The Perfected Shield", "ach_ids": [2390], "bits_total": 13, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "The Flameseeker Prophecies III: The Chosen", "ach_ids": [2536], "bits_total": 32, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29181: [
        {"tier": 1, "name": "Frenzy I: The Experimental Harpoon Gun", "ach_ids": [2637], "bits_total": 6, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Frenzy II: The Perfected Harpoon Gun", "ach_ids": [2232], "bits_total": 7, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Frenzy III: Rage", "ach_ids": [2409], "bits_total": 18, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29174: [
        {"tier": 1, "name": "The Bifrost I: The Experimental Staff", "ach_ids": [2530], "bits_total": 16, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "The Bifrost II: The Perfected Staff", "ach_ids": [2500], "bits_total": 14, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "The Bifrost III: The Legend", "ach_ids": [2187], "bits_total": 32, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29179: [
        {"tier": 1, "name": "Rodgort I: The Experimental Torch", "ach_ids": [2180], "bits_total": 11, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Rodgort II: The Perfected Torch", "ach_ids": [2596], "bits_total": 12, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Rodgort III: Rodgort's Flame", "ach_ids": [2388], "bits_total": 31, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29182: [
        {"tier": 1, "name": "Kraitkin I: The Experimental Trident", "ach_ids": [2483], "bits_total": 7, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Kraitkin II: The Perfected Trident", "ach_ids": [2522], "bits_total": 9, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Kraitkin III: Venom", "ach_ids": [2296], "bits_total": 21, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29180: [
        {"tier": 1, "name": "Howler I: The Experimental Warhorn", "ach_ids": [2270], "bits_total": 22, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Howler II: The Perfected Warhorn", "ach_ids": [2588], "bits_total": 13, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Howler III: Howl", "ach_ids": [2260], "bits_total": 35, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    29183: [
        {"tier": 1, "name": "Kamohoali'i Kotaki I: The Experimental Spear", "ach_ids": [2642], "bits_total": 6, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Kamohoali'i Kotaki II: The Perfected Spear", "ach_ids": [2306], "bits_total": 7, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Kamohoali'i Kotaki III: Carcharias", "ach_ids": [2535], "bits_total": 28, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
    ],
    71384: [
        {"tier": 1, "name": "Nevermore I: Ravenswood Branch", "ach_ids": [2528], "bits_total": 14, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Nevermore II: Ravenswood Staff", "ach_ids": [2288], "bits_total": 14, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Nevermore III: The Raven Staff", "ach_ids": [2336], "bits_total": 34, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
        {"tier": 4, "name": "Nevermore IV: The Raven Spirit", "ach_ids": [2550], "bits_total": 63, "mastery_tier": 4, "mastery_name": "Scholar of Secrets"},
    ],
    76159: [
        {"tier": 1, "name": "Astralaria I: The Device", "ach_ids": [2571], "bits_total": 19, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Astralaria II: The Apparatus", "ach_ids": [2447], "bits_total": 14, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Astralaria III: The Mechanism", "ach_ids": [2433], "bits_total": 33, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
        {"tier": 4, "name": "Astralaria IV: The Cosmos", "ach_ids": [2268], "bits_total": 54, "mastery_tier": 4, "mastery_name": "Scholar of Secrets"},
    ],
    75208: [
        {"tier": 1, "name": "HOPE I: Research", "ach_ids": [2450], "bits_total": 20, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "HOPE II: Development", "ach_ids": [2354], "bits_total": 14, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "HOPE III: Prototype", "ach_ids": [2556], "bits_total": 31, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
        {"tier": 4, "name": "HOPE IV: The Catalyst", "ach_ids": [2250], "bits_total": 59, "mastery_tier": 4, "mastery_name": "Scholar of Secrets"},
    ],
    78053: [
        {"tier": 1, "name": "Chuka and Champawat I: Hunter's Journal", "ach_ids": [2920, 2990], "bits_total": 20, "mastery_tier": 1, "mastery_name": "Revered Antiquarian"},
        {"tier": 2, "name": "Chuka and Champawat II: Ambush", "ach_ids": [2921], "bits_total": 16, "mastery_tier": 2, "mastery_name": "Magister of Legends"},
        {"tier": 3, "name": "Chuka and Champawat III: Tigris", "ach_ids": [2951, 2946], "bits_total": 20, "mastery_tier": 3, "mastery_name": "Historian of the Armaments"},
        {"tier": 4, "name": "Chuka and Champawat IV: Baby Book", "ach_ids": [2913, 2943, 2974], "bits_total": 15, "mastery_tier": 4, "mastery_name": "Scholar of Secrets"},
    ]
}

# Also map weapon ID to collection tiers
for _p_id, _tiers in list(HOBBS_COLLECTIONS.items()):
    _w_id = PRECURSOR_TO_WEAPON.get(_p_id)
    if _w_id and _w_id not in HOBBS_COLLECTIONS:
        HOBBS_COLLECTIONS[_w_id] = _tiers


def verify_legendary_prerequisites(
    goal_item_id: int,
    account_state: AccountState,
    graph_store: Optional[PrioryGraphStore] = None
) -> PrerequisiteReport:
    """Convenience standalone wrapper for AccountDiffEngine.verify_legendary_prerequisites."""
    engine = AccountDiffEngine(graph_store=graph_store)
    return engine.verify_legendary_prerequisites(goal_item_id, account_state)
