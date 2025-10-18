"""
简单的12玩家圆圈LLM对话系统
12 Players in a Circle - Simple LLM Dialogue System
"""

from flask import Flask, render_template_string
import requests
import json
import threading
import time
from queue import Queue

app = Flask(__name__)

# 全局变量
dialogue_queue = Queue()
is_running = False
current_player = 0
seer_claims = []  # Track who claimed to be Seer/Prophet (预言家)
sheriff_player_id = None  # Track who is the sheriff

# 12个玩家配置
# 4狼人 (包括1个狼王) + 4平民 + 4神职
PLAYERS = [
    {"id": 0, "role": "狼人", "emoji": "🐺", "color": "#f44336"},
    {"id": 1, "role": "狼人", "emoji": "🐺", "color": "#f44336"},
    {"id": 2, "role": "狼人", "emoji": "🐺", "color": "#f44336"},
    {"id": 3, "role": "狼王", "emoji": "👑", "color": "#d32f2f"},  # Wolf King - 狼王
    {"id": 4, "role": "村民", "emoji": "👨‍🌾", "color": "#4CAF50"},
    {"id": 5, "role": "村民", "emoji": "👨‍🌾", "color": "#4CAF50"},
    {"id": 6, "role": "村民", "emoji": "👨‍🌾", "color": "#4CAF50"},
    {"id": 7, "role": "村民", "emoji": "👨‍🌾", "color": "#4CAF50"},
    {"id": 8, "role": "预言家", "emoji": "👁️", "color": "#2196F3"},  # Seer
    {"id": 9, "role": "女巫", "emoji": "🧪", "color": "#9C27B0"},  # Witch
    {"id": 10, "role": "猎人", "emoji": "🏹", "color": "#FF9800"},  # Hunter
    {"id": 11, "role": "守卫", "emoji": "🛡️", "color": "#00BCD4"},  # Guard
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
    <title>12 Players Circle - LLM Dialogue</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            margin: 0;
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

        /* 圆圈区域 */
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

        .player-circle:hover {
            transform: scale(1.15);
            z-index: 10;
        }

        .player-circle.speaking {
            animation: pulse 1s infinite;
            border-width: 6px;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.8);
        }

        .player-circle.sheriff {
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
            border-width: 5px;
            box-shadow: 0 0 15px rgba(255, 215, 0, 0.6);
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

        /* 对话区域 */
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
            display: flex;
            align-items: center;
            gap: 8px;
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
        <h1>🎮 12玩家圆圈对话系统</h1>

        <div class="status-info" id="status">
            状态：等待开始
        </div>

        <div class="controls">
            <button onclick="startDialogue()" id="btn-start">▶️ 开始对话</button>
            <button onclick="stopDialogue()" id="btn-stop" disabled>⏹️ 停止</button>
            <button onclick="clearDialogue()">🗑️ 清空</button>
        </div>

        <div class="main-area">
            <!-- 圆圈区域 -->
            <div class="circle-area">
                <div class="circle-container" id="circle-container">
                    <div class="center-circle">
                        🐺<br>狼人杀
                    </div>
                </div>
            </div>

            <!-- 对话区域 -->
            <div class="dialogue-area">
                <div class="dialogue-header">💬 实时对话</div>
                <div class="dialogue-output" id="dialogue-output">
                    <div style="color: #999; text-align: center; padding: 20px;">
                        等待玩家发言...
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const players = {{ players | tojson }};
        let eventSource = null;

        // 创建圆圈中的玩家
        function createCircle() {
            const container = document.getElementById('circle-container');
            const radius = 250; // 半径
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

        // 高亮正在说话的玩家
        function highlightPlayer(playerId) {
            // 移除所有高亮
            document.querySelectorAll('.player-circle').forEach(el => {
                el.classList.remove('speaking');
            });

            // 添加当前玩家高亮
            const playerEl = document.getElementById('player-' + playerId);
            if (playerEl) {
                playerEl.classList.add('speaking');
            }
        }

        // 添加对话
        function addDialogue(data) {
            const output = document.getElementById('dialogue-output');

            // 清除"等待"消息
            if (output.innerHTML.includes('等待玩家发言')) {
                output.innerHTML = '';
            }

            const item = document.createElement('div');
            item.className = 'dialogue-item';

            // 处理系统消息 (player_id === -1)
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
            playerDiv.innerHTML = player.emoji + ' Player ' + player.id + ' (' + player.role + ')';

            const contentDiv = document.createElement('div');
            contentDiv.className = 'dialogue-content';

            const metaDiv = document.createElement('div');
            metaDiv.className = 'dialogue-meta';
            const roundText = data.round === 0 ? '警长竞选' : '轮次 ' + data.round;
            metaDiv.textContent = roundText + ' | ' + new Date().toLocaleTimeString();

            item.appendChild(playerDiv);
            item.appendChild(contentDiv);
            item.appendChild(metaDiv);

            output.insertBefore(item, output.firstChild);

            // 打字机效果
            const text = data.content;
            let index = 0;

            function typeChar() {
                if (index < text.length) {
                    contentDiv.textContent += text[index];
                    index++;
                    setTimeout(typeChar, 30);
                } else {
                    // 打字完成，滚动到顶部
                    output.scrollTop = 0;
                }
            }

            typeChar();
        }

        // 更新警长状态
        function updateSheriff(playerId) {
            // 移除所有警长标记
            document.querySelectorAll('.player-circle').forEach(el => {
                el.classList.remove('sheriff');
            });

            // 添加新警长标记
            const playerEl = document.getElementById('player-' + playerId);
            if (playerEl) {
                playerEl.classList.add('sheriff');
            }
        }

        // 开始对话
        function startDialogue() {
            document.getElementById('btn-start').disabled = true;
            document.getElementById('btn-stop').disabled = false;

            fetch('/api/start', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    console.log('Started:', data);
                    startEventStream();
                });
        }

        // 停止对话
        function stopDialogue() {
            document.getElementById('btn-start').disabled = false;
            document.getElementById('btn-stop').disabled = true;

            fetch('/api/stop', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    console.log('Stopped:', data);
                    if (eventSource) {
                        eventSource.close();
                        eventSource = null;
                    }
                });
        }

        // 清空对话
        function clearDialogue() {
            document.getElementById('dialogue-output').innerHTML =
                '<div style="color: #999; text-align: center; padding: 20px;">等待玩家发言...</div>';
        }

        // 事件流
        function startEventStream() {
            if (eventSource) eventSource.close();

            eventSource = new EventSource('/api/stream');

            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);
                console.log('Event:', data);

                if (data.type === 'dialogue') {
                    // 检查是否是警长选举结果
                    if (data.player_id === -1 && data.content.includes('当选警长')) {
                        // 从内容中提取警长ID
                        const match = data.content.match(/Player (\d+)/);
                        if (match) {
                            const sheriffId = parseInt(match[1]);
                            updateSheriff(sheriffId);
                        }
                    }

                    if (data.player_id >= 0) {
                        highlightPlayer(data.player_id);
                    }
                    addDialogue(data);
                } else if (data.type === 'status') {
                    document.getElementById('status').textContent = '状态：' + data.message;
                }
            };

            eventSource.onerror = function() {
                console.error('EventSource error');
                eventSource.close();
            };
        }

        // 页面加载时创建圆圈
        window.addEventListener('load', () => {
            createCircle();
            console.log('Circle created with', players.length, 'players');
        });
    </script>
