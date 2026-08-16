"""Official Guild Wars 2 REST API Client (v2).

Handles authenticated account fetches, high-speed 200-chunk bulk lookups,
local disk caching, and Trading Post price queries.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
from engine.account_diff import AccountState

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"


class GW2ApiClient:
    """Async client for GW2 API v2 with bulk chunking and disk caching support."""

    BASE_URL = "https://api.guildwars2.com/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    async def get_items(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        """Batch fetches item metadata by IDs."""
        ids_str = ",".join(map(str, item_ids))
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/items", params={"ids": ids_str})
            resp.raise_for_status()
            return resp.json()

    async def get_tp_prices(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        """Batch fetches live Trading Post buy/sell prices."""
        ids_str = ",".join(map(str, item_ids))
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/commerce/prices", params={"ids": ids_str})
            resp.raise_for_status()
            return resp.json()

    async def fetch_all_item_ids(self) -> List[int]:
        """Fetches all valid item IDs in the entire game (~70,000 IDs)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/items")
            resp.raise_for_status()
            return resp.json()

    async def fetch_all_recipe_ids(self) -> List[int]:
        """Fetches all valid recipe IDs in the entire game (~12,000 IDs)."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.BASE_URL}/recipes")
            resp.raise_for_status()
            return resp.json()

    async def fetch_items_bulk(self, item_ids: List[int], chunk_size: int = 200, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Fetches item details in high-speed 200-item chunks with disk caching."""
        cache_file = CACHE_DIR / "api_items.json"
        cached_items: Dict[str, Dict[str, Any]] = {}

        if use_cache and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_items = json.load(f)
            except Exception:
                cached_items = {}

        missing_ids = [i_id for i_id in item_ids if str(i_id) not in cached_items]
        fetched_items = []

        if missing_ids:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for i in range(0, len(missing_ids), chunk_size):
                    chunk = missing_ids[i:i + chunk_size]
                    ids_str = ",".join(map(str, chunk))
                    try:
                        resp = await client.get(f"{self.BASE_URL}/items", params={"ids": ids_str})
                        if resp.status_code == 200:
                            items_data = resp.json()
                            for item in items_data:
                                cached_items[str(item["id"])] = item
                                fetched_items.append(item)
                    except Exception:
                        pass

            if use_cache:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cached_items, f, indent=2)

        return [cached_items[str(i_id)] for i_id in item_ids if str(i_id) in cached_items]

    async def fetch_recipes_bulk(self, recipe_ids: List[int], chunk_size: int = 200, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Fetches recipe details in high-speed 200-recipe chunks with disk caching."""
        cache_file = CACHE_DIR / "api_recipes.json"
        cached_recipes: Dict[str, Dict[str, Any]] = {}

        if use_cache and cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cached_recipes = json.load(f)
            except Exception:
                cached_recipes = {}

        missing_ids = [r_id for r_id in recipe_ids if str(r_id) not in cached_recipes]

        if missing_ids:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for i in range(0, len(missing_ids), chunk_size):
                    chunk = missing_ids[i:i + chunk_size]
                    ids_str = ",".join(map(str, chunk))
                    try:
                        resp = await client.get(f"{self.BASE_URL}/recipes", params={"ids": ids_str})
                        if resp.status_code == 200:
                            recipes_data = resp.json()
                            for rec in recipes_data:
                                cached_recipes[str(rec["id"])] = rec
                    except Exception:
                        pass

            if use_cache:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cached_recipes, f, indent=2)

        return [cached_recipes[str(r_id)] for r_id in recipe_ids if str(r_id) in cached_recipes]

    async def fetch_account_snapshot(self) -> AccountState:
        """Fetches full player account state across materials, bank, inventory, wallet, legendary armory, and characters."""
        if not self.api_key:
            raise ValueError("An authenticated API key is required to fetch account state.")

        async with httpx.AsyncClient(headers=self.headers, timeout=10.0) as client:
            materials = {}
            bank = {}
            wallet = {}
            inventory = {}
            disciplines = {}
            legendary_armory = {}

            # 1. Materials
            try:
                mat_resp = await client.get(f"{self.BASE_URL}/account/materials")
                if mat_resp.status_code == 200:
                    mat_data = mat_resp.json()
                    materials = {item["id"]: item["count"] for item in mat_data if item.get("count", 0) > 0}
            except Exception:
                pass

            # 2. Bank
            try:
                bank_resp = await client.get(f"{self.BASE_URL}/account/bank")
                if bank_resp.status_code == 200:
                    bank_data = bank_resp.json()
                    for item in bank_data:
                        if item and item.get("id"):
                            bank[item["id"]] = bank.get(item["id"], 0) + item.get("count", 1)
            except Exception:
                pass

            # 3. Wallet
            try:
                wallet_resp = await client.get(f"{self.BASE_URL}/account/wallet")
                if wallet_resp.status_code == 200:
                    wallet_data = wallet_resp.json()
                    wallet = {curr["id"]: curr["value"] for curr in wallet_data}
            except Exception:
                pass

            # 4. Legendary Armory
            try:
                armory_resp = await client.get(f"{self.BASE_URL}/account/legendaryarmory")
                if armory_resp.status_code == 200:
                    armory_data = armory_resp.json()
                    legendary_armory = {item["id"]: item.get("count", 1) for item in armory_data if item.get("id")}
            except Exception:
                pass

            # 5. Shared Inventory Slots
            try:
                shared_resp = await client.get(f"{self.BASE_URL}/account/inventory")
                if shared_resp.status_code == 200:
                    shared_data = shared_resp.json()
                    for s_item in shared_data:
                        if s_item and s_item.get("id"):
                            inventory[s_item["id"]] = inventory.get(s_item["id"], 0) + s_item.get("count", 1)
            except Exception:
                pass

            # 6. Characters (for bag inventories and crafting disciplines)
            try:
                char_resp = await client.get(f"{self.BASE_URL}/characters", params={"page": 0})
                if char_resp.status_code == 200:
                    char_data = char_resp.json()
                    for char in char_data:
                        for disc in char.get("crafting", []):
                            d_name = disc["discipline"].lower()
                            d_rating = disc["rating"]
                            if d_rating > disciplines.get(d_name, 0):
                                disciplines[d_name] = d_rating
                        for bag in char.get("bags", []):
                            if bag:
                                for bag_item in bag.get("inventory", []):
                                    if bag_item and bag_item.get("id"):
                                        b_id = bag_item["id"]
                                        b_cnt = bag_item.get("count", 1)
                                        inventory[b_id] = inventory.get(b_id, 0) + b_cnt
            except Exception:
                pass

            return AccountState(
                materials=materials,
                bank=bank,
                inventory=inventory,
                wallet=wallet,
                legendary_armory=legendary_armory,
                disciplines=disciplines
            )
