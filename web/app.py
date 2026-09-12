"""Project Priory — Lightweight Web GUI & Reasoning Explorer.

Temporary developer web interface and conversational playground for the
neuro-symbolic semantic layer before integration with the main gw2priory website.
"""

from __future__ import annotations
import os
import asyncio
import dataclasses
from typing import Dict, Any, Optional
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

load_dotenv()

from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState, AccountDiffEngine
from engine.path_solver import PathSolver
from engine.account_ranker import AccountRanker
from ingestion.gw2_api import GW2ApiClient, InsufficientPermissionsError, MissingApiKeyError
from agent.orchestrator import PrioryAgentOrchestrator, PrioryChatSession
from agent.llm_client import (
    GeminiLLMClient,
    LocalOllamaClient,
    RuleBasedMockLLMClient,
    get_default_llm_client,
)

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static")
)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "priory-secret-dev-key-42")

# Global Semantic Components
GRAPH_STORE: Optional[PrioryGraphStore] = None
ORCHESTRATOR: Optional[PrioryAgentOrchestrator] = None
ACTIVE_ACCOUNT: Optional[AccountState] = None
SESSIONS: Dict[str, PrioryChatSession] = {}
DEFAULT_GW2_API_KEY: str = os.getenv("GW2_API_KEY", "")


def get_or_create_store() -> PrioryGraphStore:
    global GRAPH_STORE
    if GRAPH_STORE is None:
        GRAPH_STORE = PrioryGraphStore()
        GRAPH_STORE.load_all()
    return GRAPH_STORE


def get_or_create_orchestrator() -> PrioryAgentOrchestrator:
    global ORCHESTRATOR
    if ORCHESTRATOR is None:
        store = get_or_create_store()
        llm = get_default_llm_client()
        ORCHESTRATOR = PrioryAgentOrchestrator(graph_store=store, llm_client=llm)
    return ORCHESTRATOR


