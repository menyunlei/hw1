"""
Deep Reasoning Evaluators for Werewolf Game
============================================

This module implements advanced evaluators to measure deep reasoning abilities
in combinatorially explosive environments, specifically targeting:
1. Combinatorial reasoning in exponential search spaces
2. Information extraction from noisy/deceptive data
3. Bayesian probabilistic inference
4. Strategic search and pruning
5. Computational complexity management

These evaluators assess mathematical reasoning capabilities such as:
- Enumeration of possibility spaces (combinatorics)
- Constraint satisfaction and propagation (SAT solving)
- Probabilistic updating (Bayes' theorem)
- Heuristic search algorithms
- Information theory (entropy, mutual information)
"""

import re
import math
import json
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Set, Any, Optional
import numpy as np


class CombinatorialReasoningEvaluator:
    """
    Evaluates ability to reason in exponentially large possibility spaces.

    Key metrics:
    1. Hypothesis Coverage: Does the player enumerate multiple scenarios?
    2. Elimination Rate: Does the player systematically rule out impossibilities?
    3. Constraint Usage: Does the player use logical constraints to prune search?
    4. Combinatorial Awareness: Does the player recognize the size of the problem?
    """

    def __init__(self, game_state, dialogue_history):
        self.game_state = game_state
        self.dialogue_history = dialogue_history

        # Handle both object and dict formats for game_state
        if hasattr(game_state, 'players'):
            # Object format
            self.num_players = len([p for p in game_state.players if p.get('alive', True)])
            self.num_wolves = game_state.wolf_num
        elif isinstance(game_state, dict):
            # Dict format
            players = game_state.get('players', [])
            self.num_players = len([p for p in players if p.get('alive', True)])
            self.num_wolves = game_state.get('wolf_num', 3)  # Default to 3 wolves
        else:
            # Fallback defaults
            self.num_players = 7
            self.num_wolves = 3

    def evaluate_player(self, player_id: int, round_num: int) -> Dict[str, float]:
        """
        Comprehensive evaluation of combinatorial reasoning ability.
        """

        # Get player's dialogues for this round
        player_dialogues = self._get_player_dialogues(player_id, round_num)

        if not player_dialogues:
            return self._zero_score()

        # Metric 1: Hypothesis Generation
        hypotheses_score = self._evaluate_hypothesis_generation(player_dialogues)

        # Metric 2: Systematic Elimination
        elimination_score = self._evaluate_elimination_strategy(player_dialogues)

        # Metric 3: Constraint-based Pruning
        constraint_score = self._evaluate_constraint_usage(player_dialogues)

        # Metric 4: Combinatorial Awareness
        awareness_score = self._evaluate_combinatorial_awareness(player_dialogues)

        # Metric 5: Search Depth
        depth_score = self._evaluate_reasoning_depth(player_dialogues)

        return {
            "hypothesis_generation": hypotheses_score,
            "systematic_elimination": elimination_score,
            "constraint_usage": constraint_score,
            "combinatorial_awareness": awareness_score,
            "reasoning_depth": depth_score,
            "composite_score": self._compute_composite([
                hypotheses_score, elimination_score, constraint_score,
                awareness_score, depth_score
            ])
        }

    def _evaluate_hypothesis_generation(self, dialogues: List[str]) -> float:
        """
        Score based on how many distinct hypotheses/scenarios the player considers.

        Examples of good reasoning:
        - "If Player 2 is the Seer, then Player 5 must be lying..."
        - "There are two possibilities: either X or Y..."
        - "Assuming Player 3 is a wolf, then..."

        Theoretical maximum hypotheses for N players, W wolves:
        - Role assignments: C(N, W) combinations
        - For 7 players, 3 wolves: C(7,3) = 35 possible wolf teams
        """
        full_text = " ".join(dialogues).lower()

        # Pattern matching for hypothesis indicators (both English and Chinese)
        hypothesis_patterns = [
            r'if .+? (is|were|was) .+?, then',
            r'(assuming|suppose|let\'s say|what if|scenario|possibility|case)',
            r'either .+? or .+?',
            r'could be .+? or .+?',
            r'two (scenarios|possibilities|cases)',
            r'multiple (scenarios|possibilities|explanations)',
            # Chinese patterns
            r'(如果|假设|假如|假设在|如果说) .+? (是|就是|那么)',
            r'(两种|多种|几种|多个) (可能|场景|情况|假设)',
            r'(或者|或|要么|还是) .+? (或者|或|要么|还是)',
            r'(可能是|应该是|应该) .+? (或者|或|也可能)',
        ]

        hypothesis_count = 0
        for pattern in hypothesis_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            hypothesis_count += len(matches)

        # Extract explicit scenario mentions (both English and Chinese)
        scenario_keywords = [
            'scenario', 'possibility', 'case', 'hypothesis', 'theory',
            '场景', '可能', '情况', '假设', '假定', '推测', '猜测', '理论'
        ]
        for keyword in scenario_keywords:
            hypothesis_count += full_text.count(keyword)

        # Adjusted baseline: realistic expectation is 2-3 hypothesis indicators per round
        # Not 10, which is way too high
        baseline = 3
        score = min(1.0, hypothesis_count / baseline) if baseline > 0 else 0.0
        return score

    def _evaluate_elimination_strategy(self, dialogues: List[str]) -> float:
        """
        Score based on systematic elimination of possibilities.

        Good indicators:
        - "This can't be true because..."
        - "We can rule out..."
        - "This contradicts..."
        - "This is impossible given..."
        """
        full_text = " ".join(dialogues).lower()

        elimination_patterns = [
            r'(cannot|can\'t|impossible|ruled? out|eliminate|exclude)',
            r'(contradicts?|inconsistent|doesn\'t match)',
            r'(therefore not|so .+? is not|thus .+? cannot)',
            r'(given .+?, .+? must be false)',
            # Chinese patterns
            r'(不可能|不能|不会|排除|排除出|不是)',
            r'(矛盾|不一致|不符合)',
            r'(所以.+?不是|因此.+?不是|故.+?不能)',
        ]

        elimination_count = 0
        for pattern in elimination_patterns:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            elimination_count += len(matches)

        # Check for explicit reasoning about impossibility
        impossibility_keywords = [
            'impossible', 'cannot', 'ruled out', 'eliminate', 'exclude',
            '不可能', '不能', '排除', '不是', '矛盾'
        ]
        for keyword in impossibility_keywords:
            elimination_count += full_text.count(keyword)

        # Adjusted: Even 1-2 clear eliminations show reasoning
        # Changed from 5 to 2 as more realistic expectation
        expected_eliminations = 2
        score = min(1.0, elimination_count / expected_eliminations)

        return score

    def _evaluate_constraint_usage(self, dialogues: List[str]) -> float:
        """
        Evaluate use of logical constraints to prune search space.

        Constraints in Werewolf:
        - Only one Seer exists (if two claim, one is lying)
        - Wolves know each other (wolf wouldn't accuse another wolf on Day 1)
        - Dead players' roles are known (constraints based on revealed roles)
        - Vote patterns (consistent voting behavior)
        """
        full_text = " ".join(dialogues).lower()

        constraint_indicators = 0

        # Pattern 1: Mutual exclusivity ("if A then not B")
        mutual_exclusion = [
            r'(only one|exactly one)',
            r'both cannot be',
            r'if .+? is .+?, then .+? cannot be',
            r'(either|neither) .+? (or|nor)',
        ]
        for pattern in mutual_exclusion:
            constraint_indicators += len(re.findall(pattern, full_text, re.IGNORECASE))

        # Pattern 2: Transitive reasoning ("if A then B, if B then C")
        transitive = [
            r'if .+?, then .+?, (and|so) .+?',
            r'since .+?, and .+?, therefore',
            r'given .+? and .+?, we (know|conclude)',
        ]
        for pattern in transitive:
            constraint_indicators += len(re.findall(pattern, full_text, re.IGNORECASE))

        # Pattern 3: Role-based constraints
        role_constraints = [
            'seer', 'witch', 'guard', 'hunter', 'wolf king',
            'claim', 'counter-claim', 'role conflict'
        ]
        for keyword in role_constraints:
            if keyword in full_text:
                constraint_indicators += 0.5  # Weaker signal

        # Adjusted: Even 1-2 constraint indicators show logical reasoning
        # Changed from 4 to 1.5 for more realistic scoring
        expected_constraints = 1.5
        score = min(1.0, constraint_indicators / expected_constraints) if expected_constraints > 0 else 0.0

        return score

    def _evaluate_combinatorial_awareness(self, dialogues: List[str]) -> float:
        """
        Does the player demonstrate awareness of the combinatorial complexity?

        Indicators:
        - Mentions of "many possibilities"
        - Explicit enumeration ("there are X scenarios")
        - Discussion of probability/likelihood
        - Acknowledgment of uncertainty
        """
        full_text = " ".join(dialogues).lower()

        awareness_score = 0.0

        # Explicit mention of multiple possibilities
        multiplicity_patterns = [
            r'(many|several|multiple|numerous) (possibilities|scenarios|cases)',
            r'(\d+) (different|possible) (scenarios|cases|possibilities)',
            r'(too many|countless|various) (ways|possibilities)',
        ]
        for pattern in multiplicity_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                awareness_score += 0.3

        # Probabilistic language (indicates awareness of uncertainty)
        probability_keywords = [
            'likely', 'unlikely', 'probably', 'possibly', 'maybe',
            'chance', 'probability', 'odds', 'percent'
        ]
        prob_count = sum(1 for kw in probability_keywords if kw in full_text)
        awareness_score += min(0.4, prob_count * 0.1)

        # Uncertainty acknowledgment
        uncertainty_patterns = [
            r'(not sure|uncertain|unclear|ambiguous)',
            r'(need more|insufficient) (information|evidence)',
            r'(could be|might be|may be)',
        ]
        for pattern in uncertainty_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                awareness_score += 0.15

        return min(1.0, awareness_score)

    def _evaluate_reasoning_depth(self, dialogues: List[str]) -> float:
        """
        Measure the depth of reasoning chain.

        Depth levels:
        - Depth 1: Single observation ("Player X voted for Y")
        - Depth 2: Single inference ("Player X voted for Y, so X suspects Y")
        - Depth 3: Chained inference ("X voted Y, so X suspects Y, but Y is likely good, so X might be wolf")
        - Depth 4+: Multiple chained inferences with counter-arguments
        """
        full_text = " ".join(dialogues).lower()

        # Count reasoning connectors
        depth_indicators = [
            'because', 'therefore', 'thus', 'hence', 'so',
            'which means', 'this implies', 'this suggests',
            'given that', 'considering', 'since'
        ]

        connector_count = sum(full_text.count(indicator) for indicator in depth_indicators)

        # Count logical chain markers
        chain_patterns = [
            r'if .+?, then .+?, (and|so|therefore)',
            r'since .+? and .+?, (then|therefore|thus)',
            r'first .+?, second .+?, (third|finally)',
        ]
        chain_count = sum(len(re.findall(pattern, full_text, re.IGNORECASE)) for pattern in chain_patterns)

        # Depth score: 1 connector = depth 2, 2 connectors = depth 3, etc.
        depth = 1 + connector_count * 0.5 + chain_count

        # Normalize: depth 4+ is excellent
        score = min(1.0, depth / 4.0)

        return score

    def _calculate_max_hypotheses(self) -> int:
        """Calculate theoretical maximum meaningful hypotheses."""
        n = self.num_players
        w = self.num_wolves

        # Maximum possible wolf teams
        from math import comb
        max_combinations = comb(n, w)

        # In practice, should consider top 10-20% most likely
        return max(5, int(max_combinations * 0.2))

    def _get_player_dialogues(self, player_id: int, round_num: int) -> List[str]:
        """Extract all dialogues from a specific player in a specific round."""
        dialogues = []
        for entry in self.dialogue_history:
            if (entry.get('player_id') == player_id and
                entry.get('round') == round_num and
                entry.get('type') in ['speech', 'dialogue']):
                dialogues.append(entry.get('content', ''))
        return dialogues

    def _zero_score(self) -> Dict[str, float]:
        """Return zero scores for all metrics."""
        return {
            "hypothesis_generation": 0.0,
            "systematic_elimination": 0.0,
            "constraint_usage": 0.0,
            "combinatorial_awareness": 0.0,
            "reasoning_depth": 0.0,
            "composite_score": 0.0
        }

    def _compute_composite(self, scores: List[float]) -> float:
        """Compute weighted composite score."""
        if not scores:
            return 0.0
        # Weighted average: hypothesis generation and elimination are most important
        weights = [0.25, 0.25, 0.2, 0.15, 0.15]
        return sum(s * w for s, w in zip(scores, weights))


