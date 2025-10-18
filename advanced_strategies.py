"""
高级策略模块 (Advanced Strategies Module)
包含信息对冲、机械冲突、票型搅动等复杂策略的实现
"""

# ========================================================================
# 信息对冲策略 (Information Hedging)
# ========================================================================

def analyze_seer_counter_claim(seer_claims_history, player_id, claimed_round):
    """
    分析预言家对跳情况

    Args:
        seer_claims_history: 历史预言家声称记录
        player_id: 当前声称玩家ID
        claimed_round: 声称轮次

    Returns:
        dict: {"is_counter_claim": bool, "conflicts_with": [player_ids], "credibility": float}
    """
    conflicts = []
    for claim in seer_claims_history:
        if claim["player_id"] != player_id and claim["claimed_round"] <= claimed_round:
            conflicts.append(claim["player_id"])

    credibility = max(0.0, 1.0 - len(conflicts) * 0.3)  # 每个冲突降低30%可信度

    return {
        "is_counter_claim": len(conflicts) > 0,
        "conflicts_with": conflicts,
        "credibility": credibility
    }

def detect_fake_identity(player_speech, claimed_role, night_actions):
    """
    检测假金水/假身份

    Args:
        player_speech: 玩家发言内容
        claimed_role: 声称的角色
        night_actions: 夜间行动记录

    Returns:
        dict: {"is_likely_fake": bool, "confidence": float, "evidence": [str]}
    """
    evidence = []
    confidence = 0.0

    # 检查是否有矛盾的行动记录
    if claimed_role == "预言家":
        # 如果声称预言家但没有查验记录
        if len(night_actions.get("seer_checks", [])) == 0:
            evidence.append("声称预言家但无查验记录")
            confidence += 0.4

    # 检查时间线矛盾
    if "昨晚" in player_speech and "前天" in player_speech:
        # 时间线混乱可能是编造
        evidence.append("时间线描述混乱")
        confidence += 0.2

    return {
        "is_likely_fake": confidence > 0.5,
        "confidence": confidence,
        "evidence": evidence
    }

def identify_wolf_charge_play(player_id, speech_pattern, vote_pattern, claimed_identities):
    """
    识别冲锋狼/悍跳狼

    Args:
        player_id: 玩家ID
        speech_pattern: 发言模式分析
        vote_pattern: 投票模式分析
        claimed_identities: 身份声称记录

    Returns:
        dict: {"is_charge_wolf": bool, "aggression_score": float, "tactics": [str]}
    """
    aggression_score = 0.0
    tactics = []

    # 检查是否悍跳神职
    if "预言家" in str(claimed_identities.get(player_id, {})):
        tactics.append("悍跳预言家")
        aggression_score += 0.5

    # 检查投票激进程度
    if vote_pattern.get("vote_changes", 0) > 2:
        tactics.append("频繁改票")
        aggression_score += 0.2

    # 检查发言压制程度
    if speech_pattern.get("suspicion_targets", 0) > 3:
        tactics.append("广撒怀疑")
        aggression_score += 0.3

    return {
        "is_charge_wolf": aggression_score > 0.6,
        "aggression_score": aggression_score,
        "tactics": tactics
    }


# ========================================================================
# 机械冲突策略 (Mechanical Conflicts)
# ========================================================================

def check_witch_guard_conflict(witch_saved_id, guard_protected_id, wolf_target_id, round_num):
    """
    检测女巫解药与守卫守护的冲突

    Args:
        witch_saved_id: 女巫解救的玩家ID
        guard_protected_id: 守卫守护的玩家ID
        wolf_target_id: 狼人击杀目标ID
        round_num: 轮次

    Returns:
        dict: {"has_conflict": bool, "conflict_type": str, "saved_player": int}
    """
    has_conflict = False
    conflict_type = "none"
    saved_player = None

    if wolf_target_id is None:
        return {"has_conflict": False, "conflict_type": "no_kill", "saved_player": None}

    # 情况1: 守卫守住了狼人目标
    guard_saved = (guard_protected_id == wolf_target_id)

    # 情况2: 女巫救了狼人目标
    witch_saved = (witch_saved_id == wolf_target_id)

    if guard_saved and witch_saved:
        has_conflict = True
        conflict_type = "both_saved_same"  # 双重守护同一人
        saved_player = wolf_target_id
    elif guard_saved:
        conflict_type = "guard_saved"
        saved_player = guard_protected_id
    elif witch_saved:
        conflict_type = "witch_saved"
        saved_player = witch_saved_id
    else:
        conflict_type = "not_saved"
        saved_player = None

    return {
        "has_conflict": has_conflict,
        "conflict_type": conflict_type,
        "saved_player": saved_player,
        "round": round_num
    }

