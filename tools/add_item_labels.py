#!/usr/bin/env python3
"""Fetches missing rdfs:label annotations for GW2 item:<id> entities from the public GW2 API
and inserts them inline directly next to each item:<id> subject declaration.

Usage:
    # Hydrate a single file:
    python tools/add_item_labels.py ontology/instances/shared/precursor_taxonomy.ttl

    # Hydrate multiple files or glob patterns:
    python tools/add_item_labels.py ontology/instances/**/*.ttl
"""

from __future__ import annotations

import glob
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _create_ssl_context() -> ssl.SSLContext:
    """Configures an SSL context using certifi if available (handles macOS Python cert store)."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx


def fetch_gw2_item_names(item_ids: list[str]) -> dict[str, str]:
    """Queries the official GW2 v2/items endpoint in batches of 200 IDs."""
    id_to_name: dict[str, str] = {}
    if not item_ids:
        return id_to_name

    ssl_context = _create_ssl_context()
    for idx in range(0, len(item_ids), 200):
        chunk = item_ids[idx : idx + 200]
        url = f"https://api.guildwars2.com/v2/items?ids={','.join(chunk)}&lang=en"
        req = urllib.request.Request(url, headers={"User-Agent": "PrioryOntologyTools/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15, context=ssl_context) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for entry in data:
                    item_id_str = str(entry.get("id"))
                    name = entry.get("name", "").strip()
                    if name:
                        safe_name = name.replace("\\", "\\\\").replace('"', '\\"')
                        id_to_name[item_id_str] = safe_name
        except urllib.error.HTTPError as err:
            print(f"Warning: GW2 API returned HTTP {err.code} for chunk: {chunk[:5]}... ({err.reason})")
        except Exception as err:
            print(f"Warning: Failed to fetch chunk from GW2 API: {err}")

    return id_to_name


def enrich_ttl_file(ttl_path: Path) -> None:
    if not ttl_path.is_file():
        print(f"Skipping non-file: {ttl_path}")
        return

    text = ttl_path.read_text(encoding="utf-8")

    # Remove any legacy bottom-appended block if present from an earlier run
    text = re.sub(
        r"\n*# --- Auto-hydrated GW2 API Item Labels ---(?:\nitem:\d+\s+rdfs:label\s+\"[^\"]*\"@en\s*\.)+\s*$",
        "\n",
        text,
    )

    # Match top-level Turtle subject statements for item:<id> or <https://priory.gw2/id/item/<id>>
    # Captures:
    #   group(1): leading subject token + trailing horizontal whitespace (e.g. "item:76158 ")
    #   group(2): numeric GW2 item ID (e.g. "76158")
    #   group(3): remainder of the Turtle statement up to its terminating period
    stmt_pattern = re.compile(
        r"^([ \t]*(?:item:|<https://priory\.gw2/id/item/)(\d+)>?[ \t]+)"
        r"([^#.\n]*\.(?:[ \t]*#[^\n]*)?|[^.\n]*(?:\n[ \t]+[^.\n]*)*\.(?:[ \t]*#[^\n]*)?)",
        flags=re.MULTILINE,
    )

    matches = list(stmt_pattern.finditer(text))
    if not matches:
        print(f"No item subject declarations found in {ttl_path.name}")
        return

    unlabeled_ids: list[str] = []
    for m in matches:
        item_id = m.group(2)
        body = m.group(3)
        if not re.search(r"(?:rdfs:label|skos:prefLabel)\s+[\"']", body):
            if item_id not in unlabeled_ids:
                unlabeled_ids.append(item_id)

    if not unlabeled_ids:
        total_subjects = len({m.group(2) for m in matches})
        print(f"✓ All {total_subjects} item subject IDs in {ttl_path.name} already have inline labels.")
        return

    print(f"Fetching {len(unlabeled_ids)} missing item label(s) for {ttl_path.name} from GW2 API...")
    id_to_name = fetch_gw2_item_names(sorted(unlabeled_ids, key=int))

    if not id_to_name:
        print(f"No names returned from API for missing IDs in {ttl_path.name}.")
        return

    added_count = 0

    def _inject_inline_label(match: re.Match[str]) -> str:
        nonlocal added_count
        subject_prefix = match.group(1)
        item_id = match.group(2)
        body = match.group(3)

        # Skip if this statement block already has a label
        if re.search(r"(?:rdfs:label|skos:prefLabel)\s+[\"']", body):
            return match.group(0)

        name = id_to_name.get(item_id)
        if not name:
            return match.group(0)

        added_count += 1
        return f'{subject_prefix}rdfs:label "{name}"@en ; {body}'

    updated_text = stmt_pattern.sub(_inject_inline_label, text)
    ttl_path.write_text(updated_text, encoding="utf-8")
    print(f"✓ Successfully inserted {added_count} inline label(s) next to their IDs in {ttl_path.name}!")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        default_target = Path("ontology/instances/shared/precursor_taxonomy.ttl")
        if default_target.exists():
            print(f"No arguments passed. Running on default: {default_target}\n")
            enrich_ttl_file(default_target.resolve())
        else:
            sys.exit(1)
        return

    targets: list[Path] = []
    for pattern in sys.argv[1:]:
        matches = glob.glob(pattern, recursive=True)
        if matches:
            targets.extend([Path(m).resolve() for m in matches])
        else:
            p = Path(pattern).resolve()
            if p.exists():
                targets.append(p)
            else:
                print(f"Target path not found: {pattern}")

    for target in targets:
        enrich_ttl_file(target)


if __name__ == "__main__":
    main()