class InformationTheoryEvaluator:
    """
    Evaluates information extraction from noisy environments.

    Key concepts:
    1. Signal-to-Noise Ratio: Can the player identify reliable information?
    2. Information Gain: Does the player extract new information each round?
    3. Source Credibility: Does the player weight information by source reliability?
    4. Multi-source Fusion: Does the player combine information from multiple sources?
    """

    def __init__(self, game_state, dialogue_history):
        self.game_state = game_state
        self.dialogue_history = dialogue_history

    def evaluate_player(self, player_id: int, round_num: int) -> Dict[str, float]:
        """Evaluate information extraction ability."""

        player_dialogues = self._get_player_dialogues(player_id, round_num)

        if not player_dialogues:
            return self._zero_score()

        # Metric 1: Signal Extraction
        signal_score = self._evaluate_signal_extraction(player_dialogues, round_num)

        # Metric 2: Information Gain Per Round
        info_gain_score = self._evaluate_information_gain(player_id, round_num)

        # Metric 3: Source Credibility Assessment
        credibility_score = self._evaluate_credibility_assessment(player_dialogues)

        # Metric 4: Cross-Validation
        cross_val_score = self._evaluate_cross_validation(player_dialogues)

        return {
            "signal_extraction": signal_score,
            "information_gain": info_gain_score,
            "credibility_assessment": credibility_score,
            "cross_validation": cross_val_score,
            "composite_score": np.mean([signal_score, info_gain_score, credibility_score, cross_val_score])
        }

    def _evaluate_signal_extraction(self, dialogues: List[str], round_num: int) -> float:
        """
        Evaluate ability to identify high-quality information amid noise.

        Signals in Werewolf:
        - Consistency over multiple rounds
        - Alignment with known facts
        - Logical coherence

        Noise:
        - Contradictions
        - Deception
        - Irrelevant information
        """
        full_text = " ".join(dialogues).lower()

        signal_indicators = 0.0

        # Pattern 1: References to verifiable facts
        fact_patterns = [
            r'(we know|it\'s confirmed|proven|revealed) that',
            r'(based on|according to) (the|what) (death|vote|claim)',
            r'(consistent with|matches|aligns with)',
        ]
        for pattern in fact_patterns:
            signal_indicators += len(re.findall(pattern, full_text, re.IGNORECASE)) * 0.2

        # Pattern 2: Identification of contradictions (spotting noise)
        noise_detection = [
            r'(contradicts?|inconsistent|doesn\'t match)',
            r'(claimed .+? but)',
            r'(said .+? (but|yet|however))',
        ]
        for pattern in noise_detection:
            signal_indicators += len(re.findall(pattern, full_text, re.IGNORECASE)) * 0.3

        # Pattern 3: Multi-round consistency checks
        consistency_keywords = ['consistent', 'pattern', 'behavior', 'history', 'track record']
        for kw in consistency_keywords:
            if kw in full_text:
                signal_indicators += 0.15

        return min(1.0, signal_indicators)

    def _evaluate_information_gain(self, player_id: int, round_num: int) -> float:
        """
        Measure whether player extracts NEW information each round.

        High information gain = player learns from new events
        Low information gain = player repeats same conclusions
        """
        # Get dialogues from this round and previous round
        current_dialogues = self._get_player_dialogues(player_id, round_num)
        previous_dialogues = self._get_player_dialogues(player_id, round_num - 1)

        if not current_dialogues:
            return 0.0

        # Extract key concepts/players mentioned
        current_concepts = self._extract_key_concepts(" ".join(current_dialogues))
        previous_concepts = self._extract_key_concepts(" ".join(previous_dialogues))

        # New concepts = information gain
        new_concepts = current_concepts - previous_concepts

        if len(current_concepts) == 0:
            return 0.0

        novelty_ratio = len(new_concepts) / max(len(current_concepts), 1)

        # Also check for explicit "new information" language
        full_text = " ".join(current_dialogues).lower()
        learning_indicators = ['now i realize', 'new information', 'just learned', 'this changes', 'update']
        learning_score = sum(0.2 for indicator in learning_indicators if indicator in full_text)

        return min(1.0, novelty_ratio + learning_score)

    def _evaluate_credibility_assessment(self, dialogues: List[str]) -> float:
        """
        Does the player assess source credibility?

        Good indicators:
        - "Player X is trustworthy because..."
        - "I believe/don't believe Player Y"
        - "Player Z has been consistent"
        """
        full_text = " ".join(dialogues).lower()

        credibility_score = 0.0

        # Explicit trust/distrust statements
        trust_patterns = [
            r'(trust|believe|suspicious of) player \d+',
            r'player \d+ (is|seems) (trustworthy|reliable|honest|deceptive|lying)',
            r'(don\'t believe|doubt) player \d+',
        ]
        for pattern in trust_patterns:
            credibility_score += len(re.findall(pattern, full_text, re.IGNORECASE)) * 0.25

        # Reasoning about credibility
        credibility_reasoning = [
            r'(because|since) .+? (been consistent|always voted|never)',
            r'track record',
            r'(history|past behavior)',
        ]
        for pattern in credibility_reasoning:
            credibility_score += len(re.findall(pattern, full_text, re.IGNORECASE)) * 0.3

        return min(1.0, credibility_score)

    def _evaluate_cross_validation(self, dialogues: List[str]) -> float:
        """
        Does the player cross-reference information from multiple sources?

        Example: "Player 2 said X, and Player 4 confirmed it, so..."
        """
        full_text = " ".join(dialogues).lower()

        # Check for references to multiple players
        player_mentions = re.findall(r'player \d+', full_text, re.IGNORECASE)
        unique_players = len(set(player_mentions))

        # Check for cross-referencing language
        cross_ref_patterns = [
            r'player \d+ (said|claimed).+?player \d+ (also|confirmed|contradicted)',
            r'both player \d+ and player \d+',
            r'(comparing|between) player \d+ and player \d+',
            r'player \d+.+?(while|but|whereas) player \d+',
        ]

        cross_ref_count = sum(len(re.findall(pattern, full_text, re.IGNORECASE)) for pattern in cross_ref_patterns)

        # Score: mentioning 3+ players + explicit cross-referencing
        multi_source_score = min(0.5, unique_players / 6)  # Max 0.5 for mentioning 3+ players
        cross_ref_score = min(0.5, cross_ref_count * 0.2)

        return multi_source_score + cross_ref_score

    def _extract_key_concepts(self, text: str) -> Set[str]:
        """Extract key concepts from text."""
        text = text.lower()
        concepts = set()

        # Extract player mentions
        concepts.update(re.findall(r'player \d+', text))

        # Extract role mentions
        roles = ['seer', 'witch', 'guard', 'hunter', 'wolf', 'villager']
        for role in roles:
            if role in text:
                concepts.add(role)

        # Extract action words
        actions = ['vote', 'claim', 'defend', 'accuse', 'suspect', 'trust', 'kill', 'protect']
        for action in actions:
            if action in text:
                concepts.add(action)

        return concepts

    def _get_player_dialogues(self, player_id: int, round_num: int) -> List[str]:
        """Extract all dialogues from a specific player in a specific round."""
        dialogues = []
        for entry in self.dialogue_history:
            if (entry.get('player_id') == player_id and
                entry.get('round') == round_num and
                entry.get('type') in ['speech', 'dialogue']):
                dialogues.append(entry.get('content', ''))
        return dialogues

    def _zero_score(self) -> Dict[str, float]:
        return {
            "signal_extraction": 0.0,
            "information_gain": 0.0,
            "credibility_assessment": 0.0,
            "cross_validation": 0.0,
            "composite_score": 0.0
        }


