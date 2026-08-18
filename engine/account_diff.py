"""Account Diff Engine.

Calculates the deterministic difference between a player's live account state
and the recursive ingredient requirements of any item in the Knowledge Graph.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from rdflib import Literal, URIRef
from engine.graph_store import PrioryGraphStore


@dataclass
class WizardVaultListing:
    """Represents a Wizard's Vault shop listing with purchase status."""
    id: int
    item_id: int
    item_count: int = 1
    listing_type: str = "Normal"
    cost: int = 0
    purchased: int = 0
    purchase_limit: Optional[int] = None

    @property
    def remaining_purchases(self) -> int:
        if self.purchase_limit is None:
            return 999999
        return max(0, self.purchase_limit - self.purchased)

    @property
    def is_sold_out(self) -> bool:
        return self.purchase_limit is not None and self.purchased >= self.purchase_limit


@dataclass
class AccountState:
    """Represents a player's live account snapshot from the GW2 API."""
    materials: Dict[int, int] = field(default_factory=dict)
    bank: Dict[int, int] = field(default_factory=dict)
    inventory: Dict[int, int] = field(default_factory=dict)
    wallet: Dict[int, int] = field(default_factory=dict)
    legendary_armory: Dict[int, int] = field(default_factory=dict)
    disciplines: Dict[str, int] = field(default_factory=dict)
    achievements: Dict[int, int] = field(default_factory=dict)
    completed_achievements: Set[int] = field(default_factory=set)
    masteries: Dict[int, int] = field(default_factory=dict)
    wizards_vault_listings: Dict[int, WizardVaultListing] = field(default_factory=dict)

    def total_item_count(self, item_id: int) -> int:
        """Aggregates an item's count across materials, bank, bags, and legendary armory."""
        return (
            self.materials.get(item_id, 0) +
            self.bank.get(item_id, 0) +
            self.inventory.get(item_id, 0) +
            self.legendary_armory.get(item_id, 0)
        )

    def total_currency_count(self, currency_id: int) -> int:
        """Returns total owned amount of a wallet currency by its API ID."""
        return self.wallet.get(currency_id, 0)

    def has_legendary_unlocked(self, item_id: int) -> bool:
        """Returns True if the item is unlocked in the Legendary Armory."""
        return self.legendary_armory.get(item_id, 0) > 0

    def wizards_vault_remaining(self, item_id: int) -> Optional[int]:
        """Returns the number of remaining purchases for a Wizard's Vault item, or None if not listed."""
        listing = self.wizards_vault_listings.get(item_id)
        if listing:
            return listing.remaining_purchases
        return None

    def is_wizards_vault_sold_out(self, item_id: int) -> bool:
        """Returns True if the item is listed in the Wizard's Vault and sold out."""
        listing = self.wizards_vault_listings.get(item_id)
        if listing:
            return listing.is_sold_out
        return False


@dataclass
class ItemRequirementNode:
    """A node in the recursive recipe dependency tree."""
    item_id: int
    label: str
    required_quantity: int
    owned_quantity: int
    missing_quantity: int
    is_satisfied: bool
    is_account_bound: bool = False
    sub_requirements: List[ItemRequirementNode] = field(default_factory=list)


@dataclass
class AccountDiffReport:
    """Final calculated diff report for a target crafting goal."""
    goal_item_id: int
    goal_item_name: str
    target_quantity: int
    overall_readiness_pct: float
    is_fully_satisfied: bool
    root_node: ItemRequirementNode
    summary_missing_materials: Dict[str, int] = field(default_factory=dict)
    summary_missing_currencies: Dict[str, int] = field(default_factory=dict)
    missing_disciplines: List[Dict[str, Any]] = field(default_factory=list)


