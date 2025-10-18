"""
Example Usage of Werewolf Game Framework
Demonstrates various ways to use the system for LLM evaluation
"""

from werewolf_game import WerewolfGame, Role
from game_visualizer import GameVisualizer
import json


def example_1_basic_game():
    """Example 1: Run a basic game with default settings"""
    print("="*60)
    print("Example 1: Basic Game")
    print("="*60)

    # Configure LLM API (replace with your actual API)
    llm_config = {
        'api_key': 'your-api-key-here',
        'model': 'gpt-4',  # or 'gpt-3.5-turbo', 'claude-3-opus', etc.
        'temperature': 0.7,
        'max_tokens': 500
    }

    # Create game
    game = WerewolfGame(num_players=13, llm_api_config=llm_config)

    # Play complete game
    results = game.play_game()

    # Save report
    game.save_report('example1_report.json')

    # Print summary
    print("\nGame Summary:")
    print(f"Winner: {results['game_summary']['winner']}")
    print(f"Rounds: {results['game_summary']['total_rounds']}")
    print(f"Average Consistency: {results['quantified_metrics']['avg_consistency_score']:.3f}")

    return results


def example_2_compare_models():
    """Example 2: Compare different LLM models"""
    print("\n" + "="*60)
    print("Example 2: Model Comparison")
    print("="*60)

    models = [
        {'name': 'gpt-4', 'temperature': 0.7},
        {'name': 'gpt-3.5-turbo', 'temperature': 0.7},
        # Add more models to compare
    ]

    results_comparison = {}

    for model_config in models:
        print(f"\nTesting model: {model_config['name']}")

        llm_config = {
            'api_key': 'your-api-key',
            'model': model_config['name'],
            'temperature': model_config['temperature'],
            'max_tokens': 500
        }

        game = WerewolfGame(num_players=13, llm_api_config=llm_config)
        results = game.play_game()

        # Store results
        results_comparison[model_config['name']] = {
            'winner': results['game_summary']['winner'],
            'rounds': results['game_summary']['total_rounds'],
            'metrics': results['quantified_metrics']
        }

        game.save_report(f"comparison_{model_config['name']}.json")

    # Print comparison
    print("\n" + "-"*60)
    print("Model Comparison Results:")
    print("-"*60)

    for model, data in results_comparison.items():
        print(f"\n{model}:")
        print(f"  Winner: {data['winner']}")
        print(f"  Rounds: {data['rounds']}")
        print(f"  Avg Consistency: {data['metrics']['avg_consistency_score']:.3f}")
        print(f"  Avg Deception Rate: {data['metrics']['avg_deception_rate']:.3f}")
        print(f"  Avg Optimal Votes: {data['metrics']['avg_optimal_vote_ratio']:.3f}")

    return results_comparison


def example_3_temperature_experiment():
    """Example 3: Test different temperature settings"""
    print("\n" + "="*60)
    print("Example 3: Temperature Sensitivity Analysis")
    print("="*60)

    temperatures = [0.3, 0.5, 0.7, 0.9]
    temp_results = {}

    for temp in temperatures:
        print(f"\nTesting temperature: {temp}")

        llm_config = {
            'api_key': 'your-api-key',
            'model': 'gpt-4',
            'temperature': temp,
            'max_tokens': 500
        }

        game = WerewolfGame(num_players=13, llm_api_config=llm_config)
        results = game.play_game()

        temp_results[temp] = results['quantified_metrics']
        game.save_report(f"temp_{temp}_report.json")

    # Analysis
    print("\n" + "-"*60)
    print("Temperature Analysis:")
    print("-"*60)

    for temp, metrics in temp_results.items():
        print(f"\nTemperature {temp}:")
        print(f"  Consistency: {metrics['avg_consistency_score']:.3f}")
        print(f"  Deception: {metrics['avg_deception_rate']:.3f}")
        print(f"  Strategic Voting: {metrics['avg_optimal_vote_ratio']:.3f}")

    return temp_results


