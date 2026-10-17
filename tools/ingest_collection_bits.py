#!/usr/bin/env python3
"""Ingests bit-level precursor achievement objectives from GW2 API and GW2 Wiki.

Fetches `/v2/achievements`, `/v2/items`, and GW2 Wiki parsed HTML tables for:
- Twilight / Dusk (30704 / 29185): 2420 (T1), 2184 (T2), 2183 (T3)
- Sunrise / Dawn (30703 / 29169): 2253 (T1), 2278 (T2), 2630 (T3)
- Bolt / Zap (30699 / 29181): 2355 (T1), 2356 (T2), 2480 (T3)

Emits `ontology/instances/shared/precursor_collection_bits.ttl`.
"""

from __future__ import annotations

import base64
import html as html_mod
import json
from pathlib import Path
import re
import ssl
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_TTL = (
    REPO_ROOT
    / "ontology"
    / "instances"
    / "shared"
    / "precursor_collection_bits.ttl"
)

COLLECTION_TARGETS: List[Dict[str, Any]] = [
    {
        "achievement_id": 2420,
        "wiki_page": "Twilight_I:_The_Experimental_Nightsword",
        "tier": 1,
        "expected_bits": 15,
        "stage_ids": [30704, 29185],
    },
    {
        "achievement_id": 2184,
        "wiki_page": "Twilight_II:_The_Perfected_Nightsword",
        "tier": 2,
        "expected_bits": 16,
        "stage_ids": [30704, 29185],
    },
    {
        "achievement_id": 2183,
        "wiki_page": "Twilight_III:_Dusk",
        "tier": 3,
        "expected_bits": 30,
        "stage_ids": [30704, 29185],
    },
    {
        "achievement_id": 2253,
        "wiki_page": "Sunrise_I:_The_Experimental_Daysword",
        "tier": 1,
        "expected_bits": 15,
        "stage_ids": [30703, 29169],
    },
    {
        "achievement_id": 2278,
        "wiki_page": "Sunrise_II:_The_Perfected_Daysword",
        "tier": 2,
        "expected_bits": 16,
        "stage_ids": [30703, 29169],
    },
    {
        "achievement_id": 2630,
        "wiki_page": "Sunrise_III:_Dawn",
        "tier": 3,
        "expected_bits": 35,
        "stage_ids": [30703, 29169],
    },
    {
        "achievement_id": 2355,
        "wiki_page": "Bolt_I:_The_Experimental_Sword",
        "tier": 1,
        "expected_bits": 21,
        "stage_ids": [30699, 29181],
    },
    {
        "achievement_id": 2356,
        "wiki_page": "Bolt_II:_The_Perfected_Sword",
        "tier": 2,
        "expected_bits": 13,
        "stage_ids": [30699, 29181],
    },
    {
        "achievement_id": 2480,
        "wiki_page": "Bolt_III:_Zap",
        "tier": 3,
        "expected_bits": 30,
        "stage_ids": [30699, 29181],
    },
]


def _fetch_json(url: str) -> Any:
  """Fetches JSON from a URL with a custom User-Agent and fallback SSL context."""
  req = urllib.request.Request(
      url,
      headers={
          "User-Agent": (
              "ProjectPriory/1.0 (https://priory.gw2/def/; ontology-ingestor)"
          )
      },
  )
  try:
    with urllib.request.urlopen(req, timeout=30) as resp:
      return json.loads(resp.read().decode("utf-8"))
  except Exception:
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
      return json.loads(resp.read().decode("utf-8"))


def encode_gamelink(gtype: str, gid: str) -> str:
  """Encodes a GW2 Wiki gamelink span (data-type, data-id) into a `[&...]` chat link."""
  type_map = {
      "item": 2,
      "text": 3,
      "map": 4,
      "skill": 6,
      "trait": 7,
      "recipe": 9,
      "skin": 10,
      "outfit": 11,
  }
  n = type_map.get(gtype.strip().lower(), 0)
  if not n:
    return ""
  try:
    i = int(gid)
  except ValueError:
    return ""
  b: List[int] = []
  while i > 0:
    b.append(i & 255)
    i >>= 8
  while len(b) < 4 or len(b) % 2 != 0:
    b.append(0)
  if n == 2:
    b.insert(0, 1)
  b.insert(0, n)
  return "[&" + base64.b64encode(bytes(b)).decode("ascii") + "]"


