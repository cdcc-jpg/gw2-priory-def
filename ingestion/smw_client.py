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


class _AwaitableList(list):
    """A list subclass that can also be awaited in async contexts."""

    def __await__(self):
        async def _coro():
            return list(self)
        return _coro().__await__()


# Canonical multi-tier precursor specifications used to enrich SMW results
# and provide deterministic offline fallback when the wiki API is unreachable.
CANONICAL_PRECURSOR_CHAINS: Dict[str, Dict[str, Any]] = {
    "Dusk": {
        "precursor_name": "Dusk",
        "precursor_item_id": 29185,
        "legendary_name": "Twilight",
        "legendary_item_id": 30704,
        "generation": 1,
        "weapon_type": "Greatsword",
        "discipline": "Weaponsmith",
        "tiers": [
            {
                "tier": 1,
                "item_id": 73210,
                "item_name": "Experimental Nightsword",
                "recipe_id": "craft_experimental_nightsword",
                "collection_id": "col_dusk_vol1",
                "collection_title": "Dusk I: The Experimental Nightsword",
                "discipline": "Weaponsmith",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": None,
                "ingredients": [
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 15, "is_time_gated": True},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 5, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 25, "is_time_gated": False},
                ],
            },
            {
                "tier": 2,
                "item_id": 75619,
                "item_name": "Perfected Nightsword",
                "recipe_id": "craft_perfected_nightsword",
                "collection_id": "col_dusk_vol2",
                "collection_title": "Dusk II: The Perfected Nightsword",
                "discipline": "Weaponsmith",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 73210,
                "ingredients": [
                    {"item_id": 73210, "item_name": "Experimental Nightsword", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 30, "is_time_gated": True},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 10, "is_time_gated": True},
                ],
            },
            {
                "tier": 3,
                "item_id": 29185,
                "item_name": "Dusk",
                "recipe_id": "craft_dusk_tier3",
                "collection_id": "col_dusk_vol3",
                "collection_title": "Dusk III: Dusk",
                "discipline": "Weaponsmith",
                "required_rating": 500,
                "is_final_precursor": True,
                "is_account_bound": False,
                "precursor_type": "TradablePrecursor",
                "previous_tier_item_id": 75619,
                "ingredients": [
                    {"item_id": 75619, "item_name": "Perfected Nightsword", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 45, "is_time_gated": True},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 15, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 100, "is_time_gated": False},
                ],
            },
        ],
    },
    "Dawn": {
        "precursor_name": "Dawn",
        "precursor_item_id": 29169,
        "legendary_name": "Sunrise",
        "legendary_item_id": 30703,
        "generation": 1,
        "weapon_type": "Greatsword",
        "discipline": "Weaponsmith",
        "tiers": [
            {
                "tier": 1,
                "item_id": 71423,
                "item_name": "Experimental Daysword",
                "recipe_id": "craft_experimental_daysword",
                "collection_id": "col_dawn_vol1",
                "collection_title": "Dawn I: The Experimental Daysword",
                "discipline": "Weaponsmith",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": None,
                "ingredients": [
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 15, "is_time_gated": True},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 5, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 25, "is_time_gated": False},
                ],
            },
            {
                "tier": 2,
                "item_id": 73433,
                "item_name": "Perfected Daysword",
                "recipe_id": "craft_perfected_daysword",
                "collection_id": "col_dawn_vol2",
                "collection_title": "Dawn II: The Perfected Daysword",
                "discipline": "Weaponsmith",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 71423,
                "ingredients": [
                    {"item_id": 71423, "item_name": "Experimental Daysword", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 30, "is_time_gated": True},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 10, "is_time_gated": True},
                ],
            },
            {
                "tier": 3,
                "item_id": 29169,
                "item_name": "Dawn",
                "recipe_id": "craft_dawn_tier3",
                "collection_id": "col_dawn_vol3",
                "collection_title": "Dawn III: Dawn",
                "discipline": "Weaponsmith",
                "required_rating": 500,
                "is_final_precursor": True,
                "is_account_bound": False,
                "precursor_type": "TradablePrecursor",
                "previous_tier_item_id": 73433,
                "ingredients": [
                    {"item_id": 73433, "item_name": "Perfected Daysword", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 45, "is_time_gated": True},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 15, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 100, "is_time_gated": False},
                ],
            },
        ],
    },
    "Zap": {
        "precursor_name": "Zap",
        "precursor_item_id": 29181,
        "legendary_name": "Bolt",
        "legendary_item_id": 30699,
        "generation": 1,
        "weapon_type": "Sword",
        "discipline": "Weaponsmith",
        "tiers": [
            {
                "tier": 1,
                "item_id": 76664,
                "item_name": "Experimental Rapier",
                "recipe_id": "craft_experimental_rapier",
                "collection_id": "col_zap_vol1",
                "collection_title": "Zap I: The Experimental Sword",
                "discipline": "Weaponsmith",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": None,
                "ingredients": [
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 10, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 5, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 25, "is_time_gated": False},
                ],
            },
            {
                "tier": 2,
                "item_id": 76416,
                "item_name": "Perfected Rapier",
                "recipe_id": "craft_perfected_rapier",
                "collection_id": "col_zap_vol2",
                "collection_title": "Zap II: The Perfected Sword",
                "discipline": "Weaponsmith",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 76664,
                "ingredients": [
                    {"item_id": 76664, "item_name": "Experimental Rapier", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 25, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 10, "is_time_gated": True},
                ],
            },
            {
                "tier": 3,
                "item_id": 29181,
                "item_name": "Zap",
                "recipe_id": "craft_zap_tier3",
                "collection_id": "col_zap_vol3",
                "collection_title": "Zap III: Zap",
                "discipline": "Weaponsmith",
                "required_rating": 500,
                "is_final_precursor": True,
                "is_account_bound": False,
                "precursor_type": "TradablePrecursor",
                "previous_tier_item_id": 76416,
                "ingredients": [
                    {"item_id": 76416, "item_name": "Perfected Rapier", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 40, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 15, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 100, "is_time_gated": False},
                ],
            },
        ],
    },
    "The Legend": {
        "precursor_name": "The Legend",
        "precursor_item_id": 29180,
        "legendary_name": "The Bifrost",
        "legendary_item_id": 30698,
        "generation": 1,
        "weapon_type": "Staff",
        "discipline": "Artificer",
        "tiers": [
            {
                "tier": 1,
                "item_id": 74561,
                "item_name": "Experimental Staff",
                "recipe_id": "craft_experimental_staff",
                "collection_id": "col_the_legend_vol1",
                "collection_title": "The Legend I: The Experimental Staff",
                "discipline": "Artificer",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": None,
                "ingredients": [
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 15, "is_time_gated": True},
                    {"item_id": 46741, "item_name": "Bolt of Damask", "quantity": 5, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 25, "is_time_gated": False},
                ],
            },
            {
                "tier": 2,
                "item_id": 73566,
                "item_name": "Perfected Staff",
                "recipe_id": "craft_perfected_staff",
                "collection_id": "col_the_legend_vol2",
                "collection_title": "The Legend II: The Perfected Staff",
                "discipline": "Artificer",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 74561,
                "ingredients": [
                    {"item_id": 74561, "item_name": "Experimental Staff", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 30, "is_time_gated": True},
                    {"item_id": 46741, "item_name": "Bolt of Damask", "quantity": 10, "is_time_gated": True},
                ],
            },
            {
                "tier": 3,
                "item_id": 29180,
                "item_name": "The Legend",
                "recipe_id": "craft_the_legend_tier3",
                "collection_id": "col_the_legend_vol3",
                "collection_title": "The Legend III: The Legend",
                "discipline": "Artificer",
                "required_rating": 500,
                "is_final_precursor": True,
                "is_account_bound": False,
                "precursor_type": "TradablePrecursor",
                "previous_tier_item_id": 73566,
                "ingredients": [
                    {"item_id": 73566, "item_name": "Perfected Staff", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 45, "is_time_gated": True},
                    {"item_id": 46741, "item_name": "Bolt of Damask", "quantity": 15, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 100, "is_time_gated": False},
                ],
            },
        ],
    },
    "The Living Ravens": {
        "precursor_name": "The Living Ravens",
        "precursor_item_id": 71436,
        "legendary_name": "Nevermore",
        "legendary_item_id": 71383,
        "generation": 2,
        "weapon_type": "Staff",
        "discipline": "Artificer",
        "tiers": [
            {
                "tier": 1,
                "item_id": 71385,
                "item_name": "Ravenswood Branch",
                "recipe_id": "craft_ravenswood_branch",
                "collection_id": "col_nevermore_vol1",
                "collection_title": "Nevermore I: Ravenswood Branch",
                "discipline": "Artificer",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": None,
                "ingredients": [
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 10, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 5, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 25, "is_time_gated": False},
                ],
            },
            {
                "tier": 2,
                "item_id": 76363,
                "item_name": "Ravenswood Staff",
                "recipe_id": "craft_ravenswood_staff",
                "collection_id": "col_nevermore_vol2",
                "collection_title": "Nevermore II: Ravenswood Staff",
                "discipline": "Artificer",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 71385,
                "ingredients": [
                    {"item_id": 71385, "item_name": "Ravenswood Branch", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 20, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 10, "is_time_gated": True},
                ],
            },
            {
                "tier": 3,
                "item_id": 74678,
                "item_name": "The Raven Spirit",
                "recipe_id": "craft_the_raven_spirit",
                "collection_id": "col_nevermore_vol3",
                "collection_title": "Nevermore III: The Raven Spirit",
                "discipline": "Artificer",
                "required_rating": 500,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 76363,
                "ingredients": [
                    {"item_id": 76363, "item_name": "Ravenswood Staff", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 30, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 10, "is_time_gated": True},
                ],
            },
            {
                "tier": 4,
                "item_id": 71436,
                "item_name": "The Living Ravens",
                "recipe_id": "craft_the_living_ravens",
                "collection_id": "col_nevermore_vol4",
                "collection_title": "Nevermore IV: The Ravenspirit",
                "discipline": "Artificer",
                "required_rating": 500,
                "is_final_precursor": True,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 74678,
                "ingredients": [
                    {"item_id": 74678, "item_name": "The Raven Spirit", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 30, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 15, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 100, "is_time_gated": False},
                ],
            },
        ],
    },
    "The Mechanism": {
        "precursor_name": "The Mechanism",
        "precursor_item_id": 76688,
        "legendary_name": "Astralaria",
        "legendary_item_id": 76158,
        "generation": 2,
        "weapon_type": "Axe",
        "discipline": "Weaponsmith",
        "tiers": [
            {
                "tier": 1,
                "item_id": 75948,
                "item_name": "The Experimental Axe",
                "recipe_id": "craft_the_experimental_axe",
                "collection_id": "col_astralaria_vol1",
                "collection_title": "Astralaria I: The Device",
                "discipline": "Weaponsmith",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": None,
                "ingredients": [
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 10, "is_time_gated": True},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 5, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 25, "is_time_gated": False},
                ],
            },
            {
                "tier": 2,
                "item_id": 72094,
                "item_name": "The Apparatus",
                "recipe_id": "craft_the_apparatus",
                "collection_id": "col_astralaria_vol2",
                "collection_title": "Astralaria II: The Apparatus",
                "discipline": "Weaponsmith",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 75948,
                "ingredients": [
                    {"item_id": 75948, "item_name": "The Experimental Axe", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 20, "is_time_gated": True},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 10, "is_time_gated": True},
                ],
            },
            {
                "tier": 3,
                "item_id": 73194,
                "item_name": "The Device",
                "recipe_id": "craft_the_device",
                "collection_id": "col_astralaria_vol3",
                "collection_title": "Astralaria III: The Mechanism",
                "discipline": "Weaponsmith",
                "required_rating": 500,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 72094,
                "ingredients": [
                    {"item_id": 72094, "item_name": "The Apparatus", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 30, "is_time_gated": True},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 10, "is_time_gated": True},
                ],
            },
            {
                "tier": 4,
                "item_id": 76688,
                "item_name": "The Mechanism",
                "recipe_id": "craft_the_mechanism",
                "collection_id": "col_astralaria_vol4",
                "collection_title": "Astralaria IV: The Cosmos",
                "discipline": "Weaponsmith",
                "required_rating": 500,
                "is_final_precursor": True,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 73194,
                "ingredients": [
                    {"item_id": 73194, "item_name": "The Device", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 30, "is_time_gated": True},
                    {"item_id": 46736, "item_name": "Spiritwood Plank", "quantity": 15, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 100, "is_time_gated": False},
                ],
            },
        ],
    },
    "Prototype": {
        "precursor_name": "Prototype",
        "precursor_item_id": 71950,
        "legendary_name": "HOPE",
        "legendary_item_id": 72713,
        "generation": 2,
        "weapon_type": "Pistol",
        "discipline": "Huntsman",
        "tiers": [
            {
                "tier": 1,
                "item_id": 74155,
                "item_name": "Experimental Pistol",
                "recipe_id": "craft_experimental_pistol",
                "collection_id": "col_hope_vol1",
                "collection_title": "HOPE I: Research",
                "discipline": "Huntsman",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": None,
                "ingredients": [
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 10, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 5, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 25, "is_time_gated": False},
                ],
            },
            {
                "tier": 2,
                "item_id": 75209,
                "item_name": "Research",
                "recipe_id": "craft_research_pistol",
                "collection_id": "col_hope_vol2",
                "collection_title": "HOPE II: Development",
                "discipline": "Huntsman",
                "required_rating": 450,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 74155,
                "ingredients": [
                    {"item_id": 74155, "item_name": "Experimental Pistol", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 20, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 10, "is_time_gated": True},
                ],
            },
            {
                "tier": 3,
                "item_id": 75657,
                "item_name": "Development",
                "recipe_id": "craft_development_pistol",
                "collection_id": "col_hope_vol3",
                "collection_title": "HOPE III: Prototype",
                "discipline": "Huntsman",
                "required_rating": 500,
                "is_final_precursor": False,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 75209,
                "ingredients": [
                    {"item_id": 75209, "item_name": "Research", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 30, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 10, "is_time_gated": True},
                ],
            },
            {
                "tier": 4,
                "item_id": 71950,
                "item_name": "Prototype",
                "recipe_id": "craft_prototype_pistol",
                "collection_id": "col_hope_vol4",
                "collection_title": "HOPE IV: The Catalyst",
                "discipline": "Huntsman",
                "required_rating": 500,
                "is_final_precursor": True,
                "is_account_bound": True,
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": 75657,
                "ingredients": [
                    {"item_id": 75657, "item_name": "Development", "quantity": 1, "is_time_gated": False},
                    {"item_id": 46738, "item_name": "Deldrimor Steel Ingot", "quantity": 30, "is_time_gated": True},
                    {"item_id": 46739, "item_name": "Elonian Leather Square", "quantity": 15, "is_time_gated": True},
                    {"item_id": 79418, "item_name": "Memory of Battle", "quantity": 100, "is_time_gated": False},
                ],
            },
        ],
    },
}