def get_live_account() -> AccountState:
    global ACTIVE_ACCOUNT
    if ACTIVE_ACCOUNT is not None:
        return ACTIVE_ACCOUNT

    gw2_key = os.getenv("GW2_API_KEY")
    if not gw2_key or not gw2_key.strip():
        # Check MCP config
        mcp_config = Path.home() / ".gemini" / "config" / "mcp_config.json"
        if mcp_config.exists():
            try:
                import json
                with open(mcp_config, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    h = data.get("mcpServers", {}).get("gw2priory", {}).get("headers", {})
                    if "X-GW2-Key" in h and h["X-GW2-Key"]:
                        gw2_key = h["X-GW2-Key"].strip()
            except Exception:
                pass

    if gw2_key and gw2_key.strip():
        api_client = GW2ApiClient(api_key=gw2_key)
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ACTIVE_ACCOUNT = loop.run_until_complete(api_client.fetch_account_snapshot())
            loop.close()
            return ACTIVE_ACCOUNT
        except Exception:
            pass

    ACTIVE_ACCOUNT = AccountState()
    return ACTIVE_ACCOUNT


@app.route("/")
def index():
    """Renders the main Priory Reasoning Explorer page (Classic Grimoire)."""
    return render_template("index.html")


@app.route("/3d")
def grimoire_3d():
    """Renders the Next-Gen WebGL 3D Interactive Grimoire prototype."""
    return render_template("grimoire_3d.html")


@app.route("/api/status", methods=["GET"])
def api_status():
    """Returns knowledge graph and LLM provider status, reporting live vs fallback mode."""
    store = get_or_create_store()
    orchestrator = get_or_create_orchestrator()
    account = get_live_account()

    llm = orchestrator.llm
    is_fallback = False
    fallback_reason = None

    if isinstance(llm, RuleBasedMockLLMClient):
        is_fallback = True
        fallback_reason = "Operating on deterministic rule-based mock engine."
        provider_name = "Rule-Based Deterministic Engine (Fallback)"
    elif isinstance(llm, GeminiLLMClient):
        if getattr(llm, "fallback_active", False):
            is_fallback = True
            fallback_reason = getattr(llm, "last_error", "API policy or quota limit")
            provider_name = f"Google Gemini ({llm.model}) [Fallback Active]"
        else:
            if hasattr(llm, "check_liveness"):
                is_live = llm.check_liveness()
                if not is_live:
                    is_fallback = True
                    fallback_reason = getattr(llm, "last_error", "API policy or connectivity failed")
                    provider_name = f"Google Gemini ({llm.model}) [Fallback Active]"
                else:
                    provider_name = f"Google Gemini Live ({llm.model})"
            else:
                provider_name = f"Google Gemini Live ({llm.model})"
    elif isinstance(llm, LocalOllamaClient):
        if getattr(llm, "fallback_active", False):
            is_fallback = True
            fallback_reason = getattr(llm, "last_error", "Local Ollama server unreachable")
            provider_name = f"Local Ollama ({llm.model_name}) [Fallback Active]"
        else:
            provider_name = f"Local Ollama ({llm.model_name})"
    else:
        is_fallback = True
        fallback_reason = "Unrecognized LLM client type."
        provider_name = "Rule-Based Deterministic Engine"

    gw2_key = os.getenv("GW2_API_KEY", "")
    has_key = bool(gw2_key and gw2_key.strip())
    masked_key = f"{gw2_key[:6]}...{gw2_key[-4:]}" if has_key else "None"

    return jsonify({
        "status": "ready",
        "triples_loaded": len(store.graph),
        "llm_provider": provider_name,
        "is_fallback": is_fallback,
        "llm_mode": "fallback" if is_fallback else "live",
        "fallback_reason": fallback_reason,
        "account_name": getattr(account, "account_name", "") or (getattr(account, "account_created", "") and "Commander") or "Authenticated Scholar",
        "api_key_configured": has_key,
        "api_key_masked": masked_key,
        "account_materials_count": len(account.materials),
        "account_armory_count": len(account.legendary_armory),
        "wallet": {
            "astral_acclaim": account.wallet.get(63, 0),
            "volatile_magic": account.wallet.get(45, 0),
            "spirit_shards": account.wallet.get(23, 0),
            "laurels": account.wallet.get(3, 0),
            "provisioner_tokens": account.wallet.get(29, 0),
            "liquid_gold": account.wallet.get(1, 0) / 10000.0 if 1 in account.wallet else 0.0,
        }
    })


@app.route("/api/account/refresh", methods=["POST"])
def api_refresh_account():
    """Refreshes live account data from GW2 API with optional new API key or reset to default."""
    global ACTIVE_ACCOUNT, SESSIONS
    data = request.get_json(silent=True) or {}
    reset = data.get("reset", False)

    if reset:
        key_to_use = DEFAULT_GW2_API_KEY
        if DEFAULT_GW2_API_KEY:
            os.environ["GW2_API_KEY"] = DEFAULT_GW2_API_KEY
        else:
            os.environ.pop("GW2_API_KEY", None)
        ACTIVE_ACCOUNT = None
        SESSIONS.clear()
        account = get_live_account()
        return jsonify({
            "success": True,
            "reset": True,
            "account_name": getattr(account, "account_name", "Default Account") or "Default Account",
            "materials_count": len(account.materials),
            "armory_count": len(account.legendary_armory),
            "wallet": account.wallet,
            "api_key_masked": f"{DEFAULT_GW2_API_KEY[:6]}...{DEFAULT_GW2_API_KEY[-4:]}" if DEFAULT_GW2_API_KEY else "None"
        })

    new_key = data.get("api_key") or data.get("new_key")
    if not new_key or not isinstance(new_key, str) or not new_key.strip():
        return jsonify({"success": False, "error": "No API key provided."}), 400

    new_key = new_key.strip()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        api_client = GW2ApiClient(api_key=new_key)
        account = loop.run_until_complete(api_client.fetch_account_snapshot())
        ACTIVE_ACCOUNT = account
        os.environ["GW2_API_KEY"] = new_key
        SESSIONS.clear()
        return jsonify({
            "success": True,
            "account_name": account.account_name or "Custom Account",
            "materials_count": len(account.materials),
            "armory_count": len(account.legendary_armory),
            "wallet": account.wallet,
            "api_key_masked": f"{new_key[:6]}...{new_key[-4:]}"
        })
    except (InsufficientPermissionsError, MissingApiKeyError) as e:
        return jsonify({"success": False, "error": str(e)}), 401
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        loop.close()


@app.route("/api/session/history", methods=["GET"])
def api_session_history():
    """Returns recent session conversation history from SESSIONS for real-time monitoring and verification."""
    session_id = request.args.get("session_id")
    limit = int(request.args.get("limit", 20))

    if session_id:
        sess = SESSIONS.get(session_id)
        if not sess:
            return jsonify({
                "success": True,
                "session_id": session_id,
                "history": [],
                "turns_count": 0,
                "message": f"Session '{session_id}' not found or no conversation history."
            })

        last_goal_dict = None
        if sess.last_goal:
            if hasattr(sess.last_goal, "model_dump"):
                last_goal_dict = sess.last_goal.model_dump()
            elif dataclasses.is_dataclass(sess.last_goal):
                last_goal_dict = dataclasses.asdict(sess.last_goal)

        return jsonify({
            "success": True,
            "session_id": session_id,
            "history": sess.history[-limit:],
            "turns_count": len(sess.history),
            "last_goal": last_goal_dict,
        })

    # Return summary of all active sessions
    sessions_summary = {}
    for s_id, sess in SESSIONS.items():
        last_goal_dict = None
        if sess.last_goal:
            if hasattr(sess.last_goal, "model_dump"):
                last_goal_dict = sess.last_goal.model_dump()
            elif dataclasses.is_dataclass(sess.last_goal):
                last_goal_dict = dataclasses.asdict(sess.last_goal)
        sessions_summary[s_id] = {
            "turns_count": len(sess.history),
            "recent_turns": sess.history[-limit:],
            "last_goal": last_goal_dict,
        }

    default_history = []
    if "default_user_session" in SESSIONS:
        default_history = SESSIONS["default_user_session"].history[-limit:]
    elif SESSIONS:
        default_history = list(SESSIONS.values())[0].history[-limit:]

    return jsonify({
        "success": True,
        "active_sessions_count": len(SESSIONS),
        "history": default_history,
        "sessions": sessions_summary,
    })


@app.route("/api/query", methods=["POST"])
def api_query():
    """Processes a natural language query through the neuro-symbolic sandwich."""
    data = request.get_json(silent=True) or {}
    user_prompt = data.get("query", "").strip()
    session_id = data.get("session_id", "default_user_session")

    if not user_prompt:
        return jsonify({"error": "Empty query provided."}), 400

    print(f"📥 [PRIORY WEB] Query: '{user_prompt}' | Session: {session_id}")

    orchestrator = get_or_create_orchestrator()
    account = get_live_account()

    if session_id not in SESSIONS:
        SESSIONS[session_id] = orchestrator.create_session(account_state=account)

    session_obj = SESSIONS[session_id]

    try:
        # Process message with session context
        guide = session_obj.send_message(user_prompt)

        last_goal = getattr(session_obj, "last_goal", None)
        parsed_goal = (
            getattr(last_goal, "resolved_item_name", None)
            or getattr(last_goal, "category_filter", None)
            or (getattr(last_goal.intent, "target_item_name", None) if last_goal and hasattr(last_goal, "intent") else None)
            or guide.goal_name
        )
        goal_type = (
            last_goal.goal_type.value
            if last_goal and hasattr(last_goal, "goal_type") and hasattr(last_goal.goal_type, "value")
            else str(getattr(last_goal, "goal_type", "UNKNOWN"))
        )
        target_quantity = getattr(last_goal, "target_quantity", getattr(guide, "target_quantity", 1))

        print(f"🎯 [PRIORY PARSER] Goal: '{parsed_goal}' | Type: {goal_type} | Qty: {target_quantity}")
        print(f"🔍 [PRIORY INTENT] Goal: '{guide.goal_name}' | Readiness: {guide.readiness_percentage}%")

        return jsonify({
            "success": True,
            "query": user_prompt,
            "session_id": session_id,
            "guide": {
                "goal_name": guide.goal_name,
                "target_quantity": guide.target_quantity,
                "chat_code": guide.chat_code,
                "readiness_percentage": guide.readiness_percentage,
                "executive_summary": guide.executive_summary,
                "strategic_recommendations": guide.strategic_recommendations,
                "character_recommendations": getattr(guide, "character_recommendations", []),
                "master_roadmap_phases": guide.master_roadmap_phases,
                "session_checklist": [
                    {
                        "step_number": s.step_number,
                        "title": s.title,
                        "estimated_time_minutes": s.estimated_time_minutes,
                        "game_mode": s.game_mode,
                        "description": s.description,
                        "chat_code": s.chat_code,
                    }
                    for s in guide.session_checklist
                ],
                "missing_materials_summary": guide.missing_materials_summary,
                "missing_disciplines_summary": guide.missing_disciplines_summary,
                "motivational_tip": guide.motivational_tip,
                "vip_lounge_callout": getattr(guide, "vip_lounge_callout", None),
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/solver/itinerary", methods=["POST"])
def api_solver_itinerary():
    """Generates mathematically optimal daily session itinerary using 0/1 knapsack priority scheduling."""
    data = request.get_json(silent=True) or {}
    time_budget = int(data.get("time_budget_minutes") or 60)
    goal_item_id = int(data.get("goal_item_id") or 30704)
    active_events = data.get("active_events")

    store = get_or_create_store()
    account = get_live_account()
    solver = PathSolver(store)

    try:
        itinerary = solver.schedule_daily_session_itinerary(
            goal_item_id=goal_item_id,
            time_budget_minutes=time_budget,
            account_state=account,
            active_events=active_events,
        )
        return jsonify({
            "success": True,
            "itinerary": dataclasses.asdict(itinerary)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/solver/arbitrage", methods=["POST"])
def api_solver_arbitrage():
    """Computes buy vs craft vs vault multi-way arbitrage matrix with Wallace's 15% TP tax model."""
    data = request.get_json(silent=True) or {}
    goal_item_id = int(data.get("goal_item_id") or 30704)
    custom_prices = data.get("live_prices") or {}

    store = get_or_create_store()
    account = get_live_account()
    solver = PathSolver(store)

    prices_map = dict(custom_prices)
    if not prices_map:
        try:
            api_client = GW2ApiClient()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            fetched = loop.run_until_complete(api_client.get_tp_prices([goal_item_id, 19721, 19976]))
            loop.close()
            for p in fetched:
                prices_map[p["id"]] = p
        except Exception:
            pass

    try:
        report = solver.solve_buy_vs_craft_vs_vault(
            goal_item_id=goal_item_id,
            live_prices=prices_map,
            account_state=account,
        )
        return jsonify({
            "success": True,
            "arbitrage": dataclasses.asdict(report)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/solver/prerequisites", methods=["POST"])
def api_solver_prerequisites():
    """Audits account masteries, world completion, active crafting disciplines, and collection prerequisites."""
    data = request.get_json(silent=True) or {}
    goal_item_id = int(data.get("goal_item_id") or 30704)

    store = get_or_create_store()
    account = get_live_account()
    diff_engine = AccountDiffEngine(store)

    try:
        report = diff_engine.verify_legendary_prerequisites(
            goal_item_id=goal_item_id,
            account_state=account,
        )
        return jsonify({
            "success": True,
            "prerequisites": dataclasses.asdict(report)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/solver/opportunity-cost", methods=["POST"])
def api_solver_opportunity_cost():
    """Evaluates cross-role opportunity cost (TP liquidation vs salvage vs currency spending)."""
    data = request.get_json(silent=True) or {}
    currency_id = int(data.get("currency_id") or 63)
    account = get_live_account()

    default_qty = account.wallet.get(currency_id) or account.get_item_count(currency_id) or 100
    quantity = int(data.get("quantity") or default_qty)
    tp_sell = int(data.get("tp_sell_unit_price") or 0)
    salvage_val = int(data.get("salvage_expected_unit_value") or 0)
    direct_val = float(data.get("direct_exchange_unit_value") or 0.0)

    store = get_or_create_store()
    solver = PathSolver(store)

    try:
        report = solver.evaluate_cross_role_opportunity_cost(
            item_id=currency_id,
            quantity=quantity,
            tp_sell_unit_price=tp_sell,
            salvage_expected_unit_value=salvage_val,
            direct_exchange_unit_value=direct_val,
        )
        return jsonify({
            "success": True,
            "opportunity_cost": report
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    print(f"🏛️ Starting Project Priory Web GUI on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
