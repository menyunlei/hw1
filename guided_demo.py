"""
Guided Demo Module - Orchestrates 11 NPC players through a scripted Werewolf game scenario
引导演示模块 - 编排11个NPC玩家执行狼人杀剧本

Workflow:
N1: Wolf kills 5; Witch doesn't save, poisons 4; Guard protects 3; Real Seer checks 10 (Wolf)
D1: Sheriff election - Real Seer vs Fake Seer compete, vote ties 4-4-3, goes to PK
N2: Wolves adjust strategy based on voting patterns
D2: Wolf King may explode to take key player
D3: Final deduction phase
"""

# ========================================================================
# Player Role Assignments and Scripts
# ========================================================================

DEMO_ROLES = {
    1: {
        "role": "狼王",
        "duty": "强势逻辑、控最后票，必要时自爆带走关键信息位",
        "behavior": {
            "sheriff_campaign": False,  # Don't run for sheriff
            "voting_style": "aggressive",
            "speech_style": "logical_aggressive",
            "side_with": "fake_seer",  # Side with fake seer (player 10 or wolf teammate)
        }
    },
    2: {
        "role": "预言家",  # Real Seer
        "duty": "稳定叙述验序与视角，不主动贴脸，但要能回怼细节",
        "behavior": {
            "sheriff_campaign": True,  # Must run for sheriff
            "check_target_n1": 10,  # Check player 10 on Night 1 (will find wolf)
            "claim_info": "10查杀、3金水",
            "speech_style": "calm_detailed",
            "side_with": "self"
        }
    },
    3: {
        "role": "村民",  # Could be villager or god role, treated as golden water
        "duty": "刻意出现一处小口误（给被测者真伪判断的素材）",
        "behavior": {
            "sheriff_campaign": False,
            "speech_style": "nervous_mistake",  # Intentionally make small error
            "side_with": "real_seer",
            "protected_n1": True  # Guard protects this player N1
        }
    },
    4: {
        "role": "村民",
        "duty": "D1讲话略显狼形，死后提供歧义遗言",
        "behavior": {
            "sheriff_campaign": False,
            "speech_style": "suspicious",
            "will_be_poisoned": True,  # Witch poisons N1
            "last_words": "ambiguous"
        }
    },
    5: {
        "role": "村民",
        "duty": "D1发言中庸，让女巫不救更合理",
        "behavior": {
            "sheriff_campaign": False,
            "speech_style": "neutral",
            "will_be_killed": True  # Wolf kills N1
        }
    },
    6: {
        "role": "女巫",
        "duty": "D2是否自证视现场难度；自证时只抛一半药序引争议",
        "behavior": {
            "sheriff_campaign": False,
            "save_n1": False,  # Don't save player 5
            "poison_n1": 4,  # Poison player 4
            "reveal_style": "partial",  # Only reveal partial info
            "side_with": "real_seer"
        }
    },
    7: {
        "role": "村民",  # The test subject / player being evaluated
        "duty": "被测平民：自由发挥",
        "behavior": {
            "sheriff_campaign": False,
            "speech_style": "free",
            "side_with": "fake_seer",  # Sides with fake seer initially
            "test_subject": True
        }
    },
    8: {
        "role": "守卫",
        "duty": "D2伪装成读到女巫药顺的口风，钓被测者追问守位逻辑",
        "behavior": {
            "sheriff_campaign": False,
            "protect_n1": 3,  # Protect player 3
            "protect_n2": 2,  # Protect real seer N2
            "speech_style": "hinting",  # Hint at witch's actions
            "side_with": "real_seer"
        }
    },
    9: {
        "role": "猎人",
        "duty": "被出局时倒钩或不开枪，逼出被测者的再归票",
        "behavior": {
            "sheriff_campaign": False,
            "shoot_when_killed": "conditional",  # May not shoot to create confusion
            "speech_style": "neutral"
        }
    },
    10: {
        "role": "狼人",  # Regular wolf, gets checked by real seer
        "duty": "演好人细节位，反复追问预言家验序",
        "behavior": {
            "sheriff_campaign": True,  # Must run as fake seer
            "fake_claim": "预言家",
            "fake_check_info": "3金水、10好人",  # Claim self as good
            "speech_style": "detailed_questioning",
            "side_with": "self"
        }
    },
    11: {
        "role": "狼人",
        "duty": "负责牵制被测者或其核心同盟",
        "behavior": {
            "sheriff_campaign": False,
            "speech_style": "disruptive",
            "target_player": 7,  # Target test subject
            "side_with": "fake_seer"
        }
    },
    12: {
        "role": "狼人",  # Could be wolf or villager actor
        "duty": "控票与节奏衔接，补位平票或秒定",
        "behavior": {
            "sheriff_campaign": False,
            "voting_style": "strategic",
            "speech_style": "rhythmic"
        }
    }
}

