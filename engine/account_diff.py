"""Dynamic Overlay & Account Delta Engine for Project Priory.

Calculates the exact mathematical difference between a player's live account snapshot
(materials, bank, inventory, wallet, masteries, crafting levels) and a target item's dependency graph.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field
from rdflib import URIRef, Literal
from engine.graph_store import PrioryGraphStore


class AccountState(BaseModel):
    """Snapshot of a player's live account state fetched from GW2 REST API."""
    materials: Dict[int, int] = Field(default_factory=dict, description="Material storage: item_id -> count")
    bank: Dict[int, int] = Field(default_factory=dict, description="Bank storage: item_id -> count")
    inventory: Dict[int, int] = Field(default_factory=dict, description="Character inventories: item_id -> count")
    wallet: Dict[int, int] = Field(default_factory=dict, description="Wallet: currency_id -> count")
    disciplines: Dict[str, int] = Field(default_factory=dict, description="Discipline -> max rating level")
    unlocked_recipes: List[int] = Field(default_factory=list, description="List of unlocked recipe IDs")

    def total_item_count(self, item_id: int) -> int:
        """Returns aggregate count of an item across materials, bank, and inventories."""
        return (
            self.materials.get(item_id, 0) +
            self.bank.get(item_id, 0) +
            self.inventory.get(item_id, 0)
        )

    def total_currency_count(self, currency_id: int) -> int:
        """Returns aggregate count of a currency in wallet (plus any legacy physical token items)."""
        count = self.wallet.get(currency_id, 0)
        if currency_id == 35:
            count += self.total_item_count(78172)
        return count


class ItemRequirementNode(BaseModel):
    """A node in the resolved requirement graph."""
    item_id: int
    label: str
    required_quantity: int
    owned_quantity: int
    missing_quantity: int
    is_satisfied: bool
    is_account_bound: bool = True
    sub_requirements: List[ItemRequirementNode] = Field(default_factory=list)


class AccountDiffReport(BaseModel):
    """Complete diff report for a goal item against a player's account."""
    goal_item_id: int
    goal_item_name: str
    target_quantity: int = 1
    is_fully_satisfied: bool
    root_node: ItemRequirementNode
    missing_disciplines: List[Dict[str, Any]] = Field(default_factory=list)
    missing_currencies: Dict[str, int] = Field(default_factory=dict)
    summary_missing_materials: Dict[str, int] = Field(default_factory=dict)


