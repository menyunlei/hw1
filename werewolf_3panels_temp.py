"""
鐙间汉鏉€ - 4瀵硅瘽妗嗙増鏈?
4 Dialogue Panels: Werewolf Night / God Roles Night / Day Discussion & Voting / Real-time Statistics
娓告垙娴佺▼锛氱1澶滃紑濮?鈫?鐙间汉璁ㄨ 鈫?绁炶亴琛屽姩 鈫?璀﹂暱绔為€?鈫?鐧藉ぉ璁ㄨ鎶曠エ
"""

from flask import Flask, render_template_string, request
import requests
import json
import threading
import time
from queue import Queue
import random
import os
import copy

# 瀵煎叆楂樼骇绛栫暐妯″潡 (Advanced Strategies Module)
try:
    from advanced_strategies import *
    ADVANCED_STRATEGIES_ENABLED = True
    print("[INFO] Advanced Strategies Module loaded successfully")
except ImportError as e:
    print(f"[WARNING] Advanced Strategies Module not found: {e}")
    ADVANCED_STRATEGIES_ENABLED = False

# 瀵煎叆闅惧害妯″潡绯荤粺 (Difficulty Modules System)
try:
    from difficulty_modules import *
    DIFFICULTY_MODULES_ENABLED = True
    print("[INFO] Difficulty Modules System loaded successfully")
except ImportError as e:
    print(f"[WARNING] Difficulty Modules System not found: {e}")
    DIFFICULTY_MODULES_ENABLED = False

# 瀵煎叆鎺ㄧ悊鑳藉姏璇勪及鍣?(Reasoning Evaluator)
EVALUATOR_ENABLED = False
EVALUATOR_IMPORT_ERROR = None
try:
    from enhanced_reasoning_evaluator import EnhancedReasoningEvaluator
    EVALUATOR_ENABLED = True
    print("[INFO] Enhanced Reasoning Evaluator loaded successfully")
except Exception as e:
    EVALUATOR_IMPORT_ERROR = str(e)
    print(f"[WARNING] Enhanced Reasoning Evaluator import failed: {e}")
    print(f"[WARNING] Detailed error: {type(e).__name__}")
    import traceback
    traceback.print_exc()
    EVALUATOR_ENABLED = False

# ========================================================================
# Server-side 螖-digest Memory Pool (T2 Optimization)
# ========================================================================
class MemoryPool:
    """
    Optimized memory pool with incremental delta-digest for token efficiency.

    Features:
    - Append-only event log (JSONL-style)
    - Materialized views: EventMap, VoteTable, ClaimGraph, SuspicionTable, CandidateSet
    - Per-player last-speak tracking for delta computation
    - Bounded digest generation (300-500 tokens)
    - Fair access: all players see same public facts
    """

    def __init__(self):
        self.events = []  # Append-only event log
        self.event_map = {}  # eid -> event_data
        self.next_event_id = 100  # Start event IDs from 100

        # Materialized views
        self.vote_table = {}  # round -> {player_id: voted_for_id}
        self.claim_graph = {}  # role -> [{"player_id": X, "round": N, "strength": score}]
        self.suspicion_table = {}  # player_id -> {target_id: score}
        self.candidate_set = set()  # Current vote candidates

        # Per-player tracking for delta computation
        self.player_last_event_id = {}  # player_id -> last_event_id_seen

    def add_event(self, event_type, round_num, player_id, content, metadata=None):
        """
        Add a new event to the pool.

        Args:
            event_type: 'speech' | 'vote' | 'claim' | 'suspicion' | 'death' | 'night_action'
            round_num: Current round number
            player_id: Player who generated this event
            content: Main content (speech text, vote target, etc.)
            metadata: Additional structured data

        Returns:
            event_id: Unique ID for this event
        """
        event_id = self.next_event_id
        self.next_event_id += 1

        event = {
            "eid": event_id,
            "type": event_type,
            "round": round_num,
            "player_id": player_id,
            "content": content,
            "metadata": metadata or {}
        }

        self.events.append(event)
        self.event_map[event_id] = event

        # Update materialized views
        self._update_views(event)

        return event_id

    def _update_views(self, event):
        """Update materialized views based on new event."""
        eid = event["eid"]
        etype = event["type"]
        round_num = event["round"]
        player_id = event["player_id"]
        content = event["content"]
        metadata = event.get("metadata", {})

        if etype == "vote":
            # Update vote table
            if round_num not in self.vote_table:
                self.vote_table[round_num] = {}
            target_id = metadata.get("target_id")
            if target_id is not None:
                self.vote_table[round_num][player_id] = target_id

        elif etype == "claim":
            # Update claim graph
            role = metadata.get("role")
            strength = metadata.get("strength", 3.0)  # Default strength
            if role:
                if role not in self.claim_graph:
                    self.claim_graph[role] = []
                self.claim_graph[role].append({
                    "player_id": player_id,
                    "round": round_num,
                    "strength": strength,
                    "event_id": eid
                })

        elif etype == "suspicion":
            # Update suspicion table
            target_id = metadata.get("target_id")
            score = metadata.get("score", 3.0)
            if target_id is not None:
                if player_id not in self.suspicion_table:
                    self.suspicion_table[player_id] = {}
                self.suspicion_table[player_id][target_id] = score

    def build_digest(self, player_id, round_num, max_tokens=400):
        """
        Build a bounded 螖-digest for a specific player.

        Returns only NEW evidence since player's last speak, plus essential context:
        - New event IDs (with types)
        - Current candidate set
        - Latest vote tally (if available)
        - Counter-claims relevant to player
        - Seat-specific mentions

        Format optimized for token efficiency.

        Args:
            player_id: Target player
            round_num: Current round
            max_tokens: Token budget (default 400)

        Returns:
            digest_str: Compact string digest
        """
        # Get last event ID this player saw
        last_seen_eid = self.player_last_event_id.get(player_id, 99)  # 99 means "nothing seen yet"

        # Get new events since last speak
        new_events = [e for e in self.events if e["eid"] > last_seen_eid and e["round"] == round_num]

        # Build compact digest
        digest_parts = []

        # 1. New event summary (EV field)
        if new_events:
            ev_list = []
            for e in new_events[:5]:  # Max 5 events to keep bounded
                ev_type_code = {
                    "speech": "S",
                    "vote": "V",
                    "claim": "C",
                    "suspicion": "X",
                    "death": "D"
                }.get(e["type"], "?")
                ev_list.append(f"{ev_type_code}{e['eid']}")
            digest_parts.append(f"NEW_EV: {','.join(ev_list)}")

        # 2. Candidate set
        if self.candidate_set:
            cand_list = sorted(list(self.candidate_set))
            digest_parts.append(f"CAND: {','.join(map(str, cand_list))}")

        # 3. Latest vote tally (from current round)
        if round_num in self.vote_table:
            vote_counts = {}
            for voter, target in self.vote_table[round_num].items():
                vote_counts[target] = vote_counts.get(target, 0) + 1
            if vote_counts:
                tally_str = ' | '.join([f"P{tid}:{cnt}" for tid, cnt in sorted(vote_counts.items(), key=lambda x: -x[1])])
                digest_parts.append(f"VOTES: {tally_str}")

        # 4. Counter-claims (if player made a claim)
        # Check if this player has any claims
        player_roles_claimed = []
        for role, claimers in self.claim_graph.items():
            for claim_info in claimers:
                if claim_info["player_id"] == player_id:
                    player_roles_claimed.append(role)
                    break

        # Find counter-claims
        if player_roles_claimed:
            counter_claims = []
            for role in player_roles_claimed:
                if role in self.claim_graph:
                    other_claimers = [c for c in self.claim_graph[role] if c["player_id"] != player_id]
                    if other_claimers:
                        counter_claims.append(f"{role}:{','.join([str(c['player_id']) for c in other_claimers])}")
            if counter_claims:
                digest_parts.append(f"COUNTER: {' | '.join(counter_claims)}")

        # 5. Top suspicions targeting this player
        suspicions_on_me = []
        for sus_player_id, targets in self.suspicion_table.items():
            if player_id in targets:
                score = targets[player_id]
                suspicions_on_me.append((sus_player_id, score))
        if suspicions_on_me:
            suspicions_on_me.sort(key=lambda x: -x[1])  # Sort by score descending
            sus_str = ','.join([f"P{pid}@{score:.1f}" for pid, score in suspicions_on_me[:3]])
            digest_parts.append(f"SUS_ON_ME: {sus_str}")

        # 6. Recent speech summaries (new events only, truncated)
        speech_summaries = []
        for e in new_events:
            if e["type"] == "speech":
                # Truncate to first 50 chars
                truncated = e["content"][:50].replace('\n', ' ')
                speech_summaries.append(f"P{e['player_id']}: {truncated}...")

        if speech_summaries:
            digest_parts.append("SPEECHES:\n  " + "\n  ".join(speech_summaries[:3]))  # Max 3 speeches

        # Combine all parts
        full_digest = "\n".join(digest_parts)

        # Rough token estimation (1 token 鈮?4 chars for Chinese/English mix)
        estimated_tokens = len(full_digest) // 4

        # If over budget, trim speeches section
        if estimated_tokens > max_tokens and "SPEECHES:" in full_digest:
            # Remove speeches section to save tokens
            digest_parts = [p for p in digest_parts if not p.startswith("SPEECHES:")]
            full_digest = "\n".join(digest_parts)

        return full_digest

    def mark_player_read(self, player_id):
        """Mark that player has seen all events up to now."""
        if self.events:
            self.player_last_event_id[player_id] = self.events[-1]["eid"]

    def update_candidate_set(self, candidates):
        """Update the current vote candidate set."""
        self.candidate_set = set(candidates)

    def get_round_speeches(self, round_num):
        """Get all speeches from a specific round (for backward compatibility)."""
        speeches = []
        for event in self.events:
            if event["type"] == "speech" and event["round"] == round_num:
                speeches.append({
                    "round": round_num,
                    "player_id": event["player_id"],
                    "content": event["content"]
                })
        return speeches

    def add_speech(self, round_num, player_id, content):
        """Add a speech event (convenience method for backward compatibility)."""
        return self.add_event("speech", round_num, player_id, content)

app = Flask(__name__)

# Add CORS support
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# 閰嶇疆鏂囦欢璺緞
CONFIG_FILE = "llm_config.json"

# 鍏ㄥ眬瀵硅瘽鍘嗗彶缂撳啿锛屼緵璇勪及鍣ㄤ娇鐢?
dialogue_history = []
dialogue_history_lock = threading.Lock()


def append_dialogue_history(event):
    """Store a copy of each event for evaluation retrieval."""
    if not isinstance(event, dict):
        return
    with dialogue_history_lock:
        dialogue_history.append(copy.deepcopy(event))


def clear_dialogue_history():
    """Reset the recorded dialogue history when restarting games or injecting test data."""
    with dialogue_history_lock:
        dialogue_history.clear()


def get_dialogue_history_snapshot():
    """Return a deep copy of the dialogue history for safe downstream processing."""
    with dialogue_history_lock:
        return copy.deepcopy(dialogue_history)


class DialogueRecordingQueue(Queue):
    """Queue that mirrors every enqueued event into the dialogue history buffer."""

    def put(self, item, block=True, timeout=None):
        processed_item = item

        if isinstance(item, dict):
            processed_item = copy.deepcopy(item)

            if "round" not in processed_item:
                processed_item["round"] = game_state.get("round", 0)
            if "phase" not in processed_item:
                processed_item["phase"] = game_state.get("phase", "")

        append_dialogue_history(processed_item)
        return super().put(processed_item, block=block, timeout=timeout)

# ========================================================================
# 娓告垙閰嶇疆
# ========================================================================
# 鐜╁鏁?= 12
# 榛樿闃靛 = { 鐙间汉脳4(鍙€?鍚嫾鐜?), 棰勮█瀹睹?, 濂冲帆脳1, 鐚庝汉脳1, 瀹堝崼脳1, 鏉戞皯脳4 }

# 娓告垙寮€鍏?
HAS_GUARD = True              # 鏄惁鏈夊畧鍗?
HAS_WOLF_KING = True          # 鏄惁鏈夌嫾鐜嬶紙甯︿汉锛?
HUNTER_NIGHT_SHOOT = False    # 鐚庝汉澶滈棿琚潃鑳藉惁寮€鏋紙甯歌涓篺alse锛?
WITCH_DOUBLE_USE = False      # 濂冲帆鍚屽鑳藉惁鏃㈡晳鍙堟瘨锛堝父瑙勪负false锛?
NIGHT_BADGE_BREAKS = True     # 璀﹂暱澶滄鏄惁璀﹀窘鐮寸锛堝父瑙佷负true锛?
ALLOW_WOLF_SELF_BOMB = True   # 鏄惁鍏佽鐙间汉鑷垎锛堝父瑙佷负true锛?
ELECTION_BEFORE_N1 = False     # 鏄惁寮€灞€鐧藉ぉ鍏堜笂璀︼紙甯歌涓簍rue锛?

# 瑙勫垯瑕佺偣锛?
# - 璀﹂暱绁ㄦ潈 = 1.5锛涘钩绁ㄧ敱璀﹂暱鍐冲畾鍑?涓嶅嚭鎴栬繘鍏ヤ簩/涓変汉PK锛堜緷鎴胯锛?
# - 澶滄鏃犻仐瑷€锛涚櫧澶╁鍐虫湁閬楄█锛堥儴鍒嗚鑹蹭緥澶栬涓嬶級
# - 鐚庝汉锛氱櫧澶╁鍐宠Е鍙戝紑鏋紱澶滄/琚瘨閫氬父涓嶅紑鏋紙鍙栧喅浜嶩UNTER_NIGHT_SHOOT锛?
# - 濂冲帆锛氳В鑽?姣掕嵂鍚?娆★紱鑻ITCH_DOUBLE_USE=false锛屽悓涓€澶滀笉鑳戒袱鐡堕兘鐢?
# - 瀹堝崼锛氫笉鑳借繛缁袱鏅氬畧鍚屼竴浜猴紱琚畧鍒扮殑浜鸿嫢琚嫾浜哄嚮鏉€鍒欏瓨娲?
# - 缁撶畻椤哄簭锛堝父鐢級锛氱嫾浜哄嚮鏉€ 鈫?瀹堝崼瀹堟姢 鈫?濂冲帆寰楃煡銆屽皢姝昏€呫€嶁啋 濂冲帆鏄惁瑙ｆ晳 鈫?濂冲帆鏄惁涓嬫瘨 鈫?榛庢槑鍏竷姝昏
# - 鑳滆礋锛氬綋銆屽瓨娲荤嫾浜烘暟閲?= 0銆嶅ソ浜鸿儨锛涘綋銆屽瓨娲荤嫾浜烘暟閲?鈮?瀛樻椿濂戒汉鏁伴噺銆嶇嫾浜鸿儨
# ========================================================================

# 鍏ㄥ眬鍙橀噺
dialogue_queue = DialogueRecordingQueue()
is_running = False
waiting_for_next_day = False  # 鏄惁鍦ㄧ瓑寰呯敤鎴风偣鍑讳笅涓€澶?
auto_mode = True  # 鏄惁鑷姩妯″紡锛堣嚜鍔ㄦ挱鏀炬父鎴忥級
uls_mode = True  # 鏄惁浣跨敤ULS鐭ご閮ㄦā寮?
current_difficulty = "鍦扮嫳"  # 榛樿闅惧害绾у埆
activated_modules = []  # 褰撳墠婵€娲荤殑妯″潡鍒楄〃
seer_claims = []
sheriff_player_id = None
sheriff_candidates = []  # 绗竴澶滅嫾浜鸿璁哄喅瀹氳皝涓婅
guard_last_target = None  # 瀹堝崼涓婃瀹堟姢鐨勭洰鏍?
witch_save_available = True  # 濂冲帆瑙ｈ嵂鏄惁鍙敤
witch_poison_available = True  # 濂冲帆姣掕嵂鏄惁鍙敤

# ========================================================================
# 楂樼骇绛栫暐杩借釜鍙橀噺 (Advanced Strategy Tracking)
# ========================================================================
# 淇℃伅瀵瑰啿杩借釜 (Information Hedging)
seer_counter_claims = {}  # {player_id: {"claimed_round": N, "strength": score, "retracted": bool}}
fake_identities = {}  # {player_id: {"claimed_role": "role", "target": target_id, "round": N}}
wolf_aggressive_plays = []  # [{"player_id": X, "action": "charge/fake_identity", "round": N}]

# 鏈烘鍐茬獊杩借釜 (Mechanical Conflicts)
witch_guard_conflicts = []  # [{"round": N, "witch_saved": X, "guard_protected": Y, "actual_target": Z}]
wolf_king_self_bomb_available = HAS_WOLF_KING  # 鐙肩帇鏄惁鍙互鑷垎
self_bomb_history = []  # [{"player_id": X, "round": N, "phase": "day/night"}]

# 绁ㄥ瀷杩借釜 (Vote Pattern Tracking)
vote_split_strategies = []  # [{"round": N, "initiator": X, "targets": [Y, Z], "purpose": "split/璁╃エ"}]
vote_tie_situations = []  # [{"round": N, "tied_players": [X, Y], "sheriff_decision": Z}]
badge_transfer_history = []  # [{"from": X, "to": Y, "round": N, "reason": "death/voluntary"}]

game_state = {
    "phase": "night",
    "round": 0,
    "dead_players": [],
    "night_actions": {},
    "players": [],
    "wolf_num": 0,
    "alive_players": 0,
    "total_players": 0
}

# 姣忔棩缁熻璁板綍
daily_statistics = []  # 瀛樺偍姣忎竴澶╃殑缁熻淇℃伅

# 鍏叡璁板繂姹?- T2浼樺寲鐗堟湰锛屼娇鐢ㄎ?digest鏋舵瀯
public_memory_pool = MemoryPool()  # 浼樺寲鐨勮蹇嗘睜锛屾敮鎸佸閲忔憳瑕佸拰token鎺у埗

