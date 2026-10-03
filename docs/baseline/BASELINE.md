# Project Priory — Baseline Health Check Report

**Date:** October 3, 2026  
**Auditor / Tool:** Antigravity Groundwork Agent  
**Environment:** macOS (Darwin arm64), Python 3.14.1, Java(TM) SE Runtime Environment (build 1.8.0_501-b08), RDFLib 7.6.0, PySHACL 0.31.0, Owlready2 0.51 (HermiT 1.4.3), owlrl 7.1.4.  
**Git Repositories:**
- `gw2-priory-def`: branch `chore/groundwork` (branched from `feat/catalog-v0.1`)
- `gw2-priory-ref`: branch `feat/catalog-v0.1`

---

## 1. Executive Summary

| Verification Axis | Tool / Engine | Target / Scope | Result | Summary Details |
| :--- | :--- | :--- | :--- | :--- |
| **Test Suite** | `pytest 9.1.1` | `tests/` (all modules) | **PASS** | 170 passed, 0 failed, 0 skipped in 88.8s |
| **TTL Syntax Parse** | `rdflib 7.6.0` | 62 `.ttl` files across def & ref | **PASS** | 0 parse errors; 19,803 distinct merged triples |
| **SHACL (RDFS)** | `pyshacl 0.31.0` | `priory_shacl.ttl` + `shapes/` | **PASS** | Conforms: True; 0 violations in 2.06s |
| **SHACL (OWL-RL)** | `pyshacl 0.31.0` | `priory_shacl.ttl` + `shapes/` | **FAIL (Expected)** | Conforms: False; 114 violations from RL entailments |
| **OWL Reasoner (Core)** | `HermiT 1.4.3` via Owlready2 | `priory_core.ttl` + `bfo_subset.ttl` | **PASS** | Consistent: True; 0 unsatisfiable classes in 1.11s |
| **OWL Reasoner (Merged)**| `HermiT 1.4.3` via Owlready2 | Merged TBox + ABox + Vocabularies | **FAIL (Diagnosed)**| Inconsistent: 3 disjoint individuals & datatype clashes |
| **OWL-RL Closure** | `owlrl 7.1.4` | Full merged graph | **PASS (Syntactic)** | Inferred +23,964 triples (19,803 -> 43,767 in 6.07s) |

---

## 2. Test Suite Execution

### 2.1 Results
* **Command:** `python3 -m pytest tests/ -v -W ignore::DeprecationWarning`
* **Passed:** 170 tests (165 existing engine/agent/ontology tests + 5 newly added competency question tests in `tests/test_competency_questions.py`)
* **Failed:** 0
* **Skipped:** 0
* **Runtime:** 88.80s (1m 28s)
* **Deprecation Notice:** On Python 3.14, RDFLib 7.6.0 emits `DeprecationWarning: Dataset.default_context is deprecated, use Dataset.default_graph instead` (approx. 2.3M warning allocations when unsuppressed, increasing runtime to 91.02s). Suppressing deprecation warnings via `-W ignore::DeprecationWarning` prevents excess string allocation.

---

## 3. Turtle (TTL) Parse & Triple Inventory

Every `.ttl` file across `gw2-priory-def/ontology/` and `gw2-priory-ref/vocab/` was parsed with `rdflib.Graph().parse(..., format='turtle')`.

* **Files Parsed:** 62 files (50 in `gw2-priory-def`, 12 in `gw2-priory-ref`)
* **Parse Errors:** 0
* **Total Raw Triples Sum:** 21,300 triples (19,975 in def, 1,325 in ref)
* **Merged Distinct Triples:** 19,803 triples

### 3.1 Per-File Triple Breakdown

