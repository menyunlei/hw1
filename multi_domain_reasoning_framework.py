"""
Multi-Domain Deep Reasoning Evaluation Framework
多领域深度推理能力评估框架

This framework extends beyond single-task evaluation to comprehensively assess
LLM's deep reasoning capabilities across multiple domains.
"""

import json
import random
import math
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from abc import ABC, abstractmethod

class ReasoningDomain(Enum):
    """Different domains for reasoning evaluation"""
    SOCIAL_DEDUCTION = "social_deduction"  # Werewolf game
    MATHEMATICAL = "mathematical"  # Math problems
    LOGICAL = "logical"  # Logic puzzles
    CAUSAL = "causal"  # Cause-effect reasoning
    SPATIAL = "spatial"  # Spatial reasoning
    TEMPORAL = "temporal"  # Time-based reasoning
    COUNTERFACTUAL = "counterfactual"  # What-if scenarios
    ETHICAL = "ethical"  # Moral dilemmas
    SCIENTIFIC = "scientific"  # Scientific method
    STRATEGIC = "strategic"  # Game theory

@dataclass
class ReasoningTask:
    """Base class for reasoning tasks"""
    domain: ReasoningDomain
    difficulty: str  # "easy", "medium", "hard", "expert"
    description: str
    expected_reasoning_steps: List[str]
    evaluation_criteria: Dict[str, float]
    max_score: float = 100.0

class MathematicalReasoningTasks:
    """Mathematical reasoning evaluation tasks"""

    @staticmethod
    def generate_algebra_task(difficulty="medium"):
        """Generate algebraic reasoning problems"""
        if difficulty == "easy":
            return {
                "problem": "If 3x + 7 = 22, what is the value of x?",
                "solution_steps": [
                    "Subtract 7 from both sides: 3x = 15",
                    "Divide both sides by 3: x = 5"
                ],
                "answer": 5,
                "reasoning_type": "linear_equation"
            }
        elif difficulty == "medium":
            return {
                "problem": "A train travels from City A to City B at 60 km/h and returns at 40 km/h. If the total journey takes 5 hours, what is the distance between the cities?",
                "solution_steps": [
                    "Let distance = d km",
                    "Time to go = d/60 hours",
                    "Time to return = d/40 hours",
                    "Total time: d/60 + d/40 = 5",
                    "Find LCD: 2d/120 + 3d/120 = 5",
                    "5d/120 = 5",
                    "d = 120 km"
                ],
                "answer": 120,
                "reasoning_type": "rate_problem"
            }
        elif difficulty == "hard":
            return {
                "problem": "Prove that √2 is irrational",
                "solution_steps": [
                    "Assume √2 is rational = p/q in lowest terms",
                    "Then 2 = p²/q², so p² = 2q²",
                    "This means p² is even, therefore p is even",
                    "Let p = 2k, then 4k² = 2q², so q² = 2k²",
                    "This means q is also even",
                    "But p and q both even contradicts lowest terms",
                    "Therefore √2 is irrational"
                ],
                "answer": "proof_complete",
                "reasoning_type": "proof_by_contradiction"
            }
        else:  # expert
            return {
                "problem": "Find the number of ways to partition the integer 10 into distinct positive integers",
                "solution_steps": [
                    "Use generating function approach",
                    "Product from k=1 to 10 of (1 + x^k)",
                    "Find coefficient of x^10",
                    "Systematically enumerate: {10}, {1,9}, {2,8}, {3,7}, {4,6}, {1,2,7}, {1,3,6}, {1,4,5}, {2,3,5}, {1,2,3,4}",
                    "Count = 10 partitions"
                ],
                "answer": 10,
                "reasoning_type": "combinatorial"
            }

    @staticmethod
    def generate_probability_task(difficulty="medium"):
        """Generate probability reasoning problems"""
        if difficulty == "medium":
            return {
                "problem": "In a modified Monty Hall problem with 4 doors (1 car, 3 goats), you pick door 1. The host opens door 3 (goat). Should you switch to door 2 or 4? What's the probability of winning if you switch?",
                "solution_steps": [
                    "Initial probability of car behind door 1: 1/4",
                    "Initial probability of car behind doors 2,3,4: 3/4",
                    "After host opens door 3 (always a goat)",
                    "If car was behind door 1: P = 1/4 (unchanged)",
                    "If car behind door 2 or 4: P = 3/4 distributed",
                    "P(car behind 2 or 4 | door 3 opened) = 3/8 each",
                    "Switching gives 3/4 chance vs 1/4 staying"
                ],
                "answer": 0.75,
                "reasoning_type": "conditional_probability"
            }
        return None