class BayesianReasoningEvaluator:
    """
    Evaluates probabilistic reasoning and Bayesian updating.

    Key metrics:
    1. Probability Language: Does the player use probabilistic terms?
    2. Bayesian Updating: Does the player update beliefs based on new evidence?
    3. Conditional Reasoning: Does the player reason about P(A|B)?
    4. Calibration: Are probability estimates reasonable?
    """

    def __init__(self, game_state, dialogue_history):
        self.game_state = game_state
        self.dialogue_history = dialogue_history

    def evaluate_player(self, player_id: int, round_num: int) -> Dict[str, float]:
        """Evaluate Bayesian reasoning ability."""

        player_dialogues = self._get_player_dialogues(player_id, round_num)

        if not player_dialogues:
            return self._zero_score()

        # Metric 1: Probability Language Usage
        prob_language_score = self._evaluate_probability_language(player_dialogues)

        # Metric 2: Evidence-Based Updating
        updating_score = self._evaluate_bayesian_updating(player_id, round_num)

        # Metric 3: Conditional Reasoning
        conditional_score = self._evaluate_conditional_reasoning(player_dialogues)

        # Metric 4: Quantitative Reasoning
        quant_score = self._evaluate_quantitative_reasoning(player_dialogues)

        return {
            "probability_language": prob_language_score,
            "bayesian_updating": updating_score,
            "conditional_reasoning": conditional_score,
            "quantitative_reasoning": quant_score,
            "composite_score": np.mean([prob_language_score, updating_score, conditional_score, quant_score])
        }

    def _evaluate_probability_language(self, dialogues: List[str]) -> float:
        """Score based on use of probabilistic language."""
        full_text = " ".join(dialogues).lower()

        prob_keywords = [
            'likely', 'unlikely', 'probably', 'possibly', 'maybe',
            'chance', 'probability', 'odds', 'percent', 'certain',
            'confident', 'doubt', 'sure', 'almost', 'barely',
            # Chinese keywords
            '可能', '可能性', '概率', '概率论', '大概', '也许',
            '大概率', '小概率', '可能性较大', '机率', '百分比', '百分',
            '我觉得', '我认为', '我估计', '应该是', '大概率', '确定', '不确定'
        ]

        keyword_count = sum(1 for kw in prob_keywords if kw in full_text)

        # Also check for comparative probability
        comparative_patterns = [
            r'more likely',
            r'less likely',
            r'most probable',
            r'least probable',
            r'higher chance',
            r'lower chance',
            # Chinese patterns
            r'更可能|更有可能',
            r'较大概率|较小概率',
            r'\d+%',  # Percentage
        ]
        comparative_count = sum(len(re.findall(pattern, full_text, re.IGNORECASE)) for pattern in comparative_patterns)

        # Adjusted: Even 1-2 probability keywords show statistical thinking
        # Score: keyword_count alone is often sufficient for decent score
        score = min(1.0, (keyword_count * 0.2) + (comparative_count * 0.3))

        return score

    def _evaluate_bayesian_updating(self, player_id: int, round_num: int) -> float:
        """
        Does the player update their beliefs based on new evidence?

        Good example:
        Round 1: "I think Player 3 is suspicious"
        Round 2: "Player 3 voted correctly, so I trust them more now"
        """
        if round_num <= 1:
            return 0.5  # Can't evaluate updating on first round

        current_dialogues = self._get_player_dialogues(player_id, round_num)
        previous_dialogues = self._get_player_dialogues(player_id, round_num - 1)

        full_text = " ".join(current_dialogues).lower()

        # Check for explicit updating language
        updating_patterns = [
            r'(now i|i now|changed my mind)',
            r'(previously|before) .+? (but now|however now)',
            r'(used to think|thought .+? but)',
            r'(evidence suggests|this shows|this proves)',
            r'(given|considering|based on) (what|this|that)',
        ]

        updating_count = sum(len(re.findall(pattern, full_text, re.IGNORECASE)) for pattern in updating_patterns)

        # Check for opinion shifts on specific players
        # Compare suspicion/trust mentions between rounds
        prev_text = " ".join(previous_dialogues).lower()

        opinion_shift = 0.0
        for player_num in range(1, 10):  # Check players 1-9
            prev_suspicion = f"player {player_num}" in prev_text and any(word in prev_text for word in ['suspect', 'wolf', 'lying'])
            curr_trust = f"player {player_num}" in full_text and any(word in full_text for word in ['trust', 'good', 'innocent'])

            if prev_suspicion and curr_trust:  # Opinion changed
                opinion_shift += 0.3

        score = min(1.0, (updating_count * 0.2) + opinion_shift)

        return score

    def _evaluate_conditional_reasoning(self, dialogues: List[str]) -> float:
        """
        Evaluate P(A|B) type reasoning.

        Example: "If Player 3 is the Seer (A), then Player 5 must be a wolf (B)"
        """
        full_text = " ".join(dialogues).lower()

        conditional_patterns = [
            r'if .+? (is|were|was) .+?, then .+? (is|must be|would be)',
            r'given (that)? .+?, .+? (is|must be|would be)',
            r'assuming .+?, (then)? .+?',
            r'(since|because) .+?, (therefore|thus|so) .+?',
        ]

        conditional_count = sum(len(re.findall(pattern, full_text, re.IGNORECASE)) for pattern in conditional_patterns)

        # Adjusted: Even 1 clear conditional statement shows good reasoning
        # Changed from 3 to 1 to be more realistic
        baseline = 1
        score = min(1.0, conditional_count / baseline) if baseline > 0 else 0.0

        return score

    def _evaluate_quantitative_reasoning(self, dialogues: List[str]) -> float:
        """
        Does the player use numbers/quantitative reasoning?

        Examples:
        - "There's a 70% chance Player 3 is a wolf"
        - "3 out of 5 times, Player 2 voted correctly"
        """
        full_text = " ".join(dialogues).lower()

        # Check for percentage/fraction usage
        quant_patterns = [
            r'\d+%',
            r'\d+/\d+',
            r'\d+ out of \d+',
            r'\d+ in \d+',
        ]

        quant_count = sum(len(re.findall(pattern, full_text)) for pattern in quant_patterns)

        # Check for counting/enumeration
        counting_keywords = ['count', 'total', 'sum', 'number of', 'how many']
        counting_score = sum(0.2 for kw in counting_keywords if kw in full_text)

        score = min(1.0, (quant_count * 0.3) + counting_score)

        return score

    def _get_player_dialogues(self, player_id: int, round_num: int) -> List[str]:
        """Extract all dialogues from a specific player in a specific round."""
        dialogues = []
        for entry in self.dialogue_history:
            if (entry.get('player_id') == player_id and
                entry.get('round') == round_num and
                entry.get('type') in ['speech', 'dialogue']):
                dialogues.append(entry.get('content', ''))
        return dialogues

    def _zero_score(self) -> Dict[str, float]:
        return {
            "probability_language": 0.0,
            "bayesian_updating": 0.0,
            "conditional_reasoning": 0.0,
            "quantitative_reasoning": 0.0,
            "composite_score": 0.0
        }