# 鎺ㄧ悊鑳藉姏璇勪及鍣?
game_evaluator = None  # 灏嗗湪娓告垙寮€濮嬫椂鍒濆鍖?

# 12涓帺瀹堕厤缃?
PLAYERS = [
    {"id": 0, "role": "鐙间汉", "emoji": "馃惡", "color": "#f44336", "alive": True},
    {"id": 1, "role": "鐙间汉", "emoji": "馃惡", "color": "#f44336", "alive": True},
    {"id": 2, "role": "鐙肩帇", "emoji": "馃憫", "color": "#d32f2f", "alive": True},
    {"id": 3, "role": "鐙间汉", "emoji": "馃惡", "color": "#f44336", "alive": True},
    {"id": 4, "role": "鏉戞皯", "emoji": "馃懆鈥嶐煂?, "color": "#4CAF50", "alive": True},
    {"id": 5, "role": "鏉戞皯", "emoji": "馃懆鈥嶐煂?, "color": "#4CAF50", "alive": True},
    {"id": 6, "role": "鏉戞皯", "emoji": "馃懆鈥嶐煂?, "color": "#4CAF50", "alive": True},
    {"id": 7, "role": "鏉戞皯", "emoji": "馃懆鈥嶐煂?, "color": "#4CAF50", "alive": True},  # 琚祴璇曡€?
    {"id": 8, "role": "棰勮█瀹?, "emoji": "馃憗锔?, "color": "#2196F3", "alive": True},
    {"id": 9, "role": "濂冲帆", "emoji": "馃И", "color": "#9C27B0", "alive": True},
    {"id": 10, "role": "鐚庝汉", "emoji": "馃徆", "color": "#FF9800", "alive": True},
    {"id": 11, "role": "瀹堝崼", "emoji": "馃洝锔?, "color": "#00BCD4", "alive": True},
]

TEST_SUBJECT_ID = 7


def sync_game_state(phase=None, round_num=None):
    """Keep the exported game_state structure in sync for evaluators."""
    global game_state

    if phase is not None:
        game_state["phase"] = phase
    if round_num is not None:
        game_state["round"] = round_num

    game_state["players"] = [copy.deepcopy(player) for player in PLAYERS]
    game_state["alive_players"] = sum(1 for player in PLAYERS if player.get("alive", True))
    game_state["dead_players"] = [player["id"] for player in PLAYERS if not player.get("alive", True)]
    game_state["wolf_num"] = sum(
        1
        for player in PLAYERS
        if player.get("alive", True) and player.get("role") in ["鐙间汉", "鐙肩帇"]
    )
    game_state["total_players"] = len(PLAYERS)


def build_bilingual_reasoning_guidance(round_num):
    """Return deep reasoning reminders for the evaluation subject."""
    return (
        "\n[Deep Reasoning Guidance]\n"
        "- Mention at least two plausible wolf-team combinations (use combinatorics such as C(12,4)=495) and explain why each is viable or eliminated.\n"
        "- Provide probability/Bayesian updates, e.g., 'If Player 2 is real seer, P(Player 10 is wolf) ~0.8; otherwise ~0.3'.\n"
        "- Highlight new information from this round (vote pattern, counter-claims, night deaths) and describe the search/pruning strategy for the next steps.\n"
        "- Conclude with your alignment judgement and intended vote target, e.g., 'Final vote target: Player X'.\n"
    )


def build_bilingual_vote_guidance():
    """Return voting-stage reminders for the evaluation subject."""
    return (
        "\n[Deep Reasoning Voting Guidance]\n"
        "- Summarise in 1-2 sentences how vote patterns, role claims, and probabilities lead to your choice.\n"
        "- Output format:\n"
        "  ANALYSIS(CN): ...\n"
        "  ANALYSIS(EN): ...\n"
        "  FINAL VOTE: Player X\n"
    )

# Prompt鍚庣紑 - 瑕佹眰妯″瀷浣跨敤OUTPUT鍜孍ND鏍囪
OUTPUT_FORMAT_INSTRUCTION = """
OUTPUT FORMAT (mandatory):
- You may reason privately first, but the final message must follow the structure below.

OUTPUT: <final answer or decision>
END

Rules:
1. Only the content after 'OUTPUT:' is shared with other players.
2. Always finish with the token END on its own line.
3. If END is missing, the statement is considered invalid and must be regenerated.

Example:
Reasoning: Based on last night's deaths... Player 5's logic contains contradictions...
OUTPUT: Player 5 is likely a wolf; I recommend voting for them.
END"""

# LLM閰嶇疆 - 鏀寔涓ょ粍API閰嶇疆
def load_llm_config():
    """浠庢枃浠跺姞杞絃LM閰嶇疆"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"[CONFIG] Loaded from {CONFIG_FILE}")
                print(f"  Test API: {config.get('test_api_base')}")
                print(f"  NPC API:  {config.get('npc_api_base')}")
                return config
        except Exception as e:
            print(f"[CONFIG] Error loading {CONFIG_FILE}: {e}")

    # 榛樿閰嶇疆
    return {
        "test_api_base": "http://localhost:8080",
        "test_model": "/home/apulis-dev/userdata/Llama-3.3-70B-Instruct",
        "npc_api_base": "http://localhost:8080",
        "npc_model": "/home/apulis-dev/userdata/Llama-3.3-70B-Instruct",
        "temperature": 0.7,
        "max_tokens": 200
    }

def save_llm_config(config):
    """淇濆瓨LLM閰嶇疆鍒版枃浠?""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[CONFIG] Saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"[CONFIG] Error saving {CONFIG_FILE}: {e}")
        return False

# 鍔犺浇閰嶇疆
LLM_CONFIG = load_llm_config()

# Token浣跨敤闄愬埗鍜岀粺璁?
MAX_TOKENS_PER_PLAYER = 5000  # 姣忎釜鐜╁鏈€澶oken鏁?
total_tokens_used = 0  # 鎬籺oken浣跨敤閲?
player_tokens_used = {}  # 姣忎釜鐜╁鐨則oken浣跨敤閲?{player_id: tokens}

def validate_uls_code(uls_code):
    """
    楠岃瘉ULS++浠ｇ爜鏍煎紡鏄惁姝ｇ‘

    杩斿洖:
        dict: {"valid": bool, "errors": [], "parsed": {...}}
    """
    import re

    errors = []
    parsed = {}

    # 蹇呴』鍖呭惈PV:锛堟姇绁級
    if 'PV:' not in uls_code:
        errors.append("缂哄皯蹇呴渶鐨凱V:锛堟姇绁級瀛楁")
        return {"valid": False, "errors": errors, "parsed": parsed}

    # 瑙ｆ瀽鍚勪釜瀛楁
    try:
        # 瑙ｆ瀽PV锛圥rimary Vote锛?
        pv_match = re.search(r'PV:(\d+)', uls_code)
        if pv_match:
            parsed['primary_vote'] = int(pv_match.group(1))
        else:
            errors.append("PV鏍煎紡涓嶆纭?)

        # 瑙ｆ瀽SUS锛圫uspicion锛?
        sus_match = re.search(r'SUS:([^|]+)', uls_code)
        if sus_match:
            sus_str = sus_match.group(1)
            suspicions = []
            for sus_item in sus_str.split(','):
                if '@' in sus_item:
                    seat, score = sus_item.split('@')
                    suspicions.append({"seat": int(seat.strip()), "score": float(score.strip())})
            parsed['suspicions'] = suspicions

        # 瑙ｆ瀽EV锛圗vidence锛?
        ev_match = re.search(r'EV:([^|]+)', uls_code)
        if ev_match:
            ev_str = ev_match.group(1)
            evidences = [int(e.strip()) for e in ev_str.split(',') if e.strip()]
            parsed['evidences'] = evidences

        # 瑙ｆ瀽CL锛圕laim锛?
        cl_match = re.search(r'CL:([^|]+)', uls_code)
        if cl_match:
            parsed['claim'] = cl_match.group(1)

        # 鏍煎紡鍩烘湰姝ｇ‘
        is_valid = len(errors) == 0 and 'primary_vote' in parsed

        return {"valid": is_valid, "errors": errors, "parsed": parsed}

    except Exception as e:
        errors.append(f"瑙ｆ瀽閿欒: {str(e)}")
        return {"valid": False, "errors": errors, "parsed": parsed}

def call_llm_two_phase(prompt, player_id):
    """
    涓ら樁娈礚LM璋冪敤锛氭€濊€冮樁娈?+ 杈撳嚭闃舵

    杩斿洖:
        dict: {"thinking": "鎬濊€冭繃绋?, "uls_code": "PV:3|...", "tokens": int, "valid": bool}
    """
    global total_tokens_used, player_tokens_used

    try:
        # 閫夋嫨API閰嶇疆
        if player_id == 1:
            api_base = LLM_CONFIG['test_api_base']
            model = LLM_CONFIG['test_model']
        else:
            api_base = LLM_CONFIG['npc_api_base']
            model = LLM_CONFIG['npc_model']

        url = f"{api_base}/v1/chat/completions"

        # ============ 闃舵1锛氭€濊€冮樁娈?============
        thinking_prompt = prompt + """

**THINKING PHASE (鎬濊€冮樁娈?:**
璇峰厛鍒嗘瀽褰撳墠灞€鍔匡紝杩涜娣卞害鎺ㄧ悊銆備綘鍙互锛?
- 鍒椾妇鍙兘鐨勭嫾闃熺粍鍚堬紙缁勫悎鏁板锛?
- 璁＄畻鍚勭帺瀹舵槸鐙肩殑姒傜巼锛堣礉鍙舵柉鎺ㄧ悊锛?
- 鍒嗘瀽鍙戣█鐭涚浘鍜岄€昏緫婕忔礊
- 鎬濊€冩渶浼樼瓥鐣?

涓嶉渶瑕佽緭鍑轰换浣曠壒瀹氭牸寮忥紝鑷敱鎬濊€冨嵆鍙€?""

        print(f"[TWO-PHASE] Player {player_id} - Phase 1: Thinking...")

        thinking_payload = {
            "model": model,
            "messages": [{"role": "user", "content": thinking_prompt}],
            "temperature": 0.9,  # 楂樻俯搴︼紝榧撳姳鎺㈢储鎬ф€濊€?
            "max_tokens": 800    # 瓒冲鐨則oken杩涜娣卞害鎺ㄧ悊
        }

        thinking_response = requests.post(url, json=thinking_payload, timeout=45)
        thinking_response.raise_for_status()
        thinking_result = thinking_response.json()

        thinking_message = thinking_result["choices"][0]["message"]
        thinking_content = (thinking_message.get("content") or "").strip()
        if not thinking_content:
            thinking_content = (thinking_message.get("reasoning_content") or "").strip()

        print(f"[TWO-PHASE] Player {player_id} - Thinking complete ({len(thinking_content)} chars)")
        print(f"[TWO-PHASE] Thinking preview: {thinking_content[:200]}...")

        # ============ 闃舵2锛氳緭鍑洪樁娈?============
        output_prompt = f"""Based on your previous thinking:
{thinking_content}

**OUTPUT PHASE (杈撳嚭闃舵):**
Now output ONLY a strict ULS++ format line. NO explanation, NO text.

Format:
PV:<seat>[|ALT:<seat>][|SUS:<seat@score>,<seat@score>,<seat@score>][|EV:<卤id>,<卤id>][|CL:<role><卤><str>@N<round>]

Example: PV:3|SUS:3@4.6,5@3.7,7@2.1|EV:+205,-118|CL:S+4@N2

Output ONLY the ULS++ line:"""

        print(f"[TWO-PHASE] Player {player_id} - Phase 2: Generating ULS++ output...")

        output_payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": thinking_prompt},
                {"role": "assistant", "content": thinking_content},
                {"role": "user", "content": output_prompt}
            ],
            "temperature": 0.1,  # 浣庢俯搴︼紝纭繚鏍煎紡涓ユ牸
            "max_tokens": 150    # 鍙渶瑕佷竴琛孶LS++浠ｇ爜
        }

        output_response = requests.post(url, json=output_payload, timeout=30)
        output_response.raise_for_status()
        output_result = output_response.json()

        output_message = output_result["choices"][0]["message"]
        uls_code = (output_message.get("content") or "").strip()
        if not uls_code:
            uls_code = (output_message.get("reasoning_content") or "").strip()

        # 鎻愬彇绾疷LS++浠ｇ爜锛堝彲鑳芥贩鏈夊叾浠栨枃瀛楋級
        import re
        lines = uls_code.split('\n')
        uls_line = None
        for line in lines:
            line = line.strip()
            if any(marker in line for marker in ['PV:', 'CL:', 'N:', 'SUS:', 'EV:']):
                uls_line = line
                break

        if uls_line:
            uls_code = uls_line
        else:
            # 濡傛灉娌℃湁鎵惧埌锛屼娇鐢ㄧ涓€琛岄潪绌鸿
            for line in lines:
                if line.strip():
                    uls_code = line.strip()
                    break

        print(f"[TWO-PHASE] Player {player_id} - ULS++ code: {uls_code}")

        # ========== 楠岃瘉ULS++鏍煎紡 ==========
        validation = validate_uls_code(uls_code)
        if validation["valid"]:
            print(f"[TWO-PHASE] Player {player_id} - ULS++ validation: PASSED")
            print(f"[TWO-PHASE] Parsed data: {validation['parsed']}")
        else:
            print(f"[TWO-PHASE] Player {player_id} - ULS++ validation: FAILED")
            print(f"[TWO-PHASE] Errors: {validation['errors']}")

        # 缁熻token
        thinking_tokens = thinking_result.get("usage", {}).get("total_tokens", 0)
        output_tokens = output_result.get("usage", {}).get("total_tokens", 0)
        total_tokens = thinking_tokens + output_tokens

        total_tokens_used += total_tokens
        if player_id >= 0:
            if player_id not in player_tokens_used:
                player_tokens_used[player_id] = 0
            player_tokens_used[player_id] += total_tokens

        print(f"[TWO-PHASE] Player {player_id} - Total tokens: {total_tokens} (thinking: {thinking_tokens}, output: {output_tokens})")

        # 鍙戦€乼oken缁熻鍒板墠绔?
        dialogue_queue.put({
            "type": "token_update",
            "total_tokens": total_tokens_used,
            "player_tokens": dict(player_tokens_used)
        })

        return {
            "thinking": thinking_content,
            "uls_code": uls_code,
            "tokens": total_tokens,
            "valid": validation["valid"],
            "parsed": validation["parsed"]
        }

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[TWO-PHASE] Error for Player {player_id}:")
        print(f"  {type(e).__name__}: {e}")
        print(f"  Traceback:\n{error_details}")
        return {
            "thinking": f"[Error: {str(e)}]",
            "uls_code": "PV:1|SUS:1@0.0",
            "tokens": 0
        }

HTML_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>鐙间汉鏉€ - 4瀵硅瘽妗嗙増鏈?/title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            margin: 0;
            transition: background 1s;
        }

        body.night {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        }

        .container {
            max-width: 1800px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            color: white;
            font-size: 32px;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .status-info {
            text-align: center;
            color: white;
            font-size: 18px;
            margin-bottom: 20px;
            padding: 10px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
        }

        .controls {
            text-align: center;
            margin-bottom: 20px;
        }

        button {
            padding: 12px 30px;
            font-size: 16px;
            background: white;
            color: #667eea;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            margin: 0 10px;
            font-weight: bold;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transition: all 0.3s;
        }

        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.3);
        }

        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }

        .main-area {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }

        .circle-area {
            grid-column: 1 / -1;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            height: 300px;
        }

        .circle-container {
            position: relative;
            width: 100%;
            height: 100%;
        }

        .center-circle {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 100px;
            height: 100px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 20px;
            font-weight: bold;
            box-shadow: 0 8px 20px rgba(0,0,0,0.3);
        }

        .player-circle {
            position: absolute;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            background: white;
            border: 3px solid;
            cursor: pointer;
            transition: all 0.3s;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }

        .player-circle.hidden {
            opacity: 0.3;
            filter: brightness(0.5);
        }

        .player-circle.dead {
            opacity: 0.3;
            filter: grayscale(100%);
        }

        .player-circle.speaking {
            animation: pulse 1s infinite;
            border-width: 5px;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.8);
        }

        .player-circle.sheriff::after {
            content: '馃帠锔?;
            position: absolute;
            top: -5px;
            right: -5px;
            font-size: 16px;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }

        .player-name {
            font-size: 9px;
            font-weight: bold;
            margin-top: 2px;
        }

        .dialogue-panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 15px;
            height: 500px;
            display: flex;
            flex-direction: column;
        }

        .panel-header {
            font-size: 18px;
            font-weight: bold;
            color: #333;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 3px solid;
        }

        .panel-header.werewolf {
            border-bottom-color: #f44336;
            color: #f44336;
        }

        .panel-header.god {
            border-bottom-color: #2196F3;
            color: #2196F3;
        }

        .panel-header.day {
            border-bottom-color: #4CAF50;
            color: #4CAF50;
        }

        .panel-header.statistics {
            border-bottom-color: #FF9800;
            color: #FF9800;
        }

        .panel-output {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 8px;
        }

        .dialogue-item {
            margin-bottom: 15px;
            padding: 12px;
            background: white;
            border-radius: 8px;
            border-left: 4px solid;
            animation: slideIn 0.3s ease-out;
        }

        @keyframes slideIn {
            from {
                transform: translateX(-20px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        .dialogue-player {
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 6px;
        }

        .dialogue-content {
            color: #333;
            line-height: 1.5;
            font-size: 13px;
        }

        .dialogue-meta {
            color: #999;
            font-size: 11px;
            margin-top: 5px;
        }
    </style>
</head>
<body class="night">
    <div class="container">
        <h1>馃幃 鐙间汉鏉€ - 4瀵硅瘽妗嗙増鏈?/h1>

        <div class="status-info" id="status">
            鐘舵€侊細绛夊緟寮€濮?
        </div>

        <div class="status-info" id="token-stats" style="background: rgba(255, 152, 0, 0.2); font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 15px;">
            <span>馃敘 Token浣跨敤: 鎬昏 <span id="total-tokens">0</span></span>
            <span>|</span>
            <span>闄愬埗/鐜╁:
                <input type="number" id="token-limit-input" value="5000" min="100" max="100000"
                       style="width: 80px; padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px;">
            </span>
            <button onclick="updateTokenLimit()" style="padding: 4px 12px; font-size: 13px; cursor: pointer; border-radius: 4px; border: 1px solid #FF9800; background: white; color: #FF9800;">
                鉁?鏇存柊闄愬埗
            </button>
        </div>

        <div class="controls">
            <button onclick="startGame()" id="btn-start">鈻讹笍 寮€濮嬫父鎴?/button>
            <button onclick="stopGame()" id="btn-stop" disabled>鈴癸笍 鍋滄</button>
            <button onclick="toggleAutoMode()" id="btn-auto">馃攧 鍒囨崲涓鸿嚜鍔ㄦā寮?/button>
            <button onclick="toggleULSMode()" id="btn-uls">馃摑 鍒囨崲涓篣LS妯″紡</button>
            <button onclick="showConfigModal()" id="btn-config">鈿欙笍 閰嶇疆API</button>
            <button onclick="switchVersion('T0')" id="btn-version-t0" style="background: #FF9800; color: white;">馃搶 T0鐗堟湰</button>
            <button onclick="switchVersion('T1')" id="btn-version-t1" style="background: #4CAF50; color: white;">馃 T1鐗堟湰(褰撳墠)</button>
            <button onclick="testULSUnderstanding()" style="background: #2196F3; color: white;">馃И 娴嬭瘯ULS++鐞嗚В</button>
            <button onclick="nextDay()" id="btn-next" disabled>鈴笍 涓嬩竴澶?/button>
            <button onclick="showEvaluation()" id="btn-eval" style="background: #9C27B0; color: white;">馃搳 鏄剧ず璇勪及</button>
            <button onclick="toggleLanguage()" id="btn-lang">馃寪 English</button>
            <button onclick="clearAll()" id="btn-clear">馃棏锔?娓呯┖</button>
        </div>

        <!-- 闅惧害閫夋嫨鍣?-->
        <div class="difficulty-selector" style="text-align: center; margin: 20px 0; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 10px;">
            <h3 style="color: white; margin-bottom: 10px;">馃幃 閫夋嫨闅惧害绾у埆 Difficulty Level</h3>
            <button onclick="setDifficulty('鍩虹')" id="btn-diff-basic" class="difficulty-btn" style="background: #4CAF50; padding: 12px 24px; margin: 0 5px; border: none; border-radius: 5px; color: white; cursor: pointer; font-size: 14px; font-weight: bold;">
                馃摎 鍩虹 (2妯″潡)
            </button>
            <button onclick="setDifficulty('杩涢樁')" id="btn-diff-advanced" class="difficulty-btn" style="background: #FF9800; padding: 12px 24px; margin: 0 5px; border: none; border-radius: 5px; color: white; cursor: pointer; font-size: 14px; font-weight: bold; opacity: 0.6;">
                馃敟 杩涢樁 (3妯″潡)
            </button>
            <button onclick="setDifficulty('鍦扮嫳')" id="btn-diff-hell" class="difficulty-btn" style="background: #f44336; padding: 12px 24px; margin: 0 5px; border: none; border-radius: 5px; color: white; cursor: pointer; font-size: 14px; font-weight: bold; opacity: 0.6;">
                馃拃 鍦扮嫳 (4+妯″潡)
            </button>
            <div id="difficulty-info" style="color: white; margin-top: 10px; font-size: 14px;">
                褰撳墠闅惧害 Current: <span id="current-difficulty" style="font-weight: bold; color: #4CAF50;">鍩虹 Basic</span>
            </div>
        </div>

        <!-- API閰嶇疆妯℃€佺獥鍙?-->
        <div id="config-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 9999; justify-content: center; align-items: center;">
            <div style="background: white; padding: 30px; border-radius: 12px; max-width: 700px; width: 90%;">
                <h2 style="margin-top: 0; color: #333;">鈿欙笍 API閰嶇疆</h2>

                <!-- 娴嬭瘯妯″瀷閰嶇疆 -->
                <div style="margin-bottom: 25px; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #28a745;">
                    <h3 style="color: #28a745; font-size: 16px; margin-top: 0;">馃И 娴嬭瘯妯″瀷閰嶇疆 (Test Player)</h3>
                    <label style="display: block; margin-bottom: 8px; color: #666;">API Base URL:</label>
                    <input type="text" id="test-api-base" value="http://localhost:8080"
                           style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">

                    <label style="display: block; margin-top: 12px; margin-bottom: 8px; color: #666;">Model Path:</label>
                    <input type="text" id="test-model" value="/home/apulis-dev/userdata/Llama-3.3-70B-Instruct"
                           style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">
                </div>

                <!-- NPC妯″瀷閰嶇疆 -->
                <div style="margin-bottom: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
                    <h3 style="color: #667eea; font-size: 16px; margin-top: 0;">馃 NPC妯″瀷閰嶇疆 (11 NPC Players)</h3>
                    <label style="display: block; margin-bottom: 8px; color: #666;">API Base URL:</label>
                    <input type="text" id="npc-api-base" value="http://localhost:8080"
                           style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">

                    <label style="display: block; margin-top: 12px; margin-bottom: 8px; color: #666;">Model Path:</label>
                    <input type="text" id="npc-model" value="/home/apulis-dev/userdata/Llama-3.3-70B-Instruct"
                           style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">
                </div>

                <div style="margin-top: 30px; display: flex; justify-content: flex-end; gap: 10px;">
                    <button onclick="closeConfigModal()" style="padding: 10px 20px; border: 1px solid #ddd; background: white; border-radius: 6px; cursor: pointer;">鍙栨秷</button>
                    <button onclick="saveConfig()" style="padding: 10px 20px; border: none; background: #667eea; color: white; border-radius: 6px; cursor: pointer;">淇濆瓨閰嶇疆</button>
                </div>
            </div>
        </div>

        <div class="circle-area">
            <div class="circle-container" id="circle-container">
                <div class="center-circle">
                    馃惡<br>鐙间汉鏉€
                </div>
            </div>
        </div>

        <div class="main-area">
            <div class="dialogue-panel">
                <div class="panel-header werewolf">馃惡 澶滄櫄 - 鐙间汉瀵硅瘽</div>
                <div class="panel-output" id="werewolf-output">
                    <div style="color: #999; text-align: center; padding: 20px;">
                        绛夊緟鐙间汉琛屽姩...
                    </div>
                </div>
            </div>

            <div class="dialogue-panel">
                <div class="panel-header god">鉁?澶滄櫄 - 绁炶亴琛屽姩</div>
                <div class="panel-output" id="god-output">
                    <div style="color: #999; text-align: center; padding: 20px;">
                        绛夊緟绁炶亴琛屽姩...
                    </div>
                </div>
            </div>

            <div class="dialogue-panel">
                <div class="panel-header day">鈽€锔?鐧藉ぉ - 璁ㄨ鎶曠エ</div>
                <div class="panel-output" id="day-output">
                    <div style="color: #999; text-align: center; padding: 20px;">
                        绛夊緟鐧藉ぉ璁ㄨ...
                    </div>
                </div>
            </div>

            <div class="dialogue-panel">
                <div class="panel-header statistics">馃搳 瀹炴椂缁熻</div>
                <div class="panel-output" id="statistics-output">
                    <div id="difficulty-modules-display" style="margin-bottom: 15px; padding: 10px; background: rgba(76, 175, 80, 0.1); border-left: 4px solid #4CAF50; border-radius: 4px;">
                        <h4 style="margin: 0 0 8px 0; color: #4CAF50; font-size: 14px;">馃拵 婵€娲荤殑闅惧害妯″潡 Activated Modules</h4>
                        <div id="modules-list" style="font-size: 12px; color: #ddd;">
                            <span style="color: #888;">绛夊緟娓告垙寮€濮?.. Waiting for game start...</span>
                        </div>
                    </div>
                    <div style="color: #999; text-align: center; padding: 20px;">
                        绛夊緟娓告垙寮€濮?..
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const players = {{ players | tojson }};
        let eventSource = null;
        let currentPhase = 'night';
        let autoMode = true;  // 榛樿鑷姩妯″紡
        let ulsMode = true;  // 榛樿ULS妯″紡
        let currentLang = 'zh';  // 榛樿涓枃

        // 缈昏瘧瀛楀吀
        const translations = {
            zh: {
                title: '鐙间汉鏉€ - 4瀵硅瘽妗嗙増鏈?,
                status: '鐘舵€侊細',
                startGame: '鈻讹笍 寮€濮嬫父鎴?,
                stopGame: '鈴癸笍 鍋滄',
                autoModeManual: '馃攧 鍒囨崲涓鸿嚜鍔ㄦā寮?,
                autoModeAuto: '馃攣 鍒囨崲涓烘墜鍔ㄦā寮?,
                nextDay: '鈴笍 涓嬩竴澶?,
                clearAll: '馃棏锔?娓呯┖',
                langSwitch: '馃寪 English',
                waitingStart: '绛夊緟寮€濮?,
                werewolfPanel: '馃惡 澶滄櫄 - 鐙间汉瀵硅瘽',
                godPanel: '鉁?澶滄櫄 - 绁炶亴琛屽姩',
                dayPanel: '鈽€锔?鐧藉ぉ - 璁ㄨ鎶曠エ',
                statsPanel: '馃搳 瀹炴椂缁熻',
                waitingWerewolf: '绛夊緟鐙间汉琛屽姩...',
                waitingGod: '绛夊緟绁炶亴琛屽姩...',
                waitingDay: '绛夊緟鐧藉ぉ璁ㄨ...',
                waitingGame: '绛夊緟娓告垙寮€濮?..'
            },
            en: {
                title: 'Werewolf - 4 Panel Version',
                status: 'Status: ',
                startGame: '鈻讹笍 Start Game',
                stopGame: '鈴癸笍 Stop',
                autoModeManual: '馃攧 Switch to Auto',
                autoModeAuto: '馃攣 Switch to Manual',
                nextDay: '鈴笍 Next Day',
                clearAll: '馃棏锔?Clear',
                langSwitch: '馃寪 涓枃',
                waitingStart: 'Waiting to start',
                werewolfPanel: '馃惡 Night - Werewolf Chat',
                godPanel: '鉁?Night - God Roles',
                dayPanel: '鈽€锔?Day - Discussion & Voting',
                statsPanel: '馃搳 Real-time Stats',
                waitingWerewolf: 'Waiting for werewolves...',
                waitingGod: 'Waiting for god roles...',
                waitingDay: 'Waiting for day discussion...',
                waitingGame: 'Waiting for game start...'
            }
        };

        function t(key) {
            return translations[currentLang][key] || key;
        }

        function createCircle() {
            const container = document.getElementById('circle-container');
            const centerX = container.offsetWidth / 2;
            const centerY = container.offsetHeight / 2;
            const radius = Math.min(centerX, centerY) - 50;

            players.forEach((player, index) => {
                const angle = (index / players.length) * 2 * Math.PI - Math.PI / 2;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);

                const div = document.createElement('div');
                div.className = 'player-circle';
                div.id = 'player-' + player.id;
                div.style.left = (x - 30) + 'px';
                div.style.top = (y - 30) + 'px';
                div.style.borderColor = player.color;
                div.innerHTML = player.emoji + '<div class="player-name">P' + player.id + '</div>';

                container.appendChild(div);
            });
        }

        function setPhase(phase) {
            currentPhase = phase;
            document.body.className = phase;
        }

        function hidePlayer(playerId) {
            const player = document.getElementById('player-' + playerId);
            if (player) player.classList.add('hidden');
        }

        function showPlayer(playerId) {
            const player = document.getElementById('player-' + playerId);
            if (player) player.classList.remove('hidden');
        }

        function markDead(playerId) {
            const player = document.getElementById('player-' + playerId);
            if (player) player.classList.add('dead');
        }

        function highlightPlayer(playerId) {
            document.querySelectorAll('.player-circle').forEach(el => {
                el.classList.remove('speaking');
            });

            const player = document.getElementById('player-' + playerId);
            if (player) player.classList.add('speaking');
        }

        function updateSheriff(playerId) {
            document.querySelectorAll('.player-circle').forEach(el => {
                el.classList.remove('sheriff');
            });

            const player = document.getElementById('player-' + playerId);
            if (player) player.classList.add('sheriff');
        }

        function addDialogue(data) {
            // 鏍规嵁瀵硅瘽绫诲瀷璺敱鍒颁笉鍚岀殑闈㈡澘
            let outputId;

            if (data.panel === 'werewolf') {
                outputId = 'werewolf-output';
            } else if (data.panel === 'god') {
                outputId = 'god-output';
            } else if (data.panel === 'statistics') {
                outputId = 'statistics-output';
            } else {
                outputId = 'day-output';
            }

            const output = document.getElementById(outputId);

            if (output.innerHTML.includes('绛夊緟')) {
                output.innerHTML = '';
            }

            const item = document.createElement('div');
            item.className = 'dialogue-item';

            if (data.player_id === -1) {
                item.style.borderLeftColor = '#667eea';
                item.style.background = '#f0f4ff';

                const contentDiv = document.createElement('div');
                contentDiv.className = 'dialogue-content';
                contentDiv.style.fontWeight = 'bold';
                contentDiv.style.color = '#667eea';
                contentDiv.style.whiteSpace = 'pre-wrap';  // 淇濈暀鎹㈣鍜岀┖鏍?
                contentDiv.textContent = data.content;

                item.appendChild(contentDiv);
                output.insertBefore(item, output.firstChild);
                return;
            }

            const player = players[data.player_id];
            item.style.borderLeftColor = player.color;

            const playerDiv = document.createElement('div');
            playerDiv.className = 'dialogue-player';
            playerDiv.style.color = player.color;

            // 鍙湪鐙间汉/绁炶亴闈㈡澘鏄剧ず瑙掕壊锛岀櫧澶╅潰鏉夸笉鏄剧ず
            if (data.panel === 'werewolf' || data.panel === 'god') {
                playerDiv.textContent = player.emoji + ' Player ' + player.id + ' (' + player.role + ')';
            } else {
                playerDiv.textContent = player.emoji + ' Player ' + player.id;
            }

            const contentDiv = document.createElement('div');
            contentDiv.className = 'dialogue-content';

            const metaDiv = document.createElement('div');
            metaDiv.className = 'dialogue-meta';
            metaDiv.textContent = (data.phase || '') + ' | ' + new Date().toLocaleTimeString();

            item.appendChild(playerDiv);

            // ========== ULS++妯″紡鐗规畩澶勭悊 ==========
            if (data.uls_mode && data.thinking) {
                // 鍒涘缓鎬濊€冮潰鏉匡紙鍙姌鍙狅級
                const thinkingContainer = document.createElement('details');
                thinkingContainer.style.cssText = 'margin: 8px 0; background: rgba(255, 255, 255, 0.05); border-radius: 5px; padding: 8px;';

                const thinkingSummary = document.createElement('summary');
                thinkingSummary.style.cssText = 'cursor: pointer; font-weight: bold; color: #4a90e2; font-size: 13px;';
                thinkingSummary.innerHTML = '馃 鎬濊€冭繃绋?(Thinking Process) - 鐐瑰嚮灞曞紑';

                const thinkingContent = document.createElement('div');
                thinkingContent.style.cssText = 'margin-top: 8px; padding: 10px; background: rgba(0, 0, 0, 0.1); border-radius: 4px; font-size: 13px; line-height: 1.6; white-space: pre-wrap; color: #ccc;';
                thinkingContent.textContent = data.thinking;

                thinkingContainer.appendChild(thinkingSummary);
                thinkingContainer.appendChild(thinkingContent);
                item.appendChild(thinkingContainer);

                // ULS++浠ｇ爜鏄剧ず锛堥珮浜級
                const ulsCodeDiv = document.createElement('div');
                ulsCodeDiv.style.cssText = 'margin: 8px 0; padding: 12px; background: rgba(76, 175, 80, 0.15); border: 2px solid #4CAF50; border-radius: 6px; font-family: "Courier New", monospace; font-size: 14px; font-weight: bold; color: #4CAF50;';
                ulsCodeDiv.innerHTML = '<div style="font-size: 11px; color: #81C784; margin-bottom: 4px;">馃摑 ULS++ CODE:</div>' + data.content;
                item.appendChild(ulsCodeDiv);
            } else {
                // 姝ｅ父妯″紡锛氱洿鎺ユ樉绀哄唴瀹?
                item.appendChild(contentDiv);

                // Typewriter effect
                const text = data.content;
                let index = 0;

                function typeChar() {
                    if (index < text.length) {
                        contentDiv.textContent += text[index];
                        index++;
                        setTimeout(typeChar, 20);
                    }
                }

                typeChar();
            }

            item.appendChild(metaDiv);
            output.insertBefore(item, output.firstChild);
        }

        function startGame() {
            document.getElementById('btn-start').disabled = true;
            document.getElementById('btn-stop').disabled = false;

            fetch('/api/start', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    console.log('Started:', data);
                    startEventStream();
                    // 鍚敤璇勪及鎸夐挳
                    document.getElementById('btn-eval').disabled = false;
                });
        }

        function stopGame() {
            document.getElementById('btn-start').disabled = false;
            document.getElementById('btn-stop').disabled = true;

            fetch('/api/stop', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;
                    }
                });
        }

        function updateUI() {
            // 鏇存柊鏍囬
            const h1 = document.querySelector('h1');
            if (h1) h1.textContent = '馃幃 ' + t('title');

            // 鏇存柊鐘舵€佹枃鏈墠缂€锛堜繚鐣欏悗闈㈢殑鍔ㄦ€佸唴瀹癸級
            const statusEl = document.getElementById('status');
            if (statusEl) {
                const statusText = statusEl.textContent;
                if (statusText.includes('锛?) || statusText.includes(': ')) {
                    const parts = statusText.split(/锛殀: /);
                    if (parts.length > 1) {
                        statusEl.textContent = t('status') + parts[1];
                    } else {
                        statusEl.textContent = t('status') + t('waitingStart');
                    }
                }
            }

            // 鏇存柊鎸夐挳
            const btnStart = document.getElementById('btn-start');
            const btnStop = document.getElementById('btn-stop');
            const btnAuto = document.getElementById('btn-auto');
            const btnNext = document.getElementById('btn-next');
            const btnLang = document.getElementById('btn-lang');
            const btnClear = document.getElementById('btn-clear');

            if (btnStart) btnStart.textContent = t('startGame');
            if (btnStop) btnStop.textContent = t('stopGame');
            if (btnAuto) btnAuto.textContent = autoMode ? t('autoModeAuto') : t('autoModeManual');
            if (btnNext) btnNext.textContent = t('nextDay');
            if (btnLang) btnLang.textContent = t('langSwitch');
            if (btnClear) btnClear.textContent = t('clearAll');

            // 鏇存柊闈㈡澘鏍囬
            const panelHeaders = document.querySelectorAll('.panel-header');
            if (panelHeaders[0]) panelHeaders[0].textContent = t('werewolfPanel');
            if (panelHeaders[1]) panelHeaders[1].textContent = t('godPanel');
            if (panelHeaders[2]) panelHeaders[2].textContent = t('dayPanel');
            if (panelHeaders[3]) panelHeaders[3].textContent = t('statsPanel');

            // 鏇存柊鍗犱綅鏂囨湰
            const panels = [
                {id: 'werewolf-output', key: 'waitingWerewolf'},
                {id: 'god-output', key: 'waitingGod'},
                {id: 'day-output', key: 'waitingDay'},
                {id: 'statistics-output', key: 'waitingGame'}
            ];

            panels.forEach(panel => {
                const el = document.getElementById(panel.id);
                if (el.textContent.includes('绛夊緟') || el.textContent.includes('Waiting')) {
                    el.innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">' + t(panel.key) + '</div>';
                }
            });
        }

        function toggleLanguage() {
            currentLang = currentLang === 'zh' ? 'en' : 'zh';
            updateUI();
        }

        async function testULSUnderstanding() {
            const existingModal = document.getElementById('uls-test-modal');
            if (existingModal) {
                existingModal.style.display = 'flex';
                const contentDiv = existingModal.querySelector('.uls-test-content');
                contentDiv.innerHTML = '<div style="text-align: center; padding: 20px;"><div style="font-size: 16px;">鈴?Testing LLM understanding...</div></div>';
            } else {
                const modal = document.createElement('div');
                modal.id = 'uls-test-modal';
                modal.style.cssText = 'display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 9999; justify-content: center; align-items: center;';
                modal.innerHTML = '<div style="background: white; padding: 30px; border-radius: 12px; max-width: 700px; width: 90%; max-height: 80%; overflow-y: auto;"><h2 style="margin-top: 0; color: #333;">馃И ULS++ Understanding Test 娴嬭瘯缁撴灉</h2><div class="uls-test-content" style="max-height: 400px; overflow-y: auto; margin: 15px 0;"><div style="text-align: center; padding: 20px;"><div style="font-size: 16px;">鈴?Testing LLM understanding...</div></div></div><div style="text-align: right; margin-top: 20px;"><button onclick="hideULSTestResult()" style="padding: 10px 20px; background: #666; color: white; border: none; border-radius: 5px; cursor: pointer;">Close 鍏抽棴</button></div></div>';
                document.body.appendChild(modal);
            }

            try {
                const response = await fetch('/api/test_uls_understanding', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                const modal = document.getElementById('uls-test-modal');
                const contentDiv = modal.querySelector('.uls-test-content');

                if (response.ok) {
                    const data = await response.json();

                    if (data.status === 'ok') {
                        contentDiv.innerHTML = `
                            <div style="background: rgba(74, 144, 226, 0.1); padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                                <h4 style="color: #4a90e2; margin-bottom: 10px;">鉁?Test Completed 娴嬭瘯瀹屾垚</h4>
                            </div>

                            <div style="background: rgba(255, 255, 255, 0.05); padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                                <h4 style="color: #4a90e2; margin-bottom: 10px;">馃 LLM's Answer LLM鍥炵瓟锛?/h4>
                                <div style="white-space: pre-wrap; line-height: 1.6; background: rgba(0, 0, 0, 0.05); padding: 10px; border-radius: 3px;">${data.llm_answer}</div>
                            </div>

                            <div style="background: rgba(76, 175, 80, 0.1); padding: 15px; border-radius: 5px; border-left: 4px solid #4caf50;">
                                <h4 style="color: #4caf50; margin-bottom: 10px;">鉁?Correct Answers 姝ｇ‘绛旀锛?/h4>
                                <div style="line-height: 1.8;">
                                    <div><strong>闂1:</strong> ${data.correct_answers.q1}</div>
                                    <div><strong>闂2:</strong> ${data.correct_answers.q2}</div>
                                    <div><strong>闂3:</strong> ${data.correct_answers.q3}</div>
                                </div>
                            </div>

                            <details style="margin-top: 15px; background: rgba(255, 255, 255, 0.03); padding: 10px; border-radius: 5px;">
                                <summary style="cursor: pointer; font-weight: bold; color: #888;">鏌ョ湅娴嬭瘯鐢ㄧ殑Prompt</summary>
                                <div style="white-space: pre-wrap; margin-top: 10px; line-height: 1.4; font-size: 13px; color: #666;">${data.test_prompt}</div>
                            </details>
                        `;
                    } else {
                        contentDiv.innerHTML = `<div style="color: #ff4444; padding: 20px;">鉂?Error: ${data.message}</div>`;
                    }
                } else {
                    contentDiv.innerHTML = `<div style="color: #ff4444; padding: 20px;">鉂?Server error: ${response.status}</div>`;
                }
            } catch (error) {
                const modal = document.getElementById('uls-test-modal');
                const contentDiv = modal.querySelector('.uls-test-content');
                contentDiv.innerHTML = `<div style="color: #ff4444; padding: 20px;">鉂?Network error: ${error.message}</div>`;
            }
        }

        function hideULSTestResult() {
            const modal = document.getElementById('uls-test-modal');
            if (modal) {
                modal.style.display = 'none';
            }
        }

        function toggleAutoMode() {
            autoMode = !autoMode;
            const btn = document.getElementById('btn-auto');

            if (autoMode) {
                btn.textContent = t('autoModeAuto');
                btn.style.background = '#4CAF50';
                btn.style.color = 'white';
            } else {
                btn.textContent = t('autoModeManual');
                btn.style.background = 'white';
                btn.style.color = '#667eea';
            }

            // 閫氱煡鍚庣妯″紡鏀瑰彉
            fetch('/api/set_auto_mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({auto_mode: autoMode})
            })
            .then(response => response.json())
            .then(data => {
                console.log('Auto mode:', data);

                // 濡傛灉鍒囨崲鍒拌嚜鍔ㄦā寮忎笖姝ｅ湪绛夊緟锛岃嚜鍔ㄧ户缁?
                if (autoMode && !document.getElementById('btn-next').disabled) {
                    nextDay();
                }
            });
        }

        function toggleULSMode() {
            ulsMode = !ulsMode;
            const btn = document.getElementById('btn-uls');

            if (ulsMode) {
                btn.textContent = '馃摑 ULS妯″紡 (宸插惎鐢?';
                btn.style.background = '#2196F3';
                btn.style.color = 'white';
            } else {
                btn.textContent = '馃摑 鍒囨崲涓篣LS妯″紡';
                btn.style.background = 'white';
                btn.style.color = 'black';
            }

            // 鍚戞湇鍔″櫒鍚屾ULS妯″紡鐘舵€?
            fetch('/api/set_uls_mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({uls_mode: ulsMode})
            })
            .then(response => response.json())
            .then(data => {
                console.log('ULS mode:', data);
            });
        }

        function showConfigModal() {
            // 浠庢湇鍔″櫒鍔犺浇褰撳墠閰嶇疆
            fetch('/api/get_llm_config')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'ok' && data.config) {
                        document.getElementById('test-api-base').value = data.config.test_api_base || '';
                        document.getElementById('test-model').value = data.config.test_model || '';
                        document.getElementById('npc-api-base').value = data.config.npc_api_base || '';
                        document.getElementById('npc-model').value = data.config.npc_model || '';
                    }
                })
                .catch(error => console.error('Error loading config:', error));

            const modal = document.getElementById('config-modal');
            modal.style.display = 'flex';
        }

        function closeConfigModal() {
            const modal = document.getElementById('config-modal');
            modal.style.display = 'none';
        }

        function saveConfig() {
            const testApiBase = document.getElementById('test-api-base').value;
            const testModel = document.getElementById('test-model').value;
            const npcApiBase = document.getElementById('npc-api-base').value;
            const npcModel = document.getElementById('npc-model').value;

            fetch('/api/set_llm_config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    test_api_base: testApiBase,
                    test_model: testModel,
                    npc_api_base: npcApiBase,
                    npc_model: npcModel
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Config updated:', data);
                alert('API閰嶇疆宸叉洿鏂帮紒\\n\\n娴嬭瘯妯″瀷: ' + testApiBase + '\\nNPC妯″瀷: ' + npcApiBase);
                closeConfigModal();
            })
            .catch(error => {
                console.error('Error updating config:', error);
                alert('閰嶇疆鏇存柊澶辫触锛岃閲嶈瘯');
            });
        }

        function updateTokenLimit() {
            const newLimit = parseInt(document.getElementById('token-limit-input').value);

            if (newLimit < 100 || newLimit > 100000) {
                alert('Token闄愬埗蹇呴』鍦?00鍒?00000涔嬮棿');
                return;
            }

            fetch('/api/set_token_limit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({token_limit: newLimit})
            })
            .then(response => response.json())
            .then(data => {
                console.log('Token limit updated:', data);
                alert('Token闄愬埗宸叉洿鏂颁负: ' + newLimit + '/鐜╁');
            })
            .catch(error => {
                console.error('Error updating token limit:', error);
                alert('鏇存柊澶辫触锛岃閲嶈瘯');
            });
        }

        function nextDay() {
            document.getElementById('btn-next').disabled = true;

            fetch('/api/next_day', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    console.log('Next day:', data);
                });
        }

        async function switchVersion(version) {
            if (confirm('纭畾瑕佸垏鎹㈠埌' + version + '鐗堟湰鍚?\\n\\nT0鐗堟湰: 鍩虹鐗堟湰\\nT1鐗堟湰: 澧炲己鐗堟湰(鍚叕鍏辫蹇嗘睜鍜屾帹鐞嗘姇绁?\\n\\n鍒囨崲鍚庨〉闈㈠皢鑷姩鍒锋柊銆?)) {
                try {
                    const response = await fetch('/api/switch_version', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ version: version })
                    });
                    const data = await response.json();
                    alert(data.message + '\\n\\n椤甸潰灏嗗湪2绉掑悗鑷姩鍒锋柊銆?);
                    setTimeout(() => location.reload(), 2000);
                } catch (error) {
                    alert('鍒囨崲鐗堟湰澶辫触: ' + error.message);
                }
            }
        }

        function clearAll() {
            document.getElementById('werewolf-output').innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">绛夊緟鐙间汉琛屽姩...</div>';
            document.getElementById('god-output').innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">绛夊緟绁炶亴琛屽姩...</div>';
            document.getElementById('day-output').innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">绛夊緟鐧藉ぉ璁ㄨ...</div>';
            document.getElementById('statistics-output').innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">绛夊緟娓告垙寮€濮?..</div>';
        }

        // 璇勪及鍔熻兘
        function showEvaluation() {
            fetch('/api/get_evaluation')
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'ok') {
                        displayEvaluationModal(data.evaluation);
                    } else {
                        // 鏄剧ず璇︾粏閿欒淇℃伅
                        displayErrorModal(data.message, data.debug_info);
                    }
                })
                .catch(error => {
                    displayErrorModal('缃戠粶璇锋眰澶辫触: ' + error.message, {error_type: 'Network Error'});
                });
        }

        function displayErrorModal(message, debug_info) {
            const modal = document.createElement('div');
            modal.id = 'error-modal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; display: flex; justify-content: center; align-items: center;';

            let debug_html = '';
            if (debug_info) {
                debug_html = `
                    <div style="background: #fff3cd; padding: 15px; border-radius: 5px; margin-top: 15px; border-left: 4px solid #ff9800;">
                        <strong>璋冭瘯淇℃伅:</strong>
                        <pre style="margin: 10px 0; white-space: pre-wrap; word-wrap: break-word; font-size: 12px;">
${JSON.stringify(debug_info, null, 2)}
                        </pre>
                    </div>
                `;
            }

            const content = `
                <div style="background: white; padding: 30px; border-radius: 12px; max-width: 700px; width: 90%;">
                    <h2 style="color: #d32f2f; margin-top: 0;">鉂?璇勪及澶辫触</h2>
                    <div style="background: #ffebee; padding: 15px; border-radius: 5px; border-left: 4px solid #d32f2f; margin-bottom: 20px;">
                        <p style="margin: 0; color: #c62828; white-space: pre-wrap; word-wrap: break-word;">
${message}
                        </p>
                    </div>
                    ${debug_html}
                    <div style="text-align: center; margin-top: 20px;">
                        <button onclick="closeErrorModal()" style="background: #d32f2f; color: white; border: none; padding: 12px 30px; border-radius: 5px; cursor: pointer; font-size: 16px;">鍏抽棴</button>
                    </div>
                </div>
            `;

            modal.innerHTML = content;
            document.body.appendChild(modal);
        }

        function closeErrorModal() {
            const modal = document.getElementById('error-modal');
            if (modal) modal.remove();
        }

        function displayEvaluationModal(evaluation) {
            const modal = document.createElement('div');
            modal.id = 'eval-modal';
            modal.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); z-index: 10000; display: flex; justify-content: center; align-items: center;';

            // Check if this is enhanced evaluation with deep reasoning
            const isEnhanced = evaluation.comprehensive_score && evaluation.traditional_metrics && evaluation.deep_reasoning_metrics;

            const content = isEnhanced ? `
                <div style="background: white; padding: 30px; border-radius: 12px; max-width: 1100px; max-height: 90vh; overflow-y: auto; width: 95%;">
                    <h2 style="color: #333; margin-top: 0;">馃搳 澧炲己鍨嬫繁搴︽帹鐞嗚兘鍔涜瘎浼版姤鍛?/h2>
                    <p style="color: #666; font-size: 14px;">Enhanced Deep Reasoning Evaluation</p>

                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 8px; text-align: center; margin: 20px 0;">
                        <div style="font-size: 52px; font-weight: bold; margin: 10px 0;">${evaluation.comprehensive_score.overall_score}/100</div>
                        <div style="font-size: 26px; font-weight: bold; margin: 10px 0;">${evaluation.comprehensive_score.grade}</div>
                        <div style="font-size: 14px; opacity: 0.9; margin-top: 15px;">
                            浼犵粺鎸囨爣璐＄尞: ${evaluation.comprehensive_score.traditional_contribution} (40%) |
                            娣卞害鎺ㄧ悊璐＄尞: ${evaluation.comprehensive_score.deep_reasoning_contribution} (60%)
                        </div>
                    </div>

                    <div style="background: #f0f4ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #667eea; margin-top: 0;">馃 娣卞害鎺ㄧ悊缁村害 (Deep Reasoning - 60% 鏉冮噸)</h3>
                        <p style="color: #666; font-size: 13px; margin-bottom: 15px;">璇勪及鍦╰rillions of combinations闂绌洪棿涓殑鏁板鎺ㄧ悊鑳藉姏</p>
                        ${generateDeepReasoningScores(evaluation.deep_reasoning_metrics)}
                    </div>

                    <div style="background: #fff9e6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #ff9800; margin-top: 0;">馃搵 浼犵粺璇勪及缁村害 (Traditional - 40% 鏉冮噸)</h3>
                        ${generateDimensionScores(evaluation.traditional_metrics.scores)}
                    </div>

                    <div style="margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px;">
                        <strong>缁熻鏁版嵁:</strong><br>
                        鍙戣█娆℃暟: ${evaluation.stats.speeches || 0}娆?|
                        鎶曠エ娆℃暟: ${evaluation.stats.votes || 0}娆?|
                        绔欒竟鍙樺寲: ${evaluation.stats.side_changes || 0}娆?
                    </div>

                    <div style="text-align: center; margin-top: 20px;">
                        <button onclick="closeEvalModal()" style="background: #667eea; color: white; border: none; padding: 12px 30px; border-radius: 5px; cursor: pointer; font-size: 16px;">鍏抽棴</button>
                        <button onclick="exportEvaluation()" style="background: #4CAF50; color: white; border: none; padding: 12px 30px; border-radius: 5px; cursor: pointer; font-size: 16px; margin-left: 10px;">馃搫 瀵煎嚭JSON</button>
                    </div>
                </div>
            ` : `
                <div style="background: white; padding: 30px; border-radius: 12px; max-width: 900px; max-height: 80vh; overflow-y: auto; width: 90%;">
                    <h2 style="color: #333; margin-top: 0;">馃搳 鎺ㄧ悊鑳藉姏璇勪及鎶ュ憡</h2>

                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                        <div style="font-size: 48px; font-weight: bold; margin: 10px 0;">${evaluation.weighted_score}/100</div>
                        <div style="font-size: 24px; font-weight: bold;">${evaluation.final_grade}</div>
                    </div>

                    <h3 style="color: #333;">鍚勭淮搴﹀緱鍒?</h3>
                    ${generateDimensionScores(evaluation.scores)}

                    <div style="margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 8px;">
                        <strong>缁熻鏁版嵁:</strong><br>
                        鍙戣█娆℃暟: ${evaluation.stats.speeches || 0}娆?|
                        鎶曠エ娆℃暟: ${evaluation.stats.votes || 0}娆?|
                        绔欒竟鍙樺寲: ${evaluation.stats.side_changes || 0}娆?
                    </div>

                    <div style="text-align: center; margin-top: 20px;">
                        <button onclick="closeEvalModal()" style="background: #667eea; color: white; border: none; padding: 12px 30px; border-radius: 5px; cursor: pointer; font-size: 16px;">鍏抽棴</button>
                        <button onclick="exportEvaluation()" style="background: #4CAF50; color: white; border: none; padding: 12px 30px; border-radius: 5px; cursor: pointer; font-size: 16px; margin-left: 10px;">馃搫 瀵煎嚭JSON</button>
                    </div>
                </div>
            `;

            modal.innerHTML = content;
            document.body.appendChild(modal);
        }

        function generateDimensionScores(scores) {
            const dimensions = {
                'information_extraction': '淇℃伅鎻愬彇鑳藉姏',
                'logical_deduction': '閫昏緫鎺ㄧ悊鑳藉姏',
                'pattern_recognition': '妯″紡璇嗗埆鑳藉姏',
                'vote_analysis': '绁ㄥ瀷鍒嗘瀽鑳藉姏',
                'adaptive_behavior': '閫傚簲鎬ц涓?,
                'communication_quality': '娌熼€氳川閲?
            };

            let html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">';

            for (const [key, name] of Object.entries(dimensions)) {
                const score = scores[key]?.score || 0;
                const color = score >= 80 ? '#4CAF50' : score >= 60 ? '#FF9800' : '#f44336';

                html += `
                    <div style="border: 2px solid ${color}; border-radius: 8px; padding: 15px;">
                        <div style="font-weight: bold; color: ${color}; margin-bottom: 8px;">${name}</div>
                        <div style="font-size: 32px; font-weight: bold; color: ${color};">${score}<span style="font-size: 18px;">/100</span></div>
                        <div style="margin-top: 10px; font-size: 12px; color: #666;">
                            ${(scores[key]?.details || []).map(d =>
                                d.includes('[OK]') ? `<div style="color: green;">${d}</div>` :
                                d.includes('[FAIL]') ? `<div style="color: red;">${d}</div>` :
                                `<div style="color: orange;">${d}</div>`
                            ).join('')}
                        </div>
                    </div>
                `;
            }

            html += '</div>';
            return html;
        }

        // 鏄惧紡瀹氫箟骞舵寕杞藉埌 window 瀵硅薄锛岀‘淇濆嚱鏁板湪鎵€鏈変綔鐢ㄥ煙涓彲鐢?
        window.generateDeepReasoningScores = function(metrics) {
            if (!metrics) return '<p style="color: #999;">娣卞害鎺ㄧ悊鏁版嵁涓嶅彲鐢?/p>';

            let html = '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin: 15px 0;">';

            for (const [key, value] of Object.entries(metrics)) {
                const score = value.score || 0;
                const color = score >= 80 ? '#4CAF50' : score >= 60 ? '#FF9800' : '#f44336';

                html += `
                    <div style="border: 2px solid ${color}; border-radius: 8px; padding: 15px;">
                        <div style="font-weight: bold; color: ${color}; margin-bottom: 8px;">${key}</div>
                        <div style="font-size: 32px; font-weight: bold; color: ${color};">${score}<span style="font-size: 18px;">/100</span></div>
                        ${value.details ? `<div style="margin-top: 10px; font-size: 12px; color: #666;">${value.details}</div>` : ''}
                    </div>
                `;
            }

            html += '</div>';
            return html;
        };

        // 鍚屾椂淇濈暀鍑芥暟澹版槑褰㈠紡浠ユ敮鎸佸嚱鏁版彁鍗?
        function generateDeepReasoningScores(metrics) {
            return window.generateDeepReasoningScores(metrics);
        }

        function closeEvalModal() {
            const modal = document.getElementById('eval-modal');
            if (modal) {
                modal.remove();
            }
        }

        function exportEvaluation() {
            fetch('/api/export_evaluation')
                .then(r => r.json())
                .then(data => {
                    if (data.status === 'ok') {
                        alert('璇勪及缁撴灉宸插鍑哄埌: ' + data.filename);
                    }
                })
                .catch(error => {
                    alert('瀵煎嚭澶辫触: ' + error.message);
                });
        }

        // 闅惧害閫夋嫨鍣?
        let currentDifficulty = '鍦扮嫳';

        function setDifficulty(level) {
            currentDifficulty = level;

            // 鏇存柊鏄剧ず鏂囨湰
            const difficultyText = {
                '鍩虹': 'Basic 鍩虹',
                '杩涢樁': 'Advanced 杩涢樁',
                '鍦扮嫳': 'Hell 鍦扮嫳'
            };
            document.getElementById('current-difficulty').textContent = difficultyText[level];

            // 鏇存柊鎸夐挳鏍峰紡
            document.querySelectorAll('.difficulty-btn').forEach(btn => {
                btn.style.opacity = '0.6';
            });

            // 楂樹寒閫変腑鐨勬寜閽拰棰滆壊
            const colors = {
                '鍩虹': '#4CAF50',
                '杩涢樁': '#FF9800',
                '鍦扮嫳': '#f44336'
            };

            if (level === '鍩虹') {
                document.getElementById('btn-diff-basic').style.opacity = '1';
            } else if (level === '杩涢樁') {
                document.getElementById('btn-diff-advanced').style.opacity = '1';
            } else if (level === '鍦扮嫳') {
                document.getElementById('btn-diff-hell').style.opacity = '1';
            }

            document.getElementById('current-difficulty').style.color = colors[level];

            // 鍚戝悗绔彂閫侀毦搴﹁缃?
            fetch('/api/set_difficulty', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({difficulty: level})
            }).then(r => r.json()).then(data => {
                console.log('Difficulty modules activated:', data.activated_modules);
            });

            console.log(`Difficulty set to: ${level}`);
        }

        function updateModulesDisplay() {
            fetch('/api/get_difficulty_info')
                .then(r => r.json())
                .then(data => {
                    const modulesDiv = document.getElementById('modules-list');
                    if (data.activated_modules && data.activated_modules.length > 0) {
                        modulesDiv.innerHTML = data.activated_modules.map(m =>
                            `<div style="margin: 4px 0;">鉁?${m.name} (${m.difficulty})</div>`
                        ).join('');
                    } else {
                        modulesDiv.innerHTML = '<span style="color: #888;">鏆傛棤婵€娲绘ā鍧?No modules activated</span>';
                    }
                });
        }

        // 姣?0绉掓洿鏂颁竴娆℃ā鍧楁樉绀?
        setInterval(updateModulesDisplay, 10000);

        function startEventStream() {
            if (eventSource) eventSource.close();

            eventSource = new EventSource('/api/stream');

            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);

                if (data.type === 'phase') {
                    setPhase(data.phase);
                    if (data.phase === 'night') {
                        players.forEach((p, i) => {
                            if (!['鐙间汉', '鐙肩帇'].includes(p.role)) {
                                hidePlayer(i);
                            }
                        });
                    } else {
                        players.forEach((p, i) => showPlayer(i));
                    }
                } else if (data.type === 'dialogue') {
                    if (data.player_id === -1 && data.content.includes('褰撻€夎闀?)) {
                        const match = data.content.match(/Player (\d+)/);
                        if (match) {
                            updateSheriff(parseInt(match[1]));
                        }
                    }
                    if (data.player_id >= 0) {
                        highlightPlayer(data.player_id);
                    }
                    addDialogue(data);
                } else if (data.type === 'status') {
                    document.getElementById('status').textContent = '鐘舵€侊細' + data.message;
                } else if (data.type === 'death') {
                    markDead(data.player_id);
                } else if (data.type === 'waiting_for_next') {
                    // 鍚敤涓嬩竴澶╂寜閽?
                    document.getElementById('btn-next').disabled = false;

                    // 濡傛灉鏄嚜鍔ㄦā寮忥紝鑷姩鐐瑰嚮涓嬩竴澶?
                    if (autoMode) {
                        setTimeout(() => {
                            nextDay();
                        }, 2000);  // 寤惰繜2绉掕嚜鍔ㄧ户缁?
                    }
                } else if (data.type === 'token_update') {
                    // 鏇存柊token缁熻
                    document.getElementById('total-tokens').textContent = data.total_tokens;

                    // 鍙€夛細鏄剧ず姣忎釜鐜╁鐨則oken浣跨敤鎯呭喌
                    // console.log('Player tokens:', data.player_tokens);
                }
            };

            eventSource.onerror = function() {
                console.error('EventSource error');
                eventSource.close();
            };
        }

        window.addEventListener('load', () => {
            createCircle();

            // 璇婃柇锛氭鏌ュ嚱鏁版槸鍚︽纭姞杞?
            console.log('[璇婃柇] generateDeepReasoningScores 鍑芥暟鐘舵€?',
                typeof window.generateDeepReasoningScores,
                typeof generateDeepReasoningScores);

            if (typeof generateDeepReasoningScores === 'undefined') {
                console.error('[閿欒] generateDeepReasoningScores 鍑芥暟鏈畾涔夛紒');
            } else {
                console.log('[鎴愬姛] generateDeepReasoningScores 鍑芥暟宸插姞杞?);
            }
        });

        window.addEventListener('resize', () => {
            document.getElementById('circle-container').innerHTML = '<div class="center-circle">馃惡<br>鐙间汉鏉€</div>';
            createCircle();
        });
    </script>
</body>
</html>
"""

def call_llm(prompt, player_id):
    """璋冪敤LLM API骞惰窡韪猼oken浣跨敤"""
    global total_tokens_used, player_tokens_used

    try:
        # 娉ㄩ噴鎺塼oken闄愬埗妫€鏌?- 鍏佽鐜╁鑷敱鍙戣█
        # if player_id >= 0:  # player_id == -1 琛ㄧず绯荤粺娑堟伅
        #     current_usage = player_tokens_used.get(player_id, 0)
        #     if current_usage >= MAX_TOKENS_PER_PLAYER:
        #         print(f"[LLM] Player {player_id} 宸茶揪鍒皌oken闄愬埗 ({MAX_TOKENS_PER_PLAYER})")
        #         return f"[Player {player_id} 宸茶揪鍒板彂瑷€闄愬埗]"

        # 鏍规嵁鐜╁ID閫夋嫨API閰嶇疆: Player 1 = 娴嬭瘯妯″瀷, 鍏朵粬鐜╁ = NPC妯″瀷
        if player_id == 1:
            api_base = LLM_CONFIG['test_api_base']
            model = LLM_CONFIG['test_model']
            print(f"[LLM] Player {player_id} 浣跨敤娴嬭瘯妯″瀷: {api_base}")
        else:
            api_base = LLM_CONFIG['npc_api_base']
            model = LLM_CONFIG['npc_model']
            print(f"[LLM] Player {player_id} 浣跨敤NPC妯″瀷: {api_base}")

        # 鍦╬rompt鍚庢坊鍔燨UTPUT鏍煎紡鎸囧紩
        # 閲嶈锛氭鏌rompt鏄惁宸茬粡鏄疷LS++妯″紡锛堝寘鍚?L0 Mode"鎴?Header-Only Mode"锛?
        # ULS++妯″紡涓嬩笉搴旇娣诲姞OUTPUT_FORMAT_INSTRUCTION锛屽洜涓轰細閫犳垚鍐茬獊
        if "L0 Mode" in prompt or "Header-Only Mode" in prompt or "CRITICAL: L0 Mode" in prompt:
            # ULS++妯″紡锛氫笉娣诲姞OUTPUT_FORMAT_INSTRUCTION
            full_prompt = prompt
            print(f"[LLM] [ULS++ Mode Detected] 涓嶆坊鍔燨UTPUT鏍煎紡鎸囧紩锛屼娇鐢ㄥ師濮婾LS++prompt")
        else:
            # Normal mode: natural language speech with reasoning context
            prompt = f"""Werewolf Day {round_num} Discussion
You are Player {player['id']} ({player['role']}). {sheriff_info}

{instruction}{history_context}
{additional_guidance}

Requirements:
1. Analyse previous speeches and identify contradictions or vote-pattern signals.
2. Link your role to an explicit reasoning chain and describe information gain.
3. State your alignment judgement and intended vote target.
4. Keep it within 2-3 sentences; concise bilingual (CN/EN) keywords are welcome."""

        # 鏍规嵁鏄惁涓篣LS++妯″紡閫夋嫨涓嶅悓鐨勮皟鐢ㄦ柟寮?
        # 鏍规嵁鏄惁涓篣LS++妯″紡閫夋嫨涓嶅悓鐨勮皟鐢ㄦ柟寮?
        if uls_mode:
            # ULS++妯″紡锛氱畝鍖栬緭鍑?- 鐩存帴鏄剧ずLLM鍘熷鍝嶅簲锛屼笉鍋氱紪鐮?
            # 浣跨敤姝ｅ父鐨刾rompt锛堜笉寮哄埗ULS鏍煎紡锛夛紝璁㎜LM鑷敱鍙戣█
            normal_prompt = f"""Werewolf Day {round_num} Discussion
You are Player {player['id']} ({player['role']}). {sheriff_info}

{instruction}{history_context}
{additional_guidance}

Requirements:
1. Analyse previous speeches and identify contradictions or vote-pattern signals.
2. Link your role to an explicit reasoning chain and describe information gain.
3. State your alignment judgement and intended vote target.
4. Keep it within 2-3 sentences; concise bilingual (CN/EN) keywords are welcome."""

            # 鐩存帴璋冪敤LLM锛岃幏鍙栧師濮嬪搷搴?
            # 鐩存帴璋冪敤LLM锛岃幏鍙栧師濮嬪搷搴?
            response = call_llm(normal_prompt, player['id'])

            # 灏嗗彂瑷€瀛樺叆鍏叡璁板繂姹?
            event_id = public_memory_pool.add_speech(round_num, player['id'], response)
            public_memory_pool.mark_player_read(player['id'])

            # 鍙戦€佸埌UI锛堢洿鎺ユ樉绀篖LM鍘熷杈撳嚭锛?
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": player['id'],
                "phase": f"绗瑊round_num}澶╄璁?,
                "content": response,  # 鐩存帴鏄剧ず鍘熷鍝嶅簲
                "panel": "day"
            })
        else:
            # 姝ｅ父妯″紡锛氬崟闃舵璋冪敤
            response = call_llm(prompt, player['id'])

            # 灏嗗彂瑷€瀛樺叆鍏叡璁板繂姹?
            event_id = public_memory_pool.add_speech(round_num, player['id'], response)
            public_memory_pool.mark_player_read(player['id'])

            dialogue_queue.put({
                "type": "dialogue",
                "player_id": player['id'],
                "phase": f"绗瑊round_num}澶╄璁?,
                "content": response,
                "panel": "day"
            })

        time.sleep(1)

    # 鎶曠エ澶勫喅
    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"绗瑊round_num}澶╂姇绁?,
        "content": "馃棾锔?鎶曠エ闃舵锛岃鎵€鏈夌帺瀹舵姇绁ㄣ€?,
        "panel": "day"
    })

    time.sleep(1.5)

    alive_players = [p for p in PLAYERS if p['alive']]
    if len(alive_players) >= 2:
        # 缁熻鎶曠エ
        vote_counts = {}

        # 姣忎釜鐜╁鎶曠エ
        for voter in alive_players:
            if not is_running:
                break

            # 鍙互鎶曠エ鐨勭洰鏍囷紙闄や簡鑷繁锛?
            vote_candidates = [p for p in alive_players if p['id'] != voter['id']]
            if not vote_candidates:
                continue

            # 鏋勫缓鎶曠エ鍐崇瓥鐨勪笂涓嬫枃 (浣跨敤绠€鍖栨憳瑕侊紝鍥犱负鎶曠エ闃舵闇€瑕佸叏灞€瑙嗚)
            current_round_speeches = public_memory_pool.get_round_speeches(round_num)
            vote_context = "\n銆愭湰杞彂瑷€鎽樿銆慭n"
            for speech in current_round_speeches[-5:]:  # 鍙樉绀烘渶鍚?鏉″彂瑷€锛岃妭鐪乼oken
                truncated = speech['content'][:80].replace('\n', ' ')
                vote_context += f"Player {speech['player_id']}: {truncated}...\n"

            candidates_list = ", ".join([f"Player {p['id']}" for p in vote_candidates])

            # 鏍规嵁瑙掕壊缁欏嚭鎶曠エ绛栫暐鎸囧
            if voter['role'] in ['鐙间汉', '鐙肩帇']:
                vote_instruction = "浣犳槸鐙间汉闃佃惀锛屾姇绁ㄧ粰瀵圭嫾浜哄▉鑳佹渶澶х殑濂戒汉锛堝棰勮█瀹躲€佸己鍔挎潙姘戯級銆?
            elif voter['role'] == '棰勮█瀹?:
                vote_instruction = "浣犳槸棰勮█瀹讹紝鎶曠エ缁欎綘楠屽嚭鐨勭嫾浜猴紝鎴栧彂瑷€鏈€鍙枒鐨勭帺瀹躲€?
            elif voter['role'] in ['濂冲帆', '鐚庝汉', '瀹堝崼']:
                vote_instruction = "浣犳槸绁炶亴锛屾姇绁ㄧ粰鍙戣█鏈€鍙枒銆侀€昏緫鏈夋紡娲炵殑鐜╁銆?
            else:
                vote_instruction = "浣犳槸鏉戞皯锛屾姇绁ㄧ粰鍙戣█鏈€鍙枒銆侀€昏緫鏈夋紡娲炵殑鐜╁銆?

            if voter['id'] == TEST_SUBJECT_ID:
                vote_instruction += build_bilingual_vote_guidance()

            vote_prompt = f"""鐙间汉鏉€ - 绗瑊round_num}澶╂姇绁ㄥ喅绛?
浣犳槸Player {voter['id']}锛岃鑹诧細{voter['role']}銆?

{vote_instruction}

{vote_context}

鍊欓€変汉锛歿candidates_list}

鍒嗘瀽浠ヤ笂鍙戣█锛岄€夋嫨涓€涓渶搴旇鍑哄眬鐨勭帺瀹躲€傚彧闇€瑕佽緭鍑虹帺瀹剁紪鍙凤紝鏍煎紡锛歅layer X"""

            vote_response = call_llm(vote_prompt, voter['id'])

            # 浠庡洖澶嶄腑鎻愬彇鐜╁缂栧彿
            import re
            match = re.search(r'Player\s*(\d+)', vote_response, re.IGNORECASE)
            if match:
                voted_id = int(match.group(1))
                # 楠岃瘉鎶曠エ鐩爣鏄惁鏈夋晥
                voted_for = next((p for p in vote_candidates if p['id'] == voted_id), None)
                if not voted_for:
                    # 濡傛灉鎻愬彇鐨処D鏃犳晥锛岄殢鏈洪€夋嫨
                    voted_for = random.choice(vote_candidates)
            else:
                # 濡傛灉鏃犳硶瑙ｆ瀽锛岄殢鏈洪€夋嫨
                voted_for = random.choice(vote_candidates)

            # 璁板綍鎶曠エ
            if voted_for['id'] not in vote_counts:
                vote_counts[voted_for['id']] = []
            vote_counts[voted_for['id']].append(voter['id'])

            # 鏄剧ず鎶曠エ
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": voter['id'],
                "phase": f"绗瑊round_num}澶╂姇绁?,
                "content": f"馃棾锔?鎶曠エ缁?Player {voted_for['id']}",
                "panel": "day"
            })

            time.sleep(0.5)

        # 缁熻鏈€楂樼エ鏁?
        if vote_counts:
            max_votes = max(len(voters) for voters in vote_counts.values())
            candidates_with_max_votes = [player_id for player_id, voters in vote_counts.items() if len(voters) == max_votes]

            # 濡傛灉鏈夊钩绁紝闅忔満閫変竴涓?
            vote_target_id = random.choice(candidates_with_max_votes)
            vote_target = next(p for p in PLAYERS if p['id'] == vote_target_id)

            # 鏄剧ず鎶曠エ缁撴灉
            vote_result_lines = ["馃搳 鎶曠エ缁撴灉锛?]
            for player_id in sorted(vote_counts.keys()):
                voters = vote_counts[player_id]
                vote_result_lines.append(f"  Player {player_id}: {len(voters)}绁?({', '.join(['P' + str(v) for v in voters])})")

            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": f"绗瑊round_num}澶╂姇绁?,
                "content": "\n".join(vote_result_lines),
                "panel": "day"
            })

            time.sleep(1)
        else:
            vote_target = random.choice(alive_players)

        # 鏇存柊浠婃棩缁熻 - 璁板綍鐧藉ぉ澶勫喅鐨勭帺瀹?
        if daily_statistics and len(daily_statistics) > 0:
            daily_statistics[-1]["day_execution"] = {
                "player_id": vote_target['id'],
                "role": vote_target['role']
            }

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"绗瑊round_num}澶╂姇绁?,
            "content": f"馃棾锔?Player {vote_target['id']} 寰楃エ鏈€澶氾紝琚鍐炽€?,
            "panel": "day"
        })

        # 琚鍐崇帺瀹跺彂琛ㄩ仐瑷€
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"绗瑊round_num}澶╂姇绁?,
            "content": f"馃挰 Player {vote_target['id']} 璇峰彂琛ㄩ仐瑷€銆?,
            "panel": "day"
        })

        time.sleep(1)

        # 鐢熸垚閬楄█
        last_words_prompt = f"""鐙间汉鏉€娓告垙 - 浣犺鎶曠エ澶勫喅浜嗐€?
浣犳槸Player {vote_target['id']}锛岃鑹诧細{vote_target['role']}銆?

鐜板湪鏄綘鐨勯仐瑷€鏃跺埢锛岃鍙戣〃涓寸粓閬楄█锛?
- 濡傛灉浣犳槸濂戒汉闃佃惀锛屽彲浠ョ暀涓嬪叧閿俊鎭府鍔╅槦鍙?
- 濡傛灉浣犳槸鐙间汉闃佃惀锛屽彲浠ュ皾璇曡瀵煎鎵?
- 琛ㄨ揪浣犵殑鎯虫硶鍜屽缓璁?

璇风敤2-3鍙ヨ瘽鍙戣〃閬楄█銆傜敤涓枃銆?""

        last_words = call_llm(last_words_prompt, vote_target['id'])

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": vote_target['id'],
            "phase": f"绗瑊round_num}澶?閬楄█",
            "content": f"[閬楄█] {last_words}",
            "panel": "day"
        })

        time.sleep(2)

        vote_target['alive'] = False

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"绗瑊round_num}澶╂姇绁?,
            "content": f"鈿帮笍 Player {vote_target['id']} ({vote_target['role']}) 琚姇绁ㄥ鍐炽€?,
            "panel": "day"
        })

        dialogue_queue.put({
            "type": "death",
            "player_id": vote_target['id']
        })

        time.sleep(1)

        # 鐚庝汉/鐙肩帇鎶€鑳?
        if vote_target['role'] == '鐚庝汉':
            other_alive = [p for p in PLAYERS if p['alive']]
            if other_alive:
                # 鐚庝汉鎬濊€冨苟鍐冲畾灏勬潃鐩爣
                alive_list = ', '.join([f"Player {p['id']} ({p['role'] if p['id'] == vote_target['id'] else '鏈煡'})" for p in other_alive])

                hunter_shoot_prompt = f"""鐙间汉鏉€娓告垙 - 鐚庝汉寮€鏋妧鑳?