class LogicalReasoningTasks:
    """Logical and deductive reasoning tasks"""

    @staticmethod
    def generate_syllogism_task():
        """Generate syllogistic reasoning problems"""
        return {
            "premises": [
                "All deep learning models are machine learning models",
                "All machine learning models require data",
                "Some deep learning models are transformers"
            ],
            "question": "What can we conclude about transformers?",
            "valid_conclusions": [
                "Some transformers require data",
                "Some transformers are machine learning models"
            ],
            "invalid_conclusions": [
                "All transformers are deep learning models",
                "No transformers require data"
            ],
            "reasoning_type": "syllogistic"
        }

    @staticmethod
    def generate_knights_knaves_puzzle():
        """Classic logic puzzle"""
        return {
            "problem": "On an island, knights always tell truth, knaves always lie. You meet A and B. A says 'B is a knave'. B says 'A and I are of opposite types'. What are A and B?",
            "solution_steps": [
                "Case 1: Assume A is a knight",
                "Then A tells truth, so B is a knave",
                "B lies, but 'opposite types' is true - contradiction",
                "Case 2: Assume A is a knave",
                "Then A lies, so B is a knight",
                "B tells truth, 'opposite types' is true - consistent",
                "Therefore: A is a knave, B is a knight"
            ],
            "answer": {"A": "knave", "B": "knight"},
            "reasoning_type": "truth_table"
        }

class CausalReasoningTasks:
    """Causal and counterfactual reasoning"""

    @staticmethod
    def generate_causal_chain():
        """Generate causal reasoning problems"""
        return {
            "scenario": "A new policy reduced speed limits. Accident rates decreased. Traffic flow improved. Commute times increased slightly.",
            "question": "What is the most likely causal chain?",
            "options": {
                "A": "Lower speeds → Fewer accidents → Better flow → Longer commutes",
                "B": "Lower speeds → Longer commutes + Fewer accidents → Better flow",
                "C": "Policy → All effects independently",
                "D": "Better flow → Fewer accidents → Longer commutes"
            },
            "answer": "B",
            "reasoning": "Direct effect on speed affects commute time and accidents; reduced accidents improve flow",
            "reasoning_type": "causal_chain"
        }

    @staticmethod
    def generate_counterfactual():
        """Generate counterfactual reasoning tasks"""
        return {
            "scenario": "A company launched product X and sales increased 20%. They also ran a marketing campaign.",
            "counterfactual": "What would have happened without the marketing campaign?",
            "considerations": [
                "Baseline growth trend",
                "Product quality impact",
                "Market conditions",
                "Competitor actions",
                "Campaign reach and effectiveness"
            ],
            "reasoning_type": "counterfactual_analysis"
        }

class ScientificReasoningTasks:
    """Scientific method and hypothesis testing"""

    @staticmethod
    def generate_hypothesis_testing():
        """Generate scientific reasoning problems"""
        return {
            "observation": "Plants in room A (with music) grew 15% taller than room B (silence)",
            "task": "Design a rigorous experiment to test if music affects plant growth",
            "required_elements": [
                "Control variables (light, water, temperature, soil)",
                "Sample size calculation",
                "Randomization method",
                "Blind measurement protocol",
                "Statistical test selection",
                "Alternative explanations"
            ],
            "reasoning_type": "experimental_design"
        }

class StrategicReasoningTasks:
    """Game theory and strategic reasoning"""

    @staticmethod
    def generate_game_theory_task():
        """Generate strategic reasoning problems"""
        return {
            "problem": "Two companies can choose High or Low prices. Payoff matrix (A,B): HH:(5,5), HL:(2,8), LH:(8,2), LL:(3,3). What is the Nash equilibrium?",
            "solution_steps": [
                "If B chooses H, A prefers L (8>5)",
                "If B chooses L, A prefers L (3>2)",
                "If A chooses H, B prefers L (8>5)",
                "If A chooses L, B prefers L (3>2)",
                "Both choosing L is Nash equilibrium",
                "Note: HH Pareto dominates LL (prisoner's dilemma structure)"
            ],
            "answer": "LL",
            "reasoning_type": "nash_equilibrium"
        }

