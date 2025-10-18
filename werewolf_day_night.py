"""
狼人杀完整昼夜循环系统
Werewolf Game with Complete Day/Night Cycle
包含：警长竞选、夜晚行动、白天讨论
"""

from flask import Flask, render_template_string
import requests
import json
import threading
import time
from queue import Queue
import random

app = Flask(__name__)

# 全局变量
dialogue_queue = Queue()
is_running = False
seer_claims = []
sheriff_player_id = None
game_state = {
    "phase": "day",  # day or night
    "round": 0,
    "dead_players": [],
    "night_actions": {}
}

# 12个玩家配置
PLAYERS = [
    {"id": 0, "role": "狼人", "emoji": "🐺", "color": "#f44336", "alive": True},
    {"id": 1, "role": "狼人", "emoji": "🐺", "color": "#f44336", "alive": True},
    {"id": 2, "role": "狼人", "emoji": "🐺", "color": "#f44336", "alive": True},
    {"id": 3, "role": "狼王", "emoji": "👑", "color": "#d32f2f", "alive": True},
    {"id": 4, "role": "村民", "emoji": "👨‍🌾", "color": "#4CAF50", "alive": True},
    {"id": 5, "role": "村民", "emoji": "👨‍🌾", "color": "#4CAF50", "alive": True},
    {"id": 6, "role": "村民", "emoji": "👨‍🌾", "color": "#4CAF50", "alive": True},
    {"id": 7, "role": "村民", "emoji": "👨‍🌾", "color": "#4CAF50", "alive": True},
    {"id": 8, "role": "预言家", "emoji": "👁️", "color": "#2196F3", "alive": True},
    {"id": 9, "role": "女巫", "emoji": "🧪", "color": "#9C27B0", "alive": True},
    {"id": 10, "role": "猎人", "emoji": "🏹", "color": "#FF9800", "alive": True},
    {"id": 11, "role": "守卫", "emoji": "🛡️", "color": "#00BCD4", "alive": True},
]

