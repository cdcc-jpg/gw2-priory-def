#!/usr/bin/env python3
"""Project Priory — Interactive Live Multi-Turn Conversational CLI.

Run:
    # Interactive chat mode:
    python3 priory_cli.py

    # Or one-shot query:
    python3 priory_cli.py "I want to craft 4 legendary sigils"
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountState
from engine.path_solver import PathSolver
from ingestion.gw2_api import GW2ApiClient
from agent.orchestrator import PrioryAgentOrchestrator, PrioryChatSession
from agent.llm_client import GeminiLLMClient, LocalOllamaClient, RuleBasedMockLLMClient, get_default_llm_client


def print_guide(guide):
    """Formats and prints the synthesized guide to the terminal."""
    target_str = f"{guide.target_quantity}x " if guide.target_quantity > 1 else ""
    chat_str = f" {guide.chat_code}" if guide.chat_code else ""
    print("\n" + "─" * 78)
    print(f" 🎯  OPTIMAL PROGRESSION GUIDE: {target_str}{guide.goal_name.upper()}{chat_str}")
    print("─" * 78)
    print(f"📊 Overall Account Readiness: {guide.readiness_percentage}%\n")
    print(f"📝 {guide.executive_summary}\n")

    print("💡 STRATEGIC RECOMMENDATIONS & CONSTRAINTS:")
    for rec in guide.strategic_recommendations:
        print(f"   {rec}")

    if getattr(guide, "character_recommendations", None):
        print("\n👤 CHARACTER ASSIGNMENTS & CRAFTING HANDOFFS:")
        for cr in guide.character_recommendations:
            print(f"   • {cr}")

    if guide.master_roadmap_phases:
        print("\n🗺️  5-PHASE MASTER CRAFTING ROADMAP:")
        for line in guide.master_roadmap_phases:
            print(f"   {line}")

    print("\n📋 ACTIONABLE SESSION PLAN:")
    for step in guide.session_checklist:
        chat = f" [{step.chat_code}]" if step.chat_code else ""
        print(f"   [{step.step_number}] {step.title} (~{step.estimated_time_minutes} mins | {step.game_mode}){chat}")
        print(f"       -> {step.description}")

    if guide.missing_materials_summary:
        print("\n📦 REMAINING DELTA TO CRAFT:")
        for mat, qty in guide.missing_materials_summary.items():
            print(f"   • {mat}: {qty} needed")

    print(f"\n{guide.motivational_tip}")
    print("=" * 78 + "\n")


def resolve_gw2_api_key() -> str | None:
    """Discovers GW2 API key from environment, mcp_config.json, or .env."""
    key = os.environ.get("GW2_API_KEY")
    if key and key.strip():
        return key.strip()

    # Check MCP config
    mcp_config_path = Path.home() / ".gemini" / "config" / "mcp_config.json"
    if mcp_config_path.exists():
        try:
            with open(mcp_config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                headers = data.get("mcpServers", {}).get("gw2priory", {}).get("headers", {})
                if "X-GW2-Key" in headers and headers["X-GW2-Key"]:
                    return headers["X-GW2-Key"].strip()
        except Exception:
            pass

    return None


async def main():
    print("=" * 78)
    print(" 🏛️  PROJECT PRIORY — NEURO-SYMBOLIC CONVERSATIONAL COPILOT")
    print("=" * 78)

    # 1. Initialize Semantic Graph Store
    store = PrioryGraphStore()
    triples_loaded = store.load_all()
    print(f"[+] Semantic Knowledge Graph Loaded: {triples_loaded} triples (OWL 2 DL + SKOS).")

    # 2. Detect LLM Provider
    llm_client = get_default_llm_client()
    if isinstance(llm_client, GeminiLLMClient):
        print(f"[+] LLM Provider: Google Gemini Live API ({llm_client.model}) 🌐")
    elif isinstance(llm_client, LocalOllamaClient):
        print(f"[+] LLM Provider: Local Ollama Model ({llm_client.model_name}) 🦙")
    else:
        print("[+] LLM Provider: Rule-Based Deterministic Engine (Offline Mock) ⚙️")

    # 3. Check for Live GW2 Account API Key
    gw2_key = resolve_gw2_api_key()
    if not gw2_key or not gw2_key.strip():
        print("\n❌ ERROR: No GW2 API Key detected!")
        print("   Project Priory runs strictly against live ArenaNet account data.")
        print("   Please create an API key at https://account.arena.net/applications with scopes:")
        print("   • 'account', 'characters', 'inventories', 'builds'")
        print("   Then set it in .env (GW2_API_KEY=your_key) or ~/.gemini/config/mcp_config.json.\n")
        sys.exit(1)

    api_client = GW2ApiClient(api_key=gw2_key)
    print(f"[+] GW2 API Key Detected: {gw2_key[:6]}...{gw2_key[-4:]} 🔑")
    print("    Fetching live player materials, bank, wallet, legendary armory, and characters (with ETag conditional caching)...")
    try:
        player_account = await api_client.fetch_account_snapshot()
        armory_count = len(player_account.legendary_armory)
        mat_count = len(player_account.materials)
        char_count = len(player_account.characters)
        print(f"    ✅ Live account snapshot successfully retrieved! ({mat_count} materials, {armory_count} armory legendaries, {char_count} characters)")
    except Exception as e:
        print(f"\n❌ FAILED TO FETCH LIVE ACCOUNT: {e}")
        print("   Please verify that your API key is valid and has required scopes.\n")
        sys.exit(1)

    # 4. Trading Post Prices (Live TP fetch for standard milestone goods)
    live_tp_prices = {}
    try:
        sample_ids = [29185, 19721, 24562, 19976, 24277]
        tp_data = await api_client.get_tp_prices(sample_ids)
        for entry in tp_data:
            item_id = entry.get("id")
            buys = entry.get("buys", {})
            unit_price = (buys.get("unit_price", 0)) / 10000.0  # Convert copper to gold
            if item_id:
                live_tp_prices[item_id] = unit_price
    except Exception:
        live_tp_prices = {29185: 280.0, 19721: 0.22, 24562: 4.50, 19976: 1.50}

    # 5. Initialize Orchestrator & Multi-Turn Session
    orchestrator = PrioryAgentOrchestrator(graph_store=store, llm_client=llm_client)
    session = orchestrator.create_session(account_state=player_account)

    # 6. Execution Mode: One-shot or Interactive Multi-Turn Loop
    if len(sys.argv) > 1:
        # One-shot mode
        user_prompt = " ".join(sys.argv[1:])
        print(f"\n💬 Query: \"{user_prompt}\"")
        guide = session.send_message(user_prompt, live_tp_prices)
        print_guide(guide)
    else:
        # Interactive Multi-Turn Chat Mode
        print("\n💬 [Interactive Chat Mode Active] Type your question, follow-up, or 'exit' to quit.\n")
        
        # Initial greeting prompt
        first_prompt = "I want to craft 4 legendary sigils."
        print(f"User > {first_prompt}")
        guide = session.send_message(first_prompt, live_tp_prices)
        print_guide(guide)

        while True:
            try:
                user_input = input("Priory User > ").strip()
                if not user_input or user_input.lower() in ["exit", "quit", "q"]:
                    print("\n👋 Happy hunting in Tyria!")
                    break

                print("\n⚙️  Processing follow-up with Knowledge Graph & Delta Engine...")
                guide = session.send_message(user_input, live_tp_prices)
                print_guide(guide)
            except (KeyboardInterrupt, EOFError):
                print("\n👋 Exiting.")
                break


if __name__ == "__main__":
    asyncio.run(main())