class AccountDiffEngine:
    """Recursive graph traversal engine for computing inventory deltas and progression gaps."""

    def __init__(self, graph_store: PrioryGraphStore):
        self.store = graph_store

    def compute_diff(self, goal_item_id: int, account: AccountState, target_quantity: int = 1) -> AccountDiffReport:
        """Recursively evaluates the delta between the goal item's recipe DAG and the account."""
        item_meta = self.store.get_item_by_id(goal_item_id)
        goal_name = item_meta["label"] if item_meta else f"Item {goal_item_id}"

        summary_missing: Dict[str, int] = {}
        missing_currencies: Dict[str, int] = {}
        used_recipes: Set[str] = set()
        visited: Set[int] = set()

        root_node = self._resolve_node(
            goal_item_id,
            target_quantity,
            account,
            summary_missing,
            missing_currencies,
            used_recipes,
            visited
        )

        missing_disciplines = self._evaluate_discipline_requirements(used_recipes, account)

        # Calculate exact tree units owned vs needed across all branches
        total_owned_units, total_needed_units = self._calculate_tree_units(root_node)
        if root_node.is_satisfied:
            readiness = 100.0
        else:
            readiness = max(0.0, min(100.0, (total_owned_units / max(1, total_needed_units)) * 100.0))

        is_fully_satisfied = (
            root_node.is_satisfied or 
            (len(summary_missing) == 0 and len(missing_currencies) == 0 and len(missing_disciplines) == 0)
        )

        return AccountDiffReport(
            goal_item_id=goal_item_id,
            goal_item_name=goal_name,
            target_quantity=target_quantity,
            overall_readiness_pct=round(readiness, 1),
            is_fully_satisfied=is_fully_satisfied,
            root_node=root_node,
            summary_missing_materials=summary_missing,
            summary_missing_currencies=missing_currencies,
            missing_disciplines=missing_disciplines
        )

    def _calculate_tree_units(self, node: ItemRequirementNode) -> Tuple[int, int]:
        """Recursively calculates (owned_credited_units, total_required_units) across DAG nodes."""
        if not node.sub_requirements:
            needed = node.required_quantity
            owned = min(needed, node.owned_quantity) if not node.is_satisfied else needed
            return (owned, needed)

        if node.is_satisfied:
            return (node.required_quantity, node.required_quantity)

        total_owned = 0
        total_needed = 0
        for child in node.sub_requirements:
            c_owned, c_needed = self._calculate_tree_units(child)
            total_owned += c_owned
            total_needed += c_needed

        return (total_owned, max(1, total_needed))

    def is_unpackable_from_account(self, item_id: int, account: AccountState) -> Optional[str]:
        """Checks if an item can be obtained from an owned container (e.g. Starter Kit in bank)."""
        container_query = """
        SELECT ?containerId ?containerLabel WHERE {
            ?container priory:unpacksInto ?item ;
                       priory:gw2Id ?containerId .
            ?item priory:gw2Id ?gw2Id .
            OPTIONAL { ?container rdfs:label ?containerLabel }
        }
        """
        c_res = self.store.query(container_query, init_bindings={"gw2Id": Literal(item_id)})
        for c_row in c_res:
            c_id = int(c_row["containerId"])
            if account.total_item_count(c_id) > 0:
                return c_row.get("containerLabel", "Choice Chest in Bank")
        return None

    def _resolve_node(
        self,
        item_id: int,
        multiplier: int,
        account: AccountState,
        summary_missing: Dict[str, int],
        missing_currencies: Dict[str, int],
        used_recipes: Optional[Set[str]] = None,
        visited: Optional[Set[int]] = None
    ) -> ItemRequirementNode:
        if visited is None:
            visited = set()

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

        if not is_satisfied and item_id not in visited:
            branch_visited = visited.copy()
            branch_visited.add(item_id)

            # Check 0: Container Unpack Path (e.g. Starter Kit in Bank or Inventory)
            container_name = self.is_unpackable_from_account(item_id, account)
            if container_name:
                node.is_satisfied = True
                node.missing_quantity = 0
                node.label = f"{label} (Unpackable from {container_name})"
                return node

            # Check 1: Direct crafting recipes producing this item
            rec_query = """
            SELECT DISTINCT ?recipe ?discipline ?requiredRating WHERE {
                ?item priory:gw2Id ?gw2Id ;
                      priory:producedBy ?recipe .
                OPTIONAL { ?recipe priory:requiresDiscipline ?discipline }
                OPTIONAL { 
                    ?recipe priory:requiredRating ?requiredRating 
                }
                OPTIONAL { 
                    ?recipe priory:requiresRating ?requiredRating 
                }
            }
            """
            recipes = self.store.query(rec_query, init_bindings={"gw2Id": Literal(item_id)})

            if recipes:
                # Multi-discipline preference: Select recipe matching player's active high-level discipline
                selected_recipe_str = None
                if len(recipes) > 1 and account.disciplines:
                    for r in recipes:
                        disc_raw = r.get("discipline", "")
                        disc_name = disc_raw.split("/")[-1].lower() if disc_raw else ""
                        req_rating = int(r.get("requiredRating", 0)) if r.get("requiredRating") is not None else 0
                        if disc_name and account.disciplines.get(disc_name, 0) >= req_rating:
                            selected_recipe_str = r["recipe"]
                            break

                if not selected_recipe_str:
                    selected_recipe_str = recipes[0]["recipe"]

                if used_recipes is not None:
                    used_recipes.add(selected_recipe_str)

                # Fetch ingredients for the selected recipe
                ing_query = """
                SELECT DISTINCT ?ingredientId ?ingredientLabel ?quantity WHERE {
                    ?recipe priory:hasIngredientRequirement ?req .
                    ?req priory:requiresItem ?ingredient ;
                         priory:requiredQuantity ?quantity .
                    ?ingredient priory:gw2Id ?ingredientId ;
                                rdfs:label ?ingredientLabel .
                }
                """
                ingredients = self.store.query(ing_query, init_bindings={"recipe": URIRef(selected_recipe_str)})
                if ingredients:
                    for ing in ingredients:
                        ing_id = int(ing["ingredientId"])
                        ing_qty = int(ing["quantity"]) * missing
                        sub_node = self._resolve_node(
                            ing_id, ing_qty, account, summary_missing, missing_currencies, used_recipes, branch_visited
                        )
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
                curr_not = v_info.get("currNotation")
                try:
                    curr_id = int(curr_not) if curr_not is not None else 0
                except (ValueError, TypeError):
                    curr_id = 0
                curr_label = v_info.get("currLabel", "Currency")
                total_curr_needed = int(v_info.get("requiredQty", 1)) * missing
                owned_curr = account.total_currency_count(curr_id) if curr_id > 0 else 0

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

    def _evaluate_discipline_requirements(self, used_recipes: Set[str], account: AccountState) -> List[Dict[str, Any]]:
        """Determines if the account lacks required crafting disciplines for used recipes."""
        missing = []
        if not used_recipes:
            return missing

        disc_query = """
        SELECT DISTINCT ?recipe ?discipline ?requiredRating WHERE {
            ?recipe a priory:DisciplineRecipe ;
                    priory:requiresDiscipline ?discipline .
            OPTIONAL { ?recipe priory:requiredRating ?requiredRating }
            OPTIONAL { ?recipe priory:requiresRating ?requiredRating }
        }
        """
        for row in self.store.query(disc_query):
            rec_uri = row["recipe"]
            if rec_uri in used_recipes:
                disc_uri = row.get("discipline", "")
                disc_name = disc_uri.split("/")[-1].lower() if disc_uri else "unknown"
                req_rating = int(row.get("requiredRating", 0)) if row.get("requiredRating") is not None else 0
                player_rating = account.disciplines.get(disc_name, 0)

                if player_rating < req_rating:
                    missing.append({
                        "discipline": disc_name,
                        "required_rating": req_rating,
                        "current_rating": player_rating
                    })
        return missing