# ========================================================================
# Voting Instructions per Round
# ========================================================================

VOTING_SCRIPT = {
    "sheriff_election": {
        "candidates": [2, 10],  # Real Seer vs Fake Seer
        "votes": {
            # Side with fake seer (player 10)
            1: 10,
            7: 10,
            11: 10,
            12: 10,  # 4 votes

            # Side with real seer (player 2)
            3: 2,
            6: 2,
            8: 2,  # 3 votes

            # Neutral/swing (will cause tie)
            4: 10,  # Makes it 4-4 before PK
            5: 2,
            9: 2   # Intentionally create tension
        },
        "result": "tie_to_pk"  # Goes to PK debate
    },

    "day1_exile": {
        "target": None,  # To be determined by PK results
        "voting_strategy": "follow_sheriff"
    },

    "day2_exile": {
        "wolf_king_explode": True,  # Player 1 may self-destruct
        "target_when_explode": 2  # Take out real seer if explodes
    }
}

# ========================================================================
# Night Action Scripts
# ========================================================================

NIGHT_ACTIONS = {
    "night1": {
        "wolves_kill": 5,  # Kill player 5
        "seer_check": 10,  # Real seer checks player 10
        "guard_protect": 3,  # Guard protects player 3
        "witch_save": False,  # Don't save player 5
        "witch_poison": 4  # Poison player 4
    },

    "night2": {
        "wolves_kill": None,  # Determined by D1 voting patterns
        "wolves_strategy": "kill_real_seer_supporter",
        "guard_protect": 2,  # Protect seer
        "witch_save": False,  # Keep suspense
        "witch_poison": None  # Already used
    }
}

# ========================================================================
# ULS++ Encoded Instructions for Each Player
# ========================================================================

