"""
狼人杀 - ULS/ULS++ 短头部标准版
12人局：预言家×1、女巫×1、猎人×1、守卫×1、狼王×1、普通狼×3、平民×4

完整流程：
1. 上警阶段（Election）
2. 竞选投票阶段
3. 警长定序
4. 白天发言阶段（ULS++ 头部）
5. 投票/平票复投
6. 处决/遗言/开枪
7. 夜晚行动
8. 黎明公布
"""

import random
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict

# ====== 角色配置 ======
ROLE_CONFIG = {
    "S": {"name": "预言家", "team": "good", "unique": True},
    "W": {"name": "女巫", "team": "good", "unique": True},
    "H": {"name": "猎人", "team": "good", "unique": True},
    "G": {"name": "守卫", "team": "good", "unique": True},
    "WK": {"name": "狼王", "team": "wolf", "unique": True},
    "WF": {"name": "狼人", "team": "wolf", "unique": False},
    "V": {"name": "平民", "team": "good", "unique": False}
}

FIXED_ROLES = ["S", "W", "H", "G", "WK", "WF", "WF", "WF", "V", "V", "V", "V"]

# ====== ULS++ 头部解析器 ======
class ULSParser:
    """解析 ULS/ULS++ 格式的头部"""

    @staticmethod
    def parse_speech(text: str) -> Dict[str, Any]:
        """
        解析白天发言头部
        格式: PV:3|ALT:5|TIE:3,5|ST:A|SUS:3@4.4,5@3.6|EV:+12,-27|CL:S+9|DM:2:QV|CF:4.2|RK:3|K:120
        """
        result = {
            "pv": None,           # 主投票目标
            "alt": None,          # 备选目标
            "tie": [],            # 平票选项
            "stance": None,       # 立场 A(激进)/M(中立)/D(防御)
            "sus": {},            # 怀疑度 {player_id: score}
            "evidence": [],       # 证据 [+12, -27]
            "claim": None,        # 身份声明
            "claim_strength": 0,  # 声明强度
            "dm": None,           # 定向信息
            "confidence": 0.0,    # 自信度
            "rank": None,         # 自我排位
            "tokens": 0           # token预算
        }

        # 提取头部（第一行以 | 分隔的部分）
        lines = text.strip().split('\n')
        header = lines[0] if lines else ""

        parts = header.split('|')
        for part in parts:
            part = part.strip()
            if not part:
                continue

            # PV:3
            if part.startswith("PV:"):
                result["pv"] = int(part.split(':')[1])

            # ALT:5
            elif part.startswith("ALT:"):
                result["alt"] = int(part.split(':')[1])

            # TIE:3,5
            elif part.startswith("TIE:"):
                tie_str = part.split(':')[1]
                result["tie"] = [int(x) for x in tie_str.split(',') if x]

            # ST:A/M/D
            elif part.startswith("ST:"):
                result["stance"] = part.split(':')[1]

            # SUS:3@4.4,5@3.6
            elif part.startswith("SUS:"):
                sus_str = part.split(':')[1]
                for item in sus_str.split(','):
                    if '@' in item:
                        pid, score = item.split('@')
                        result["sus"][int(pid)] = float(score)

            # EV:+12,-27
            elif part.startswith("EV:"):
                ev_str = part.split(':')[1]
                result["evidence"] = [int(x) for x in ev_str.split(',') if x]

            # CL:S+9 (预言家+9强度)
            elif part.startswith("CL:"):
                claim_str = part.split(':')[1]
                # 提取角色码和强度
                match = re.match(r'([A-Z]+)([+\-]?\d+)', claim_str)
                if match:
                    result["claim"] = match.group(1)
                    result["claim_strength"] = int(match.group(2))

            # DM:2:QV (向2号发定向信息QV)
            elif part.startswith("DM:"):
                dm_parts = part.split(':')
                if len(dm_parts) >= 3:
                    result["dm"] = {"target": int(dm_parts[1]), "msg": dm_parts[2]}

            # CF:4.2
            elif part.startswith("CF:"):
                result["confidence"] = float(part.split(':')[1])

            # RK:3
            elif part.startswith("RK:"):
                result["rank"] = int(part.split(':')[1])

            # K:120
            elif part.startswith("K:"):
                result["tokens"] = int(part.split(':')[1])

        return result

    @staticmethod
    def parse_election(text: str) -> Optional[str]:
        """解析上警动作: ELC:JOIN 或 ELC:PASS"""
        if "ELC:JOIN" in text:
            return "JOIN"
        elif "ELC:PASS" in text:
            return "PASS"
        return None

    @staticmethod
    def parse_vote(text: str) -> Optional[int]:
        """解析投票: VT:3 或 RVT:3"""
        match = re.search(r'(?:VT|RVT):(\d+)', text)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def parse_night_action(text: str, role: str) -> Optional[Dict[str, Any]]:
        """
        解析夜晚动作
        狼: N:3 (刀3号)
        守卫: G:3 (守3号)
        预言家: S:3 (查3号)
        女巫: W+:3 (救3号) 或 W-:3 (毒3号)
        """
        result = {}

        # 狼刀
        if role in ["WF", "WK"]:
            match = re.search(r'N:(\d+)', text)
            if match:
                result["action"] = "kill"
                result["target"] = int(match.group(1))

        # 守卫
        elif role == "G":
            match = re.search(r'G:(\d+)', text)
            if match:
                result["action"] = "guard"
                result["target"] = int(match.group(1))

        # 预言家
        elif role == "S":
            match = re.search(r'S:(\d+)', text)
            if match:
                result["action"] = "check"
                result["target"] = int(match.group(1))

        # 女巫
        elif role == "W":
            save_match = re.search(r'W\+:(\d+)', text)
            poison_match = re.search(r'W-:(\d+)', text)
            if save_match:
                result["action"] = "save"
                result["target"] = int(save_match.group(1))
            elif poison_match:
                result["action"] = "poison"
                result["target"] = int(poison_match.group(1))

        return result if result else None

    @staticmethod
    def parse_shoot(text: str) -> Optional[int]:
        """解析开枪: H:SHOT:3 或 WK:SHOT:3"""
        match = re.search(r'(?:H|WK):SHOT:(\d+)', text)
        if match:
            return int(match.group(1))
        return None


