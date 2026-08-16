import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
from ingestion.gw2_api import GW2ApiClient


async def check():
    key = os.getenv("GW2_API_KEY")
    client = GW2ApiClient(api_key=key)
    account = await client.fetch_account_snapshot()

    all_bank_ids = list(account.bank.keys())
    all_inv_ids = list(account.inventory.keys())

    items_to_lookup = list(set(all_bank_ids + all_inv_ids))
    print(f"Total distinct items in bank/inv: {len(items_to_lookup)}")

    # Chunk into 200 items
    all_details = []
    for i in range(0, len(items_to_lookup), 200):
        chunk = items_to_lookup[i:i + 200]
        details = await client.get_items(chunk)
        all_details.extend(details)

    print("=== BANK & INVENTORY CONTAINERS / LEGENDARY ITEMS ===")
    for item in all_details:
        name = item.get("name", "")
        i_type = item.get("type", "")
        item_id = item.get("id")
        loc = "Bank" if item_id in account.bank else "Inventory"
        qty = account.bank.get(item_id, 0) or account.inventory.get(item_id, 0)
        if any(k in name.lower() for k in ["starter", "kit", "moot", "energizer", "gift", "box", "chest", "legendary", "weapon", "mace", "tribute"]):
            print(f"[{loc}] {name} (ID: {item_id}) x{qty} [Type: {i_type}]")


if __name__ == "__main__":
    asyncio.run(check())
