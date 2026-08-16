"""Honest benchmark comparing:
1. Pure LLM Baseline (Raw Account JSON + Gemini directly, NO ontology / graph solver)
2. Priory Neuro-Symbolic Sandwich (OWL 2 DL + SPARQL DAG + AccountDiffEngine + Gemini)
"""

import os
import sys
import json
import time
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load env
load_dotenv()

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from engine.graph_store import PrioryGraphStore
from engine.account_diff import AccountDiffEngine
from agent.orchestrator import PrioryAgentOrchestrator
from agent.llm_client import GeminiLLMClient, RuleBasedMockLLMClient
from ingestion.gw2_api import GW2ApiClient

USER_PROMPT = "I want to craft the legendary harpoon"

async def run_experiment():
    print("=" * 80)
    print(" 🔬 EXPERIMENT: PURE LLM vs. PRIORY NEURO-SYMBOLIC GRAPH LAYER")
    print("=" * 80)

    # 1. Fetch Live Account Snapshot
    gw2_key = os.getenv("GW2_API_KEY")
    api_client = GW2ApiClient(api_key=gw2_key)
    account = await api_client.fetch_account_snapshot()
    
    print(f"\n[+] Live Player Account Loaded:")
    print(f"    • Materials in Storage: {len(account.materials)} categories")
    print(f"    • Bank Items: {len(account.bank)} slots")
    print(f"    • Wallet Currencies: {len(account.wallet)} currencies")
    print(f"    • Legendary Armory: {len(account.legendary_armory)} legendaries")

    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("[-] Error: GEMINI_API_KEY not found.")
        return

    gemini = GeminiLLMClient(api_key=gemini_key)

    # =========================================================================
    # APPROACH 1: PURE LLM BASELINE (Direct Prompting with Raw Account Data)
    # =========================================================================
    print("\n" + "#" * 80)
    print(" 🧪 RUNNING APPROACH 1: PURE LLM (Gemini 2.0 Flash directly against API JSON)")
    print("#" * 80)

    # Format the entire raw account state as context for pure LLM
    raw_account_summary = {
        "materials_storage_sample": {k: v for k, v in account.materials.items() if v > 0},
        "bank_sample": {k: v for k, v in account.bank.items() if v > 0},
        "wallet": account.wallet,
        "legendary_armory": account.legendary_armory,
        "crafting_disciplines": account.disciplines
    }

    pure_llm_system_prompt = (
        "You are an expert Guild Wars 2 crafting copilot. "
        "The player wants advice on acquiring or crafting items in Guild Wars 2. "
        "You are given the player's account inventory and material storage data in JSON format. "
        "Analyze the player's account against the required crafting recipe and components, "
        "calculate the EXACT missing materials delta, identify bottlenecks, and provide an actionable progression guide."
    )

    pure_llm_user_prompt = f"""
Player Query: "{USER_PROMPT}"

Player Account Data (JSON):
{json.dumps(raw_account_summary, indent=2)}

Please provide:
1. Identified Weapon & Precursor
2. Overall Account Readiness %
3. Exact Remaining Materials Delta (calculate what is owned in account JSON vs needed)
4. Strategic Bottlenecks & Recommendations
5. Actionable Session Plan with Waypoint Chat Codes
"""

    t0 = time.perf_counter()
    pure_llm_output = gemini.generate_text(
        prompt=pure_llm_user_prompt,
        system_prompt=pure_llm_system_prompt
    )
    pure_llm_time = time.perf_counter() - t0

    # =========================================================================
    # APPROACH 2: PRIORY NEURO-SYMBOLIC GRAPH (OWL 2 DL + SPARQL Solver)
    # =========================================================================
    print("\n" + "#" * 80)
    print(" 🏛️ RUNNING APPROACH 2: PRIORY NEURO-SYMBOLIC LAYER (Graph + Solver)")
    print("#" * 80)

    store = PrioryGraphStore()
    store.load_all()

    orchestrator = PrioryAgentOrchestrator(graph_store=store, llm_client=gemini)
    session = orchestrator.create_session(account_state=account)

    t1 = time.perf_counter()
    priory_guide = session.send_message(USER_PROMPT)
    priory_time = time.perf_counter() - t1

    # =========================================================================
    # PRINT RESULTS SIDE BY SIDE
    # =========================================================================
    print("\n" + "=" * 80)
    print(" 📊 COMPARISON OF OUTPUTS")
    print("=" * 80)

    print("\n--- [1. PURE LLM OUTPUT (Direct Gemini 2.0 Flash)] ---")
    print(f"⏱️ Time: {pure_llm_time:.2f}s | Input context: {len(json.dumps(raw_account_summary))} bytes")
    print(pure_llm_output)

    print("\n--- [2. PRIORY NEURO-SYMBOLIC OUTPUT (Ontology + Engine + Gemini)] ---")
    print(f"⏱️ Time: {priory_time:.2f}s | Triples queried: {len(store.graph)}")
    print(f"Goal: {priory_guide.goal_name} ({priory_guide.chat_code})")
    print(f"Readiness: {priory_guide.readiness_percentage}%")
    print(f"\nRecommendations:")
    for r in priory_guide.strategic_recommendations:
        print(f" - {r}")
    print(f"\nSession Plan:")
    for s in priory_guide.session_checklist:
        print(f" [{s.step_number}] {s.title} ({s.estimated_time_minutes}m) -> {s.description}")
    print(f"\nExact Leaf Delta to Craft:")
    for k, v in priory_guide.missing_materials_summary.items():
        print(f" • {k}: {v} needed")


if __name__ == "__main__":
    asyncio.run(run_experiment())
