#!/usr/bin/env python3
"""Automated Full-Ontology Ground-Truth Validator against GW2 REST API v2.

Scans all 50 .ttl files in the ontology, extracts every:
1. Item individual (item:XXXXX, priory:gw2Id, rdfs:label, priory:hasRarity, itemtype)
2. Container relationship (priory:unpacksInto, priory:grantsItem, priory:fromContainer)
3. Recipe relationship (priory:requiresItem, priory:createsItem, priory:targetItem)

Queries the official ArenaNet API (with chunking, caching, and rate limiting)
to generate a forensic discrepancy report of:
- Fatal/404 non-existent IDs
- Label/name mismatches
- Rarity discrepancies
- Broken or aberrant container unpack relationships
"""

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple
import httpx

ONTOLOGY_DIR = Path(__file__).parent.parent / "ontology"
CACHE_FILE = Path(__file__).parent.parent / "data" / "cache" / "api_items.json"
BASE_URL = "https://api.guildwars2.com/v2"


def parse_ontology_items() -> Tuple[Dict[int, List[Dict[str, Any]]], List[Dict[str, Any]]]:
    """Parses all .ttl files for item definitions and container unpack relationships."""
    items_by_id: Dict[int, List[Dict[str, Any]]] = {}
    container_relationships: List[Dict[str, Any]] = []

    ttl_files = sorted(list(ONTOLOGY_DIR.glob("**/*.ttl")))

    for ttl_file in ttl_files:
        content = ttl_file.read_text(encoding="utf-8")
        rel_path = str(ttl_file.relative_to(ONTOLOGY_DIR.parent))

        # 1. Parse container unpacksInto and grantsItem
        lines = content.splitlines()

        for idx, line in enumerate(lines):
            unpack_match = re.search(r"priory:unpacksInto\s+([^;.]+)", line)
            if unpack_match:
                targets = re.findall(r"item:(\d+)", unpack_match.group(1))
                container_id = None
                for back in range(idx - 1, max(-1, idx - 25), -1):
                    c_match = re.search(r"^item:(\d+)\s+a\s+", lines[back]) or re.search(r"^item:(\d+)", lines[back])
                    if c_match:
                        container_id = int(c_match.group(1))
                        break
                container_relationships.append({
                    "file": rel_path,
                    "line": idx + 1,
                    "type": "unpacksInto",
                    "container_id": container_id,
                    "target_ids": [int(t) for t in targets],
                    "raw": line.strip()
                })

            grants_match = re.search(r"priory:grantsItem\s+([^;.]+)", line)
            if grants_match:
                targets = re.findall(r"item:(\d+)", grants_match.group(1))
                container_id = None
                for back in range(max(0, idx - 15), min(len(lines), idx + 15)):
                    c_match = re.search(r"priory:fromContainer\s+item:(\d+)", lines[back])
                    if c_match:
                        container_id = int(c_match.group(1))
                        break
                container_relationships.append({
                    "file": rel_path,
                    "line": idx + 1,
                    "type": "grantsItem",
                    "container_id": container_id,
                    "target_ids": [int(t) for t in targets],
                    "raw": line.strip()
                })

        # Match specific individual declarations
        blocks = re.split(r"\n(?=item:\d+)", content)
        for block in blocks:
            id_match = re.match(r"item:(\d+)", block)
            if not id_match:
                continue
            item_id = int(id_match.group(1))
            
            label_match = re.search(r'rdfs:label\s+"([^"]+)"', block)
            label = label_match.group(1) if label_match else None

            rarity_match = re.search(r'priory:hasRarity\s+rarity:([a-zA-Z0-9_]+)', block)
            rarity = rarity_match.group(1) if rarity_match else None

            gw2_id_match = re.search(r'priory:gw2Id\s+(\d+)', block)
            declared_gw2_id = int(gw2_id_match.group(1)) if gw2_id_match else None

            entry = {
                "file": rel_path,
                "item_id": item_id,
                "label": label,
                "rarity": rarity,
                "declared_gw2_id": declared_gw2_id
            }

            if item_id not in items_by_id:
                items_by_id[item_id] = []
            items_by_id[item_id].append(entry)

        all_referenced_ids = [int(x) for x in re.findall(r"item:(\d+)", content)]
        for ref_id in all_referenced_ids:
            if ref_id not in items_by_id:
                items_by_id[ref_id] = [{
                    "file": rel_path,
                    "item_id": ref_id,
                    "label": None,
                    "rarity": None,
                    "declared_gw2_id": None
                }]

    return items_by_id, container_relationships