class SearchStrategyEvaluator:
    """
    Evaluates strategic search in exponential spaces.

    Key metrics:
    1. Search Depth: How many steps ahead does the player think?
    2. Pruning Efficiency: Does the player efficiently eliminate branches?
    3. Heuristic Quality: Does the player use good rules of thumb?
    4. Backtracking: Does the player revisit and revise earlier conclusions?
    """

    def __init__(self, game_state, dialogue_history):
        self.game_state = game_state
        self.dialogue_history = dialogue_history

    def evaluate_player(self, player_id: int, round_num: int) -> Dict[str, float]:
        """Evaluate search strategy."""

        player_dialogues = self._get_player_dialogues(player_id, round_num)

        if not player_dialogues:
            return self._zero_score()

        # Metric 1: Search Depth
        depth_score = self._evaluate_search_depth(player_dialogues)

        # Metric 2: Pruning Strategy
        pruning_score = self._evaluate_pruning(player_dialogues)

        # Metric 3: Heuristic Use
        heuristic_score = self._evaluate_heuristic_use(player_dialogues)

        # Metric 4: Exploration vs Exploitation
        explore_exploit_score = self._evaluate_explore_exploit(player_id, round_num)

        return {
            "search_depth": depth_score,
            "pruning_efficiency": pruning_score,
            "heuristic_quality": heuristic_score,
            "explore_exploit_balance": explore_exploit_score,
            "composite_score": np.mean([depth_score, pruning_score, heuristic_score, explore_exploit_score])
        }

    def _evaluate_search_depth(self, dialogues: List[str]) -> float:
        """
        Measure how many reasoning steps ahead the player thinks.

        Depth 1: "Player 3 voted for Player 5"
        Depth 2: "Player 3 voted for Player 5, so Player 3 suspects Player 5"
        Depth 3: "Player 3 voted for Player 5, so Player 3 suspects Player 5, but Player 5 is good, so Player 3 might be wolf"
        """
        full_text = " ".join(dialogues).lower()

        # Count logical connectors indicating reasoning chains
        connectors = ['because', 'therefore', 'thus', 'so', 'which means', 'this implies']
        connector_count = sum(full_text.count(c) for c in connectors)

        # Count multi-step reasoning patterns
        multi_step_patterns = [
            r'(first|then|next|finally)',
            r'step \d+',
            r'if .+?, then .+?, (and|so|therefore) .+?'
        ]
        multi_step_count = sum(len(re.findall(pattern, full_text, re.IGNORECASE)) for pattern in multi_step_patterns)

        # Depth = 1 + number of reasoning steps
        depth = 1 + connector_count + multi_step_count

        # Adjusted: Even depth 2 (1-2 connectors) shows good reasoning
        # Changed from 4 to 2.5 for more realistic normalization
        baseline = 2.5
        score = min(1.0, depth / baseline) if baseline > 0 else 0.0

        return score

    def _evaluate_pruning(self, dialogues: List[str]) -> float:
        """Evaluate search space pruning."""
        full_text = " ".join(dialogues).lower()

        pruning_patterns = [
            r'(rule out|eliminate|exclude|impossible)',
            r'(can\'t be|cannot be|not possible)',
            r'(narrow down|focus on)',
            r'(ignore|disregard|set aside)',
        ]

        pruning_count = sum(len(re.findall(pattern, full_text, re.IGNORECASE)) for pattern in pruning_patterns)

        # Adjusted: Even 1-2 pruning indicators show efficient search
        # Changed from 3 to 1.5
        baseline = 1.5
        score = min(1.0, pruning_count / baseline) if baseline > 0 else 0.0

        return score

    def _evaluate_heuristic_use(self, dialogues: List[str]) -> float:
        """
        Does the player use heuristics/rules of thumb?

        Common Werewolf heuristics:
        - Wolves don't kill strong speakers (to avoid suspicion)
        - First to claim Seer is often real Seer
        - Consistent voting patterns indicate same team
        """
        full_text = " ".join(dialogues).lower()

        heuristic_patterns = [
            r'usually', r'typically', r'generally', r'often',
            r'rule of thumb', r'pattern', r'tendency',
            r'in my experience', r'common', r'rare'
        ]

        heuristic_count = sum(1 for pattern in heuristic_patterns if pattern in full_text)

        score = min(1.0, heuristic_count / 5)

        return score

    def _evaluate_explore_exploit(self, player_id: int, round_num: int) -> float:
        """
        Balance between exploring new hypotheses vs exploiting current belief.

        Good: Exploring multiple theories early, committing later
        Bad: Either too rigid (only one theory) or too scattered (no commitment)
        """
        current_dialogues = self._get_player_dialogues(player_id, round_num)
        full_text = " ".join(current_dialogues).lower()

        # Count unique players mentioned (exploration)
        player_mentions = len(set(re.findall(r'player \d+', full_text)))
        exploration_score = min(0.5, player_mentions / 6)

        # Check for commitment statements (exploitation)
        commitment_patterns = [
            r'(i believe|i think|i\'m sure|confident that)',
            r'(definitely|certainly|clearly)',
            r'(should vote|must vote|will vote)',
        ]
        commitment_count = sum(len(re.findall(pattern, full_text, re.IGNORECASE)) for pattern in commitment_patterns)
        exploitation_score = min(0.5, commitment_count / 3)

        # Good balance = moderate exploration + moderate exploitation
        return exploration_score + exploitation_score

    def _get_player_dialogues(self, player_id: int, round_num: int) -> List[str]:
        """Extract all dialogues from a specific player in a specific round."""
        dialogues = []
        for entry in self.dialogue_history:
            if (entry.get('player_id') == player_id and
                entry.get('round') == round_num and
                entry.get('type') in ['speech', 'dialogue']):
                dialogues.append(entry.get('content', ''))
        return dialogues

    def _zero_score(self) -> Dict[str, float]:
        return {
            "search_depth": 0.0,
            "pruning_efficiency": 0.0,
            "heuristic_quality": 0.0,
            "explore_exploit_balance": 0.0,
            "composite_score": 0.0
        }


