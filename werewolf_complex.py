"""
高复杂度狼人杀游戏 - 12人固定阵容
固定阵容：预言家×1、女巫×1、猎人×1、守卫×1、狼王×1、普通狼×3、平民×4
MUT = 平民，其余11个为固定偏置克隆
"""

from dataclasses import dataclass
from typing import Dict, List, Callable, Optional, Any, Tuple
import random
import math
import time
import json
from collections import defaultdict

# ====== 难度与全局配置 ======
@dataclass
class Difficulty:
    name: str
    p_cc: float         # 对跳概率
    show_cause: bool    # 死因可见
    r_buss: float       # 狼队互踩率
    tie_rate: float     # 平票概率
    cand_k: int         # 候选宽度
    lam: float          # 惯性 λ
    rho: float          # 从众 ρ
    b_sheriff: float    # 上警偏置
    var_q: str          # 发言质量方差策略

PRESETS = {
    "easy":   Difficulty("easy",   0.15, True,  0.05, 0.05, 3, 0.40, 0.10, 0.10, "wide"),
    "medium": Difficulty("medium", 0.35, True,  0.15, 0.10, 4, 0.55, 0.20, 0.15, "medium"),
    "hard":   Difficulty("hard",   0.65, False, 0.40, 0.25, 5, 0.70, 0.30, 0.20, "clamped"),
    "insane": Difficulty("insane", 0.80, False, 0.50, 0.35, 5, 0.80, 0.35, 0.25, "tight"),
}

# ====== 角色定义 ======
ROLE_CONFIG = {
    "seer": {"name": "预言家", "team": "good"},
    "witch": {"name": "女巫", "team": "good"},
    "hunter": {"name": "猎人", "team": "good"},
    "guard": {"name": "守卫", "team": "good"},
    "wolf_king": {"name": "狼王", "team": "wolf"},
    "wolf": {"name": "狼人", "team": "wolf"},
    "villager": {"name": "平民", "team": "good"}
}

# 固定12人阵容
FIXED_ROLES = ["seer", "witch", "hunter", "guard", "wolf_king",
               "wolf", "wolf", "wolf", "villager", "villager", "villager", "villager"]

MUT_SEAT_DEFAULT = 8  # MUT默认座位（平民）

# ====== MUT 接口 ======
class MUTInterface:
    """MUT（被测模型）接口"""
    def __init__(self,
                 on_dawn: Callable[[Dict[str,Any]], Dict[str,Any]],
                 on_prevote: Callable[[Dict[str,Any]], Dict[str,Any]]):
        self.on_dawn = on_dawn
        self.on_prevote = on_prevote

# ====== 打分策略参数 ======
@dataclass
class Alphas:
    claim_conflict: float      # α1: 身份冲突
    quality: float             # α2: 发言质量
    vote_incons: float         # α3: 投票不一致
    high_bad: float            # α4: 高位低质
    sheriff_bias: float        # α5: 上警偏置
    accuse_strength: float     # α6: 指控强度

ALPHAS = {
    "D1": Alphas(0.9, 0.7, 0.2, 0.6, 0.5, 0.4),
    "D2": Alphas(1.2, 0.5, 0.6, 0.7, 0.4, 0.6)
}

# ====== 辅助函数 ======
def softmax(scores: Dict[int, float]) -> Dict[int, float]:
    """Softmax归一化"""
    if not scores:
        return {}
    mx = max(scores.values())
    ex = {k: math.exp(v - mx) for k, v in scores.items()}
    s = sum(ex.values()) or 1.0
    return {k: v / s for k, v in ex.items()}

def clamp_quality(q: float, mode: str) -> float:
    """根据难度模式压缩发言质量方差"""
    if mode == "clamped":
        return 0.5 + 0.2 * (q - 0.5)  # 拉齐话术
    if mode == "tight":
        return 0.5 + 0.1 * (q - 0.5)
    if mode == "medium":
        return 0.5 + 0.3 * (q - 0.5)
    return q  # wide

def clone_quality_score(speech_text: str, role: str) -> float:
    """评估发言质量（简化版）"""
    base_quality = random.uniform(0.35, 0.85)
    # 根据角色微调
    if role in ["seer", "witch", "hunter"]:
        base_quality += 0.05
    elif role in ["wolf", "wolf_king"]:
        base_quality += random.uniform(-0.05, 0.10)
    return min(max(base_quality, 0.0), 1.0)

