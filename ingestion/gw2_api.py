"""Official Guild Wars 2 REST API Client (v2).

Handles authenticated account fetches, static item/recipe lookups, and Trading Post prices.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import httpx
from engine.account_diff import AccountState


class GW2ApiClient:
    """Async client for GW2 API v2."""

    BASE_URL = "https://api.guildwars2.com/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

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

    async def fetch_account_snapshot(self) -> AccountState:
        """Fetches full player account state across materials, bank, inventory, wallet, and characters."""
        if not self.api_key:
            raise ValueError("An authenticated API key is required to fetch account state.")

        async with httpx.AsyncClient(headers=self.headers) as client:
            # 1. Materials
            mat_resp = await client.get(f"{self.BASE_URL}/account/materials")
            mat_data = mat_resp.json() if mat_resp.status_code == 200 else []
            materials = {item["id"]: item["count"] for item in mat_data if item.get("count", 0) > 0}

            # 2. Bank
            bank_resp = await client.get(f"{self.BASE_URL}/account/bank")
            bank_data = bank_resp.json() if bank_resp.status_code == 200 else []
            bank = {}
            for item in bank_data:
                if item and item.get("id"):
                    bank[item["id"]] = bank.get(item["id"], 0) + item.get("count", 1)

            # 3. Wallet
            wallet_resp = await client.get(f"{self.BASE_URL}/account/wallet")
            wallet_data = wallet_resp.json() if wallet_resp.status_code == 200 else []
            wallet = {curr["id"]: curr["value"] for curr in wallet_data}

            # 4. Characters (for inventory and crafting disciplines)
            char_resp = await client.get(f"{self.BASE_URL}/characters", params={"page": 0})
            char_data = char_resp.json() if char_resp.status_code == 200 else []
            
            inventory = {}
            disciplines = {}
            for char in char_data:
                # Disciplines
                for disc in char.get("crafting", []):
                    d_name = disc["discipline"].lower()
                    d_rating = disc["rating"]
                    if d_rating > disciplines.get(d_name, 0):
                        disciplines[d_name] = d_rating
                
                # Bags
                for bag in char.get("bags", []):
                    if bag:
                        for bag_item in bag.get("inventory", []):
                            if bag_item and bag_item.get("id"):
                                b_id = bag_item["id"]
                                b_cnt = bag_item.get("count", 1)
                                inventory[b_id] = inventory.get(b_id, 0) + b_cnt

            # 5. Unlocked Recipes
            recipes_resp = await client.get(f"{self.BASE_URL}/account/recipes")
            unlocked_recipes = recipes_resp.json() if recipes_resp.status_code == 200 else []

            return AccountState(
                materials=materials,
                bank=bank,
                inventory=inventory,
                wallet=wallet,
                disciplines=disciplines,
                unlocked_recipes=unlocked_recipes
            )
