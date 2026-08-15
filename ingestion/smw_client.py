"""GW2 Semantic MediaWiki (SMW) Scraper and Parser.

Queries the MediaWiki API (action=ask) to extract Mystic Forge recipes,
vendor tables, and drop sources for semantic ingestion into Project Priory.
"""

from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
import httpx


class GW2SMWClient:
    """Async client for querying the GW2 Semantic MediaWiki."""

    WIKI_API_URL = "https://wiki.guildwars2.com/api.php"

    def __init__(self):
        self.headers = {"User-Agent": "PriorySemanticBot/1.0 (Project Priory GW2 Tool)"}

    async def ask_query(self, query_str: str) -> Dict[str, Any]:
        """Executes a Semantic MediaWiki #ask query via the API."""
        params = {
            "action": "ask",
            "format": "json",
            "query": query_str
        }
        async with httpx.AsyncClient(headers=self.headers) as client:
            resp = await client.get(self.WIKI_API_URL, params=params)
            resp.raise_for_status()
            return resp.json()

    async def get_mystic_forge_recipes_for_item(self, item_name: str) -> List[Dict[str, Any]]:
        """Queries SMW for Mystic Forge recipes producing a given item."""
        ask_query = f"[[Has canonical name::{item_name}]][[Has recipe source::Mystic forge]]|?Has ingredient|?Has output quantity"
        res = await self.ask_query(ask_query)
        
        results = []
        query_res = res.get("query", {}).get("results", {})
        for page_name, page_data in query_res.items():
            printouts = page_data.get("printouts", {})
            ingredients = []
            for ing_record in printouts.get("Has ingredient", []):
                # Format is often "Quantity Item Name" or structured SMW record
                if isinstance(ing_record, dict):
                    ing_item = ing_record.get("fulltext", "")
                    ingredients.append(ing_item)
                else:
                    ingredients.append(str(ing_record))

            results.append({
                "source_page": page_name,
                "output_item": item_name,
                "output_quantity": printouts.get("Has output quantity", [1])[0] if printouts.get("Has output quantity") else 1,
                "ingredients": ingredients
            })
        return results
