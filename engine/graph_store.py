"""Priory Graph Store.

Manages the RDF Knowledge Graph, loads OWL schemas, SKOS reference vocabularies,
and instance graphs, and provides SPARQL query interfaces for recipe trees and acquisition options.
"""

from __future__ import annotations
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import rdflib
from rdflib import Dataset, Graph, Literal, Namespace, URIRef
from rdflib.plugins.sparql import prepareQuery

PRIORY = Namespace("https://priory.gw2/def/")
PRIORY_REF = Namespace("https://priory.gw2/ref/")
ITEM = Namespace("https://priory.gw2/id/item/")
RECIPE = Namespace("https://priory.gw2/id/recipe/")
CHARACTER = Namespace("https://priory.gw2/id/character/")
WEAPON = Namespace("https://priory.gw2/ref/weapon/")
RARITY = Namespace("https://priory.gw2/ref/rarity/")
DISCIPLINE = Namespace("https://priory.gw2/ref/discipline/")
GAMEMODE = Namespace("https://priory.gw2/ref/gamemode/")
CURRENCY = Namespace("https://priory.gw2/ref/currency/")
ARMOR = Namespace("https://priory.gw2/ref/armor/")
SLOT = Namespace("https://priory.gw2/ref/slot/")
ITEMTYPE = Namespace("https://priory.gw2/ref/itemtype/")
PROFESSION = Namespace("https://priory.gw2/ref/profession/")
RACE = Namespace("https://priory.gw2/ref/race/")
MOUNT = Namespace("https://priory.gw2/ref/mount/")
REGION = Namespace("https://priory.gw2/ref/region/")
ZONE = Namespace("https://priory.gw2/ref/zone/")
GUILD_ENHANCEMENT = Namespace("https://priory.gw2/id/guild_enhancement/")
BFO = Namespace("http://purl.obolibrary.org/obo/BFO_")
IAO = Namespace("http://purl.obolibrary.org/obo/IAO_")
ROLE = Namespace("https://priory.gw2/ref/role/")

DEFAULT_NAMESPACES = {
    "priory": PRIORY,
    "priory-ref": PRIORY_REF,
    "item": ITEM,
    "recipe": RECIPE,
    "character": CHARACTER,
    "weapon": WEAPON,
    "armor": ARMOR,
    "slot": SLOT,
    "itemtype": ITEMTYPE,
    "profession": PROFESSION,
    "race": RACE,
    "rarity": RARITY,
    "discipline": DISCIPLINE,
    "gamemode": GAMEMODE,
    "currency": CURRENCY,
    "guild_enhancement": GUILD_ENHANCEMENT,
    "mount": MOUNT,
    "region": REGION,
    "zone": ZONE,
    "bfo": BFO,
    "iao": IAO,
    "role": ROLE,
    "skos": rdflib.SKOS,
    "rdfs": rdflib.RDFS,
    "owl": rdflib.OWL,
    "rdf": rdflib.RDF,
}


_DEFAULT_STORE: Optional[PrioryGraphStore] = None
_DEFAULT_STORE_LOCK = threading.Lock()