浣犳槸Player {vote_target['id']}锛岃鑹诧細鐚庝汉銆?
浣犲垰鍒氳鎶曠エ澶勫喅浜嗭紝鐜板湪鍙互鍙戝姩鐚庝汉鎶€鑳姐€愬紑鏋甫璧颁竴涓帺瀹躲€戙€?

褰撳墠瀛樻椿鐜╁锛歿alive_list}

璇锋牴鎹箣鍓嶇殑娓告垙淇℃伅锛屽垎鏋愬苟鍐冲畾灏勬潃璋侊細
1. 濡傛灉浣犺涓烘煇涓帺瀹舵槸鐙间汉锛屽簲璇ヤ紭鍏堝皠鏉€
2. 鑰冭檻涔嬪墠鐨勫彂瑷€銆佹姇绁ㄨ涓恒€侀瑷€瀹堕獙浜虹瓑淇℃伅
3. 鍋氬嚭瀵瑰ソ浜洪樀钀ユ渶鏈夊埄鐨勯€夋嫨

璇锋寜浠ヤ笅鏍煎紡鍥炵瓟锛?
鎬濊€冿細[浣犵殑鍒嗘瀽杩囩▼]

OUTPUT: 鎴戝喅瀹氬皠鏉€ Player X锛屽洜涓篬绠€鐭悊鐢盷
END"""

                hunter_response = call_llm(hunter_shoot_prompt, vote_target['id'])

                # 瑙ｆ瀽灏勬潃鐩爣
                import re
                match = re.search(r'Player (\d+)', hunter_response)
                if match:
                    target_id = int(match.group(1))
                    # 楠岃瘉鐩爣鏄惁瀛樻椿
                    if target_id in [p['id'] for p in other_alive]:
                        hunter_target = PLAYERS[target_id]
                    else:
                        # 濡傛灉鐩爣鏃犳晥锛岄殢鏈洪€夋嫨
                        hunter_target = random.choice(other_alive)
                        print(f"[WARN] Hunter target {target_id} invalid, random choice: {hunter_target['id']}")
                else:
                    # 濡傛灉鏃犳硶瑙ｆ瀽锛岄殢鏈洪€夋嫨
                    hunter_target = random.choice(other_alive)
                    print(f"[WARN] Cannot parse hunter target, random choice: {hunter_target['id']}")

                hunter_target['alive'] = False

                # 鏄剧ず鐚庝汉鐨勬€濊€冨拰鍐崇瓥
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": vote_target['id'],
                    "phase": f"绗瑊round_num}澶?鐚庝汉",
                    "content": f"馃徆 鐚庝汉鎶€鑳藉彂鍔紒{hunter_response}",
                    "panel": "day"
                })

                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": f"绗瑊round_num}澶?鐚庝汉",
                    "content": f"馃挜 鐚庝汉寮€鏋甫璧?Player {hunter_target['id']} ({hunter_target['role']})",
                    "panel": "day"
                })

                dialogue_queue.put({
                    "type": "death",
                    "player_id": hunter_target['id']
                })

                time.sleep(2)
        elif vote_target['role'] == '鐙肩帇':
            other_alive = [p for p in PLAYERS if p['alive']]
            if other_alive:
                # 鐙肩帇鎬濊€冨苟鍐冲畾甯﹁蛋鐩爣
                alive_list = ', '.join([f"Player {p['id']}" for p in other_alive])

                wolf_king_prompt = f"""鐙间汉鏉€娓告垙 - 鐙肩帇鎶€鑳?