# ====== 游戏状态 ======
@dataclass
class GameState:
    """游戏状态"""
    day: int = 0
    phase: str = "init"  # init, election, sheriff_vote, order, speech, vote, revote, last_words, night, dawn

    # 玩家状态
    players: Dict[int, Dict[str, Any]] = None
    alive: List[int] = None
    dead: List[int] = None

    # 警长
    sheriff: Optional[int] = None
    sheriff_candidates: List[int] = None
    speech_order: List[int] = None

    # 投票
    votes: Dict[int, int] = None
    vote_weights: Dict[int, float] = None

    # 夜晚行动
    night_actions: Dict[int, Dict[str, Any]] = None

    # 女巫药
    witch_save_used: bool = False
    witch_poison_used: bool = False

    # 守卫
    guard_last_target: Optional[int] = None

    # 预言家查验
    seer_checks: List[Tuple[int, str]] = None  # [(target, result)]

    # 对跳检测
    claim_conflicts: Dict[str, List[int]] = None

    # 日志
    log: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.players is None:
            self.players = {}
        if self.alive is None:
            self.alive = []
        if self.dead is None:
            self.dead = []
        if self.sheriff_candidates is None:
            self.sheriff_candidates = []
        if self.speech_order is None:
            self.speech_order = []
        if self.votes is None:
            self.votes = {}
        if self.vote_weights is None:
            self.vote_weights = {}
        if self.night_actions is None:
            self.night_actions = {}
        if self.seer_checks is None:
            self.seer_checks = []
        if self.claim_conflicts is None:
            self.claim_conflicts = defaultdict(list)
        if self.log is None:
            self.log = []


