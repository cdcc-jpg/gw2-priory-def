"""Unit tests for Currency-to-Material Optimization, Arbitrage Matrix, and Discipline Routing."""

import unittest
from engine.graph_store import PrioryGraphStore
from engine.account_diff import (
    AccountDiffEngine,
    AccountState,
    WizardVaultListing
)
from engine.path_solver import (
    PathSolver,
    ArbitrageReport,
    solve_buy_vs_craft_vs_vault,
    get_live_market_prices
)
from engine.character_graph import (
    route_crafting_discipline,
    encode_item_chat_link
)


class TestCurrencyOptimization(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store = PrioryGraphStore()
        cls.store.load_all()
        cls.diff_engine = AccountDiffEngine(cls.store)
        cls.solver = PathSolver(cls.store)

    def test_volatile_magic_and_acclaim_recommendations(self):
        """Verifies that solver recommends Trophy Shipments when player has Volatile Magic and Astral Acclaim."""
        account = AccountState(
            materials={19721: 100},  # missing T6
            wallet={
                45: 5000,  # 5,000 Volatile Magic (Currency 45)
                63: 500,   # 500 Astral Acclaim (Currency 63)
                3: 50      # 50 Laurels (Currency 3)
            }
        )
        report = self.diff_engine.compute_diff(goal_item_id=30704, account=account)
        plan = self.solver.solve_optimal_path(diff_report=report, account=account)

        # Check that T6 strategies contain Volatile Magic, Astral Acclaim, and Laurels
        strat_text = " ".join(plan.t6_strategies)
        self.assertIn("Volatile Magic Conversion", strat_text)
        self.assertIn("Wizard's Vault Acclaim", strat_text)
        self.assertIn("Laurel Merchant", strat_text)

    def test_twilight_arbitrage_report_comprehensive(self):
        """Verifies solve_buy_vs_craft_vs_vault on Twilight (30704) adhering to Wallace's 15% TP tax model."""
        live_prices = {
            30704: {"sells": {"unit_price": 28500000}, "buys": {"unit_price": 23500000}},  # Twilight (2,850g / 2,350g)
            29185: {"sells": {"unit_price": 1800000}, "buys": {"unit_price": 1500000}},    # Dusk (180g / 150g)
            19976: {"sells": {"unit_price": 19500}, "buys": {"unit_price": 18000}},        # Mystic Coin (1.95g)
            19721: {"sells": {"unit_price": 3000}, "buys": {"unit_price": 2800}},          # Glob of Ectoplasm (0.30g)
            24277: {"sells": {"unit_price": 1600}},                                         # Crystalline Dust
            24295: {"sells": {"unit_price": 2500}},                                         # Powerful Blood
            24294: {"sells": {"unit_price": 50}},                                           # Potent Blood (T5)
        }
        account = AccountState(
            materials={},
            bank={},
            characters=[],
            wallet={63: 0}
        )

        report = self.solver.solve_buy_vs_craft_vs_vault(
            goal_item_id=30704,
            live_prices=live_prices,
            account_state=account
        )

        self.assertIsInstance(report, ArbitrageReport)
        self.assertEqual(report.goal_item_id, 30704)
        self.assertEqual(report.goal_name, "Twilight")
        self.assertEqual(report.instant_buy_total, 28500000)
        self.assertEqual(report.buy_order_total, 23500000)

        # Wallace's 15% TP tax model: net_sell = int(buys.unit_price * 0.85)
        expected_net_sell = int(23500000 * 0.85)
        self.assertEqual(report.net_sell_if_sold, expected_net_sell)
        self.assertEqual(report.profit_margin_if_sold, expected_net_sell - report.craft_from_scratch_total)

        # Precursor Strategy (Dusk is not in Starter Kit, buy order 150g < Hobbs 210g)
        self.assertEqual(report.precursor_strategy["precursor_id"], 29185)
        self.assertEqual(report.precursor_strategy["precursor_name"], "Dusk")
        self.assertEqual(report.precursor_strategy["recommended_option"], "BUY_ORDER")
        self.assertEqual(report.precursor_strategy["buy_order_copper"], 1500000)

        # Clover Strategy (Mystic Forge EV = 3.2 MC + 3.2 Ecto = 3.2*19500 + 3.2*3000 = 62400 + 9600 = 72000 copper)
        expected_forge_clover = int(3.2 * 19500 + 3.2 * 3000)
        self.assertEqual(report.clover_strategy["mystic_forge"]["unit_gold_copper"], expected_forge_clover)
        expected_fractal_clover = int(1 * 19500 + 3 * 3000)
        self.assertEqual(report.clover_strategy["fractal_relics"]["unit_gold_copper"], expected_fractal_clover)

        # T6 Promotion Strategy across all 8 fine categories
        for cat in ["Blood", "Bone", "Claw", "Fang", "Scale", "Totem", "Venom", "Dust"]:
            self.assertIn(cat, report.t6_promotion_strategy)
            strat = report.t6_promotion_strategy[cat]
            self.assertIn(strat["recommended_action"], ["BUY_DIRECT", "PROMOTE_T5_FORGE"])
            self.assertGreater(strat["buy_direct_copper"], 0)
            self.assertGreater(strat["forge_promoted_copper"], 0)

        # Blood should be recommended for Forge Promotion due to cheap T5 (50 copper)
        self.assertEqual(report.t6_promotion_strategy["Blood"]["recommended_action"], "PROMOTE_T5_FORGE")

    def test_wizards_vault_starter_kit_priority_the_moot(self):
        """Verifies Wizard's Vault Starter Kit priority (1,200 Astral Acclaim) for The Moot (30692)."""
        live_prices = {
            30692: {"sells": {"unit_price": 20000000}, "buys": {"unit_price": 16000000}},
            29166: {"sells": {"unit_price": 600000}, "buys": {"unit_price": 450000}},  # The Energizer
        }
        account = AccountState(
            wallet={63: 1500}  # 1500 Astral Acclaim
        )

        report = solve_buy_vs_craft_vs_vault(
            goal_item_id=30692,
            live_prices=live_prices,
            account_state=account,
            graph_store=self.store
        )

        self.assertEqual(report.goal_item_id, 30692)
        self.assertEqual(report.precursor_strategy["precursor_id"], 29166)
        self.assertEqual(report.precursor_strategy["recommended_option"], "WIZARDS_VAULT")
        self.assertTrue(report.precursor_strategy["wizards_vault_available"])
        self.assertEqual(report.precursor_strategy["wizards_vault_acclaim"], 1200)

    def test_clover_strategy_vault_vs_fractals_vs_forge(self):
        """Verifies Clover Strategy priority: Wizard's Vault > Fractal Relics > Mystic Forge."""
        live_prices = {
            19976: {"sells": {"unit_price": 20000}},  # Mystic Coin 2g
            19721: {"sells": {"unit_price": 3000}},   # Ecto 0.3g
        }
        # Case A: Vault clovers available -> WIZARDS_VAULT
        account_vault_avail = AccountState(
            wizards_vault_listings={19675: WizardVaultListing(id=1, item_id=19675, cost=9, purchased=5, purchase_limit=20)}
        )
        rep_a = self.solver.solve_buy_vs_craft_vs_vault(30704, live_prices, account_vault_avail)
        self.assertEqual(rep_a.clover_strategy["recommended_option"], "WIZARDS_VAULT")

        # Case B: Vault clovers sold out, player has Fractal Relics -> FRACTAL_RELICS
        account_fractals = AccountState(
            wallet={7: 1000},  # 1,000 Fractal Relics (Currency 7)
            wizards_vault_listings={19675: WizardVaultListing(id=1, item_id=19675, cost=9, purchased=20, purchase_limit=20)}
        )
        rep_b = self.solver.solve_buy_vs_craft_vs_vault(30704, live_prices, account_fractals)
        self.assertEqual(rep_b.clover_strategy["recommended_option"], "FRACTAL_RELICS")
        self.assertTrue(rep_b.clover_strategy["wizards_vault"]["is_sold_out"])

        # Case C: Vault sold out, no Fractal Relics -> MYSTIC_FORGE
        account_forge = AccountState(
            wallet={7: 0},
            wizards_vault_listings={19675: WizardVaultListing(id=1, item_id=19675, cost=9, purchased=20, purchase_limit=20)}
        )
        rep_c = self.solver.solve_buy_vs_craft_vs_vault(30704, live_prices, account_forge)
        self.assertEqual(rep_c.clover_strategy["recommended_option"], "MYSTIC_FORGE")

    def test_multi_character_discipline_routing_and_fee_avoidance(self):
        """Verifies that discipline routing picks active characters (Kerling/Legacy) avoiding 50 silver fees."""
        # Character roster:
        # 1. Kerling: Weaponsmith 500 (active), Armorsmith 500 (active), Artificer 403 (inactive)
        # 2. Legacy Of Harathi: Artificer 404 (active), Huntsman 500 (active)
        account = AccountState(
            characters=[
                {
                    "name": "Kerling",
                    "crafting": [
                        {"discipline": "Weaponsmith", "rating": 500, "active": True},
                        {"discipline": "Armorsmith", "rating": 500, "active": True},
                        {"discipline": "Artificer", "rating": 403, "active": False}
                    ]
                },
                {
                    "name": "Legacy Of Harathi",
                    "crafting": [
                        {"discipline": "Artificer", "rating": 404, "active": True},
                        {"discipline": "Huntsman", "rating": 500, "active": True}
                    ]
                }
            ]
        )

        # Test Weaponsmith 500 -> Kerling (active, 0 fee)
        route_ws = route_crafting_discipline("weaponsmith", 500, account, self.store)
        self.assertEqual(route_ws["character"], "Kerling")
        self.assertEqual(route_ws["action"], "ASSIGNED_ACTIVE")
        self.assertTrue(route_ws["is_active"])
        self.assertEqual(route_ws["reactivation_fee_copper"], 0)
        self.assertEqual(route_ws["waypoint"], "[&BBAEAAA=]")
        self.assertIn("Weaponsmithing Station", route_ws["station_name"])

        # Test Artificer 400 -> Legacy Of Harathi (active, avoiding Kerling's inactive license and 50 silver fee)
        route_art = route_crafting_discipline("artificer", 400, account, self.store)
        self.assertEqual(route_art["character"], "Legacy Of Harathi")
        self.assertEqual(route_art["action"], "ASSIGNED_ACTIVE")
        self.assertTrue(route_art["is_active"])
        self.assertEqual(route_art["reactivation_fee_copper"], 0)

        # Test discipline where character has license but it is inactive -> warning and reactivation fee
        account_inactive_only = AccountState(
            characters=[
                {
                    "name": "Kerling",
                    "crafting": [
                        {"discipline": "Tailor", "rating": 500, "active": False}
                    ]
                }
            ]
        )
        route_tailor = route_crafting_discipline("tailor", 500, account_inactive_only, self.store)
        self.assertEqual(route_tailor["character"], "Kerling")
        self.assertEqual(route_tailor["action"], "ACTIVATE")
        self.assertFalse(route_tailor["is_active"])
        self.assertEqual(route_tailor["reactivation_fee_copper"], 5000)  # 50 silver = 5000 copper
        self.assertIsNotNone(route_tailor["warning"])
        self.assertIn("50 silver reactivation fee", route_tailor["warning"])

    def test_item_chat_link_encoder(self):
        """Verifies authentic Guild Wars 2 base64 chat link generation [&...]."""
        # Item 30704 (Twilight)
        chat_link_twilight = encode_item_chat_link(30704)
        self.assertEqual(chat_link_twilight, "[&AgHwdwAA]")

        # Item 26155 (Ghostly Hero's Ring)
        chat_link_ring = encode_item_chat_link(26155)
        self.assertEqual(chat_link_ring, "[&AgErZgAA]")

    def test_roadmap_phase4_character_discipline_assignment(self):
        """Verifies Phase 4 milestone steps assign active character and station chat links."""
        account = AccountState(
            characters=[
                {
                    "name": "Kerling",
                    "crafting": [
                        {"discipline": "Weaponsmith", "rating": 500, "active": True},
                        {"discipline": "Armorsmith", "rating": 500, "active": True}
                    ]
                }
            ]
        )
        diff_report = self.diff_engine.compute_diff(30704, account)
        phases = self.solver.generate_master_roadmap(diff_report, account)
        p4 = next(p for p in phases if p.phase_number == 4)
        craft_step = next(s for s in p4.milestone_steps if "Craft" in s.title)
        self.assertEqual(craft_step.assigned_character, "Kerling")
        self.assertEqual(craft_step.waypoint, "[&BBAEAAA=]")

    def test_arbitrage_gen2_account_bound_and_actions(self):
        """Verifies Gen 2 account bound legendaries (76158 Astralaria) have no TP sell values."""
        live_prices = {
            76158: {"sells": {"unit_price": 0}, "buys": {"unit_price": 0}},
        }
        account = AccountState()
        report = self.solver.solve_buy_vs_craft_vs_vault(76158, live_prices, account)

        self.assertEqual(report.goal_item_id, 76158)
        self.assertIsNone(report.net_sell_if_sold)
        self.assertIsNone(report.profit_margin_if_sold)
        self.assertEqual(report.recommended_action, "CRAFT_FOR_SELF")

    def test_get_live_market_prices_helper_contracts(self):
        """Verifies get_live_market_prices helper contracts, deduplication, and fallback mechanisms."""
        from ingestion.gw2_api import get_live_market_prices as api_helper

        # Re-exported function is identical to module implementation
        self.assertIs(get_live_market_prices, api_helper)

        # Empty / invalid requests
        self.assertEqual(get_live_market_prices([]), {})
        self.assertEqual(get_live_market_prices([0, -1]), {})

        # Resolves standard materials with valid structure
        prices = get_live_market_prices([19721, 19976])  # Ecto, Mystic Coin
        self.assertIn(19721, prices)
        self.assertIn(19976, prices)
        for item_id, p_obj in prices.items():
            self.assertIn("buys", p_obj)
            self.assertIn("sells", p_obj)
            self.assertIn("unit_price", p_obj["buys"])
            self.assertIn("unit_price", p_obj["sells"])
            self.assertGreater(p_obj["sells"]["unit_price"], 0)
            self.assertGreater(p_obj["buys"]["unit_price"], 0)

    def test_solve_buy_vs_craft_vs_vault_automatic_price_resolution(self):
        """Verifies solve_buy_vs_craft_vs_vault automatically resolves prices when live_prices is None or empty."""
        # Case A: live_prices is None
        rep_none = solve_buy_vs_craft_vs_vault(goal_item_id=30704, live_prices=None, graph_store=self.store)
        self.assertIsInstance(rep_none, ArbitrageReport)
        self.assertEqual(rep_none.goal_item_id, 30704)
        self.assertEqual(rep_none.goal_name, "Twilight")
        self.assertGreater(rep_none.instant_buy_total, 0)
        self.assertGreater(rep_none.buy_order_total, 0)
        self.assertIsNotNone(rep_none.net_sell_if_sold)

        # Case B: live_prices is empty dict {}
        rep_empty = self.solver.solve_buy_vs_craft_vs_vault(goal_item_id=30704, live_prices={})
        self.assertIsInstance(rep_empty, ArbitrageReport)
        self.assertEqual(rep_empty.goal_item_id, 30704)
        self.assertGreater(rep_empty.instant_buy_total, 0)
        self.assertGreater(rep_empty.buy_order_total, 0)
        self.assertIsNotNone(rep_empty.net_sell_if_sold)

    def test_wallaces_15_percent_tax_model_preservation(self):
        """Verifies that Wallace's 15% TP tax model (int(buys.unit_price * 0.85)) is strictly preserved."""
        test_buy_order_copper = 1234567
        live_prices = {
            30704: {"sells": {"unit_price": 2000000}, "buys": {"unit_price": test_buy_order_copper}},
        }
        report = self.solver.solve_buy_vs_craft_vs_vault(30704, live_prices=live_prices)

        # Wallace's verified liquidation formula: int(buys.unit_price * 0.85)
        expected_net_sell = int(test_buy_order_copper * 0.85)
        self.assertEqual(report.net_sell_if_sold, expected_net_sell)
        # Verify exact profit margin calculation
        expected_margin = expected_net_sell - report.craft_from_scratch_total
        self.assertEqual(report.profit_margin_if_sold, expected_margin)

    def test_dynamic_tradeability_zero_domain_hardcoding(self):
        """Verifies tradeability is determined dynamically via RDF queries with zero hardcoded weapon lists."""
        # Gen 1 Legendary Greatsword (Twilight - 30704): tradeable on TP
        rep_gen1 = self.solver.solve_buy_vs_craft_vs_vault(30704, live_prices=None)
        self.assertIsNotNone(rep_gen1.net_sell_if_sold)

        # Gen 2 Legendary Axe (Astralaria - 76158): account bound, cannot be liquidated on TP
        rep_gen2 = self.solver.solve_buy_vs_craft_vs_vault(76158, live_prices=None)
        self.assertIsNone(rep_gen2.net_sell_if_sold)
        self.assertIsNone(rep_gen2.profit_margin_if_sold)
        self.assertEqual(rep_gen2.recommended_action, "CRAFT_FOR_SELF")


if __name__ == "__main__":
    unittest.main()


