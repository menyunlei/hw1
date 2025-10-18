"""
难度模块系统 (Difficulty Modules System)
包含基础、进阶、地狱三个难度级别的复杂策略实现
"""

# ========================================================================
# 模块 A: 双预言家对跳 + 假金水 (Double Seer Counter-claim + Fake Golden Water)
# ========================================================================

def module_a_double_seer_counterclaim(game_state, real_seer_id, fake_seer_id, golden_water_id, wolf_target_id):
    """
    模块A: 双预言家对跳策略

    Args:
        game_state: 游戏状态
        real_seer_id: 真预言家ID
        fake_seer_id: 假预言家ID (悍跳狼)
        golden_water_id: 金水位ID
        wolf_target_id: 狼队查杀目标ID

    Returns:
        dict: 对跳配置和剧本
    """

    # 真预言家发言
    real_seer_script = {
        "player_id": real_seer_id,
        "claim_role": "预言家",
        "n1_check": wolf_target_id,
        "n1_result": "狼人",
        "golden_water": golden_water_id,
        "speech_details": f"N1我验到{wolf_target_id}号是狼，给{golden_water_id}号发金水。验{wolf_target_id}是因为他位置靠后，容易藏狼。"
    }

    # 假预言家发言（完全对冲）
    fake_seer_script = {
        "player_id": fake_seer_id,
        "claim_role": "预言家",
        "n1_check": wolf_target_id,
        "n1_result": "好人",
        "golden_water": golden_water_id,
        "speech_details": f"我才是真预言家！{wolf_target_id}号是好人，{golden_water_id}号是金水。对方在悍跳！"
    }

    # 站队玩家分配
    support_real = []
    support_fake = []

    # 分配2-3人站真预
    for player in game_state.get("PLAYERS", []):
        if player.get("role") in ["村民", "女巫", "守卫"] and player["id"] != golden_water_id:
            if len(support_real) < 3:
                support_real.append(player["id"])
        elif player.get("role") == "狼人" and player["id"] != fake_seer_id:
            if len(support_fake) < 3:
                support_fake.append(player["id"])

    return {
        "module": "A_双预对跳",
        "real_seer": real_seer_script,
        "fake_seer": fake_seer_script,
        "support_real": support_real,
        "support_fake": support_fake,
        "difficulty": "高",
        "detection_clues": ["验序细节", "夜间动机", "金水重复"]
    }


# ========================================================================
# 模块 B: 女巫药顺对冲 + 守卫误守 (Witch Potion Conflict + Guard Mis-protection)
# ========================================================================

def module_b_witch_guard_conflict(game_state, wolf_target_id, witch_id, guard_id, poison_target_id, guard_target_id):
    """
    模块B: 女巫药顺与守卫守护冲突

    Args:
        game_state: 游戏状态
        wolf_target_id: 狼刀目标ID
        witch_id: 女巫ID
        guard_id: 守卫ID
        poison_target_id: 女巫毒杀目标ID
        guard_target_id: 守卫守护目标ID

    Returns:
        dict: 冲突配置
    """

    # N1 狼队刀一名陪跑民
    night1_actions = {
        "wolf_kill": wolf_target_id,
        "witch_save": None,  # 女巫N1不救
        "witch_poison": poison_target_id,  # 女巫毒另一个陪跑民
        "guard_protect": guard_target_id  # 守卫守金水位
    }

    # 判断是否平安夜
    is_peaceful_night = (guard_target_id == wolf_target_id)

    # 女巫发言策略
    witch_speech = {
        "player_id": witch_id,
        "strategy": "不自证" if not is_peaceful_night else "可能自证",
        "save_used": False,
        "poison_used": True,
        "claim": f"我N1{'救了刀口' if is_peaceful_night else '没有救人'}，药已用"
    }

    # 守卫发言策略
    guard_speech = {
        "player_id": guard_id,
        "protected": guard_target_id,
        "result": "守中" if is_peaceful_night else "空守",
        "claim": f"我N1守{guard_target_id}号，{'成功守住' if is_peaceful_night else '被刀了其他位置'}"
    }

    # D2 死亡情况
    if is_peaceful_night:
        d2_deaths = [poison_target_id]  # 只有毒死的
        discussion_point = "平安夜：女巫救？守卫守？"
    else:
        d2_deaths = [wolf_target_id, poison_target_id]  # 刀死+毒死
        discussion_point = "双死：守卫为什么没守住？"

    return {
        "module": "B_女巫守卫冲突",
        "night1_actions": night1_actions,
        "witch_speech": witch_speech,
        "guard_speech": guard_speech,
        "d2_deaths": d2_deaths,
        "is_peaceful": is_peaceful_night,
        "discussion_point": discussion_point,
        "difficulty": "中高"
    }


# ========================================================================
# 模块 C: 票型操控（平票+PK）(Vote Manipulation + Tie PK)
# ========================================================================