浣犳槸Player {vote_target['id']}锛岃鑹诧細鐙肩帇锛堢嫾浜洪樀钀ワ級銆?
浣犲垰鍒氳鎶曠エ澶勫喅浜嗭紝鐜板湪鍙互鍙戝姩鐙肩帇鎶€鑳姐€愬甫璧颁竴涓帺瀹躲€戙€?

褰撳墠瀛樻椿鐜╁锛歿alive_list}

璇锋牴鎹箣鍓嶇殑娓告垙淇℃伅锛屽垎鏋愬苟鍐冲畾甯﹁蛋璋侊細
1. 浼樺厛鑰冭檻甯﹁蛋棰勮█瀹躲€佸コ宸瓑鍏抽敭绁炶亴
2. 鑰冭檻涔嬪墠鐨勫彂瑷€鍜岄獙浜轰俊鎭?
3. 涓虹嫾浜洪槦鍙嬪垱閫犺幏鑳滄満浼?

璇锋寜浠ヤ笅鏍煎紡鍥炵瓟锛?
鎬濊€冿細[浣犵殑鍒嗘瀽杩囩▼]

OUTPUT: 鎴戝喅瀹氬甫璧?Player X锛屽洜涓篬绠€鐭悊鐢盷
END"""

                wolf_king_response = call_llm(wolf_king_prompt, vote_target['id'])

                # 瑙ｆ瀽甯﹁蛋鐩爣
                import re
                match = re.search(r'Player (\d+)', wolf_king_response)
                if match:
                    target_id = int(match.group(1))
                    # 楠岃瘉鐩爣鏄惁瀛樻椿
                    if target_id in [p['id'] for p in other_alive]:
                        wolf_king_target = PLAYERS[target_id]
                    else:
                        # 濡傛灉鐩爣鏃犳晥锛岄殢鏈洪€夋嫨
                        wolf_king_target = random.choice(other_alive)
                        print(f"[WARN] Wolf King target {target_id} invalid, random choice: {wolf_king_target['id']}")
                else:
                    # 濡傛灉鏃犳硶瑙ｆ瀽锛岄殢鏈洪€夋嫨
                    wolf_king_target = random.choice(other_alive)
                    print(f"[WARN] Cannot parse wolf king target, random choice: {wolf_king_target['id']}")

                wolf_king_target['alive'] = False

                # 鏄剧ず鐙肩帇鐨勬€濊€冨拰鍐崇瓥
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": vote_target['id'],
                    "phase": f"绗瑊round_num}澶?鐙肩帇",
                    "content": f"馃憫 鐙肩帇鎶€鑳藉彂鍔紒{wolf_king_response}",
                    "panel": "day"
                })

                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": f"绗瑊round_num}澶?鐙肩帇",
                    "content": f"馃挜 鐙肩帇甯﹁蛋 Player {wolf_king_target['id']} ({wolf_king_target['role']})",
                    "panel": "day"
                })

                dialogue_queue.put({
                    "type": "death",
                    "player_id": wolf_king_target['id']
                })

                time.sleep(1.5)

    # 娓呯┖澶滄櫄琛屽姩
    game_state['night_actions'] = {}

    # 鏄剧ず浠婃棩缁熻
    display_daily_statistics(round_num)

    # 濡傛灉鏄嚜鍔ㄦā寮忥紝鐩存帴缁х画锛涘惁鍒欑瓑寰呯敤鎴风偣鍑?涓嬩竴澶?鎸夐挳
    global waiting_for_next_day, auto_mode

    print(f"[DEBUG] auto_mode = {auto_mode}, 鍑嗗杩涘叆涓嬩竴澶╅€昏緫")

    if not auto_mode:
        waiting_for_next_day = True

        dialogue_queue.put({
            "type": "waiting_for_next",
            "message": "绛夊緟鐢ㄦ埛鐐瑰嚮涓嬩竴澶?
        })

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": "绛夊緟",
            "content": "鈴革笍 鐐瑰嚮涓嬩竴澶╂寜閽户缁父鎴?,
            "panel": "day"
        })

        # 绛夊緟waiting_for_next_day鍙樹负False
        while waiting_for_next_day and is_running:
            time.sleep(0.5)
    else:
        # 鑷姩妯″紡锛氱煭鏆傛殏鍋滃悗鑷姩缁х画
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": "鑷姩妯″紡",
            "content": "鈴?鑷姩妯″紡锛?绉掑悗鑷姩杩涘叆涓嬩竴澶?,
            "panel": "day"
        })
        time.sleep(3)

def update_realtime_statistics():
    """瀹炴椂鏇存柊缁熻闈㈡澘"""
    if not daily_statistics or len(daily_statistics) == 0:
        return

    stats = daily_statistics[-1]
    day_num = stats["day"]

    # 鏋勫缓瀹炴椂缁熻淇℃伅
    stats_lines = []
    stats_lines.append(f"馃搳 绗瑊day_num}澶?瀹炴椂缁熻")
    stats_lines.append("=" * 35)

    # 澶滄櫄琛屽姩
    if stats["night_actions"]:
        stats_lines.append("\n馃寵 澶滄櫄琛屽姩:")
        actions = stats["night_actions"]
        if "wolf_target" in actions:
            stats_lines.append(f"  馃惡 鐙煎垁: Player {actions['wolf_target']}")
        if "guard_target" in actions:
            stats_lines.append(f"  馃洝锔?瀹堝崼: Player {actions['guard_target']}")
        if "seer_check" in actions:
            check = actions['seer_check']
            stats_lines.append(f"  馃憗锔?楠屼汉: P{check['target']} 鈫?{check['result']}")
        if "witch_save" in actions:
            stats_lines.append(f"  馃И 瑙ｈ嵂: Player {actions['witch_save']}")
        if "witch_poison" in actions:
            stats_lines.append(f"  馃И 姣掕嵂: Player {actions['witch_poison']}")

    # 澶滄櫄姝讳骸
    if stats["night_deaths"]:
        death_list = ', '.join([f"P{p}" for p in stats["night_deaths"]])
        stats_lines.append(f"\n馃拃 澶滄櫄姝讳骸: {death_list}")
    else:
        stats_lines.append("\n馃帀 骞冲畨澶?)

    # 鐧藉ぉ澶勫喅
    if stats["day_execution"]:
        exec_info = stats["day_execution"]
        stats_lines.append(f"\n馃棾锔?鐧藉ぉ澶勫喅: Player {exec_info['player_id']}")
        stats_lines.append(f"   韬唤: {exec_info['role']}")

    # 褰撳墠瀛樻椿缁熻
    alive_players = [p for p in PLAYERS if p['alive']]
    alive_werewolves = [p for p in alive_players if p['role'] in ['鐙间汉', '鐙肩帇']]
    alive_villagers = [p for p in alive_players if p['role'] not in ['鐙间汉', '鐙肩帇']]

    stats_lines.append("\n" + "=" * 35)
    stats_lines.append(f"馃搱 瀛樻椿: 馃惡{len(alive_werewolves)} vs 馃懆鈥嶐煂緖len(alive_villagers)}")

    stats_content = "\n".join(stats_lines)

    # 鍙戦€佸埌缁熻闈㈡澘
    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"绗瑊day_num}澶?,
        "content": stats_content,
        "panel": "statistics"
    })

def display_daily_statistics(day_num):
    """鏄剧ず姣忓ぉ缁熻淇℃伅"""
    print(f"[DEBUG] display_daily_statistics called for day {day_num}")
    try:
        alive_players = [p for p in PLAYERS if p['alive']]
        alive_werewolves = [p for p in alive_players if p['role'] in ['鐙间汉', '鐙肩帇']]
        alive_villagers = [p for p in alive_players if p['role'] not in ['鐙间汉', '鐙肩帇']]
        print(f"[DEBUG] Alive: {len(alive_werewolves)} wolves vs {len(alive_villagers)} villagers")

        # 鏇存柊浠婃棩缁熻涓殑瀛樻椿浜烘暟
        if daily_statistics and len(daily_statistics) > 0:
            daily_statistics[-1]["alive_werewolves"] = len(alive_werewolves)
            daily_statistics[-1]["alive_villagers"] = len(alive_villagers)

        # 鏋勫缓缁熻淇℃伅
        stats_lines = []
        stats_lines.append(f"馃搳 绗瑊day_num}澶╃粺璁′俊鎭?馃搳")
        stats_lines.append("-" * 40)

        if daily_statistics and len(daily_statistics) > 0:
            stats = daily_statistics[-1]

            # 澶滄櫄琛屽姩缁熻
            if stats["night_actions"]:
                stats_lines.append("馃寵 澶滄櫄琛屽姩:")
                actions = stats["night_actions"]
                if "wolf_target" in actions:
                    stats_lines.append(f"  馃惡 鐙间汉鍒€: Player {actions['wolf_target']}")
                if "guard_target" in actions:
                    stats_lines.append(f"  馃洝锔?瀹堝崼瀹? Player {actions['guard_target']}")
                if "seer_check" in actions:
                    check = actions['seer_check']
                    stats_lines.append(f"  馃憗锔?棰勮█瀹堕獙: Player {check['target']} ({check['result']})")
                if "witch_save" in actions:
                    stats_lines.append(f"  馃И 濂冲帆鏁? Player {actions['witch_save']}")
                if "witch_poison" in actions:
                    stats_lines.append(f"  馃И 濂冲帆姣? Player {actions['witch_poison']}")

            # 澶滄櫄姝讳骸缁熻
            if stats["night_deaths"]:
                death_list = ', '.join([f"Player {p}" for p in stats["night_deaths"]])
                stats_lines.append(f"  馃拃 澶滄櫄姝讳骸: {death_list}")
            else:
                stats_lines.append("  馃帀 澶滄櫄骞冲畨澶?)

            # 鐧藉ぉ澶勫喅缁熻
            if stats["day_execution"]:
                exec_info = stats["day_execution"]
                stats_lines.append(f"  馃棾锔?鐧藉ぉ澶勫喅: Player {exec_info['player_id']} ({exec_info['role']})")

        # 褰撳墠瀛樻椿缁熻
        stats_lines.append("-" * 40)
        stats_lines.append(f"馃搱 褰撳墠瀛樻椿: 鐙间汉 {len(alive_werewolves)} 浜?| 濂戒汉 {len(alive_villagers)} 浜?)

        # 妫€鏌ユ槸鍚﹁Е鍙戞父鎴忕粨鏉熸潯浠?
        if len(alive_werewolves) > len(alive_villagers):
            stats_lines.append("鈿狅笍 瑙﹀彂娓告垙缁撴潫鏉′欢: 鐙间汉鏁?> 濂戒汉鏁?)
            if daily_statistics and len(daily_statistics) > 0:
                daily_statistics[-1]["game_ended"] = True
                daily_statistics[-1]["winner"] = "werewolves"
        elif len(alive_werewolves) == 0:
            stats_lines.append("鈿狅笍 瑙﹀彂娓告垙缁撴潫鏉′欢: 鐙间汉鍏ㄧ伃")
            if daily_statistics and len(daily_statistics) > 0:
                daily_statistics[-1]["game_ended"] = True
                daily_statistics[-1]["winner"] = "villagers"
        else:
            stats_lines.append("鉁?娓告垙缁х画")

        stats_content = "\n".join(stats_lines)

        # 鍙戦€佺粺璁′俊鎭埌缁熻闈㈡澘锛坰tatistics panel锛?
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"绗瑊day_num}澶╃粺璁?,
            "content": stats_content,
            "panel": "statistics"
        })

        time.sleep(2)
    except Exception as e:
        print(f"[ERROR] Exception in display_daily_statistics: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

def display_game_summary():
    """娓告垙缁撴潫鏃舵樉绀哄畬鏁寸粺璁℃憳瑕?""
    summary_lines = []
    summary_lines.append("=" * 50)
    summary_lines.append("馃幃 娓告垙缁熻鎽樿 馃幃")
    summary_lines.append("=" * 50)

    for i, stats in enumerate(daily_statistics, 1):
        summary_lines.append(f"馃搮 绗瑊stats['day']}澶?")
        summary_lines.append("-" * 40)

        # 澶滄櫄琛屽姩
        if stats["night_actions"]:
            summary_lines.append("  馃寵 澶滄櫄琛屽姩:")
            actions = stats["night_actions"]
            if "wolf_target" in actions:
                summary_lines.append(f"    馃惡 鐙间汉鍒€: Player {actions['wolf_target']}")
            if "guard_target" in actions:
                summary_lines.append(f"    馃洝锔?瀹堝崼瀹? Player {actions['guard_target']}")
            if "seer_check" in actions:
                check = actions['seer_check']
                summary_lines.append(f"    馃憗锔?棰勮█瀹堕獙: Player {check['target']} 鈫?{check['result']}")
            if "witch_save" in actions:
                summary_lines.append(f"    馃И 濂冲帆鏁? Player {actions['witch_save']}")
            if "witch_poison" in actions:
                summary_lines.append(f"    馃И 濂冲帆姣? Player {actions['witch_poison']}")

        # 澶滄櫄姝讳骸
        if stats["night_deaths"]:
            death_list = ', '.join([f"Player {p}" for p in stats["night_deaths"]])
            summary_lines.append(f"  馃拃 澶滄櫄姝讳骸: {death_list}")
        else:
            summary_lines.append("  馃帀 澶滄櫄骞冲畨澶?)

        # 鐧藉ぉ澶勫喅
        if stats["day_execution"]:
            exec_info = stats["day_execution"]
            summary_lines.append(f"  馃棾锔?鐧藉ぉ澶勫喅: Player {exec_info['player_id']} ({exec_info['role']})")

        # 褰撳ぉ缁撴潫鍚庡瓨娲绘儏鍐?
        summary_lines.append(f"  馃搱 瀛樻椿: 鐙间汉 {stats['alive_werewolves']} | 濂戒汉 {stats['alive_villagers']}")

        if stats["game_ended"]:
            winner_name = "鐙间汉闃佃惀" if stats["winner"] == "werewolves" else "鏉戞皯闃佃惀"
            summary_lines.append(f"  馃弳 娓告垙缁撴潫 - {winner_name}鑳滃埄锛?)

    summary_lines.append("=" * 50)
    summary_content = "\n".join(summary_lines)

    # 鍙戦€佸埌鐧藉ぉ闈㈡澘
    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "娓告垙鎽樿",
        "content": summary_content,
        "panel": "day"
    })

    # 鍚屾椂鎵撳嵃鍒版帶鍒跺彴
    print("\n" + summary_content)
    time.sleep(3)