class AccountDiffEngine:
    """Computes the difference between an account snapshot and a target item's dependency graph."""

    def __init__(self, graph_store: PrioryGraphStore):
        self.store = graph_store

    def compute_diff(
        self,
        goal_item_id: int,
        account: AccountState,
        target_quantity: int = 1
    ) -> AccountDiffReport:
        """Computes the full delta tree for a goal item with quantity multiplier."""
        goal_item = self.store.get_item_by_id(goal_item_id)
        goal_name = goal_item["label"] if goal_item else f"Item {goal_item_id}"

        summary_missing: Dict[str, int] = {}
        missing_currencies: Dict[str, int] = {}
        used_recipes: Set[str] = set()
        root_node = self._resolve_node(goal_item_id, target_quantity, account, summary_missing, missing_currencies, used_recipes)

        # Check required crafting disciplines for recipes actually in this goal's tree
        missing_disciplines = []
        for recipe_uri_str in used_recipes:
            disc_query = """
            SELECT ?recipe ?recipeLabel ?discipline ?rating WHERE {
                ?recipe a priory:DisciplineRecipe ;
                        priory:requiresDiscipline ?discipline ;
                        priory:requiresRating ?rating .
                OPTIONAL { ?recipe rdfs:label ?recipeLabel }
            }
            """
            for r in self.store.query(disc_query, init_bindings={"recipe": URIRef(recipe_uri_str)}):
                disc_name = str(r["discipline"]).split("/")[-1].lower()
                required_rating = r["rating"]
                current_rating = account.disciplines.get(disc_name, 0)
                if current_rating < required_rating:
                    missing_disciplines.append({
                        "discipline": disc_name,
                        "required_rating": required_rating,
                        "current_rating": current_rating,
                        "recipe": r.get("recipeLabel", "Unknown Recipe")
                    })

        return AccountDiffReport(
            goal_item_id=goal_item_id,
            goal_item_name=goal_name,
            target_quantity=target_quantity,
            is_fully_satisfied=root_node.is_satisfied,
            root_node=root_node,
            missing_disciplines=missing_disciplines,
            missing_currencies=missing_currencies,
            summary_missing_materials=summary_missing
        )

    def _resolve_node(
        self,
        item_id: int,
        multiplier: int,
        account: AccountState,
        summary_missing: Dict[str, int],
        missing_currencies: Dict[str, int],
        used_recipes: Optional[Set[str]] = None
    ) -> ItemRequirementNode:
        item_meta = self.store.get_item_by_id(item_id)
        label = item_meta["label"] if item_meta else f"Item {item_id}"
        is_bound = item_meta.get("isAccountBound", True) if item_meta else True

        owned = account.total_item_count(item_id)
        needed = multiplier
        missing = max(0, needed - owned)
        is_satisfied = (owned >= needed)

        node = ItemRequirementNode(
            item_id=item_id,
            label=label,
            required_quantity=needed,
            owned_quantity=owned,
            missing_quantity=missing,
            is_satisfied=is_satisfied,
            is_account_bound=is_bound
        )

        if not is_satisfied:
            # Add item's producedBy recipe to used_recipes
            if used_recipes is not None:
                rec_query = """
                SELECT ?recipe WHERE {
                    ?item priory:gw2Id ?gw2Id ;
                          priory:producedBy ?recipe .
                }
                """
                for r_row in self.store.query(rec_query, init_bindings={"gw2Id": Literal(item_id)}):
                    used_recipes.add(r_row["recipe"])

            # Check 1: Direct crafting recipe ingredients
            direct_ingredients = self.store.get_direct_recipe_ingredients(item_id)
            if direct_ingredients:
                for ing in direct_ingredients:
                    ing_id = ing["ingredientId"]
                    ing_qty = ing["quantity"] * missing
                    sub_node = self._resolve_node(ing_id, ing_qty, account, summary_missing, missing_currencies, used_recipes)
                    node.sub_requirements.append(sub_node)
                return node

            # Check 2: Vendor Exchange with Currency (e.g. Gift of Craftsmanship -> Provisioner Tokens)
            vendor_query = """
            SELECT ?curr ?currNotation ?currLabel ?requiredQty WHERE {
                ?item priory:gw2Id ?gw2Id ;
                      priory:acquiredVia ?path .
                ?path a priory:VendorExchangePath ;
                      priory:requiresCurrency ?curr ;
                      priory:requiredQuantity ?requiredQty .
                OPTIONAL { ?curr skos:notation ?currNotation }
                OPTIONAL { ?curr skos:prefLabel ?currLabel }
            } LIMIT 1
            """
            v_res = self.store.query(vendor_query, init_bindings={"gw2Id": Literal(item_id)})
            if v_res:
                v_info = v_res[0]
                curr_id = int(v_info.get("currNotation", 0))
                curr_label = v_info.get("currLabel", "Currency")
                total_curr_needed = int(v_info.get("requiredQty", 1)) * missing
                owned_curr = account.total_currency_count(curr_id)

                if owned_curr >= total_curr_needed:
                    node.is_satisfied = True
                    node.missing_quantity = 0
                    return node
                else:
                    curr_missing = total_curr_needed - owned_curr
                    missing_currencies[curr_label] = missing_currencies.get(curr_label, 0) + curr_missing
                    summary_missing[label] = summary_missing.get(label, 0) + missing
                    return node

            # Check 3: Leaf crafting material
            summary_missing[label] = summary_missing.get(label, 0) + missing

        return node
