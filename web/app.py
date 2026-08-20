"""Project Priory — Lightweight Web GUI & Reasoning Explorer.

Temporary developer web interface and conversational playground for the
neuro-symbolic semantic layer before integration with the main gw2priory website.
"""

from __future__ import annotations
import os
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

load_dotenv()

from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState, AccountDiffEngine
from engine.path_solver import PathSolver
from engine.account_ranker import AccountRanker
from ingestion.gw2_api import GW2ApiClient
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
    """Returns knowledge graph and LLM provider status."""
    store = get_or_create_store()
    orchestrator = get_or_create_orchestrator()
    account = get_live_account()

    llm = orchestrator.llm
    if isinstance(llm, GeminiLLMClient):
        provider_name = f"Google Gemini Live ({llm.model})"
    elif isinstance(llm, LocalOllamaClient):
        provider_name = f"Local Ollama ({llm.model_name})"
    else:
        provider_name = "Rule-Based Deterministic Engine"

    gw2_key = os.getenv("GW2_API_KEY", "")
    has_key = bool(gw2_key and gw2_key.strip())
    masked_key = f"{gw2_key[:6]}...{gw2_key[-4:]}" if has_key else "None"

    return jsonify({
        "status": "ready",
        "triples_loaded": len(store.graph),
        "llm_provider": provider_name,
        "api_key_configured": has_key,
        "api_key_masked": masked_key,
        "account_materials_count": len(account.materials),
        "account_armory_count": len(account.legendary_armory),
        "wallet": {
            "astral_acclaim": account.wallet.get(68, 0),
            "volatile_magic": account.wallet.get(45, 0),
            "spirit_shards": account.wallet.get(23, 0),
            "laurels": account.wallet.get(3, 0),
            "provisioner_tokens": account.wallet.get(35, 0),
            "liquid_gold": account.wallet.get(1, 0) / 10000.0 if 1 in account.wallet else 0.0,
        }
    })


@app.route("/api/account/refresh", methods=["POST"])
def api_refresh_account():
    """Refreshes live account data from GW2 API with optional new API key."""
    global ACTIVE_ACCOUNT, SESSIONS
    data = request.get_json(silent=True) or {}
    new_key = data.get("api_key") or os.getenv("GW2_API_KEY")

    if not new_key or not new_key.strip():
        return jsonify({"success": False, "error": "No API key provided."}), 400

    try:
        api_client = GW2ApiClient(api_key=new_key.strip())
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        account = loop.run_until_complete(api_client.fetch_account_snapshot())
        loop.close()
        ACTIVE_ACCOUNT = account
        SESSIONS.clear()  # Clear sessions to bind to updated account
        return jsonify({
            "success": True,
            "materials_count": len(account.materials),
            "armory_count": len(account.legendary_armory),
            "wallet": account.wallet
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/query", methods=["POST"])
def api_query():
    """Processes a natural language query through the neuro-symbolic sandwich."""
    data = request.get_json(silent=True) or {}
    user_prompt = data.get("query", "").strip()
    session_id = data.get("session_id", "default_user_session")

    if not user_prompt:
        return jsonify({"error": "Empty query provided."}), 400

    orchestrator = get_or_create_orchestrator()
    account = get_live_account()

    if session_id not in SESSIONS:
        SESSIONS[session_id] = orchestrator.create_session(account_state=account)

    session_obj = SESSIONS[session_id]

    try:
        # Process message with session context
        guide = session_obj.send_message(user_prompt)

        return jsonify({
            "success": True,
            "query": user_prompt,
            "guide": {
                "goal_name": guide.goal_name,
                "target_quantity": guide.target_quantity,
                "chat_code": guide.chat_code,
                "readiness_percentage": guide.readiness_percentage,
                "executive_summary": guide.executive_summary,
                "strategic_recommendations": guide.strategic_recommendations,
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
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    print(f"🏛️ Starting Project Priory Web GUI on http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False)
