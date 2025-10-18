"""
Deep Reasoning Ability Evaluator for Werewolf Game
狼人杀深度推理能力评估器

Evaluates the test subject's (Player 7) reasoning ability across multiple dimensions:
- Information Extraction (信息提取)
- Logical Deduction (逻辑推理)
- Pattern Recognition (模式识别)
- Vote Analysis (票型分析)
- Adaptive Behavior (适应性行为)
- Communication Quality (沟通质量)
"""

import json
from collections import defaultdict
import re

class ReasoningEvaluator:
    """
    Evaluates deep reasoning ability of the test subject player.
    """

    def __init__(self, test_subject_id=7):
        self.test_subject_id = test_subject_id
        self.evaluation_data = {
            "player_id": test_subject_id,
            "scores": {},
            "detailed_analysis": {},
            "timeline": [],
            "final_grade": None
        }

        # Evaluation dimensions
        self.dimensions = {
            "information_extraction": {
                "name": "信息提取能力",
                "weight": 0.15,
                "max_score": 100,
                "criteria": [
                    "识别真假预言家",
                    "记录金水/查杀信息",
                    "追踪夜晚死亡模式",
                    "识别药序线索"
                ]
            },
            "logical_deduction": {
                "name": "逻辑推理能力",
                "weight": 0.25,
                "max_score": 100,
                "criteria": [
                    "根据发言推断身份",
                    "分析站边合理性",
                    "推导夜晚行动逻辑",
                    "识别矛盾点"
                ]
            },
            "pattern_recognition": {
                "name": "模式识别能力",
                "weight": 0.20,
                "max_score": 100,
                "criteria": [
                    "识别狼队抱团模式",
                    "发现票型异常",
                    "识别发言套路",
                    "察觉节奏控制"
                ]
            },
            "vote_analysis": {
                "name": "票型分析能力",
                "weight": 0.20,
                "max_score": 100,
                "criteria": [
                    "分析警长票型",
                    "追踪站边变化",
                    "识别冲锋/倒钩",
                    "预测票型走向"
                ]
            },
            "adaptive_behavior": {
                "name": "适应性行为",
                "weight": 0.10,
                "max_score": 100,
                "criteria": [
                    "根据信息调整站边",
                    "修正错误判断",
                    "灵活应对局势",
                    "容错能力"
                ]
            },
            "communication_quality": {
                "name": "沟通质量",
                "weight": 0.10,
                "max_score": 100,
                "criteria": [
                    "发言逻辑清晰",
                    "关键信息传达",
                    "说服力",
                    "团队协作"
                ]
            }
        }

        # Ground truth from demo script
        self.ground_truth = {
            "real_seer": 2,
            "fake_seer": 10,
            "wolves": [1, 10, 11, 12],
            "golden_water": [3],
            "checked_wolf": [10],
            "night1_deaths": [4, 5],  # 4 poisoned, 5 killed
            "witch": 6,
            "guard": 8,
            "hunter": 9
        }

        # Event tracking
        self.events = []
        self.speeches = []
        self.votes = []
        self.side_changes = []

    def add_event(self, event_type, player_id, content, round_num, metadata=None):
        """Record an event for evaluation."""
        event = {
            "type": event_type,
            "player_id": player_id,
            "content": content,
            "round": round_num,
            "metadata": metadata or {},
            "timestamp": len(self.events)
        }
        self.events.append(event)

        if event_type == "speech" and player_id == self.test_subject_id:
            self.speeches.append(event)
        elif event_type == "vote" and player_id == self.test_subject_id:
            self.votes.append(event)

    def evaluate_information_extraction(self):
        """
        Evaluate how well the test subject extracts key information.
        评估信息提取能力
        """
        score = 0
        details = []

        # Check if identified real vs fake seer (25 points)
        identified_real_seer = False
        identified_fake_seer = False

        for speech in self.speeches:
            content = speech["content"].lower()

            # Check for seer identification
            if "2" in content and ("真" in content or "预言家" in content or "相信" in content):
                identified_real_seer = True
            if "10" in content and ("假" in content or "狼" in content or "跳" in content):
                identified_fake_seer = True

        if identified_real_seer:
            score += 15
            details.append("[OK] 正确识别真预言家 (Player 2) [+15分]")
        else:
            details.append("[FAIL] 未识别真预言家 [0分]")

        if identified_fake_seer:
            score += 10
            details.append("[OK] 正确识别假预言家 (Player 10) [+10分]")
        else:
            details.append("[FAIL] 未识别假预言家 [0分]")

        # Check if tracked golden water (15 points)
        tracked_golden_water = any("3" in s["content"] and "金水" in s["content"] for s in self.speeches)
        if tracked_golden_water:
            score += 15
            details.append("[OK] 追踪金水位 (Player 3) [+15分]")
        else:
            details.append("[FAIL] 未追踪金水位 [0分]")

        # Check if noticed night deaths (20 points)
        noticed_deaths = any(("4" in s["content"] or "5" in s["content"]) and "死" in s["content"]
                            for s in self.speeches)
        if noticed_deaths:
            score += 20
            details.append("[OK] 注意到夜晚死亡 (Player 4, 5) [+20分]")
        else:
            details.append("[FAIL] 未关注夜晚死亡 [0分]")

        # Check if deduced witch actions (30 points)
        deduced_witch = any("女巫" in s["content"] or "毒" in s["content"] or "药" in s["content"]
                           for s in self.speeches)
        if deduced_witch:
            score += 30
            details.append("[OK] 推理女巫药序 [+30分]")
        else:
            details.append("[FAIL] 未推理女巫药序 [0分]")

        return {
            "score": min(score, 100),
            "details": details,
            "summary": f"信息提取能力: {score}/100"
        }

    def evaluate_logical_deduction(self):
        """
        Evaluate logical reasoning and deduction ability.
        评估逻辑推理能力
        """
        score = 0
        details = []

        # Check for identity deduction from speeches (30 points)
        deduction_keywords = ["根据", "推理", "分析", "因为", "所以", "逻辑"]
        used_deduction = any(any(kw in s["content"] for kw in deduction_keywords)
                            for s in self.speeches)
        if used_deduction:
            score += 30
            details.append("[OK] 使用逻辑推理语言 [+30分]")
        else:
            details.append("[FAIL] 缺乏明确推理过程 [0分]")

        # Check for contradiction detection (30 points)
        detected_contradiction = any("矛盾" in s["content"] or "不对" in s["content"] or "冲突" in s["content"]
                                    for s in self.speeches)
        if detected_contradiction:
            score += 30
            details.append("[OK] 发现信息矛盾 [+30分]")
        else:
            details.append("[FAIL] 未发现信息矛盾 [0分]")

        # Check for chain reasoning (20 points)
        multi_step_reasoning = any(len(s["content"]) > 100 and s["content"].count("，") > 3
                                  for s in self.speeches)
        if multi_step_reasoning:
            score += 20
            details.append("[OK] 展现多步骤推理 [+20分]")
        else:
            details.append("[FAIL] 推理深度不足 [0分]")

        # Check for side analysis (20 points)
        analyzed_sides = any("站边" in s["content"] or "阵营" in s["content"]
                            for s in self.speeches)
        if analyzed_sides:
            score += 20
            details.append("[OK] 分析站边逻辑 [+20分]")
        else:
            details.append("[FAIL] 未分析站边 [0分]")

        return {
            "score": min(score, 100),
            "details": details,
            "summary": f"逻辑推理能力: {score}/100"
        }

    def evaluate_pattern_recognition(self):
        """
        Evaluate pattern recognition ability.
        评估模式识别能力
        """
        score = 0
        details = []

        # Check for wolf pack pattern recognition (40 points)
        recognized_wolf_pack = any("抱团" in s["content"] or "狼队" in s["content"] or
                                   ("1" in s["content"] and "10" in s["content"] and "11" in s["content"])
                                   for s in self.speeches)
        if recognized_wolf_pack:
            score += 40
            details.append("[OK] 识别狼队抱团模式 [+40分]")
        else:
            details.append("[FAIL] 未识别狼队抱团 [0分]")

        # Check for vote pattern analysis (30 points)
        analyzed_vote_pattern = any("票型" in s["content"] or "投票" in s["content"]
                                   for s in self.speeches)
        if analyzed_vote_pattern:
            score += 30
            details.append("[OK] 分析票型模式 [+30分]")
        else:
            details.append("[FAIL] 未分析票型 [0分]")

        # Check for speech pattern recognition (30 points)
        recognized_speech_pattern = any("套路" in s["content"] or "发言" in s["content"] or "风格" in s["content"]
                                       for s in self.speeches)
        if recognized_speech_pattern:
            score += 30
            details.append("[OK] 识别发言模式 [+30分]")
        else:
            details.append("[FAIL] 未识别发言模式 [0分]")

        return {
            "score": min(score, 100),
            "details": details,
            "summary": f"模式识别能力: {score}/100"
        }

    def evaluate_vote_analysis(self):
        """
        Evaluate vote analysis ability.
        评估票型分析能力
        """
        score = 0
        details = []

        if not self.votes:
            return {
                "score": 0,
                "details": ["[FAIL] 无投票记录"],
                "summary": "票型分析能力: 0/100 (无投票)"
            }

        # Check if voted correctly in sheriff election (40 points)
        sheriff_vote = next((v for v in self.votes if v["metadata"].get("vote_type") == "sheriff"), None)
        if sheriff_vote:
            voted_for = sheriff_vote["metadata"].get("target")
            if voted_for == 2:  # Voted for real seer
                score += 40
                details.append("[OK] 警长票投给真预言家 [+40分]")
            elif voted_for == 10:  # Voted for fake seer
                score += 0
                details.append("[FAIL] 警长票投给假预言家 [0分]")

        # Check if tracked vote changes (30 points)
        if len(self.votes) > 1:
            vote_targets = [v["metadata"].get("target") for v in self.votes]
            if len(set(vote_targets)) > 1:
                score += 30
                details.append("[OK] 根据信息调整投票 [+30分]")
            else:
                details.append("○ 投票未变化 [0分]")

        # Check if analyzed others' votes (30 points)
        analyzed_others_votes = any("票" in s["content"] or "投" in s["content"]
                                   for s in self.speeches)
        if analyzed_others_votes:
            score += 30
            details.append("[OK] 分析其他人投票 [+30分]")

        return {
            "score": min(score, 100),
            "details": details,
            "summary": f"票型分析能力: {score}/100"
        }

    def evaluate_adaptive_behavior(self):
        """
        Evaluate adaptive behavior and error correction.
        评估适应性和容错能力
        """
        score = 0
        details = []

        # Check for side changes (40 points)
        if len(self.side_changes) > 0:
            score += 40
            details.append(f"[OK] 调整站边 {len(self.side_changes)}次 [+40分]")
        else:
            details.append("○ 未调整站边 [0分]")

        # Check for self-correction (30 points)
        self_corrected = any("之前" in s["content"] or "重新" in s["content"] or "修正" in s["content"]
                            for s in self.speeches)
        if self_corrected:
            score += 30
            details.append("[OK] 展现自我修正能力 [+30分]")
        else:
            details.append("[FAIL] 未见自我修正 [0分]")

        # Check for flexibility (30 points)
        flexible = len(self.speeches) >= 3 and any(len(s["content"]) > 80 for s in self.speeches)
        if flexible:
            score += 30
            details.append("[OK] 展现灵活应对能力 [+30分]")
        else:
            details.append("[FAIL] 应对较僵化 [0分]")

        return {
            "score": min(score, 100),
            "details": details,
            "summary": f"适应性行为: {score}/100"
        }

    def evaluate_communication_quality(self):
        """
        Evaluate communication quality.
        评估沟通质量
        """
        score = 0
        details = []

        if not self.speeches:
            return {
                "score": 0,
                "details": ["[FAIL] 无发言记录"],
                "summary": "沟通质量: 0/100 (无发言)"
            }

        # Check for clear structure (25 points)
        avg_length = sum(len(s["content"]) for s in self.speeches) / len(self.speeches)
        if avg_length >= 80:
            score += 25
            details.append("[OK] 发言详细充分 [+25分]")
        elif avg_length >= 40:
            score += 15
            details.append("○ 发言基本完整 [+15分]")
        else:
            details.append("[FAIL] 发言过于简短 [0分]")

        # Check for key information delivery (25 points)
        delivered_key_info = any(("预言家" in s["content"] or "身份" in s["content"])
                                for s in self.speeches)
        if delivered_key_info:
            score += 25
            details.append("[OK] 传达关键信息 [+25分]")
        else:
            details.append("[FAIL] 缺少关键信息 [0分]")

        # Check for persuasiveness (25 points)
        persuasive = any("建议" in s["content"] or "应该" in s["content"] or "可以" in s["content"]
                        for s in self.speeches)
        if persuasive:
            score += 25
            details.append("[OK] 具有说服力 [+25分]")
        else:
            details.append("[FAIL] 缺乏说服力 [0分]")

        # Check for teamwork (25 points)
        cooperative = any("我们" in s["content"] or "一起" in s["content"] or "帮" in s["content"]
                         for s in self.speeches)
        if cooperative:
            score += 25
            details.append("[OK] 展现团队协作 [+25分]")
        else:
            details.append("[FAIL] 缺少团队意识 [0分]")

        return {
            "score": min(score, 100),
            "details": details,
            "summary": f"沟通质量: {score}/100"
        }

    def calculate_final_score(self):
        """
        Calculate weighted final score and grade.
        计算加权总分和等级
        """
        results = {}
        weighted_sum = 0

        # Evaluate each dimension
        results["information_extraction"] = self.evaluate_information_extraction()
        results["logical_deduction"] = self.evaluate_logical_deduction()
        results["pattern_recognition"] = self.evaluate_pattern_recognition()
        results["vote_analysis"] = self.evaluate_vote_analysis()
        results["adaptive_behavior"] = self.evaluate_adaptive_behavior()
        results["communication_quality"] = self.evaluate_communication_quality()

        # Calculate weighted score
        for dim_key, result in results.items():
            weight = self.dimensions[dim_key]["weight"]
            weighted_sum += result["score"] * weight

        self.evaluation_data["scores"] = results
        self.evaluation_data["weighted_score"] = round(weighted_sum, 2)

        # Determine grade
        if weighted_sum >= 90:
            grade = "S (卓越)"
        elif weighted_sum >= 80:
            grade = "A (优秀)"
        elif weighted_sum >= 70:
            grade = "B (良好)"
        elif weighted_sum >= 60:
            grade = "C (及格)"
        else:
            grade = "D (不及格)"

        self.evaluation_data["final_grade"] = grade

        return self.evaluation_data

    def generate_report(self):
        """
        Generate detailed evaluation report.
        生成详细评估报告
        """
        report = []
        report.append("=" * 80)
        report.append("深度推理能力评估报告 (Deep Reasoning Ability Evaluation)")
        report.append("=" * 80)
        report.append(f"\n测试主体: Player {self.test_subject_id}")
        report.append(f"总分: {self.evaluation_data['weighted_score']}/100")
        report.append(f"等级: {self.evaluation_data['final_grade']}\n")

        report.append("-" * 80)
        report.append("维度得分 (Dimension Scores):")
        report.append("-" * 80)

        for dim_key, dim_info in self.dimensions.items():
            result = self.evaluation_data["scores"].get(dim_key, {})
            score = result.get("score", 0)
            weight = dim_info["weight"]
            weighted = score * weight

            report.append(f"\n【{dim_info['name']}】 权重: {weight*100}%")
            report.append(f"得分: {score}/100 (加权: {weighted:.1f})")
            report.append(f"\n标准:")
            for criterion in dim_info["criteria"]:
                report.append(f"  - {criterion}")

            report.append(f"\n详细评分:")
            for detail in result.get("details", []):
                report.append(f"  {detail}")

        report.append("\n" + "=" * 80)
        report.append("评分标准说明:")
        report.append("=" * 80)
        report.append("S (90-100): 卓越 - 深度推理能力出众，能独立完成复杂推理")
        report.append("A (80-89):  优秀 - 推理能力强，大部分推理正确")
        report.append("B (70-79):  良好 - 推理能力较好，有一定推理深度")
        report.append("C (60-69):  及格 - 基本推理能力，但深度不足")
        report.append("D (0-59):   不及格 - 推理能力欠缺，需要改进")

        report.append("\n" + "=" * 80)
        report.append("统计数据:")
        report.append("=" * 80)
        report.append(f"发言次数: {len(self.speeches)}")
        report.append(f"投票次数: {len(self.votes)}")
        report.append(f"站边变化: {len(self.side_changes)}次")
        report.append(f"记录事件: {len(self.events)}个")

        return "\n".join(report)

    def export_json(self, filename="evaluation_result.json"):
        """Export evaluation results to JSON file."""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.evaluation_data, f, ensure_ascii=False, indent=2)
        return filename


# Example usage
if __name__ == "__main__":
    import sys
    import io

    # Set stdout encoding to utf-8 for Windows
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    # Create evaluator
    evaluator = ReasoningEvaluator(test_subject_id=7)

    # Simulate some events (in real game, these would be collected automatically)
    evaluator.add_event("speech", 7, "我认为2号是真预言家，因为他验了10号是狼。3号金水可信。", 1)
    evaluator.add_event("speech", 7, "根据票型分析，1、11、12可能在抱团，他们都投给了10号。", 1)
    evaluator.add_event("vote", 7, "投票给2号", 1, {"vote_type": "sheriff", "target": 2})
    evaluator.add_event("speech", 7, "昨晚4号和5号同时死亡，女巫可能毒了4号。我建议出10号。", 2)

    # Calculate scores
    result = evaluator.calculate_final_score()

    # Generate report
    report = evaluator.generate_report()
    print(report)

    # Export to JSON
    evaluator.export_json()
    print("\n结果已导出到 evaluation_result.json")
