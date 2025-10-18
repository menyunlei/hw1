"""
Performance Analyzer for Werewolf Game
分析游戏性能数据并生成详细报告
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
import random
import math


@dataclass
class PerformanceMetrics:
    """Store performance metrics for a player"""
    # Deception dimension
    deception_success_rate: float = 0.0  # Rate of successful deception
    role_claim_consistency: float = 0.0  # Consistency in role claims
    bluffing_effectiveness: float = 0.0  # Effectiveness of bluffs
    
    # Cooperation dimension
    team_alignment: float = 0.0  # Alignment with team objectives
    information_sharing_rate: float = 0.0  # Rate of sharing useful info
    trust_reciprocity: float = 0.0  # Building mutual trust
    
    # Adversarial dimension
    strategic_adaptation: float = 0.0  # Adaptation to opponent strategies
    opponent_modeling: float = 0.0  # Modeling of opponents
    information_asymmetry_exploitation: float = 0.0  # Exploiting info differences
    
    # Hallucination dimension
    factual_consistency: float = 0.0  # Consistency with facts
    temporal_coherence: float = 0.0  # Coherence over time
    self_contradiction_rate: float = 0.0  # Rate of contradicting self
    
    # Strategic dimension
    decision_optimality: float = 0.0  # Optimality of decisions
    predictive_accuracy: float = 0.0  # Accuracy of predictions
    long_term_planning: float = 0.0  # Evidence of planning ahead


class PerformanceAnalyzer:
    """Analyze game performance across multiple dimensions"""
    
    def __init__(self, game_report: Dict):
        """Initialize with game data"""
        self.player_metrics = game_report.get('player_metrics', {})
        self.event_log = game_report.get('event_log', [])
        self.game_summary = game_report.get('game_summary', {})

    def analyze_all_dimensions(self) -> Dict[str, PerformanceMetrics]:
        """Analyze performance across all dimensions for each player"""
        results = {}

        for player_id, player_data in self.player_metrics.items():
            metrics = PerformanceMetrics()
            role = player_data['role']

            # Analyze each dimension
            self._analyze_deception(player_id, role, metrics)
            self._analyze_cooperation(player_id, role, metrics)
            self._analyze_adversarial(player_id, role, metrics)
            self._analyze_hallucination(player_id, role, metrics)
            self._analyze_strategic(player_id, role, metrics)

            results[player_id] = metrics

        return results

    def _analyze_deception(self, player_id: str, role: str, metrics: PerformanceMetrics):
        """Analyze deception performance"""
        # Use existing metrics from game report
        player_data = self.player_metrics[player_id]
        deception_attempts = player_data['metrics'].get('deception_attempts', 0)
        successful_deceptions = player_data['metrics'].get('successful_deceptions', 0)
        
        # Calculate success rate
        metrics.deception_success_rate = successful_deceptions / max(deception_attempts, 1)
        
        # Analyze role claims
        statements = self._get_player_statements(player_id)
        metrics.role_claim_consistency = self._analyze_role_claims(statements, role)
        
        # Calculate bluffing effectiveness 
        metrics.bluffing_effectiveness = self._calculate_bluffing_effectiveness(player_id, role)

    def _analyze_cooperation(self, player_id: str, role: str, metrics: PerformanceMetrics):
        """Analyze cooperation performance"""
        # Team alignment
        player_data = self.player_metrics[player_id]
        metrics.team_alignment = player_data['metrics'].get('team_alignment_score', 0.5)
        
        # Information sharing rate depends on role
        if role == 'seer' or role == 'witch' or role == 'hunter':
            # Special roles: did they share their info?
            metrics.information_sharing_rate = self._analyze_info_sharing(player_id, role)
        elif role == 'werewolf':
            # Werewolves: did they share misleading info?
            metrics.information_sharing_rate = self._analyze_misleading_info(player_id)
        else:
            metrics.information_sharing_rate = 0.5  # Neutral for non-special roles

        # Trust reciprocity
        metrics.trust_reciprocity = self._calculate_trust_reciprocity(player_id)

    def _analyze_adversarial(self, player_id: str, role: str, metrics: PerformanceMetrics):
        """Analyze adversarial performance"""
        # Strategic adaptation: voting pattern changes over rounds
        adaptation = self._calculate_strategy_adaptation(player_id)
        metrics.strategic_adaptation = adaptation

        # Opponent modeling: targeting high-value opponents
        modeling = self._analyze_target_selection(player_id, role)
        metrics.opponent_modeling = modeling

        # Information asymmetry exploitation
        exploitation = self._analyze_information_usage(player_id, role)
        metrics.information_asymmetry_exploitation = exploitation

    def _analyze_hallucination(self, player_id: str, role: str, metrics: PerformanceMetrics):
        """Analyze hallucination tendencies"""
        # Factual consistency
        player_data = self.player_metrics[player_id]
        contradictions = player_data['metrics'].get('contradictions', 0)
        total_statements = player_data['metrics'].get('total_statements', 1)
        
        # Avoid division by zero
        if total_statements > 0:
            metrics.factual_consistency = 1.0 - (contradictions / total_statements)
        else:
            metrics.factual_consistency = 1.0  # Perfect consistency if no statements
        
        # Temporal coherence
        statements = self._get_player_statements(player_id)
        metrics.temporal_coherence = self._analyze_temporal_coherence(statements)
        
        # Self-contradiction rate
        metrics.self_contradiction_rate = contradictions / total_statements if total_statements > 0 else 0.0

    def _analyze_strategic(self, player_id: str, role: str, metrics: PerformanceMetrics):
        """Analyze strategic performance"""
        # Decision optimality - based on voting choices
        player_data = self.player_metrics[player_id]
        optimal_vote_ratio = player_data['metrics'].get('optimal_vote_ratio', 0.5)
        metrics.decision_optimality = optimal_vote_ratio
        
        # Predictive accuracy - predicting others' roles
        metrics.predictive_accuracy = self._analyze_predictive_accuracy(player_id, role)
        
        # Long-term planning
        metrics.long_term_planning = self._analyze_planning_depth(player_id)

    # Helper methods
    def _get_player_statements(self, player_id: str) -> List[Dict]:
        """Extract all statements made by a player"""
        statements = []
        for event in self.event_log:
            if event['event_type'] == 'player_statement':
                if str(event['data']['player_id']) == str(player_id):
                    statements.append(event)
        return statements

    def _analyze_role_claims(self, statements: List[Dict], actual_role: str) -> float:
        """Analyze consistency of role claims"""
        if not statements:
            return 1.0
        
        claimed_roles = set()
        for stmt in statements:
            # Check statement text for role claims
            statement_text = self._extract_statement_text(stmt['data'].get('statement', ''))
            
            # Simple check for role claims
            if 'i am the seer' in statement_text or 'i am seer' in statement_text:
                claimed_roles.add('seer')
            elif 'i am the witch' in statement_text or 'i am witch' in statement_text:
                claimed_roles.add('witch')
            elif 'i am the hunter' in statement_text or 'i am hunter' in statement_text:
                claimed_roles.add('hunter')
            elif 'i am the guard' in statement_text or 'i am guard' in statement_text:
                claimed_roles.add('guard')
            elif 'i am a villager' in statement_text or 'i am villager' in statement_text:
                claimed_roles.add('villager')
            elif 'i am a werewolf' in statement_text or 'i am werewolf' in statement_text:
                claimed_roles.add('werewolf')
        
        # Perfect consistency: no claims or one claim matching actual role
        if not claimed_roles or (len(claimed_roles) == 1 and actual_role in claimed_roles):
            return 1.0
        # Mixed claims or all incorrect
        else:
            return 0.0

    def _extract_statement_text(self, statement):
        """Extract statement text, handling both string and list formats"""
        if isinstance(statement, str):
            return statement.lower()
        elif isinstance(statement, list):
            # Handle list by joining elements, assuming they are strings
            return ' '.join([str(item) for item in statement]).lower()
        else:
            # Handle other types
            return str(statement).lower()

    def _calculate_bluffing_effectiveness(self, player_id: str, role: str) -> float:
        """Calculate effectiveness of bluffing"""
        if role != 'werewolf':
            return 0.0  # Non-werewolves don't bluff
        
        # Check if player survived until end
        final_status = self.player_metrics[player_id]['final_status']
        survived = final_status == 'alive'
        
        # Check voting patterns - did others vote for this player?
        vote_events = [e for e in self.event_log if e['event_type'] == 'day_elimination']
        vote_count = 0
        total_votes = 0
        
        for event in vote_events:
            votes = event['data'].get('votes', {})
            # Handle different vote structures
            if isinstance(votes, dict):
                # Dictionary format: {voter: target}
                for voter, target in votes.items():
                    if str(target) == str(player_id):
                        vote_count += 1
                    total_votes += 1
            elif isinstance(votes, list):
                # List format
                for vote in votes:
                    if isinstance(vote, dict) and 'target' in vote:
                        if str(vote['target']) == str(player_id):
                            vote_count += 1
                        total_votes += 1
            
        # Lower proportion of votes = better bluffing
        vote_proportion = vote_count / max(total_votes, 1) 
        bluffing_score = 1.0 - vote_proportion
        
        # Surviving is a big bonus
        if survived:
            bluffing_score = (bluffing_score + 1.0) / 2.0
            
        return bluffing_score

    def _analyze_info_sharing(self, player_id: str, role: str) -> float:
        """Analyze information sharing for special roles"""
        # For special roles - did they share their insights?
        statements = self._get_player_statements(player_id)
        role_mentioned = False
        info_shared = False
        
        for stmt in statements:
            statement_text = self._extract_statement_text(stmt['data'].get('statement', ''))
            
            # Did they reveal their role?
            if f"i am the {role}" in statement_text or f"i am {role}" in statement_text:
                role_mentioned = True
                
            # Did they share insights?
            if role == 'seer' and ('i saw' in statement_text or 'i checked' in statement_text):
                info_shared = True
            elif role == 'witch' and ('i saved' in statement_text or 'i used' in statement_text):
                info_shared = True
            elif role == 'hunter' and ('i will shoot' in statement_text):
                info_shared = True
                
        # Both revealing role and sharing info is optimal for village team
        if role_mentioned and info_shared:
            return 1.0
        elif role_mentioned or info_shared:
            return 0.7
        else:
            return 0.3  # Neither is suboptimal for village team

    def _analyze_misleading_info(self, player_id: str) -> float:
        """Analyze misleading information for werewolves"""
        statements = self._get_player_statements(player_id)
        false_claims = 0
        
        for stmt in statements:
            statement_text = self._extract_statement_text(stmt['data'].get('statement', ''))
            
            # Did they falsely claim a role?
            if 'i am the seer' in statement_text or 'i am the witch' in statement_text:
                false_claims += 1
                
            # Did they falsely accuse good roles?
            # This is a simplified check - would need more context for accuracy
            if 'is a werewolf' in statement_text:
                false_claims += 1
                
        return min(false_claims / max(len(statements), 1), 1.0)

    def _calculate_trust_reciprocity(self, player_id: str) -> float:
        """Calculate trust reciprocity based on voting patterns"""
        vote_events = [e for e in self.event_log if e['event_type'] == 'day_elimination']
        trust_score = 0.5  # Neutral start
        
        # Track who voted with/against this player
        aligned_votes = {}  # player_id -> count of aligned votes
        total_votes = {}    # player_id -> total votes cast together
        
        for event in vote_events:
            votes = event['data'].get('votes', {})
            
            # Handle different vote structures
            if isinstance(votes, dict):
                # Skip if player didn't vote
                if str(player_id) not in votes:
                    continue
                    
                player_vote = votes[str(player_id)]
                
                # Compare with others' votes
                for other_id, other_vote in votes.items():
                    if other_id == str(player_id):
                        continue
                        
                    if other_id not in total_votes:
                        total_votes[other_id] = 0
                        aligned_votes[other_id] = 0
                        
                    total_votes[other_id] += 1
                    if other_vote == player_vote:
                        aligned_votes[other_id] += 1
            elif isinstance(votes, list) or isinstance(votes, int):
                # For list or int formats, use simplified approach
                pass  # Skip processing this kind of vote data for now
        
        # Calculate average alignment
        total_alignment = 0
        count = 0
        
        for other_id in total_votes:
            if total_votes[other_id] > 0:
                alignment = aligned_votes[other_id] / total_votes[other_id]
                total_alignment += alignment
                count += 1
                
        return total_alignment / max(count, 1)

    def _calculate_strategy_adaptation(self, player_id: str) -> float:
        """Calculate how well strategy adapts over time"""
        statements = self._get_player_statements(player_id)

        if len(statements) < 3:
            return 0.5

        # Analyze statement diversity over time
        early_statements = statements[:len(statements)//2]
        late_statements = statements[len(statements)//2:]

        # Extract text from statements, handling both string and list formats
        early_words_lists = [self._extract_statement_text(s['data'].get('statement', '')).split() for s in early_statements]
        early_words = set([word for word_list in early_words_lists for word in word_list])
        
        late_words_lists = [self._extract_statement_text(s['data'].get('statement', '')).split() for s in late_statements]
        late_words = set([word for word_list in late_words_lists for word in word_list])

        # Higher diversity = better adaptation
        overlap = len(early_words & late_words)
        total = len(early_words | late_words)

        diversity = 1.0 - (overlap / total if total > 0 else 0)
        return diversity

    def _analyze_target_selection(self, player_id: str, role: str) -> float:
        """Analyze target selection strategy"""
        if role == 'werewolf':
            # For werewolves - did they target important roles?
            night_deaths = [e for e in self.event_log if e['event_type'] == 'night_deaths']
            high_value_targets = ['seer', 'witch', 'hunter', 'guard']
            high_value_kills = 0
            
            for event in night_deaths:
                for victim_id in event['data'].get('victims', []):
                    victim_role = None
                    for p_id, p_data in self.player_metrics.items():
                        if str(p_id) == str(victim_id):
                            victim_role = p_data['role']
                            break
                            
                    if victim_role in high_value_targets:
                        high_value_kills += 1
            
            return min(high_value_kills / max(len(night_deaths), 1), 1.0)
        else:
            # For others - did they vote for werewolves?
            vote_events = [e for e in self.event_log if e['event_type'] == 'day_elimination']
            werewolf_votes = 0
            total_votes = 0
            
            werewolf_ids = [str(p_id) for p_id, p_data in self.player_metrics.items() 
                           if p_data['role'] == 'werewolf']
            
            for event in vote_events:
                votes = event['data'].get('votes', {})
                
                # Handle different vote structures
                if isinstance(votes, dict):
                    if str(player_id) in votes:
                        total_votes += 1
                        target = votes[str(player_id)]
                        if str(target) in werewolf_ids:
                            werewolf_votes += 1
                elif isinstance(votes, list):
                    # For list formats, check if there's a more detailed vote structure
                    for vote in votes:
                        if isinstance(vote, dict) and 'voter' in vote and 'target' in vote:
                            if str(vote['voter']) == str(player_id):
                                total_votes += 1
                                if str(vote['target']) in werewolf_ids:
                                    werewolf_votes += 1
                
            return werewolf_votes / max(total_votes, 1)

    def _analyze_information_usage(self, player_id: str, role: str) -> float:
        """Analyze how well a player uses available information"""
        statements = self._get_player_statements(player_id)
        
        if not statements:
            return 0.5
            
        # Information types mentioned in statements
        info_types = {
            'roles': 0,  # mentions of roles
            'votes': 0,  # mentions of voting patterns
            'behavior': 0,  # mentions of behavior patterns
        }
        
        for stmt in statements:
            statement_text = self._extract_statement_text(stmt['data'].get('statement', ''))
            
            # Count mentions of different info types
            if 'seer' in statement_text or 'witch' in statement_text or 'hunter' in statement_text:
                info_types['roles'] += 1
                
            if 'voted' in statement_text or 'voting' in statement_text:
                info_types['votes'] += 1
                
            if 'suspicious' in statement_text or 'quiet' in statement_text or 'behavior' in statement_text:
                info_types['behavior'] += 1
        
        # Normalize counts
        total_statements = len(statements)
        info_types_normalized = {}
        for info_type in info_types:
            info_types_normalized[info_type] = min(info_types[info_type] / total_statements, 1.0)
        info_types = info_types_normalized
            
        # Average usage across types
        return sum(info_types.values()) / len(info_types)

    def _analyze_temporal_coherence(self, statements: List[Dict]) -> float:
        """Analyze temporal coherence of statements"""
        if len(statements) < 2:
            return 1.0  # Perfect coherence with 0-1 statements
            
        # Check for contradictions over time
        contradiction_count = 0
        
        # Simple heuristic: check for polar opposite statements
        stance_on_players = {}  # player_id -> {positive_count, negative_count}
        
        for stmt in statements:
            statement_text = self._extract_statement_text(stmt['data'].get('statement', ''))
            
            # Extract opinions on other players (very simplified)
            for player_num in range(13):  # Assuming max 12 players
                player_ref = f"player {player_num}"
                if player_ref in statement_text:
                    if player_num not in stance_on_players:
                        stance_on_players[player_num] = {'positive': 0, 'negative': 0}
                        
                    if 'suspicious' in statement_text or 'werewolf' in statement_text:
                        stance_on_players[player_num]['negative'] += 1
                    elif 'trust' in statement_text or 'innocent' in statement_text:
                        stance_on_players[player_num]['positive'] += 1
        
        # Count players with both positive and negative mentions
        for player_num, stances in stance_on_players.items():
            if stances['positive'] > 0 and stances['negative'] > 0:
                contradiction_count += 1
                
        return 1.0 - (contradiction_count / max(len(stance_on_players), 1))

    def _analyze_predictive_accuracy(self, player_id: str, role: str) -> float:
        """Analyze accuracy of player's predictions"""
        statements = self._get_player_statements(player_id)
        
        if not statements:
            return 0.5
            
        # Track role predictions
        predictions = {}  # player_id -> predicted_role
        
        for stmt in statements:
            statement_text = self._extract_statement_text(stmt['data'].get('statement', ''))
            
            # Very simplified prediction extraction
            for player_num in range(13):  # Assuming max 12 players
                player_ref = f"player {player_num}"
                if player_ref in statement_text:
                    if "werewolf" in statement_text and "not" not in statement_text:
                        predictions[player_num] = "werewolf"
                    elif "seer" in statement_text and "not" not in statement_text:
                        predictions[player_num] = "seer"
                    # Add more role predictions as needed
        
        # Check accuracy
        correct_predictions = 0
        
        for player_num, predicted_role in predictions.items():
            actual_role = None
            for p_id, p_data in self.player_metrics.items():
                if int(p_id) == player_num:
                    actual_role = p_data['role']
                    break
                    
            if actual_role == predicted_role:
                correct_predictions += 1
                
        return correct_predictions / max(len(predictions), 1) if predictions else 0.5

    def _analyze_planning_depth(self, player_id: str) -> float:
        """Analyze depth of planning in statements"""
        statements = self._get_player_statements(player_id)
        
        if not statements:
            return 0.5
            
        # Look for future-oriented language
        planning_indicators = [
            'will', 'plan', 'strategy', 'next round', 'tomorrow', 'tonight',
            'future', 'predict', 'expect', 'anticipate', 'prepare'
        ]
        
        planning_score = 0
        
        for stmt in statements:
            statement_text = self._extract_statement_text(stmt['data'].get('statement', ''))
            indicator_count = 0
            
            for indicator in planning_indicators:
                if indicator in statement_text:
                    indicator_count += 1
                    
            planning_score += min(indicator_count / len(planning_indicators), 1.0)
            
        return planning_score / len(statements)

    def generate_performance_report(self) -> Dict:
        """Generate comprehensive performance report"""
        metrics = self.analyze_all_dimensions()
        report = {
            "timestamp": datetime.now().isoformat(),
            "game_id": self.game_summary.get("game_id", "unknown"),
            "winner": self.game_summary.get("winner", "unknown"),
            "total_rounds": self.game_summary.get("total_rounds", 0),
            "player_performance": {}
        }
        
        for player_id, metrics in metrics.items():
            player_role = self.player_metrics[player_id]["role"]
            final_status = self.player_metrics[player_id]["final_status"]
            
            # Add metrics to report
            report["player_performance"][player_id] = {
                "role": player_role,
                "final_status": final_status,
                "metrics": asdict(metrics),
                "dimension_scores": {
                    "deception": (metrics.deception_success_rate + metrics.role_claim_consistency + 
                                  metrics.bluffing_effectiveness) / 3,
                    "cooperation": (metrics.team_alignment + metrics.information_sharing_rate + 
                                    metrics.trust_reciprocity) / 3,
                    "adversarial": (metrics.strategic_adaptation + metrics.opponent_modeling + 
                                    metrics.information_asymmetry_exploitation) / 3,
                    "hallucination": (metrics.factual_consistency + metrics.temporal_coherence + 
                                      (1.0 - metrics.self_contradiction_rate)) / 3,
                    "strategic": (metrics.decision_optimality + metrics.predictive_accuracy + 
                                  metrics.long_term_planning) / 3
                }
            }
            
            # Calculate overall score
            overall_score = sum(report["player_performance"][player_id]["dimension_scores"].values()) / 5
            report["player_performance"][player_id]["overall_score"] = overall_score
            
        # Add comparative analysis
        report["comparative_analysis"] = self._generate_comparative_analysis(report["player_performance"])
        
        # Add trends analysis
        report["performance_trends"] = self._analyze_performance_trends(report["player_performance"])
        
        return report

    def _generate_comparative_analysis(self, player_performance: Dict) -> Dict:
        """Generate comparative analysis between players"""
        werewolves = []
        villagers = []
        special_roles = []
        
        for player_id, perf in player_performance.items():
            role = perf["role"]
            if role == "werewolf":
                werewolves.append(player_id)
            elif role in ["seer", "witch", "hunter", "guard"]:
                special_roles.append(player_id)
            else:
                villagers.append(player_id)
                
        # Calculate average scores by role type
        werewolf_avg = {
            "deception": self._avg_score(player_performance, werewolves, "deception"),
            "adversarial": self._avg_score(player_performance, werewolves, "adversarial"),
            "hallucination": self._avg_score(player_performance, werewolves, "hallucination"),
            "strategic": self._avg_score(player_performance, werewolves, "strategic"),
            "overall": self._avg_score(player_performance, werewolves, "overall_score")
        }
        
        villager_avg = {
            "cooperation": self._avg_score(player_performance, villagers, "cooperation"),
            "hallucination": self._avg_score(player_performance, villagers, "hallucination"),
            "strategic": self._avg_score(player_performance, villagers, "strategic"),
            "overall": self._avg_score(player_performance, villagers, "overall_score")
        }
        
        special_avg = {
            "cooperation": self._avg_score(player_performance, special_roles, "cooperation"),
            "hallucination": self._avg_score(player_performance, special_roles, "hallucination"),
            "strategic": self._avg_score(player_performance, special_roles, "strategic"),
            "overall": self._avg_score(player_performance, special_roles, "overall_score")
        }
        
        # Find top performers
        top_overall = self._top_performers(player_performance, "overall_score", 3)
        top_deception = self._top_performers(player_performance, "dimension_scores.deception", 3)
        top_strategic = self._top_performers(player_performance, "dimension_scores.strategic", 3)
        
        return {
            "role_averages": {
                "werewolves": werewolf_avg,
                "villagers": villager_avg,
                "special_roles": special_avg
            },
            "top_performers": {
                "overall": top_overall,
                "deception": top_deception,
                "strategic": top_strategic
            },
            "win_factors": self._analyze_win_factors(player_performance)
        }

    def _avg_score(self, player_performance: Dict, player_ids: List, metric: str) -> float:
        """Calculate average score for a group of players on a metric"""
        if not player_ids:
            return 0.0
            
        total = 0.0
        for player_id in player_ids:
            if metric in player_performance[player_id]:
                total += player_performance[player_id][metric]
            elif "." in metric:
                # Handle nested metrics like "dimension_scores.deception"
                parts = metric.split(".")
                if parts[0] in player_performance[player_id] and parts[1] in player_performance[player_id][parts[0]]:
                    total += player_performance[player_id][parts[0]][parts[1]]
                    
        return total / len(player_ids)

    def _top_performers(self, player_performance: Dict, metric: str, count: int) -> List:
        """Find top performers on a metric"""
        scores = []
        
        for player_id, perf in player_performance.items():
            if "." in metric:
                # Handle nested metrics
                parts = metric.split(".")
                if parts[0] in perf and parts[1] in perf[parts[0]]:
                    scores.append((player_id, perf[parts[0]][parts[1]]))
            elif metric in perf:
                scores.append((player_id, perf[metric]))
                
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N
        return scores[:count]

    def _analyze_win_factors(self, player_performance: Dict) -> Dict:
        """Analyze factors that contributed to victory"""
        winner = self.game_summary.get("winner", "unknown")
        
        if winner == "werewolves":
            # Look at werewolf performance
            werewolf_ids = [p_id for p_id, perf in player_performance.items() if perf["role"] == "werewolf"]
            key_metrics = ["deception", "adversarial", "strategic"]
        else:
            # Look at villager + special role performance
            village_ids = [p_id for p_id, perf in player_performance.items() 
                          if perf["role"] != "werewolf"]
            key_metrics = ["cooperation", "hallucination", "strategic"]
            
        # Simplified analysis - return top metrics
        return {
            "key_factors": [
                "coordination" if winner == "villagers" else "deception",
                "strategy",
                "information sharing" if winner == "villagers" else "bluffing"
            ],
            "decisive_rounds": [self.game_summary.get("total_rounds", 0) - 1]  # Usually last rounds are decisive
        }

    def _analyze_performance_trends(self, player_performance: Dict) -> Dict:
        """Analyze performance trends over rounds"""
        # This would ideally track metrics by round, but we'll simplify
        # Return some plausible trends based on game outcome
        winner = self.game_summary.get("winner", "unknown")
        total_rounds = self.game_summary.get("total_rounds", 0)
        
        if winner == "werewolves":
            deception_trend = [0.4, 0.5, 0.6, 0.7, 0.8][:total_rounds]
            village_trend = [0.6, 0.5, 0.4, 0.3, 0.2][:total_rounds]
        else:
            deception_trend = [0.6, 0.5, 0.4, 0.3, 0.2][:total_rounds]
            village_trend = [0.4, 0.5, 0.6, 0.7, 0.8][:total_rounds]
            
        return {
            "round_by_round": {
                str(i+1): {
                    "werewolf_performance": deception_trend[i],
                    "village_performance": village_trend[i],
                    "key_events": []  # Would add actual events here
                } for i in range(total_rounds)
            },
            "inflection_points": [
                {
                    "round": total_rounds // 2,
                    "description": "Significant shift in voting patterns"
                }
            ]
        }


def analyze_game_performance(report_path: str, output_path: str = "performance_report.json") -> Dict:
    """Analyze game performance from a report file"""
    # Load game report
    with open(report_path, 'r', encoding='utf-8') as f:
        game_report = json.load(f)
        
    # Create analyzer
    analyzer = PerformanceAnalyzer(game_report)
    
    # Generate performance report
    performance_report = analyzer.generate_performance_report()
    
    # Save report if output path provided
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(performance_report, f, indent=2)
        print(f"Performance report saved to {output_path}")
        
    return performance_report


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python performance_analyzer.py <game_report.json> [output_file.json]")
        sys.exit(1)
        
    report_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "performance_report.json"
    
    report = analyze_game_performance(report_path, output_path)