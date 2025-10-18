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
        'api_base': 'http://172.28.32.1:1234',  # 你的本地LLM服务器地址
        'model': 'meta-llama-3.1-8b-instruct',  # 模型名称
        'temperature': 0.7,                      # 温度参数，控制随机性
        'max_tokens': 500                        # 最大生成token数
    }

    print("="*70)
    print("[WOLF]  LLM ")
    print("="*70)
    print(f"\n[API] API: {llm_config['api_base']}")
    print(f"[BOT] : {llm_config['model']}")
    print(f"[TEMP] : {llm_config['temperature']}")
    print(f"[TEXT] Max Tokens: {llm_config['max_tokens']}")
    print(f"\n[PEOPLE] : 13")
    print("   - 1 [KING][WOLF]")
    print("   - 3 [WOLF]")
    print("   - 1 [SEER]")
    print("   - 1 [WITCH]")
    print("   - 1 [TARGET]")
    print("   - 1 [GUARD]")
    print("   - 4 ")
    print("   - 1 [JUDGE] ()")
    print("\n" + "="*70)

    try:
        # 测试API连接
        print("\n[TEST] API...")
        import requests
        response = requests.get(f"{llm_config['api_base']}/v1/models", timeout=5)
        if response.status_code == 200:
            print("[OK] API!")
        else:
            print(f"[WARN] API: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] API: {e}")
        print(f"\nLLM: {llm_config['api_base']}")
        sys.exit(1)

    # 启动实时观战系统
    observer_started = False
    try:
        from realtime_observer import start_observer_server, start_interactive_judge
        import threading
        import webbrowser
        import time

        print("\n ...")

        # 启动WebSocket服务器
        server_thread = threading.Thread(target=start_observer_server, daemon=True)
        server_thread.start()
        time.sleep(1)  # 等待服务器启动

        # 启动交互式裁判
        judge_thread = threading.Thread(target=start_interactive_judge, daemon=True)
        judge_thread.start()

        print("[OK] !")
        print("[VIEW]  observer_ui.html ")
        print("[JUDGE]  'mark' \n")

        observer_started = True

        # 可选：自动打开浏览器
        import os
        ui_path = os.path.join(os.path.dirname(__file__), 'observer_ui.html')
        webbrowser.open(f'file://{ui_path}')

    except Exception as e:
        print(f"[WARN] : {e}")
        print("...\n")

    print("\n ...")
    print("="*70 + "\n")

    # 创建并运行游戏
    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    results = game.play_game()

    # 保存报告
    report_file = 'werewolf_game_report.json'
    game.save_report(report_file)

    # 打印摘要
    print("\n" + "="*70)
    print("[STATS] ")
    print("="*70)

    summary = results['game_summary']
    metrics = results['quantified_metrics']

    print(f"\n[WIN] : {summary['winner'].upper()}")
    print(f"[TIME] : {summary['total_rounds']}")
    print(f"[SHERIFF] : Player {summary.get('sheriff_id', 'None')}")
    print(f"[TARGET] : {summary['final_nash_score']:.3f}")
    print(f"[BALANCE] : {summary['final_werewolf_advantage']:.3f}")
    print(f"\n[CLOCK] :")
    print(f"   ID: {results.get('game_id', 'N/A')}")
    print(f"   : {summary.get('start_time', 'N/A')}")
    print(f"   : {summary.get('end_time', 'N/A')}")

    print(f"\n[CHART] :")
    print(f"   : {metrics['avg_deception_rate']:.3f}")
    print(f"   : {metrics['avg_consistency_score']:.3f}")
    print(f"   : {metrics['avg_optimal_vote_ratio']:.3f}")
    print(f"   : {metrics['total_contradictions']}")
    print(f"   : {metrics['total_statements']}")

    print(f"\n[SAVE] : {report_file}")

    # 生成性能分析报告
    print("\n[STATS] ...")
    try:
        from performance_analyzer import analyze_game_performance
        perf_report = 'performance_report.json'
        analyze_game_performance(report_file, perf_report)
        print(f"[OK] : {perf_report}")
    except Exception as e:
        print(f"[WARN] : {e}")
        perf_report = None

    # 生成增强可视化
    print("\n[CHART] ...")
    try:
        from enhanced_visualizer import EnhancedVisualizer
        visualizer = EnhancedVisualizer(report_file, perf_report)
        visualizer.create_all_visualizations()
        visualizer.generate_summary_report()
        print("[OK]  visualizations/ ")
    except Exception as e:
        print(f"[WARN] : {e}")

    print(f"\n[TIP] :")
    print(f"   1. :  visualizations/ ")
    print(f"   2. Web UI: python web_ui.py {report_file} {perf_report if perf_report else ''}")
    print(f"   3. : python game_visualizer.py {report_file}")

    # 询问是否启动Web UI
    print("\n" + "="*70)
    try:
        response = input("是否启动Web UI查看详细分析? (y/n): ").strip().lower()
        if response == 'y':
            from web_ui import run_dashboard
            run_dashboard(report_file, perf_report)
    except KeyboardInterrupt:
        print("\n")

    print("\n" + "="*70)
    print("[OK] !")
    print("="*70)


if __name__ == '__main__':
    main()
