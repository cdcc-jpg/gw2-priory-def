"""Priory Graph Store.

Manages the RDF Knowledge Graph, loads OWL schemas, SKOS reference vocabularies,
and instance graphs, and provides SPARQL query interfaces for recipe trees and acquisition options.
"""

from __future__ import annotations
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
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


class PrioryGraphStore:
    """In-memory RDF Graph Store powered by RDFLib Dataset with SPARQL 1.1 and Named Graph support."""

    def __init__(self, ref_repo_path: Optional[Path] = None, def_repo_path: Optional[Path] = None):
        self.dataset = Dataset(default_union=True)
        self.graph = self.dataset.default_graph
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
