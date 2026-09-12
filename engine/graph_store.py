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

        self._loaded = True
        return len(self.graph) - total_triples_before

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