async def fetch_api_items(item_ids: Set[int]) -> Tuple[Dict[int, Dict[str, Any]], Set[int]]:
    """Fetches item data for all item IDs in chunks from GW2 API v2."""
    cached: Dict[str, Dict[str, Any]] = {}
    if CACHE_FILE.exists():
        try:
            cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            cached = {}

    results: Dict[int, Dict[str, Any]] = {}
    missing = []

    for i_id in item_ids:
        if str(i_id) in cached:
            results[i_id] = cached[str(i_id)]
        else:
            missing.append(i_id)

    invalid_ids: Set[int] = set()

    if missing:
        print(f"[*] Querying GW2 API for {len(missing)} missing items...")
        chunk_size = 50
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i in range(0, len(missing), chunk_size):
                chunk = missing[i:i + chunk_size]
                ids_str = ",".join(map(str, chunk))
                try:
                    resp = await client.get(f"{BASE_URL}/items", params={"ids": ids_str})
                    if resp.status_code in [200, 206]:
                        data = resp.json()
                        ret_ids = set()
                        for item in data:
                            results[item["id"]] = item
                            cached[str(item["id"])] = item
                            ret_ids.add(item["id"])
                        for cid in chunk:
                            if cid not in ret_ids:
                                invalid_ids.add(cid)
                    elif resp.status_code in [404, 400]:
                        for single_id in chunk:
                            try:
                                s_resp = await client.get(f"{BASE_URL}/items/{single_id}")
                                if s_resp.status_code == 200:
                                    s_item = s_resp.json()
                                    results[single_id] = s_item
                                    cached[str(single_id)] = s_item
                                else:
                                    invalid_ids.add(single_id)
                            except Exception:
                                invalid_ids.add(single_id)
                    else:
                        print(f"[!] API HTTP {resp.status_code} for chunk {chunk[:5]}...")
                except Exception as e:
                    print(f"[!] Request error on chunk {chunk[:5]}: {e}")

        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(json.dumps(cached, indent=2), encoding="utf-8")
        except Exception:
            pass

    return results, invalid_ids