def module_c_vote_manipulation(game_state, target_a, target_b, manipulators):
    """
    模块C: 票型操控，制造平票PK

    Args:
        game_state: 游戏状态
        target_a: PK目标A（真预或关键好人）
        target_b: PK目标B（假预或悍跳狼）
        manipulators: 操票玩家列表 [{id, faction}]

    Returns:
        dict: 票型配置
    """

    # 预分配票型
    vote_plan = {
        "vote_target_a": [],  # 投A的玩家
        "vote_target_b": [],  # 投B的玩家
        "swing_votes": []     # 游离票（关键票）
    }

    # 分配3票给A, 3票给B
    for player in game_state.get("PLAYERS", []):
        if not player.get("alive", False):
            continue

        if player["id"] in [m["id"] for m in manipulators if m["faction"] == "good"]:
            if len(vote_plan["vote_target_a"]) < 3:
                vote_plan["vote_target_a"].append(player["id"])
        elif player["id"] in [m["id"] for m in manipulators if m["faction"] == "wolf"]:
            if len(vote_plan["vote_target_b"]) < 3:
                vote_plan["vote_target_b"].append(player["id"])
        else:
            vote_plan["swing_votes"].append(player["id"])

    # 平票策略
    tie_strategy = {
        "initial_vote": {
            "target_a": vote_plan["vote_target_a"][:3],
            "target_b": vote_plan["vote_target_b"][:3]
        },
        "swing_decision": "由狼王或关键神职决定",
        "pk_trigger": len(vote_plan["vote_target_a"]) == len(vote_plan["vote_target_b"])
    }

    return {
        "module": "C_票型搅动",
        "vote_plan": vote_plan,
        "tie_strategy": tie_strategy,
        "pk_candidates": [target_a, target_b],
        "difficulty": "中",
        "win_condition": "被测者必须合理归票"
    }


# ========================================================================
# 模块 D: 狼王节奏 + 猎人倒钩 (Wolf King Bomb + Hunter Betrayal)
# ========================================================================

def module_d_wolf_king_hunter_tactics(game_state, wolf_king_id, hunter_id, bomb_target_id, shot_target_id):
    """
    模块D: 狼王自爆节奏 + 猎人倒钩

    Args:
        game_state: 游戏状态
        wolf_king_id: 狼王ID
        hunter_id: 猎人ID
        bomb_target_id: 狼王带走目标ID
        shot_target_id: 猎人开枪目标ID（可能是好人）

    Returns:
        dict: 狼王猎人配置
    """

    # 狼王自爆时机判断
    current_round = game_state.get("round", 1)
    vote_pressure = game_state.get("vote_pressure", {}).get(wolf_king_id, 0)

    # 判断是否应该自爆
    should_bomb = False
    bomb_reason = []

    if vote_pressure > 0.7:
        should_bomb = True
        bomb_reason.append("投票压力过大")

    if current_round >= 2:
        alive_wolves = sum(1 for p in game_state.get("PLAYERS", [])
                          if p.get("role") in ["狼人", "狼王"] and p.get("alive", False))
        if alive_wolves <= 2:
            should_bomb = True
            bomb_reason.append("队友告急，必须换神")

    # 狼王自爆配置
    wolf_king_bomb = {
        "player_id": wolf_king_id,
        "should_bomb": should_bomb,
        "bomb_timing": f"D{current_round}投票前" if should_bomb else "待定",
        "bomb_target": bomb_target_id,
        "bomb_reason": bomb_reason,
        "bomb_speech": f"我是狼王，自爆带走{bomb_target_id}号！"
    }

    # 猎人倒钩配置
    hunter_tactics = {
        "player_id": hunter_id,
        "tactic": "倒钩",  # 或"正常开枪"
        "shot_target": shot_target_id,
        "shot_reason": "制造好人互伤" if shot_target_id in [p["id"] for p in game_state.get("PLAYERS", []) if p.get("role") not in ["狼人", "狼王"]] else "正常出狼",
        "death_trigger": "夜刀" if random.choice([True, False]) else "白天出局"
    }

    return {
        "module": "D_狼王猎人博弈",
        "wolf_king_bomb": wolf_king_bomb,
        "hunter_tactics": hunter_tactics,
        "difficulty": "极高",
        "impact": "迫使被测者重算格局"
    }


# ========================================================================
# 难度配置系统
# ========================================================================

DIFFICULTY_CONFIG = {
    "基础": {
        "name": "基础难度",
        "modules": ["A_双预对跳", "B_女巫守卫冲突"],
        "module_count": 2,
        "description": "双预言家对跳 + 女巫守卫冲突",
        "recommended_for": "新手测试"
    },
    "进阶": {
        "name": "进阶难度",
        "modules": ["A_双预对跳", "B_女巫守卫冲突", "C_票型搅动"],
        "module_count": 3,
        "description": "基础模块 + 票型操控",
        "recommended_for": "有经验玩家"
    },
    "地狱": {
        "name": "地狱难度",
        "modules": ["A_双预对跳", "B_女巫守卫冲突", "C_票型搅动", "D_狼王猎人博弈"],
        "module_count": 4,
        "description": "全模块激活",
        "recommended_for": "高级玩家/专业测试"
    }
}


def get_difficulty_config(difficulty_level):
    """获取难度配置"""
    return DIFFICULTY_CONFIG.get(difficulty_level, DIFFICULTY_CONFIG["基础"])


def activate_modules(difficulty_level, game_state):
    """
    根据难度级别激活对应模块

    Args:
        difficulty_level: "基础" | "进阶" | "地狱"
        game_state: 游戏状态

    Returns:
        list: 激活的模块列表
    """
    config = get_difficulty_config(difficulty_level)
    activated = []

    for module_name in config["modules"]:
        activated.append({
            "name": module_name,
            "status": "activated",
            "difficulty": config["name"]
        })

    return activated


import random
