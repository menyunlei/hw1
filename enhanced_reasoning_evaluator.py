"""
Enhanced Deep Reasoning Evaluator with Combinatorial & Mathematical Metrics
===========================================================================

This module extends the basic ReasoningEvaluator with advanced mathematical
reasoning capabilities specifically designed to evaluate performance in
combinatorially explosive environments like Werewolf.

New Evaluation Dimensions:
1. Combinatorial Reasoning (组合推理)
2. Information Theory Metrics (信息论指标)
3. Bayesian Reasoning (贝叶斯推理)
4. Strategic Search (策略搜索)
5. Complexity Handling (复杂度处理)

These dimensions specifically target the "trillions of vote combinations" problem
and evaluate the ability to reason in exponentially large search spaces.
"""

import json
from collections import defaultdict
import re
import numpy as np

# Import the original evaluator
from reasoning_evaluator import ReasoningEvaluator

# Import new deep reasoning evaluators
from deep_reasoning_evaluators import (
    CombinatorialReasoningEvaluator,
    InformationTheoryEvaluator,
    BayesianReasoningEvaluator,
    SearchStrategyEvaluator,
    ComplexityEvaluator,
    evaluate_deep_reasoning
)


class EnhancedReasoningEvaluator(ReasoningEvaluator):
    """
    Enhanced evaluator that combines traditional metrics with deep reasoning metrics.

    Original 6 Dimensions (from ReasoningEvaluator):
    - Information Extraction
    - Logical Deduction
    - Pattern Recognition
    - Vote Analysis
    - Adaptive Behavior
    - Communication Quality

    New 5 Deep Reasoning Dimensions:
    - Combinatorial Reasoning
    - Information Theory
    - Bayesian Reasoning
    - Strategic Search
    - Complexity Handling
    """

    def __init__(self, test_subject_id=7):
        super().__init__(test_subject_id)

        # Add new evaluation dimensions
        self.deep_reasoning_dimensions = {
            "combinatorial_reasoning": {
                "name": "组合推理能力 (Combinatorial Reasoning)",
                "weight": 0.25,  # High weight - this is core to trillions of combinations
                "max_score": 100,
                "description": "在指数级可能性空间中进行推理的能力",
                "math_concepts": ["组合数学 C(n,k)", "搜索空间剪枝", "约束传播"]
            },
            "information_theory": {
                "name": "信息提取能力 (Information Theory)",
                "weight": 0.20,
                "max_score": 100,
                "description": "从噪声中提取信号的能力",
                "math_concepts": ["信息熵", "信噪比", "互信息"]
            },
            "bayesian_reasoning": {
                "name": "概率推理能力 (Bayesian Reasoning)",
                "weight": 0.20,
                "max_score": 100,
                "description": "贝叶斯更新和概率推理能力",
                "math_concepts": ["贝叶斯定理", "条件概率", "似然估计"]
            },
            "strategic_search": {
                "name": "策略搜索能力 (Strategic Search)",
                "weight": 0.20,
                "max_score": 100,
                "description": "在指数搜索空间中的策略能力",
                "math_concepts": ["启发式搜索", "A*算法", "探索vs利用"]
            },
            "complexity_handling": {
                "name": "复杂度处理能力 (Complexity Handling)",
                "weight": 0.15,
                "max_score": 100,
                "description": "处理NP-hard问题的能力",
                "math_concepts": ["近似算法", "复杂度分析", "资源管理"]
            }
        }

        # Store game state for deep reasoning evaluation
        self.game_state = None
        self.dialogue_history = []

    def set_game_context(self, game_state, dialogue_history):
        """
        Set the game context needed for deep reasoning evaluation.

        Args:
            game_state: Current game state object
            dialogue_history: List of all dialogues
        """
        self.game_state = game_state
        self.dialogue_history = dialogue_history

    def evaluate_deep_reasoning_dimensions(self, round_num=None):
        """
        Evaluate all deep reasoning dimensions for the test subject.

        Args:
            round_num: Specific round to evaluate, or None for all rounds

        Returns:
            Dict with scores for each deep reasoning dimension
        """
        if self.game_state is None or not self.dialogue_history:
            return {
                "error": "Game context not set. Call set_game_context() first.",
                "scores": {}
            }

        # If no round specified, use the latest round
        if round_num is None:
            round_num = max((entry.get('round', 1) for entry in self.dialogue_history), default=1)

        # Run deep reasoning evaluation
        deep_results = evaluate_deep_reasoning(
            self.game_state,
            self.dialogue_history,
            self.test_subject_id,
            round_num
        )

        return deep_results

    def calculate_comprehensive_score(self, include_deep_reasoning=True, round_num=None):
        """
        Calculate comprehensive score combining traditional and deep reasoning metrics.

        Args:
            include_deep_reasoning: Whether to include deep reasoning dimensions
            round_num: Round number for deep reasoning evaluation

        Returns:
            Dict with comprehensive evaluation results
        """
        # Calculate traditional scores (from parent class)
        traditional_results = self.calculate_final_score()

        if not include_deep_reasoning:
            return traditional_results

        # Calculate deep reasoning scores
        deep_results = self.evaluate_deep_reasoning_dimensions(round_num)

        if "error" in deep_results:
            return {
                **traditional_results,
                "deep_reasoning_error": deep_results["error"],
                "deep_reasoning_enabled": False
            }

        # Combine scores
        combined_results = {
            "player_id": self.test_subject_id,
            "traditional_metrics": traditional_results,
            "deep_reasoning_metrics": deep_results,
            "comprehensive_score": self._compute_comprehensive_score(
                traditional_results,
                deep_results
            ),
            "evaluation_type": "Enhanced (Traditional + Deep Reasoning)"
        }

        return combined_results

    def _compute_comprehensive_score(self, traditional_results, deep_results):
        """
        Compute weighted comprehensive score from both traditional and deep reasoning.

        Weighting strategy:
        - Traditional metrics: 40%
        - Deep reasoning metrics: 60% (higher weight for mathematical reasoning)
        """
        # Extract traditional score
        traditional_score = traditional_results.get("weighted_score", 0)

        # Extract deep reasoning score
        deep_score = deep_results.get("overall_deep_reasoning_score", 0) * 100  # Convert to 0-100 scale

        # Weighted combination
        comprehensive_score = (traditional_score * 0.4) + (deep_score * 0.6)

        # Determine comprehensive grade
        if comprehensive_score >= 90:
            grade = "S+ (卓越+) - 深度数学推理能力突出"
        elif comprehensive_score >= 85:
            grade = "S (卓越) - 优秀的数学推理能力"
        elif comprehensive_score >= 80:
            grade = "A+ (优秀+) - 强大的组合推理能力"
        elif comprehensive_score >= 75:
            grade = "A (优秀) - 良好的数学推理能力"
        elif comprehensive_score >= 70:
            grade = "B+ (良好+) - 基本数学推理能力"
        elif comprehensive_score >= 65:
            grade = "B (良好) - 推理能力尚可"
        elif comprehensive_score >= 60:
            grade = "C (及格) - 基础推理能力"
        else:
            grade = "D (不及格) - 推理能力需要提升"

        return {
            "overall_score": round(comprehensive_score, 2),
            "grade": grade,
            "traditional_contribution": round(traditional_score * 0.4, 2),
            "deep_reasoning_contribution": round(deep_score * 0.6, 2),
            "breakdown": {
                "traditional_score": traditional_score,
                "deep_reasoning_score": round(deep_score, 2)
            }
        }

    def generate_comprehensive_report(self, round_num=None):
        """
        Generate comprehensive report with both traditional and deep reasoning metrics.
        """
        # Calculate comprehensive scores
        results = self.calculate_comprehensive_score(
            include_deep_reasoning=True,
            round_num=round_num
        )

        if results.get("deep_reasoning_enabled") == False:
            # Fall back to traditional report
            return self.generate_report()

        report = []
        report.append("=" * 100)
        report.append("增强型深度推理能力评估报告 (Enhanced Deep Reasoning Evaluation Report)")
        report.append("=" * 100)
        report.append(f"\n测试主体: Player {self.test_subject_id}")
        report.append(f"评估类型: {results['evaluation_type']}")

        # Overall Score
        comp_score = results["comprehensive_score"]
        report.append(f"\n【综合得分】")
        report.append(f"总分: {comp_score['overall_score']}/100")
        report.append(f"等级: {comp_score['grade']}")
        report.append(f"\n分数构成:")
        report.append(f"  传统指标贡献: {comp_score['traditional_contribution']:.2f} (权重: 40%)")
        report.append(f"  深度推理贡献: {comp_score['deep_reasoning_contribution']:.2f} (权重: 60%)")

        # Traditional Metrics Section
        report.append("\n" + "=" * 100)
        report.append("【传统评估指标】Traditional Metrics (40% weight)")
        report.append("=" * 100)

        trad_results = results["traditional_metrics"]
        trad_scores = trad_results.get("scores", {})

        for dim_key, dim_info in self.dimensions.items():
            result = trad_scores.get(dim_key, {})
            score = result.get("score", 0)
            weight = dim_info["weight"]

            report.append(f"\n【{dim_info['name']}】 权重: {weight*100}%")
            report.append(f"得分: {score}/100")
            for detail in result.get("details", []):
                report.append(f"  {detail}")

        # Deep Reasoning Metrics Section
        report.append("\n" + "=" * 100)
        report.append("【深度推理指标】Deep Reasoning Metrics (60% weight)")
        report.append("=" * 100)
        report.append("这些指标评估在指数级复杂度环境中的数学推理能力\n")

        deep_results = results["deep_reasoning_metrics"]

        # Combinatorial Reasoning
        report.append(self._format_deep_dimension(
            "组合推理能力 (Combinatorial Reasoning)",
            deep_results.get("combinatorial_reasoning", {}),
            self.deep_reasoning_dimensions["combinatorial_reasoning"]
        ))

        # Information Theory
        report.append(self._format_deep_dimension(
            "信息论指标 (Information Theory)",
            deep_results.get("information_theory", {}),
            self.deep_reasoning_dimensions["information_theory"]
        ))

        # Bayesian Reasoning
        report.append(self._format_deep_dimension(
            "贝叶斯推理 (Bayesian Reasoning)",
            deep_results.get("bayesian_reasoning", {}),
            self.deep_reasoning_dimensions["bayesian_reasoning"]
        ))

        # Strategic Search
        report.append(self._format_deep_dimension(
            "策略搜索 (Strategic Search)",
            deep_results.get("search_strategy", {}),
            self.deep_reasoning_dimensions["strategic_search"]
        ))

        # Complexity Handling
        report.append(self._format_deep_dimension(
            "复杂度处理 (Complexity Handling)",
            deep_results.get("complexity_handling", {}),
            self.deep_reasoning_dimensions["complexity_handling"]
        ))

        # Mathematical Reasoning Summary
        report.append("\n" + "=" * 100)
        report.append("【数学推理能力总结】Mathematical Reasoning Summary")
        report.append("=" * 100)

        overall_deep_score = deep_results.get("overall_deep_reasoning_score", 0) * 100

        report.append(f"\n深度推理综合分数: {overall_deep_score:.2f}/100")
        report.append(f"\n对应数学能力:")
        report.append(f"  • 组合数学 (Combinatorics): 能否在C(N,W)个可能性中推理?")
        report.append(f"  • 信息论 (Information Theory): 能否从噪声中提取信号?")
        report.append(f"  • 概率论 (Probability Theory): 能否进行贝叶斯更新?")
        report.append(f"  • 算法设计 (Algorithm Design): 能否使用启发式搜索?")
        report.append(f"  • 复杂度分析 (Complexity Analysis): 能否识别NP-hard问题?")

        # Interpretation
        report.append("\n" + "=" * 100)
        report.append("【评估说明】Interpretation")
        report.append("=" * 100)
        report.append("\n狼人杀的推理复杂度:")
        report.append("  • 7名玩家，3只狼: C(7,3) = 35 种可能的狼队组合")
        report.append("  • 每天投票: 7^7 ≈ 823,543 种可能的投票组合")
        report.append("  • 5轮游戏: 总决策空间 > 10^15 (千万亿级别)")
        report.append("\n这就是 'trillions of vote combinations' 问题!")
        report.append("优秀的AI应该能在这个指数级空间中进行有效推理。")

        report.append("\n" + "=" * 100)
        report.append("统计数据:")
        report.append("=" * 100)
        report.append(f"发言次数: {len(self.speeches)}")
        report.append(f"投票次数: {len(self.votes)}")
        report.append(f"记录事件: {len(self.events)}个")

        return "\n".join(report)

    def _format_deep_dimension(self, name, scores, dimension_info):
        """Format a deep reasoning dimension for the report."""
        lines = []
        lines.append(f"\n【{name}】 权重: {dimension_info['weight']*100}%")
        lines.append(f"描述: {dimension_info['description']}")
        lines.append(f"数学概念: {', '.join(dimension_info['math_concepts'])}")
        lines.append(f"\n维度得分:")

        composite_score = scores.get("composite_score", 0) * 100

        # Extract sub-scores
        for metric_key, metric_value in scores.items():
            if metric_key != "composite_score" and isinstance(metric_value, (int, float)):
                score_pct = metric_value * 100
                status = "✓" if score_pct >= 70 else "○" if score_pct >= 40 else "✗"
                lines.append(f"  {status} {metric_key}: {score_pct:.1f}/100")

        lines.append(f"\n综合得分: {composite_score:.2f}/100")

        return "\n".join(lines)

    def export_comprehensive_json(self, filename="comprehensive_evaluation_result.json"):
        """Export comprehensive evaluation results to JSON."""
        results = self.calculate_comprehensive_score(include_deep_reasoning=True)

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        return filename