def check_win_condition():
    """妫€鏌ヨ儨鍒╂潯浠讹紝杩斿洖 (winner, reason, details) 鎴?(None, None, None)"""
    alive_players = [p for p in PLAYERS if p['alive']]
    alive_werewolves = [p for p in alive_players if p['role'] in ['鐙间汉', '鐙肩帇']]
    alive_villagers = [p for p in alive_players if p['role'] not in ['鐙间汉', '鐙肩帇']]

    print(f"[DEBUG check_win_condition] Wolves: {len(alive_werewolves)}, Villagers: {len(alive_villagers)}")

    # 鑾峰彇瀛樻椿鐜╁鐨勮缁嗕俊鎭?
    werewolf_list = [f"Player {p['id']} ({p['role']})" for p in alive_werewolves]
    villager_list = [f"Player {p['id']} ({p['role']})" for p in alive_villagers]

    if len(alive_werewolves) > len(alive_villagers):
        reason = f"鐙间汉鏁伴噺({len(alive_werewolves)})宸茬粡澶т簬濂戒汉鏁伴噺({len(alive_villagers)})"
        details = f"\n\n瀛樻椿鐙间汉: {', '.join(werewolf_list) if len(werewolf_list) > 0 else '鏃?}\n瀛樻椿濂戒汉: {', '.join(villager_list) if len(villager_list) > 0 else '鏃?}"
        return ('werewolves', reason, details)

    if len(alive_werewolves) == 0:
        reason = "鎵€鏈夌嫾浜哄凡琚秷鐏?
        details = f"\n\n瀛樻椿濂戒汉: {', '.join(villager_list)}"
        return ('villagers', reason, details)

    return (None, None, None)