# ====== 怀疑打分系统 ======
def calc_scores(day: int, candidates: List[int], features: Dict[int, Dict[str, float]],
                preset: Difficulty, alive: List[int]) -> Dict[int, float]:
    """计算怀疑分数"""
    stage = "D1" if day == 1 else "D2"
    a = ALPHAS[stage]
    scores = {}

    for i in candidates:
        if i not in alive:
            continue
        f = features.get(i, {})
        quality = clamp_quality(f.get("quality", 0.6), preset.var_q)

        score = (
            a.claim_conflict * f.get("claim_conflict", 0.0)
            - a.quality * (1.0 - quality)
            + a.vote_incons * f.get("vote_incons", 0.0)
            + a.high_bad * f.get("high_low_bad", 0.0)
            - a.sheriff_bias * f.get("is_sheriff", 0.0) * preset.b_sheriff
            + a.accuse_strength * f.get("accuse_strength", 0.0)
        )
        scores[i] = score

    return scores

# ====== 惯性+从众投票策略 ======
def clone_vote_choice(voter: int, last_vote: Optional[int], scores: Dict[int, float],
                      majority: Optional[int], preset: Difficulty) -> int:
    """克隆投票选择：惯性 λ=0.70 + 从众 ρ=0.30"""
    # 惯性：以概率 λ 保持上一票
    if last_vote is not None and last_vote in scores and random.random() < preset.lam:
        return last_vote

    # 基于分数的 softmax 分布
    dist = softmax(scores)

    # 从众：以概率 ρ 向多数靠拢
    if majority is not None and majority in dist:
        new_dist = {}
        for k, v in dist.items():
            if k == majority:
                new_dist[k] = (1 - preset.rho) * v + preset.rho
            else:
                new_dist[k] = (1 - preset.rho) * v
        s = sum(new_dist.values()) or 1.0
        dist = {k: v / s for k, v in new_dist.items()}

    # 采样
    r = random.random()
    acc = 0.0
    for k, v in sorted(dist.items()):
        acc += v
        if r <= acc:
            return k

    return max(dist, key=dist.get)

# ====== 观测构造 ======
def make_observation(pub_state: Dict[str, Any]) -> Dict[str, Any]:
    """构造给MUT的公开观测"""
    return {
        "day": pub_state["day"],
        "public": {
            "alive": pub_state["alive"][:],
            "dead": pub_state.get("dead", []),
            "sheriff": pub_state.get("sheriff"),
            "speeches": pub_state.get("speeches", [])[:],
            "claims": pub_state.get("claims", [])[:],
            "last_votes": pub_state.get("last_votes", [])[:],
            "dawn": pub_state.get("dawn", {}).copy(),
            "night_info": pub_state.get("night_info", {}).copy()
        }
    }

