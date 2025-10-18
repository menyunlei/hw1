"""
Quick start script for running Werewolf game with local LLM
配置好后直接运行此脚本启动游戏
"""

from werewolf_game import WerewolfGame
import sys


def main():
    """运行游戏"""

    # 本地LLM API配置
    llm_config = {
        'api_base': 'http://localhost:8080',  # 你的本地LLM服务器地址
        'model': '/home/apulis-dev/userdata/Llama-3.3-70B-Instruct',  # 模型名称
        'temperature': 0.7,                      # 温度参数，控制随机性
        'max_tokens': 500                        # 最大生成token数
    }

    print("="*70)
    print("WEREWOLF GAME - LLM EVALUATION SYSTEM")
    print("狼人杀 LLM 评估系统")
    print("="*70)
    print(f"\n[API] Address: {llm_config['api_base']}")
    print(f"[MODEL] {llm_config['model']}")
    print(f"[TEMP] Temperature: {llm_config['temperature']}")
    print(f"[TOKENS] Max Tokens: {llm_config['max_tokens']}")
    print(f"\n[PLAYERS] Total: 13")
    print("   - 1 Werewolf King (狼王)")
    print("   - 3 Werewolves (狼人)")
    print("   - 1 Seer (预言家)")
    print("   - 1 Witch (女巫)")
    print("   - 1 Hunter (猎人)")
    print("   - 1 Guard (守卫)")
    print("   - 4 Villagers (村民)")
    print("   - 1 Judge (裁判) - For marking hallucinations")

    print("\n[SHERIFF ELECTION RULES]")
    print("   * Werewolves MUST campaign (强制上警)")
    print("   * Seer MUST campaign (强制上警)")
    print("   * Others campaign voluntarily (自愿上警)")
    print("\n" + "="*70)

    try:
        # 测试API连接
        print("\n[TEST] Testing API connection...")
        import requests
        response = requests.get(f"{llm_config['api_base']}/v1/models", timeout=5)
        if response.status_code == 200:
            print("[OK] API connected successfully!")
        else:
            print(f"[WARN] API returned status: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] Cannot connect to API: {e}")
        print(f"\nPlease ensure LLM server is running at: {llm_config['api_base']}")
        sys.exit(1)

    # 启动实时观战系统
    observer_started = False
    try:
        from realtime_observer import start_observer_server, start_interactive_judge
        import threading
        import webbrowser
        import time

        print("\n[OBSERVER] Starting real-time observation system...")

        # 启动WebSocket服务器
        server_thread = threading.Thread(target=start_observer_server, daemon=True)
        server_thread.start()
        time.sleep(1)  # 等待服务器启动

        # 启动交互式裁判
        judge_thread = threading.Thread(target=start_interactive_judge, daemon=True)
        judge_thread.start()

        print("[OK] Real-time observation system started!")
        print("    Open observer_ui.html in browser to watch live")
        print("    Type 'mark' commands in console to mark hallucinations\n")

        observer_started = True

        # 可选：自动打开浏览器
        import os
        ui_path = os.path.join(os.path.dirname(__file__), 'observer_ui.html')
        webbrowser.open(f'file://{ui_path}')

    except Exception as e:
        print(f"[WARN] Cannot start observer: {e}")
        print("Continuing without observation features...\n")

    print("\n[GAME] Starting game...")
    print("="*70 + "\n")

    # 创建并运行游戏
    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    results = game.play_game()

    # 保存报告
    report_file = 'werewolf_game_report.json'
    game.save_report(report_file)

    # 打印摘要
    print("\n" + "="*70)
    print("GAME ANALYSIS SUMMARY")
    print("游戏分析摘要")
    print("="*70)

    summary = results['game_summary']
    metrics = results['quantified_metrics']

    print(f"\n[WINNER] {summary['winner'].upper()}")
    print(f"[ROUNDS] Total: {summary['total_rounds']}")
    print(f"[SHERIFF] Player {summary.get('sheriff_id', 'None')}")
    print(f"[NASH] Equilibrium Score: {summary['final_nash_score']:.3f}")
    print(f"[ADVANTAGE] Werewolf: {summary['final_werewolf_advantage']:.3f}")

    print(f"\n[TIMESTAMP]")
    print(f"   Game ID: {results.get('game_id', 'N/A')}")
    print(f"   Start: {summary.get('start_time', 'N/A')}")
    print(f"   End: {summary.get('end_time', 'N/A')}")

    print(f"\n[METRICS]")
    print(f"   Avg Deception Rate: {metrics['avg_deception_rate']:.3f}")
    print(f"   Avg Consistency: {metrics['avg_consistency_score']:.3f}")
    print(f"   Avg Optimal Vote Ratio: {metrics['avg_optimal_vote_ratio']:.3f}")
    print(f"   Total Contradictions: {metrics['total_contradictions']}")
    print(f"   Total Statements: {metrics['total_statements']}")

    print(f"\n[SAVE] Detailed report saved to: {report_file}")

    # 生成性能分析报告
    print("\n[ANALYSIS] Generating performance analysis...")
    try:
        from performance_analyzer import analyze_game_performance
        perf_report = 'performance_report.json'
        analyze_game_performance(report_file, perf_report)
        print(f"[OK] Performance report saved to: {perf_report}")
    except Exception as e:
        print(f"[WARN] Performance analysis failed: {e}")
        perf_report = None

    # 生成增强可视化
    print("\n[VISUALIZE] Generating enhanced visualizations...")
    try:
        from enhanced_visualizer import EnhancedVisualizer
        visualizer = EnhancedVisualizer(report_file, perf_report)
        visualizer.create_all_visualizations()
        visualizer.generate_summary_report()
        print("[OK] Visualizations saved to visualizations/ directory")
    except Exception as e:
        print(f"[WARN] Visualization failed: {e}")

    print(f"\n[NEXT STEPS]")
    print(f"   1. View visualizations: Open visualizations/ directory")
    print(f"   2. Start Web UI: python web_ui.py {report_file} {perf_report if perf_report else ''}")
    print(f"   3. Traditional viz: python game_visualizer.py {report_file}")

    # 询问是否启动Web UI
    print("\n" + "="*70)
    try:
        response = input("Start Web UI for detailed analysis? (y/n): ").strip().lower()
        if response == 'y':
            from web_ui import run_dashboard
            run_dashboard(report_file, perf_report)
    except KeyboardInterrupt:
        print("\n")

    print("\n" + "="*70)
    print("[COMPLETE] Game finished successfully!")
    print("="*70)


if __name__ == '__main__':
    main()