"""
Enhanced Werewolf Game with Real-time Observer
增强版狼人杀游戏 - 带实时观战和幻觉标记
"""

import sys
import time
import threading
import webbrowser
import os
from werewolf_game import WerewolfGame


def main():
    """Run game with real-time observation"""

    # LLM configuration
    llm_config = {
        'api_base': 'http://localhost:8080',
        'model': '/home/apulis-dev/userdata/Llama-3.3-70B-Instruct',
        'temperature': 0.7,
        'max_tokens': 500
    }

    print("\n" + "="*80)
    print("[WOLF] ENHANCED WEREWOLF GAME - WITH REAL-TIME OBSERVER")
    print(" - ")
    print("="*80)

    print("\n[LIST] NEW CONFIGURATION :")
    print("    4 Werewolves (1 King + 3 Regular) - 41+3")
    print("    4 Gods (Seer, Witch, Hunter, Guard) - 4")
    print("    4 Villagers - 4")
    print("    1 Judge (for marking hallucinations) - 1")

    print("\n[TARGET] FEATURES :")
    print("    Werewolf King can take someone down when eliminated - ")
    print("    Real-time game observation - ")
    print("    Interactive hallucination marking - ")
    print("    WebSocket live updates - WebSocket")

    # Try to start observer system
    observer_started = False
    observer_ui_path = None

    try:
        from realtime_observer import (
            get_observer,
            start_observer_server,
            InteractiveJudge,
            HallucinationType
        )

        print("\n" + "="*80)
        print(" STARTING OBSERVER SYSTEM ...")

        # Start WebSocket server
        def run_ws_server():
            observer = get_observer()
            observer.start_websocket_server()

        ws_thread = threading.Thread(target=run_ws_server, daemon=True)
        ws_thread.start()
        time.sleep(1)

        print("[OK] WebSocket server started on ws://localhost:8765")

        # Start interactive judge
        observer = get_observer()
        judge = InteractiveJudge(observer)

        def run_judge():
            # Start judge in background
            judge.start_interactive_mode()

        judge_thread = threading.Thread(target=run_judge, daemon=True)
        judge_thread.start()

        print("[OK] Interactive judge mode activated")

        # Open observer UI
        observer_ui_path = os.path.join(os.path.dirname(__file__), 'observer_ui.html')
        if os.path.exists(observer_ui_path):
            print(f"[OK] Opening observer UI: {observer_ui_path}")
            webbrowser.open(f'file://{observer_ui_path}')
        else:
            print("[WARN] Observer UI file not found")

        observer_started = True

        print("\n" + "="*80)
        print("[VIEW] OBSERVER INSTRUCTIONS :")
        print("   1. Browser window will open automatically - ")
        print("   2. Watch real-time game events - ")
        print("   3. Mark hallucinations via UI or console - UI")
        print("\n[JUDGE] JUDGE COMMANDS :")
        print("   mark <player_id> <type> <severity> <description> - ")
        print("   types - ")
        print("   stats - ")
        print("   help - ")
        print("="*80)

    except Exception as e:
        print(f"\n[WARN] Could not start observer system: {e}")
        print("Continuing without observation features...")

    # Test API connection
    print("\n[TEST] Testing API connection...")
    try:
        import requests
        response = requests.get(f"{llm_config['api_base']}/v1/models", timeout=5)
        if response.status_code == 200:
            print("[OK] API connected successfully!")
        else:
            print(f"[WARN] API returned status: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Cannot connect to API: {e}")
        print(f"Please ensure LLM server is running at: {llm_config['api_base']}")
        return

    # Wait for user confirmation
    print("\n" + "="*80)
    input("Press ENTER to start the game / 按回车开始游戏...")
    print("="*80)

    # Create and run game
    print("\n STARTING GAME ...")
    print("="*80 + "\n")

    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    results = game.play_game()

    # Save reports
    print("\n" + "="*80)
    print("[STATS] GENERATING REPORTS ...")

    # Save game report
    game_report_file = f"game_report_{results['game_id']}.json"
    game.save_report(game_report_file)
    print(f"[OK] Game report saved: {game_report_file}")

    # Generate hallucination report if observer was used
    if observer_started:
        try:
            hallucination_report = observer.generate_hallucination_report()
            import json

            hallucination_file = f"hallucination_report_{results['game_id']}.json"
            with open(hallucination_file, 'w', encoding='utf-8') as f:
                json.dump(hallucination_report, f, indent=2, ensure_ascii=False)

            print(f"[OK] Hallucination report saved: {hallucination_file}")

            # Print hallucination summary
            print("\n HALLUCINATION SUMMARY :")
            print(f"   Total marks: {hallucination_report['total_hallucinations']}")
            print(f"   By type:")
            for h_type, count in hallucination_report['by_type'].items():
                print(f"      {h_type}: {count}")

        except Exception as e:
            print(f"[WARN] Could not generate hallucination report: {e}")

    # Game summary
    print("\n" + "="*80)
    print("[WIN] GAME SUMMARY ")
    print("="*80)

    summary = results['game_summary']
    metrics = results['quantified_metrics']

    print(f"\n[TARGET] Winner : {summary['winner'].upper()}")
    print(f"[TIME] Total rounds : {summary['total_rounds']}")
    print(f"[SHERIFF] Sheriff : Player {summary.get('sheriff_id', 'None')}")
    print(f"[CHART] Nash equilibrium : {summary['final_nash_score']:.3f}")
    print(f"[BALANCE] Werewolf advantage : {summary['final_werewolf_advantage']:.3f}")

    print(f"\n[STATS] METRICS :")
    print(f"   Avg deception : {metrics['avg_deception_rate']:.3f}")
    print(f"   Avg consistency : {metrics['avg_consistency_score']:.3f}")
    print(f"   Avg optimal vote : {metrics['avg_optimal_vote_ratio']:.3f}")
    print(f"   Total contradictions : {metrics['total_contradictions']}")
    print(f"   Total statements : {metrics['total_statements']}")

    print("\n" + "="*80)
    print("[OK] GAME COMPLETE! !")
    print("="*80)

    # Performance analysis option
    try:
        from performance_analyzer import analyze_game_performance

        print("\n[CHART] Generating performance analysis...")
        perf_report = f"performance_{results['game_id']}.json"
        analyze_game_performance(game_report_file, perf_report)
        print(f"[OK] Performance report saved: {perf_report}")

    except Exception as e:
        print(f"[WARN] Could not generate performance analysis: {e}")

    print("\n[TIP] NEXT STEPS :")
    print(f"   1. Review hallucination marks in: {hallucination_file if observer_started else 'N/A'}")
    print(f"   2. Analyze performance metrics: python performance_analyzer.py {game_report_file}")
    print(f"   3. Generate visualizations: python enhanced_visualizer.py {game_report_file}")
    print(f"   4. Open Web UI: python web_ui.py {game_report_file}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[STOP] Game interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()