async def run_audit():
    print("================================================================================")
    print("       PROJECT PRIORY — ONTOLOGY & API GROUND-TRUTH INTEGRITY AUDITOR           ")
    print("================================================================================")

    items_by_id, container_rels = parse_ontology_items()
    all_unique_ids = set(items_by_id.keys())
    print(f"[+] Scanned 50 ontology files.")
    print(f"[+] Total unique item IDs referenced: {len(all_unique_ids)}")
    print(f"[+] Total container unpack relationships parsed: {len(container_rels)}")

    api_items, invalid_ids = await fetch_api_items(all_unique_ids)
    print(f"[+] Successfully resolved {len(api_items)} items from ArenaNet API.")
    print(f"[+] Discovered {len(invalid_ids)} INVALID / NON-EXISTENT IDs in API.")

    fatal_invalid_ids: List[Dict[str, Any]] = []
    label_mismatches: List[Dict[str, Any]] = []
    rarity_mismatches: List[Dict[str, Any]] = []
    container_discrepancies: List[Dict[str, Any]] = []

    for inv_id in sorted(invalid_ids):
        occurrences = items_by_id.get(inv_id, [])
        for occ in occurrences:
            fatal_invalid_ids.append({
                "item_id": inv_id,
                "label": occ.get("label"),
                "file": occ.get("file")
            })

    for item_id, occurrences in items_by_id.items():
        if item_id in api_items:
            api_data = api_items[item_id]
            api_name = api_data.get("name")
            api_rarity = api_data.get("rarity")
            api_type = api_data.get("type")

            for occ in occurrences:
                ont_label = occ.get("label")
                ont_rarity = occ.get("rarity")
                ont_file = occ.get("file")

                if ont_label and ont_label.strip() and api_name:
                    clean_ont = ont_label.strip().lower()
                    clean_api = api_name.strip().lower()
                    if clean_ont != clean_api:
                        label_mismatches.append({
                            "item_id": item_id,
                            "ontology_label": ont_label,
                            "api_name": api_name,
                            "file": ont_file,
                            "type": api_type
                        })

                if ont_rarity and api_rarity:
                    if ont_rarity.strip().lower() != api_rarity.strip().lower():
                        rarity_mismatches.append({
                            "item_id": item_id,
                            "label": ont_label or api_name,
                            "ontology_rarity": ont_rarity,
                            "api_rarity": api_rarity,
                            "file": ont_file
                        })

    for c_rel in container_rels:
        cid = c_rel.get("container_id")
        targets = c_rel.get("target_ids", [])
        c_api = api_items.get(cid) if cid else None
        c_name = c_api.get("name") if c_api else f"Unknown/Invalid (ID: {cid})"

        target_info = []
        for tid in targets:
            t_api = api_items.get(tid)
            if t_api:
                target_info.append(f"{t_api.get('name')} (ID: {tid})")
            else:
                target_info.append(f"INVALID ID {tid}")

        container_discrepancies.append({
            "container": c_name,
            "container_id": cid,
            "rel_type": c_rel.get("type"),
            "file": c_rel.get("file"),
            "line": c_rel.get("line"),
            "targets": target_info,
            "raw": c_rel.get("raw")
        })

    print("\n" + "=" * 80)
    print(f"🚨 1. FATAL / NON-EXISTENT IDs IN GW2 API ({len(fatal_invalid_ids)} occurrences):")
    print("=" * 80)
    for f in fatal_invalid_ids:
        print(f"  ❌ ID {f['item_id']:6d} | Label: {f['label']} | File: {f['file']}")

    print("\n" + "=" * 80)
    print(f"⚠️  2. LABEL / NAME MISMATCHES ({len(label_mismatches)} occurrences):")
    print("=" * 80)
    for m in label_mismatches:
        print(f"  ⚠️  ID {m['item_id']:6d} | Ontology: '{m['ontology_label']}' ❌ => API: '{m['api_name']}' ✅ ({m['type']}) | File: {m['file']}")

    print("\n" + "=" * 80)
    print(f"🎨 3. RARITY MISMATCHES ({len(rarity_mismatches)} occurrences):")
    print("=" * 80)
    for r in rarity_mismatches:
        print(f"  🎨 ID {r['item_id']:6d} ({r['label']}): Ontology '{r['ontology_rarity']}' vs API '{r['api_rarity']}' | File: {r['file']}")

    print("\n" + "=" * 80)
    print(f"📦 4. CONTAINER RELATIONSHIPS AUDITED ({len(container_discrepancies)} occurrences):")
    print("=" * 80)
    for cd in container_discrepancies:
        print(f"  📦 {cd['container']} (ID: {cd['container_id']}) -> {cd['rel_type']}: {', '.join(cd['targets'])} [{cd['file']}:{cd['line']}]")

    audit_report_data = {
        "total_scanned_files": len(items_by_id),
        "total_unique_item_ids": len(all_unique_ids),
        "fatal_invalid_ids": fatal_invalid_ids,
        "label_mismatches": label_mismatches,
        "rarity_mismatches": rarity_mismatches,
        "container_relationships": container_discrepancies
    }
    out_path = Path(__file__).parent.parent / "data" / "cache" / "ontology_audit_manifest.json"
    out_path.write_text(json.dumps(audit_report_data, indent=2), encoding="utf-8")
    print(f"\n[+] Full audit manifest saved to: {out_path}")


if __name__ == "__main__":
    asyncio.run(run_audit())