def example_4_multiple_runs():
    """Example 4: Run multiple games for statistical significance"""
    print("\n" + "="*60)
    print("Example 4: Multiple Runs for Statistics")
    print("="*60)

    num_runs = 5
    llm_config = {
        'api_key': 'your-api-key',
        'model': 'gpt-4',
        'temperature': 0.7,
        'max_tokens': 500
    }

    all_results = []

    for run in range(num_runs):
        print(f"\nRun {run + 1}/{num_runs}")

        game = WerewolfGame(num_players=13, llm_api_config=llm_config)
        results = game.play_game()

        all_results.append(results)
        game.save_report(f"run_{run+1}_report.json")

    # Calculate aggregate statistics
    print("\n" + "-"*60)
    print("Aggregate Statistics:")
    print("-"*60)

    metrics_to_aggregate = [
        'avg_consistency_score',
        'avg_deception_rate',
        'avg_optimal_vote_ratio'
    ]

    for metric in metrics_to_aggregate:
        values = [r['quantified_metrics'][metric] for r in all_results]
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5

        print(f"\n{metric}:")
        print(f"  Mean: {mean:.3f}")
        print(f"  Std Dev: {std:.3f}")
        print(f"  Min: {min(values):.3f}")
        print(f"  Max: {max(values):.3f}")

    # Werewolf win rate
    werewolf_wins = sum(1 for r in all_results
                       if r['game_summary']['winner'] == 'werewolves')
    win_rate = werewolf_wins / num_runs

    print(f"\nWerewolf Win Rate: {win_rate:.2%}")

    return all_results


def example_5_role_analysis():
    """Example 5: Analyze performance by role"""
    print("\n" + "="*60)
    print("Example 5: Role-Based Performance Analysis")
    print("="*60)

    llm_config = {
        'api_key': 'your-api-key',
        'model': 'gpt-4',
        'temperature': 0.7,
        'max_tokens': 500
    }

    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    results = game.play_game()
    game.save_report('role_analysis_report.json')

    # Analyze by role
    players = results['player_metrics']
    role_stats = {}

    for player_id, player_data in players.items():
        role = player_data['role']
        metrics = player_data['metrics']

        if role not in role_stats:
            role_stats[role] = {
                'consistency': [],
                'survival': [],
                'optimal_votes': [],
                'deceptions': []
            }

        role_stats[role]['consistency'].append(metrics['consistency_score'])
        role_stats[role]['survival'].append(metrics['rounds_survived'])
        role_stats[role]['optimal_votes'].append(metrics['optimal_vote_ratio'])
        role_stats[role]['deceptions'].append(metrics['deception_attempts'])

    # Print analysis
    print("\n" + "-"*60)
    print("Performance by Role:")
    print("-"*60)

    for role, stats in role_stats.items():
        print(f"\n{role.upper()}:")
        print(f"  Avg Consistency: {sum(stats['consistency'])/len(stats['consistency']):.3f}")
        print(f"  Avg Survival: {sum(stats['survival'])/len(stats['survival']):.2f} rounds")
        print(f"  Avg Optimal Votes: {sum(stats['optimal_votes'])/len(stats['optimal_votes']):.3f}")
        print(f"  Avg Deceptions: {sum(stats['deceptions'])/len(stats['deceptions']):.2f}")

    return role_stats


def example_6_visualization():
    """Example 6: Generate visualizations"""
    print("\n" + "="*60)
    print("Example 6: Generate Visualizations")
    print("="*60)

    # First run a game
    llm_config = {
        'api_key': 'your-api-key',
        'model': 'gpt-4',
        'temperature': 0.7,
        'max_tokens': 500
    }

    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    results = game.play_game()
    game.save_report('visualization_report.json')

    # Create visualizations
    print("\nGenerating visualizations...")
    visualizer = GameVisualizer('visualization_report.json')
    visualizer.create_all_visualizations()
    visualizer.generate_text_report()

    print("✅ Visualizations saved to 'visualizations/' folder")

    return visualizer