def clean_html_cell(cell_html: str) -> str:
  """Strips inline `<script>` tags, converts gamelink spans to `[&...]` codes, and extracts clean text."""

  def _repl_gamelink(match: re.Match[str]) -> str:
    attrs = match.group(1)
    tm = re.search(r'data-type="([^"]+)"', attrs)
    im = re.search(r'data-id="(\d+)"', attrs)
    if tm and im:
      return encode_gamelink(tm.group(1), im.group(1))
    return ""

  s = re.sub(
      r'<span[^>]*class="gamelink"([^>]*)></span>', _repl_gamelink, cell_html
  )
  s = re.sub(r"<script[^>]*>.*?</script>", "", s, flags=re.S | re.I)
  s = re.sub(r"<style[^>]*>.*?</style>", "", s, flags=re.S | re.I)
  s = re.sub(r"<(br|/?div|/?li|/?p|/?ul|/?dl|/?dd)[^>]*>", " ", s, flags=re.I)
  s = re.sub(r"<[^>]+>", "", s)
  s = html_mod.unescape(s)
  s = re.sub(r"\s+", " ", s).strip()
  s = re.sub(r"\s*—\s*$", "", s).strip()
  return s


def parse_wiki_collection_table(html_text: str) -> List[Dict[str, str]]:
  """Parses the GW2 Wiki rendered HTML collection table into a list of row dicts."""
  tables = re.findall(r"<table[^>]*>.*?</table>", html_text, flags=re.S | re.I)
  target_table: Optional[str] = None
  for tbl in tables:
    if "Collectible" in tbl:
      target_table = tbl
      break
  if not target_table:
    raise ValueError(
        "Could not find Collectible table in Wiki page HTML output."
    )

  rows = re.findall(r"<tr[^>]*>.*?</tr>", target_table, flags=re.S | re.I)
  if not rows:
    return []

  headers = [
      clean_html_cell(th)
      for th in re.findall(r"<th[^>]*>(.*?)</th>", rows[0], flags=re.S | re.I)
  ]

  parsed_rows: List[Dict[str, str]] = []
  for row_html in rows[1:]:
    cells = [
        clean_html_cell(td)
        for td in re.findall(r"<td[^>]*>(.*?)</td>", row_html, flags=re.S | re.I)
    ]
    if not cells:
      continue
    row_dict: Dict[str, str] = {}
    for col_idx, col_name in enumerate(headers):
      key = col_name.strip() or "Index"
      if col_idx < len(cells):
        row_dict[key] = cells[col_idx]
    parsed_rows.append(row_dict)

  return parsed_rows


def _escape_ttl(val: str) -> str:
  """Escapes a string for Turtle double-quoted literals."""
  return (
      val.replace("\\", "\\\\")
      .replace('"', '\\"')
      .replace("\n", " ")
      .replace("\r", " ")
  )


def fetch_achievements(ach_ids: List[int]) -> Dict[int, Dict[str, Any]]:
  """Fetches achievement records from `/v2/achievements`."""
  ids_param = ",".join(str(i) for i in ach_ids)
  url = f"https://api.guildwars2.com/v2/achievements?ids={ids_param}"
  data = _fetch_json(url)
  return {int(a["id"]): a for a in data}


def fetch_items(item_ids: List[int]) -> Dict[int, Dict[str, Any]]:
  """Fetches item records in batches of 200 from `/v2/items`."""
  unique_ids = sorted(set(i for i in item_ids if i > 0))
  items_map: Dict[int, Dict[str, Any]] = {}
  batch_size = 180
  for i in range(0, len(unique_ids), batch_size):
    batch = unique_ids[i : i + batch_size]
    ids_param = ",".join(str(x) for x in batch)
    url = f"https://api.guildwars2.com/v2/items?ids={ids_param}"
    try:
      data = _fetch_json(url)
      for item in data:
        items_map[int(item["id"])] = item
    except Exception:
      pass
  return items_map


def fetch_wiki_page_html(page_title: str) -> str:
  """Fetches rendered HTML of a GW2 Wiki page via MediaWiki `action=parse`."""
  encoded_page = urllib.parse.quote(page_title, safe=":_")
  url = f"https://wiki.guildwars2.com/api.php?action=parse&page={encoded_page}&prop=text&format=json"
  data = _fetch_json(url)
  return str(data["parse"]["text"]["*"])