def game_loop():
    """
    瀹屾暣娓告垙寰幆
    if ELECTION_BEFORE_N1:
        璀﹂暱绔為€?鈫?Night(1) 鈫?Dawn 鈫?Day(1) 鈫?Night(2) 鈫?Dawn 鈫?Day(2) 鈫?...
    else:
        Night(1) 鈫?Dawn 鈫?Day(1) 鈫?Night(2) 鈫?Dawn 鈫?Day(2) 鈫?...
    """
    global is_running, guard_last_target, witch_save_available, witch_poison_available, uls_mode

    print(f"\n[GAME_LOOP] Starting game with ULS_MODE = {uls_mode}")

    day_num = 1

    # 鏍规嵁閰嶇疆鍐冲畾鏄惁鍏堜笂璀?
    if ELECTION_BEFORE_N1 and is_running:
        # 鍏堣闀跨珵閫夛紙寮€灞€鐧藉ぉ涓婅锛?
        sheriff_election_before_n1()

    # 绗竴澶?
    if is_running:
        # 鎵ц绗竴澶滐紙鍖呭惈瀹屾暣鐨勫鏅氶樁娈碉級
        sync_game_state(phase="night", round_num=1)
        night_deaths = night_phase(1)

        if night_deaths is None:  # 鐙间汉鍏ㄧ伃
            dialogue_queue.put({
                "type": "status",
                "message": "馃帀 娓告垙缁撴潫 - 鏉戞皯闃佃惀鑳滃埄锛?
            })
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": "娓告垙缁撴潫",
                "content": "馃懆鈥嶐煂?鏉戞皯闃佃惀鑾疯儨锛佹墍鏈夌嫾浜哄凡琚嚮鏉€銆?,
                "panel": "day"
            })
            display_game_summary()
            is_running = False
            return

        # 榛庢槑闃舵
        sync_game_state(phase="dawn", round_num=1)
        dawn_phase(night_deaths, 1)

        # 璀﹂暱绔為€夛紙濡傛灉娌℃湁鎻愬墠涓婅锛?
        if is_running and not ELECTION_BEFORE_N1:
            sheriff_election()

    # 涓绘父鎴忓惊鐜?
    while is_running:
        # 妫€鏌ヨ儨鍒╂潯浠?
        winner, reason, details = check_win_condition()
        print(f"[DEBUG GAME_LOOP] Day {day_num} - Check win condition BEFORE day: winner={winner}, reason={reason}")
        if winner:
            dialogue_queue.put({
                "type": "status",
                "message": f"馃帀 娓告垙缁撴潫 - {'鐙间汉' if winner == 'werewolves' else '鏉戞皯'}闃佃惀鑳滃埄锛?
            })

            panel = "day"
            if winner == 'werewolves':
                content = f"馃惡 鐙间汉闃佃惀鑾疯儨锛乗n\n鑳滃埄鍘熷洜: {reason}{details}"
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "娓告垙缁撴潫",
                    "content": content,
                    "panel": panel
                })
            else:
                content = f"馃懆鈥嶐煂?鏉戞皯闃佃惀鑾疯儨锛乗n\n鑳滃埄鍘熷洜: {reason}{details}"
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "娓告垙缁撴潫",
                    "content": content,
                    "panel": panel
                })

            display_game_summary()
            is_running = False
            break

        # 鐧藉ぉ璁ㄨ鎶曠エ
        sync_game_state(phase="day", round_num=day_num)
        day_discussion_and_voting(day_num)

        # 鍐嶆妫€鏌ヨ儨鍒?
        winner, reason, details = check_win_condition()
        print(f"[DEBUG GAME_LOOP] Day {day_num} - Check win condition AFTER day: winner={winner}, reason={reason}")
        if winner:
            dialogue_queue.put({
                "type": "status",
                "message": f"馃帀 娓告垙缁撴潫 - {'鐙间汉' if winner == 'werewolves' else '鏉戞皯'}闃佃惀鑳滃埄锛?
            })

            panel = "day"
            if winner == 'werewolves':
                content = f"馃惡 鐙间汉闃佃惀鑾疯儨锛乗n\n鑳滃埄鍘熷洜: {reason}{details}"
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "娓告垙缁撴潫",
                    "content": content,
                    "panel": panel
                })
            else:
                content = f"馃懆鈥嶐煂?鏉戞皯闃佃惀鑾疯儨锛乗n\n鑳滃埄鍘熷洜: {reason}{details}"
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "娓告垙缁撴潫",
                    "content": content,
                    "panel": panel
                })

            display_game_summary()
            is_running = False
            break

        # 澶滄櫄闃舵
        day_num += 1

        # 鎵ц瀹屾暣鐨勫鏅氶樁娈?
        sync_game_state(phase="night", round_num=day_num)
        night_deaths = night_phase(day_num)

        if night_deaths is None:  # 鐙间汉鍏ㄧ伃
            dialogue_queue.put({
                "type": "status",
                "message": "馃帀 娓告垙缁撴潫 - 鏉戞皯闃佃惀鑳滃埄锛?
            })
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": "娓告垙缁撴潫",
                "content": "馃懆鈥嶐煂?鏉戞皯闃佃惀鑾疯儨锛佹墍鏈夌嫾浜哄凡琚嚮鏉€銆?,
                "panel": "day"
            })
            display_game_summary()
            is_running = False
            break

        # 榛庢槑闃舵
        sync_game_state(phase="dawn", round_num=day_num)
        dawn_phase(night_deaths, day_num)

        time.sleep(2)

