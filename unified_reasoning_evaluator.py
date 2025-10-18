"""
Unified Deep Reasoning Evaluation System
统一深度推理评估系统

Integrates Werewolf game evaluation with multi-domain reasoning tasks
to provide comprehensive assessment of LLM deep reasoning capabilities.
"""

import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import os

# Import existing modules
from reasoning_evaluator import ReasoningEvaluator
from multi_domain_reasoning_framework import (
    MultiDomainEvaluator,
    MathematicalReasoningTasks,
    LogicalReasoningTasks,
    CausalReasoningTasks,
    ScientificReasoningTasks,
    StrategicReasoningTasks,
    ReasoningDomain
)

class UnifiedReasoningEvaluator:
    """
    Unified system that combines social deduction (Werewolf)
    with mathematical and other reasoning domains
    """

    def __init__(self, test_subject_id=7):
        self.test_subject_id = test_subject_id

        # Initialize component evaluators
        self.werewolf_evaluator = ReasoningEvaluator(test_subject_id)
        self.multi_domain_evaluator = MultiDomainEvaluator()

        # Results storage
        self.comprehensive_results = {
            "timestamp": datetime.now().isoformat(),
            "test_subject": f"Player {test_subject_id}",
            "domains_evaluated": [],
            "overall_score": 0,
            "overall_grade": "",
            "domain_scores": {},
            "detailed_analysis": {}
        }

        # Enhanced weights for comprehensive evaluation
        self.domain_weights = {
            "social_deduction": 0.15,      # Werewolf game
            "mathematical": 0.20,           # Math reasoning (increased weight)
            "logical": 0.15,               # Logic puzzles
            "causal": 0.10,                # Cause-effect
            "scientific": 0.10,            # Scientific method
            "strategic": 0.10,             # Game theory
            "pattern_recognition": 0.10,   # From Werewolf
            "communication": 0.10          # From Werewolf
        }

    def evaluate_werewolf_performance(self):
        """
        Extract and evaluate Werewolf game performance
        Returns domain-specific scores
        """
        # Run Werewolf evaluation
        werewolf_results = self.werewolf_evaluator.calculate_final_score()

        # Map Werewolf scores to broader domains
        domain_mapping = {
            "social_deduction": {
                "score": werewolf_results["weighted_score"],
                "components": {
                    "information_extraction": werewolf_results["scores"]["information_extraction"]["score"],
                    "vote_analysis": werewolf_results["scores"]["vote_analysis"]["score"],
                    "adaptive_behavior": werewolf_results["scores"]["adaptive_behavior"]["score"]
                },
                "description": "Performance in Werewolf game social deduction"
            },
            "pattern_recognition": {
                "score": werewolf_results["scores"]["pattern_recognition"]["score"],
                "components": {
                    "wolf_pack_identification": "From Werewolf pattern analysis",
                    "vote_patterns": "From vote analysis",
                    "speech_patterns": "From communication analysis"
                },
                "description": "Pattern recognition in social dynamics"
            },
            "communication": {
                "score": werewolf_results["scores"]["communication_quality"]["score"],
                "components": {
                    "clarity": "Speech structure and clarity",
                    "persuasiveness": "Ability to convince others",
                    "information_delivery": "Key information communication"
                },
                "description": "Strategic communication abilities"
            }
        }

        return domain_mapping, werewolf_results

    async def evaluate_mathematical_reasoning(self, llm_interface=None):
        """
        Comprehensive mathematical reasoning evaluation
        """
        tasks = []
        results = []

        # Task 1: Basic Algebra
        tasks.append({
            "type": "algebra",
            "problem": "Solve: 2x² - 8x + 6 = 0",
            "difficulty": "easy",
            "max_score": 25
        })

        # Task 2: Word Problem
        tasks.append({
            "type": "word_problem",
            "problem": "A factory produces widgets at a rate that increases by 10% each month. If it produces 1000 widgets in January, how many total widgets will it have produced by the end of June?",
            "difficulty": "medium",
            "max_score": 25
        })

        # Task 3: Proof
        tasks.append({
            "type": "proof",
            "problem": "Prove that the sum of any two odd numbers is even",
            "difficulty": "easy",
            "max_score": 25
        })

        # Task 4: Probability
        tasks.append({
            "type": "probability",
            "problem": "In a bag with 5 red, 3 blue, and 2 green balls, what's the probability of drawing 2 balls of the same color without replacement?",
            "difficulty": "medium",
            "max_score": 25
        })

        # Simulate evaluation (in real system, would send to LLM)
        total_score = 0
        for task in tasks:
            # This would normally involve sending to LLM and evaluating response
            # For demonstration, using placeholder scoring
            task_score = self._evaluate_math_task(task, llm_interface)
            results.append({
                "task": task["type"],
                "score": task_score,
                "max": task["max_score"]
            })
            total_score += task_score

        return {
            "score": total_score,
            "max_score": 100,
            "tasks_evaluated": len(tasks),
            "breakdown": results,
            "strengths": self._identify_math_strengths(results),
            "weaknesses": self._identify_math_weaknesses(results)
        }

    def _evaluate_math_task(self, task, llm_interface=None):
        """
        Evaluate a single math task
        In production, this would analyze LLM's response
        """
        # Placeholder scoring logic
        # In real implementation, would check:
        # - Problem understanding
        # - Step-by-step reasoning
        # - Correct methodology
        # - Final answer
        # - Verification/checking

        base_score = task["max_score"] * 0.7  # Placeholder
        return base_score

    def _identify_math_strengths(self, results):
        """Identify mathematical reasoning strengths"""
        strengths = []
        for result in results:
            if result["score"] / result["max"] >= 0.8:
                strengths.append(f"Strong in {result['task']}")
        return strengths

    def _identify_math_weaknesses(self, results):
        """Identify mathematical reasoning weaknesses"""
        weaknesses = []
        for result in results:
            if result["score"] / result["max"] < 0.6:
                weaknesses.append(f"Needs improvement in {result['task']}")
        return weaknesses

    async def evaluate_logical_reasoning(self, llm_interface=None):
        """Evaluate logical and deductive reasoning"""

        tasks = []

        # Syllogistic reasoning
        tasks.append({
            "type": "syllogism",
            "premises": [
                "All neural networks are machine learning models",
                "Some machine learning models are interpretable",
                "GPT is a neural network"
            ],
            "question": "What can we conclude about GPT?",
            "max_score": 33
        })

        # Truth table reasoning
        tasks.append({
            "type": "truth_table",
            "problem": "If P→Q and Q→R, and we know R is false, what can we conclude?",
            "max_score": 33
        })

        # Logical paradox
        tasks.append({
            "type": "paradox",
            "problem": "Resolve: 'This statement is false'",
            "max_score": 34
        })

        # Evaluate tasks
        total_score = 0
        for task in tasks:
            task_score = self._evaluate_logic_task(task, llm_interface)
            total_score += task_score

        return {
            "score": total_score,
            "max_score": 100,
            "tasks_evaluated": len(tasks)
        }

    def _evaluate_logic_task(self, task, llm_interface=None):
        """Evaluate a single logic task"""
        # Placeholder - would check for:
        # - Valid logical structure
        # - Correct inference rules
        # - Avoidance of fallacies
        return task["max_score"] * 0.75

    async def run_comprehensive_evaluation(self,
                                          include_werewolf=True,
                                          llm_interface=None):
        """
        Run complete evaluation across all domains
        """
        print("=" * 60)
        print("COMPREHENSIVE DEEP REASONING EVALUATION")
        print("=" * 60)

        all_scores = {}

        # 1. Werewolf/Social Deduction Evaluation
        if include_werewolf:
            print("\n[1/6] Evaluating Social Deduction (Werewolf)...")
            werewolf_domains, werewolf_raw = self.evaluate_werewolf_performance()
            all_scores.update(werewolf_domains)
            self.comprehensive_results["domains_evaluated"].append("social_deduction")

        # 2. Mathematical Reasoning
        print("\n[2/6] Evaluating Mathematical Reasoning...")
        math_results = await self.evaluate_mathematical_reasoning(llm_interface)
        all_scores["mathematical"] = {
            "score": math_results["score"],
            "components": math_results["breakdown"],
            "description": "Mathematical problem solving and proofs"
        }
        self.comprehensive_results["domains_evaluated"].append("mathematical")

        # 3. Logical Reasoning
        print("\n[3/6] Evaluating Logical Reasoning...")
        logic_results = await self.evaluate_logical_reasoning(llm_interface)
        all_scores["logical"] = {
            "score": logic_results["score"],
            "description": "Logical deduction and inference"
        }
        self.comprehensive_results["domains_evaluated"].append("logical")

        # 4. Causal Reasoning
        print("\n[4/6] Evaluating Causal Reasoning...")
        causal_results = self._evaluate_causal_reasoning()
        all_scores["causal"] = causal_results
        self.comprehensive_results["domains_evaluated"].append("causal")

        # 5. Scientific Reasoning
        print("\n[5/6] Evaluating Scientific Reasoning...")
        scientific_results = self._evaluate_scientific_reasoning()
        all_scores["scientific"] = scientific_results
        self.comprehensive_results["domains_evaluated"].append("scientific")

        # 6. Strategic Reasoning
        print("\n[6/6] Evaluating Strategic Reasoning...")
        strategic_results = self._evaluate_strategic_reasoning()
        all_scores["strategic"] = strategic_results
        self.comprehensive_results["domains_evaluated"].append("strategic")

        # Calculate overall score
        self._calculate_overall_score(all_scores)

        # Generate final report
        return self.generate_final_report(all_scores)

    def _evaluate_causal_reasoning(self):
        """Evaluate causal reasoning abilities"""
        return {
            "score": 75,  # Placeholder
            "description": "Cause-effect analysis and counterfactual reasoning"
        }

    def _evaluate_scientific_reasoning(self):
        """Evaluate scientific method application"""
        return {
            "score": 70,  # Placeholder
            "description": "Hypothesis testing and experimental design"
        }

    def _evaluate_strategic_reasoning(self):
        """Evaluate strategic and game-theoretic reasoning"""
        return {
            "score": 72,  # Placeholder
            "description": "Game theory and strategic decision making"
        }

    def _calculate_overall_score(self, all_scores):
        """Calculate weighted overall score"""
        total_weighted = 0
        total_weight = 0

        for domain, weight in self.domain_weights.items():
            if domain in all_scores:
                score = all_scores[domain].get("score", 0)
                total_weighted += score * weight
                total_weight += weight

        # Normalize if not all domains evaluated
        if total_weight > 0:
            self.comprehensive_results["overall_score"] = round(total_weighted / total_weight, 2)
        else:
            self.comprehensive_results["overall_score"] = 0

        # Determine grade
        score = self.comprehensive_results["overall_score"]
        if score >= 90:
            self.comprehensive_results["overall_grade"] = "S - Exceptional Deep Reasoning Capability"
        elif score >= 80:
            self.comprehensive_results["overall_grade"] = "A - Strong Deep Reasoning Capability"
        elif score >= 70:
            self.comprehensive_results["overall_grade"] = "B - Good Deep Reasoning Capability"
        elif score >= 60:
            self.comprehensive_results["overall_grade"] = "C - Adequate Deep Reasoning Capability"
        else:
            self.comprehensive_results["overall_grade"] = "D - Limited Deep Reasoning Capability"

    def generate_final_report(self, all_scores):
        """Generate comprehensive final report"""

        report = []
        report.append("\n" + "=" * 60)
        report.append("DEEP REASONING EVALUATION REPORT")
        report.append("=" * 60)

        # Overall Results
        report.append(f"\nOVERALL ASSESSMENT")
        report.append(f"Score: {self.comprehensive_results['overall_score']}/100")
        report.append(f"Grade: {self.comprehensive_results['overall_grade']}")

        # Domain Breakdown
        report.append(f"\nDOMAIN SCORES:")
        report.append("-" * 40)

        for domain, data in all_scores.items():
            score = data.get("score", 0)
            weight = self.domain_weights.get(domain, 0)
            weighted_contribution = score * weight

            report.append(f"\n{domain.upper()}")
            report.append(f"  Score: {score}/100")
            report.append(f"  Weight: {weight*100}%")
            report.append(f"  Contribution: {weighted_contribution:.1f} points")
            report.append(f"  {data.get('description', '')}")

        # Strengths and Weaknesses
        report.append(f"\nSTRENGTHS:")
        strengths = [d for d, data in all_scores.items() if data.get("score", 0) >= 80]
        for strength in strengths:
            report.append(f"  [OK] {strength}: Excellent performance")

        report.append(f"\nAREAS FOR IMPROVEMENT:")
        weaknesses = [d for d, data in all_scores.items() if data.get("score", 0) < 60]
        for weakness in weaknesses:
            report.append(f"  * {weakness}: Needs development")

        # Recommendations
        report.append(f"\nRECOMMENDATIONS:")
        recommendations = self._generate_recommendations(all_scores)
        for rec in recommendations:
            report.append(f"  -> {rec}")

        # Save results
        self.comprehensive_results["domain_scores"] = all_scores
        self.comprehensive_results["report"] = "\n".join(report)

        return self.comprehensive_results

    def _generate_recommendations(self, scores):
        """Generate personalized improvement recommendations"""
        recommendations = []

        # Check each domain
        for domain, data in scores.items():
            score = data.get("score", 0)

            if domain == "mathematical" and score < 70:
                recommendations.append("Practice step-by-step mathematical proofs and verification")
            elif domain == "logical" and score < 70:
                recommendations.append("Study formal logic and practice syllogistic reasoning")
            elif domain == "social_deduction" and score < 70:
                recommendations.append("Improve pattern recognition in social interactions")
            elif domain == "causal" and score < 70:
                recommendations.append("Practice identifying causal chains and counterfactuals")
            elif domain == "scientific" and score < 70:
                recommendations.append("Study experimental design and hypothesis testing")
            elif domain == "strategic" and score < 70:
                recommendations.append("Learn game theory fundamentals and Nash equilibrium")

        if not recommendations:
            recommendations.append("Continue practicing across all domains to maintain excellence")

        return recommendations

    def export_results(self, filename="unified_reasoning_evaluation.json"):
        """Export comprehensive evaluation results"""
        output_path = os.path.join(os.getcwd(), filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.comprehensive_results, f,
                     indent=2, ensure_ascii=False, default=str)

        print(f"\nResults exported to: {output_path}")
        return output_path

# Example usage
async def main():
    """Example of running unified evaluation"""

    evaluator = UnifiedReasoningEvaluator(test_subject_id=7)

    # Run comprehensive evaluation
    results = await evaluator.run_comprehensive_evaluation(
        include_werewolf=True,
        llm_interface=None  # Would pass actual LLM interface
    )

    # Print report
    print(results["report"])

    # Export results
    evaluator.export_results()

if __name__ == "__main__":
    # Run example
    asyncio.run(main())