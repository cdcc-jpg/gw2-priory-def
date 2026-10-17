"""Multi-Weapon Precursor Collection & Crafting Chain Ingestor for Project Priory.

Combines GW2SMWClient (Semantic MediaWiki API) and GW2ApiClient (Official GW2 v2 API)
to generate W3C OWL 2 DL (HermiT)-consistent and SHACL-validated RDF/Turtle graphs for
Gen 1 (3-tier) and Gen 2 (4-tier) precursor weapon collections and crafting chains.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

import rdflib
from rdflib import Literal, Namespace, OWL, RDF, RDFS, SKOS, URIRef, XSD

from ingestion.gw2_api import GW2ApiClient
from ingestion.smw_client import (
    CANONICAL_PRECURSOR_CHAINS,
    DISCIPLINE,
    GW2SMWClient,
    ITEM,
    PRECURSOR_ALIASES,
    PRIORY,
    RARITY,
    RECIPE,
    WEAPON,
)

DEFAULT_MULTI_WEAPON_PRECURSORS: List[str] = [
    "Dawn",
    "Zap",
    "The Legend",
    "The Living Ravens",
    "The Mechanism",
    "Prototype",
]


class PrecursorCollectionIngestor:
    """Ingests multi-tier precursor collections and crafting recipes into OWL 2 DL / SHACL RDF."""

    def __init__(
        self,
        smw_client: Optional[GW2SMWClient] = None,
        api_client: Optional[GW2ApiClient] = None,
        instances_dir: Optional[Union[str, Path]] = None,
        offline: bool = True,
    ):
        self.smw_client = smw_client or GW2SMWClient(offline=offline)
        self.api_client = api_client or GW2ApiClient()
        if instances_dir is None:
            repo_root = Path(__file__).resolve().parent.parent
            self.instances_dir = repo_root / "ontology" / "instances"
        else:
            self.instances_dir = Path(instances_dir)

    def scan_existing_ontology_constraints(
        self, exclude_filenames: Optional[Set[str]] = None
    ) -> Dict[str, Set[int]]:
        """Scans existing Turtle files in ontology/instances to prevent duplicate functional triples.

        Specifically guards against:
        1. Emitting a second `priory:producedBy` on an item that already has one (`ItemShape` has `sh:maxCount 1`).
        2. Emitting a second `rdfs:label` on an item that already has `priory:armoryMaxCap` (which would duplicate
           SPARQL rows in Competency Question 5).
        """
        excluded = exclude_filenames or {"multi_weapon_precursor_collections.ttl"}
        items_with_produced_by: Set[int] = set()
        items_with_label: Set[int] = set()
        items_with_armory_cap: Set[int] = set()

        if not self.instances_dir.exists():
            return {
                "produced_by": items_with_produced_by,
                "label": items_with_label,
                "armory_cap": items_with_armory_cap,
            }

        item_prefix = str(ITEM)
        for ttl_path in sorted(self.instances_dir.rglob("*.ttl")):
            if ttl_path.name in excluded:
                continue
            g = rdflib.Graph()
            try:
                g.parse(str(ttl_path), format="turtle")
            except Exception:
                continue

            for subj in g.subjects(PRIORY.producedBy, None):
                s_str = str(subj)
                if s_str.startswith(item_prefix):
                    tail = s_str[len(item_prefix):]
                    if tail.isdigit():
                        items_with_produced_by.add(int(tail))

            for subj in g.subjects(RDFS.label, None):
                s_str = str(subj)
                if s_str.startswith(item_prefix):
                    tail = s_str[len(item_prefix):]
                    if tail.isdigit():
                        items_with_label.add(int(tail))

            for subj in g.subjects(PRIORY.armoryMaxCap, None):
                s_str = str(subj)
                if s_str.startswith(item_prefix):
                    tail = s_str[len(item_prefix):]
                    if tail.isdigit():
                        items_with_armory_cap.add(int(tail))

        return {
            "produced_by": items_with_produced_by,
            "label": items_with_label,
            "armory_cap": items_with_armory_cap,
        }

    def _create_base_graph(self) -> rdflib.Graph:
        """Creates an RDF graph with standard Priory namespace bindings and OWL 2 DL property declarations."""
        g = rdflib.Graph()
        g.bind("priory", PRIORY)
        g.bind("item", ITEM)
        g.bind("recipe", RECIPE)
        g.bind("discipline", DISCIPLINE)
        g.bind("rarity", RARITY)
        g.bind("weapon", WEAPON)
        g.bind("owl", OWL)
        g.bind("rdfs", RDFS)
        g.bind("skos", SKOS)
        g.bind("xsd", XSD)

        # Ensure all helper/alias properties are strictly typed for OWL 2 DL (HermiT) consistency
        object_props = [
            PRIORY.precursorTo,
            PRIORY.hasAcquisitionPath,
            PRIORY.requiresCraftingDiscipline,
            PRIORY.hasCollectionStep,
        ]
        for op in object_props:
            g.add((op, RDF.type, OWL.ObjectProperty))

        datatype_props = [
            PRIORY.requiresDisciplineRating,
            PRIORY.hasQuantity,
            PRIORY.stepIndex,
            PRIORY.stepObjective,
        ]
        for dp in datatype_props:
            g.add((dp, RDF.type, OWL.DatatypeProperty))

        return g

    def _add_shared_ascended_materials(
        self,
        g: rdflib.Graph,
        existing_constraints: Dict[str, Set[int]],
    ) -> None:
        """Ensures the shared time-gated Ascended materials and Memories of Battle exist as SHACL-valid Items."""
        shared_materials = [
            (46738, "Deldrimor Steel Ingot", "Ascended", True),
            (46736, "Spiritwood Plank", "Ascended", True),
            (46739, "Elonian Leather Square", "Ascended", True),
            (46741, "Bolt of Damask", "Ascended", True),
            (79418, "Memory of Battle", "Fine", False),
        ]
        for mat_id, mat_name, rarity_name, is_time_gated in shared_materials:
            mat_uri = ITEM[str(mat_id)]
            g.add((mat_uri, RDF.type, OWL.NamedIndividual))
            g.add((mat_uri, RDF.type, PRIORY.Item))
            g.add((mat_uri, RDF.type, PRIORY.CraftingMaterial))
            if is_time_gated:
                g.add((mat_uri, RDF.type, PRIORY.AscendedMaterial))
            if mat_id not in existing_constraints["armory_cap"]:
                g.add((mat_uri, RDFS.label, Literal(mat_name, lang="en")))
            g.add((mat_uri, PRIORY.gw2Id, Literal(mat_id, datatype=XSD.integer)))
            g.add((mat_uri, PRIORY.hasRarity, RARITY[rarity_name]))
            g.add((mat_uri, PRIORY.isAccountBound, Literal(False, datatype=XSD.boolean)))

    def ingest_precursor_chain(
        self,
        precursor_name: str,
        graph: Optional[rdflib.Graph] = None,
        existing_constraints: Optional[Dict[str, Set[int]]] = None,
    ) -> rdflib.Graph:
        """Ingests a single multi-tier precursor chain into the provided (or new) RDF graph."""
        g = graph if graph is not None else self._create_base_graph()
        constraints = (
            existing_constraints
            if existing_constraints is not None
            else self.scan_existing_ontology_constraints()
        )
        self._add_shared_ascended_materials(g, constraints)

        tiers = self.smw_client.fetch_precursor_collection_tiers(precursor_name)
        if not tiers:
            raise ValueError(f"No precursor collection tiers found for '{precursor_name}'")

        prev_collection_uri: Optional[URIRef] = None
        for tier_data in tiers:
            tier_num = int(tier_data["tier"])
            item_id = int(tier_data["item_id"])
            item_name = str(tier_data["item_name"])
            recipe_id = str(tier_data["recipe_id"])
            collection_id = str(tier_data["collection_id"])
            collection_title = str(tier_data["collection_title"])
            discipline_name = str(tier_data["discipline"])
            required_rating = int(tier_data["required_rating"])
            is_final = bool(tier_data["is_final_precursor"])
            is_account_bound = bool(tier_data["is_account_bound"])
            precursor_type = str(tier_data["precursor_type"])
            weapon_type = str(tier_data.get("weapon_type", "Weapon"))
            legendary_id = int(tier_data["legendary_item_id"])
            legendary_name = str(tier_data["legendary_name"])

            item_uri = ITEM[str(item_id)]
            recipe_uri = RECIPE[recipe_id]
            collection_uri = PRIORY[collection_id]
            legendary_uri = ITEM[str(legendary_id)]
            discipline_uri = DISCIPLINE[discipline_name]

            # 1. AchievementCollectionPath node & steps
            g.add((collection_uri, RDF.type, OWL.NamedIndividual))
            g.add((collection_uri, RDF.type, PRIORY.AchievementCollectionPath))
            g.add((collection_uri, RDFS.label, Literal(collection_title, lang="en")))
            g.add((collection_uri, PRIORY.unlocksRecipe, recipe_uri))
            if prev_collection_uri is not None:
                g.add((collection_uri, PRIORY.requiresCollection, prev_collection_uri))
            prev_collection_uri = collection_uri

            steps = self.smw_client.fetch_collection_achievement_steps(collection_title)
            for step in steps:
                step_idx = int(step["step_index"])
                step_uri = PRIORY[f"{collection_id}_step{step_idx}"]
                g.add((step_uri, RDF.type, OWL.NamedIndividual))
                g.add((step_uri, RDFS.label, Literal(str(step["step_name"]), lang="en")))
                g.add((step_uri, PRIORY.stepIndex, Literal(step_idx, datatype=XSD.integer)))
                g.add((step_uri, PRIORY.stepObjective, Literal(str(step["objective"]), lang="en")))
                g.add((collection_uri, PRIORY.hasCollectionStep, step_uri))

            # 2. Tier Precursor Item node
            g.add((item_uri, RDF.type, OWL.NamedIndividual))
            g.add((item_uri, RDF.type, PRIORY.Item))
            g.add((item_uri, RDF.type, PRIORY.PrecursorWeapon))
            g.add((item_uri, PRIORY.gw2Id, Literal(item_id, datatype=XSD.integer)))

            # Avoid adding a second rdfs:label if the item already has armoryMaxCap in another TTL file
            if item_id in constraints["armory_cap"] and item_id in constraints["label"]:
                g.add((item_uri, SKOS.altLabel, Literal(item_name, lang="en")))
            else:
                g.add((item_uri, RDFS.label, Literal(item_name, lang="en")))

            if item_id not in constraints["armory_cap"]:
                g.add((item_uri, PRIORY.hasRarity, RARITY.Exotic))
                g.add((item_uri, PRIORY.isAccountBound, Literal(is_account_bound, datatype=XSD.boolean)))
            g.add((item_uri, PRIORY.hasWeaponType, WEAPON[weapon_type]))
            g.add((item_uri, PRIORY.hasPrecursorTier, Literal(tier_num, datatype=XSD.integer)))
            g.add((item_uri, PRIORY.hasPrecursorType, PRIORY[precursor_type]))
            g.add((item_uri, PRIORY.acquiredVia, collection_uri))
            g.add((item_uri, PRIORY.acquiredVia, recipe_uri))
            g.add((item_uri, PRIORY.hasAcquisitionPath, collection_uri))
            g.add((item_uri, PRIORY.hasAcquisitionPath, recipe_uri))

            # Guard against duplicate priory:producedBy (ItemShape enforces sh:maxCount 1)
            if item_id not in constraints["produced_by"]:
                g.add((item_uri, PRIORY.producedBy, recipe_uri))
                constraints["produced_by"].add(item_id)

            # Link final precursor to its target Legendary Weapon
            if is_final and legendary_id > 0:
                g.add((item_uri, PRIORY.isPrecursorOf, legendary_uri))
                g.add((item_uri, PRIORY.precursorTo, legendary_uri))
                # Ensure target Legendary Weapon is typed as an Item for SHACL / OWL 2 DL
                g.add((legendary_uri, RDF.type, OWL.NamedIndividual))
                g.add((legendary_uri, RDF.type, PRIORY.Item))
                g.add((legendary_uri, RDF.type, PRIORY.LegendaryWeapon))
                g.add((legendary_uri, PRIORY.gw2Id, Literal(legendary_id, datatype=XSD.integer)))
                if legendary_id not in constraints["label"]:
                    g.add((legendary_uri, RDFS.label, Literal(legendary_name, lang="en")))

            # 3. DisciplineRecipe node & IngredientRequirements
            g.add((recipe_uri, RDF.type, OWL.NamedIndividual))
            g.add((recipe_uri, RDF.type, PRIORY.Recipe))
            g.add((recipe_uri, RDF.type, PRIORY.DisciplineRecipe))
            g.add((recipe_uri, RDFS.label, Literal(f"Recipe: {item_name}", lang="en")))
            g.add((recipe_uri, PRIORY.producesItem, item_uri))
            g.add((recipe_uri, PRIORY.outputQuantity, Literal(1, datatype=XSD.integer)))
            g.add((recipe_uri, PRIORY.requiresDiscipline, discipline_uri))
            g.add((recipe_uri, PRIORY.requiresCraftingDiscipline, discipline_uri))
            g.add((recipe_uri, PRIORY.requiredRating, Literal(required_rating, datatype=XSD.integer)))
            g.add((recipe_uri, PRIORY.requiresDisciplineRating, Literal(required_rating, datatype=XSD.integer)))

            # Ensure the crafting discipline is typed as priory:CraftingDiscipline for SHACL class checking
            g.add((discipline_uri, RDF.type, OWL.NamedIndividual))
            g.add((discipline_uri, RDF.type, PRIORY.CraftingDiscipline))

            for ing in tier_data["ingredients"]:
                ing_item_id = int(ing["item_id"])
                ing_qty = int(ing["quantity"])
                ing_item_uri = ITEM[str(ing_item_id)]
                req_uri = RECIPE[f"req_{recipe_id}_{ing_item_id}"]

                g.add((recipe_uri, PRIORY.hasIngredientRequirement, req_uri))
                g.add((req_uri, RDF.type, OWL.NamedIndividual))
                g.add((req_uri, RDF.type, PRIORY.IngredientRequirement))
                g.add((req_uri, PRIORY.requiresItem, ing_item_uri))
                g.add((req_uri, PRIORY.requiredQuantity, Literal(ing_qty, datatype=XSD.integer)))
                g.add((req_uri, PRIORY.hasQuantity, Literal(ing_qty, datatype=XSD.integer)))

        return g

    def ingest_all_precursors(
        self,
        precursor_names: Optional[List[str]] = None,
    ) -> rdflib.Graph:
        """Ingests all specified multi-weapon precursor chains into a single unified RDF graph."""
        targets = precursor_names if precursor_names is not None else list(DEFAULT_MULTI_WEAPON_PRECURSORS)
        constraints = self.scan_existing_ontology_constraints()
        g = self._create_base_graph()
        self._add_shared_ascended_materials(g, constraints)

        for name in targets:
            self.ingest_precursor_chain(name, graph=g, existing_constraints=constraints)

        return g

    def export_turtle(
        self,
        output_path: Optional[Union[str, Path]] = None,
        precursor_names: Optional[List[str]] = None,
    ) -> Path:
        """Generates and serializes the multi-weapon precursor collections Turtle file."""
        if output_path is None:
            out_file = self.instances_dir / "shared" / "multi_weapon_precursor_collections.ttl"
        else:
            out_file = Path(output_path)

        out_file.parent.mkdir(parents=True, exist_ok=True)
        g = self.ingest_all_precursors(precursor_names=precursor_names)
        ttl_text = g.serialize(format="turtle")
        out_file.write_text(ttl_text, encoding="utf-8")
        return out_file


if __name__ == "__main__":
    ingestor = PrecursorCollectionIngestor(offline=True)
    generated_path = ingestor.export_turtle()
    print(f"Generated {generated_path}")