# ====== 游戏引擎 ======
class WerewolfGame:
    """狼人杀游戏引擎"""

    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.state = GameState()
        self.parser = ULSParser()

        # 初始化玩家
        roles = FIXED_ROLES[:]
        random.shuffle(roles)

        for i in range(1, 13):
            self.state.players[i] = {
                "id": i,
                "role": roles[i-1],
                "alive": True,
                "is_sheriff": False,
                "speeches": [],
                "votes": []
            }
            self.state.alive.append(i)

    def log_event(self, event_type: str, **data):
        """记录事件"""
        self.state.log.append({
            "type": event_type,
            "day": self.state.day,
            "phase": self.state.phase,
            **data
        })

    def get_role(self, player_id: int) -> str:
        """获取角色"""
        return self.state.players[player_id]["role"]

    def get_team(self, player_id: int) -> str:
        """获取阵营"""
        role = self.get_role(player_id)
        return ROLE_CONFIG[role]["team"]

    def is_alive(self, player_id: int) -> bool:
        """是否存活"""
        return player_id in self.state.alive

    def kill_player(self, player_id: int, cause: str):
        """杀死玩家"""
        if player_id in self.state.alive:
            self.state.alive.remove(player_id)
            self.state.dead.append(player_id)
            self.state.players[player_id]["alive"] = False
            self.log_event("player_died", player=player_id, cause=cause)

    def check_win_condition(self) -> Optional[Tuple[str, str]]:
        """检查胜利条件"""
        wolves = [p for p in self.state.alive if self.get_team(p) == "wolf"]
        goods = [p for p in self.state.alive if self.get_team(p) == "good"]

        if len(wolves) == 0:
            return ("good", f"所有狼人被消灭。存活好人: {goods}")

        if len(wolves) >= len(goods):
            return ("wolf", f"狼人数({len(wolves)}) >= 好人数({len(goods)})。存活狼人: {wolves}")

        return None

    # ====== 阶段1: 上警 ======
    def phase_election(self, responses: Dict[int, str]):
        """上警阶段"""
        self.state.phase = "election"
        self.state.sheriff_candidates = []

        for player_id in self.state.alive:
            response = responses.get(player_id, "")
            action = self.parser.parse_election(response)

            if action == "JOIN":
                self.state.sheriff_candidates.append(player_id)
                self.log_event("election_join", player=player_id)

        print(f"\n[上警] 参选警长: {self.state.sheriff_candidates}")
        return self.state.sheriff_candidates

    # ====== 阶段2: 竞选投票 ======
    def phase_sheriff_vote(self, responses: Dict[int, str]):
        """竞选投票阶段"""
        self.state.phase = "sheriff_vote"
        votes = {}

        for player_id in self.state.alive:
            response = responses.get(player_id, "")
            # 解析 ELCV:x
            match = re.search(r'ELCV:(\d+)', response)
            if match:
                target = int(match.group(1))
                if target in self.state.sheriff_candidates:
                    votes[player_id] = target

        # 统计票数
        tally = defaultdict(int)
        for target in votes.values():
            tally[target] += 1

        if tally:
            # 选出得票最多的
            max_votes = max(tally.values())
            winners = [p for p, v in tally.items() if v == max_votes]

            if len(winners) == 1:
                self.state.sheriff = winners[0]
                self.state.players[self.state.sheriff]["is_sheriff"] = True
                self.log_event("sheriff_elected", sheriff=self.state.sheriff, votes=dict(tally))
                print(f"\n[竞选] Player {self.state.sheriff} 当选警长 (票数: {tally})")
                return self.state.sheriff
            else:
                # 平票，随机选一个
                self.state.sheriff = random.choice(winners)
                self.state.players[self.state.sheriff]["is_sheriff"] = True
                self.log_event("sheriff_elected_tie", sheriff=self.state.sheriff, tied=winners)
                print(f"\n[竞选] 平票 {winners}，随机选出 Player {self.state.sheriff}")
                return self.state.sheriff

        return None

    # ====== 阶段3: 警长定序 ======
    def set_speech_order(self, order: List[int]):
        """警长定序"""
        self.state.phase = "order"
        self.state.speech_order = order
        self.log_event("speech_order_set", order=order)
        print(f"\n[定序] 警长指定发言顺序: {order}")

    # ====== 阶段4: 白天发言 ======
    def phase_speech(self, responses: Dict[int, str]):
        """白天发言阶段"""
        self.state.phase = "speech"
        parsed_speeches = {}
        self.state.claim_conflicts.clear()

        order = self.state.speech_order if self.state.speech_order else self.state.alive

        for player_id in order:
            if player_id not in self.state.alive:
                continue

            response = responses.get(player_id, "")
            parsed = self.parser.parse_speech(response)
            parsed_speeches[player_id] = parsed

            # 记录身份声明
            if parsed["claim"]:
                claim_role = parsed["claim"]
                self.state.claim_conflicts[claim_role].append(player_id)

            self.state.players[player_id]["speeches"].append(parsed)
            self.log_event("speech", player=player_id, content=parsed)

        # 检测对跳
        conflicts = {}
        for role, claimants in self.state.claim_conflicts.items():
            if len(claimants) > 1 and ROLE_CONFIG.get(role, {}).get("unique", False):
                conflicts[role] = claimants
                print(f"\n[对跳] {ROLE_CONFIG[role]['name']} 对跳: {claimants}")

        return parsed_speeches, conflicts

    # ====== 阶段5: 投票 ======
    def phase_vote(self, responses: Dict[int, str]) -> Tuple[int, Dict[int, float]]:
        """投票阶段"""
        self.state.phase = "vote"
        self.state.votes.clear()
        self.state.vote_weights.clear()

        for player_id in self.state.alive:
            response = responses.get(player_id, "")
            target = self.parser.parse_vote(response)

            if target and target in self.state.alive:
                self.state.votes[player_id] = target
                weight = 2.0 if self.state.players[player_id]["is_sheriff"] else 1.0
                self.state.vote_weights[target] = self.state.vote_weights.get(target, 0) + weight

        # 找出得票最多的
        if self.state.vote_weights:
            max_votes = max(self.state.vote_weights.values())
            candidates = [p for p, v in self.state.vote_weights.items() if v == max_votes]

            executed = candidates[0] if len(candidates) == 1 else None

            self.log_event("vote_tally", votes=dict(self.state.votes),
                          weights=dict(self.state.vote_weights),
                          executed=executed, tied=len(candidates) > 1)

            print(f"\n[投票] 票数统计: {self.state.vote_weights}")
            if executed:
                print(f"[投票] 处决 Player {executed}")
            else:
                print(f"[投票] 平票: {candidates}")

            return executed, self.state.vote_weights

        return None, {}

    # ====== 阶段6: 遗言/开枪 ======
    def phase_last_words(self, player_id: int, response: str) -> Optional[int]:
        """遗言/开枪"""
        self.state.phase = "last_words"
        role = self.get_role(player_id)

        # 猎人或狼王可以开枪
        if role in ["H", "WK"]:
            target = self.parser.parse_shoot(response)
            if target and target in self.state.alive:
                self.log_event("shoot", shooter=player_id, target=target, role=role)
                print(f"\n[开枪] Player {player_id} ({ROLE_CONFIG[role]['name']}) 带走 Player {target}")
                return target

        return None

    # ====== 阶段7: 夜晚行动 ======
    def phase_night(self, responses: Dict[int, str]) -> List[int]:
        """夜晚行动阶段"""
        self.state.phase = "night"
        self.state.night_actions.clear()

        # 收集所有行动
        for player_id in self.state.alive:
            response = responses.get(player_id, "")
            role = self.get_role(player_id)
            action = self.parser.parse_night_action(response, role)

            if action:
                self.state.night_actions[player_id] = action
                self.log_event("night_action", player=player_id, action=action)

        # 结算夜晚行动
        deaths = []

        # 1. 狼刀
        wolf_target = None
        wolf_votes = defaultdict(int)
        for pid, action in self.state.night_actions.items():
            if action.get("action") == "kill":
                wolf_votes[action["target"]] += 1

        if wolf_votes:
            wolf_target = max(wolf_votes, key=wolf_votes.get)
            print(f"\n[夜晚] 狼队刀 Player {wolf_target}")

        # 2. 守卫守护
        guard_target = None
        for pid, action in self.state.night_actions.items():
            if action.get("action") == "guard":
                guard_target = action["target"]
                # 不能连续守同一人
                if guard_target == self.state.guard_last_target:
                    print(f"[夜晚] 守卫不能连续守同一人，守护失败")
                    guard_target = None
                else:
                    self.state.guard_last_target = guard_target
                    print(f"[夜晚] 守卫守护 Player {guard_target}")
                break

        # 3. 预言家查验
        for pid, action in self.state.night_actions.items():
            if action.get("action") == "check":
                target = action["target"]
                result = self.get_team(target)
                self.state.seer_checks.append((target, result))
                print(f"[夜晚] 预言家查验 Player {target}: {result}")
                break

        # 4. 女巫行动
        witch_save = False
        witch_poison = None

        for pid, action in self.state.night_actions.items():
            if action.get("action") == "save" and not self.state.witch_save_used:
                if action["target"] == wolf_target:
                    witch_save = True
                    self.state.witch_save_used = True
                    print(f"[夜晚] 女巫救 Player {wolf_target}")

            elif action.get("action") == "poison" and not self.state.witch_poison_used:
                witch_poison = action["target"]
                self.state.witch_poison_used = True
                print(f"[夜晚] 女巫毒 Player {witch_poison}")

        # 5. 结算死亡
        # 狼刀的人
        if wolf_target:
            if guard_target == wolf_target:
                print(f"[夜晚] Player {wolf_target} 被守卫守护，未死")
            elif witch_save:
                print(f"[夜晚] Player {wolf_target} 被女巫救，未死")
            else:
                deaths.append((wolf_target, "wolf_kill"))

        # 女巫毒的人
        if witch_poison:
            deaths.append((witch_poison, "witch_poison"))

        # 执行死亡
        for pid, cause in deaths:
            self.kill_player(pid, cause)

            # 猎人被杀可以开枪
            if self.get_role(pid) == "H":
                print(f"[夜晚] 猎人 Player {pid} 死亡，可以开枪")
                # 这里需要额外的输入，简化处理：随机选择
                # 实际应该给猎人玩家一个机会输入 H:SHOT:x

        return [d[0] for d in deaths]

    # ====== 阶段8: 黎明公布 ======
    def phase_dawn(self, deaths: List[int]):
        """黎明阶段"""
        self.state.phase = "dawn"
        self.state.day += 1

        self.log_event("dawn", deaths=deaths)
        print(f"\n{'='*60}")
        print(f"第 {self.state.day} 天黎明")
        print(f"昨夜死亡: {deaths if deaths else '平安夜'}")
        print(f"存活玩家: {self.state.alive}")
        print(f"{'='*60}")


