import json
import os
import random
import threading
import time
from queue import Empty, Queue

import requests
from flask import Flask, Response, jsonify, render_template_string, request


app = Flask(__name__)


# ----------------------------------------------------------------------
# Game setup
# ----------------------------------------------------------------------
PLAYERS = [
    {"id": 0, "name": "Player 0", "role": "狼人", "emoji": "🐺"},
    {"id": 1, "name": "Player 1", "role": "狼人", "emoji": "🐺"},
    {"id": 2, "name": "Player 2", "role": "狼王", "emoji": "👑"},
    {"id": 3, "name": "Player 3", "role": "狼人", "emoji": "🐺"},
    {"id": 4, "name": "Player 4", "role": "村民", "emoji": "😀"},
    {"id": 5, "name": "Player 5", "role": "村民", "emoji": "😀"},
    {"id": 6, "name": "Player 6", "role": "村民", "emoji": "😀"},
    {"id": 7, "name": "Player 7", "role": "村民", "emoji": "😀"},
    {"id": 8, "name": "Player 8", "role": "预言家", "emoji": "🔮"},
    {"id": 9, "name": "Player 9", "role": "女巫", "emoji": "🧪"},
    {"id": 10, "name": "Player 10", "role": "猎人", "emoji": "🏹"},
    {"id": 11, "name": "Player 11", "role": "守卫", "emoji": "🛡️"},
]


CONFIG_FILE = "llm_config.json"


def load_llm_config() -> dict:
    defaults = {
        "test_api_base": "http://localhost:8080",
        "test_model": "/home/apulis-dev/userdata/Llama-3.3-70B-Instruct",
        "npc_api_base": "http://localhost:8080",
        "npc_model": "/home/apulis-dev/userdata/Llama-3.3-70B-Instruct",
        "temperature": 0.7,
        "max_tokens": 256,
        "timeout": 30,
    }

    if not os.path.exists(CONFIG_FILE):
        return defaults

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        print(f"[LLM_CONFIG] Failed to load {CONFIG_FILE}: {exc}")
        return defaults

    cfg = defaults.copy()
    for key, value in data.items():
        if key in cfg:
            cfg[key] = value
    return cfg


LLM_CONFIG = load_llm_config()
LLM_CONFIG.setdefault("timeout", 30)


# Dialog templates used as fallbacks when LLM is unavailable
WOLF_LINES = [
    "今晚刀掉谁？我觉得 {target} 不妙。",
    "低调一点，别太明显。",
    "我们投 {target}，理由充分。",
    "我来扛推，大家顺着我的节奏走。",
]
GOD_LINES = [
    "今晚我查验 {target}。",
    "我考虑救 {target}，他白天表现很好。",
    "{target} 的发言太假了，我要毒他。",
    "猎人准备好，必要时带走最狼的人。",
]
DAY_LINES = [
    "我觉得 {suspect} 昨晚行为异常，是狼人。",
    "票型出来了，{suspect} 的位置不安全。",
    "我身份清晰，请跟票我。",
    "{suspect} 逻辑漏洞太多了。",
]
VOTE_LINES = [
    "🗳️ 投票给 Player {target}",
    "🗳️ 投票给 Player {target}",
    "🗳️ 投票给 Player {target}",
]

OUTPUT_FORMAT_INSTRUCTION = """

【格式要求 - 必须遵守】
你可以先思考和推理，但最终必须按照以下格式输出：

OUTPUT: [你的最终发言或决策]
END

说明：
1. 你可以在 OUTPUT 之前进行推理（这段不会被公开）。
2. OUTPUT: 后面写最终要说的话。
3. 必须以 END 结尾。
4. 如果没有 END，会被视为无效响应。
"""

# Runtime state
event_queue: "Queue[dict]" = Queue()
dialogue_history: list[dict] = []
is_running = False
game_thread: threading.Thread | None = None
state_lock = threading.Lock()