def get_default_graph_store() -> PrioryGraphStore:
    """Returns a cached, fully-loaded PrioryGraphStore singleton instance."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is not None and _DEFAULT_STORE._loaded:
        return _DEFAULT_STORE
    with _DEFAULT_STORE_LOCK:
        if _DEFAULT_STORE is None or not _DEFAULT_STORE._loaded:
            store = PrioryGraphStore()
            store.load_all()
            _DEFAULT_STORE = store
    return _DEFAULT_STORE


class PrioryGraphStore:
    """In-memory RDF Graph Store powered by RDFLib Dataset with SPARQL 1.1 and Named Graph support."""

    def __init__(self, ref_repo_path: Optional[Path] = None, def_repo_path: Optional[Path] = None):
        self.dataset = Dataset(default_union=True)
        self.graph = self.dataset.default_graph
        self._uses_default_paths = ref_repo_path is None and def_repo_path is None
        self.ref_repo_path = ref_repo_path or Path("/Users/clementd/Documents/GitHub/gw2-priory-ref")
        self.def_repo_path = def_repo_path or Path("/Users/clementd/Documents/GitHub/gw2-priory-def")
        self._loaded = False
        self._prepared_queries: Dict[str, Any] = {}
        self._item_cache: Dict[int, Optional[Dict[str, Any]]] = {}
        self._direct_ingredients_cache: Dict[int, List[Dict[str, Any]]] = {}
        self._booster_catalog_cache: Optional[Dict[str, Any]] = None
        self._t6_promotions_cache: Optional[Dict[int, Dict[str, Any]]] = None
        self._starter_kit_precursors_cache: Optional[set[int]] = None
        self._benchmark_prices_cache: Optional[Dict[int, float]] = None
        self._weapon_pillars_cache: Dict[int, Dict[str, Any]] = {}
        self._exploration_regions_cache: Dict[str, List[Dict[str, Any]]] = {}
        self._crafting_stations_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._stat_prefix_map_cache: Optional[Dict[str, URIRef]] = None
        self._default_roster_cache: Optional[List[str]] = None
        self._lounge_passes_cache: Optional[Dict[int, Dict[str, Any]]] = None
        self._convenience_catalog_cache: Optional[Tuple[List[str], Dict[str, Dict[str, Any]]]] = None
        self._legendary_precursor_catalog_cache: Optional[Dict[str, Any]] = None
        self._collection_bits_cache: Dict[int, List[Dict[str, Any]]] = {}
        self._query_lock = threading.Lock()

        self._bind_namespaces()

    def _bind_namespaces(self) -> None:
        for prefix, ns in DEFAULT_NAMESPACES.items():
            self.dataset.bind(prefix, ns)
            self.graph.bind(prefix, ns)

    def load_all(self) -> int:
        """Loads all schemas, reference vocabularies, character models, and instances into the graph once."""
        if self._loaded:
            return len(self.graph)

        total_triples_before = len(self.graph)

        # 1. Load Reference Vocabularies exclusively from gw2-priory-ref repository
        vocab_dir = self.ref_repo_path / "vocab"
        if vocab_dir.exists():
            for ttl_file in vocab_dir.glob("*.ttl"):
                self.graph.parse(ttl_file, format="turtle")
        else:
            raise FileNotFoundError(
                f"Reference vocabulary directory not found at: {vocab_dir}. "
                "Ensure gw2-priory-ref repository is cloned."
            )

        # 2. Load Ontology Schemas (BFO Subset, Core, Character, and Application Schemas)
        bfo_subset = self.def_repo_path / "ontology" / "bfo_subset.ttl"
        if bfo_subset.exists():
            self.graph.parse(bfo_subset, format="turtle")

        core_ontology = self.def_repo_path / "ontology" / "priory_core.ttl"
        if core_ontology.exists():
            self.graph.parse(core_ontology, format="turtle")

        character_ontology = self.def_repo_path / "ontology" / "character.ttl"
        if character_ontology.exists():
            self.graph.parse(character_ontology, format="turtle")

        schemas_dir = self.def_repo_path / "ontology" / "schemas"
        if schemas_dir.exists():
            for ttl_file in schemas_dir.glob("*.ttl"):
                self.graph.parse(ttl_file, format="turtle")

        # 3. Load Vocabularies from def if present (e.g. mounts, regions)
        def_vocab_dir = self.def_repo_path / "ontology" / "vocab"
        if def_vocab_dir.exists():
            for ttl_file in def_vocab_dir.glob("*.ttl"):
                self.graph.parse(ttl_file, format="turtle")

        # 4. Load Instances (Recursively from ontology/instances/**/*.ttl)
        instances_dir = self.def_repo_path / "ontology" / "instances"
        if instances_dir.exists():
            for ttl_file in instances_dir.rglob("*.ttl"):
                self.graph.parse(ttl_file, format="turtle")

        # 5. Materialize OWL 2 RL property chains, inverses, and transitive closure
        self._materialize_owl_entailments()

        self._loaded = True
        global _DEFAULT_STORE
        if _DEFAULT_STORE is None and getattr(self, "_uses_default_paths", False):
            _DEFAULT_STORE = self
        return len(self.graph) - total_triples_before

    def _materialize_owl_entailments(self) -> None:
        """Materializes OWL 2 RL property chains, inverses, defined classes, and transitive closures."""
        rdf_type = rdflib.RDF.type
        rdfs_sub = rdflib.RDFS.subClassOf
        p_produces = PRIORY.producesItem
        p_produced_by = PRIORY.producedBy
        p_precursor_to = PRIORY.precursorTo
        p_is_precursor_of = PRIORY.isPrecursorOf
        p_has_precursor = PRIORY.hasPrecursor
        p_has_req = PRIORY.hasIngredientRequirement
        p_req_item = PRIORY.requiresItem
        p_req_ing = PRIORY.requiresIngredient
        p_depends = PRIORY.dependsOnItem
        p_prec_type = PRIORY.hasPrecursorType
        p_leg_gen = PRIORY.legendaryGeneration
        p_gen = PRIORY.generation

        # 1. Canonical recipe output & precursor inverses (producedBy -> producesItem, precursorTo <-> isPrecursorOf <-> hasPrecursor)
        for item, _, r in list(self.graph.triples((None, p_produced_by, None))):
            if (r, p_produces, None) not in self.graph:
                self.graph.add((r, p_produces, item))

        for prec, _, leg in list(self.graph.triples((None, p_precursor_to, None))):
            self.graph.add((leg, p_has_precursor, prec))
            self.graph.add((prec, p_is_precursor_of, leg))
        for prec, _, leg in list(self.graph.triples((None, p_is_precursor_of, None))):
            self.graph.add((leg, p_has_precursor, prec))
            self.graph.add((prec, p_precursor_to, leg))
        for leg, _, prec in list(self.graph.triples((None, p_has_precursor, None))):
            self.graph.add((prec, p_precursor_to, leg))
            self.graph.add((prec, p_is_precursor_of, leg))

        # 2. Property chain: (hasIngredientRequirement o requiresItem) -> requiresIngredient
        req_to_items: Dict[Any, List[Any]] = {}
        for req, _, ing in self.graph.triples((None, p_req_item, None)):
            req_to_items.setdefault(req, []).append(ing)
        for r, _, req in list(self.graph.triples((None, p_has_req, None))):
            for ing in req_to_items.get(req, []):
                self.graph.add((r, p_req_ing, ing))

        # 3. Property chain: (producedBy o requiresIngredient) -> dependsOnItem
        recipe_to_ings: Dict[Any, List[Any]] = {}
        for r, _, ing in self.graph.triples((None, p_req_ing, None)):
            recipe_to_ings.setdefault(r, []).append(ing)
        adj: Dict[Any, set] = {}
        for item, _, r in self.graph.triples((None, p_produced_by, None)):
            for ing in recipe_to_ings.get(r, []):
                if item != ing:
                    self.graph.add((item, p_depends, ing))
                    adj.setdefault(item, set()).add(ing)

        # 4. Transitive closure of dependsOnItem
        for src in list(adj.keys()):
            visited = set()
            stack = list(adj.get(src, []))
            while stack:
                curr = stack.pop()
                if curr in visited or curr == src:
                    continue
                visited.add(curr)
                self.graph.add((src, p_depends, curr))
                for nxt in adj.get(curr, []):
                    if nxt not in visited:
                        stack.append(nxt)

        # 5. Materialize Gen1LegendaryWeapon, Gen2LegendaryWeapon, Gen3LegendaryWeapon
        c_leg_weap = PRIORY.LegendaryWeapon
        c_gen1 = PRIORY.Gen1LegendaryWeapon
        c_gen2 = PRIORY.Gen2LegendaryWeapon
        c_gen3 = PRIORY.Gen3LegendaryWeapon

        gen1_types = {PRIORY.TradablePrecursor, PRIORY.CraftedAndTradeablePrecursor}
        gen2_types = {PRIORY.CollectionHuntPrecursor, PRIORY.ShardCraftingPrecursor, PRIORY.CollectionBoundPrecursor}
        gen3_types = {PRIORY.DragonVendorPrecursor, PRIORY.CraftedGen3Precursor}

        leg_weapons = set(self.graph.subjects(rdf_type, c_leg_weap))
        for w in list(leg_weapons):
            ptypes = set(self.graph.objects(w, p_prec_type))
            gens = {
                int(g.toPython())
                for prop in (p_leg_gen, p_gen)
                for g in self.graph.objects(w, prop)
                if isinstance(g, Literal)
            }
            if (ptypes & gen1_types) or (1 in gens):
                self.graph.add((w, rdf_type, c_gen1))
            if (ptypes & gen2_types) or (2 in gens):
                self.graph.add((w, rdf_type, c_gen2))
            if (ptypes & gen3_types) or (3 in gens):
                self.graph.add((w, rdf_type, c_gen3))

        # 6. Materialize WeaponSpecificPillarGift
        c_gift = PRIORY.GiftItem
        c_leg_gift = PRIORY.LegendaryGift
        c_mastery_gift = PRIORY.MasteryPillarGift
        c_tribute_gift = PRIORY.TributePillarGift
        c_weapon_gift = PRIORY.WeaponSpecificPillarGift

        mastery_gifts = set(self.graph.subjects(rdf_type, c_mastery_gift))
        tribute_gifts = set(self.graph.subjects(rdf_type, c_tribute_gift))
        gift_items = set(self.graph.subjects(rdf_type, c_gift)) | mastery_gifts | tribute_gifts

        for w in leg_weapons:
            for r in self.graph.objects(w, p_produced_by):
                for ing in recipe_to_ings.get(r, []):
                    if ing in gift_items and ing not in mastery_gifts and ing not in tribute_gifts:
                        self.graph.add((ing, rdf_type, c_weapon_gift))
                        self.graph.add((ing, rdf_type, c_leg_gift))

        # 7. Materialize rdfs:subClassOf transitive closure for rdf:type on key Priory classes
        sub_adj: Dict[Any, set] = {}
        for sub_c, _, sup_c in self.graph.triples((None, rdfs_sub, None)):
            if isinstance(sub_c, URIRef) and isinstance(sup_c, URIRef):
                sub_adj.setdefault(sub_c, set()).add(sup_c)

        super_closure: Dict[Any, set] = {}
        for cls in list(sub_adj.keys()):
            visited_cls = set()
            stack_cls = list(sub_adj.get(cls, []))
            while stack_cls:
                curr_c = stack_cls.pop()
                if curr_c in visited_cls or curr_c == cls:
                    continue
                visited_cls.add(curr_c)
                for nxt_c in sub_adj.get(curr_c, []):
                    if nxt_c not in visited_cls:
                        stack_cls.append(nxt_c)
            super_closure[cls] = visited_cls

        target_superclasses = {
            PRIORY.LegendaryWeapon,
            PRIORY.LegendaryGift,
            PRIORY.GiftItem,
            PRIORY.PrecursorWeapon,
            PRIORY.Item,
            PRIORY.ItemBuff,
        }
        for inst, _, cls in list(self.graph.triples((None, rdf_type, None))):
            for sup_c in super_closure.get(cls, ()):
                if sup_c in target_superclasses:
                    self.graph.add((inst, rdf_type, sup_c))

    def query(self, sparql_str: str, init_bindings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a SPARQL query against the graph/dataset and returns list of dict results."""
        with self._query_lock:
            if sparql_str not in self._prepared_queries:
                try:
                    self._prepared_queries[sparql_str] = prepareQuery(sparql_str, initNs=DEFAULT_NAMESPACES)
                except Exception:
                    self._prepared_queries[sparql_str] = None
            q = self._prepared_queries.get(sparql_str)
            if q is not None:
                results = self.dataset.query(q, initBindings=init_bindings or {})
            else:
                results = self.dataset.query(sparql_str, initNs=DEFAULT_NAMESPACES, initBindings=init_bindings or {})
        
        output = []
        for row in results:
            row_dict = {}
            for var in results.vars:
                val = row[var]
                if isinstance(val, Literal):
                    row_dict[str(var)] = val.toPython()
                elif isinstance(val, URIRef):
                    row_dict[str(var)] = str(val)
                else:
                    row_dict[str(var)] = val
            output.append(row_dict)
        return output

    def get_item_by_id(self, gw2_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves item metadata by GW2 API ID."""
        if gw2_id in self._item_cache:
            return self._item_cache[gw2_id]
        sparql = """
        SELECT DISTINCT ?item ?label ?rarity ?chatCode ?isAccountBound WHERE {
            ?item priory:gw2Id ?gw2Id ;
                  rdfs:label ?label .
            OPTIONAL { ?item priory:hasRarity ?rarity }
            OPTIONAL { ?item priory:chatCode ?chatCode }
            OPTIONAL { ?item priory:isAccountBound ?isAccountBound }
        } LIMIT 1
        """
        res = self.query(sparql, init_bindings={"gw2Id": Literal(gw2_id)})
        meta = res[0] if res else None
        self._item_cache[gw2_id] = meta
        return meta

    def get_direct_recipe_ingredients(self, item_id: int) -> List[Dict[str, Any]]:
        """Retrieves direct ingredient requirements for an item's primary recipe."""
        if item_id in self._direct_ingredients_cache:
            return self._direct_ingredients_cache[item_id]
        sparql = """
        SELECT DISTINCT ?recipe ?recipeLabel ?ingredientId ?ingredientLabel ?quantity WHERE {
            ?item priory:gw2Id ?gw2Id ;
                  priory:producedBy ?recipe .
            ?recipe priory:hasIngredientRequirement ?req .
            OPTIONAL { ?recipe rdfs:label ?recipeLabel }
            ?req priory:requiresItem ?ingredient ;
                 priory:requiredQuantity ?quantity .
            ?ingredient priory:gw2Id ?ingredientId ;
                        rdfs:label ?ingredientLabel .
        }
        """
        res = self.query(sparql, init_bindings={"gw2Id": Literal(item_id)})
        self._direct_ingredients_cache[item_id] = res
        return res

    def get_booster_catalog(self) -> Dict[str, Any]:
        """Queries the ontology for all booster, festival gobbler, and tome of knowledge items."""
        if self._booster_catalog_cache is not None:
            return self._booster_catalog_cache

        sparql = """
        SELECT DISTINCT ?id ?label ?cls WHERE {
            VALUES ?cls {
                priory:FestivalGobbler
                priory:TomeOfKnowledge
                priory:ExperienceBooster
                priory:HeroicBooster
                priory:KarmaBooster
                priory:WXPBooster
                priory:CelebrationBooster
                priory:ItemBooster
            }
            ?item a ?cls ;
                  priory:gw2Id ?id ;
                  rdfs:label ?label .
        }
        """
        rows = self.query(sparql)
        booster_names: Dict[int, str] = {}
        gobbler_ids: set[int] = set()
        tome_ids: set[int] = set()
        xp_booster_ids: set[int] = set()
        wvw_booster_ids: set[int] = set()
        karma_booster_ids: set[int] = set()

        xp_classes = {
            str(PRIORY.ExperienceBooster),
            str(PRIORY.HeroicBooster),
            str(PRIORY.CelebrationBooster),
            str(PRIORY.ItemBooster),
        }
        wvw_classes = {
            str(PRIORY.WXPBooster),
            str(PRIORY.ExperienceBooster),
            str(PRIORY.HeroicBooster),
            str(PRIORY.CelebrationBooster),
            str(PRIORY.ItemBooster),
        }
        karma_classes = {
            str(PRIORY.KarmaBooster),
            str(PRIORY.HeroicBooster),
            str(PRIORY.ItemBooster),
        }

        for r in rows:
            item_id = int(r["id"])
            label = str(r["label"])
            cls_uri = str(r["cls"])
            booster_names[item_id] = label
            if cls_uri == str(PRIORY.FestivalGobbler):
                gobbler_ids.add(item_id)
            elif cls_uri == str(PRIORY.TomeOfKnowledge):
                tome_ids.add(item_id)
            if cls_uri in xp_classes:
                xp_booster_ids.add(item_id)
            if cls_uri in wvw_classes:
                wvw_booster_ids.add(item_id)
            if cls_uri in karma_classes:
                karma_booster_ids.add(item_id)

        catalog = {
            "booster_names": booster_names,
            "gobbler_ids": gobbler_ids,
            "tome_ids": tome_ids,
            "xp_booster_ids": xp_booster_ids,
            "wvw_booster_ids": wvw_booster_ids,
            "karma_booster_ids": karma_booster_ids,
        }
        self._booster_catalog_cache = catalog
        return catalog

    def get_t6_material_promotions(self) -> Dict[int, Dict[str, Any]]:
        """Queries the ontology for the 8 canonical T6 materials and their T5 promotion sources."""
        if self._t6_promotions_cache is not None:
            return self._t6_promotions_cache

        sparql = """
        SELECT DISTINCT ?t6Id ?t6Label ?cat ?t5Id ?t5Label WHERE {
            ?t6 priory:gw2Id ?t6Id ;
                rdfs:label ?t6Label ;
                priory:trophyCategory ?cat ;
                priory:promotedFromT5 ?t5 .
            ?t5 priory:gw2Id ?t5Id ;
                rdfs:label ?t5Label .
        }
        """
        rows = self.query(sparql)
        promotions: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            t6_id = int(r["t6Id"])
            t5_id = int(r["t5Id"])
            if t6_id not in promotions:
                promotions[t6_id] = {
                    "name": str(r["t6Label"]),
                    "category": str(r["cat"]),
                    "t5_id": t5_id,
                    "t5_ids": [t5_id],
                    "t5_name": str(r["t5Label"]),
                }
            elif t5_id not in promotions[t6_id]["t5_ids"]:
                promotions[t6_id]["t5_ids"].append(t5_id)

        self._t6_promotions_cache = promotions
        return promotions

    def get_starter_kit_precursor_ids(self) -> set[int]:
        """Queries the ontology for all Generation 1 precursor IDs in the Wizard's Vault Starter Kit pool."""
        if self._starter_kit_precursors_cache is not None:
            return self._starter_kit_precursors_cache

        sparql = """
        SELECT DISTINCT ?id WHERE {
            {
                ?item priory:gw2Id ?id ;
                      priory:inStarterKitPool true .
            } UNION {
                ?kit a priory:LegendaryStarterKit ;
                     priory:unpacksInto ?item .
                ?item a priory:PrecursorWeapon ;
                      priory:gw2Id ?id .
            }
        }
        """
        rows = self.query(sparql)
        ids = {int(r["id"]) for r in rows if r.get("id") is not None}
        self._starter_kit_precursors_cache = ids
        return ids

    def get_benchmark_prices(self) -> Dict[int, float]:
        """Queries the ontology for item fallback benchmark gold prices."""
        if self._benchmark_prices_cache is not None:
            return self._benchmark_prices_cache

        sparql = """
        SELECT DISTINCT ?id ?price WHERE {
            ?item priory:gw2Id ?id ;
                  priory:benchmarkUnitGold ?price .
        }
        """
        rows = self.query(sparql)
        prices = {int(r["id"]): float(r["price"]) for r in rows if r.get("id") is not None and r.get("price") is not None}
        self._benchmark_prices_cache = prices
        return prices

    def get_weapon_inferred_pillars(self, target_item_id: int) -> Dict[str, Any]:
        """Infers generation, precursor, BOM pillar gifts, and cross-weapon synergies for a target weapon."""
        if target_item_id in self._weapon_pillars_cache:
            return self._weapon_pillars_cache[target_item_id]

        gen_sparql = """
        SELECT DISTINCT ?cls ?gen ?precId ?precLabel WHERE {
            ?w priory:gw2Id ?targetId .
            OPTIONAL {
                VALUES ?cls {
                    priory:Gen1LegendaryWeapon
                    priory:Gen2LegendaryWeapon
                    priory:Gen3LegendaryWeapon
                }
                ?w a ?cls .
            }
            OPTIONAL { ?w priory:legendaryGeneration ?gen }
            OPTIONAL {
                ?w priory:hasPrecursor ?prec .
                ?prec priory:gw2Id ?precId ;
                      rdfs:label ?precLabel .
            }
        }
        """
        gen_rows = self.query(gen_sparql, init_bindings={"targetId": Literal(target_item_id)})
        generation = 1
        precursor_id: Optional[int] = None
        precursor_name: Optional[str] = None

        for r in gen_rows:
            cls_uri = str(r.get("cls") or "")
            if cls_uri == str(PRIORY.Gen3LegendaryWeapon):
                generation = 3
            elif cls_uri == str(PRIORY.Gen2LegendaryWeapon):
                generation = 2
            elif cls_uri == str(PRIORY.Gen1LegendaryWeapon):
                generation = 1
            elif r.get("gen") is not None:
                generation = int(r["gen"])
            if r.get("precId") is not None and precursor_id is None:
                precursor_id = int(r["precId"])
                precursor_name = str(r["precLabel"])

        # Query direct recipe ingredients and their pillar classifications
        ing_sparql = """
        SELECT DISTINCT ?ingId ?ingLabel ?cls WHERE {
            ?w priory:gw2Id ?targetId ;
               priory:producedBy ?recipe .
            ?recipe priory:requiresIngredient ?ing .
            ?ing priory:gw2Id ?ingId ;
                 rdfs:label ?ingLabel .
            OPTIONAL {
                VALUES ?cls {
                    priory:PrecursorWeapon
                    priory:MasteryPillarGift
                    priory:TributePillarGift
                    priory:WeaponSpecificPillarGift
                }
                ?ing a ?cls .
            }
        }
        """
        ing_rows = self.query(ing_sparql, init_bindings={"targetId": Literal(target_item_id)})
        mastery_gift_id: Optional[int] = None
        mastery_gift_name: Optional[str] = None
        tribute_gift_id: Optional[int] = None
        tribute_gift_name: Optional[str] = None
        weapon_gift_id: Optional[int] = None
        weapon_gift_name: Optional[str] = None

        # Group classes per ingredient ID
        ing_classes: Dict[int, set[str]] = {}
        ing_labels: Dict[int, str] = {}
        for r in ing_rows:
            iid = int(r["ingId"])
            ing_labels[iid] = str(r["ingLabel"])
            if r.get("cls"):
                ing_classes.setdefault(iid, set()).add(str(r["cls"]))
            else:
                ing_classes.setdefault(iid, set())

        for iid, classes in ing_classes.items():
            label = ing_labels[iid]
            if str(PRIORY.PrecursorWeapon) in classes and precursor_id is None:
                precursor_id = iid
                precursor_name = label
            elif str(PRIORY.WeaponSpecificPillarGift) in classes:
                weapon_gift_id = iid
                weapon_gift_name = label
            elif str(PRIORY.TributePillarGift) in classes and str(PRIORY.MasteryPillarGift) not in classes:
                tribute_gift_id = iid
                tribute_gift_name = label
            elif str(PRIORY.MasteryPillarGift) in classes and str(PRIORY.TributePillarGift) not in classes:
                mastery_gift_id = iid
                mastery_gift_name = label

        # Handle dual-tagged gifts (such as item:71820 Mystic Tribute)
        for iid, classes in ing_classes.items():
            label = ing_labels[iid]
            if str(PRIORY.TributePillarGift) in classes and str(PRIORY.MasteryPillarGift) in classes:
                if tribute_gift_id is None and ("Tribute" in label or "Fortune" in label):
                    tribute_gift_id = iid
                    tribute_gift_name = label
                elif mastery_gift_id is None:
                    mastery_gift_id = iid
                    mastery_gift_name = label

        # Query cross-weapon synthesis targets (e.g., Twilight/Sunrise -> Eternity)
        syn_sparql = """
        SELECT DISTINCT ?synId ?synLabel ?partnerId ?partnerLabel WHERE {
            ?w priory:gw2Id ?targetId ;
               priory:unlocksSynthesisTarget ?syn .
            ?syn priory:gw2Id ?synId ;
                 rdfs:label ?synLabel .
            OPTIONAL {
                ?syn priory:requiresPartnerLegendary ?partner .
                ?partner priory:gw2Id ?partnerId ;
                         rdfs:label ?partnerLabel .
                FILTER(?partnerId != ?targetId)
            }
        }
        """
        syn_rows = self.query(syn_sparql, init_bindings={"targetId": Literal(target_item_id)})
        syn_map: Dict[int, Dict[str, Any]] = {}
        for r in syn_rows:
            sid = int(r["synId"])
            if sid not in syn_map:
                syn_map[sid] = {
                    "id": sid,
                    "name": str(r["synLabel"]),
                    "partner_ids": [],
                    "partner_names": [],
                }
            if r.get("partnerId") is not None:
                pid = int(r["partnerId"])
                if pid not in syn_map[sid]["partner_ids"]:
                    syn_map[sid]["partner_ids"].append(pid)
                    syn_map[sid]["partner_names"].append(str(r["partnerLabel"]))

        # Query partner legendaries if the target itself is a composite synthesis weapon (e.g., Eternity 30689)
        partner_sparql = """
        SELECT DISTINCT ?partnerId ?partnerLabel WHERE {
            ?w priory:gw2Id ?targetId ;
               priory:requiresPartnerLegendary ?partner .
            ?partner priory:gw2Id ?partnerId ;
                     rdfs:label ?partnerLabel .
        }
        """
        partner_rows = self.query(partner_sparql, init_bindings={"targetId": Literal(target_item_id)})
        partner_legendaries: List[Dict[str, Any]] = []
        seen_partners: set[int] = set()
        for r in partner_rows:
            pid = int(r["partnerId"])
            if pid not in seen_partners:
                seen_partners.add(pid)
                partner_legendaries.append({"id": pid, "name": str(r["partnerLabel"])})

        result = {
            "generation": generation,
            "precursor_id": precursor_id,
            "precursor_name": precursor_name,
            "mastery_gift_id": mastery_gift_id,
            "mastery_gift_name": mastery_gift_name,
            "tribute_gift_id": tribute_gift_id,
            "tribute_gift_name": tribute_gift_name,
            "weapon_gift_id": weapon_gift_id,
            "weapon_gift_name": weapon_gift_name,
            "synergy_targets": list(syn_map.values()),
            "partner_legendaries": partner_legendaries,
        }
        self._weapon_pillars_cache[target_item_id] = result
        return result

    def get_exploration_regions(self, generation: str = "GEN1") -> List[Dict[str, Any]]:
        """Queries ontology-grounded priory:ExplorationRegion individuals for GEN1, GEN2, or GEN3."""
        gen_raw = str(generation or "GEN1").strip().upper()
        if gen_raw in ("1", "GEN 1", "GENERATION 1"):
            gen_key = "GEN1"
        elif gen_raw in ("2", "GEN 2", "GENERATION 2"):
            gen_key = "GEN2"
        elif gen_raw in ("3", "GEN 3", "GENERATION 3"):
            gen_key = "GEN3"
        else:
            gen_key = gen_raw

        if gen_key in self._exploration_regions_cache:
            return [dict(r) for r in self._exploration_regions_cache[gen_key]]

        sparql = """
        SELECT DISTINCT ?region ?label ?order ?zoneCount ?baseHours ?diff ?primaryMount ?fallbackMount ?notes ?waypoint WHERE {
            ?region a priory:ExplorationRegion ;
                    rdfs:label ?label ;
                    priory:forGeneration ?gen .
            OPTIONAL { ?region priory:regionOrder ?order }
            OPTIONAL { ?region priory:zoneCount ?zoneCount }
            OPTIONAL { ?region priory:baseExplorationHours ?baseHours }
            OPTIONAL { ?region priory:explorationDifficulty ?diff }
            OPTIONAL { ?region priory:primaryMountRecommendation ?primaryMount }
            OPTIONAL { ?region priory:fallbackMountRecommendation ?fallbackMount }
            OPTIONAL { ?region priory:strategyNotes ?notes }
            OPTIONAL { ?region priory:startingWaypoint ?waypoint }
        }
        """
        rows = self.query(sparql, init_bindings={"gen": Literal(gen_key)})
        sorted_rows = sorted(
            rows,
            key=lambda r: (
                int(r["order"]) if r.get("order") is not None else 999,
                str(r.get("label", "")),
            ),
        )
        regions: List[Dict[str, Any]] = []
        for r in sorted_rows:
            regions.append({
                "region_name": str(r["label"]),
                "zones_count": int(r["zoneCount"]) if r.get("zoneCount") is not None else 1,
                "base_hours": float(r["baseHours"]) if r.get("baseHours") is not None else 2.0,
                "difficulty": str(r.get("diff") or "Moderate"),
                "recommended_mount": str(r.get("primaryMount") or "skyscale"),
                "fallback_mount": str(r.get("fallbackMount") or "raptor"),
                "strategy_notes": str(r.get("notes") or ""),
                "starting_waypoint": str(r.get("waypoint") or ""),
            })
        if regions:
            self._exploration_regions_cache[gen_key] = regions
        return [dict(r) for r in regions]

    def get_crafting_stations(self) -> Dict[str, Dict[str, Any]]:
        """Queries ontology-grounded priory:CraftingStation individuals for all disciplines and Mystic Forge."""
        if self._crafting_stations_cache is not None:
            return {k: dict(v) for k, v in self._crafting_stations_cache.items()}

        sparql = """
        SELECT DISTINCT ?station ?slug ?disc ?label ?npc ?wp ?zone ?altWp WHERE {
            ?station a priory:CraftingStation ;
                     rdfs:label ?label .
            OPTIONAL { ?station priory:disciplineSlug ?slug }
            OPTIONAL { ?station priory:forDiscipline ?disc }
            OPTIONAL { ?station priory:vendorNPC ?npc }
            OPTIONAL { ?station priory:nearestWaypoint ?wp }
            OPTIONAL { ?station priory:zoneName ?zone }
            OPTIONAL { ?station priory:alternateWaypoint ?altWp }
        }
        """
        rows = self.query(sparql)
        stations: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            slug = str(r.get("slug") or "").strip().lower()
            if not slug and r.get("disc"):
                slug = str(r["disc"]).rstrip("/").split("/")[-1].strip().lower()
            if not slug:
                continue
            stations[slug] = {
                "station_name": str(r["label"]),
                "vendor_npc": str(r.get("npc") or f"Master {slug.title()}"),
                "chat_link": str(r.get("wp") or "[&BBAEAAA=]"),
                "zone": str(r.get("zone") or "Lion's Arch"),
                "alternate_waypoint": str(r.get("altWp") or "[&BBAEAAA=]"),
            }
        if stations:
            self._crafting_stations_cache = stations
        return {k: dict(v) for k, v in stations.items()}

    def get_stat_prefix_map(self) -> Dict[str, URIRef]:
        """Queries ontology-grounded priory:StatPrefix concepts and maps lowercase stat slugs to URIRef."""
        if self._stat_prefix_map_cache is not None:
            return dict(self._stat_prefix_map_cache)

        sparql = """
        SELECT DISTINCT ?stat ?slug ?label WHERE {
            { ?stat a priory:StatPrefix }
            UNION
            { ?stat skos:inScheme priory:StatCombinationScheme }
            OPTIONAL { ?stat priory:statSlug ?slug }
            OPTIONAL { ?stat skos:prefLabel ?label }
        }
        """
        rows = self.query(sparql)
        stat_map: Dict[str, URIRef] = {}
        for r in rows:
            stat_uri = URIRef(str(r["stat"]))
            if r.get("slug"):
                stat_map[str(r["slug"]).strip().lower()] = stat_uri
            else:
                local_slug = str(r["stat"]).rstrip("/").split("/")[-1].strip().lower()
                if local_slug:
                    stat_map[local_slug] = stat_uri
                if r.get("label"):
                    lbl_slug = str(r["label"]).replace("'s", "").strip().lower()
                    if lbl_slug:
                        stat_map[lbl_slug] = stat_uri
        if stat_map:
            self._stat_prefix_map_cache = stat_map
        return dict(stat_map)

    def get_default_character_roster(self) -> List[str]:
        """Queries ontology-grounded priory:DefaultRosterMember individuals in canonical roster order."""
        if self._default_roster_cache is not None:
            return list(self._default_roster_cache)

        sparql = """
        SELECT DISTINCT ?member ?name ?rName ?label ?order WHERE {
            ?member a priory:DefaultRosterMember .
            OPTIONAL { ?member priory:rosterCharacterName ?rName }
            OPTIONAL { ?member priory:characterName ?name }
            OPTIONAL { ?member rdfs:label ?label }
            OPTIONAL { ?member priory:rosterOrder ?order }
        }
        """
        rows = self.query(sparql)
        sorted_rows = sorted(
            rows,
            key=lambda r: (
                int(r["order"]) if r.get("order") is not None else 999,
                str(r.get("rName") or r.get("name") or r.get("label") or ""),
            ),
        )
        roster: List[str] = []
        for r in sorted_rows:
            nm = str(r.get("rName") or r.get("name") or r.get("label") or "").strip()
            if nm and nm not in roster:
                roster.append(nm)
        if roster:
            self._default_roster_cache = roster
        return list(roster)

    def get_lounge_passes(self) -> Dict[int, Dict[str, Any]]:
        """Queries ontology-grounded VIP Lounge Pass catalog entries and dynamic VIPLoungePass instances."""
        sparql = """
        SELECT DISTINCT ?entry ?id ?label ?chatLink ?zone ?slug ?tier ?hasCrafting ?hasForge ?hasBank ?hasTp ?hasVendor ?instantReturn ?tpNote WHERE {
            {
                ?entry a priory:LoungePassCatalogEntry ;
                       priory:catalogItemId ?id ;
                       rdfs:label ?label .
            }
            UNION
            {
                { ?entry a priory:VIPLoungePass } UNION { ?entry a priory:VIPPass }
                ?entry priory:gw2Id ?id ;
                       rdfs:label ?label .
            }
            OPTIONAL { ?entry priory:catalogChatLink ?chatLink }
            OPTIONAL { ?entry priory:chatCode ?chatLink }
            OPTIONAL { ?entry priory:zoneName ?zone }
            OPTIONAL { ?entry priory:loungeSlug ?slug }
            OPTIONAL { ?entry priory:convenienceTier ?tier }
            OPTIONAL { ?entry priory:hasCraftingStations ?hasCrafting }
            OPTIONAL { ?entry priory:hasMysticForge ?hasForge }
            OPTIONAL { ?entry priory:hasBank ?hasBank }
            OPTIONAL { ?entry priory:hasTradingPost ?hasTp }
            OPTIONAL { ?entry priory:hasVendor ?hasVendor }
            OPTIONAL { ?entry priory:hasInstantReturn ?instantReturn }
            OPTIONAL { ?entry priory:teleportNote ?tpNote }
        }
        """
        rows = self.query(sparql)
        passes: Dict[int, Dict[str, Any]] = {}
        # Prefer LoungePassCatalogEntry rows first so canonical catalog entries take precedence
        sorted_rows = sorted(
            rows,
            key=lambda r: (0 if "LoungeCatalog_" in str(r.get("entry", "")) else 1, int(r["id"])),
        )
        for r in sorted_rows:
            pid = int(r["id"])
            if pid in passes:
                continue
            entry_dict: Dict[str, Any] = {
                "name": str(r["label"]),
                "chat_link": str(r.get("chatLink") or ""),
                "zone": str(r.get("zone") or "VIP Lounge"),
            }
            if r.get("slug") is not None:
                entry_dict["lounge_id"] = str(r["slug"])
            if r.get("tier") is not None:
                entry_dict["tier"] = str(r["tier"])
            if r.get("hasCrafting") is not None:
                entry_dict["has_crafting"] = bool(r["hasCrafting"])
            if r.get("hasForge") is not None:
                entry_dict["has_mystic_forge"] = bool(r["hasForge"])
            if r.get("hasBank") is not None:
                entry_dict["has_bank"] = bool(r["hasBank"])
            if r.get("hasTp") is not None:
                entry_dict["has_tp"] = bool(r["hasTp"])
            if r.get("hasVendor") is not None:
                entry_dict["has_vendor"] = bool(r["hasVendor"])
            if r.get("instantReturn") is not None:
                entry_dict["instant_return"] = bool(r["instantReturn"])
            if r.get("tpNote") is not None:
                entry_dict["teleport_note"] = str(r["tpNote"])
            passes[pid] = entry_dict
        return passes

    def get_convenience_catalog(self) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
        """Queries ontology-grounded convenience categories and convenience items catalog."""
        if self._convenience_catalog_cache is not None:
            cats, items = self._convenience_catalog_cache
            return list(cats), {k: dict(v) for k, v in items.items()}

        cat_sparql = """
        SELECT DISTINCT ?label ?order WHERE {
            ?cat a priory:ConvenienceCategoryEntry ;
                 rdfs:label ?label ;
                 priory:categoryOrder ?order .
        }
        """
        cat_rows = sorted(
            self.query(cat_sparql),
            key=lambda r: (int(r["order"]) if r.get("order") is not None else 999, str(r.get("label", ""))),
        )
        categories: List[str] = [str(r["label"]) for r in cat_rows]

        item_sparql = """
        SELECT DISTINCT ?entry ?slug ?order ?cat ?id ?chatLink ?allIdsCsv ?label ?type ?costCopper ?ectoRate ?note WHERE {
            ?entry a priory:ConvenienceCatalogEntry ;
                   priory:convenienceSlug ?slug ;
                   priory:catalogItemId ?id ;
                   rdfs:label ?label ;
                   priory:convenienceType ?type ;
                   priory:convenienceCategory ?cat .
            OPTIONAL { ?entry priory:categoryOrder ?order }
            OPTIONAL { ?entry priory:catalogChatLink ?chatLink }
            OPTIONAL { ?entry priory:allItemIdsCsv ?allIdsCsv }
            OPTIONAL { ?entry priory:salvageCostCopper ?costCopper }
            OPTIONAL { ?entry priory:ectoYieldRate ?ectoRate }
            OPTIONAL { ?entry priory:utilityNote ?note }
        }
        """
        item_rows = sorted(
            self.query(item_sparql),
            key=lambda r: (int(r["order"]) if r.get("order") is not None else 999, str(r.get("slug", ""))),
        )
        items: Dict[str, Dict[str, Any]] = {}
        for r in item_rows:
            slug = str(r["slug"])
            pid = int(r["id"])
            all_ids_str = str(r.get("allIdsCsv") or "")
            if all_ids_str:
                all_ids = [int(x) for x in all_ids_str.split(",") if x.strip()]
            else:
                all_ids = [pid]
            info: Dict[str, Any] = {
                "id": pid,
                "all_ids": all_ids,
                "name": str(r["label"]),
                "chat_link": str(r.get("chatLink") or ""),
                "type": str(r["type"]),
                "category": str(r["cat"]),
            }
            if r.get("costCopper") is not None:
                info["cost_copper"] = int(r["costCopper"])
            if r.get("ectoRate") is not None:
                info["ecto_rate"] = float(r["ectoRate"])
            if r.get("note") is not None:
                info["note"] = str(r["note"])
            items[slug] = info

        if categories and items:
            self._convenience_catalog_cache = (categories, items)
        return list(categories), {k: dict(v) for k, v in items.items()}

    def get_legendary_and_precursor_catalog(self) -> Dict[str, Any]:
        """Queries ontology-grounded weapon, armor, precursor, weapon-type discipline rules, and Hobbs collections."""
        graph_len = len(self.graph)
        if (
            self._legendary_precursor_catalog_cache is not None
            and getattr(self, "_legendary_precursor_catalog_sig", -1) == graph_len
        ):
            return self._legendary_precursor_catalog_cache

        # 1. Weapon Type Discipline Rules
        rule_sparql = """
        SELECT DISTINCT ?wtype ?pDisc ?pRat ?sDisc ?sRat WHERE {
            ?rule a priory:WeaponTypeDisciplineRule ;
                  priory:weaponTypeSlug ?wtype ;
                  priory:primaryDisciplineSlug ?pDisc ;
                  priory:primaryDisciplineRating ?pRat .
            OPTIONAL { ?rule priory:secondaryDisciplineSlug ?sDisc }
            OPTIONAL { ?rule priory:secondaryDisciplineRating ?sRat }
        }
        """
        weapon_type_disciplines: Dict[str, Tuple[Tuple[str, int], Tuple[str, int]]] = {}
        for r in self.query(rule_sparql):
            wt = str(r["wtype"]).strip().lower()
            p_pair = (str(r["pDisc"]), int(r["pRat"]))
            s_pair = (
                str(r.get("sDisc") or "armorsmith"),
                int(r["sRat"]) if r.get("sRat") is not None else 400,
            )
            weapon_type_disciplines[wt] = (p_pair, s_pair)

        # 2. Gen 1, Gen 2, Gen 3 Legendary Weapon Catalog Entries
        weap_sparql = """
        SELECT DISTINCT ?gen ?id ?label ?wtype ?precId ?precName ?legacyCsv ?pDisc ?pRat ?sDisc ?sRat WHERE {
            ?entry a priory:LegendaryWeaponCatalogEntry ;
                   priory:forGeneration ?gen ;
                   priory:catalogItemId ?id ;
                   rdfs:label ?label ;
                   priory:primaryDisciplineSlug ?pDisc ;
                   priory:primaryDisciplineRating ?pRat .
            OPTIONAL { ?entry priory:weaponTypeSlug ?wtype }
            OPTIONAL { ?entry priory:precursorItemId ?precId }
            OPTIONAL { ?entry priory:precursorName ?precName }
            OPTIONAL { ?entry priory:legacyPrecursorIdsCsv ?legacyCsv }
            OPTIONAL { ?entry priory:secondaryDisciplineSlug ?sDisc }
            OPTIONAL { ?entry priory:secondaryDisciplineRating ?sRat }
        }
        """
        gen1_weapons: Dict[int, Dict[str, Any]] = {}
        gen2_weapons: Dict[int, Dict[str, Any]] = {}
        gen3_weapon_names: Dict[int, str] = {}
        gen3_weapon_disciplines: Dict[int, Tuple[str, int]] = {}

        for r in self.query(weap_sparql):
            gen_key = str(r["gen"]).strip().upper()
            wid = int(r["id"])
            wname = str(r["label"])
            p_disc = str(r["pDisc"])
            p_rat = int(r["pRat"])
            if gen_key == "GEN3":
                gen3_weapon_names[wid] = wname
                gen3_weapon_disciplines[wid] = (p_disc, p_rat)
                continue

            s_disc = str(r.get("sDisc") or "armorsmith")
            s_rat = int(r["sRat"]) if r.get("sRat") is not None else 400
            prec_id = int(r["precId"]) if r.get("precId") is not None else 0
            prec_name = str(r.get("precName") or "")
            wtype = str(r.get("wtype") or "Greatsword")
            legacy_str = str(r.get("legacyCsv") or "")
            legacy_tuple = tuple(int(x) for x in legacy_str.split(",") if x.strip())

            winfo: Dict[str, Any] = {
                "name": wname,
                "precursor_id": prec_id,
                "precursor_name": prec_name,
                "type": wtype,
                "disc": (p_disc, p_rat),
                "sec_disc": (s_disc, s_rat),
                "primary": p_disc,
                "rating": p_rat,
                "secondary": s_disc,
                "secondary_rating": s_rat,
            }
            if legacy_tuple:
                winfo["legacy_precursor_ids"] = legacy_tuple

            if gen_key == "GEN1":
                gen1_weapons[wid] = winfo
            elif gen_key == "GEN2":
                gen2_weapons[wid] = winfo

        # 3. Legendary Armor Catalog Entries
        armor_sparql = """
        SELECT DISTINCT ?id ?label ?pDisc ?pRat WHERE {
            ?entry a priory:LegendaryArmorCatalogEntry ;
                   priory:catalogItemId ?id ;
                   rdfs:label ?label ;
                   priory:primaryDisciplineSlug ?pDisc ;
                   priory:primaryDisciplineRating ?pRat .
        }
        """
        armor_names: Dict[int, str] = {}
        legendary_armor_disciplines: Dict[int, Tuple[str, int]] = {}
        for r in self.query(armor_sparql):
            aid = int(r["id"])
            armor_names[aid] = str(r["label"])
            legendary_armor_disciplines[aid] = (str(r["pDisc"]), int(r["pRat"]))

        # 4. Precursor Catalog Entries
        prec_sparql = """
        SELECT DISTINCT ?id ?label ?targetWid WHERE {
            ?entry a priory:PrecursorCatalogEntry ;
                   priory:catalogItemId ?id ;
                   rdfs:label ?label .
            OPTIONAL { ?entry priory:targetWeaponId ?targetWid }
        }
        """
        precursor_names: Dict[int, str] = {}
        precursor_to_weapon: Dict[int, int] = {}
        for r in self.query(prec_sparql):
            pid = int(r["id"])
            precursor_names[pid] = str(r["label"])
            if r.get("targetWid") is not None:
                precursor_to_weapon[pid] = int(r["targetWid"])

        # Dynamic scan for any additional LegendaryWeapon / PrecursorWeapon / LegendaryArmor nodes in graph
        dyn_weap_sparql = """
        SELECT DISTINCT ?wId ?wLabel ?wType ?gen ?facet ?precId ?precLabel WHERE {
            ?w a priory:LegendaryWeapon ;
               priory:gw2Id ?wId ;
               rdfs:label ?wLabel .
            OPTIONAL { ?w priory:hasWeaponType ?wType }
            OPTIONAL { ?w priory:generation ?gen }
            OPTIONAL { ?w priory:hasDragonFacet ?facet }
            OPTIONAL {
                { ?w priory:hasPrecursor ?prec }
                UNION { ?prec priory:precursorTo ?w }
                UNION { ?prec priory:isPrecursorOf ?w }
                ?prec priory:gw2Id ?precId ;
                      rdfs:label ?precLabel .
            }
        }
        """
        for row in self.query(dyn_weap_sparql):
            if row.get("facet"):
                continue
            w_id = int(row["wId"])
            if w_id in gen1_weapons or w_id in gen2_weapons or w_id in gen3_weapon_names:
                continue
            w_label = str(row["wLabel"])
            w_type_uri = str(row.get("wType", ""))
            w_type = w_type_uri.rstrip("/").split("/")[-1] if w_type_uri else "Greatsword"
            disc_pair = weapon_type_disciplines.get(
                w_type.lower(), (("weaponsmith", 500), ("armorsmith", 400))
            )
            gen_str = str(row.get("gen", ""))
            p_id = int(row["precId"]) if row.get("precId") is not None else 0
            p_label = str(row.get("precLabel", f"Precursor {p_id}")) if p_id else "Precursor"
            if "1" in gen_str or (30680 <= w_id <= 30705):
                if p_id:
                    gen1_weapons[w_id] = {
                        "name": w_label,
                        "precursor_id": p_id,
                        "precursor_name": p_label,
                        "type": w_type,
                        "disc": disc_pair[0],
                        "sec_disc": disc_pair[1],
                        "primary": disc_pair[0][0],
                        "rating": disc_pair[0][1],
                        "secondary": disc_pair[1][0],
                        "secondary_rating": disc_pair[1][1],
                    }
                    precursor_names.setdefault(p_id, p_label)
            elif "2" in gen_str or (70000 <= w_id < 95000):
                gen2_weapons[w_id] = {
                    "name": w_label,
                    "precursor_id": p_id,
                    "precursor_name": p_label,
                    "type": w_type,
                    "disc": disc_pair[0],
                    "sec_disc": disc_pair[1],
                    "primary": disc_pair[0][0],
                    "rating": disc_pair[0][1],
                    "secondary": disc_pair[1][0],
                    "secondary_rating": disc_pair[1][1],
                }
                if p_id:
                    precursor_names.setdefault(p_id, p_label)
            else:
                gen3_weapon_names[w_id] = w_label
                gen3_weapon_disciplines[w_id] = disc_pair[0]

        dyn_prec_sparql = """
        SELECT DISTINCT ?pId ?pLabel WHERE {
            ?p a priory:PrecursorWeapon ;
               priory:gw2Id ?pId ;
               rdfs:label ?pLabel .
        }
        """
        for row in self.query(dyn_prec_sparql):
            p_id = int(row["pId"])
            precursor_names.setdefault(p_id, str(row["pLabel"]))

        dyn_armor_sparql = """
        SELECT DISTINCT ?aId ?aLabel ?weightClass WHERE {
            ?a a priory:LegendaryArmor ;
               priory:gw2Id ?aId ;
               rdfs:label ?aLabel .
            OPTIONAL { ?a priory:hasArmorWeight ?weightClass }
            OPTIONAL { ?a priory:hasWeightClass ?weightClass }
        }
        """
        for row in self.query(dyn_armor_sparql):
            a_id = int(row["aId"])
            armor_names.setdefault(a_id, str(row["aLabel"]))
            if a_id not in legendary_armor_disciplines:
                w_cls = str(row.get("weightClass", "")).lower()
                if "light" in w_cls:
                    legendary_armor_disciplines[a_id] = ("tailor", 500)
                elif "medium" in w_cls:
                    legendary_armor_disciplines[a_id] = ("leatherworker", 500)
                else:
                    legendary_armor_disciplines[a_id] = ("armorsmith", 500)

        # Re-apply deterministic GEN1 / GEN2 precursor_to_weapon mapping order
        for wid, winfo in gen1_weapons.items():
            if winfo.get("precursor_id"):
                precursor_to_weapon[winfo["precursor_id"]] = wid
        for wid, winfo in gen2_weapons.items():
            if winfo.get("precursor_id"):
                precursor_to_weapon[winfo["precursor_id"]] = wid
            for l_prec in winfo.get("legacy_precursor_ids", ()):
                if l_prec not in precursor_to_weapon:
                    precursor_to_weapon[l_prec] = wid

        # 5. Master Craftsman Hobbs Collection Stages
        hobbs_sparql = """
        SELECT DISTINCT ?pid ?tier ?achCsv ?label ?bits ?mTier ?mName WHERE {
            ?stage a priory:HobbsCollectionStage ;
                   priory:forPrecursorId ?pid ;
                   priory:collectionTierNumber ?tier ;
                   priory:achievementIdsCsv ?achCsv ;
                   rdfs:label ?label ;
                   priory:bitsTotal ?bits ;
                   priory:masteryTier ?mTier ;
                   priory:masteryName ?mName .
        }
        """
        hobbs_by_pid: Dict[int, List[Dict[str, Any]]] = {}
        for r in self.query(hobbs_sparql):
            pid = int(r["pid"])
            ach_ids = [int(x) for x in str(r["achCsv"]).split(",") if x.strip()]
            hobbs_by_pid.setdefault(pid, []).append({
                "tier": int(r["tier"]),
                "id": ach_ids[0] if ach_ids else 0,
                "name": str(r["label"]),
                "ach_ids": ach_ids,
                "bits_total": int(r["bits"]),
                "mastery_tier": int(r["mTier"]),
                "mastery_name": str(r["mName"]),
            })
        hobbs_collections: Dict[int, List[Dict[str, Any]]] = {
            pid: sorted(tiers, key=lambda t: t["tier"])
            for pid, tiers in hobbs_by_pid.items()
        }
        for pid, tiers in list(hobbs_collections.items()):
            wid = precursor_to_weapon.get(pid)
            if wid and wid not in hobbs_collections:
                hobbs_collections[wid] = tiers
        for alias_wid, src_pid in ((75207, 75208), (72713, 75208), (78052, 78053), (78556, 78053)):
            if src_pid in hobbs_collections:
                hobbs_collections[alias_wid] = hobbs_collections[src_pid]

        gen1_precursor_ids = {w["precursor_id"] for w in gen1_weapons.values() if w.get("precursor_id")} | (
            {29165} if 29165 in precursor_names else set()
        )
        gen2_precursor_ids = {w["precursor_id"] for w in gen2_weapons.values() if w.get("precursor_id")}
        for w in gen2_weapons.values():
            for lp in w.get("legacy_precursor_ids", ()):
                if lp in precursor_names:
                    gen2_precursor_ids.add(lp)

        catalog = {
            "weapon_type_disciplines": weapon_type_disciplines,
            "gen1_weapons": gen1_weapons,
            "gen2_weapons": gen2_weapons,
            "gen3_weapon_names": gen3_weapon_names,
            "gen3_weapon_disciplines": gen3_weapon_disciplines,
            "armor_names": armor_names,
            "legendary_armor_disciplines": legendary_armor_disciplines,
            "precursor_names": precursor_names,
            "precursor_to_weapon": precursor_to_weapon,
            "hobbs_collections": hobbs_collections,
            "gen1_weapon_ids": set(gen1_weapons.keys()),
            "gen1_precursor_ids": gen1_precursor_ids,
            "gen2_weapon_ids": set(gen2_weapons.keys()),
            "gen2_precursor_ids": gen2_precursor_ids,
            "gen3_weapon_ids": set(gen3_weapon_names.keys()),
            "legendary_armor_ids": set(armor_names.keys()),
        }
        self._legendary_precursor_catalog_cache = catalog
        self._legendary_precursor_catalog_sig = graph_len
        return catalog

    def get_collection_bits(self, achievement_id: int) -> List[Dict[str, Any]]:
        """Queries ontology-grounded priory:CollectionBitObjective individuals for a given achievement ID."""
        ach_id = int(achievement_id)
        graph_len = len(self.graph)
        if (
            ach_id in self._collection_bits_cache
            and getattr(self, "_collection_bits_sig", -1) == graph_len
        ):
            return [dict(b) for b in self._collection_bits_cache[ach_id]]

        if getattr(self, "_collection_bits_sig", -1) != graph_len:
            self._collection_bits_cache.clear()
            self._collection_bits_sig = graph_len

        sparql = """
        SELECT DISTINCT ?bit ?idx ?label ?itemId ?subtype ?zone ?waypoint ?hint WHERE {
            ?bit a priory:CollectionBitObjective ;
                 priory:forAchievementId ?achId ;
                 priory:bitIndex ?idx ;
                 rdfs:label ?label .
            OPTIONAL { ?bit priory:bitItemId ?itemId }
            OPTIONAL { ?bit priory:bitSubtype ?subtype }
            OPTIONAL { ?bit priory:zoneName ?zone }
            OPTIONAL { ?bit priory:waypointName ?waypoint }
            OPTIONAL { ?bit priory:acquisitionHint ?hint }
        }
        """
        rows = self.query(sparql, init_bindings={"achId": Literal(ach_id)})
        sorted_rows = sorted(
            rows,
            key=lambda r: (
                int(r["idx"]) if r.get("idx") is not None else 999,
                str(r.get("label", "")),
            ),
        )
        bits: List[Dict[str, Any]] = []
        seen_indices: set[int] = set()
        for r in sorted_rows:
            b_idx = int(r["idx"])
            if b_idx in seen_indices:
                continue
            seen_indices.add(b_idx)
            bits.append({
                "bit_index": b_idx,
                "item_id": int(r["itemId"]) if r.get("itemId") is not None else None,
                "name": str(r["label"]),
                "subtype": str(r["subtype"]) if r.get("subtype") is not None else None,
                "zone": str(r["zone"]) if r.get("zone") is not None else None,
                "waypoint": str(r["waypoint"]) if r.get("waypoint") is not None else None,
                "hint": str(r.get("hint") or ""),
            })
        self._collection_bits_cache[ach_id] = bits
        return [dict(b) for b in bits]

    def get_precursor_collection_bit_breakdown(
        self,
        item_id: int,
        account_achievements: Optional[Dict[int, Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Resolves Hobbs collection stages for a weapon or precursor ID and breaks down completed vs missing bits."""
        target_id = int(item_id)
        catalog = self.get_legendary_and_precursor_catalog()
        hobbs_collections: Dict[int, List[Dict[str, Any]]] = catalog.get("hobbs_collections", {})

        stages = hobbs_collections.get(target_id)
        if not stages:
            gen1_weaps = catalog.get("gen1_weapons", {})
            gen2_weaps = catalog.get("gen2_weapons", {})
            prec_to_weap = catalog.get("precursor_to_weapon", {})
            if target_id in gen1_weaps:
                prec_id = int(gen1_weaps[target_id].get("precursor_id") or 0)
                stages = hobbs_collections.get(prec_id)
            elif target_id in gen2_weaps:
                prec_id = int(gen2_weaps[target_id].get("precursor_id") or 0)
                stages = hobbs_collections.get(prec_id)
            elif target_id in prec_to_weap:
                weap_id = int(prec_to_weap[target_id])
                stages = hobbs_collections.get(weap_id)

        if not stages:
            return []

        acct_achs = account_achievements or {}
        breakdown: List[Dict[str, Any]] = []

        for stage in sorted(stages, key=lambda s: int(s["tier"])):
            tier_num = int(stage["tier"])
            ach_id = int(stage["id"])
            stage_name = str(stage["name"])
            bits_total = int(stage["bits_total"])
            mastery_name = str(stage.get("mastery_name") or "")
            candidate_ach_ids: List[int] = list(stage.get("ach_ids") or ([ach_id] if ach_id else []))

            all_bits = self.get_collection_bits(ach_id)
            if not all_bits:
                for alt_aid in candidate_ach_ids:
                    if alt_aid != ach_id:
                        all_bits = self.get_collection_bits(int(alt_aid))
                        if all_bits:
                            ach_id = int(alt_aid)
                            break

            ach_prog: Dict[str, Any] = {}
            for cand_id in [ach_id] + [int(x) for x in candidate_ach_ids if int(x) != ach_id]:
                prog = acct_achs.get(cand_id)
                if prog is None:
                    prog = acct_achs.get(str(cand_id))  # type: ignore[arg-type]
                if isinstance(prog, dict) and prog:
                    ach_prog = prog
                    break

            is_done_flag = bool(ach_prog.get("done", False))
            raw_bits = ach_prog.get("bits")
            current_val = ach_prog.get("current")

            if is_done_flag or (raw_bits is None and current_val is not None and int(current_val) >= bits_total > 0):
                is_complete = True
                completed_bits = [dict(b) for b in all_bits]
                missing_bits: List[Dict[str, Any]] = []
                bits_done = bits_total
            elif raw_bits is not None:
                done_indices = {int(b) for b in raw_bits}
                if all_bits:
                    completed_bits = [dict(b) for b in all_bits if int(b["bit_index"]) in done_indices]
                    missing_bits = [dict(b) for b in all_bits if int(b["bit_index"]) not in done_indices]
                    bits_done = len(completed_bits)
                else:
                    completed_bits = []
                    missing_bits = []
                    bits_done = min(len(done_indices), bits_total)
                if current_val is not None and not all_bits:
                    bits_done = max(bits_done, min(int(current_val), bits_total))
                is_complete = bits_done >= bits_total and bits_total > 0
                if is_complete:
                    missing_bits = []
            else:
                completed_bits = []
                missing_bits = [dict(b) for b in all_bits]
                bits_done = min(int(current_val), bits_total) if current_val is not None else 0
                is_complete = bits_done >= bits_total and bits_total > 0
                if is_complete:
                    completed_bits = [dict(b) for b in all_bits]
                    missing_bits = []

            breakdown.append({
                "tier": tier_num,
                "achievement_id": ach_id,
                "name": stage_name,
                "mastery_name": mastery_name,
                "bits_total": bits_total,
                "bits_done": bits_done,
                "is_complete": is_complete,
                "completed_bits": completed_bits,
                "missing_bits": missing_bits,
            })

        return breakdown