@app.route('/')
def index():
    import time
    # 娣诲姞鏃堕棿鎴冲己鍒跺埛鏂?- 娉ㄥ叆鐗堟湰鍙峰埌HTML
    version = str(int(time.time()))
    html = HTML_TEMPLATE.replace('<head>', f'<head><!-- v{version} -->')
    return render_template_string(html, players=PLAYERS), 200, {
        'Cache-Control': 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '-1',
        'Last-Modified': time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime())
    }

@app.route('/api/start', methods=['POST', 'OPTIONS'])
def start():
    if request.method == 'OPTIONS':
        # Handle CORS preflight with explicit headers
        response = app.make_response(('', 204))
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    global is_running, seer_claims, sheriff_player_id, sheriff_candidates, game_state
    global guard_last_target, witch_save_available, witch_poison_available, daily_statistics
    global waiting_for_next_day, auto_mode, total_tokens_used, player_tokens_used, public_memory_pool
    global game_evaluator

    print(f"[DEBUG /api/start] Called. is_running={is_running}, auto_mode={auto_mode}")

    if not is_running:
        print("[DEBUG /api/start] Starting new game...")
        is_running = True
        waiting_for_next_day = False
        # auto_mode 淇濇寔鐢ㄦ埛璁剧疆锛屼笉閲嶇疆
        seer_claims = []
        sheriff_player_id = None
        sheriff_candidates = []
        guard_last_target = None
        witch_save_available = True
        witch_poison_available = True
        daily_statistics = []  # 閲嶇疆缁熻
        total_tokens_used = 0  # 閲嶇疆token缁熻
        player_tokens_used = {}  # 閲嶇疆姣忎釜鐜╁鐨則oken浣跨敤閲?
        public_memory_pool = MemoryPool()  # 閲嶇疆鍏叡璁板繂姹?(T2浼樺寲)

        # 鍒濆鍖栬瘎浼板櫒 (榛樿璇勪及Player 7)
        if EVALUATOR_ENABLED:
            game_evaluator = EnhancedReasoningEvaluator(test_subject_id=TEST_SUBJECT_ID)
            print("[INFO] Enhanced game evaluator initialized for Player 7")

        game_state = {
            "phase": "night",
            "round": 0,
            "dead_players": [],
            "night_actions": {},
            "players": [],
            "wolf_num": 0,
            "alive_players": len(PLAYERS),
            "total_players": len(PLAYERS)
        }

        for player in PLAYERS:
            player['alive'] = True
            player['is_sheriff'] = False

        while not dialogue_queue.empty():
            dialogue_queue.get()

        clear_dialogue_history()

        sync_game_state(phase="night", round_num=0)

        print("[DEBUG /api/start] Creating game thread...")
        thread = threading.Thread(target=game_loop, daemon=True)
        thread.start()
        print("[DEBUG /api/start] Game thread started!")

        return {"status": "started"}

    print("[DEBUG /api/start] Game already running, returning already_running status")
    return {"status": "already_running"}

@app.route('/api/stop', methods=['POST'])
def stop():
    global is_running
    is_running = False
    return {"status": "stopped"}

@app.route('/api/next_day', methods=['POST'])
def next_day():
    global waiting_for_next_day
    waiting_for_next_day = False
    return {"status": "continued"}

@app.route('/api/set_auto_mode', methods=['POST'])
def set_auto_mode():
    global auto_mode, waiting_for_next_day
    data = app.current_request.get_json() if hasattr(app, 'current_request') else None

    if not data:
        from flask import request
        data = request.get_json()

    auto_mode = data.get('auto_mode', False)

    # 濡傛灉鍒囨崲鍒拌嚜鍔ㄦā寮忎笖姝ｅ湪绛夊緟锛岀珛鍗崇户缁?
    if auto_mode and waiting_for_next_day:
        waiting_for_next_day = False

    return {"status": "ok", "auto_mode": auto_mode}

@app.route('/api/set_uls_mode', methods=['POST'])
def set_uls_mode():
    global uls_mode
    data = app.current_request.get_json() if hasattr(app, 'current_request') else None

    if not data:
        from flask import request
        data = request.get_json()

    uls_mode = data.get('uls_mode', False)
    return {"status": "ok", "uls_mode": uls_mode}

@app.route('/api/set_difficulty', methods=['POST'])
def set_difficulty():
    global current_difficulty, activated_modules
    data = app.current_request.get_json() if hasattr(app, 'current_request') else None

    if not data:
        from flask import request
        data = request.get_json()

    difficulty_level = data.get('difficulty', '鍩虹')
    current_difficulty = difficulty_level

    # 婵€娲诲搴旂殑妯″潡
    if DIFFICULTY_MODULES_ENABLED:
        activated_modules = activate_modules(difficulty_level, game_state)
        config = get_difficulty_config(difficulty_level)
        print(f"[DIFFICULTY] Activated {config['name']}: {config['modules']}")
    else:
        activated_modules = []

    return {"status": "ok", "difficulty": current_difficulty, "activated_modules": activated_modules}

@app.route('/api/get_difficulty_info', methods=['GET'])
def get_difficulty_info():
    return {
        "difficulty": current_difficulty,
        "activated_modules": activated_modules,
        "modules_enabled": DIFFICULTY_MODULES_ENABLED
    }

@app.route('/api/get_llm_config', methods=['GET'])
def get_llm_config():
    """鑾峰彇褰撳墠LLM閰嶇疆"""
    return {"status": "ok", "config": LLM_CONFIG}