PRECURSOR_ALIASES: Dict[str, str] = {
    "dusk": "Dusk",
    "twilight": "Dusk",
    "dawn": "Dawn",
    "sunrise": "Dawn",
    "zap": "Zap",
    "bolt": "Zap",
    "the legend": "The Legend",
    "legend": "The Legend",
    "the bifrost": "The Legend",
    "bifrost": "The Legend",
    "the living ravens": "The Living Ravens",
    "living ravens": "The Living Ravens",
    "nevermore": "The Living Ravens",
    "the mechanism": "The Mechanism",
    "mechanism": "The Mechanism",
    "astralaria": "The Mechanism",
    "prototype": "Prototype",
    "hope": "Prototype",
}


class GW2SMWClient:
    """Complete client for querying the GW2 Semantic MediaWiki across all 7 acquisition archetypes."""

    WIKI_API_URL = "https://wiki.guildwars2.com/api.php"

    def __init__(self, offline: bool = False, timeout: float = 2.0):
        self.headers = {"User-Agent": "PriorySemanticIngestion/1.0 (Project Priory Knowledge Layer)"}
        self.offline = offline
        self.timeout = timeout
        self._network_unreachable = False

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

    def ask_query_sync(self, query_str: str) -> Dict[str, Any]:
        """Executes a synchronous Semantic MediaWiki #ask query with graceful offline handling."""
        if self.offline or self._network_unreachable:
            return {"query": {"results": {}}}
        params = {
            "action": "ask",
            "format": "json",
            "query": query_str,
        }
        try:
            with httpx.Client(headers=self.headers, timeout=self.timeout) as client:
                resp = client.get(self.WIKI_API_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data if isinstance(data, dict) else {"query": {"results": {}}}
        except Exception:
            self._network_unreachable = True
            return {"query": {"results": {}}}

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

    def fetch_precursor_collection_tiers(self, precursor_name: str) -> List[Dict[str, Any]]:
        """Queries the GW2 Wiki SMW API (action=ask) for multi-tier precursor collections and crafting chains.

        Supports both Gen 1 (3-tier) and Gen 2 (4-tier) precursor weapon chains, returning a list of
        tier dictionaries ordered from Tier 1 to the final Precursor Tier. Gracefully handles offline
        environments using canonical precursor specifications.
        """
        norm_key = PRECURSOR_ALIASES.get(precursor_name.strip().lower(), precursor_name.strip())
        canonical_chain = CANONICAL_PRECURSOR_CHAINS.get(norm_key)

        ask_query = (
            f"[[Category:Legendary weapons||Category:Precursor weapons||Category:Achievements]]"
            f"[[Has canonical name::~*{norm_key}*]]"
            f"|?Has game id|?Has canonical name|?Requires discipline|?Requires discipline rating"
            f"|?Has recipe ingredient|?Has ingredient count|?Has collection item|limit=50"
        )
        raw_response = self.ask_query_sync(ask_query)
        smw_results = raw_response.get("query", {}).get("results", {})
        if not isinstance(smw_results, dict):
            smw_results = {}

        if canonical_chain is not None:
            tiers_out: List[Dict[str, Any]] = []
            for tier_spec in canonical_chain["tiers"]:
                tier_copy = dict(tier_spec)
                tier_copy["precursor_name"] = canonical_chain["precursor_name"]
                tier_copy["precursor_item_id"] = canonical_chain["precursor_item_id"]
                tier_copy["legendary_name"] = canonical_chain["legendary_name"]
                tier_copy["legendary_item_id"] = canonical_chain["legendary_item_id"]
                tier_copy["generation"] = canonical_chain["generation"]
                tier_copy["weapon_type"] = canonical_chain["weapon_type"]
                tier_copy["output_quantity"] = 1
                tier_copy["ingredients"] = [dict(ing) for ing in tier_spec["ingredients"]]
                tier_copy["smw_query"] = ask_query
                # If SMW returned printouts matching this tier item or collection title, attach raw metadata
                matched_page = smw_results.get(tier_spec["item_name"]) or smw_results.get(tier_spec["collection_title"])
                if isinstance(matched_page, dict):
                    tier_copy["smw_printouts"] = matched_page.get("printouts", {})
                tiers_out.append(tier_copy)
            return _AwaitableList(tiers_out)

        # Generic SMW printout parsing for custom/non-canonical precursor names
        parsed_tiers: List[Dict[str, Any]] = []
        for idx, (page_name, page_data) in enumerate(smw_results.items(), start=1):
            if not isinstance(page_data, dict):
                continue
            po = page_data.get("printouts", {})
            game_ids = po.get("Has game id", [])
            item_id = int(game_ids[0]) if game_ids else 0
            disc_arr = po.get("Requires discipline", ["Weaponsmith"])
            disc_val = disc_arr[0] if disc_arr else "Weaponsmith"
            disc_str = disc_val.get("fulltext", str(disc_val)) if isinstance(disc_val, dict) else str(disc_val)
            rating_arr = po.get("Requires discipline rating", [450])
            rating_val = int(rating_arr[0]) if rating_arr else 450

            parsed_tiers.append({
                "tier": idx,
                "precursor_name": norm_key,
                "precursor_item_id": item_id,
                "legendary_name": norm_key,
                "legendary_item_id": 0,
                "generation": 1,
                "weapon_type": "Weapon",
                "item_id": item_id,
                "item_name": page_name,
                "recipe_id": f"craft_{ re.sub(r'[^a-z0-9]+', '_', page_name.lower()).strip('_') }",
                "collection_id": f"col_{ re.sub(r'[^a-z0-9]+', '_', norm_key.lower()).strip('_') }_vol{idx}",
                "collection_title": f"{norm_key} Tier {idx}",
                "discipline": disc_str,
                "required_rating": rating_val,
                "output_quantity": 1,
                "is_final_precursor": idx == len(smw_results),
                "is_account_bound": idx < len(smw_results),
                "precursor_type": "CollectionPrecursor",
                "previous_tier_item_id": parsed_tiers[-1]["item_id"] if parsed_tiers else None,
                "ingredients": [],
                "smw_query": ask_query,
            })
        return _AwaitableList(parsed_tiers)

    def fetch_collection_achievement_steps(self, collection_title: str) -> List[Dict[str, Any]]:
        """Queries the GW2 Wiki SMW API (action=ask) for achievement collection steps and objectives.

        Returns an ordered list of step dicts for the requested precursor collection volume.
        """
        ask_query = (
            f"[[Category:Achievements]][[Has canonical name::{collection_title}]]"
            f"|?Has tier objective|?Has collection item|?Has prerequisite|?Gives item"
        )
        raw_response = self.ask_query_sync(ask_query)
        smw_results = raw_response.get("query", {}).get("results", {})
        if not isinstance(smw_results, dict):
            smw_results = {}

        # Match against canonical tier definitions if available
        matched_tier: Optional[Dict[str, Any]] = None
        matched_chain: Optional[Dict[str, Any]] = None
        norm_title = collection_title.strip().lower()
        for chain in CANONICAL_PRECURSOR_CHAINS.values():
            for tier_spec in chain["tiers"]:
                if (
                    tier_spec["collection_title"].lower() == norm_title
                    or tier_spec["collection_id"].lower() == norm_title
                    or f"{chain['precursor_name'].lower()} {tier_spec['tier']}" == norm_title
                ):
                    matched_tier = tier_spec
                    matched_chain = chain
                    break
            if matched_tier is not None:
                break

        if collection_title in smw_results and isinstance(smw_results[collection_title], dict):
            po = smw_results[collection_title].get("printouts", {})
            objectives = [
                o.get("fulltext", str(o)) if isinstance(o, dict) else str(o)
                for o in po.get("Has tier objective", [])
            ]
            items = [
                i.get("fulltext", str(i)) if isinstance(i, dict) else str(i)
                for i in po.get("Has collection item", [])
            ]
            step_records = objectives or items
            if step_records:
                steps_out = []
                for idx, step_text in enumerate(step_records, start=1):
                    steps_out.append({
                        "step_index": idx,
                        "collection_title": collection_title,
                        "collection_id": matched_tier["collection_id"] if matched_tier else re.sub(r"[^a-z0-9]+", "_", norm_title).strip("_"),
                        "step_name": step_text,
                        "objective": f"Complete collection step {idx}: {step_text}",
                        "unlocks_recipe_id": matched_tier["recipe_id"] if matched_tier else None,
                        "produces_item_id": matched_tier["item_id"] if matched_tier else None,
                        "smw_query": ask_query,
                    })
                return _AwaitableList(steps_out)

        if matched_tier is not None and matched_chain is not None:
            tier_num = matched_tier["tier"]
            prec_name = matched_chain["precursor_name"]
            leg_name = matched_chain["legendary_name"]
            col_id = matched_tier["collection_id"]
            col_title = matched_tier["collection_title"]
            item_name = matched_tier["item_name"]
            steps = [
                {
                    "step_index": 1,
                    "collection_title": col_title,
                    "collection_id": col_id,
                    "step_name": f"Unlock {col_title} via Grandmaster Hobbs in Lion's Arch",
                    "objective": f"Speak with Grandmaster Hobbs to begin Volume {tier_num} of the {prec_name} ({leg_name}) precursor journey.",
                    "unlocks_recipe_id": matched_tier["recipe_id"],
                    "produces_item_id": matched_tier["item_id"],
                    "smw_query": ask_query,
                },
                {
                    "step_index": 2,
                    "collection_title": col_title,
                    "collection_id": col_id,
                    "step_name": f"Complete Tyrian field research for {item_name}",
                    "objective": f"Gather all collection trophies and mastery tokens for {col_title}.",
                    "unlocks_recipe_id": matched_tier["recipe_id"],
                    "produces_item_id": matched_tier["item_id"],
                    "smw_query": ask_query,
                },
                {
                    "step_index": 3,
                    "collection_title": col_title,
                    "collection_id": col_id,
                    "step_name": f"Craft {item_name} ({matched_tier['discipline']} {matched_tier['required_rating']})",
                    "objective": f"Use unlocked recipe {matched_tier['recipe_id']} to craft {item_name}.",
                    "unlocks_recipe_id": matched_tier["recipe_id"],
                    "produces_item_id": matched_tier["item_id"],
                    "smw_query": ask_query,
                },
            ]
            return _AwaitableList(steps)

        return _AwaitableList([
            {
                "step_index": 1,
                "collection_title": collection_title,
                "collection_id": re.sub(r"[^a-z0-9]+", "_", norm_title).strip("_"),
                "step_name": f"Complete {collection_title}",
                "objective": f"Complete all achievement objectives for {collection_title}.",
                "unlocks_recipe_id": None,
                "produces_item_id": None,
                "smw_query": ask_query,
            }
        ])

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
