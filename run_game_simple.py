"""
Simple werewolf game runner without interactive features
"""

from werewolf_game import WerewolfGame
import sys


def main():
    """Run game without interactive observer"""

    # LLM configuration
    llm_config = {
        'api_base': 'http://localhost:8080',
        'model': '/home/apulis-dev/userdata/Llama-3.3-70B-Instruct',
        'temperature': 0.7,
        'max_tokens': 500
    }

    print("="*70)
    print("WEREWOLF GAME - SIMPLE RUNNER")
    print("="*70)
    print(f"\n[CONFIG]")
    print(f"  API: {llm_config['api_base']}")
    print(f"  Model: {llm_config['model']}")
    print(f"  Temperature: {llm_config['temperature']}")

    print(f"\n[PLAYERS] 13 players total:")
    print("  - 1 Werewolf King + 3 Werewolves")
    print("  - 1 Seer, 1 Witch, 1 Hunter, 1 Guard")
    print("  - 4 Villagers")
    print("  - 1 Judge (non-participant)")

    print(f"\n[RULES]")
    print("  - Werewolves and Seer MUST campaign for sheriff")
    print("  - Others campaign voluntarily")
    print("  - Judge observes but doesn't participate")

    # Test API
    try:
        import requests
        print("\n[TEST] Testing API connection...")
        response = requests.get(f"{llm_config['api_base']}/v1/models", timeout=5)
        if response.status_code == 200:
            print("[OK] API connected!")
        else:
            print(f"[WARN] API status: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Cannot connect: {e}")
        sys.exit(1)

    print("\n" + "="*70)
    print("[GAME] Starting game...")
    print("="*70 + "\n")

    # Create and run game
    game = WerewolfGame(num_players=13, llm_api_config=llm_config)

    try:
        results = game.play_game()

        # Save report
        report_file = 'game_report.json'
        game.save_report(report_file)

        # Print summary
        print("\n" + "="*70)
        print("GAME SUMMARY")
        print("="*70)

        summary = results['game_summary']
        metrics = results['quantified_metrics']

        print(f"\n[RESULT]")
        print(f"  Winner: {summary['winner'].upper()}")
        print(f"  Total Rounds: {summary['total_rounds']}")
        print(f"  Sheriff: Player {summary.get('sheriff_id', 'None')}")

        print(f"\n[METRICS]")
        print(f"  Avg Deception: {metrics['avg_deception_rate']:.3f}")
        print(f"  Avg Consistency: {metrics['avg_consistency_score']:.3f}")
        print(f"  Avg Optimal Vote: {metrics['avg_optimal_vote_ratio']:.3f}")
        print(f"  Contradictions: {metrics['total_contradictions']}")

        print(f"\n[SAVE] Report saved to: {report_file}")

        print("\n" + "="*70)
        print("[COMPLETE] Game finished successfully!")
        print("="*70)

    except KeyboardInterrupt:
        print("\n[STOP] Game interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Game failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()