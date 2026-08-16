"""Account-wide Legendary Readiness Ranker.

Evaluates all known Legendary items in the Knowledge Graph against a player's live account snapshot,
accounting for owned items, Bank Choice Chests / Starter Kits, and materials to rank which legendaries
the player is closest to crafting.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from rdflib import Literal
from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine, AccountState, AccountDiffReport


class LegendaryRankingItem(BaseModel):
    """Ranked assessment of a single legendary item for a player account."""
    gw2_id: int
    name: str
    item_type: str
    subtype: Optional[str] = None
    chat_code: Optional[str] = None
    is_already_unlocked: bool = False
    readiness_pct: float
    starter_kit_eligible: bool = False
    starter_kit_name: Optional[str] = None
    precursor_status: str = "Missing"
    missing_materials_count: int = 0
    top_missing_items: List[str] = Field(default_factory=list)
    estimated_remaining_gold: float = 0.0


class AccountRanker:
    """Ranks all legendary items by player account readiness and remaining cost."""

    def __init__(self, graph_store: PrioryGraphStore, diff_engine: Optional[AccountDiffEngine] = None):
        self.store = graph_store
        self.diff_engine = diff_engine or AccountDiffEngine(graph_store)

    def get_all_legendaries_in_graph(self) -> List[Dict[str, Any]]:
        """Retrieves all legendary items from the Knowledge Graph."""
        sparql = """
        SELECT DISTINCT ?item ?gw2Id ?label ?weaponTypeLabel ?chatCode WHERE {
            ?item a ?type ;
                  priory:gw2Id ?gw2Id ;
                  rdfs:label ?label .
            FILTER (?type IN (
                priory:LegendaryWeapon,
                priory:LegendaryArmor,
                priory:LegendaryTrinket,
                priory:LegendaryRelic,
                priory:LegendarySigil,
                priory:LegendaryRune
            ))
            OPTIONAL {
                ?item priory:hasWeaponType ?wt .
                ?wt skos:prefLabel ?weaponTypeLabel .
            }
            OPTIONAL { ?item priory:chatCode ?chatCode }
        } ORDER BY ?label
        """
        results = self.store.query(sparql)
        items = []
        seen_ids = set()
        for r in results:
            iid = r.get("gw2Id")
            if iid and iid not in seen_ids:
                seen_ids.add(iid)
                items.append({
                    "gw2Id": int(iid),
                    "label": r.get("label", "Unknown Legendary"),
                    "weaponType": r.get("weaponTypeLabel"),
                    "chatCode": r.get("chatCode")
                })
        return items

    def rank_all_legendaries(
        self,
        account: AccountState,
        tp_prices: Optional[Dict[int, float]] = None,
        top_n: int = 10,
        exclude_unlocked: bool = True
    ) -> List[LegendaryRankingItem]:
        """Evaluates and ranks all legendary items against the player account.
        
        Args:
            account: Player's live AccountState snapshot.
            tp_prices: Optional dict mapping GW2 item IDs to live TP prices.
            top_n: Number of top closest items to return.
            exclude_unlocked: Whether to exclude already owned Armory legendaries.
        """
        legendaries = self.get_all_legendaries_in_graph()
        rankings: List[LegendaryRankingItem] = []

        # Default baseline price fallbacks for leaf materials (if no live TP feed)
        prices = tp_prices or {
            19721: 0.22,  # Ecto
            19675: 5.50,  # Clover (approx forge value)
            24277: 0.25,  # Dust
            24289: 0.40,  # Venom
            24295: 0.35,  # Blood
            24358: 0.20,  # Totem
            24283: 0.30,  # Scale
            24276: 0.30,  # Bone
            24288: 0.30,  # Fang
            24351: 0.30,  # Claw
            19684: 0.02,  # Mithril
            19685: 0.35,  # Orichalcum
        }

        for leg in legendaries:
            item_id = leg["gw2Id"]
            name = leg["label"]

            # 1. Check if already unlocked in Legendary Armory
            if account.has_legendary_unlocked(item_id):
                if not exclude_unlocked:
                    rankings.append(LegendaryRankingItem(
                        gw2_id=item_id,
                        name=name,
                        item_type="Legendary",
                        subtype=leg.get("weaponType"),
                        chat_code=leg.get("chatCode"),
                        is_already_unlocked=True,
                        readiness_pct=100.0,
                        precursor_status="Already in Legendary Armory",
                        estimated_remaining_gold=0.0
                    ))
                continue

            # 2. Run deterministic AccountDiff traversal
            report: AccountDiffReport = self.diff_engine.compute_diff(item_id, account)

            # 3. Check for Bank Starter Kit Eligibility
            # (Check if any owned container in bank unpacks into this weapon's precursor or gift)
            starter_kit_eligible = False
            starter_kit_name = None
            precursor_status = "Missing"

            # Check direct ingredients in graph to find precursor
            ingredients = self.store.get_direct_recipe_ingredients(item_id)
            for ing in ingredients:
                ing_id = ing.get("ingredientId")
                ing_label = ing.get("ingredientLabel", "")
                
                # Check if unpackable from bank
                if ing_id and self.diff_engine.is_unpackable_from_account(ing_id, account):
                    starter_kit_eligible = True
                    starter_kit_name = "Legendary Weapon Starter Kit (in Bank)"
                    precursor_status = f"Unpackable for 0g via Bank Starter Kit ({ing_label})"
                    break
                elif ing_id and account.total_item_count(ing_id) > 0:
                    precursor_status = f"Owned in Inventory/Bank ({ing_label})"
                elif "Gift of" not in ing_label and ing_label:
                    if precursor_status == "Missing":
                        precursor_status = f"Need {ing_label}"

            # 4. Calculate approximate remaining gold cost
            est_gold = 0.0
            for mat_name, qty in report.summary_missing_materials.items():
                if "Icy Runestone" in mat_name:
                    est_gold += qty * 1.0  # 1g vendor price
                elif "Glob of Ectoplasm" in mat_name:
                    est_gold += qty * prices.get(19721, 0.22)
                elif "Mystic Clover" in mat_name:
                    est_gold += qty * prices.get(19675, 5.50)
                elif any(t6 in mat_name for t6 in ["Blood", "Venom", "Totem", "Scale", "Bone", "Fang", "Claw", "Dust"]):
                    est_gold += qty * 0.32
                elif "Ore" in mat_name or "Ingot" in mat_name:
                    est_gold += qty * 0.10
                elif mat_name in [leg["label"], "Gift of Mastery", "Gift of Exploration", "Gift of Battle"]:
                    # Account bound / goal - 0 TP cost
                    pass
                else:
                    est_gold += qty * 0.25

            # If precursor is missing and NOT in starter kit, add typical Gen 1 TP precursor price (~150-250g)
            if not starter_kit_eligible and "Need" in precursor_status:
                est_gold += 200.0

            # 5. Compute Adjusted Readiness Score
            # If player has starter kit for this weapon, boost readiness significantly
            effective_readiness = report.overall_readiness_pct
            if starter_kit_eligible:
                effective_readiness = max(effective_readiness, 55.0)

            # Top missing materials
            top_missing = [
                f"{qty}x {mat}" for mat, qty in sorted(
                    report.summary_missing_materials.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:4]
            ]

            rankings.append(LegendaryRankingItem(
                gw2_id=item_id,
                name=name,
                item_type="Legendary",
                subtype=leg.get("weaponType"),
                chat_code=leg.get("chatCode"),
                is_already_unlocked=False,
                readiness_pct=round(effective_readiness, 1),
                starter_kit_eligible=starter_kit_eligible,
                starter_kit_name=starter_kit_name,
                precursor_status=precursor_status,
                missing_materials_count=sum(report.summary_missing_materials.values()),
                top_missing_items=top_missing,
                estimated_remaining_gold=round(est_gold, 1)
            ))

        # Sort:
        # 1. Starter kit eligible first (True first)
        # 2. Has expanded recipe DAG (missing_materials_count > 1 first)
        # 3. Readiness % desc
        # 4. Remaining gold asc
        rankings.sort(
            key=lambda x: (
                x.starter_kit_eligible,
                x.missing_materials_count > 1,
                x.readiness_pct,
                -x.estimated_remaining_gold
            ),
            reverse=True
        )

        return rankings[:top_n]
