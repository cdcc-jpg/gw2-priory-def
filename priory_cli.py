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
import asyncio
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
    gw2_key = os.getenv("GW2_API_KEY")
    api_client = GW2ApiClient(api_key=gw2_key)

    if gw2_key and gw2_key.strip():
        print(f"[+] GW2 API Key Detected: {gw2_key[:6]}...{gw2_key[-4:]} 🔑")
        print("    Fetching live player materials, bank, wallet, legendary armory, and characters...")
        try:
            player_account = await api_client.fetch_account_snapshot()
            armory_count = len(player_account.legendary_armory)
            mat_count = len(player_account.materials)
            print(f"    ✅ Live account snapshot successfully retrieved! ({mat_count} materials, {armory_count} armory legendaries)")
        except Exception as e:
            print(f"    ⚠️ Failed to fetch live account: {e}. Falling back to default account snapshot.")
            player_account = AccountState(
                materials={19675: 50, 19721: 180},
                bank={29185: 1},
                wallet={35: 440},
                legendary_armory={91505: 4},
                disciplines={"weaponsmith": 500}
            )
    else:
        print("[ℹ️] No GW2_API_KEY set in .env. Using default test account snapshot:")
        print("    • 4 Legendary Sigils in Armory ✅ | Dusk in Bank ✅ | 440 Provisioner Tokens | Weaponsmith 500 ✅")
        player_account = AccountState(
            materials={19675: 50, 19721: 180},
            bank={29185: 1},
            wallet={35: 440},
            legendary_armory={91505: 4},
            disciplines={"weaponsmith": 500}
        )

    # 4. Trading Post Prices
    live_tp_prices = {29185: 280.0, 19721: 0.22, 24562: 4.50}

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