ULS_INSTRUCTIONS = {
    # 上警环节 (Sheriff Campaign)
    "sheriff_campaign": {
        2: {  # Real Seer - Player 2
            "uls_format": "CL:S+5@N1|CHK:10:W|CHK:3:V",
            "instruction": "You are real seer. Checked seat 10: W (wolf). Checked seat 3: V (villager). Claim with confidence 5.",
            "natural_language": "我是预言家，昨晚验了10号是狼人，3号是金水。"
        },
        10: {  # Fake Seer - Wolf Player 10
            "uls_format": "CL:S+4@N1|CHK:3:V|CHK:10:V",
            "instruction": "You are wolf. Fake claim seer. Pretend checked seat 3: V, seat 10: V (protect yourself).",
            "natural_language": "我是预言家，昨晚验了3号是金水，10号是好人。"
        }
    },

    # 狼人夜晚讨论 (Werewolf Night Discussion)
    "wolf_discussion": {
        "night1": {
            1: {  # Wolf King
                "uls_format": "ATK:5|STRAT:KILL_NEUTRAL|CAMP:FAKE_SEER:10",
                "instruction": "Suggest kill player 5 (neutral speaker). Support player 10 to fake claim seer.",
                "natural_language": "我建议刀5号，他发言中庸，女巫可能不救。10号明天上警跳预言家。"
            },
            10: {  # Wolf - will fake claim seer
                "uls_format": "CL:S@D1|CAMP:YES|ATK:5",
                "instruction": "Agree to fake claim seer tomorrow. Agree to kill player 5.",
                "natural_language": "好，我明天上警跳预言家。同意刀5号。"
            },
            11: {  # Wolf
                "uls_format": "CAMP:YES|TARGET:7|ATK:5",
                "instruction": "Support wolf king. Will target player 7 (test subject) during day. Agree kill 5.",
                "natural_language": "同意。我明天盯住7号，看他的站边。"
            },
            12: {  # Wolf
                "uls_format": "VOTE:CONTROL|CAMP:FAKE_SEER:10|ATK:5",
                "instruction": "Focus on vote control. Support fake seer (player 10). Agree kill 5.",
                "natural_language": "收到。我明天控票，争取平票。"
            }
        },
        "night2": {
            1: {  # Wolf King
                "uls_format": "ATK:2|STRAT:KILL_SEER|BACKUP:EXPLODE",
                "instruction": "Suggest kill player 2 (real seer) or supporters. Ready to explode if needed.",
                "natural_language": "今天刀站真预的人，比如6号或8号。如果局势不利，我考虑自爆带人。"
            }
        }
    },

    # 白天投票 (Day Voting)
    "day_voting": {
        "sheriff_election": {
            1: {"uls_format": "VOTE:10|SIDE:FAKE_SEER", "vote": 10, "reason": "支持10号预言家"},
            3: {"uls_format": "VOTE:2|SIDE:REAL_SEER", "vote": 2, "reason": "我是金水，支持2号"},
            4: {"uls_format": "VOTE:10|SIDE:UNCERTAIN", "vote": 10, "reason": "我觉得10号更像真的"},
            5: {"uls_format": "VOTE:2|SIDE:NEUTRAL", "vote": 2, "reason": "听完发言，我选2号"},
            6: {"uls_format": "VOTE:2|SIDE:REAL_SEER", "vote": 2, "reason": "2号细节更真实"},
            7: {"uls_format": "VOTE:10|SIDE:FAKE_SEER", "vote": 10, "reason": "10号逻辑更清晰"},
            8: {"uls_format": "VOTE:2|SIDE:REAL_SEER", "vote": 2, "reason": "站2号这边"},
            9: {"uls_format": "VOTE:2|SIDE:NEUTRAL", "vote": 2, "reason": "暂时站2号"},
            11: {"uls_format": "VOTE:10|SIDE:FAKE_SEER", "vote": 10, "reason": "相信10号"},
            12: {"uls_format": "VOTE:10|SIDE:FAKE_SEER", "vote": 10, "reason": "10号是真预言家"}
        },
        "day1_exile": {
            # After PK, vote for exile (flexible based on sheriff decision)
        }
    }
}

# ========================================================================
# Speech Templates for Each Player
# ========================================================================

SPEECH_TEMPLATES = {
    "logical_aggressive": [
        "我觉得{target}的发言有明显漏洞，逻辑站不住脚。",
        "从{target}的票型和站边来看，他的身份很可疑。",
        "我建议今天直接出{target}，不要拖节奏。"
    ],

    "calm_detailed": [
        "我是预言家，昨晚验了{check_target}，身份是{result}。",
        "我详细说一下我的验人逻辑：{reasoning}",
        "请大家仔细听我的发言，对比另一个跳预言家的人。"
    ],

    "nervous_mistake": [
        "我觉得...等等，我刚才说的是{mistake}，不对，应该是{correction}。",
        "我支持{side}，因为...呃，他的发言比较真。"
    ],

    "suspicious": [
        "我是好人，但是{target}为什么一直盯着我？",
        "我觉得预言家两边都有可能，不好判断。",
        "如果我死了，请大家注意{hint}。"  # Ambiguous last words
    ],

    "neutral": [
        "今天的局势不太明朗，两边预言家都有道理。",
        "我先听完大家发言再决定站边。"
    ],

    "partial": [
        "我是女巫，昨晚我看到{wolf_target}被刀了。",
        "至于我用没用药...这个我暂时不想说。"  # Only partial info
    ],

    "hinting": [
        "我感觉昨晚的药序有点意思，{target}可能知道一些东西。",
        "如果女巫是这样用药的话，那么{reasoning}。"
    ],

    "detailed_questioning": [
        "你说你验了{player}，那么你的验人顺序是怎么决定的？",
        "我也是预言家，我昨晚验了{check_target}，是{result}。",
        "请大家对比我们两个的发言细节，看谁更像真预言家。"
    ],

    "disruptive": [
        "{target}你为什么站那边？你的理由能详细说说吗？",
        "我觉得{target}的站边很奇怪，大家注意一下。"
    ],

    "rhythmic": [
        "现在的票型是{vote_count}，我们需要{action}。",
        "我建议大家{suggestion}，控制一下节奏。"
    ]
}

