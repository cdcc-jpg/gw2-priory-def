#!/usr/bin/env python3
"""Interactive demonstration of Project Priory's Neuro-Symbolic Sandwich Pipeline.

Run:
    python3 demo_neuro_symbolic.py
"""

from agent.orchestrator import PrioryAgentOrchestrator
from engine.account_diff import AccountState


def main():
    print("=" * 75)
    print(" 🥪  PROJECT PRIORY — NEURO-SYMBOLIC SANDWICH AGENT PIPELINE")
    print("=" * 75)

    orchestrator = PrioryAgentOrchestrator()

    # 1. Simulate a real player prompt
    user_prompt = (
        "I want to make Twilight! I have about 2 hours to play tonight, "
        "I hate WvW, and I have about 400g saved up."
    )
    print("\n💬 [User Prompt]:")
    print(f'   "{user_prompt}"\n')

    # 2. Simulate the player's live account state (from GW2 API)
    # The player already owns Dusk in their bank, 50/77 Mystic Clovers, and has 500 Weaponsmithing
    player_account = AccountState(
        materials={
            19675: 50,  # 50 Mystic Clovers (needs 77)
            19721: 180, # 180 Ectoplasm (needs 250)
        },
        bank={
            29185: 1,   # Owns Dusk precursor in bank!
        },
        disciplines={
            "weaponsmith": 500 # Max weaponsmithing
        }
    )
    print("👤 [Player Account State Loaded via Symbolic Layer]:")
    print("   • Bank: Dusk (Precursor) Owned ✅")
    print("   • Materials: 50x Mystic Clovers, 180x Ectoplasm")
    print("   • Disciplines: Weaponsmith 500 (Meets 400 req) ✅")

    print("\n⚙️  Running Neuro-Symbolic Sandwich Pipeline (Top LLM -> Symbolic Delta -> Bottom LLM)...")
    guide = orchestrator.run_pipeline(user_prompt, player_account)

    # 3. Display the personalized synthesized output
    print("\n" + "─" * 75)
    print(f" 🎯  PERSONALIZED PROGRESSION PLAN FOR: {guide.goal_name.upper()} {guide.chat_code or ''}")
    print("─" * 75)
    print(f"📊 Readiness Score: {guide.readiness_percentage}%\n")
    print(f"📝 {guide.executive_summary}\n")

    print("💡 STRATEGIC RECOMMENDATIONS & CONSTRAINTS:")
    for rec in guide.strategic_recommendations:
        print(f"   {rec}")

    print("\n📋 ACTIONABLE SESSION CHECKLIST (Tonight's Play Session):")
    for step in guide.session_checklist:
        chat = f" [{step.chat_code}]" if step.chat_code else ""
        print(f"   [{step.step_number}] {step.title} (~{step.estimated_time_minutes} mins | {step.game_mode}){chat}")
        print(f"       -> {step.description}")

    print("\n📦 REMAINING DELTA TO CRAFT:")
    for mat, qty in guide.missing_materials_summary.items():
        print(f"   • {mat}: {qty} needed")

    print(f"\n{guide.motivational_tip}")
    print("=" * 75)


if __name__ == "__main__":
    main()