class MultiDomainEvaluator:
    """Main evaluator that combines all domains"""

    def __init__(self):
        self.domains = {
            ReasoningDomain.MATHEMATICAL: MathematicalReasoningTasks(),
            ReasoningDomain.LOGICAL: LogicalReasoningTasks(),
            ReasoningDomain.CAUSAL: CausalReasoningTasks(),
            ReasoningDomain.SCIENTIFIC: ScientificReasoningTasks(),
            ReasoningDomain.STRATEGIC: StrategicReasoningTasks(),
            ReasoningDomain.SOCIAL_DEDUCTION: None  # Use existing Werewolf evaluator
        }

        self.weights = {
            ReasoningDomain.MATHEMATICAL: 0.20,
            ReasoningDomain.LOGICAL: 0.15,
            ReasoningDomain.CAUSAL: 0.15,
            ReasoningDomain.SCIENTIFIC: 0.10,
            ReasoningDomain.STRATEGIC: 0.10,
            ReasoningDomain.SOCIAL_DEDUCTION: 0.15,
            ReasoningDomain.SPATIAL: 0.05,
            ReasoningDomain.TEMPORAL: 0.05,
            ReasoningDomain.COUNTERFACTUAL: 0.05
        }

        self.evaluation_results = {}

    def evaluate_mathematical_reasoning(self, llm_response: str, task: dict) -> dict:
        """Evaluate mathematical reasoning"""
        score = 0
        max_score = 100
        feedback = []

        # Check for problem understanding (20 points)
        if "let" in llm_response.lower() or "assume" in llm_response.lower():
            score += 20
            feedback.append("[OK] Problem formulation identified")
        else:
            feedback.append("[FAIL] No clear problem formulation")

        # Check for step-by-step reasoning (30 points)
        steps_found = 0
        for step in task.get("solution_steps", []):
            key_words = step.split()[:3]  # Check first few words
            if any(word.lower() in llm_response.lower() for word in key_words):
                steps_found += 1

        step_score = (steps_found / len(task.get("solution_steps", [1]))) * 30
        score += step_score
        feedback.append(f"[OK] Reasoning steps: {steps_found}/{len(task.get('solution_steps', []))}")

        # Check for correct answer (30 points)
        answer = task.get("answer")
        if str(answer) in llm_response:
            score += 30
            feedback.append("[OK] Correct answer reached")
        else:
            feedback.append("[FAIL] Incorrect or missing answer")

        # Check for verification (20 points)
        if "check" in llm_response.lower() or "verify" in llm_response.lower():
            score += 20
            feedback.append("[OK] Answer verification attempted")
        else:
            feedback.append("[FAIL] No answer verification")

        return {
            "score": min(score, max_score),
            "feedback": feedback,
            "domain": "mathematical",
            "task_type": task.get("reasoning_type", "unknown")
        }

    def evaluate_logical_reasoning(self, llm_response: str, task: dict) -> dict:
        """Evaluate logical reasoning"""
        score = 0
        max_score = 100
        feedback = []

        # Check for systematic case analysis
        if "case" in llm_response.lower() or "assume" in llm_response.lower():
            score += 25
            feedback.append("[OK] Systematic case analysis")
        else:
            feedback.append("[FAIL] No systematic approach")

        # Check for contradiction detection
        if "contradiction" in llm_response.lower() or "inconsistent" in llm_response.lower():
            score += 25
            feedback.append("[OK] Contradiction reasoning used")

        # Check for valid conclusions
        if task.get("valid_conclusions"):
            for conclusion in task["valid_conclusions"]:
                if conclusion.lower() in llm_response.lower():
                    score += 25
                    feedback.append(f"[OK] Valid conclusion: {conclusion[:30]}...")
                    break

        # Check for avoiding invalid conclusions
        invalid_found = False
        for invalid in task.get("invalid_conclusions", []):
            if invalid.lower() in llm_response.lower():
                invalid_found = True
                feedback.append(f"[FAIL] Invalid conclusion stated: {invalid[:30]}...")
                break

        if not invalid_found and task.get("invalid_conclusions"):
            score += 25
            feedback.append("[OK] Avoided invalid conclusions")

        return {
            "score": min(score, max_score),
            "feedback": feedback,
            "domain": "logical",
            "task_type": task.get("reasoning_type", "unknown")
        }

    def generate_comprehensive_report(self, all_scores: dict) -> dict:
        """Generate comprehensive evaluation report"""

        # Calculate weighted overall score
        total_weighted = 0
        for domain, result in all_scores.items():
            if domain in self.weights:
                weight = self.weights[domain]
                total_weighted += result.get("score", 0) * weight

        # Determine grade
        if total_weighted >= 90:
            grade = "S - Exceptional Deep Reasoning"
        elif total_weighted >= 80:
            grade = "A - Strong Deep Reasoning"
        elif total_weighted >= 70:
            grade = "B - Good Deep Reasoning"
        elif total_weighted >= 60:
            grade = "C - Adequate Deep Reasoning"
        else:
            grade = "D - Insufficient Deep Reasoning"

        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []

        for domain, result in all_scores.items():
            if result.get("score", 0) >= 80:
                strengths.append(domain)
            elif result.get("score", 0) < 60:
                weaknesses.append(domain)

        return {
            "overall_score": round(total_weighted, 2),
            "grade": grade,
            "domain_scores": all_scores,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": self.generate_recommendations(weaknesses),
            "detailed_feedback": self.generate_detailed_feedback(all_scores)
        }

    def generate_recommendations(self, weaknesses: list) -> list:
        """Generate improvement recommendations"""
        recommendations = []

        if ReasoningDomain.MATHEMATICAL in weaknesses:
            recommendations.append("Practice step-by-step mathematical proofs and verification")
        if ReasoningDomain.LOGICAL in weaknesses:
            recommendations.append("Focus on systematic case analysis and contradiction detection")
        if ReasoningDomain.CAUSAL in weaknesses:
            recommendations.append("Improve causal chain identification and counterfactual thinking")
        if ReasoningDomain.SCIENTIFIC in weaknesses:
            recommendations.append("Enhance experimental design and hypothesis testing skills")
        if ReasoningDomain.STRATEGIC in weaknesses:
            recommendations.append("Study game theory and Nash equilibrium concepts")

        return recommendations

    def generate_detailed_feedback(self, all_scores: dict) -> dict:
        """Generate detailed feedback for each domain"""
        feedback = {}

        for domain, result in all_scores.items():
            feedback[domain] = {
                "score": result.get("score", 0),
                "strengths": [f for f in result.get("feedback", []) if "[OK]" in f],
                "improvements": [f for f in result.get("feedback", []) if "[FAIL]" in f],
                "task_types": result.get("task_type", "unknown")
            }

        return feedback