# ----------------------------------------------------------------------
# Utility helpers
# ----------------------------------------------------------------------
def push_event(panel: str, message: str, *, player_id: int | None = None, phase: str = "") -> None:
    """Send an event to the frontend through the SSE queue."""
    event = {
        "panel": panel,
        "message": message,
        "player_id": player_id,
        "phase": phase,
        "timestamp": time.strftime("%H:%M:%S"),
    }
    event_queue.put(event)
    dialogue_history.append(event)
    if len(dialogue_history) > 200:
        dialogue_history.pop(0)


def random_player(exclude: set[int] | None = None) -> dict:
    exclude = exclude or set()
    choices = [p for p in PLAYERS if p["id"] not in exclude]
    return random.choice(choices)


def get_recent_history(panel: str, limit: int = 5) -> list[str]:
    lines: list[str] = []
    for item in reversed(dialogue_history):
        if item["panel"] == panel:
            lines.append(item["message"])
            if len(lines) >= limit:
                break
    lines.reverse()
    return lines


def call_llm(prompt: str, player_id: int, fallback: str) -> str:
    api_base = ""
    model = ""

    if player_id == 1:
        api_base = LLM_CONFIG.get("test_api_base", "")
        model = LLM_CONFIG.get("test_model", "")
    else:
        api_base = LLM_CONFIG.get("npc_api_base", "")
        model = LLM_CONFIG.get("npc_model", "")

    api_base = (api_base or "").rstrip("/")
    if not api_base or not model:
        return fallback

    full_prompt = prompt + OUTPUT_FORMAT_INSTRUCTION
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": full_prompt}],
        "temperature": LLM_CONFIG.get("temperature", 0.7),
        "max_tokens": LLM_CONFIG.get("max_tokens", 256),
    }

    url = f"{api_base}/v1/chat/completions"
    print(f"[LLM] Calling API for Player {player_id}...")
    print(f"[LLM]   URL: {url}")
    print(f"[LLM]   Model: {model}")
    print(f"[LLM]   Prompt preview: {prompt[:100]}...")

    try:
        response = requests.post(url, json=payload, timeout=LLM_CONFIG.get("timeout", 30))
        response.raise_for_status()
        data = response.json()
        message = data["choices"][0]["message"]
        raw_content = (message.get("content") or "").strip()
        reasoning_content = (message.get("reasoning_content") or "").strip()

        full_response = raw_content or reasoning_content
        if not full_response:
            print(f"[LLM] Empty response for Player {player_id}, using fallback.")
            return fallback

        import re

        has_output = re.search(r'(?:OUTPUT|output)\s*[:：]\s*(.+)', full_response, re.DOTALL | re.IGNORECASE)
        has_end = re.search(r'\bEND\b', full_response, re.IGNORECASE)

        if has_output and has_end:
            between = re.search(r'(?:OUTPUT|output)\s*[:：]\s*(.+?)\s*END', full_response, re.DOTALL | re.IGNORECASE)
            if between:
                content = between.group(1).strip()
                print(f"[LLM] [OK] Player {player_id} Output: {content[:80]}...")
                return content
            print(f"[LLM] [WARN] Player {player_id} format invalid, using fallback.")
            return fallback
        elif has_output:
            content = has_output.group(1).strip()
            print(f"[LLM] [WARN] Player {player_id} missing END, partial content used.")
            return content[:200]
        else:
            print(f"[LLM] [WARN] Player {player_id} no OUTPUT marker, using tail of response.")
            return full_response[-200:]
    except Exception as exc:
        print(f"[LLM] Error for Player {player_id}: {exc}")
        return fallback