# ========================================================================
# Helper Functions
# ========================================================================

def get_uls_instruction(player_id, phase, context=None):
    """
    Get ULS++ encoded instruction for a player in a specific phase.

    Args:
        player_id: Player ID (1-12)
        phase: Phase name (sheriff_campaign, wolf_discussion, day_voting, etc.)
        context: Additional context (night number, vote type, etc.)

    Returns:
        dict with ULS format, instruction, and natural language
    """
    if phase not in ULS_INSTRUCTIONS:
        return None

    phase_data = ULS_INSTRUCTIONS[phase]

    # Handle nested structures (e.g., wolf_discussion has night1/night2)
    if context and "night" in context:
        night_key = f"night{context['night']}"
        if night_key in phase_data:
            phase_data = phase_data[night_key]

    if context and "vote_type" in context:
        vote_type = context["vote_type"]
        if vote_type in phase_data:
            phase_data = phase_data[vote_type]

    if player_id in phase_data:
        return phase_data[player_id]

    return None


def get_player_script(player_id, phase, context=None):
    """
    Get the scripted behavior for a player in a specific phase.

    Args:
        player_id: Player ID (1-12)
        phase: Game phase (sheriff_campaign, day1_speech, voting, etc.)
        context: Additional context (voting targets, etc.)

    Returns:
        dict with player's actions/speech for this phase
    """
    if player_id not in DEMO_ROLES:
        return None

    player = DEMO_ROLES[player_id]
    behavior = player["behavior"]

    script = {
        "player_id": player_id,
        "role": player["role"],
        "duty": player["duty"]
    }

    # Get ULS++ instruction if available
    uls_data = get_uls_instruction(player_id, phase, context)
    if uls_data:
        script["uls_format"] = uls_data.get("uls_format")
        script["uls_instruction"] = uls_data.get("instruction")
        script["natural_language"] = uls_data.get("natural_language")

    # Phase-specific instructions
    if phase == "sheriff_campaign":
        script["should_run"] = behavior.get("sheriff_campaign", False)
        if script["should_run"]:
            if player_id == 2:  # Real seer
                script["speech"] = "我是预言家，昨晚验了10号是狼人，3号是金水。"
                script["uls_output"] = "CL:S+5@N1|CHK:10:W|CHK:3:V"
            elif player_id == 10:  # Fake seer
                script["speech"] = "我是预言家，昨晚验了3号是金水，10号是好人。"
                script["uls_output"] = "CL:S+4@N1|CHK:3:V|CHK:10:V"

    elif phase == "voting":
        if context and "vote_type" in context:
            vote_type = context["vote_type"]
            if vote_type in VOTING_SCRIPT:
                script["vote_for"] = VOTING_SCRIPT[vote_type]["votes"].get(player_id)

    elif phase == "day_speech":
        speech_style = behavior.get("speech_style", "neutral")
        script["speech_template"] = SPEECH_TEMPLATES.get(speech_style, [])
        script["side_with"] = behavior.get("side_with")

    elif phase == "night_action":
        if player["role"] == "狼人":
            script["action"] = "kill"
            if context and "night" in context:
                night_num = context["night"]
                if f"night{night_num}" in NIGHT_ACTIONS:
                    script["target"] = NIGHT_ACTIONS[f"night{night_num}"].get("wolves_kill")

        elif player["role"] == "预言家":
            script["action"] = "check"
            if context and "night" in context:
                night_num = context["night"]
                script["target"] = behavior.get(f"check_target_n{night_num}")

        elif player["role"] == "守卫":
            script["action"] = "protect"
            if context and "night" in context:
                night_num = context["night"]
                script["target"] = behavior.get(f"protect_n{night_num}")

        elif player["role"] == "女巫":
            script["action"] = "witch"
            if context and "night" in context:
                night_num = context["night"]
                script["save"] = behavior.get(f"save_n{night_num}", False)
                script["poison"] = behavior.get(f"poison_n{night_num}")

    return script


def get_night_script(night_num):
    """Get the complete night action script for a specific night."""
    night_key = f"night{night_num}"
    if night_key in NIGHT_ACTIONS:
        return NIGHT_ACTIONS[night_key]
    return None


def get_voting_script(vote_type):
    """Get voting instructions for a specific voting phase."""
    if vote_type in VOTING_SCRIPT:
        return VOTING_SCRIPT[vote_type]
    return None