# ====== 游戏状态类 ======
class GameState:
    def __init__(self, seed: int, mut_seat: int, preset: Difficulty):
        random.seed(seed)
        self.seed = seed
        self.mut_seat = mut_seat
        self.preset = preset
        self.day = 0

        # 分配角色
        self.seats = list(range(1, 13))
        roles = FIXED_ROLES[:]
        random.shuffle(roles)

        # 确保 MUT 座位是平民
        villager_indices = [i for i, r in enumerate(roles) if r == "villager"]
        if roles[mut_seat - 1] != "villager":
            swap_idx = villager_indices[0]
            roles[mut_seat - 1], roles[swap_idx] = roles[swap_idx], roles[mut_seat - 1]

        self.roles = {i + 1: roles[i] for i in range(12)}

        # 玩家状态
        self.alive = self.seats[:]
        self.dead = []

        # 角色状态
        self.seer_checks = []  # (night, target, result)
        self.witch_save_used = False
        self.witch_poison_used = False
        self.guard_last_guard = None
        self.hunter_shot_used = False

        # 发言和投票记录
        self.speeches = []
        self.claims = []
        self.votes_history = []
        self.last_vote = {}

        # 警长
        self.sheriff = None

        # 双预言对跳
        self.fake_seer = None
        self.fake_seer_checks = []

        # 公开信息
        self.pub = {
            "day": 0,
            "alive": self.alive[:],
            "dead": [],
            "sheriff": None,
            "speeches": [],
            "claims": [],
            "last_votes": [],
            "dawn": {},
            "night_info": {}
        }

    def get_role(self, seat: int) -> str:
        return self.roles[seat]

    def is_alive(self, seat: int) -> bool:
        return seat in self.alive

    def kill(self, seat: int, cause: str = "unknown"):
        if seat in self.alive:
            self.alive.remove(seat)
            self.dead.append({"seat": seat, "cause": cause, "day": self.day})

    def get_team(self, seat: int) -> str:
        role = self.get_role(seat)
        return ROLE_CONFIG[role]["team"]

    def check_win_condition(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """检查胜利条件"""
        alive_wolves = [s for s in self.alive if self.get_team(s) == "wolf"]
        alive_goods = [s for s in self.alive if self.get_team(s) == "good"]

        if len(alive_wolves) == 0:
            reason = "所有狼人已被消灭"
            details = f"\\n\\n存活好人: {alive_goods}"
            return ("good", reason, details)

        if len(alive_wolves) >= len(alive_goods):
            reason = f"狼人数量({len(alive_wolves)})已经大于等于好人数量({len(alive_goods)})"
            details = f"\\n\\n存活狼人: {alive_wolves}\\n存活好人: {alive_goods}"
            return ("wolf", reason, details)

        return (None, None, None)

# ====== 主游戏循环 ======
def run_game(seed: int = 42,
             mut_seat: int = MUT_SEAT_DEFAULT,
             preset: Difficulty = PRESETS["hard"],
             mut: Optional[MUTInterface] = None,
             max_days: int = 5) -> List[Dict[str, Any]]:
    """运行游戏主循环"""

    game = GameState(seed, mut_seat, preset)
    log: List[Dict[str, Any]] = []

    # 记录初始状态
    log.append({
        "t": "GameStart",
        "payload": {
            "seed": seed,
            "mut_seat": mut_seat,
            "preset": preset.name,
            "roles": {str(k): v for k, v in game.roles.items()}
        }
    })

    # 主游戏循环
    for day in range(1, max_days + 1):
        game.day = day
        game.pub["day"] = day

        log.append({"t": "DayStart", "day": day})

        # ========== 夜晚阶段 (发生在黎明前) ==========
        night_log = {}
        dawn_deaths = []

        if day > 1:
            # 1. 狼人刀人
            alive_wolves = [s for s in game.alive if game.get_team(s) == "wolf"]
            alive_goods = [s for s in game.alive if game.get_team(s) == "good"]

            wolf_target = None
            if alive_wolves and alive_goods:
                # 狼队讨论选择目标（简化：随机选择好人）
                # 考虑互踩率 r_buss
                if random.random() < preset.r_buss and len(alive_wolves) > 1:
                    # 狼队互踩：选择狼人
                    wolf_target = random.choice(alive_wolves)
                else:
                    # 正常选择好人
                    wolf_target = random.choice(alive_goods)

                night_log["wolf_kill_target"] = wolf_target

            # 2. 守卫守护
            guard_seat = next((s for s in game.alive if game.get_role(s) == "guard"), None)
            guard_target = None
            if guard_seat:
                # 守卫选择守护对象（不能连续守同一人）
                guard_candidates = [s for s in game.alive if s != game.guard_last_guard]
                if guard_candidates:
                    guard_target = random.choice(guard_candidates)
                    game.guard_last_guard = guard_target
                    night_log["guard_protect"] = guard_target

            # 3. 女巫行动
            witch_seat = next((s for s in game.alive if game.get_role(s) == "witch"), None)
            witch_save = False
            witch_poison = None

            if witch_seat and wolf_target:
                # 女巫得知谁被刀
                # 决定是否救人（如果有解药且不是守卫守护的人）
                if not game.witch_save_used and wolf_target != guard_target:
                    if random.random() < 0.6:  # 60% 概率使用解药
                        witch_save = True
                        game.witch_save_used = True
                        night_log["witch_save"] = wolf_target

                # 决定是否毒人
                if not game.witch_poison_used and alive_wolves:
                    if random.random() < 0.3:  # 30% 概率使用毒药
                        poison_candidates = [s for s in game.alive if s != witch_seat]
                        if poison_candidates:
                            witch_poison = random.choice(poison_candidates)
                            game.witch_poison_used = True
                            night_log["witch_poison"] = witch_poison

            # 4. 预言家查验
            seer_seat = next((s for s in game.alive if game.get_role(s) == "seer"), None)
            if seer_seat:
                check_candidates = [s for s in game.alive if s != seer_seat]
                if check_candidates:
                    check_target = random.choice(check_candidates)
                    check_result = game.get_team(check_target)
                    game.seer_checks.append((day - 1, check_target, check_result))
                    night_log["seer_check"] = {"target": check_target, "result": check_result}

            # 5. 结算死亡
            # 狼刀的人如果被守卫守护或女巫救，则不死
            if wolf_target:
                if guard_target == wolf_target:
                    night_log["wolf_kill_blocked"] = "guard"
                elif witch_save:
                    night_log["wolf_kill_blocked"] = "witch"
                else:
                    wolf_target_role = game.get_role(wolf_target)
                    game.kill(wolf_target, "wolf_kill")
                    dawn_deaths.append(wolf_target)

                    # 猎人被杀，触发技能
                    if wolf_target_role == "hunter" and not game.hunter_shot_used:
                        game.hunter_shot_used = True
                        if game.alive:
                            hunter_target = random.choice(game.alive)
                            game.kill(hunter_target, "hunter_shoot")
                            dawn_deaths.append(hunter_target)
                            night_log["hunter_shoot"] = {"hunter": wolf_target, "target": hunter_target}

            # 女巫毒的人必死
            if witch_poison:
                witch_poison_role = game.get_role(witch_poison)
                game.kill(witch_poison, "witch_poison")
                dawn_deaths.append(witch_poison)

                # 猎人被毒，触发技能
                if witch_poison_role == "hunter" and not game.hunter_shot_used:
                    game.hunter_shot_used = True
                    if game.alive:
                        hunter_target = random.choice(game.alive)
                        game.kill(hunter_target, "hunter_shoot")
                        dawn_deaths.append(hunter_target)
                        night_log["hunter_shoot"] = {"hunter": witch_poison, "target": hunter_target}

        # 构造黎明公告
        deaths_info = []
        for s in dawn_deaths:
            # 确定死因
            cause = "unknown"
            if preset.show_cause:
                # 查找真实死因
                dead_entry = next((d for d in game.dead if d["seat"] == s and d["day"] == day), None)
                if dead_entry:
                    cause = dead_entry["cause"]

            deaths_info.append({"seat": s, "cause": cause})

        game.pub["dawn"] = {
            "dead": dawn_deaths,
            "deaths": deaths_info,
            "night_log": night_log if preset.show_cause else {}
        }

        log.append({
            "t": "DawnAnnounced",
            "day": day,
            "payload": game.pub["dawn"]
        })

        # MUT 钩子：Dawn
        if mut is not None:
            obs = make_observation(game.pub)
            out = mut.on_dawn(obs)
            log.append({
                "t": "BeliefSnapshot",
                "phase": "dawn",
                "day": day,
                "who": "MUT",
                "payload": out
            })

        # 检查胜利条件
        winner, reason, details = game.check_win_condition()
        if winner:
            log.append({
                "t": "GameEnd",
                "winner": winner,
                "reason": reason,
                "details": details
            })
            break

        # ========== 发言阶段 ==========
        game.pub["speeches"] = []
        seer_seat = next((s for s in game.alive if game.get_role(s) == "seer"), None)

        # 决定是否有狼对跳预言家
        if day == 1 and seer_seat and game.fake_seer is None:
            alive_wolves = [s for s in game.alive if game.get_team(s) == "wolf"]
            if alive_wolves and random.random() < preset.p_cc:
                # 狼对跳预言家
                game.fake_seer = random.choice(alive_wolves)
                log.append({
                    "t": "FakeSeerDecided",
                    "day": day,
                    "fake_seer": game.fake_seer
                })

        for idx, pid in enumerate(game.alive, start=1):
            role = game.get_role(pid)
            speech_text = f"Player {pid} 发言..."
            claim = None

            # 预言家发言：报查验结果
            if role == "seer" and pid == seer_seat:
                if day > 1 and game.seer_checks:
                    last_check = game.seer_checks[-1]
                    check_target, check_result = last_check[1], last_check[2]
                    team_str = "好人" if check_result == "good" else "狼人"
                    speech_text = f"Player {pid}: 我是预言家，昨晚查验了 Player {check_target}，结果是{team_str}"
                    claim = "seer"
                else:
                    speech_text = f"Player {pid}: 我是预言家"
                    claim = "seer"

            # 假预言家发言（狼对跳）
            elif pid == game.fake_seer:
                if day == 1:
                    speech_text = f"Player {pid}: 我是预言家"
                    claim = "seer"
                else:
                    # 伪造查验结果
                    alive_goods = [s for s in game.alive if game.get_team(s) == "good" and s != pid]
                    if alive_goods:
                        fake_target = random.choice(alive_goods)
                        # 随机报假结果
                        fake_result = "狼人" if random.random() < 0.7 else "好人"
                        speech_text = f"Player {pid}: 我是预言家，昨晚查验了 Player {fake_target}，结果是{fake_result}"
                        claim = "seer"
                        game.fake_seer_checks.append((day - 1, fake_target, fake_result))

            # 其他角色
            elif role in ["witch", "hunter", "guard"]:
                # 特殊角色可能暴露身份（简化：不主动暴露）
                pass

            q = clone_quality_score(speech_text, role)

            speech = {
                "who": pid,
                "order": idx,
                "text": speech_text,
                "quality": q,
                "role": role,  # 实际不公开
                "claim": claim  # 公开的身份声明
            }
            game.pub["speeches"].append(speech)
            game.speeches.append(speech)

            if claim:
                game.claims.append({"day": day, "who": pid, "claim": claim})
                game.pub["claims"].append({"day": day, "who": pid, "claim": claim})

            log.append({
                "t": "SpeechEnded",
                "day": day,
                "actor": pid,
                "payload": speech
            })

        # ========== 投票阶段 ==========
        # 确定候选人
        candidates = game.alive[:]
        random.shuffle(candidates)
        candidates = candidates[:min(len(candidates), preset.cand_k)]

        log.append({
            "t": "PreVoteSnapshot",
            "day": day,
            "payload": {
                "alive": game.alive[:],
                "candidates": candidates
            }
        })

        # MUT 钩子：PreVote
        if mut is not None:
            obs = make_observation(game.pub)
            obs["public"]["candidates"] = candidates
            out = mut.on_prevote(obs)
            log.append({
                "t": "BeliefSnapshot",
                "phase": "prevote",
                "day": day,
                "who": "MUT",
                "payload": out
            })

        # 构造特征
        features = {}

        # 检测身份冲突（多人声称同一角色）
        claim_conflicts = defaultdict(list)
        for claim in game.pub["claims"]:
            claim_conflicts[claim["claim"]].append(claim["who"])

        for i in candidates:
            speech = next((s for s in game.pub["speeches"] if s["who"] == i), None)

            # 计算身份冲突分数
            conflict_score = 0.0
            player_claims = [c["claim"] for c in game.pub["claims"] if c["who"] == i]
            for claim in player_claims:
                if len(claim_conflicts[claim]) > 1:
                    # 有多人声称同一角色，产生冲突
                    conflict_score = 1.0
                    break

            features[i] = {
                "claim_conflict": conflict_score,
                "vote_incons": 0.0,
                "high_low_bad": 1.0 if (speech and speech["order"] <= len(game.alive) // 3
                                       and speech["quality"] < 0.5) else 0.0,
                "is_sheriff": 1.0 if i == game.sheriff else 0.0,
                "accuse_strength": random.uniform(0, 0.6),
                "quality": speech["quality"] if speech else 0.6
            }

        # 计算分数
        scores = calc_scores(day, candidates, features, preset, game.alive)

        # 确定多数
        majority = None
        if game.last_vote:
            tally = defaultdict(int)
            for v in game.last_vote.values():
                if v in candidates:
                    tally[v] += 1
            if tally:
                majority = max(tally, key=tally.get)

        # 投票
        votes = []
        weights = {c: 0.0 for c in candidates}

        for voter in game.alive:
            if voter == mut_seat:
                # MUT 投票（Phase 1: 跟随克隆策略）
                choice = clone_vote_choice(voter, game.last_vote.get(voter),
                                          scores, majority, preset)
            else:
                choice = clone_vote_choice(voter, game.last_vote.get(voter),
                                          scores, majority, preset)

            vote_weight = 2.0 if voter == game.sheriff else 1.0
            votes.append({"voter": voter, "target": choice, "weight": vote_weight})
            weights[choice] += vote_weight
            game.last_vote[voter] = choice

        game.pub["last_votes"] = votes
        game.votes_history.append(votes)

        # 平票控制
        if random.random() < preset.tie_rate and len(candidates) >= 2:
            sorted_cands = sorted(weights.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_cands) >= 2:
                weights[sorted_cands[1][0]] = weights[sorted_cands[0][0]]

        executed = max(weights, key=weights.get)

        log.append({
            "t": "VoteTally",
            "day": day,
            "payload": {
                "votes": votes,
                "weights": weights,
                "executed": executed
            }
        })

        # 处决
        if executed in game.alive:
            executed_role = game.get_role(executed)
            game.kill(executed, "execution")
            log.append({
                "t": "PlayerExecuted",
                "day": day,
                "seat": executed,
                "role": executed_role
            })

            # 猎人带走（如果是猎人被出局且技能未用）
            if executed_role == "hunter" and not game.hunter_shot_used:
                game.hunter_shot_used = True
                # 猎人选择带走一个存活玩家
                if game.alive:
                    # 简化：随机选择一个存活玩家带走
                    hunter_target = random.choice(game.alive)
                    hunter_target_role = game.get_role(hunter_target)
                    game.kill(hunter_target, "hunter_shoot")

                    log.append({
                        "t": "HunterShoot",
                        "day": day,
                        "hunter": executed,
                        "target": hunter_target,
                        "target_role": hunter_target_role
                    })

            # 狼王带走（如果是狼王被出局）
            elif executed_role == "wolf_king":
                # 狼王可以选择带走一个存活玩家
                if game.alive:
                    # 简化：随机选择一个存活玩家带走
                    wolf_king_target = random.choice(game.alive)
                    wolf_king_target_role = game.get_role(wolf_king_target)
                    game.kill(wolf_king_target, "wolf_king_shoot")

                    log.append({
                        "t": "WolfKingShoot",
                        "day": day,
                        "wolf_king": executed,
                        "target": wolf_king_target,
                        "target_role": wolf_king_target_role
                    })

        # 检查胜利条件
        winner, reason, details = game.check_win_condition()
        if winner:
            log.append({
                "t": "GameEnd",
                "winner": winner,
                "reason": reason,
                "details": details
            })
            break

    # 记录真相
    wolves = [s for s in game.seats if game.get_team(s) == "wolf"]
    log.append({
        "t": "Truth",
        "payload": {
            "wolves": wolves,
            "roles": {str(k): v for k, v in game.roles.items()}
        }
    })

    return log

# ====== 示例 MUT 回调 ======
def dummy_mut_on_dawn(obs):
    """示例：黎明阶段的 MUT 回调"""
    alive = obs["public"]["alive"]
    p = {str(i): round(1.0 / len(alive) + random.uniform(-0.1, 0.1), 3)
         for i in alive}
    topk = sorted(alive)[:min(3, len(alive))]
    evidence = [f"Night_{obs['day']-1}_deaths"]
    return {"p_wolf": p, "topk": topk, "evidence": evidence}

def dummy_mut_on_prevote(obs):
    """示例：投票前的 MUT 回调"""
    alive = obs["public"]["alive"]
    candidates = obs["public"].get("candidates", alive)
    p = {str(i): round(1.0 / len(alive) + random.uniform(-0.1, 0.1), 3)
         for i in alive}
    topk = candidates[:min(3, len(candidates))]
    evidence = [f"Day_{obs['day']}_speeches"]
    return {"p_wolf": p, "topk": topk, "evidence": evidence}

# ====== 主程序 ======
if __name__ == "__main__":
    print("=" * 60)
    print("高复杂度狼人杀游戏 - Phase 1 实现")
    print("=" * 60)

    # 创建 MUT 接口
    mut = MUTInterface(dummy_mut_on_dawn, dummy_mut_on_prevote)

    # 运行游戏
    log = run_game(
        seed=123,
        mut_seat=MUT_SEAT_DEFAULT,
        preset=PRESETS["hard"],
        mut=mut,
        max_days=5
    )

    # 输出日志
    print("\\n游戏日志：")
    print("-" * 60)
    for entry in log:
        print(json.dumps(entry, ensure_ascii=False, indent=2))

    print("\\n" + "=" * 60)
    print(f"游戏结束，共 {len(log)} 条日志")
    print("=" * 60)