def build_prompt(player: dict, panel: str, round_num: int, context: dict) -> str:
    history = get_recent_history(panel, limit=4)
    history_text = "\n".join(history) if history else "（暂无历史发言）"

    if panel == "werewolf":
        target_name = context.get("target_name", "某位好人")
        objective = f"你和同伴正在夜晚讨论，目标是在不暴露身份的前提下决定是否击杀 {target_name}。"
    elif panel == "god":
        objective = (
            "你是神职队伍的一员，在夜晚进行行动。"
            " 请谨慎分析当前局势，做出一条简短的行动宣言。"
        )
    elif panel == "day":
        suspect = context.get("suspect_name", "某个玩家")
        objective = (
            f"现在是白天，请结合昨夜信息和讨论，发表一段推理，重点评价 {suspect} 是否值得怀疑。"
        )
    elif panel == "vote":
        target = context.get("vote_target_id")
        objective = (
            f"现在进入投票环节，请给出最终投票决定。务必按照格式输出：'🗳️ 投票给 Player {target}'。"
        )
    else:
        objective = "请发表一段与狼人杀局势相关的简短发言。"

    prompt = (
        f"你正在参加一场 12 人狼人杀对局。\n"
        f"你的身份：{player['role']}，ID：{player['id']}，昵称：{player['name']}。\n"
        f"当前轮次：第 {round_num} 轮。\n"
        f"{objective}\n\n"
        "最近相关对话：\n"
        f"{history_text}\n\n"
        "输出要求：\n"
        "- 使用简短的中文第一人称表述（一两句即可）。\n"
        "- 注意保密自己的真实阵营，符合身份设定。\n"
        "- 不要描述游戏机制，只讨论当前局势。\n"
    )

    if panel == "vote":
        prompt += "- 严格按照指定格式输出投票决定，不要添加其他句子。\n"

    return prompt


def generate_message(
    player: dict,
    panel: str,
    round_num: int,
    fallback_templates: list[str],
    fallback_kwargs: dict,
    context: dict,
) -> str:
    fallback = random.choice(fallback_templates).format(**fallback_kwargs)
    prompt = build_prompt(player, panel, round_num, context)
    return call_llm(prompt, player["id"], fallback)


def simulate_game() -> None:
    """Background loop that emits simple scripted events."""
    round_num = 1
    push_event("log", "游戏开始，祝各位好运！", phase="system")

    while True:
        with state_lock:
            running = is_running
        if not running:
            push_event("log", "游戏暂停。", phase="system")
            return

        # Night phase: werewolves discuss
        push_event("log", f"--- 第 {round_num} 夜 ---", phase="night")
        wolves = [p for p in PLAYERS if "狼" in p["role"]]
        target = random_player({w["id"] for w in wolves})
        for wolf in wolves:
            line = generate_message(
                player=wolf,
                panel="werewolf",
                round_num=round_num,
                fallback_templates=WOLF_LINES,
                fallback_kwargs={"target": target["name"]},
                context={"target_name": target["name"]},
            )
            push_event("werewolf", f"{wolf['emoji']} {wolf['name']}: {line}", player_id=wolf["id"], phase="night")
            time.sleep(0.8)

        # Night phase: god roles act
        push_event("log", "神职开始行动。", phase="night")
        seer = next(p for p in PLAYERS if p["role"] == "预言家")
        witch = next(p for p in PLAYERS if p["role"] == "女巫")
        guard = next(p for p in PLAYERS if p["role"] == "守卫")

        for role_player in (seer, witch, guard):
            line = generate_message(
                player=role_player,
                panel="god",
                round_num=round_num,
                fallback_templates=GOD_LINES,
                fallback_kwargs={"target": random_player().get("name")},
                context={},
            )
            push_event(
                "god",
                f"{role_player['emoji']} {role_player['name']}: {line}",
                player_id=role_player["id"],
                phase="night",
            )
            time.sleep(0.8)

        time.sleep(1.2)

        # Day announcement
        push_event("log", f"第 {round_num} 天白天开始。", phase="day")

        # Day speeches
        alive = [p for p in PLAYERS]
        for speaker in random.sample(alive, k=min(5, len(alive))):
            suspect = random_player({speaker["id"]})
            line = generate_message(
                player=speaker,
                panel="day",
                round_num=round_num,
                fallback_templates=DAY_LINES,
                fallback_kwargs={"suspect": suspect["name"]},
                context={"suspect_name": suspect["name"]},
            )
            push_event("day", f"{speaker['emoji']} {speaker['name']}: {line}", player_id=speaker["id"], phase="day")
            time.sleep(0.9)

        # Voting
        push_event("log", "进入投票环节。", phase="vote")
        vote_target = random_player()
        for voter in random.sample(alive, k=len(alive)):
            line = generate_message(
                player=voter,
                panel="vote",
                round_num=round_num,
                fallback_templates=VOTE_LINES,
                fallback_kwargs={"target": vote_target["id"]},
                context={"vote_target_id": vote_target["id"]},
            )
            push_event("day", f"{voter['emoji']} {voter['name']}: {line}", player_id=voter["id"], phase="vote")
            time.sleep(0.4)

        push_event("statistics", f"第 {round_num} 天投票出局：{vote_target['name']}", phase="vote")
        push_event("log", f"第 {round_num} 天结束。", phase="system")

        round_num += 1
        time.sleep(2)