# ====== 测试/示例 ======
def run_test_game():
    """运行测试游戏"""
    game = WerewolfGame(seed=123)

    print("="*60)
    print("狼人杀 ULS/ULS++ 版本测试")
    print("="*60)
    print("\n角色分配:")
    for pid, player in game.state.players.items():
        role = player["role"]
        print(f"  Player {pid}: {ROLE_CONFIG[role]['name']} ({role})")

    # ====== 第1天 ======
    print("\n\n" + "="*60)
    print("第 1 天开始")
    print("="*60)

    # 阶段1: 上警
    print("\n【阶段1: 上警】")
    election_responses = {
        1: "ELC:JOIN",  # 1号上警
        3: "ELC:JOIN",  # 3号上警
        5: "ELC:JOIN",  # 5号上警
        7: "ELC:PASS",  # 7号不上
    }
    # 其他玩家默认PASS
    for i in range(1, 13):
        if i not in election_responses:
            election_responses[i] = "ELC:PASS"

    candidates = game.phase_election(election_responses)

    # 阶段2: 竞选投票
    if candidates:
        print("\n【阶段2: 竞选投票】")
        vote_responses = {}
        for i in range(1, 13):
            # 简化：随机投给候选人之一
            target = random.choice(candidates)
            vote_responses[i] = f"ELCV:{target}"

        sheriff = game.phase_sheriff_vote(vote_responses)

        # 阶段3: 警长定序
        if sheriff:
            print("\n【阶段3: 警长定序】")
            order = list(range(1, 13))
            random.shuffle(order)
            game.set_speech_order(order)

    # 阶段4: 白天发言
    print("\n【阶段4: 白天发言】")
    speech_responses = {}
    for pid in range(1, 13):
        # 简化：生成随机的ULS++头部
        pv = random.choice([p for p in range(1, 13) if p != pid])
        sus_list = random.sample([p for p in range(1, 13) if p != pid], 2)

        role = game.get_role(pid)
        claim = ""
        if random.random() < 0.3:  # 30%概率声明身份
            claim = f"|CL:{role}+{random.randint(5, 9)}"

        speech = f"PV:{pv}|ST:M|SUS:{sus_list[0]}@{random.uniform(3, 5):.1f},{sus_list[1]}@{random.uniform(2, 4):.1f}|CF:{random.uniform(3, 5):.1f}{claim}|K:80"
        speech_responses[pid] = speech

    parsed, conflicts = game.phase_speech(speech_responses)

    # 阶段5: 投票
    print("\n【阶段5: 投票】")
    vote_responses = {}
    for pid in range(1, 13):
        if pid in game.state.alive:
            # 使用发言中的PV作为投票目标
            target = parsed.get(pid, {}).get("pv", random.choice(game.state.alive))
            vote_responses[pid] = f"VT:{target}"

    executed, weights = game.phase_vote(vote_responses)

    # 阶段6: 处决
    if executed:
        print("\n【阶段6: 处决】")
        game.kill_player(executed, "execution")

        # 遗言/开枪
        role = game.get_role(executed)
        if role in ["H", "WK"]:
            # 随机选择一个目标开枪
            target = random.choice([p for p in game.state.alive if p != executed])
            response = f"{role}:SHOT:{target}"
            shot_target = game.phase_last_words(executed, response)
            if shot_target:
                game.kill_player(shot_target, f"{role}_shoot")

    # 检查胜利
    result = game.check_win_condition()
    if result:
        winner, reason = result
        print(f"\n{'='*60}")
        print(f"游戏结束！{winner} 阵营获胜")
        print(f"原因: {reason}")
        print(f"{'='*60}")
        return

    # 阶段7: 夜晚
    print("\n【阶段7: 夜晚行动】")
    night_responses = {}

    # 狼队投票刀人
    wolves = [p for p in game.state.alive if game.get_team(p) == "wolf"]
    if wolves:
        target = random.choice([p for p in game.state.alive if p not in wolves])
        for wolf in wolves:
            night_responses[wolf] = f"N:{target}"

    # 守卫守人
    guards = [p for p in game.state.alive if game.get_role(p) == "G"]
    if guards:
        target = random.choice(game.state.alive)
        night_responses[guards[0]] = f"G:{target}"

    # 预言家查验
    seers = [p for p in game.state.alive if game.get_role(p) == "S"]
    if seers:
        target = random.choice([p for p in game.state.alive if p != seers[0]])
        night_responses[seers[0]] = f"S:{target}"

    # 女巫（简化：不行动）

    deaths = game.phase_night(night_responses)

    # 阶段8: 黎明
    game.phase_dawn(deaths)

    # 检查胜利
    result = game.check_win_condition()
    if result:
        winner, reason = result
        print(f"\n{'='*60}")
        print(f"游戏结束！{winner} 阵营获胜")
        print(f"原因: {reason}")
        print(f"{'='*60}")

    print(f"\n\n总共产生 {len(game.state.log)} 条游戏日志")


if __name__ == "__main__":
    run_test_game()