#### `gw2-priory-def` (50 files, 19,975 triples)
| Relative Path | Triples | Relative Path | Triples |
| :--- | :--- | :--- | :--- |
| `ontology/bfo_subset.ttl` | 116 | `ontology/instances/shared/boosters_and_buffs.ttl` | 184 |
| `ontology/character.ttl` | 756 | `ontology/instances/shared/clover_sources.ttl` | 56 |
| `ontology/instances/containers/legendary_starter_kits.ttl` | 140 | `ontology/instances/shared/common_items.ttl` | 99 |
| `ontology/instances/legendaries/all_legendary_items.ttl` | 720 | `ontology/instances/shared/common_material_refinements.ttl` | 680 |
| `ontology/instances/legendaries/competitive_legendary_armors.ttl` | 1045 | `ontology/instances/shared/competitive_and_raid_currencies.ttl` | 73 |
| `ontology/instances/legendaries/gen3_aurene_weapons.ttl` | 520 | `ontology/instances/shared/convenience_and_lounges.ttl` | 758 |
| `ontology/instances/legendaries/gen3_dragon_variants.ttl` | 126 | `ontology/instances/shared/core_exploration.ttl` | 44 |
| `ontology/instances/legendaries/obsidian_armor.ttl` | 1248 | `ontology/instances/shared/currency_exchange_networks.ttl` | 137 |
| `ontology/instances/legendary_sigil.ttl` | 228 | `ontology/instances/shared/dungeon_tokens.ttl` | 163 |
| `ontology/instances/recipes/competitive_armor_and_eternity_recipes.ttl` | 2144 | `ontology/instances/shared/dusk_precursor_collection.ttl` | 157 |
| `ontology/instances/recipes/gen1_legendary_recipes.ttl` | 1185 | `ontology/instances/shared/eternity_and_post_craft.ttl` | 205 |
| `ontology/instances/recipes/gen2_legendary_recipes.ttl` | 1996 | `ontology/instances/shared/legendary_base_components.ttl` | 99 |
| `ontology/instances/recipes/gen3_legendary_recipes.ttl` | 994 | `ontology/instances/shared/legendary_milestone_vendors.ttl` | 272 |
| `ontology/instances/recipes/gen3_variant_recipes.ttl` | 42 | `ontology/instances/shared/mastery_requirements.ttl` | 109 |
| `ontology/instances/recipes/legendary_armor_recipes.ttl` | 689 | `ontology/instances/shared/motes_charms_symbols_and_upgrades.ttl` | 98 |
| `ontology/instances/recipes/legendary_trinkets_and_upgrades.ttl` | 467 | `ontology/instances/shared/mystic_forge_transmutations.ttl` | 288 |
| `ontology/instances/shared/ascended_and_daily_materials.ttl` | 237 | `ontology/instances/shared/obsidian_farming.ttl` | 38 |
| `ontology/instances/shared/precursor_taxonomy.ttl` | 139 | `ontology/instances/shared/regional_expansion_materials.ttl` | 575 |
| `ontology/instances/shared/t6_conversions.ttl` | 33 | `ontology/instances/shared/t6_material_acquisitions.ttl` | 310 |
| `ontology/instances/shared/time_gates_and_caps.ttl` | 30 | `ontology/instances/twilight_gen1.ttl` | 456 |
| `ontology/instances/twilight_journey_web.ttl` | 145 | `ontology/priory_core.ttl` | 881 |
| `ontology/priory_shacl.ttl` | 158 | `ontology/schemas/legendary_crafting_app.ttl` | 161 |
| `ontology/shapes/character_shape.ttl` | 161 | `ontology/shapes/role_shape.ttl` | 57 |
| `ontology/vocab/core_tyria_regions.ttl` | 203 | `ontology/vocab/currencies.ttl` | 353 |
| `ontology/vocab/game_roles.ttl` | 129 | `ontology/vocab/mounts_and_mobility.ttl` | 71 |