</body>
</html>
"""

def call_llm(prompt, player_id):
    """调用LLM API"""
    try:
        print(f"[LLM] Calling for Player {player_id}...")

        url = f"{LLM_CONFIG['api_base']}/v1/chat/completions"

        payload = {
            "model": LLM_CONFIG["model"],
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": LLM_CONFIG["temperature"],
            "max_tokens": LLM_CONFIG["max_tokens"]
        }

        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()

        print(f"[LLM] Player {player_id} responded: {content[:50]}...")
        return content

    except Exception as e:
        print(f"[LLM] Error for Player {player_id}: {e}")
        return f"[Player {player_id} 暂时无法发言]"

def sheriff_election():
    """警长竞选环节 - Sheriff Election Phase"""
    import random

    print("\n" + "="*70)
    print("[SHERIFF ELECTION] Starting Sheriff Election Phase")
    print("="*70)

    dialogue_queue.put({
        "type": "status",
        "message": "🎖️ 警长竞选开始！Sheriff Election Starting..."
    })

    # 随机3-5个玩家上警（run for sheriff）
    num_candidates = random.randint(3, 5)
    candidates = random.sample(range(len(PLAYERS)), num_candidates)
    candidates.sort()

    print(f"[SHERIFF] Candidates: {candidates}")

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,  # System message
        "round": 0,
        "content": f"🎖️ 竞选警长的玩家: {', '.join(['Player ' + str(c) for c in candidates])}"
    })

    # 候选人依次竞选发言
    for candidate_id in candidates:
        if not is_running:
            break

        player = PLAYERS[candidate_id]

        dialogue_queue.put({
            "type": "status",
            "message": f"🎖️ Player {player['id']} ({player['role']}) 竞选发言中..."
        })

        # Sheriff election speech rules - ALL candidates MUST claim Seer and report inspection
        import random

        # 随机选择一个其他玩家作为验人目标
        other_players = [p for p in range(len(PLAYERS)) if p != player['id']]
        checked_player = random.choice(other_players)
        checked_role = PLAYERS[checked_player]['role']
        is_werewolf = checked_role in ['狼人', '狼王']

        role_instruction = ""
        if player['role'] == '预言家':
            # 真预言家：报告真实验人结果
            role_instruction = f"""
