"""Official Guild Wars 2 REST API Client (v2) with RFC 7232 ETag Conditional Caching.

Handles authenticated account fetches, high-speed 200-chunk bulk lookups,
local disk caching, Trading Post price queries, and conditional HTTP caching (304 Not Modified)
to eliminate redundant network payload transfers and minimize API latency.
"""

from __future__ import annotations
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx
from engine.account_diff import AccountState, WizardVaultListing

CACHE_DIR = Path(__file__).parent.parent / "data" / "cache"


class MissingApiKeyError(Exception):
    """Raised when an operation requires an authenticated GW2 API key but none is provided."""
    pass


class InsufficientPermissionsError(Exception):
    """Raised when the provided GW2 API key lacks required permissions (account, characters, inventories, builds)."""
    pass


class ETagCacheManager:
    """Manages disk-backed HTTP ETags and JSON response payloads for conditional requests."""

    def __init__(self, cache_path: Optional[Path] = None):
        self.cache_path = cache_path or (CACHE_DIR / "http_etags.json")
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}

    def _save(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception:
            pass

    def get_etag(self, cache_key: str) -> Optional[str]:
        entry = self._cache.get(cache_key)
        return entry.get("etag") if entry else None

    def get_cached_payload(self, cache_key: str) -> Optional[Any]:
        entry = self._cache.get(cache_key)
        return entry.get("payload") if entry else None

    def store_response(self, cache_key: str, etag: Optional[str], payload: Any) -> None:
        self._cache[cache_key] = {
            "etag": etag,
            "timestamp": time.time(),
            "payload": payload
        }
        self._save()

    def clear(self) -> None:
        self._cache = {}
        self._save()


class GW2ApiClient:
    """Async client for GW2 API v2 with bulk chunking, ETag conditional caching, and strict validation."""

    BASE_URL = "https://api.guildwars2.com/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key.strip() if api_key else None
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.etag_manager = ETagCacheManager()

    async def _fetch_conditional(
        self,
        client: httpx.AsyncClient,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_auth: bool = True
    ) -> Tuple[Any, bool]:
        """Performs conditional GET request using RFC 7232 If-None-Match header.
        
        Returns (payload, was_updated_from_network: bool).
        If server returns 304 Not Modified, returns (cached_payload, False) in <20ms.
        """
        param_str = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
        cache_key = f"{endpoint}?{param_str}" if param_str else endpoint
        if use_auth and self.api_key:
            # Scope cache key to API key to prevent cross-account pollution
            key_hash = str(hash(self.api_key[-8:]))
            cache_key = f"{key_hash}:{cache_key}"

        cached_etag = self.etag_manager.get_etag(cache_key)
        req_headers = dict(self.headers) if use_auth and self.headers else {}
        if cached_etag:
            req_headers["If-None-Match"] = cached_etag

        url = f"{self.BASE_URL}/{endpoint}"
        resp = await client.get(url, params=params, headers=req_headers)

        if resp.status_code == 304:
            # 304 Not Modified: 0 KB downloaded!
            cached_data = self.etag_manager.get_cached_payload(cache_key)
            if cached_data is not None:
                return cached_data, False

        if resp.status_code in (401, 403):
            raise InsufficientPermissionsError(
                f"API Key authentication failed for {endpoint}. Check API key permissions (account, characters, inventories, builds)."
            )

        resp.raise_for_status()
        payload = resp.json()
        new_etag = resp.headers.get("ETag") or resp.headers.get("etag")
        self.etag_manager.store_response(cache_key, new_etag, payload)
        return payload, True

    async def validate_api_key(self) -> Dict[str, Any]:
        """Validates API key against /v2/tokeninfo and verifies required permission scopes."""
        if not self.api_key:
            raise MissingApiKeyError("No GW2 API key provided. An authenticated API key is required.")

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.BASE_URL}/tokeninfo", headers=self.headers)
            if resp.status_code != 200:
                raise InsufficientPermissionsError(f"Invalid API key: {resp.text}")
            info = resp.json()
            permissions = set(info.get("permissions", []))
            required = {"account", "characters", "inventories"}
            missing = required - permissions
            if missing:
                raise InsufficientPermissionsError(
                    f"API key '{info.get('name')}' is missing required permissions: {', '.join(missing)}."
                )
            return info

    async def get_items(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        """Batch fetches item metadata by IDs."""
        ids_str = ",".join(map(str, item_ids))
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self.BASE_URL}/items", params={"ids": ids_str})
            resp.raise_for_status()
            return resp.json()

    async def get_tp_prices(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        """Batch fetches live Trading Post buy/sell prices."""
        ids_str = ",".join(map(str, item_ids))
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self.BASE_URL}/commerce/prices", params={"ids": ids_str})
            resp.raise_for_status()
            return resp.json()

    async def fetch_all_item_ids(self) -> List[int]:
        """Fetches all valid item IDs in the entire game (~70,000 IDs)."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self.BASE_URL}/items")
            resp.raise_for_status()
            return resp.json()

    async def fetch_all_recipe_ids(self) -> List[int]:
        """Fetches all valid recipe IDs in the entire game (~12,000 IDs)."""
        async with httpx.AsyncClient(timeout=15.0) as client:
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
        """Fetches full player account state across materials, bank, inventory, wallet, legendary armory, and characters using conditional ETags."""
        if not self.api_key:
            raise MissingApiKeyError(
                "An authenticated GW2 API key is required. Please set GW2_API_KEY in your .env or configuration."
            )

        async with httpx.AsyncClient(headers=self.headers, timeout=20.0) as client:
            materials: Dict[int, int] = {}
            bank: Dict[int, int] = {}
            wallet: Dict[int, int] = {}
            inventory: Dict[int, int] = {}
            disciplines: Dict[str, int] = {}
            legendary_armory: Dict[int, int] = {}

            # 1. Materials
            try:
                mat_data, _ = await self._fetch_conditional(client, "account/materials")
                if isinstance(mat_data, list):
                    materials = {item["id"]: item["count"] for item in mat_data if item.get("count", 0) > 0}
            except Exception as e:
                if isinstance(e, (MissingApiKeyError, InsufficientPermissionsError)):
                    raise

            # 2. Bank
            try:
                bank_data, _ = await self._fetch_conditional(client, "account/bank")
                if isinstance(bank_data, list):
                    for item in bank_data:
                        if item and item.get("id"):
                            bank[item["id"]] = bank.get(item["id"], 0) + item.get("count", 1)
            except Exception as e:
                if isinstance(e, (MissingApiKeyError, InsufficientPermissionsError)):
                    raise

            # 3. Wallet
            try:
                wallet_data, _ = await self._fetch_conditional(client, "account/wallet")
                if isinstance(wallet_data, list):
                    wallet = {curr["id"]: curr["value"] for curr in wallet_data if "id" in curr}
            except Exception as e:
                if isinstance(e, (MissingApiKeyError, InsufficientPermissionsError)):
                    raise

            # 4. Legendary Armory
            try:
                armory_data, _ = await self._fetch_conditional(client, "account/legendaryarmory")
                if isinstance(armory_data, list):
                    legendary_armory = {item["id"]: item.get("count", 1) for item in armory_data if item.get("id")}
            except Exception as e:
                if isinstance(e, (MissingApiKeyError, InsufficientPermissionsError)):
                    raise

            # 5. Shared Inventory Slots
            try:
                shared_data, _ = await self._fetch_conditional(client, "account/inventory")
                if isinstance(shared_data, list):
                    for s_item in shared_data:
                        if s_item and s_item.get("id"):
                            inventory[s_item["id"]] = inventory.get(s_item["id"], 0) + s_item.get("count", 1)
            except Exception as e:
                if isinstance(e, (MissingApiKeyError, InsufficientPermissionsError)):
                    raise

            # 6. Characters (Full payloads including equipment_tabs, build_tabs, bags, crafting)
            raw_characters: List[Dict[str, Any]] = []
            try:
                char_data, _ = await self._fetch_conditional(client, "characters", params={"ids": "all"})
                if isinstance(char_data, list):
                    raw_characters = char_data
                elif isinstance(char_data, list) and len(char_data) == 0:
                    # Try page=0 fallback
                    char_data, _ = await self._fetch_conditional(client, "characters", params={"page": 0})
                    if isinstance(char_data, list):
                        raw_characters = char_data

                for char in raw_characters:
                    for disc in char.get("crafting", []):
                        d_name = disc.get("discipline", "").lower()
                        d_rating = disc.get("rating", 0)
                        if d_name and d_rating > disciplines.get(d_name, 0):
                            disciplines[d_name] = d_rating
                    for bag in char.get("bags", []):
                        if bag:
                            for bag_item in bag.get("inventory", []):
                                if bag_item and bag_item.get("id"):
                                    b_id = bag_item["id"]
                                    b_cnt = bag_item.get("count", 1)
                                    inventory[b_id] = inventory.get(b_id, 0) + b_cnt
            except Exception as e:
                if isinstance(e, (MissingApiKeyError, InsufficientPermissionsError)):
                    raise

            # 7. Account Achievements
            achievements: Dict[int, int] = {}
            completed_achievements = set()
            try:
                ach_data, _ = await self._fetch_conditional(client, "account/achievements")
                if isinstance(ach_data, list):
                    for ach in ach_data:
                        a_id = ach.get("id")
                        if a_id:
                            achievements[a_id] = ach.get("current", 0)
                            if ach.get("done", False):
                                completed_achievements.add(a_id)
            except Exception as e:
                if isinstance(e, (MissingApiKeyError, InsufficientPermissionsError)):
                    raise

            # 8. Account Masteries
            masteries: Dict[int, int] = {}
            try:
                mast_data, _ = await self._fetch_conditional(client, "account/masteries")
                if isinstance(mast_data, list):
                    for mast in mast_data:
                        m_id = mast.get("id")
                        if m_id:
                            masteries[m_id] = mast.get("level", 0)
            except Exception as e:
                if isinstance(e, (MissingApiKeyError, InsufficientPermissionsError)):
                    raise

            # 9. Wizard's Vault Listings
            wizards_vault_listings: Dict[int, WizardVaultListing] = {}
            try:
                wv_data, _ = await self._fetch_conditional(client, "account/wizardsvault/listings")
                if isinstance(wv_data, list):
                    for listing in wv_data:
                        l_id = listing.get("id")
                        i_id = listing.get("item_id")
                        if i_id:
                            wizards_vault_listings[i_id] = WizardVaultListing(
                                id=l_id,
                                item_id=i_id,
                                item_count=listing.get("item_count", 1),
                                listing_type=listing.get("type", "Normal"),
                                cost=listing.get("cost", 0),
                                purchased=listing.get("purchased", 0),
                                purchase_limit=listing.get("purchase_limit")
                            )
            except Exception:
                pass

            return AccountState(
                materials=materials,
                bank=bank,
                inventory=inventory,
                wallet=wallet,
                legendary_armory=legendary_armory,
                disciplines=disciplines,
                achievements=achievements,
                completed_achievements=completed_achievements,
                masteries=masteries,
                wizards_vault_listings=wizards_vault_listings,
                characters=raw_characters
            )

    async def fetch_characters(self) -> List[Dict[str, Any]]:
        """Fetches all characters with equipment, bags, crafting disciplines, and build tabs using conditional ETags."""
        if not self.api_key:
            raise MissingApiKeyError("An authenticated GW2 API key is required to fetch characters.")

        async with httpx.AsyncClient(headers=self.headers, timeout=20.0) as client:
            char_data, _ = await self._fetch_conditional(client, "characters", params={"ids": "all"})
            if isinstance(char_data, list):
                return char_data
            char_data, _ = await self._fetch_conditional(client, "characters", params={"page": 0})
            if isinstance(char_data, list):
                return char_data
            return []

    async def get_tp_prices(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        """Fetches current Trading Post buy/sell prices for item IDs via /v2/commerce/prices."""
        if not item_ids:
            return []
        async with httpx.AsyncClient(timeout=15.0) as client:
            prices = []
            for i in range(0, len(item_ids), 100):
                chunk = item_ids[i:i+100]
                ids_str = ",".join(str(x) for x in chunk)
                try:
                    resp = await client.get(f"{self.BASE_URL}/commerce/prices", params={"ids": ids_str})
                    if resp.status_code == 200:
                        prices.extend(resp.json())
                except Exception:
                    pass
            return prices