class ComplexityEvaluator:
    """
    Evaluates ability to handle computational complexity.

    Key metrics:
    1. Complexity Awareness: Does the player recognize the problem is hard?
    2. Approximation Strategy: Does the player use approximations when exact solution is intractable?
    3. Resource Management: Does the player allocate reasoning effort efficiently?
    4. Scalability: Does the player's strategy scale with game size?
    """

    def __init__(self, game_state, dialogue_history):
        self.game_state = game_state
        self.dialogue_history = dialogue_history

    def evaluate_player(self, player_id: int, round_num: int) -> Dict[str, float]:
        """Evaluate complexity handling."""

        player_dialogues = self._get_player_dialogues(player_id, round_num)

        if not player_dialogues:
            return self._zero_score()

        # Metric 1: Complexity Awareness
        awareness_score = self._evaluate_complexity_awareness(player_dialogues)

        # Metric 2: Approximation Use
        approximation_score = self._evaluate_approximation_strategy(player_dialogues)

        # Metric 3: Focus/Priority
        focus_score = self._evaluate_focus(player_dialogues)

        return {
            "complexity_awareness": awareness_score,
            "approximation_strategy": approximation_score,
            "focus_prioritization": focus_score,
            "composite_score": np.mean([awareness_score, approximation_score, focus_score])
        }

    def _evaluate_complexity_awareness(self, dialogues: List[str]) -> float:
        """Does the player acknowledge the difficulty of the problem?"""
        full_text = " ".join(dialogues).lower()

        awareness_keywords = [
            'complex', 'complicated', 'difficult', 'hard to tell',
            'uncertain', 'many possibilities', 'unclear',
            'need more information', 'not enough evidence',
            # Chinese keywords
            '复杂', '困难', '不确定', '不太确定', '很多可能', '不清楚',
            '不一定', '可能性多', '无法确定', '存疑', '可能有很多', '两个都有可能'
        ]

        awareness_count = sum(1 for kw in awareness_keywords if kw in full_text)

        # Adjusted: Even 1 awareness keyword shows understanding
        # Changed from 3 to 1
        baseline = 1
        score = min(1.0, awareness_count / baseline) if baseline > 0 else 0.0

        return score

    def _evaluate_approximation_strategy(self, dialogues: List[str]) -> float:
        """
        Does the player use approximations/heuristics instead of trying to be exact?

        Good: "Player 3 is most likely good, so I'll focus on others"
        Bad: "I need to check every single possibility"
        """
        full_text = " ".join(dialogues).lower()

        approximation_patterns = [
            r'(most likely|probably|seems to be)',
            r'(focus on|prioritize|main suspects)',
            r'(top|main|primary) (candidates|suspects)',
            r'(narrow down|focus|concentrate)',
        ]

        approx_count = sum(len(re.findall(pattern, full_text, re.IGNORECASE)) for pattern in approximation_patterns)

        # Adjusted: Even 1-2 approximation indicators show practical reasoning
        # Changed from 4 to 1.5
        baseline = 1.5
        score = min(1.0, approx_count / baseline) if baseline > 0 else 0.0

        return score

    def _evaluate_focus(self, dialogues: List[str]) -> float:
        """Does the player focus on high-value information?"""
        full_text = " ".join(dialogues).lower()

        focus_patterns = [
            r'(focus on|concentrate on|pay attention to)',
            r'(priority|priorities|most important)',
            r'(key|crucial|critical) (is|point|factor)',
        ]

        focus_count = sum(len(re.findall(pattern, full_text, re.IGNORECASE)) for pattern in focus_patterns)

        # Adjusted: Even 1 focus indicator shows prioritization thinking
        # Changed from 3 to 1
        baseline = 1
        score = min(1.0, focus_count / baseline) if baseline > 0 else 0.0

        return score

    def _get_player_dialogues(self, player_id: int, round_num: int) -> List[str]:
        """Extract all dialogues from a specific player in a specific round."""
        dialogues = []
        for entry in self.dialogue_history:
            if (entry.get('player_id') == player_id and
                entry.get('round') == round_num and
                entry.get('type') in ['speech', 'dialogue']):
                dialogues.append(entry.get('content', ''))
        return dialogues

    def _zero_score(self) -> Dict[str, float]:
        return {
            "complexity_awareness": 0.0,
            "approximation_strategy": 0.0,
            "focus_prioritization": 0.0,
            "composite_score": 0.0
        }


