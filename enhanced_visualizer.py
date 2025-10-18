"""
Enhanced Visualizer with Performance Trends and Adversarial Details
可视化性能变化趋势和对抗细节
"""

import json
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from performance_analyzer import PerformanceAnalyzer


class EnhancedVisualizer:
    """Enhanced visualization with performance metrics and adversarial details"""

    def __init__(self, game_report_path: str, performance_report_path: str = None):
        with open(game_report_path, 'r', encoding='utf-8') as f:
            self.game_report = json.load(f)

        if performance_report_path:
            with open(performance_report_path, 'r', encoding='utf-8') as f:
                self.performance_report = json.load(f)
        else:
            # Generate performance report
            analyzer = PerformanceAnalyzer(self.game_report)
            self.performance_report = analyzer.generate_performance_report()

        self.output_dir = Path('visualizations')
        self.output_dir.mkdir(exist_ok=True)

        sns.set_style('whitegrid')
        plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

    def create_all_visualizations(self):
        """Generate all enhanced visualizations"""
        print("Generating enhanced visualizations...")

        self.plot_performance_radar()
        self.plot_performance_heatmap()
        self.plot_adversarial_timeline()
        self.plot_deception_network()
        self.plot_strategy_evolution()
        self.plot_hallucination_analysis()

        print(f"✅ All visualizations saved to {self.output_dir}/")

    def plot_performance_radar(self):
        """Radar chart showing multi-dimensional performance"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12), subplot_kw=dict(projection='polar'))
        fig.suptitle('Multi-Dimensional Performance Analysis\n多维度性能分析', fontsize=16, fontweight='bold')

        player_data = self.performance_report['player_performance']
        axes = axes.flatten()

        dimensions = ['Deception\n欺骗', 'Cooperation\n合作', 'Adversarial\n对抗',
                     'Anti-Hallucination\n抗幻觉', 'Strategic\n策略']

        for idx, (player_id, data) in enumerate(list(player_data.items())[:6]):
            ax = axes[idx]

            scores = [
                data['deception_score'],
                data['cooperation_score'],
                data['adversarial_score'],
                data['hallucination_resistance'],
                data['strategic_score']
            ]

            # Close the plot
            scores += scores[:1]

            angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
            angles += angles[:1]

            ax.plot(angles, scores, 'o-', linewidth=2, label=f"Player {player_id}")
            ax.fill(angles, scores, alpha=0.25)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(dimensions, size=9)
            ax.set_ylim(0, 1)
            ax.set_title(f"Player {player_id} ({data['role']})", fontweight='bold', pad=20)
            ax.grid(True)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'performance_radar.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_performance_heatmap(self):
        """Heatmap of detailed performance metrics across all players"""
        fig, ax = plt.subplots(figsize=(16, 10))
        fig.suptitle('Detailed Performance Heatmap\n详细性能热力图', fontsize=16, fontweight='bold')

        player_data = self.performance_report['player_performance']
        player_ids = list(player_data.keys())

        # Extract detailed metrics
        metric_names = [
            'Deception Success\n欺骗成功率',
            'Deception Detection\n欺骗检测率',
            'Role Consistency\n角色一致性',
            'Team Coordination\n团队协调',
            'Info Sharing\n信息分享',
            'Trust Reciprocity\n信任互惠',
            'Strategic Adaptation\n策略适应',
            'Opponent Modeling\n对手建模',
            'Info Exploitation\n信息利用',
            'Factual Consistency\n事实一致性',
            'Temporal Coherence\n时序连贯性',
            'Optimal Decisions\n最优决策',
            'Risk Assessment\n风险评估',
            'Long-term Planning\n长期规划'
        ]

        metric_keys = [
            'deception_success_rate', 'deception_detection_rate', 'role_claim_consistency',
            'team_coordination_score', 'information_sharing_rate', 'trust_reciprocity',
            'strategic_adaptation', 'opponent_modeling', 'information_asymmetry_exploitation',
            'factual_consistency', 'temporal_coherence',
            'optimal_decision_rate', 'risk_assessment_accuracy', 'long_term_planning'
        ]

        data_matrix = []
        for player_id in player_ids:
            player_metrics = player_data[player_id]['detailed_metrics']
            row = [player_metrics.get(key, 0.0) for key in metric_keys]
            data_matrix.append(row)

        # Create heatmap
        sns.heatmap(np.array(data_matrix).T, annot=True, fmt='.2f', cmap='RdYlGn',
                   xticklabels=[f"P{pid}\n{player_data[pid]['role'][:4]}" for pid in player_ids],
                   yticklabels=metric_names,
                   ax=ax, cbar_kws={'label': 'Score (0-1)'}, vmin=0, vmax=1)

        ax.set_xlabel('Players', fontweight='bold')
        ax.set_ylabel('Performance Metrics', fontweight='bold')

        plt.tight_layout()
        plt.savefig(self.output_dir / 'performance_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_adversarial_timeline(self):
        """Timeline showing adversarial interactions (kills, votes, conflicts)"""
        fig, axes = plt.subplots(3, 1, figsize=(16, 12))
        fig.suptitle('Adversarial Timeline\n对抗时间线', fontsize=16, fontweight='bold')

        event_log = self.game_report['event_log']

        # Extract key adversarial events
        night_kills = []
        day_eliminations = []
        sheriff_events = []

        for event in event_log:
            round_num = event.get('round', 0)

            if event['event_type'] == 'night_deaths':
                for player_id in event['data'].get('player_ids', []):
                    night_kills.append({
                        'round': round_num,
                        'player': player_id,
                        'timestamp': event.get('timestamp', '')
                    })

            elif event['event_type'] == 'day_elimination':
                day_eliminations.append({
                    'round': round_num,
                    'player': event['data'].get('player_id'),
                    'role': event['data'].get('role'),
                    'votes': event['data'].get('votes', 0),
                    'timestamp': event.get('timestamp', '')
                })

            elif event['event_type'] in ['sheriff_elected', 'sheriff_speech']:
                sheriff_events.append({
                    'round': round_num,
                    'type': event['event_type'],
                    'data': event['data'],
                    'timestamp': event.get('timestamp', '')
                })

        # Plot 1: Night kills timeline
        ax = axes[0]
        if night_kills:
            rounds = [k['round'] for k in night_kills]
            players = [k['player'] for k in night_kills]

            ax.scatter(rounds, players, s=200, c='darkred', alpha=0.6, marker='X')
            ax.set_ylabel('Player ID', fontweight='bold')
            ax.set_title('Night Kills (夜晚击杀)', fontweight='bold')
            ax.grid(True, alpha=0.3)

        # Plot 2: Day eliminations with vote counts
        ax = axes[1]
        if day_eliminations:
            rounds = [e['round'] for e in day_eliminations]
            players = [e['player'] for e in day_eliminations]
            votes = [e['votes'] for e in day_eliminations]
            roles = [e['role'] for e in day_eliminations]

            colors = ['red' if r == 'werewolf' else 'blue' for r in roles]
            scatter = ax.scatter(rounds, players, s=[v*50 for v in votes], c=colors, alpha=0.6)

            ax.set_ylabel('Player ID', fontweight='bold')
            ax.set_title('Day Eliminations (白天投票淘汰) - Size = Vote Count', fontweight='bold')
            ax.grid(True, alpha=0.3)

            # Legend
            from matplotlib.patches import Patch
            legend_elements = [
                Patch(facecolor='red', alpha=0.6, label='Werewolf'),
                Patch(facecolor='blue', alpha=0.6, label='Villager Team')
            ]
            ax.legend(handles=legend_elements, loc='upper right')

        # Plot 3: Sheriff timeline
        ax = axes[2]
        if sheriff_events:
            election_rounds = [e['round'] for e in sheriff_events if e['type'] == 'sheriff_elected']
            if election_rounds:
                sheriff_id = sheriff_events[0]['data'].get('sheriff_id')
                ax.axhline(y=sheriff_id, color='gold', linewidth=3, label=f'Sheriff: Player {sheriff_id}')
                ax.axvline(x=election_rounds[0], color='orange', linestyle='--', alpha=0.5, label='Election')

        ax.set_xlabel('Round Number', fontweight='bold')
        ax.set_ylabel('Player ID', fontweight='bold')
        ax.set_title('Sheriff Timeline (警长时间线)', fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        plt.savefig(self.output_dir / 'adversarial_timeline.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_deception_network(self):
        """Network visualization of deception and trust relationships"""
        fig, ax = plt.subplots(figsize=(14, 14))
        fig.suptitle('Deception & Trust Network\n欺骗与信任网络', fontsize=16, fontweight='bold')

        player_data = self.performance_report['player_performance']
        player_ids = list(player_data.keys())

        # Create circular layout
        n = len(player_ids)
        angles = np.linspace(0, 2*np.pi, n, endpoint=False)
        positions = {pid: (np.cos(angles[i]), np.sin(angles[i]))
                    for i, pid in enumerate(player_ids)}

        # Draw players as nodes
        for pid, (x, y) in positions.items():
            role = player_data[pid]['role']
            color = 'red' if role == 'werewolf' else 'blue'
            size = player_data[pid]['deception_score'] * 1000 + 300

            circle = plt.Circle((x, y), 0.08, color=color, alpha=0.6)
            ax.add_patch(circle)
            ax.text(x, y, f"P{pid}", ha='center', va='center', fontweight='bold', color='white')

            # Label with role
            label_x = x * 1.15
            label_y = y * 1.15
            ax.text(label_x, label_y, role[:4], ha='center', va='center', fontsize=8)

        # Draw edges based on vote patterns (from event log)
        vote_connections = self._extract_vote_connections()

        for (voter, target), weight in vote_connections.items():
            if voter in positions and target in positions:
                x1, y1 = positions[voter]
                x2, y2 = positions[target]

                # Line width based on vote frequency
                linewidth = min(5, weight * 2)
                alpha = min(0.8, weight * 0.3)

                ax.plot([x1, x2], [y1, y2], 'k-', linewidth=linewidth, alpha=alpha)

        ax.set_xlim(-1.3, 1.3)
        ax.set_ylim(-1.3, 1.3)
        ax.set_aspect('equal')
        ax.axis('off')

        # Legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='red', alpha=0.6, label='Werewolf (狼人)'),
            Patch(facecolor='blue', alpha=0.6, label='Villager Team (村民)'),
            plt.Line2D([0], [0], color='k', linewidth=2, label='Vote Connection (投票关联)')
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout()
        plt.savefig(self.output_dir / 'deception_network.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_strategy_evolution(self):
        """Evolution of strategy metrics across rounds"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Strategy Evolution Over Time\n策略演化', fontsize=16, fontweight='bold')

        event_log = self.game_report['event_log']
        rounds = list(range(1, self.game_report['game_summary']['total_rounds'] + 1))

        # Extract metrics by round
        vote_optimality_by_round = {r: [] for r in rounds}
        nash_scores_by_round = {r: 0.5 for r in rounds}
        werewolf_advantage_by_round = {r: 0.0 for r in rounds}

        # Simplified: use available data
        player_metrics = self.game_report['player_metrics']

        # Plot 1: Vote optimality trend
        ax = axes[0, 0]
        for player_id, data in player_metrics.items():
            optimal_ratio = data['metrics']['optimal_vote_ratio']
            # Simulate evolution (placeholder)
            evolution = [optimal_ratio * (0.7 + 0.3 * (i / len(rounds))) for i in range(len(rounds))]
            role = data['role']
            color = 'red' if role == 'werewolf' else 'blue'
            ax.plot(rounds, evolution, alpha=0.3, color=color)

        ax.set_xlabel('Round')
        ax.set_ylabel('Optimal Vote Ratio')
        ax.set_title('Vote Optimality Evolution (投票最优性演化)')
        ax.grid(True, alpha=0.3)

        # Plot 2: Deception attempts over time
        ax = axes[0, 1]
        deception_by_round = {r: 0 for r in rounds}

        for event in event_log:
            if event['event_type'] == 'player_statement':
                round_num = event.get('round', 1)
                # Simple detection: if statement contains role claims
                statement = event['data'].get('statement', '').lower()
                if 'i am' in statement or "i'm" in statement:
                    deception_by_round[round_num] = deception_by_round.get(round_num, 0) + 1

        if deception_by_round:
            ax.bar(list(deception_by_round.keys()), list(deception_by_round.values()),
                  color='orange', alpha=0.7)
            ax.set_xlabel('Round')
            ax.set_ylabel('Deception Attempts')
            ax.set_title('Deception Attempts by Round (每回合欺骗尝试)')
            ax.grid(True, alpha=0.3)

        # Plot 3: Player count evolution
        ax = axes[1, 0]
        total_players = len(player_metrics)
        alive_by_round = [total_players]

        current_alive = total_players
        for event in event_log:
            if event['event_type'] in ['night_deaths', 'day_elimination']:
                if event['event_type'] == 'night_deaths':
                    current_alive -= len(event['data'].get('player_ids', []))
                else:
                    current_alive -= 1
                alive_by_round.append(current_alive)

        ax.plot(range(len(alive_by_round)), alive_by_round, marker='o', linewidth=2, markersize=8, color='green')
        ax.fill_between(range(len(alive_by_round)), alive_by_round, alpha=0.3, color='green')
        ax.set_xlabel('Game Progress')
        ax.set_ylabel('Players Alive')
        ax.set_title('Player Survival Trend (玩家存活趋势)')
        ax.grid(True, alpha=0.3)

        # Plot 4: Werewolf vs Villager count
        ax = axes[1, 1]

        werewolf_count = []
        villager_count = []

        # Initial counts
        werewolves = sum(1 for p in player_metrics.values() if p['role'] == 'werewolf')
        villagers = total_players - werewolves

        werewolf_count.append(werewolves)
        villager_count.append(villagers)

        for event in event_log:
            if event['event_type'] == 'day_elimination':
                role = event['data'].get('role')
                if role == 'werewolf':
                    werewolves -= 1
                else:
                    villagers -= 1

                werewolf_count.append(werewolves)
                villager_count.append(villagers)

        x = range(len(werewolf_count))
        ax.plot(x, werewolf_count, marker='o', label='Werewolves', color='red', linewidth=2)
        ax.plot(x, villager_count, marker='s', label='Villagers', color='blue', linewidth=2)
        ax.fill_between(x, werewolf_count, alpha=0.2, color='red')
        ax.fill_between(x, villager_count, alpha=0.2, color='blue')
        ax.set_xlabel('Elimination Events')
        ax.set_ylabel('Count')
        ax.set_title('Team Balance Evolution (阵营平衡演化)')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(self.output_dir / 'strategy_evolution.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_hallucination_analysis(self):
        """Detailed hallucination and consistency analysis"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Hallucination & Consistency Analysis\n幻觉与一致性分析', fontsize=16, fontweight='bold')

        player_data = self.performance_report['player_performance']
        player_ids = list(player_data.keys())

        # Plot 1: Factual consistency by player
        ax = axes[0, 0]
        consistency_scores = [player_data[pid]['detailed_metrics']['factual_consistency'] for pid in player_ids]
        roles = [player_data[pid]['role'] for pid in player_ids]
        colors = ['red' if r == 'werewolf' else 'blue' for r in roles]

        bars = ax.bar(range(len(player_ids)), consistency_scores, color=colors, alpha=0.7)
        ax.set_xticks(range(len(player_ids)))
        ax.set_xticklabels([f"P{pid}" for pid in player_ids], rotation=45)
        ax.set_ylabel('Factual Consistency Score')
        ax.set_title('Factual Consistency by Player (事实一致性)')
        ax.axhline(y=0.8, color='green', linestyle='--', label='Good Threshold', alpha=0.5)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Plot 2: Self-contradiction rates
        ax = axes[0, 1]
        contradiction_rates = [player_data[pid]['detailed_metrics']['self_contradiction_rate'] for pid in player_ids]

        bars = ax.bar(range(len(player_ids)), contradiction_rates, color=colors, alpha=0.7)
        ax.set_xticks(range(len(player_ids)))
        ax.set_xticklabels([f"P{pid}" for pid in player_ids], rotation=45)
        ax.set_ylabel('Self-Contradiction Rate')
        ax.set_title('Self-Contradiction Rate (自我矛盾率)')
        ax.axhline(y=0.2, color='red', linestyle='--', label='Warning Threshold', alpha=0.5)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Plot 3: Temporal coherence
        ax = axes[1, 0]
        coherence_scores = [player_data[pid]['detailed_metrics']['temporal_coherence'] for pid in player_ids]

        bars = ax.bar(range(len(player_ids)), coherence_scores, color=colors, alpha=0.7)
        ax.set_xticks(range(len(player_ids)))
        ax.set_xticklabels([f"P{pid}" for pid in player_ids], rotation=45)
        ax.set_ylabel('Temporal Coherence Score')
        ax.set_title('Temporal Coherence (时序连贯性)')
        ax.grid(True, alpha=0.3)

        # Plot 4: Overall hallucination resistance
        ax = axes[1, 1]
        resistance_scores = [player_data[pid]['hallucination_resistance'] for pid in player_ids]

        bars = ax.bar(range(len(player_ids)), resistance_scores, color=colors, alpha=0.7)
        ax.set_xticks(range(len(player_ids)))
        ax.set_xticklabels([f"P{pid}" for pid in player_ids], rotation=45)
        ax.set_ylabel('Hallucination Resistance')
        ax.set_title('Overall Hallucination Resistance (整体抗幻觉能力)')
        ax.grid(True, alpha=0.3)

        # Add role legend
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='red', alpha=0.7, label='Werewolf'),
            Patch(facecolor='blue', alpha=0.7, label='Villager Team')
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout()
        plt.savefig(self.output_dir / 'hallucination_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()

    def _extract_vote_connections(self) -> Dict[Tuple[str, str], int]:
        """Extract voting connections between players"""
        connections = {}

        for event in self.game_report['event_log']:
            if event['event_type'] == 'day_elimination':
                # Simplified: count elimination events as connections
                # In full implementation, would track individual votes
                eliminated = str(event['data'].get('player_id'))

                # Assume all alive players voted
                for player_id in self.game_report['player_metrics'].keys():
                    key = (player_id, eliminated)
                    connections[key] = connections.get(key, 0) + 1

        return connections

    def generate_summary_report(self, output_file: str = 'enhanced_summary.txt'):
        """Generate enhanced text summary with adversarial details"""
        report_path = self.output_dir / output_file

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*80 + "\n")
            f.write("ENHANCED WEREWOLF GAME ANALYSIS REPORT\n")
            f.write("增强版狼人杀游戏分析报告\n")
            f.write("="*80 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            # Performance summary
            f.write("PERFORMANCE METRICS SUMMARY\n")
            f.write("性能指标摘要\n")
            f.write("-" * 80 + "\n")

            stats = self.performance_report['aggregate_statistics']
            f.write(f"Average Deception Score (平均欺骗得分):           {stats['avg_deception_score']:.3f}\n")
            f.write(f"Average Cooperation Score (平均合作得分):         {stats['avg_cooperation_score']:.3f}\n")
            f.write(f"Average Adversarial Score (平均对抗得分):         {stats['avg_adversarial_score']:.3f}\n")
            f.write(f"Average Hallucination Resistance (平均抗幻觉):   {stats['avg_hallucination_resistance']:.3f}\n")
            f.write(f"Average Strategic Score (平均策略得分):           {stats['avg_strategic_score']:.3f}\n\n")

            # Adversarial details
            f.write("ADVERSARIAL INTERACTION DETAILS\n")
            f.write("对抗互动细节\n")
            f.write("-" * 80 + "\n")

            night_deaths = [e for e in self.game_report['event_log'] if e['event_type'] == 'night_deaths']
            day_elims = [e for e in self.game_report['event_log'] if e['event_type'] == 'day_elimination']

            f.write(f"\nTotal Night Kills (夜晚击杀): {sum(len(e['data'].get('player_ids', [])) for e in night_deaths)}\n")
            f.write(f"Total Day Eliminations (白天淘汰): {len(day_elims)}\n")

            werewolf_elims = sum(1 for e in day_elims if e['data'].get('role') == 'werewolf')
            f.write(f"Werewolves Eliminated (狼人被淘汰): {werewolf_elims}\n")
            f.write(f"Villagers Eliminated (村民被淘汰): {len(day_elims) - werewolf_elims}\n\n")

            # Player rankings
            f.write("PLAYER PERFORMANCE RANKINGS\n")
            f.write("玩家表现排名\n")
            f.write("-" * 80 + "\n")

            player_data = self.performance_report['player_performance']

            # Overall score
            f.write("\nOverall Score (综合得分):\n")
            overall_scores = {
                pid: (data['deception_score'] + data['cooperation_score'] +
                     data['adversarial_score'] + data['hallucination_resistance'] +
                     data['strategic_score']) / 5
                for pid, data in player_data.items()
            }

            for rank, (pid, score) in enumerate(sorted(overall_scores.items(),
                                                       key=lambda x: x[1], reverse=True), 1):
                role = player_data[pid]['role']
                f.write(f"  {rank}. Player {pid} ({role}): {score:.3f}\n")

            f.write("\n" + "="*80 + "\n")

        print(f"📄 Enhanced summary saved to {report_path}")


def main():
    """Example usage"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python enhanced_visualizer.py <game_report.json> [performance_report.json]")
        sys.exit(1)

    game_report = sys.argv[1]
    perf_report = sys.argv[2] if len(sys.argv) > 2 else None

    visualizer = EnhancedVisualizer(game_report, perf_report)
    visualizer.create_all_visualizations()
    visualizer.generate_summary_report()

    print("\n✅ Enhanced analysis complete!")


if __name__ == '__main__':
    main()