# ----------------------------------------------------------------------
# Flask views
# ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template_string(
        TEMPLATE,
        players=PLAYERS,
    )


@app.route("/api/start", methods=["POST"])
def api_start():
    global game_thread, is_running
    with state_lock:
        if is_running:
            return jsonify({"status": "already_running"})
        is_running = True

    game_thread = threading.Thread(target=simulate_game, daemon=True)
    game_thread.start()
    return jsonify({"status": "started"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    global is_running
    with state_lock:
        is_running = False
    return jsonify({"status": "stopped"})


@app.route("/api/clear", methods=["POST"])
def api_clear():
    """Allow frontend to reset panels."""
    cleared = 0
    while True:
        try:
            event_queue.get_nowait()
            cleared += 1
        except Empty:
            break
    return jsonify({"status": "cleared", "items": cleared})


@app.route("/api/stream")
def api_stream():
    def stream():
        while True:
            event = event_queue.get()
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    return Response(stream(), mimetype="text/event-stream")


@app.route("/api/llm_config", methods=["GET", "POST"])
def api_llm_config():
    global LLM_CONFIG
    if request.method == "GET":
        return jsonify({"status": "ok", "config": LLM_CONFIG})

    data = request.get_json(force=True, silent=True) or {}

    for key in (
        "test_api_base",
        "test_model",
        "npc_api_base",
        "npc_model",
        "temperature",
        "max_tokens",
        "timeout",
    ):
        if key in data:
            LLM_CONFIG[key] = data[key]

    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as handle:
            json.dump(LLM_CONFIG, handle, ensure_ascii=False, indent=2)
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500

    return jsonify({"status": "ok", "config": LLM_CONFIG})


# ----------------------------------------------------------------------
# Frontend template
# ----------------------------------------------------------------------
TEMPLATE = """
<!doctype html>
<html lang="zh">
<head>
    <meta charset="utf-8">
    <title>狼人杀 - 简易控制面板</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            margin: 0;
            padding: 0;
            color: #f3f4f6;
        }
        header {
            text-align: center;
            padding: 24px 16px 8px 16px;
        }
        h1 {
            margin: 0;
            font-size: 32px;
        }
        .controls {
            text-align: center;
            margin-bottom: 24px;
        }
        button {
            background: #f3f4f6;
            color: #1e3c72;
            border: none;
            border-radius: 6px;
            padding: 10px 24px;
            margin: 0 8px;
            font-size: 16px;
            cursor: pointer;
        }
        button:hover {
            opacity: 0.85;
        }
        .layout {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            grid-gap: 16px;
            padding: 0 24px 32px 24px;
        }
        .panel {
            background: rgba(17, 24, 39, 0.8);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            height: 420px;
        }
        .panel h2 {
            margin: 0 0 12px 0;
            font-size: 18px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding-bottom: 8px;
        }
        .panel-content {
            flex: 1;
            overflow-y: auto;
            font-size: 14px;
            line-height: 1.5;
            padding-right: 8px;
        }
        .event {
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px dashed rgba(255, 255, 255, 0.08);
        }
        .timestamp {
            font-size: 12px;
            color: #9ca3af;
        }
        .players {
            margin: 0 auto 24px auto;
            max-width: 960px;
            background: rgba(17, 24, 39, 0.7);
            border-radius: 12px;
            padding: 16px;
        }
        .players h3 {
            margin: 0 0 12px 0;
            font-size: 18px;
        }
        .player-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            grid-gap: 12px;
        }
        .player-card {
            background: rgba(255, 255, 255, 0.06);
            border-radius: 8px;
            padding: 12px;
            text-align: center;
        }
        .player-card span {
            display: block;
        }
    </style>
</head>
<body>
    <header>
        <h1>狼人杀 - 12 人简易版</h1>
        <p>快速演示用 UI，包含夜晚、神职、白天、统计四个面板。</p>
    </header>

    <div class="controls">
        <button onclick="startGame()">▶️ 开始游戏</button>
        <button onclick="stopGame()">⏹️ 停止</button>
        <button onclick="clearPanels()">🧹 清空面板</button>
    </div>

    <section class="players">
        <h3>玩家阵容</h3>
        <div class="player-grid">
            {% for player in players %}
            <div class="player-card">
                <span style="font-size: 24px;">{{ player.emoji }}</span>
                <span>{{ player.name }}</span>
                <span style="font-size: 12px; color: #9ca3af;">{{ player.role }}</span>
            </div>
            {% endfor %}
        </div>
    </section>

    <section class="layout">
        <div class="panel">
            <h2>🐺 夜晚 - 狼人对话</h2>
            <div id="panel-werewolf" class="panel-content"></div>
        </div>
        <div class="panel">
            <h2>🌙 夜晚 - 神职行动</h2>
            <div id="panel-god" class="panel-content"></div>
        </div>
        <div class="panel">
            <h2>☀️ 白天 - 讨论投票</h2>
            <div id="panel-day" class="panel-content"></div>
        </div>
        <div class="panel">
            <h2>📊 统计 & 系统日志</h2>
            <div id="panel-statistics" class="panel-content"></div>
        </div>
    </section>

    <script>
        const panelMap = {
            "werewolf": document.getElementById("panel-werewolf"),
            "god": document.getElementById("panel-god"),
            "day": document.getElementById("panel-day"),
            "statistics": document.getElementById("panel-statistics"),
            "log": document.getElementById("panel-statistics"),
        };

        function prependEvent(panelId, message, timestamp) {
            const target = panelMap[panelId] || panelMap["log"];
            const div = document.createElement("div");
            div.className = "event";
            div.innerHTML = `<div>${message}</div><div class="timestamp">${timestamp}</div>`;
            target.insertBefore(div, target.firstChild);
        }

        function startGame() {
            fetch("/api/start", {method: "POST"})
                .then(r => r.json())
                .then(data => prependEvent("log", `系统: ${data.status}`, new Date().toLocaleTimeString()));
        }

        function stopGame() {
            fetch("/api/stop", {method: "POST"})
                .then(r => r.json())
                .then(data => prependEvent("log", `系统: ${data.status}`, new Date().toLocaleTimeString()));
        }

        function clearPanels() {
            Object.values(panelMap).forEach(panel => panel.innerHTML = "");
            fetch("/api/clear", {method: "POST"})
                .then(r => r.json())
                .then(data => prependEvent("log", `系统: 清空队列 ${data.items} 条`, new Date().toLocaleTimeString()));
        }

        function connectStream() {
            const source = new EventSource("/api/stream");
            source.onmessage = (event) => {
                const data = JSON.parse(event.data);
                prependEvent(data.panel, data.message, data.timestamp);
            };
            source.onerror = () => {
                prependEvent("log", "系统: 流断开，尝试重连...", new Date().toLocaleTimeString());
                source.close();
                setTimeout(connectStream, 3000);
            };
        }

        connectStream();
    </script>
</body>
</html>
"""


if __name__ == "__main__":
    print("狼人杀简易版 UI 启动于 http://127.0.0.1:5010")
    app.run(host="127.0.0.1", port=5010, debug=False)