def example_7_custom_evaluation():
    """Example 7: Custom evaluation metrics"""
    print("\n" + "="*60)
    print("Example 7: Custom Evaluation Metrics")
    print("="*60)

    llm_config = {
        'api_key': 'your-api-key',
        'model': 'gpt-4',
        'temperature': 0.7,
        'max_tokens': 500
    }

    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    results = game.play_game()

    # Custom analysis: Identify best deceiver
    players = results['player_metrics']

    werewolf_performance = []
    for player_id, player_data in players.items():
        if player_data['role'] == 'werewolf':
            metrics = player_data['metrics']
            deception_score = 0

            # Calculate custom deception effectiveness score
            if metrics['deception_attempts'] > 0:
                success_rate = metrics['successful_deceptions'] / metrics['deception_attempts']
                deception_score = success_rate * metrics['consistency_score']

            werewolf_performance.append({
                'player_id': player_id,
                'deception_score': deception_score,
                'survival': metrics['rounds_survived'],
                'outcome': metrics['final_outcome']
            })

    # Print results
    print("\nWerewolf Performance Rankings:")
    print("-"*60)

    werewolf_performance.sort(key=lambda x: x['deception_score'], reverse=True)

    for i, wolf in enumerate(werewolf_performance, 1):
        print(f"{i}. Player {wolf['player_id']}:")
        print(f"   Deception Score: {wolf['deception_score']:.3f}")
        print(f"   Survived: {wolf['survival']} rounds")
        print(f"   Outcome: {wolf['outcome']}")

    return werewolf_performance


def example_8_batch_evaluation():
    """Example 8: Batch evaluation with different prompts"""
    print("\n" + "="*60)
    print("Example 8: Batch Evaluation")
    print("="*60)

    # Test different strategic approaches
    strategies = {
        'aggressive': 0.9,  # Higher temperature, more creative
        'conservative': 0.3,  # Lower temperature, more predictable
        'balanced': 0.7  # Medium temperature
    }

    strategy_results = {}

    for strategy_name, temperature in strategies.items():
        print(f"\nTesting strategy: {strategy_name} (temp={temperature})")

        llm_config = {
            'api_key': 'your-api-key',
            'model': 'gpt-4',
            'temperature': temperature,
            'max_tokens': 500
        }

        game = WerewolfGame(num_players=13, llm_api_config=llm_config)
        results = game.play_game()

        strategy_results[strategy_name] = {
            'temperature': temperature,
            'winner': results['game_summary']['winner'],
            'rounds': results['game_summary']['total_rounds'],
            'consistency': results['quantified_metrics']['avg_consistency_score'],
            'deception': results['quantified_metrics']['avg_deception_rate']
        }

        game.save_report(f"strategy_{strategy_name}_report.json")

    # Compare strategies
    print("\n" + "-"*60)
    print("Strategy Comparison:")
    print("-"*60)

    for strategy, data in strategy_results.items():
        print(f"\n{strategy.upper()} (temp={data['temperature']}):")
        print(f"  Winner: {data['winner']}")
        print(f"  Rounds: {data['rounds']}")
        print(f"  Consistency: {data['consistency']:.3f}")
        print(f"  Deception Rate: {data['deception']:.3f}")

    return strategy_results


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("WEREWOLF GAME - EXAMPLE USAGE")
    print("="*60)

    print("\nIMPORTANT: Before running, make sure to:")
    print("1. Install dependencies: pip install matplotlib seaborn pandas numpy")
    print("2. Configure your LLM API in the LLMAgent.call_llm() method")
    print("3. Replace 'your-api-key' with your actual API key")

    # Uncomment the examples you want to run:

    # example_1_basic_game()
    # example_2_compare_models()
    # example_3_temperature_experiment()
    # example_4_multiple_runs()
    # example_5_role_analysis()
    # example_6_visualization()
    # example_7_custom_evaluation()
    # example_8_batch_evaluation()

    print("\n" + "="*60)
    print("Examples complete! Check the generated reports and visualizations.")
    print("="*60)


if __name__ == '__main__':
    main()