def generate_collection_bits_ttl() -> Tuple[str, int]:
  """Fetches API & Wiki data for all target collections and returns (ttl_content, total_bits)."""
  ach_ids = [int(t["achievement_id"]) for t in COLLECTION_TARGETS]
  ach_map = fetch_achievements(ach_ids)

  all_bit_item_ids: List[int] = []
  for ach in ach_map.values():
    for bit in ach.get("bits", []):
      if bit.get("id") is not None:
        all_bit_item_ids.append(int(bit["id"]))

  items_map = fetch_items(all_bit_item_ids)

  lines: List[str] = [
      "@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
      "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
      "@prefix owl: <http://www.w3.org/2002/07/owl#> .",
      "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
      "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .",
      "@prefix priory: <https://priory.gw2/def/> .",
      "",
      (
          "# =============================================================================="
      ),
      (
          "# Bit-Level Precursor Collection Objectives (Twilight/Dusk, Sunrise/Dawn, Bolt/Zap)"
      ),
      (
          "# Generated by tools/ingest_collection_bits.py from live GW2 API & GW2 Wiki"
      ),
      (
          "# =============================================================================="
      ),
      "",
  ]

  total_bits = 0

  for target in COLLECTION_TARGETS:
    ach_id = int(target["achievement_id"])
    wiki_page = str(target["wiki_page"])
    tier = int(target["tier"])
    expected_bits = int(target["expected_bits"])
    stage_ids: List[int] = list(target["stage_ids"])

    ach_data = ach_map.get(ach_id, {})
    api_bits: List[Dict[str, Any]] = ach_data.get("bits", [])
    wiki_html = fetch_wiki_page_html(wiki_page)
    wiki_rows = parse_wiki_collection_table(wiki_html)

    num_bits = max(len(api_bits), len(wiki_rows))
    if num_bits != expected_bits:
      raise RuntimeError(
          f"Bit count mismatch for achievement {ach_id} ({wiki_page}): "
          f"got {num_bits} (api={len(api_bits)}, wiki={len(wiki_rows)}), expected {expected_bits}"
      )

    lines.append(
        "# ------------------------------------------------------------------------------"
    )
    lines.append(
        f"# Achievement {ach_id}: {wiki_page.replace('_', ' ')} ({num_bits} bits)"
    )
    lines.append(
        "# ------------------------------------------------------------------------------"
    )
    lines.append("")

    bit_curies: List[str] = []

    for bit_idx in range(num_bits):
      api_bit = api_bits[bit_idx] if bit_idx < len(api_bits) else {}
      wiki_row = wiki_rows[bit_idx] if bit_idx < len(wiki_rows) else {}

      bit_item_id: Optional[int] = (
          int(api_bit["id"]) if api_bit.get("id") is not None else None
      )
      item_info = items_map.get(bit_item_id, {}) if bit_item_id else {}

      collectible_name = wiki_row.get("Collectible", "").strip()
      if not collectible_name:
        collectible_name = str(
            item_info.get("name") or f"Collection Bit {ach_id} #{bit_idx}"
        ).strip()

      subtype = wiki_row.get("Subtype", "").strip()
      if not subtype:
        subtype = str(
            item_info.get("type") or api_bit.get("type") or "Trophy"
        ).strip()

      zone = wiki_row.get("Zone", "").strip()
      if zone in ("—", "-", "N/A"):
        zone = ""

      waypoint = wiki_row.get("Waypoint", "").strip()
      if waypoint in ("—", "-", "N/A"):
        waypoint = ""

      hint = wiki_row.get("Notes", "").strip()
      if not hint:
        hint = str(
            item_info.get("description") or api_bit.get("text") or ""
        ).strip()

      bit_curie = f"priory:CollectionBit_{ach_id}_{bit_idx}"
      bit_curies.append(bit_curie)

      props: List[str] = [
          f'    rdfs:label "{_escape_ttl(collectible_name)}"@en',
          f"    priory:forAchievementId {ach_id}",
          f"    priory:bitIndex {bit_idx}",
      ]
      if bit_item_id is not None:
        props.append(f"    priory:bitItemId {bit_item_id}")
      if subtype:
        props.append(f'    priory:bitSubtype "{_escape_ttl(subtype)}"')
      if zone:
        props.append(f'    priory:zoneName "{_escape_ttl(zone)}"')
      if waypoint:
        props.append(f'    priory:waypointName "{_escape_ttl(waypoint)}"')
      props.append(f'    priory:acquisitionHint "{_escape_ttl(hint)}"')

      lines.append(
          f"{bit_curie} a priory:CollectionBitObjective, owl:NamedIndividual ;"
      )
      lines.append(" ;\n".join(props) + " .")
      lines.append("")
      total_bits += 1

    # Link HobbsStage_{id}_T{tier} -> priory:hasCollectionBit -> CollectionBit_{ach_id}_{idx}
    bits_obj_list = ",\n        ".join(bit_curies)
    for sid in stage_ids:
      lines.append(
          f"priory:HobbsStage_{sid}_T{tier} priory:hasCollectionBit {bits_obj_list} ."
      )
      lines.append("")

  return "\n".join(lines), total_bits


def main() -> None:
  ttl_content, total_bits = generate_collection_bits_ttl()
  OUTPUT_TTL.parent.mkdir(parents=True, exist_ok=True)
  OUTPUT_TTL.write_text(ttl_content, encoding="utf-8")
  print(f"Wrote {total_bits} collection bit objectives to {OUTPUT_TTL}")


if __name__ == "__main__":
  main()