**核心规则：上警必须跳预言家并报验人！**

你是真预言家，昨晚验人结果：
- 验了 Player {checked_player}
- 结果：Player {checked_player} 是 {"狼人" if is_werewolf else "好人"}

**你必须在竞选发言中：**
1. 明确说"我是预言家"
2. 报告验人结果："昨晚我验了 Player {checked_player}，他是{'狼人' if is_werewolf else '好人'}"
3. 简短说明为什么适合当警长
"""
        elif player['role'] in ['狼人', '狼王']:
            # 狼人悍跳：可以编造假的验人结果
            fake_result = "好人" if random.random() > 0.5 else "狼人"
            role_instruction = f"""
**核心规则：上警必须跳预言家并报验人！**

你是狼人，需要悍跳预言家混淆好人。建议编造验人结果：
- 可以说验了 Player {checked_player}
- 可以编造结果：他是{fake_result}（可以随意编造来误导）

**你必须在竞选发言中：**
1. 明确说"我是预言家"
2. 编造验人结果："昨晚我验了 Player X，他是狼人/好人"
3. 表现得像真预言家一样有说服力
"""
        else:
            # 其他角色：也必须悍跳预言家并编造验人
            fake_result = "好人" if random.random() > 0.7 else "狼人"
            role_instruction = f"""
**核心规则：上警必须跳预言家并报验人！**

你不是预言家，但上警规则要求你必须跳预言家。编造一个验人结果：
- 可以说验了 Player {checked_player}
- 编造结果：他是{fake_result}

**你必须在竞选发言中：**
1. 明确说"我是预言家"
2. 编造验人结果："昨晚我验了 Player X，他是好人/狼人"
3. 尽量表现得有说服力
"""

        prompt = f"""你是狼人杀游戏中的 Player {player['id']}，角色是{player['role']}。
现在是警长竞选环节（Sheriff Election Phase）。

{role_instruction}

**重要：所有上警的人都必须跳预言家并报验人，这是规则！**

请按照上面的指导发表竞选宣言（2-3句话）。用中文回答。"""

        response = call_llm(prompt, player['id'])

        # Track if player claimed to be Seer
        if "我是预言家" in response or "预言家" in response.lower():
            seer_claims.append(player['id'])
            print(f"[SEER CLAIM] Player {player['id']} claimed to be Seer!")

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": player['id'],
            "round": 0,
            "content": f"【竞选发言】{response}"
        })

        time.sleep(1.5)

    # 投票选举警长
    time.sleep(2)
    dialogue_queue.put({
        "type": "status",
        "message": "🗳️ 投票选举警长中..."
    })

    # 简单随机选出警长（实际游戏中应该是所有玩家投票）
    global sheriff_player_id
    sheriff_id = random.choice(candidates)
    sheriff_player_id = sheriff_id
    PLAYERS[sheriff_id]['is_sheriff'] = True

    print(f"[SHERIFF] Player {sheriff_id} elected as Sheriff!")

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "round": 0,
        "content": f"🎖️ 警长选举结果：Player {sheriff_id} ({PLAYERS[sheriff_id]['role']}) 当选警长！"
    })

    time.sleep(2)
    print("[SHERIFF ELECTION] Sheriff Election Phase Completed")
    print(f"[SEER CLAIMS] Players who claimed Seer: {seer_claims}")
    print("="*70 + "\n")

def dialogue_loop():
    """对话循环：警长竞选 + 多轮随机发言"""
    global is_running, current_player
    import random

    # 第一阶段：警长竞选
    if is_running:
        sheriff_election()

    # 标记所有玩家初始没有警长身份
    for player in PLAYERS:
        if 'is_sheriff' not in player:
            player['is_sheriff'] = False

    round_num = 1

    while is_running:
        print(f"\n" + "="*70)
        print(f"[ROUND {round_num}] Starting Discussion Round")
        print("="*70)

        # 每轮随机打乱玩家顺序
        player_order = list(range(len(PLAYERS)))
        random.shuffle(player_order)

        print(f"[ROUND {round_num}] Player order: {player_order}")

        # 按照随机顺序让玩家发言
        for player_index in player_order:
            if not is_running:
                break

            player = PLAYERS[player_index]
            sheriff_badge = " 🎖️(警长)" if player.get('is_sheriff', False) else ""

            # 发送状态更新
            dialogue_queue.put({
                "type": "status",
                "message": f"第 {round_num} 轮 - Player {player['id']}{sheriff_badge} ({player['role']}) 正在思考..."
            })

            # 构造提示 - 根据角色和是否跳预言家给出不同指导
            sheriff_info = "你是警长，拥有更多权威和责任。" if player.get('is_sheriff', False) else ""
            is_seer_claimer = player['id'] in seer_claims

            role_instruction = ""
            if is_seer_claimer:
                # 跳了预言家的人必须报验人
                import random
                # 随机选择一个其他玩家作为验人目标
                other_players = [p for p in range(len(PLAYERS)) if p != player['id']]
                checked_player = random.choice(other_players)
                checked_role = PLAYERS[checked_player]['role']
                is_werewolf = checked_role in ['狼人', '狼王']

                role_instruction = f"""
