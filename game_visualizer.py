"""
Werewolf Game Visualizer and Analyzer
Visualizes game metrics and generates analysis reports
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from pathlib import Path


class GameVisualizer:
    """Visualize game metrics and performance"""

    def __init__(self, report_path: str):
        """Load game report"""
        with open(report_path, 'r', encoding='utf-8') as f:
            self.report = json.load(f)

        self.output_dir = Path('visualizations')
        self.output_dir.mkdir(exist_ok=True)

        # Set style
        sns.set_style('whitegrid')
        plt.rcParams['figure.figsize'] = (12, 8)

    def create_all_visualizations(self):
        """Generate all visualization plots"""
        print("Generating visualizations...")

        self.plot_player_metrics_comparison()
        self.plot_deception_analysis()
        self.plot_voting_patterns()
        self.plot_consistency_scores()
        self.plot_role_performance()
        self.plot_game_timeline()
        self.plot_game_theory_metrics()

        print(f"✅ All visualizations saved to {self.output_dir}/")

    def plot_player_metrics_comparison(self):
        """Compare metrics across all players"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Player Metrics Comparison', fontsize=16, fontweight='bold')

        players = self.report['player_metrics']
        player_ids = list(players.keys())

        metrics_to_plot = [
            ('deception_attempts', 'Deception Attempts'),
            ('optimal_vote_ratio', 'Optimal Vote Ratio'),
            ('consistency_score', 'Consistency Score'),
            ('total_statements', 'Total Statements'),
            ('rounds_survived', 'Rounds Survived'),
            ('avg_statement_length', 'Avg Statement Length')
        ]

        for idx, (metric_key, metric_name) in enumerate(metrics_to_plot):
            ax = axes[idx // 3, idx % 3]

            values = [players[pid]['metrics'][metric_key] for pid in player_ids]
            roles = [players[pid]['role'] for pid in player_ids]

            # Color by role
            colors = ['red' if role == 'werewolf' else 'blue' for role in roles]

            bars = ax.bar(player_ids, values, color=colors, alpha=0.7)
            ax.set_xlabel('Player ID')
            ax.set_ylabel(metric_name)
            ax.set_title(metric_name)
            ax.tick_params(axis='x', rotation=45)

            # Add legend
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='red', alpha=0.7, label='Werewolf'),
                Patch(facecolor='blue', alpha=0.7, label='Villager Team')
            ]
            ax.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout()
        plt.savefig(self.output_dir / 'player_metrics_comparison.png', dpi=300)
        plt.close()

    def plot_deception_analysis(self):
        """Analyze deception patterns"""
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Deception Analysis', fontsize=16, fontweight='bold')

        players = self.report['player_metrics']
        player_ids = list(players.keys())

        # Deception by role
        werewolf_deceptions = []
        villager_deceptions = []

        for pid in player_ids:
            deceptions = players[pid]['metrics']['deception_attempts']
            if players[pid]['role'] == 'werewolf':
                werewolf_deceptions.append(deceptions)
            else:
                villager_deceptions.append(deceptions)

        ax = axes[0]
        data_to_plot = [werewolf_deceptions, villager_deceptions]
        ax.boxplot(data_to_plot, labels=['Werewolves', 'Villagers'])
        ax.set_ylabel('Deception Attempts')
        ax.set_title('Deception by Role')

        # Deception success rate
        ax = axes[1]
        success_rates = []
        labels = []

        for pid in player_ids:
            attempts = players[pid]['metrics']['deception_attempts']
            successes = players[pid]['metrics']['successful_deceptions']
            if attempts > 0:
                success_rates.append(successes / attempts)
                labels.append(f"P{pid}")
            else:
                success_rates.append(0)
                labels.append(f"P{pid}")

        colors = ['red' if players[pid]['role'] == 'werewolf' else 'blue' for pid in player_ids]
        ax.bar(range(len(success_rates)), success_rates, color=colors, alpha=0.7)
        ax.set_xlabel('Player')
        ax.set_ylabel('Deception Success Rate')
        ax.set_title('Deception Success Rate by Player')
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'deception_analysis.png', dpi=300)
        plt.close()

    def plot_voting_patterns(self):
        """Visualize voting patterns and optimality"""
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Voting Pattern Analysis', fontsize=16, fontweight='bold')

        players = self.report['player_metrics']
        player_ids = list(players.keys())

        # Optimal vote ratio by player
        ax = axes[0]
        vote_ratios = [players[pid]['metrics']['optimal_vote_ratio'] for pid in player_ids]
        roles = [players[pid]['role'] for pid in player_ids]
        colors = ['red' if role == 'werewolf' else 'blue' for role in roles]

        ax.bar(player_ids, vote_ratios, color=colors, alpha=0.7)
        ax.set_xlabel('Player ID')
        ax.set_ylabel('Optimal Vote Ratio')
        ax.set_title('Voting Optimality by Player')
        ax.axhline(y=0.5, color='gray', linestyle='--', label='Random baseline')
        ax.legend()

        # Vote ratio distribution by team
        ax = axes[1]
        werewolf_votes = [players[pid]['metrics']['optimal_vote_ratio']
                         for pid in player_ids if players[pid]['role'] == 'werewolf']
        villager_votes = [players[pid]['metrics']['optimal_vote_ratio']
                         for pid in player_ids if players[pid]['role'] != 'werewolf']

        data_to_plot = [werewolf_votes, villager_votes]
        ax.boxplot(data_to_plot, labels=['Werewolves', 'Villagers'])
        ax.set_ylabel('Optimal Vote Ratio')
        ax.set_title('Voting Optimality by Team')
        ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'voting_patterns.png', dpi=300)
        plt.close()

    def plot_consistency_scores(self):
        """Visualize consistency and contradiction metrics"""
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Consistency Analysis', fontsize=16, fontweight='bold')

        players = self.report['player_metrics']
        player_ids = list(players.keys())

        # Consistency scores
        ax = axes[0]
        consistency = [players[pid]['metrics']['consistency_score'] for pid in player_ids]
        roles = [players[pid]['role'] for pid in player_ids]
        colors = ['red' if role == 'werewolf' else 'blue' for role in roles]

        ax.bar(player_ids, consistency, color=colors, alpha=0.7)
        ax.set_xlabel('Player ID')
        ax.set_ylabel('Consistency Score')
        ax.set_title('Consistency Score by Player')
        ax.axhline(y=0.8, color='green', linestyle='--', label='Good threshold', alpha=0.5)
        ax.legend()

        # Contradictions count
        ax = axes[1]
        contradictions = [players[pid]['metrics']['contradictions'] for pid in player_ids]

        ax.bar(player_ids, contradictions, color=colors, alpha=0.7)
        ax.set_xlabel('Player ID')
        ax.set_ylabel('Number of Contradictions')
        ax.set_title('Contradictions by Player')

        plt.tight_layout()
        plt.savefig(self.output_dir / 'consistency_analysis.png', dpi=300)
        plt.close()

    def plot_role_performance(self):
        """Compare performance metrics by role"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle('Role-Based Performance Analysis', fontsize=16, fontweight='bold')

        players = self.report['player_metrics']

        # Group by role
        role_data = {}
        for pid, pdata in players.items():
            role = pdata['role']
            if role not in role_data:
                role_data[role] = {
                    'survival': [],
                    'consistency': [],
                    'optimal_votes': [],
                    'statements': []
                }

            role_data[role]['survival'].append(pdata['metrics']['rounds_survived'])
            role_data[role]['consistency'].append(pdata['metrics']['consistency_score'])
            role_data[role]['optimal_votes'].append(pdata['metrics']['optimal_vote_ratio'])
            role_data[role]['statements'].append(pdata['metrics']['total_statements'])

        roles = list(role_data.keys())

        # Survival by role
        ax = axes[0, 0]
        survival_data = [role_data[role]['survival'] for role in roles]
        ax.boxplot(survival_data, labels=roles)
        ax.set_ylabel('Rounds Survived')
        ax.set_title('Survival by Role')
        ax.tick_params(axis='x', rotation=45)

        # Consistency by role
        ax = axes[0, 1]
        consistency_data = [role_data[role]['consistency'] for role in roles]
        ax.boxplot(consistency_data, labels=roles)
        ax.set_ylabel('Consistency Score')
        ax.set_title('Consistency by Role')
        ax.tick_params(axis='x', rotation=45)

        # Optimal votes by role
        ax = axes[1, 0]
        votes_data = [role_data[role]['optimal_votes'] for role in roles]
        ax.boxplot(votes_data, labels=roles)
        ax.set_ylabel('Optimal Vote Ratio')
        ax.set_title('Voting Optimality by Role')
        ax.tick_params(axis='x', rotation=45)

        # Statements by role
        ax = axes[1, 1]
        statements_data = [role_data[role]['statements'] for role in roles]
        ax.boxplot(statements_data, labels=roles)
        ax.set_ylabel('Total Statements')
        ax.set_title('Communication by Role')
        ax.tick_params(axis='x', rotation=45)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'role_performance.png', dpi=300)
        plt.close()

    def plot_game_timeline(self):
        """Visualize game progression timeline"""
        fig, axes = plt.subplots(2, 1, figsize=(15, 10))
        fig.suptitle('Game Timeline', fontsize=16, fontweight='bold')

        event_log = self.report['event_log']

        # Deaths over time
        ax = axes[0]
        rounds = []
        deaths_per_round = []
        death_types = {'night': [], 'day': []}

        current_round = 0
        for event in event_log:
            if event['event_type'] == 'night_deaths':
                round_num = event['round']
                if round_num != current_round:
                    current_round = round_num
                    rounds.append(round_num)
                    death_types['night'].append(len(event['data'].get('player_ids', [])))
                    death_types['day'].append(0)

            elif event['event_type'] == 'day_elimination':
                if rounds and rounds[-1] == event['round']:
                    death_types['day'][-1] += 1
                else:
                    rounds.append(event['round'])
                    death_types['night'].append(0)
                    death_types['day'].append(1)

        if rounds:
            x = np.arange(len(rounds))
            width = 0.35

            ax.bar(x - width/2, death_types['night'], width, label='Night Deaths', color='darkblue', alpha=0.7)
            ax.bar(x + width/2, death_types['day'], width, label='Day Eliminations', color='orange', alpha=0.7)

            ax.set_xlabel('Round')
            ax.set_ylabel('Number of Deaths')
            ax.set_title('Deaths Per Round')
            ax.set_xticks(x)
            ax.set_xticklabels(rounds)
            ax.legend()

        # Player count over time
        ax = axes[1]
        total_players = len(self.report['player_metrics'])
        alive_count = [total_players]
        round_markers = [0]

        current_alive = total_players
        for i, event in enumerate(event_log):
            if event['event_type'] in ['night_deaths', 'day_elimination']:
                if event['event_type'] == 'night_deaths':
                    current_alive -= len(event['data'].get('player_ids', []))
                else:
                    current_alive -= 1

                alive_count.append(current_alive)
                round_markers.append(event['round'])

        ax.plot(round_markers, alive_count, marker='o', linewidth=2, markersize=8)
        ax.set_xlabel('Round')
        ax.set_ylabel('Players Alive')
        ax.set_title('Player Count Over Time')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'game_timeline.png', dpi=300)
        plt.close()

    def plot_game_theory_metrics(self):
        """Visualize game theory metrics"""
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle('Game Theory Analysis', fontsize=16, fontweight='bold')

        # Nash equilibrium and werewolf advantage
        ax = axes[0]
        summary = self.report['game_summary']

        metrics = ['Nash Equilibrium\nScore', 'Werewolf\nAdvantage']
        values = [
            summary.get('final_nash_score', 0),
            (summary.get('final_werewolf_advantage', 0) + 1) / 2  # Normalize to 0-1
        ]

        colors = ['green', 'red']
        bars = ax.bar(metrics, values, color=colors, alpha=0.7)
        ax.set_ylabel('Score (0-1)')
        ax.set_title('Final Game Theory Metrics')
        ax.set_ylim(0, 1)

        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{value:.3f}',
                   ha='center', va='bottom')

        # Aggregate metrics
        ax = axes[1]
        agg_metrics = self.report['quantified_metrics']

        metric_names = [
            'Avg Deception\nRate',
            'Avg Consistency\nScore',
            'Avg Optimal\nVote Ratio'
        ]

        metric_values = [
            agg_metrics.get('avg_deception_rate', 0),
            agg_metrics.get('avg_consistency_score', 0),
            agg_metrics.get('avg_optimal_vote_ratio', 0)
        ]

        bars = ax.bar(metric_names, metric_values, color=['orange', 'blue', 'purple'], alpha=0.7)
        ax.set_ylabel('Score')
        ax.set_title('Aggregate Performance Metrics')

        # Add value labels
        for bar, value in zip(bars, metric_values):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{value:.3f}',
                   ha='center', va='bottom')

        plt.tight_layout()
        plt.savefig(self.output_dir / 'game_theory_metrics.png', dpi=300)
        plt.close()

    def generate_text_report(self, output_file: str = 'analysis_report.txt'):
        """Generate detailed text analysis report"""
        report_path = self.output_dir / output_file

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("WEREWOLF GAME ANALYSIS REPORT\n")
            f.write("="*80 + "\n\n")

            # Game summary
            summary = self.report['game_summary']
            f.write("GAME SUMMARY\n")
            f.write("-" * 40 + "\n")
            f.write(f"Winner: {summary['winner']}\n")
            f.write(f"Total Rounds: {summary['total_rounds']}\n")
            f.write(f"Nash Equilibrium Score: {summary.get('final_nash_score', 0):.3f}\n")
            f.write(f"Werewolf Advantage: {summary.get('final_werewolf_advantage', 0):.3f}\n\n")

            # Aggregate metrics
            f.write("AGGREGATE METRICS\n")
            f.write("-" * 40 + "\n")
            agg = self.report['quantified_metrics']
            for key, value in agg.items():
                f.write(f"{key}: {value:.3f}\n")
            f.write("\n")

            # Player performance
            f.write("PLAYER PERFORMANCE\n")
            f.write("-" * 40 + "\n")
            players = self.report['player_metrics']

            for pid, pdata in sorted(players.items(), key=lambda x: int(x[0])):
                f.write(f"\nPlayer {pid} ({pdata['role']}) - {pdata['final_status']}\n")
                metrics = pdata['metrics']

                f.write(f"  Outcome: {metrics['final_outcome']}\n")
                f.write(f"  Rounds Survived: {metrics['rounds_survived']}\n")
                f.write(f"  Deception Attempts: {metrics['deception_attempts']}\n")
                f.write(f"  Consistency Score: {metrics['consistency_score']:.3f}\n")
                f.write(f"  Optimal Vote Ratio: {metrics['optimal_vote_ratio']:.3f}\n")
                f.write(f"  Total Statements: {metrics['total_statements']}\n")

            # Role analysis
            f.write("\n\nROLE ANALYSIS\n")
            f.write("-" * 40 + "\n")

            role_stats = {}
            for pid, pdata in players.items():
                role = pdata['role']
                if role not in role_stats:
                    role_stats[role] = {
                        'count': 0,
                        'won': 0,
                        'avg_survival': 0,
                        'avg_consistency': 0
                    }

                role_stats[role]['count'] += 1
                if pdata['metrics']['final_outcome'] == 'won':
                    role_stats[role]['won'] += 1
                role_stats[role]['avg_survival'] += pdata['metrics']['rounds_survived']
                role_stats[role]['avg_consistency'] += pdata['metrics']['consistency_score']

            for role, stats in role_stats.items():
                count = stats['count']
                f.write(f"\n{role.upper()}\n")
                f.write(f"  Count: {count}\n")
                f.write(f"  Win Rate: {stats['won'] / count:.2%}\n")
                f.write(f"  Avg Survival: {stats['avg_survival'] / count:.2f} rounds\n")
                f.write(f"  Avg Consistency: {stats['avg_consistency'] / count:.3f}\n")

            # Key insights
            f.write("\n\nKEY INSIGHTS\n")
            f.write("-" * 40 + "\n")

            # Find best performer
            best_consistency = max(players.items(),
                                  key=lambda x: x[1]['metrics']['consistency_score'])
            f.write(f"Most Consistent Player: Player {best_consistency[0]} "
                   f"({best_consistency[1]['metrics']['consistency_score']:.3f})\n")

            best_votes = max(players.items(),
                           key=lambda x: x[1]['metrics']['optimal_vote_ratio'])
            f.write(f"Best Strategic Voter: Player {best_votes[0]} "
                   f"({best_votes[1]['metrics']['optimal_vote_ratio']:.3f})\n")

            most_deceptive = max(players.items(),
                               key=lambda x: x[1]['metrics']['deception_attempts'])
            f.write(f"Most Deceptive Player: Player {most_deceptive[0]} "
                   f"({most_deceptive[1]['metrics']['deception_attempts']} attempts)\n")

            # Overall assessment
            f.write("\n\nOVERALL ASSESSMENT\n")
            f.write("-" * 40 + "\n")

            avg_consistency = agg['avg_consistency_score']
            if avg_consistency > 0.8:
                f.write("✓ High consistency across players - low hallucination risk\n")
            elif avg_consistency > 0.6:
                f.write("⚠ Moderate consistency - some contradictions observed\n")
            else:
                f.write("✗ Low consistency - significant hallucination concerns\n")

            avg_optimal = agg['avg_optimal_vote_ratio']
            if avg_optimal > 0.6:
                f.write("✓ Strong strategic reasoning in voting behavior\n")
            elif avg_optimal > 0.4:
                f.write("⚠ Moderate strategic capability\n")
            else:
                f.write("✗ Poor strategic decision-making\n")

            f.write("\n" + "="*80 + "\n")

        print(f"📄 Text report saved to {report_path}")


def main():
    """Example usage"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python game_visualizer.py <report_json_path>")
        print("Example: python game_visualizer.py werewolf_game_report.json")
        sys.exit(1)

    report_path = sys.argv[1]

    visualizer = GameVisualizer(report_path)
    visualizer.create_all_visualizations()
    visualizer.generate_text_report()

    print("\n✅ Analysis complete!")


if __name__ == '__main__':
    main()