class IntegratedEvaluationPipeline:
    """Pipeline to run all evaluations"""

    def __init__(self):
        self.multi_domain = MultiDomainEvaluator()
        self.results = {}

    async def run_full_evaluation(self, llm_interface, include_werewolf=True):
        """Run complete evaluation across all domains"""

        all_results = {}

        # 1. Mathematical Reasoning
        math_tasks = [
            MathematicalReasoningTasks.generate_algebra_task("easy"),
            MathematicalReasoningTasks.generate_algebra_task("medium"),
            MathematicalReasoningTasks.generate_algebra_task("hard"),
            MathematicalReasoningTasks.generate_probability_task("medium")
        ]

        math_scores = []
        for task in math_tasks:
            if task:
                response = await llm_interface.generate(task["problem"])
                score = self.multi_domain.evaluate_mathematical_reasoning(response, task)
                math_scores.append(score["score"])

        all_results[ReasoningDomain.MATHEMATICAL] = {
            "score": sum(math_scores) / len(math_scores) if math_scores else 0,
            "feedback": f"Evaluated {len(math_scores)} mathematical tasks"
        }

        # 2. Logical Reasoning
        logic_tasks = [
            LogicalReasoningTasks.generate_syllogism_task(),
            LogicalReasoningTasks.generate_knights_knaves_puzzle()
        ]

        logic_scores = []
        for task in logic_tasks:
            response = await llm_interface.generate(str(task))
            score = self.multi_domain.evaluate_logical_reasoning(response, task)
            logic_scores.append(score["score"])

        all_results[ReasoningDomain.LOGICAL] = {
            "score": sum(logic_scores) / len(logic_scores) if logic_scores else 0,
            "feedback": f"Evaluated {len(logic_scores)} logical tasks"
        }

        # 3. Causal Reasoning
        causal_task = CausalReasoningTasks.generate_causal_chain()
        response = await llm_interface.generate(f"{causal_task['scenario']}\n{causal_task['question']}")
        # Simplified evaluation
        causal_score = 70 if causal_task["answer"] in response else 40
        all_results[ReasoningDomain.CAUSAL] = {
            "score": causal_score,
            "feedback": "Causal chain analysis evaluated"
        }

        # 4. Scientific Reasoning
        sci_task = ScientificReasoningTasks.generate_hypothesis_testing()
        response = await llm_interface.generate(f"{sci_task['observation']}\n{sci_task['task']}")
        # Check for required elements
        sci_score = sum(10 for element in sci_task["required_elements"]
                       if element.lower()[:10] in response.lower())
        all_results[ReasoningDomain.SCIENTIFIC] = {
            "score": min(sci_score, 100),
            "feedback": "Experimental design evaluated"
        }

        # 5. Strategic Reasoning
        game_task = StrategicReasoningTasks.generate_game_theory_task()
        response = await llm_interface.generate(game_task["problem"])
        strategic_score = 80 if game_task["answer"] in response else 40
        all_results[ReasoningDomain.STRATEGIC] = {
            "score": strategic_score,
            "feedback": "Game theory reasoning evaluated"
        }

        # 6. Social Deduction (Werewolf) - if included
        if include_werewolf:
            # This would connect to the existing Werewolf evaluation
            all_results[ReasoningDomain.SOCIAL_DEDUCTION] = {
                "score": 75,  # Placeholder - would come from actual game
                "feedback": "Social deduction from Werewolf game"
            }

        # Generate comprehensive report
        final_report = self.multi_domain.generate_comprehensive_report(all_results)

        return final_report

    def export_results(self, results: dict, filename: str = "comprehensive_reasoning_evaluation.json"):
        """Export evaluation results"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        return filename

# Example usage and testing
if __name__ == "__main__":
    print("Multi-Domain Deep Reasoning Evaluation Framework")
    print("=" * 60)

    # Example: Generate sample tasks
    print("\n1. Mathematical Reasoning Task:")
    math_task = MathematicalReasoningTasks.generate_algebra_task("medium")
    print(f"Problem: {math_task['problem']}")
    print(f"Type: {math_task['reasoning_type']}")

    print("\n2. Logical Reasoning Task:")
    logic_task = LogicalReasoningTasks.generate_knights_knaves_puzzle()
    print(f"Problem: {logic_task['problem']}")

    print("\n3. Causal Reasoning Task:")
    causal_task = CausalReasoningTasks.generate_causal_chain()
    print(f"Scenario: {causal_task['scenario']}")

    print("\n4. Scientific Reasoning Task:")
    sci_task = ScientificReasoningTasks.generate_hypothesis_testing()
    print(f"Observation: {sci_task['observation']}")

    print("\n5. Strategic Reasoning Task:")
    game_task = StrategicReasoningTasks.generate_game_theory_task()
    print(f"Problem: {game_task['problem'][:100]}...")

    print("\n" + "=" * 60)
    print("This framework provides comprehensive evaluation across:")
    print("- Mathematical reasoning (algebra, probability, proofs)")
    print("- Logical deduction (syllogisms, puzzles)")
    print("- Causal reasoning (chains, counterfactuals)")
    print("- Scientific method (hypothesis, experiments)")
    print("- Strategic thinking (game theory)")
    print("- Social deduction (Werewolf game)")
    print("\nTotal: 6+ reasoning domains for robust evaluation")