def should_player_speak(player_id, phase, context=None):
    """Determine if player should speak in current phase."""
    if player_id not in DEMO_ROLES:
        return True  # Default: allow speech

    player = DEMO_ROLES[player_id]

    # Check if player is dead
    if context and "dead_players" in context:
        if player_id in context["dead_players"]:
            return False

    return True


def get_test_subject_id():
    """Return the ID of the test subject (player being evaluated)."""
    for player_id, data in DEMO_ROLES.items():
        if data["behavior"].get("test_subject"):
            return player_id
    return 7  # Default to player 7


# ========================================================================
# Demo Execution Flow
# ========================================================================

def get_demo_summary():
    """Return a summary of the demo scenario."""
    return {
        "title": "狼人杀引导演示 - 11 NPC Player Scripted Game",
        "players": 12,
        "roles": {
            "wolves": [1, 10, 11, 12],  # Including wolf king
            "villagers": [3, 4, 5, 7],
            "seer": [2],
            "witch": [6],
            "guard": [8],
            "hunter": [9]
        },
        "test_subject": get_test_subject_id(),
        "workflow": {
            "N1": "Wolf kills 5, Witch poisons 4 (no save), Guard protects 3, Real Seer checks 10 (Wolf)",
            "D1": "Sheriff election: Real Seer (2) vs Fake Seer (10), vote ties, goes to PK",
            "N2": "Wolves adjust based on D1 votes, Guard protects Seer",
            "D2": "Wolf King may explode, take key player",
            "D3": "Final deduction phase"
        }
    }


if __name__ == "__main__":
    # Test the demo module
    print("Guided Demo Module - Configuration Test")
    print("=" * 70)

    summary = get_demo_summary()
    print(f"\nDemo: {summary['title']}")
    print(f"Players: {summary['players']}")
    print(f"Test Subject: Player {summary['test_subject']}")

    print("\n" + "=" * 70)
    print("Player Roles and Duties:")
    print("=" * 70)
    for pid, data in DEMO_ROLES.items():
        print(f"  Player {pid}: {data['role']:6s} - {data['duty'][:50]}...")

    print("\n" + "=" * 70)
    print("Night 1 Actions:")
    print("=" * 70)
    n1_script = get_night_script(1)
    for action, target in n1_script.items():
        print(f"  {action:20s}: {target}")

    print("\n" + "=" * 70)
    print("ULS++ Instructions - Sheriff Campaign:")
    print("=" * 70)
    for pid in [2, 10]:
        uls = get_uls_instruction(pid, "sheriff_campaign")
        if uls:
            print(f"\nPlayer {pid} ({DEMO_ROLES[pid]['role']}):")
            print(f"  ULS Format: {uls['uls_format']}")
            print(f"  Instruction: {uls['instruction']}")
            print(f"  Natural: {uls['natural_language']}")

    print("\n" + "=" * 70)
    print("ULS++ Instructions - Wolf Discussion N1:")
    print("=" * 70)
    for pid in [1, 10, 11, 12]:
        uls = get_uls_instruction(pid, "wolf_discussion", {"night": 1})
        if uls:
            print(f"\nPlayer {pid}:")
            print(f"  ULS Format: {uls['uls_format']}")
            print(f"  Natural: {uls['natural_language']}")

    print("\n" + "=" * 70)
    print("Sheriff Election Voting (4-4 split to create tie):")
    print("=" * 70)
    sheriff_vote = get_voting_script("sheriff_election")

    # Count votes
    vote_count = {}
    for voter, target in sheriff_vote["votes"].items():
        vote_count[target] = vote_count.get(target, 0) + 1
        uls = get_uls_instruction(voter, "day_voting", {"vote_type": "sheriff_election"})
        reason = uls["reason"] if uls else "Unknown"
        print(f"  Player {voter:2d} votes for Player {target:2d} - {reason}")

    print(f"\nVote Result:")
    for candidate, count in sorted(vote_count.items()):
        print(f"  Player {candidate}: {count} votes")
    print(f"  Result: {sheriff_vote['result']}")

    print("\n" + "=" * 70)
    print("Configuration loaded successfully!")
    print("Ready to run guided demo with ULS++ encoding!")
    print("=" * 70)