# LLM配置
LLM_CONFIG = {
    "api_base": "http://localhost:8080",
    "model": "/home/apulis-dev/userdata/Llama-3.3-70B-Instruct",
    "temperature": 0.7,
    "max_tokens": 200
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Werewolf Day/Night Cycle</title>
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
            max-width: 1400px;
            margin: 0 auto;
        }

        h1 {
            text-align: center;
            color: white;
            font-size: 32px;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .controls {
            text-align: center;
            margin-bottom: 30px;
        }

        button {
            padding: 15px 40px;
            font-size: 18px;
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
            grid-template-columns: 1fr 600px;
            gap: 20px;
        }

        .circle-area {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            position: relative;
            height: 700px;
        }

        .circle-container {
            position: relative;
            width: 600px;
            height: 600px;
            margin: 50px auto;
        }

        .center-circle {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 150px;
            height: 150px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
            box-shadow: 0 8px 20px rgba(0,0,0,0.3);
        }

        .player-circle {
            position: absolute;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            background: white;
            border: 4px solid;
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
            border-width: 6px;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.8);
        }

        .player-circle.sheriff::after {
            content: '🎖️';
            position: absolute;
            top: -5px;
            right: -5px;
            font-size: 20px;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }

        .player-name {
            font-size: 10px;
            font-weight: bold;
            margin-top: 3px;
        }

        .dialogue-area {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            height: 700px;
            display: flex;
            flex-direction: column;
        }

        .dialogue-header {
            font-size: 22px;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }

        .dialogue-output {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 8px;
        }

        .dialogue-item {
            margin-bottom: 20px;
            padding: 15px;
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
            font-size: 16px;
            margin-bottom: 8px;
        }

        .dialogue-content {
            color: #333;
            line-height: 1.6;
            font-size: 14px;
        }

        .dialogue-meta {
            color: #999;
            font-size: 12px;
            margin-top: 8px;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>🎮 狼人杀 - 昼夜循环系统</h1>

        <div class="status-info" id="status">
            状态：等待开始
        </div>

        <div class="controls">
            <button onclick="startGame()" id="btn-start">▶️ 开始游戏</button>
            <button onclick="stopGame()" id="btn-stop" disabled>⏹️ 停止</button>
            <button onclick="clearDialogue()">🗑️ 清空</button>
        </div>

        <div class="main-area">
            <div class="circle-area">
                <div class="circle-container" id="circle-container">
                    <div class="center-circle">
                        🐺<br>狼人杀
                    </div>
                </div>
            </div>

            <div class="dialogue-area">
                <div class="dialogue-header">💬 实时对话</div>
                <div class="dialogue-output" id="dialogue-output">
                    <div style="color: #999; text-align: center; padding: 20px;">
                        等待游戏开始...
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const players = {{ players | tojson }};
        let eventSource = null;
        let currentPhase = 'day';

        function createCircle() {
            const container = document.getElementById('circle-container');
            const radius = 250;
            const centerX = 300;
            const centerY = 300;

            players.forEach((player, index) => {
                const angle = (index / players.length) * 2 * Math.PI - Math.PI / 2;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);

                const div = document.createElement('div');
                div.className = 'player-circle';
                div.id = 'player-' + player.id;
                div.style.left = (x - 40) + 'px';
                div.style.top = (y - 40) + 'px';
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
            const output = document.getElementById('dialogue-output');

            if (output.innerHTML.includes('等待游戏开始')) {
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
            playerDiv.textContent = player.emoji + ' Player ' + player.id + ' (' + player.role + ')';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'dialogue-content';

            const metaDiv = document.createElement('div');
            metaDiv.className = 'dialogue-meta';
            metaDiv.textContent = (data.phase || '') + ' | ' + new Date().toLocaleTimeString();

            item.appendChild(playerDiv);
            item.appendChild(contentDiv);
            item.appendChild(metaDiv);

            output.insertBefore(item, output.firstChild);

            // Typewriter effect
            const text = data.content;
            let index = 0;

            function typeChar() {
                if (index < text.length) {
                    contentDiv.textContent += text[index];
                    index++;
                    setTimeout(typeChar, 30);
                }
            }

            typeChar();
        }

        function startGame() {
            document.getElementById('btn-start').disabled = true;
            document.getElementById('btn-stop').disabled = false;

            fetch('/api/start', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    console.log('Started:', data);
                    startEventStream();
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

        function clearDialogue() {
            document.getElementById('dialogue-output').innerHTML =
                '<div style="color: #999; text-align: center; padding: 20px;">等待游戏开始...</div>';
        }

        function startEventStream() {
            if (eventSource) eventSource.close();

            eventSource = new EventSource('/api/stream');

            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);

                if (data.type === 'phase') {
                    setPhase(data.phase);
                    if (data.phase === 'night') {
                        // Hide non-werewolf players during night
                        players.forEach((p, i) => {
                            if (!['狼人', '狼王'].includes(p.role)) {
                                hidePlayer(i);
                            }
                        });
                    } else {
                        // Show all players during day
                        players.forEach((p, i) => showPlayer(i));
                    }
                } else if (data.type === 'dialogue') {
                    if (data.player_id === -1 && data.content.includes('当选警长')) {
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
                    document.getElementById('status').textContent = '状态：' + data.message;
                } else if (data.type === 'death') {
                    markDead(data.player_id);
                }
            };

            eventSource.onerror = function() {
                console.error('EventSource error');
                eventSource.close();
            };
        }

        window.addEventListener('load', () => {
            createCircle();
        });
    </script>
</body>
</html>
"""

def call_llm(prompt, player_id):
    """调用LLM API"""
    try:
        url = f"{LLM_CONFIG['api_base']}/v1/chat/completions"
        payload = {
            "model": LLM_CONFIG["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": LLM_CONFIG["temperature"],
            "max_tokens": LLM_CONFIG["max_tokens"]
        }

        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        print(f"[LLM] Player {player_id}: {content[:50]}...")
        return content

    except Exception as e:
        print(f"[LLM] Error for Player {player_id}: {e}")
        return f"[Player {player_id} 暂时无法发言]"

def sheriff_election():
    """警长竞选"""
    print("\n[SHERIFF ELECTION] Starting...")

    dialogue_queue.put({
        "type": "status",
        "message": "🎖️ 警长竞选开始"
    })

    # 随机3-5个玩家上警
    num_candidates = random.randint(3, 5)
    candidates = random.sample(range(len(PLAYERS)), num_candidates)

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "警长竞选",
        "content": f"🎖️ 竞选警长: {', '.join(['Player ' + str(c) for c in candidates])}"
    })

    # 候选人依次发言 - 必须跳预言家并报验人
    for candidate_id in candidates:
        if not is_running:
            break

        player = PLAYERS[candidate_id]

        # 随机验人目标
        other_players = [p for p in range(len(PLAYERS)) if p != player['id']]
        checked_player = random.choice(other_players)
        checked_role = PLAYERS[checked_player]['role']
        is_werewolf = checked_role in ['狼人', '狼王']

        if player['role'] == '预言家':
            instruction = f"你是真预言家。昨晚验了Player {checked_player}，他是{'狼人' if is_werewolf else '好人'}。必须说'我是预言家'并报告这个结果。"
        else:
            fake_result = "狼人" if random.random() > 0.6 else "好人"
            instruction = f"你必须跳预言家（说'我是预言家'）并编造验人结果，例如'昨晚我验了Player {checked_player}，他是{fake_result}'。"

        prompt = f"""狼人杀游戏 - 警长竞选阶段。
你是Player {player['id']}，角色{player['role']}。

{instruction}

请用2-3句话竞选发言。用中文。"""

        response = call_llm(prompt, player['id'])

        # Track seer claims
        if "我是预言家" in response or "预言家" in response:
            seer_claims.append(player['id'])

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": player['id'],
            "phase": "警长竞选",
            "content": response
        })

        time.sleep(1.5)

    # 选举警长
    global sheriff_player_id
    sheriff_id = random.choice(candidates)
    sheriff_player_id = sheriff_id
    PLAYERS[sheriff_id]['is_sheriff'] = True

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "警长竞选",
        "content": f"🎖️ Player {sheriff_id} 当选警长！"
    })

    time.sleep(2)
    print(f"[SHERIFF] Player {sheriff_id} elected. Seer claims: {seer_claims}")

def night_werewolf_discussion():
    """夜晚 - 狼人讨论和行动（所有玩家闭眼，只有狼人睁眼）"""
    print("\n[NIGHT] Werewolf phase - All players close eyes, werewolves open eyes...")

    dialogue_queue.put({
        "type": "phase",
        "phase": "night"
    })

    dialogue_queue.put({
        "type": "status",
        "message": "🌙 天黑请闭眼 - 狼人请睁眼"
    })

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "夜晚-狼人行动",
        "content": "🌙 所有玩家闭眼... 狼人请睁眼，认识彼此，并选择一个玩家击杀。"
    })

    # 获取活着的狼人
    werewolves = [p for p in PLAYERS if p['role'] in ['狼人', '狼王'] and p['alive']]

    if not werewolves:
        return None

    # 狼人们看到彼此，依次发言讨论
    alive_non_wolves = [p for p in PLAYERS if p['alive'] and p['role'] not in ['狼人', '狼王']]

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "夜晚-狼人行动",
        "content": f"🐺 狼人们相互认识。存活的狼人：{', '.join([f'Player {w['id']}' for w in werewolves])}"
    })

    time.sleep(1)

    # 狼人们依次发言讨论（只有狼人能看到）
    for wolf in werewolves:
        if not is_running:
            break

        prompt = f"""狼人杀游戏 - 夜晚阶段，狼人内部秘密讨论。
你是Player {wolf['id']}，角色{wolf['role']}（狼人阵营）。

队友：{', '.join([f"Player {w['id']}" for w in werewolves if w['id'] != wolf['id']])}
可以击杀的玩家：{', '.join([f"Player {p['id']}" for p in alive_non_wolves])}

请简短建议（1-2句）：
- 建议击杀哪个玩家？
- 为什么选择这个目标？

用中文回答。"""

        response = call_llm(prompt, wolf['id'])

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": wolf['id'],
            "phase": "夜晚-狼人讨论",
            "content": f"[狼人内部] {response}"
        })

        time.sleep(1)

    # 狼人达成一致，选择击杀目标
    if alive_non_wolves:
        target = random.choice(alive_non_wolves)
        game_state['night_actions']['werewolf_kill'] = target['id']

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": "夜晚-狼人行动",
            "content": f"🐺 狼人统一决定：击杀 Player {target['id']}"
        })

        dialogue_queue.put({
            "type": "status",
            "message": "狼人请闭眼"
        })

        time.sleep(2)
        return target['id']

    return None

def night_seer_action():
    """夜晚 - 预言家验人（所有玩家闭眼，只有预言家睁眼）"""
    print("\n[NIGHT] Seer action - All players close eyes, seer opens eyes...")

    dialogue_queue.put({
        "type": "status",
        "message": "👁️ 预言家请睁眼"
    })

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "夜晚-预言家",
        "content": "👁️ 预言家请睁眼，选择一个玩家查验身份。"
    })

    seer = next((p for p in PLAYERS if p['role'] == '预言家' and p['alive']), None)

    if not seer:
        dialogue_queue.put({
            "type": "status",
            "message": "预言家请闭眼"
        })
        return

    alive_others = [p for p in PLAYERS if p['alive'] and p['id'] != seer['id']]

    if alive_others:
        target = random.choice(alive_others)
        is_wolf = target['role'] in ['狼人', '狼王']

        prompt = f"""狼人杀 - 夜晚阶段，预言家验人。
你是Player {seer['id']}，真预言家。

你验了Player {target['id']}，结果：他是{'狼人' if is_wolf else '好人'}。

请简短思考（1句话）：这个信息如何帮助你明天的发言？

用中文回答。"""

        response = call_llm(prompt, seer['id'])

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": seer['id'],
            "phase": "夜晚-预言家",
            "content": f"[验人] Player {target['id']} 是{'狼人' if is_wolf else '好人'}。{response}"
        })

        game_state['night_actions']['seer_check'] = {
            'target': target['id'],
            'is_wolf': is_wolf
        }

    dialogue_queue.put({
        "type": "status",
        "message": "预言家请闭眼"
    })

    time.sleep(2)

def night_witch_action(kill_target):
    """夜晚 - 女巫行动（所有玩家闭眼，只有女巫睁眼）
    标准规则：女巫不能在同一夜使用两种药"""
    print("\n[NIGHT] Witch action - All players close eyes, witch opens eyes...")

    dialogue_queue.put({
        "type": "status",
        "message": "🧪 女巫请睁眼"
    })

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "夜晚-女巫",
        "content": "🧪 女巫请睁眼，可以使用解药或毒药（不能同时使用）。"
    })

    witch = next((p for p in PLAYERS if p['role'] == '女巫' and p['alive']), None)

    if not witch:
        dialogue_queue.put({
            "type": "status",
            "message": "女巫请闭眼"
        })
        return

    if kill_target is None:
        dialogue_queue.put({
            "type": "status",
            "message": "女巫请闭眼"
        })
        return

    # 女巫知道谁被杀
    # 随机决定是否使用药，但不能同时使用
    action_choice = random.random()

    if action_choice > 0.7:  # 30% 使用解药
        action = "antidote"
    elif action_choice > 0.5:  # 20% 使用毒药
        action = "poison"
    else:  # 50% 什么都不做
        action = "none"

    prompt = f"""狼人杀 - 夜晚阶段，女巫行动。
你是Player {witch['id']}，女巫。

今晚Player {kill_target}被狼人击杀。
你可以：
1. 使用解药救他（解药只能用一次）
2. 使用毒药毒死另一个人（毒药只能用一次）
3. 什么都不做

**重要：不能在同一夜同时使用两种药！**

请简短决定（1句话）你的行动。用中文。"""

    response = call_llm(prompt, witch['id'])

    # 执行女巫决策（确保只执行一个行动）
    used_potion = False

    if not used_potion and ("解药" in response or "救" in response):
        game_state['night_actions']['witch_save'] = kill_target
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": witch['id'],
            "phase": "夜晚-女巫",
            "content": f"[使用解药] 救了 Player {kill_target}"
        })
        used_potion = True
    elif not used_potion and "毒" in response:
        alive_others = [p for p in PLAYERS if p['alive'] and p['id'] != witch['id'] and p['id'] != kill_target]
        if alive_others:
            poison_target = random.choice(alive_others)
            game_state['night_actions']['witch_poison'] = poison_target['id']
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": witch['id'],
                "phase": "夜晚-女巫",
                "content": f"[使用毒药] 毒杀 Player {poison_target['id']}"
            })
            used_potion = True

    if not used_potion:
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": witch['id'],
            "phase": "夜晚-女巫",
            "content": "[不使用药] 今晚什么都不做"
        })

    dialogue_queue.put({
        "type": "status",
        "message": "女巫请闭眼"
    })

    time.sleep(2)

def night_guard_action():
    """夜晚 - 守卫守护（所有玩家闭眼，只有守卫睁眼）"""
    print("\n[NIGHT] Guard action - All players close eyes, guard opens eyes...")

    dialogue_queue.put({
        "type": "status",
        "message": "🛡️ 守卫请睁眼"
    })

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "夜晚-守卫",
        "content": "🛡️ 守卫请睁眼，选择一个玩家进行守护。"
    })

    guard = next((p for p in PLAYERS if p['role'] == '守卫' and p['alive']), None)

    if not guard:
        dialogue_queue.put({
            "type": "status",
            "message": "守卫请闭眼"
        })
        return

    alive_others = [p for p in PLAYERS if p['alive'] and p['id'] != guard['id']]

    if alive_others:
        target = random.choice(alive_others)
        game_state['night_actions']['guard_protect'] = target['id']

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": guard['id'],
            "phase": "夜晚-守卫",
            "content": f"[守护] 守护 Player {target['id']}"
        })

    dialogue_queue.put({
        "type": "status",
        "message": "守卫请闭眼"
    })

    time.sleep(2)

def day_discussion(round_num):
    """白天讨论阶段"""
    print(f"\n[DAY] Round {round_num} discussion...")

    dialogue_queue.put({
        "type": "phase",
        "phase": "day"
    })

    dialogue_queue.put({
        "type": "status",
        "message": f"☀️ 天亮了 - 第{round_num}天讨论"
    })

    # 公布夜晚死亡
    dead_tonight = []

    kill_target = game_state['night_actions'].get('werewolf_kill')
    saved = game_state['night_actions'].get('witch_save')
    poisoned = game_state['night_actions'].get('witch_poison')
    protected = game_state['night_actions'].get('guard_protect')

    # 处理死亡
    if kill_target and kill_target != saved and kill_target != protected:
        PLAYERS[kill_target]['alive'] = False
        dead_tonight.append(kill_target)

    if poisoned:
        PLAYERS[poisoned]['alive'] = False
        dead_tonight.append(poisoned)

    if dead_tonight:
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"第{round_num}天",
            "content": f"💀 昨晚死亡：{', '.join([f'Player {p}' for p in dead_tonight])}"
        })

        for player_id in dead_tonight:
            dialogue_queue.put({
                "type": "death",
                "player_id": player_id
            })
    else:
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"第{round_num}天",
            "content": "🎉 昨晚是平安夜，无人死亡"
        })

    time.sleep(2)

    # 白天发言 - 随机顺序
    alive_players = [p for p in PLAYERS if p['alive']]
    random.shuffle(alive_players)

    for player in alive_players:
        if not is_running:
            break

        is_seer_claimer = player['id'] in seer_claims
        sheriff_info = "你是警长。" if player.get('is_sheriff') else ""

        if is_seer_claimer:
            # 跳预言家的继续报验人
            other_alive = [p for p in PLAYERS if p['alive'] and p['id'] != player['id']]
            if other_alive:
                checked = random.choice(other_alive)
                is_wolf = checked['role'] in ['狼人', '狼王']

                instruction = f"你昨晚验了Player {checked['id']}，他是{'狼人' if is_wolf else '好人'}。必须报告验人结果。"
            else:
                instruction = "报告你的验人情况。"
        elif player['role'] in ['女巫', '猎人', '守卫']:
            instruction = "不要暴露身份。以村民身份分析局势。"
        elif player['role'] in ['狼人', '狼王']:
            instruction = "装成村民，误导好人，质疑预言家。"
        else:
            instruction = "诚实分析，帮助找出狼人。"

        prompt = f"""狼人杀 - 第{round_num}天讨论。
你是Player {player['id']}，角色{player['role']}。{sheriff_info}

昨晚死亡：{dead_tonight if dead_tonight else '无人死亡'}

{instruction}

请简短发言（1-2句）。用中文。"""

        response = call_llm(prompt, player['id'])

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": player['id'],
            "phase": f"第{round_num}天讨论",
            "content": response
        })

        time.sleep(1)

    # 投票和处决阶段
    voting_and_execution(round_num, dead_tonight)

    # 清空夜晚行动记录
    game_state['night_actions'] = {}

def voting_and_execution(round_num, dead_tonight):
    """投票和处决阶段"""
    print(f"\n[DAY] Voting phase - Round {round_num}")

    dialogue_queue.put({
        "type": "status",
        "message": "🗳️ 投票阶段"
    })

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"第{round_num}天投票",
        "content": "🗳️ 现在进入投票阶段，请所有玩家投票选择要处决的玩家。"
    })

    time.sleep(2)

    alive_players = [p for p in PLAYERS if p['alive']]

    if len(alive_players) < 2:
        return None

    # 统计投票（简化版：随机选择一个玩家被投票处决）
    # 可以是被投票最多的玩家
    vote_target = random.choice(alive_players)

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"第{round_num}天投票",
        "content": f"🗳️ 投票结果：Player {vote_target['id']} 得票最多，将被处决。"
    })

    time.sleep(2)

    # 处决玩家
    vote_target['alive'] = False

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"第{round_num}天投票",
        "content": f"⚰️ Player {vote_target['id']} ({vote_target['role']}) 被投票处决。"
    })

    dialogue_queue.put({
        "type": "death",
        "player_id": vote_target['id']
    })

    time.sleep(1)

    # 猎人技能：如果猎人被处决，可以开枪带走一个玩家
    if vote_target['role'] == '猎人':
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": vote_target['id'],
            "phase": f"第{round_num}天-猎人开枪",
            "content": "🏹 猎人被处决，发动技能！"
        })

        other_alive = [p for p in PLAYERS if p['alive']]
        if other_alive:
            hunter_target = random.choice(other_alive)

            dialogue_queue.put({
                "type": "dialogue",
                "player_id": vote_target['id'],
                "phase": f"第{round_num}天-猎人开枪",
                "content": f"🏹 猎人开枪带走 Player {hunter_target['id']}"
            })

            hunter_target['alive'] = False

            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": f"第{round_num}天-猎人开枪",
                "content": f"⚰️ Player {hunter_target['id']} ({hunter_target['role']}) 被猎人枪杀。"
            })

            dialogue_queue.put({
                "type": "death",
                "player_id": hunter_target['id']
            })

            time.sleep(2)

    # 狼王技能：如果狼王被投票处决（不是夜晚被杀），可以带走一个玩家
    elif vote_target['role'] == '狼王':
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": vote_target['id'],
            "phase": f"第{round_num}天-狼王自爆",
            "content": "👑 狼王被处决，发动技能！"
        })

        other_alive = [p for p in PLAYERS if p['alive']]
        if other_alive:
            wolf_king_target = random.choice(other_alive)

            dialogue_queue.put({
                "type": "dialogue",
                "player_id": vote_target['id'],
                "phase": f"第{round_num}天-狼王自爆",
                "content": f"👑 狼王带走 Player {wolf_king_target['id']}"
            })

            wolf_king_target['alive'] = False

            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": f"第{round_num}天-狼王自爆",
                "content": f"⚰️ Player {wolf_king_target['id']} ({wolf_king_target['role']}) 被狼王带走。"
            })

            dialogue_queue.put({
                "type": "death",
                "player_id": wolf_king_target['id']
            })

            time.sleep(2)

    # 检查警长是否被处决，需要传递警徽
    global sheriff_player_id
    if vote_target.get('is_sheriff') and sheriff_player_id == vote_target['id']:
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"第{round_num}天投票",
            "content": "🎖️ 警长被处决，警徽需要传递..."
        })

        alive_players = [p for p in PLAYERS if p['alive']]
        if alive_players:
            new_sheriff = random.choice(alive_players)
            new_sheriff['is_sheriff'] = True
            sheriff_player_id = new_sheriff['id']

            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": f"第{round_num}天投票",
                "content": f"🎖️ 警徽传递给 Player {new_sheriff['id']}"
            })

            time.sleep(1)

    return vote_target['id']

def check_win_condition():
    """检查游戏胜利条件"""
    alive_players = [p for p in PLAYERS if p['alive']]
    alive_werewolves = [p for p in alive_players if p['role'] in ['狼人', '狼王']]
    alive_villagers = [p for p in alive_players if p['role'] not in ['狼人', '狼王']]

    # 狼人胜利：狼人数量 >= 好人数量
    if len(alive_werewolves) >= len(alive_villagers):
        return 'werewolves'

    # 村民胜利：所有狼人被消灭
    if len(alive_werewolves) == 0:
        return 'villagers'

    return None

def game_loop():
    """完整游戏循环"""
    global is_running

    # 第一阶段：警长竞选
    if is_running:
        sheriff_election()

    round_num = 1

    while is_running:
        # 检查胜利条件
        winner = check_win_condition()
        if winner:
            dialogue_queue.put({
                "type": "status",
                "message": f"🎉 游戏结束 - {winner}胜利！"
            })

            if winner == 'werewolves':
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "游戏结束",
                    "content": "🐺 狼人阵营获胜！狼人数量已经达到或超过好人数量。"
                })
            else:
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "游戏结束",
                    "content": "👨‍🌾 村民阵营获胜！所有狼人已被消灭。"
                })

            is_running = False
            break

        # 夜晚阶段
        dialogue_queue.put({
            "type": "status",
            "message": f"🌙 第{round_num}夜"
        })

        # 1. 狼人讨论和击杀
        kill_target = night_werewolf_discussion()

        # 2. 预言家验人
        night_seer_action()

        # 3. 女巫行动
        night_witch_action(kill_target)

        # 4. 守卫守护
        night_guard_action()

        time.sleep(3)

        # 白天阶段
        day_discussion(round_num)

        # 再次检查胜利条件（白天投票后）
        winner = check_win_condition()
        if winner:
            dialogue_queue.put({
                "type": "status",
                "message": f"🎉 游戏结束 - {'狼人阵营' if winner == 'werewolves' else '村民阵营'}胜利！"
            })

            if winner == 'werewolves':
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "游戏结束",
                    "content": "🐺 狼人阵营获胜！狼人数量已经达到或超过好人数量。"
                })
            else:
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "游戏结束",
                    "content": "👨‍🌾 村民阵营获胜！所有狼人已被消灭。"
                })

            is_running = False
            break

        round_num += 1
        time.sleep(2)

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, players=PLAYERS)

@app.route('/api/start', methods=['POST'])
def start():
    global is_running, seer_claims, sheriff_player_id, game_state

    if not is_running:
        is_running = True
        seer_claims = []
        sheriff_player_id = None
        game_state = {
            "phase": "day",
            "round": 0,
            "dead_players": [],
            "night_actions": {}
        }

        # 重置玩家状态
        for player in PLAYERS:
            player['alive'] = True
            player['is_sheriff'] = False

        while not dialogue_queue.empty():
            dialogue_queue.get()

        thread = threading.Thread(target=game_loop, daemon=True)
        thread.start()

        return {"status": "started"}

    return {"status": "already_running"}

@app.route('/api/stop', methods=['POST'])
def stop():
    global is_running
    is_running = False
    return {"status": "stopped"}

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
    print("="*70)
    print("WEREWOLF GAME - DAY/NIGHT CYCLE")
    print("="*70)
    print("\n[INFO] Starting server on http://localhost:5003")
    print("[INFO] Features:")
    print("  - Sheriff Election (警长竞选)")
    print("  - Night Phase: Werewolf discussion & actions (夜晚-狼人讨论)")
    print("  - Night Phase: Special role actions (夜晚-神职行动)")
    print("  - Day Phase: Discussion & voting (白天讨论)")
    print("="*70)

    app.run(host='127.0.0.1', port=5003, debug=False)