# Example usage
if __name__ == "__main__":
    import sys
    import io

    # Set stdout encoding to utf-8 for Windows
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # Create enhanced evaluator
    evaluator = EnhancedReasoningEvaluator(test_subject_id=7)

    # Simulate some events
    evaluator.add_event("speech", 7, "根据组合数学，7个人中有3只狼，共有C(7,3)=35种可能。我需要系统性地排除不可能的组合。", 1)
    evaluator.add_event("speech", 7, "如果2号是真预言家，那么10号是狼的概率是90%。但如果10号是真预言家，那么2号是狼的概率是80%。我倾向于相信2号。", 1)
    evaluator.add_event("vote", 7, "投票给2号", 1, {"vote_type": "sheriff", "target": 2})
    evaluator.add_event("speech", 7, "从信息论角度，两个预言家的对跳产生了高信息量。我通过交叉验证他们的发言，发现10号有3处矛盾。", 2)

    # For full evaluation, need to set game context (in real game, this would be automatic)
    print("=" * 100)
    print("演示: 增强型评估器")
    print("=" * 100)
    print("\n注意: 完整的深度推理评估需要游戏状态(game_state)和对话历史(dialogue_history)。")
    print("这里仅展示传统指标评估。\n")

    # Calculate traditional scores only (no game context)
    result = evaluator.calculate_final_score()

    # Generate report
    report = evaluator.generate_report()
    print(report)

    print("\n" + "=" * 100)
    print("要启用完整的深度推理评估，需要:")
    print("=" * 100)
    print("1. evaluator.set_game_context(game_state, dialogue_history)")
    print("2. comprehensive_results = evaluator.calculate_comprehensive_score()")
    print("3. report = evaluator.generate_comprehensive_report()")
    print("\n这将评估包括:")
    print("  • 组合推理能力 (在trillions of combinations中推理)")
    print("  • 信息提取能力 (从错误信息中筛选正确信息)")
    print("  • 贝叶斯推理能力 (概率更新)")
    print("  • 策略搜索能力 (启发式搜索)")
    print("  • 复杂度处理能力 (NP-hard问题)")