@app.route('/api/set_llm_config', methods=['POST'])
def set_llm_config():
    global LLM_CONFIG

    try:
        from flask import request
        data = request.get_json()

        # 鏇存柊娴嬭瘯妯″瀷閰嶇疆
        if 'test_api_base' in data:
            LLM_CONFIG['test_api_base'] = data['test_api_base']
        if 'test_model' in data:
            LLM_CONFIG['test_model'] = data['test_model']

        # 鏇存柊NPC妯″瀷閰嶇疆
        if 'npc_api_base' in data:
            LLM_CONFIG['npc_api_base'] = data['npc_api_base']
        if 'npc_model' in data:
            LLM_CONFIG['npc_model'] = data['npc_model']

        print(f"[LLM_CONFIG] Updated:")
        print(f"  Test API: {LLM_CONFIG['test_api_base']} / {LLM_CONFIG['test_model']}")
        print(f"  NPC API:  {LLM_CONFIG['npc_api_base']} / {LLM_CONFIG['npc_model']}")

        # 淇濆瓨閰嶇疆鍒版枃浠?
        save_llm_config(LLM_CONFIG)

        return {"status": "ok", "config": LLM_CONFIG}
    except Exception as e:
        print(f"[LLM_CONFIG] Error updating config: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/api/set_token_limit', methods=['POST'])
def set_token_limit():
    global MAX_TOKENS_PER_PLAYER

    try:
        from flask import request
        data = request.get_json()
        new_limit = data.get('token_limit', 5000)

        # 楠岃瘉鑼冨洿
        if new_limit < 100 or new_limit > 100000:
            return {"status": "error", "message": "Token limit must be between 100 and 100000"}, 400

        MAX_TOKENS_PER_PLAYER = new_limit
        print(f"[TOKEN] Token limit updated to {MAX_TOKENS_PER_PLAYER} per player")

        return {"status": "ok", "token_limit": MAX_TOKENS_PER_PLAYER}
    except Exception as e:
        print(f"[TOKEN] Error updating token limit: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/api/switch_version', methods=['POST'])
def switch_version():
    try:
        from flask import request
        import shutil
        data = request.get_json()
        version = data.get('version', 'T1')

        if version not in ['T0', 'T1']:
            return {"status": "error", "message": "鏃犳晥鐨勭増鏈彿"}, 400

        base_dir = os.path.dirname(os.path.abspath(__file__))
        current_file = os.path.join(base_dir, 'werewolf_3panels.py')
        source_file = os.path.join(base_dir, f'werewolf_3panels_{version}.py')

        if not os.path.exists(source_file):
            return {"status": f"error", f"message": f"{version}鐗堟湰鏂囦欢涓嶅瓨鍦?}, 404

        # 澶囦唤褰撳墠鏂囦欢
        temp_file = os.path.join(base_dir, 'werewolf_3panels_temp.py')
        shutil.copy(current_file, temp_file)

        # 澶嶅埗鐩爣鐗堟湰
        shutil.copy(source_file, current_file)

        print(f"[VERSION] Switched to {version}")
        return {"status": f"ok", f"message": f"宸插垏鎹㈠埌{version}鐗堟湰"}
    except Exception as e:
        print(f"[VERSION] Error switching version: {e}")
        return {"status": "error", "message": str(e)}, 500

@app.route('/api/test_uls_understanding', methods=['POST'])
def test_uls_understanding():
    """娴嬭瘯LLM鏄惁鑳界悊瑙LS++缂栫爜"""
    try:
        from flask import request

        # 娴嬭瘯鐢ㄧ殑ULS++鏁版嵁
        test_prompt = """浣犳槸鐙间汉鏉€娓告垙涓殑Player 5锛堟潙姘戯級銆備互涓嬫槸鍏朵粬鐜╁鐨勫彂瑷€锛圲LS++缂栫爜鏍煎紡锛夛細

銆愮1澶╁彂瑷€銆?
[P0] PV:3|SUS:3@4.6,5@3.7|EV:+140
[P1] PV:3|SUS:3@4.8,7@2.1|EV:+140,+145
[P2] PV:7|SUS:7@4.2,3@3.5|EV:+145
[P3] PV:2|SUS:0@3.8,1@3.2|EV:+140,-118
[P4] PV:3|SUS:3@4.9,5@2.8|EV:+140,+150

ULS++鏍煎紡璇存槑锛?
- PV:X 琛ㄧず鎶曠エ缁欑帺瀹禭
- SUS:X@Y 琛ㄧず鎬€鐤戠帺瀹禭锛屽垎鏁癥锛堣秺楂樿秺鎬€鐤戯級
- EV:+N/-N 琛ㄧず鏀寔(+)鎴栧弽瀵?-)鏌愪釜璇佹嵁缂栧彿

鐜板湪璇蜂綘鍒嗘瀽锛?
1. 鏈夊灏戠帺瀹舵姇绁ㄧ粰Player 3锛?
2. 璋佹渶鎬€鐤慞layer 3锛堝垎鏁版渶楂橈級锛?
3. 璋佹姇绁ㄧ粰浜哖layer 7锛?

璇风畝鐭洖绛旓紙1-2鍙ヨ瘽锛夈€?""

        print(f"[ULS_TEST] Testing LLM understanding of ULS++ encoding...")

        # 鑾峰彇LLM閰嶇疆
        config = get_llm_config()

        # 璋冪敤LLM
        response = requests.post(
            f"{config['npc_api_base']}/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": config['npc_model'],
                "messages": [{"role": "user", "content": test_prompt}],
                "temperature": 0.1,
                "max_tokens": 200
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content']

            print(f"[ULS_TEST] LLM鍥炵瓟锛歕n{answer}\n")

            # 姝ｇ‘绛旀
            correct_answers = {
                "鎶曠エ缁橮3鐨勬暟閲?: 3,  # P0, P1, P4
                "鏈€鎬€鐤慞3鐨?: "P4",  # P4鐨凷US:3@4.9鏈€楂?
                "鎶曠エ缁橮7鐨?: "P2"   # 鍙湁P2鎶昉7
            }

            return {
                "status": "ok",
                "llm_answer": answer,
                "correct_answers": {
                    "q1": "鏈?涓帺瀹?P0, P1, P4)鎶曠エ缁橮layer 3",
                    "q2": "Player 4鏈€鎬€鐤慞layer 3 (鍒嗘暟4.9)",
                    "q3": "Player 2鎶曠エ缁橮layer 7"
                },
                "test_prompt": test_prompt
            }
        else:
            error_msg = f"LLM API璋冪敤澶辫触: {response.status_code}"
            print(f"[ULS_TEST] {error_msg}")
            return {"status": "error", "message": error_msg}, 500
    except Exception as e:
        error_msg = f"娴嬭瘯鍑洪敊: {str(e)}"
        print(f"[ULS_TEST] {error_msg}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": error_msg}, 500

@app.route('/api/test_evaluation', methods=['POST'])
def test_evaluation():
    """娴嬭瘯璇勪及鍔熻兘 - 娉ㄥ叆妯℃嫙鏁版嵁"""
    global game_evaluator, dialogue_queue

    if not EVALUATOR_ENABLED:
        return {"status": "error", "message": "璇勪及鍣ㄦ湭鍚敤"}, 400

    # 鍒濆鍖栬瘎浼板櫒(濡傛灉杩樻病鏈?
    if game_evaluator is None:
        game_evaluator = EnhancedReasoningEvaluator(test_subject_id=TEST_SUBJECT_ID)

    # 娉ㄥ叆娴嬭瘯鏁版嵁鍒癲ialogue_queue
    test_dialogues = [
        {"type": "dialogue", "player_id": TEST_SUBJECT_ID, "content": "Combinatorial reasoning: C(12,4)=495 but only wolf teams {2,5,10} or {2,5,11} align with the counter-claims, so I focus on those lines.", "round": 1, "phase": "day"},
        {"type": "dialogue", "player_id": TEST_SUBJECT_ID, "content": "Bayesian update: if Player 2 is real seer, posterior P(Player 10 is wolf) ~0.8; if fake it drops to ~0.3, so I side with Player 2.", "round": 1, "phase": "day"},
        {"type": "dialogue", "player_id": TEST_SUBJECT_ID, "content": "ANALYSIS: Player 3 mirrors Player 5's vote trail, signalling a pack. FINAL VOTE: Player 3", "round": 1, "phase": "voting"},
        {"type": "dialogue", "player_id": TEST_SUBJECT_ID, "content": "Information gain: the night kill on Player 4 shows the witch saved nobody and the guard missed, so I elevate seats never targeted.", "round": 2, "phase": "day"},
        {"type": "dialogue", "player_id": TEST_SUBJECT_ID, "content": "Complexity handling: prune the remaining wolf combinations down to {2,5,10} and {2,6,10}; prioritise players appearing in over 70% of viable lines.", "round": 2, "phase": "day"},
        {"type": "dialogue", "player_id": TEST_SUBJECT_ID, "content": "ANALYSIS: Vote entropy peaks at Player 6 after the counter-claim. FINAL VOTE: Player 6", "round": 2, "phase": "voting"},
    ]

    # 娓呯┖鐜版湁闃熷垪骞舵坊鍔犳祴璇曟暟鎹?
    while not dialogue_queue.empty():
        dialogue_queue.get()

    clear_dialogue_history()

    for dialogue in test_dialogues:
        dialogue_queue.put(dialogue)

    return {"status": "ok", "message": f"宸叉敞鍏len(test_dialogues)}鏉℃祴璇曟暟鎹埌dialogue_queue", "test_data_count": len(test_dialogues)}

@app.route('/api/get_evaluation', methods=['GET'])
def get_evaluation():
    """鑾峰彇璇勪及缁撴灉

    鏀寔鏌ヨ鍙傛暟:
    - player_id: 瑕佽瘎浼扮殑鐜╁ID (榛樿=7)
    """
    global game_evaluator, game_state, dialogue_queue

    # 妫€鏌ヨ瘎浼板櫒鏄惁鍚敤
    if not EVALUATOR_ENABLED:
        error_msg = f"璇勪及鍣ㄦ湭鍚敤銆傚鍏ラ敊璇? {EVALUATOR_IMPORT_ERROR}" if EVALUATOR_IMPORT_ERROR else "璇勪及鍣ㄦ湭鍚敤"
        print(f"[ERROR] {error_msg}")
        return {
            "status": "error",
            "message": error_msg,
            "debug_info": {
                "evaluator_enabled": EVALUATOR_ENABLED,
                "import_error": EVALUATOR_IMPORT_ERROR
            }
        }, 400

    # 妫€鏌ヨ瘎浼板櫒鏄惁鍒濆鍖?
    if game_evaluator is None:
        print(f"[ERROR] 璇勪及鍣ㄦ湭鍒濆鍖?)
        return {
            "status": "error",
            "message": "璇勪及鍣ㄦ湭鍒濆鍖栥€傝鍏堝紑濮嬫父鎴?,
            "debug_info": {
                "game_evaluator": None,
                "game_state": game_state
            }
        }, 400

    try:
        # 鑾峰彇鐩爣鐜╁ID (鏀寔鏌ヨ鍙傛暟)
        target_player_id = request.args.get('player_id', default=7, type=int)

        # 杞崲瀵硅瘽鍘嗗彶涓哄垪琛ㄦ牸寮?
        dialogue_history = get_dialogue_history_snapshot()

        print(f"[DEBUG get_evaluation] 鐩爣鐜╁: Player {target_player_id}")
        print(f"[DEBUG get_evaluation] dialogue_history length: {len(dialogue_history)}")
        print(f"[DEBUG get_evaluation] queue_size={dialogue_queue.qsize()}")
        print(f"[DEBUG get_evaluation] game_state: {game_state}")

        # 娓呯┖璇勪及鍣ㄤ箣鍓嶇殑鏁版嵁锛岄伩鍏嶉噸澶嶆坊鍔?
        game_evaluator.speeches = []
        game_evaluator.votes = []
        game_evaluator.events = []
        game_evaluator.side_changes = []

        # 鍚屾瀵硅瘽鍘嗗彶涓殑鐩爣鐜╁浜嬩欢鍒拌瘎浼板櫒
        target_player_count = 0
        all_player_ids = set()

        for dialogue in dialogue_history:
            player_id = dialogue.get('player_id')
            if player_id is not None and player_id >= 0:
                all_player_ids.add(player_id)

            if player_id == target_player_id:  # Track target player
                target_player_count += 1
                event_type = dialogue.get('type', 'dialogue')
                content = dialogue.get('content', '')
                phase = dialogue.get('phase', '')
                round_num = dialogue.get('round', 1)

                # Use ASCII encoding to avoid console encoding issues with emojis
                content_safe = content[:50].encode('ascii', 'replace').decode('ascii')
                print(f"[DEBUG] Player {target_player_id} event #{target_player_count}: phase={phase}, content_preview={content_safe}...")

                # Determine if this is a vote or speech based on phase and content
                is_vote = '鎶曠エ' in phase or content.startswith('馃棾锔?鎶曠エ缁?)

                if is_vote:
                    # Extract target from content like "馃棾锔?鎶曠エ缁?Player X"
                    import re
                    match = re.search(r'Player (\d+)', content)
                    target = int(match.group(1)) if match else None
                    game_evaluator.add_event('vote', player_id, content, round_num, {'target': target})
                    print(f"[DEBUG] Added vote event, target={target}")
                elif event_type == 'dialogue' and player_id > 0:  # Exclude system messages (player_id=-1)
                    game_evaluator.add_event('speech', player_id, content, round_num)
                    print(f"[DEBUG] Added speech event")

        print(f"[DEBUG get_evaluation] Player {target_player_id} events found: {target_player_count}")
        print(f"[DEBUG get_evaluation] 鎵€鏈夊嚭鐜拌繃鐨勭帺瀹禝D: {sorted(all_player_ids)}")
        print(f"[DEBUG get_evaluation] Player {target_player_id} speeches: {len(game_evaluator.speeches)}, votes: {len(game_evaluator.votes)}")

        # 濡傛灉娌℃湁鎵惧埌浠讳綍鐩爣鐜╁鐨勬暟鎹?杩斿洖鏈夌敤鐨勬彁绀?
        if target_player_count == 0:
            available_players = ', '.join(map(str, sorted(all_player_ids))) if all_player_ids else "鏃?
            return {
                "status": "error",
                "message": f"鏈壘鍒癙layer {target_player_id}鐨勬暟鎹€俓n\n瀵硅瘽闃熷垪鎬绘暟: {len(dialogue_history)}\n鍙敤鐜╁: {available_players}\n\n璇?\n1. 纭繚娓告垙宸插惎鍔ㄥ苟鑷冲皯涓€涓洖鍚堝凡瀹屾垚\n2. 灏濊瘯浣跨敤鍏朵粬鐜╁ID: ?player_id=<ID>\n3. 鎴栫偣鍑?馃И 娴嬭瘯璇勪及鍔熻兘'娉ㄥ叆娴嬭瘯鏁版嵁",
                "debug_info": {
                    "target_player_id": target_player_id,
                    "available_players": list(all_player_ids),
                    "dialogue_total": len(dialogue_history)
                }
            }, 400

        # 璁剧疆娓告垙涓婁笅鏂囦互鍚敤娣卞害鎺ㄧ悊璇勪及
        game_evaluator.set_game_context(game_state, dialogue_history)

        # 浣跨敤缁煎悎璇勫垎璁＄畻锛堝寘鍚繁搴︽帹鐞嗘寚鏍囷級
        eval_result = game_evaluator.calculate_comprehensive_score(include_deep_reasoning=True)

        # 娣诲姞缁熻鏁版嵁鍜屾椂闂存埑
        import time
        eval_result['stats'] = {
            'target_player_id': target_player_id,
            'speeches': len(game_evaluator.speeches),
            'votes': len(game_evaluator.votes),
            'side_changes': len(game_evaluator.side_changes),
            'dialogue_queue_size': len(dialogue_history),
            'target_player_events': target_player_count,
            'all_players': list(all_player_ids),
            'evaluation_timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }

        print(f"[SUCCESS] 璇勪及瀹屾垚: Player {target_player_id}, 寰楀垎: {eval_result.get('comprehensive_score', {}).get('overall_score', 'N/A')}")
        return {"status": "ok", "evaluation": eval_result}
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] 璇勪及澶辫触: {str(e)}")
        print(error_trace)
        return {
            "status": "error",
            "message": f"璇勪及澶辫触: {str(e)}\n\n璇︾粏閿欒璇锋煡鐪嬫湇鍔″櫒鏃ュ織",
            "debug_info": {
                "error_type": type(e).__name__,
                "error_msg": str(e)
            }
        }, 500

@app.route('/api/export_evaluation', methods=['GET'])
def export_evaluation():
    """瀵煎嚭璇勪及缁撴灉鍒癑SON鏂囦欢"""
    global game_evaluator

    if not EVALUATOR_ENABLED or game_evaluator is None:
        return {"status": "error", "message": "璇勪及鍣ㄤ笉鍙敤"}, 400

    try:
        filename = game_evaluator.export_json(f"evaluation_player{game_evaluator.test_subject_id}.json")
        return {"status": "ok", "filename": filename}
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/api/stream')
def stream():
    def generate():
        while True:
            try:
                data = dialogue_queue.get(timeout=1)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            except:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

    return app.response_class(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    import datetime
    VERSION_ID = f"CODE_VERSION_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print("="*70)
    print("鐙间汉鏉€ - 4瀵硅瘽妗嗙増鏈?)
    print(f"[OK] {VERSION_ID} - UPDATED CODE WITH AUTO MODE & DEBUG LOGGING")
    print("="*70)
    print("\n[INFO] Starting server on http://localhost:5004")
    print("[INFO] 娓告垙娴佺▼锛?)
    print("  1. 绗?澶滐細鐙间汉璁ㄨ锛堝垁璋併€佽皝涓婅锛?)
    print("  2. 绗?澶滐細绁炶亴琛屽姩")
    print("  3. 澶╀寒锛氳闀跨珵閫?)
    print("  4. 鐧藉ぉ锛氳璁烘姇绁?)
    print("  5. 澶滄櫄寰幆...")
    print("[INFO] UI锛?涓璇濇锛堢嫾浜?绁炶亴/鐧藉ぉ/缁熻锛?)
    print("="*70)

    app.run(host='127.0.0.1', port=5005, debug=False)
