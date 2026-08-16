"""Project Priory — Automated Catalog Ingestion CLI Runner.

Orchestrates bulk data harvesting from the official GW2 REST API and
Semantic MediaWiki, translating game data into validated OWL/RDF Turtle partitions.
"""

import argparse
import asyncio
import sys
from pathlib import Path

DEF_REPO = Path(__file__).parent.parent
if str(DEF_REPO) not in sys.path:
    sys.path.insert(0, str(DEF_REPO))

import rdflib
import pyshacl
from ingestion.gw2_api import GW2ApiClient
from ingestion.smw_client import GW2SMWClient

DEF_REPO = Path(__file__).parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")
INSTANCES_DIR = DEF_REPO / "ontology" / "instances"


async def ingest_legendaries():
    """Phase 1: Ingests all Legendary items, armor, trinkets, and weapons."""
    print("=" * 70)
    print("🏛️  PROJECT PRIORY — PHASE 1: BULK LEGENDARY INGESTION")
    print("=" * 70)

    smw_client = GW2SMWClient()
    print("[+] Querying GW2 Semantic MediaWiki for all Legendary items...")
    legendaries = await smw_client.get_all_legendaries()
    print(f"[+] Discovered {len(legendaries)} Legendary entities on official Wiki.")

    out_dir = INSTANCES_DIR / "legendaries"
    out_dir.mkdir(parents=True, exist_ok=True)

    master_legendary_graph = rdflib.Graph()

    for leg in legendaries:
        g = smw_client.build_rdf_item_graph(
            item_id=leg["item_id"],
            item_name=leg["label"],
            rarity_str="Legendary",
            chat_code=leg["chat_code"],
            weapon_type=leg["weapon_type"],
            armor_weight=leg["armor_weight"],
            equipment_slot=leg["equipment_slot"],
            item_type=leg["item_type"],
            wiki_url=leg["wiki_url"]
        )
        master_legendary_graph += g

    out_file = out_dir / "all_legendary_items.ttl"
    master_legendary_graph.serialize(destination=out_file, format="turtle")
    print(f"[+] Successfully wrote {len(master_legendary_graph)} triples to {out_file}")

    # Validate against SHACL
    print("[+] Running SHACL integrity validation...")
    shacl_graph = rdflib.Graph()
    shacl_graph.parse(DEF_REPO / "ontology" / "priory_shacl.ttl", format="turtle")

    vocab_graph = rdflib.Graph()
    for ttl in (REF_REPO / "vocab").glob("*.ttl"):
        vocab_graph.parse(ttl, format="turtle")

    combined = master_legendary_graph + vocab_graph
    conforms, _, results_text = pyshacl.validate(
        combined,
        shacl_graph=shacl_graph,
        inference="rdfs",
        abort_on_first=False
    )

    if conforms:
        print("✅ SHACL Validation Passed with 100% data integrity!")
    else:
        print(f"⚠️ SHACL Validation Warnings:\n{results_text}")


def main():
    parser = argparse.ArgumentParser(description="Priory Catalog Ingestion Tool")
    parser.add_argument(
        "--target",
        choices=["legendaries", "all"],
        default="legendaries",
        help="Target catalog partition to ingest"
    )
    args = parser.parse_args()

    if args.target in ["legendaries", "all"]:
        asyncio.run(ingest_legendaries())


if __name__ == "__main__":
    main()