def analyze_wolf_king_self_bomb_timing(game_state, wolf_king_id, current_round):
    """
    分析狼王自爆时机

    Args:
        game_state: 当前游戏状态
        wolf_king_id: 狼王玩家ID
        current_round: 当前轮次

    Returns:
        dict: {"should_bomb": bool, "urgency": float, "reasons": [str]}
    """
    if not wolf_king_id or not game_state.get("PLAYERS", [])[wolf_king_id].get("alive", False):
        return {"should_bomb": False, "urgency": 0.0, "reasons": ["狼王不存活"]}

    reasons = []
    urgency = 0.0

    # 检查投票风险
    vote_pressure = game_state.get("vote_pressure", {}).get(wolf_king_id, 0)
    if vote_pressure > 0.7:
        reasons.append("投票压力过大")
        urgency += 0.5

    # 检查队友存活情况
    alive_wolves = sum(1 for p in game_state.get("PLAYERS", [])
                      if p.get("role") in ["狼人", "狼王"] and p.get("alive", False))
    if alive_wolves <= 2:
        reasons.append("队友数量告急")
        urgency += 0.3

    # 检查神职暴露情况
    exposed_gods = len([p for p in game_state.get("PLAYERS", [])
                       if p.get("role") in ["预言家", "女巫", "猎人"]
                       and p.get("exposed", False)])
    if exposed_gods >= 2:
        reasons.append("可带走关键神职")
        urgency += 0.2

    return {
        "should_bomb": urgency > 0.6,
        "urgency": urgency,
        "reasons": reasons
    }


# ========================================================================
# 票型搅动策略 (Vote Pattern Manipulation)
# ========================================================================

def detect_vote_split_strategy(votes, round_num):
    """
    检测拆票策略

    Args:
        votes: 投票记录 {voter_id: target_id}
        round_num: 轮次

    Returns:
        dict: {"is_split": bool, "split_targets": [int], "split_initiators": [int]}
    """
    from collections import Counter

    vote_counts = Counter(votes.values())

    # 如果票数分散在多个目标上
    if len(vote_counts) >= 3:
        # 找出票数相近的目标
        sorted_targets = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)

        if len(sorted_targets) >= 2:
            top_two = sorted_targets[:2]
            if abs(top_two[0][1] - top_two[1][1]) <= 1:
                # 票数非常接近，可能是故意拆票
                split_targets = [top_two[0][0], top_two[1][0]]

                # 找出可能的拆票发起者
                split_initiators = [voter for voter, target in votes.items()
                                  if target in split_targets]

                return {
                    "is_split": True,
                    "split_targets": split_targets,
                    "split_initiators": split_initiators,
                    "round": round_num
                }

    return {"is_split": False, "split_targets": [], "split_initiators": [], "round": round_num}

def analyze_vote_concession(votes, speeches, round_num):
    """
    分析让票行为

    Args:
        votes: 投票记录
        speeches: 发言记录
        round_num: 轮次

    Returns:
        dict: {"has_concession": bool, "conceder": int, "beneficiary": int}
    """
    # 检查发言中是否有让票表示
    concession_keywords = ["让票", "不投", "弃票", "跟票"]

    for speech in speeches:
        player_id = speech.get("player_id")
        content = speech.get("content", "")

        if any(keyword in content for keyword in concession_keywords):
            # 找出谁是让票受益者
            voted_target = votes.get(player_id)

            if voted_target:
                return {
                    "has_concession": True,
                    "conceder": player_id,
                    "beneficiary": voted_target,
                    "round": round_num
                }

    return {"has_concession": False, "conceder": None, "beneficiary": None, "round": round_num}

def evaluate_tie_pk_situation(votes, sheriff_id):
    """
    评估平票PK情况

    Args:
        votes: 投票记录
        sheriff_id: 警长ID

    Returns:
        dict: {"is_tie": bool, "tied_players": [int], "sheriff_can_decide": bool}
    """
    from collections import Counter

    vote_counts = Counter(votes.values())

    if not vote_counts:
        return {"is_tie": False, "tied_players": [], "sheriff_can_decide": False}

    max_votes = max(vote_counts.values())
    tied_players = [player_id for player_id, count in vote_counts.items()
                   if count == max_votes]

    is_tie = len(tied_players) > 1
    sheriff_can_decide = is_tie and sheriff_id is not None

    return {
        "is_tie": is_tie,
        "tied_players": tied_players,
        "sheriff_can_decide": sheriff_can_decide,
        "max_votes": max_votes
    }

def analyze_badge_transfer_strategy(from_player_id, to_player_id, game_state, reason):
    """
    分析警徽流转策略

    Args:
        from_player_id: 转出警徽的玩家
        to_player_id: 接收警徽的玩家
        game_state: 游戏状态
        reason: 流转原因

    Returns:
        dict: {"is_strategic": bool, "purpose": str, "risk_level": float}
    """
    purpose = "unknown"
    risk_level = 0.5
    is_strategic = False

    if reason == "death":
        # 死亡时的警徽流转
        receiver_role = game_state.get("PLAYERS", [])[to_player_id].get("role", "unknown")

        if receiver_role in ["预言家", "女巫", "猎人"]:
            purpose = "保护关键神职"
            risk_level = 0.3
            is_strategic = True
        elif receiver_role in ["村民"]:
            purpose = "测试身份"
            risk_level = 0.6
            is_strategic = True

    elif reason == "voluntary":
        # 主动让警徽
        purpose = "战略转移"
        risk_level = 0.7
        is_strategic = True

    return {
        "is_strategic": is_strategic,
        "purpose": purpose,
        "risk_level": risk_level,
        "from": from_player_id,
        "to": to_player_id
    }
