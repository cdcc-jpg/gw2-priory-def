"""Script to count and categorize all RDF triples across namespaces in Project Priory."""

import sys
from pathlib import Path
from collections import defaultdict

DEF_REPO = Path(__file__).parent.parent
REF_REPO = Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")
sys.path.insert(0, str(DEF_REPO))

from engine.graph_store import PrioryGraphStore


def analyze_namespaces():
    store = PrioryGraphStore(ref_repo_path=REF_REPO, def_repo_path=DEF_REPO)
    triples_loaded = store.load_all()

    print("=" * 75)
    print("🏛️  PROJECT PRIORY — KNOWLEDGE GRAPH NAMESPACE AUDIT")
    print("=" * 75)
    print(f"Total Triples in Graph Store: {len(store.graph):,} triples\n")

    subject_counts = defaultdict(int)
    predicate_counts = defaultdict(int)
    object_counts = defaultdict(int)

    # Namespace prefix lookup
    namespaces = {
        "https://priory.gw2/def/": "priory (OWL 2 Schema / Classes)",
        "https://priory.gw2/ref/": "priory-ref (SKOS Core Schemes)",
        "https://priory.gw2/id/item/": "item (Item Individuals & Instances)",
        "https://priory.gw2/id/recipe/": "recipe (Recipe Individuals & Reified Requirements)",
        "https://priory.gw2/ref/weapon/": "weapon (Weapon Taxonomy)",
        "https://priory.gw2/ref/armor/": "armor (Armor Weights)",
        "https://priory.gw2/ref/slot/": "slot (Equipment Slots)",
        "https://priory.gw2/ref/itemtype/": "itemtype (Item Types)",
        "https://priory.gw2/ref/rarity/": "rarity (Rarity Scheme)",
        "https://priory.gw2/ref/discipline/": "discipline (Crafting Disciplines)",
        "https://priory.gw2/ref/currency/": "currency (Currencies & Tokens)",
        "https://priory.gw2/ref/gamemode/": "gamemode (Game Modes)",
        "http://www.w3.org/2004/02/skos/core#": "skos (W3C SKOS Relations)",
        "http://www.w3.org/2000/01/rdf-schema#": "rdfs (W3C RDFS Schema)",
        "http://www.w3.org/2002/07/owl#": "owl (W3C OWL DL)",
        "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf (RDF Syntax)"
    }

    def get_ns_label(uri):
        uri_str = str(uri)
        for ns_uri, label in namespaces.items():
            if uri_str.startswith(ns_uri):
                return label
        return "other (Literals / External URIs)"

    for s, p, o in store.graph:
        subject_counts[get_ns_label(s)] += 1
        predicate_counts[get_ns_label(p)] += 1
        object_counts[get_ns_label(o)] += 1

    print("📊 1. TRIPLES BY SUBJECT NAMESPACE (Entities being described):")
    print("─" * 75)
    for label, count in sorted(subject_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(store.graph)) * 100
        print(f"  • {label:<50} : {count:>5} triples ({pct:>5.1f}%)")

    print("\n🔍 2. TRIPLES BY PREDICATE NAMESPACE (Relations & Properties used):")
    print("─" * 75)
    for label, count in sorted(predicate_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(store.graph)) * 100
        print(f"  • {label:<50} : {count:>5} triples ({pct:>5.1f}%)")

    print("\n📦 3. TRIPLES BY OBJECT NAMESPACE (Target entities, taxonomies & literals):")
    print("─" * 75)
    for label, count in sorted(object_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(store.graph)) * 100
        print(f"  • {label:<50} : {count:>5} triples ({pct:>5.1f}%)")

    print("=" * 75)


if __name__ == "__main__":
    analyze_namespaces()