**核心规则：你在竞选时跳了预言家，所以现在必须报验人！**

模拟验人结果（基于你的真实角色）：
- 你上一晚验了 Player {checked_player}
- 结果：Player {checked_player} 是 {"狼人" if is_werewolf else "好人"}

**你必须在发言中报验人：**
- 如果你是真预言家：报告真实验人结果
- 如果你是狼人悍跳：可以编造验人结果来误导好人

发言格式示例："昨晚我验了 Player X，他是狼人/好人。[简短分析]"
"""
            elif player['role'] in ['女巫', '猎人', '守卫']:
                role_instruction = """
**核心规则：你是神职，绝对不能暴露身份！**
- 不要说自己是女巫/猎人/守卫
- 以普通村民的身份发言
- 分析场上局势，质疑可疑的人
"""
            elif player['role'] in ['狼人', '狼王']:
                role_instruction = """
**核心规则：你是狼人，不要暴露身份！**
- 不要说自己是狼人
- 可以装成村民分析局势
- 可以质疑跳预言家的人
- 制造混乱，误导好人
"""
            else:
                role_instruction = """
**核心规则：你是村民，诚实发言！**
- 分析场上局势
- 质疑可疑的人
- 帮助好人阵营找出狼人
"""

            prompt = f"""你是狼人杀游戏中的 Player {player['id']}，角色是{player['role']}。{sheriff_info}
这是第 {round_num} 轮发言。

{role_instruction}

请简短发言（1-2句话），根据上面的规则表达你的观点。用中文回答。"""

            # 调用LLM
            response = call_llm(prompt, player['id'])

            # 发送对话
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": player['id'],
                "round": round_num,
                "content": response
            })

            time.sleep(1)  # 玩家之间停顿

        # 一轮结束，增加轮次
        round_num += 1
        time.sleep(2)  # 轮次之间稍微停顿

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, players=PLAYERS)

@app.route('/api/start', methods=['POST'])
def start():
    global is_running, current_player, seer_claims, sheriff_player_id

    if not is_running:
        is_running = True
        current_player = 0
        seer_claims = []  # Reset seer claims
        sheriff_player_id = None  # Reset sheriff

        # 清空队列
        while not dialogue_queue.empty():
            dialogue_queue.get()

        # 启动对话线程
        thread = threading.Thread(target=dialogue_loop, daemon=True)
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
                # 从队列获取数据
                data = dialogue_queue.get(timeout=1)
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            except:
                # 发送心跳
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

    return app.response_class(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    print("="*70)
    print("12 PLAYERS CIRCLE - LLM DIALOGUE SYSTEM")
    print("="*70)
    print("\n[INFO] Starting server...")
    print("[INFO] Open: http://localhost:5002")
    print("\n[CONFIG] LLM API:", LLM_CONFIG['api_base'])
    print("[CONFIG] Model:", LLM_CONFIG['model'])
    print("="*70)

    app.run(host='127.0.0.1', port=5002, debug=False)