# Example usage and integration
def evaluate_deep_reasoning(game_state, dialogue_history, player_id: int, round_num: int) -> Dict[str, Any]:
    """
    Comprehensive deep reasoning evaluation for a single player in a single round.

    Returns:
        Dictionary with scores for all dimensions of deep reasoning.
    """

    # Initialize all evaluators
    combinatorial = CombinatorialReasoningEvaluator(game_state, dialogue_history)
    information = InformationTheoryEvaluator(game_state, dialogue_history)
    bayesian = BayesianReasoningEvaluator(game_state, dialogue_history)
    search = SearchStrategyEvaluator(game_state, dialogue_history)
    complexity = ComplexityEvaluator(game_state, dialogue_history)

    # Run all evaluations
    results = {
        "combinatorial_reasoning": combinatorial.evaluate_player(player_id, round_num),
        "information_theory": information.evaluate_player(player_id, round_num),
        "bayesian_reasoning": bayesian.evaluate_player(player_id, round_num),
        "search_strategy": search.evaluate_player(player_id, round_num),
        "complexity_handling": complexity.evaluate_player(player_id, round_num),
    }

    # Compute overall deep reasoning score
    composite_scores = [
        results["combinatorial_reasoning"]["composite_score"],
        results["information_theory"]["composite_score"],
        results["bayesian_reasoning"]["composite_score"],
        results["search_strategy"]["composite_score"],
        results["complexity_handling"]["composite_score"],
    ]

    results["overall_deep_reasoning_score"] = np.mean(composite_scores)

    return results