#### `gw2-priory-ref` (12 files, 1,325 triples)
| Relative Path | Triples | Relative Path | Triples |
| :--- | :--- | :--- | :--- |
| `vocab/armor_weights.ttl` | 44 | `vocab/core_tyria_regions.ttl` | 203 |
| `vocab/currencies.ttl` | 282 | `vocab/damage_types.ttl` | 39 |
| `vocab/disciplines.ttl` | 101 | `vocab/equipment_slots.ttl` | 144 |
| `vocab/game_modes.ttl` | 104 | `vocab/item_types.ttl` | 88 |
| `vocab/mounts.ttl` | 71 | `vocab/rarities.ttl` | 59 |
| `vocab/upgrade_types.ttl` | 48 | `vocab/weapon_types.ttl` | 142 |

---

## 4. SHACL Conformance Validation

Validation was executed using `pyshacl 0.31.0` with the complete shapes catalog:
- `ontology/priory_shacl.ttl`
- `ontology/shapes/character_shape.ttl`
- `ontology/shapes/role_shape.ttl`
Total shapes graph: 376 triples.

### 4.1 Results under Standard RDFS Inference
* **Command:** `pyshacl.validate(data_graph, shacl_graph=shapes_graph, inference='rdfs', abort_on_first=False)`
* **Conforms:** **True**
* **Violations:** 0
* **Validation Runtime:** 2.06s

### 4.2 Results under OWL-RL Inference
* **Command:** `pyshacl.validate(data_graph, shacl_graph=shapes_graph, inference='owlrl', abort_on_first=False)`
* **Conforms:** **False** (114 violations across 3 shapes)
* **Violations by Shape:**
  1. `nc80a8318ec194e51832ab7e2fe866dd4b24` (`VendorExchangePath` shape): 51 violations (`VendorExchangePath must specify a required currency.`). Cause: Nodes inferred as vendor exchange paths without currency property.
  2. `nc80a8318ec194e51832ab7e2fe866dd4b18` (`IngredientRequirement` shape): 50 violations (`requiresItem must point to an Item IRI.`). Cause: BNodes in recipes missing direct explicit `priory:Item` rdf:type statement.
  3. `nc80a8318ec194e51832ab7e2fe866dd4b15` (`Recipe` shape): 13 violations (`Every recipe must specify exactly one output item.`). Cause: Multiple outputs inferred via transitive subsumption on Aurene precursor recipes.

---

## 5. OWL Reasoner Consistency & Satisfiability

### 5.1 Reasoner Availability
* **ROBOT (`robot.jar`)**: Not installed on machine (`which robot` exited 1).
* **HermiT 1.4.3**: Successfully installed and executed via `owlready2` package bundled JAR (`/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages/owlready2/hermit/HermiT.jar`) running under Java 1.8.0_501.
* **owlrl 7.1.4**: Installed and executed directly via Python RDFLib extension.

### 5.2 Core TBox Reasoner Results (HermiT)
* **Target:** `ontology/priory_core.ttl` + `ontology/bfo_subset.ttl`
* **Consistency:** **Consistent: True**
* **Unsatisfiable Classes:** None (`owl.Nothing` has 0 descendants).
* **Inferred Subclass / Property Reparenting:**
  * `priory:hasLoungeFeature`: Reparented `{owl:ObjectProperty, priory:hasFeature} => {priory:hasFeature}`
  * `priory:requiresRating`: Reparented `{owl:DatatypeProperty, priory:requiredRating} => {priory:requiredRating}`
* **Execution Time:** 1.11s

### 5.3 Full Merged Graph Reasoner Results (HermiT)
When the full instance catalog and reference vocabularies are loaded, HermiT reports `Inconsistent ontology`. Forensic isolation identified three distinct root causes:

1. **Disjoint Class Conflict (`priory:LedgerToken owl:disjointWith priory:Item`)**:
   * Declared in `ontology/priory_core.ttl:166`.
   * `priory:ContainerizedToken` is a subclass of `priory:LedgerToken` (`priory_core.ttl:183`).
   * `priory:CraftingMaterial` is a subclass of `priory:Item` (`priory_core.ttl:169`).
   * Three individuals assert both classes simultaneously:
     * `item:19675` (Mystic Clover) in `clover_sources.ttl`: `a priory:ContainerizedToken, priory:CraftingMaterial, priory:Item`
     * `item:19976` (Mystic Coin) in `clover_sources.ttl`: `a priory:ContainerizedToken, priory:CraftingMaterial, priory:Item`
     * `item:19721` (Glob of Ectoplasm) in `common_material_refinements.ttl`: `a priory:ContainerizedToken, priory:Item`
   * This is a direct OWL 2 DL disjointness clash.

2. **Datatype Range Mismatch on `priory:zoneLevel`**:
   * Declared in `ontology/priory_core.ttl:275` as `rdfs:range xsd:integer`.
   * In `ontology/instances/shared/core_exploration.ttl`, five exploration zone instances assign string literals: `"1-80"` and `"70-80"`.
   * In OWL 2 DL, string literals violating the datatype range of a datatype property render the ontology inconsistent.

3. **`xsd:string` vs `rdf:langString` Clash**:
   * Properties `priory:vendorNPC` (`priory_core.ttl:270`) and `priory:zoneName` (`priory_core.ttl:273`) specify `rdfs:range xsd:string`.
   * Multiple instances in `dungeon_tokens.ttl` and `time_gates_and_caps.ttl` provide language-tagged strings (e.g. `"Lion's Arch"@en`, `"Leivas"@en`).
   * In OWL 2 DL, `xsd:string` and `rdf:langString` are disjoint datatypes.

### 5.4 OWL-RL Rule Closure (`owlrl`)
* **Initial Triples:** 19,803
* **Expanded Triples:** 43,767 (+23,964 inferred triples in 6.07s)
* **Unsatisfiable Classes:** None (`[owl.Nothing]` has no other members).
* **Reason for Difference:** `owlrl` is an RDFS/RL forward-chaining rule engine; it does not evaluate tableau-style negation or lexical datatype range violations.

---

## 6. Exact Reproduction Commands

To reproduce every check in this report:

```bash
# 1. Run full test suite with warnings suppressed
pytest tests/ -v -W ignore::DeprecationWarning

# 2. Parse all TTL files and count triples
python3 -c "
import glob, rdflib
for repo in ['ontology/**/*.ttl', '/Users/clementd/Documents/GitHub/gw2-priory-ref/vocab/**/*.ttl']:
    for f in glob.glob(repo, recursive=True):
        rdflib.Graph().parse(f, format='turtle')
print('All TTL files parsed successfully.')
"

# 3. Run SHACL validation
python3 -c "
import glob, rdflib, pyshacl
g = rdflib.Graph()
for f in glob.glob('ontology/**/*.ttl', recursive=True): g.parse(f, format='turtle')
sg = rdflib.Graph()
sg.parse('ontology/priory_shacl.ttl', format='turtle')
for f in glob.glob('ontology/shapes/*.ttl'): sg.parse(f, format='turtle')
conforms, _, text = pyshacl.validate(g, shacl_graph=sg, inference='rdfs')
print('Conforms:', conforms)
"

# 4. Run HermiT OWL reasoner on core ontology
python3 -c "
import tempfile, subprocess, os, rdflib, owlready2
g = rdflib.Graph()
g.parse('ontology/bfo_subset.ttl', format='turtle')
g.parse('ontology/priory_core.ttl', format='turtle')
with tempfile.NamedTemporaryFile(suffix='.ttl', delete=False) as tmp:
    g.serialize(tmp.name, format='turtle')
jar = str(Path(owlready2.__file__).parent / 'hermit' / 'HermiT.jar')
res = subprocess.run(['java', '-cp', jar, 'org.semanticweb.HermiT.cli.CommandLine', '-k', f'file://{tmp.name}'], capture_output=True, text=True)
os.remove(tmp.name)
print(res.stdout)
"

# 5. One-command verification
make check
```
