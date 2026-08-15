#!/usr/bin/env python3
"""Interactive demonstration of Project Priory's Semantic Discovery Layer.

Run:
    python3 demo_semantic_discovery.py
"""

from engine.graph_store import PrioryGraphStore
from engine.semantic_query import SemanticQueryService


def main():
    print("=" * 70)
    print(" 🏛️  PROJECT PRIORY — SEMANTIC DISCOVERY & TAXONOMY DEMO")
    print("=" * 70)

    store = PrioryGraphStore()
    triples_loaded = store.load_all()
    print(f"\n[+] Loaded {triples_loaded} triples into RDF Knowledge Graph (OWL + SKOS + ABox).\n")

    service = SemanticQueryService(store)

    # -------------------------------------------------------------------------
    # DEMO 1: Taxonomic Subsumption Reasoning (SKOS Hierarchy)
    # -------------------------------------------------------------------------
    print("─" * 70)
    print("1. TAXONOMIC REASONING (SKOS Subsumption: Two-Handed Weapons)")
    print("─" * 70)
    print("Querying for: broad_weapon_type='TwoHandedWeapon', rarity='Legendary'...")
    legendaries = service.find_items_by_taxonomy(broad_weapon_type="TwoHandedWeapon", rarity_tier="Legendary")
    for item in legendaries:
        print(f"  👉 Found: {item['label']} (GW2 ID: {item['gw2Id']}) | Chat Code: {item.get('chatCode')} | Type: Greatsword")

    print("\nQuerying for: broad_weapon_type='TwoHandedWeapon', rarity='Exotic'...")
    exotics = service.find_items_by_taxonomy(broad_weapon_type="TwoHandedWeapon", rarity_tier="Exotic")
    for item in exotics:
        print(f"  👉 Found Precursor: {item['label']} (GW2 ID: {item['gw2Id']}) | Chat Code: {item.get('chatCode')}")

    # -------------------------------------------------------------------------
    # DEMO 2: Polymorphic Acquisition Discovery
    # -------------------------------------------------------------------------
    print("\n" + "─" * 70)
    print("2. POLYMORPHIC ACQUISITION DISCOVERY (Alternative Item Sources)")
    print("─" * 70)
    print("Discovering all known ways to obtain 'Mystic Clover' (ID: 19675)...")
    clover_data = service.discover_acquisition_paths(19675)
    
    paths = clover_data["acquisition_paths"]
    print("  🔹 Vendor Barters / Exchanges:")
    for ve in paths["vendor_exchanges"]:
        tg = f" (Constraint: {ve['time_gate']})" if ve["time_gate"] else ""
        print(f"     • {ve['required_quantity']}x {ve['currency_label']}{tg}")

    print("  🔹 Gameplay Reward Tracks:")
    for rt in paths["reward_tracks"]:
        print(f"     • Mode: {rt['game_mode']}")

    # -------------------------------------------------------------------------
    # DEMO 3: Identity & Chat Link Code Resolution
    # -------------------------------------------------------------------------
    print("\n" + "─" * 70)
    print("3. IDENTITY & CHAT LINK CODE RECONCILIATION")
    print("─" * 70)
    chat_code = "[&AgErZgAA]"
    print(f"Resolving in-game chat link code '{chat_code}' to semantic entity...")
    resolved = service.resolve_entity_by_text(chat_code)
    for r in resolved:
        print(f"  👉 Resolved to Canonical Item: {r['label']} (GW2 ID: {r['gw2Id']})")

    # -------------------------------------------------------------------------
    # DEMO 4: Self-Describing Knowledge Subgraph for LLM Prompt Grounding
    # -------------------------------------------------------------------------
    print("\n" + "─" * 70)
    print("4. SELF-DESCRIBING KNOWLEDGE SUBGRAPH (Grounding for LLMs)")
    print("─" * 70)
    print("Extracting structured semantic context for 'Twilight' (ID: 30699):\n")
    llm_context = service.get_item_semantic_context_for_llm(30699)
    print(llm_context)

    print("\n" + "=" * 70)
    print(" ✅  DEMO COMPLETE: Zero hardcoded joins, pure semantic reasoning!")
    print("=" * 70)


if __name__ == "__main__":
    main()
