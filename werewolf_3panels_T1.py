"""
狼人杀 - 4对话框版本
4 Dialogue Panels: Werewolf Night / God Roles Night / Day Discussion & Voting / Real-time Statistics
游戏流程：第1夜开始 → 狼人讨论 → 神职行动 → 警长竞选 → 白天讨论投票
"""
import sys, io
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="ignore")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="ignore")


from flask import Flask, render_template_string
import requests
import json
import threading
import time
from queue import Queue
import random
import os

app = Flask(__name__)

# 配置文件路径
CONFIG_FILE = "llm_config.json"

# ========================================================================
# 游戏配置
# ========================================================================
# 玩家数 = 12
# 默认阵容 = { 狼人×4(可选:含狼王1), 预言家×1, 女巫×1, 猎人×1, 守卫×1, 村民×4 }

# 游戏开关
HAS_GUARD = True              # 是否有守卫
HAS_WOLF_KING = True          # 是否有狼王（带人）
HUNTER_NIGHT_SHOOT = False    # 猎人夜间被杀能否开枪（常规为false）
WITCH_DOUBLE_USE = False      # 女巫同夜能否既救又毒（常规为false）
NIGHT_BADGE_BREAKS = True     # 警长夜死是否警徽破碎（常见为true）
ALLOW_WOLF_SELF_BOMB = True   # 是否允许狼人自爆（常见为true）
ELECTION_BEFORE_N1 = False     # 是否开局白天先上警（常见为true）

# 规则要点：
# - 警长票权 = 1.5；平票由警长决定出/不出或进入二/三人PK（依房规）
# - 夜死无遗言；白天处决有遗言（部分角色例外见下）
# - 猎人：白天处决触发开枪；夜死/被毒通常不开枪（取决于HUNTER_NIGHT_SHOOT）
# - 女巫：解药/毒药各1次；若WITCH_DOUBLE_USE=false，同一夜不能两瓶都用
# - 守卫：不能连续两晚守同一人；被守到的人若被狼人击杀则存活
# - 结算顺序（常用）：狼人击杀 → 守卫守护 → 女巫得知「将死者」→ 女巫是否解救 → 女巫是否下毒 → 黎明公布死讯
# - 胜负：当「存活狼人数量 = 0」好人胜；当「存活狼人数量 ≥ 存活好人数量」狼人胜
# ========================================================================

# 全局变量
dialogue_queue = Queue()
is_running = False
waiting_for_next_day = False  # 是否在等待用户点击下一天
auto_mode = False  # 是否自动模式（自动播放游戏）
uls_mode = False  # 是否使用ULS短头部模式
seer_claims = []
sheriff_player_id = None
sheriff_candidates = []  # 第一夜狼人讨论决定谁上警
guard_last_target = None  # 守卫上次守护的目标
witch_save_available = True  # 女巫解药是否可用
witch_poison_available = True  # 女巫毒药是否可用
game_state = {
    "phase": "night",  # 游戏从夜晚开始
    "round": 0,
    "dead_players": [],
    "night_actions": {}
}

# 每日统计记录
daily_statistics = []  # 存储每一天的统计信息

# 公共记忆池 - 存储白天的所有发言
public_memory_pool = []  # 格式: [{"round": 1, "player_id": 0, "content": "...", "role_visible": False}, ...]

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

# Prompt后缀 - 要求模型使用OUTPUT和END标记
OUTPUT_FORMAT_INSTRUCTION = """

【格式要求 - 必须遵守】
你可以先思考和推理，但最终必须按照以下格式输出：

OUTPUT: [你的最终答案/决策]
END

规则说明：
1. 你可以在OUTPUT前自由思考（这部分不会被公开）
2. OUTPUT: 后面写你的最终发言（这部分会被其他玩家看到）
3. 必须以 END 标记结束
4. 如果没有END标记，你的发言将被视为无效，需要重新生成

示例：
思考：根据昨晚的死亡情况分析...Player 5的发言逻辑有问题...
OUTPUT: 我认为 Player 5 是狼人，建议投他
END"""

# LLM配置 - 支持两组API配置
def load_llm_config():
    """从文件加载LLM配置"""
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

    # 默认配置
    return {
        "test_api_base": "http://localhost:8080",
        "test_model": "/home/apulis-dev/userdata/Llama-3.3-70B-Instruct",
        "npc_api_base": "http://localhost:8080",
        "npc_model": "/home/apulis-dev/userdata/Llama-3.3-70B-Instruct",
        "temperature": 0.7,
        "max_tokens": 200
    }

def save_llm_config(config):
    """保存LLM配置到文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[CONFIG] Saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"[CONFIG] Error saving {CONFIG_FILE}: {e}")
        return False

# 加载配置
LLM_CONFIG = load_llm_config()

# Token使用限制和统计
MAX_TOKENS_PER_PLAYER = 5000  # 每个玩家最大token数
total_tokens_used = 0  # 总token使用量
player_tokens_used = {}  # 每个玩家的token使用量 {player_id: tokens}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>狼人杀 - 4对话框版本</title>
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
            content: '🎖️';
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
        <h1>🎮 狼人杀 - 4对话框版本</h1>

        <div class="status-info" id="status">
            状态：等待开始
        </div>

        <div class="status-info" id="token-stats" style="background: rgba(255, 152, 0, 0.2); font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 15px;">
            <span>🔢 Token使用: 总计 <span id="total-tokens">0</span></span>
            <span>|</span>
            <span>限制/玩家:
                <input type="number" id="token-limit-input" value="5000" min="100" max="100000"
                       style="width: 80px; padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px;">
            </span>
            <button onclick="updateTokenLimit()" style="padding: 4px 12px; font-size: 13px; cursor: pointer; border-radius: 4px; border: 1px solid #FF9800; background: white; color: #FF9800;">
                ✓ 更新限制
            </button>
        </div>

        <div class="controls">
            <button onclick="startGame()" id="btn-start">▶️ 开始游戏</button>
            <button onclick="stopGame()" id="btn-stop" disabled>⏹️ 停止</button>
            <button onclick="toggleAutoMode()" id="btn-auto">🔄 切换为自动模式</button>
            <button onclick="toggleULSMode()" id="btn-uls">📝 切换为ULS模式</button>
            <button onclick="showConfigModal()" id="btn-config">⚙️ 配置API</button>
            <button onclick="switchVersion('T0')" id="btn-version-t0" style="background: #FF9800; color: white;">📌 T0版本</button>
            <button onclick="switchVersion('T1')" id="btn-version-t1" style="background: #4CAF50; color: white;">🧠 T1版本(当前)</button>
            <button onclick="nextDay()" id="btn-next" disabled>⏭️ 下一天</button>
            <button onclick="toggleLanguage()" id="btn-lang">🌐 English</button>
            <button onclick="clearAll()" id="btn-clear">🗑️ 清空</button>
        </div>

        <!-- API配置模态窗口 -->
        <div id="config-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 9999; justify-content: center; align-items: center;">
            <div style="background: white; padding: 30px; border-radius: 12px; max-width: 700px; width: 90%;">
                <h2 style="margin-top: 0; color: #333;">⚙️ API配置</h2>

                <!-- 测试模型配置 -->
                <div style="margin-bottom: 25px; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #28a745;">
                    <h3 style="color: #28a745; font-size: 16px; margin-top: 0;">🧪 测试模型配置 (Test Player)</h3>
                    <label style="display: block; margin-bottom: 8px; color: #666;">API Base URL:</label>
                    <input type="text" id="test-api-base" value="http://localhost:8080"
                           style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">

                    <label style="display: block; margin-top: 12px; margin-bottom: 8px; color: #666;">Model Path:</label>
                    <input type="text" id="test-model" value="/home/apulis-dev/userdata/Llama-3.3-70B-Instruct"
                           style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">
                </div>

                <!-- NPC模型配置 -->
                <div style="margin-bottom: 20px; padding: 20px; background: #f8f9fa; border-radius: 8px; border-left: 4px solid #667eea;">
                    <h3 style="color: #667eea; font-size: 16px; margin-top: 0;">🤖 NPC模型配置 (11 NPC Players)</h3>
                    <label style="display: block; margin-bottom: 8px; color: #666;">API Base URL:</label>
                    <input type="text" id="npc-api-base" value="http://localhost:8080"
                           style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">

                    <label style="display: block; margin-top: 12px; margin-bottom: 8px; color: #666;">Model Path:</label>
                    <input type="text" id="npc-model" value="/home/apulis-dev/userdata/Llama-3.3-70B-Instruct"
                           style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; box-sizing: border-box;">
                </div>

                <div style="margin-top: 30px; display: flex; justify-content: flex-end; gap: 10px;">
                    <button onclick="closeConfigModal()" style="padding: 10px 20px; border: 1px solid #ddd; background: white; border-radius: 6px; cursor: pointer;">取消</button>
                    <button onclick="saveConfig()" style="padding: 10px 20px; border: none; background: #667eea; color: white; border-radius: 6px; cursor: pointer;">保存配置</button>
                </div>
            </div>
        </div>

        <div class="circle-area">
            <div class="circle-container" id="circle-container">
                <div class="center-circle">
                    🐺<br>狼人杀
                </div>
            </div>
        </div>

        <div class="main-area">
            <div class="dialogue-panel">
                <div class="panel-header werewolf">🐺 夜晚 - 狼人对话</div>
                <div class="panel-output" id="werewolf-output">
                    <div style="color: #999; text-align: center; padding: 20px;">
                        等待狼人行动...
                    </div>
                </div>
            </div>

            <div class="dialogue-panel">
                <div class="panel-header god">✨ 夜晚 - 神职行动</div>
                <div class="panel-output" id="god-output">
                    <div style="color: #999; text-align: center; padding: 20px;">
                        等待神职行动...
                    </div>
                </div>
            </div>

            <div class="dialogue-panel">
                <div class="panel-header day">☀️ 白天 - 讨论投票</div>
                <div class="panel-output" id="day-output">
                    <div style="color: #999; text-align: center; padding: 20px;">
                        等待白天讨论...
                    </div>
                </div>
            </div>

            <div class="dialogue-panel">
                <div class="panel-header statistics">📊 实时统计</div>
                <div class="panel-output" id="statistics-output">
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
        let currentPhase = 'night';
        let autoMode = false;  // 默认手动模式
        let ulsMode = false;  // 默认非ULS模式
        let currentLang = 'zh';  // 默认中文

        // 翻译字典
        const translations = {
            zh: {
                title: '狼人杀 - 4对话框版本',
                status: '状态：',
                startGame: '▶️ 开始游戏',
                stopGame: '⏹️ 停止',
                autoModeManual: '🔄 切换为自动模式',
                autoModeAuto: '🔁 切换为手动模式',
                nextDay: '⏭️ 下一天',
                clearAll: '🗑️ 清空',
                langSwitch: '🌐 English',
                waitingStart: '等待开始',
                werewolfPanel: '🐺 夜晚 - 狼人对话',
                godPanel: '✨ 夜晚 - 神职行动',
                dayPanel: '☀️ 白天 - 讨论投票',
                statsPanel: '📊 实时统计',
                waitingWerewolf: '等待狼人行动...',
                waitingGod: '等待神职行动...',
                waitingDay: '等待白天讨论...',
                waitingGame: '等待游戏开始...'
            },
            en: {
                title: 'Werewolf - 4 Panel Version',
                status: 'Status: ',
                startGame: '▶️ Start Game',
                stopGame: '⏹️ Stop',
                autoModeManual: '🔄 Switch to Auto',
                autoModeAuto: '🔁 Switch to Manual',
                nextDay: '⏭️ Next Day',
                clearAll: '🗑️ Clear',
                langSwitch: '🌐 中文',
                waitingStart: 'Waiting to start',
                werewolfPanel: '🐺 Night - Werewolf Chat',
                godPanel: '✨ Night - God Roles',
                dayPanel: '☀️ Day - Discussion & Voting',
                statsPanel: '📊 Real-time Stats',
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
            // 根据对话类型路由到不同的面板
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

            if (output.innerHTML.includes('等待')) {
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
                contentDiv.style.whiteSpace = 'pre-wrap';  // 保留换行和空格
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

            // 只在狼人/神职面板显示角色，白天面板不显示
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
                    setTimeout(typeChar, 20);
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

        function updateUI() {
            // 更新标题
            document.querySelector('h1').textContent = '🎮 ' + t('title');

            // 更新状态文本前缀（保留后面的动态内容）
            const statusEl = document.getElementById('status');
            const statusText = statusEl.textContent;
            if (statusText.includes('：') || statusText.includes(': ')) {
                const parts = statusText.split(/：|: /);
                if (parts.length > 1) {
                    statusEl.textContent = t('status') + parts[1];
                } else {
                    statusEl.textContent = t('status') + t('waitingStart');
                }
            }

            // 更新按钮
            document.getElementById('btn-start').textContent = t('startGame');
            document.getElementById('btn-stop').textContent = t('stopGame');
            document.getElementById('btn-auto').textContent = autoMode ? t('autoModeAuto') : t('autoModeManual');
            document.getElementById('btn-next').textContent = t('nextDay');
            document.getElementById('btn-lang').textContent = t('langSwitch');
            document.getElementById('btn-clear').textContent = t('clearAll');

            // 更新面板标题
            document.querySelectorAll('.panel-header')[0].textContent = t('werewolfPanel');
            document.querySelectorAll('.panel-header')[1].textContent = t('godPanel');
            document.querySelectorAll('.panel-header')[2].textContent = t('dayPanel');
            document.querySelectorAll('.panel-header')[3].textContent = t('statsPanel');

            // 更新占位文本
            const panels = [
                {id: 'werewolf-output', key: 'waitingWerewolf'},
                {id: 'god-output', key: 'waitingGod'},
                {id: 'day-output', key: 'waitingDay'},
                {id: 'statistics-output', key: 'waitingGame'}
            ];

            panels.forEach(panel => {
                const el = document.getElementById(panel.id);
                if (el.textContent.includes('等待') || el.textContent.includes('Waiting')) {
                    el.innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">' + t(panel.key) + '</div>';
                }
            });
        }

        function toggleLanguage() {
            currentLang = currentLang === 'zh' ? 'en' : 'zh';
            updateUI();
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

            // 通知后端模式改变
            fetch('/api/set_auto_mode', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({auto_mode: autoMode})
            })
            .then(response => response.json())
            .then(data => {
                console.log('Auto mode:', data);

                // 如果切换到自动模式且正在等待，自动继续
                if (autoMode && !document.getElementById('btn-next').disabled) {
                    nextDay();
                }
            });
        }

        function toggleULSMode() {
            ulsMode = !ulsMode;
            const btn = document.getElementById('btn-uls');

            if (ulsMode) {
                btn.textContent = '📝 ULS模式 (已启用)';
                btn.style.background = '#2196F3';
                btn.style.color = 'white';
            } else {
                btn.textContent = '📝 切换为ULS模式';
                btn.style.background = 'white';
                btn.style.color = 'black';
            }

            // 向服务器同步ULS模式状态
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
            // 从服务器加载当前配置
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
                alert('API配置已更新！\\n\\n测试模型: ' + testApiBase + '\\nNPC模型: ' + npcApiBase);
                closeConfigModal();
            })
            .catch(error => {
                console.error('Error updating config:', error);
                alert('配置更新失败，请重试');
            });
        }

        function updateTokenLimit() {
            const newLimit = parseInt(document.getElementById('token-limit-input').value);

            if (newLimit < 100 || newLimit > 100000) {
                alert('Token限制必须在100到100000之间');
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
                alert('Token限制已更新为: ' + newLimit + '/玩家');
            })
            .catch(error => {
                console.error('Error updating token limit:', error);
                alert('更新失败，请重试');
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
            if (confirm('确定要切换到' + version + '版本吗?\n\nT0版本: 基础版本\nT1版本: 增强版本(含公共记忆池和推理投票)\n\n切换后页面将自动刷新。')) {
                try {
                    const response = await fetch('/api/switch_version', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ version: version })
                    });
                    const data = await response.json();
                    alert(data.message + '\n\n页面将在2秒后自动刷新。');
                    setTimeout(() => location.reload(), 2000);
                } catch (error) {
                    alert('切换版本失败: ' + error.message);
                }
            }
        }

        function clearAll() {
            document.getElementById('werewolf-output').innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">等待狼人行动...</div>';
            document.getElementById('god-output').innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">等待神职行动...</div>';
            document.getElementById('day-output').innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">等待白天讨论...</div>';
            document.getElementById('statistics-output').innerHTML = '<div style="color: #999; text-align: center; padding: 20px;">等待游戏开始...</div>';
        }

        function startEventStream() {
            if (eventSource) eventSource.close();

            eventSource = new EventSource('/api/stream');

            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);

                if (data.type === 'phase') {
                    setPhase(data.phase);
                    if (data.phase === 'night') {
                        players.forEach((p, i) => {
                            if (!['狼人', '狼王'].includes(p.role)) {
                                hidePlayer(i);
                            }
                        });
                    } else {
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
                } else if (data.type === 'waiting_for_next') {
                    // 启用下一天按钮
                    document.getElementById('btn-next').disabled = false;

                    // 如果是自动模式，自动点击下一天
                    if (autoMode) {
                        setTimeout(() => {
                            nextDay();
                        }, 2000);  // 延迟2秒自动继续
                    }
                } else if (data.type === 'token_update') {
                    // 更新token统计
                    document.getElementById('total-tokens').textContent = data.total_tokens;

                    // 可选：显示每个玩家的token使用情况
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
        });

        window.addEventListener('resize', () => {
            document.getElementById('circle-container').innerHTML = '<div class="center-circle">🐺<br>狼人杀</div>';
            createCircle();
        });
    </script>
</body>
</html>
"""

def call_llm(prompt, player_id):
    """调用LLM API并跟踪token使用"""
    global total_tokens_used, player_tokens_used

    try:
        # 注释掉token限制检查 - 允许玩家自由发言
        # if player_id >= 0:  # player_id == -1 表示系统消息
        #     current_usage = player_tokens_used.get(player_id, 0)
        #     if current_usage >= MAX_TOKENS_PER_PLAYER:
        #         print(f"[LLM] Player {player_id} 已达到token限制 ({MAX_TOKENS_PER_PLAYER})")
        #         return f"[Player {player_id} 已达到发言限制]"

        # 根据玩家ID选择API配置: Player 1 = 测试模型, 其他玩家 = NPC模型
        if player_id == 1:
            api_base = LLM_CONFIG['test_api_base']
            model = LLM_CONFIG['test_model']
            print(f"[LLM] Player {player_id} 使用测试模型: {api_base}")
        else:
            api_base = LLM_CONFIG['npc_api_base']
            model = LLM_CONFIG['npc_model']
            print(f"[LLM] Player {player_id} 使用NPC模型: {api_base}")

        # 在prompt后添加OUTPUT格式指引
        full_prompt = prompt + OUTPUT_FORMAT_INSTRUCTION

        url = f"{api_base}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": full_prompt}],
            "temperature": LLM_CONFIG["temperature"]
            # 移除 max_tokens 限制，让模型自由输出
        }

        print(f"[LLM] Calling API for Player {player_id}...")
        print(f"[LLM]   URL: {url}")
        print(f"[LLM]   Model: {model}")
        print(f"[LLM]   Prompt (first 100 chars): {prompt[:100]}...")

        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        print(f"[LLM] Response received for Player {player_id}")
        print(f"[LLM]   Full response: {json.dumps(result, ensure_ascii=False, indent=2)}")

        # 提取内容：优先使用content（最终结论），如果为空则从reasoning_content提取
        message = result["choices"][0]["message"]
        raw_content = message.get("content", "").strip()
        reasoning_content = message.get("reasoning_content", "").strip()

        # 合并所有内容用于提取
        full_response = raw_content
        if not full_response and reasoning_content:
            full_response = reasoning_content

        print(f"[LLM] Full response from Player {player_id} (length: {len(full_response)}):")
        print(f"[LLM] {full_response[:500]}..." if len(full_response) > 500 else f"[LLM] {full_response}")

        # 严格验证 OUTPUT: 和 END 标记
        import re

        # 检查是否包含 OUTPUT: 和 END
        has_output = re.search(r'(?:OUTPUT|output)[：:]\s*(.+)', full_response, re.DOTALL | re.IGNORECASE)
        has_end = re.search(r'\bEND\b', full_response, re.IGNORECASE)

        if has_output and has_end:
            # 提取OUTPUT和END之间的内容
            output_end_match = re.search(r'(?:OUTPUT|output)[：:]\s*(.+?)\s*END', full_response, re.DOTALL | re.IGNORECASE)
            if output_end_match:
                content = output_end_match.group(1).strip()
                print(f"[LLM] [OK] Valid format detected for Player {player_id}")
                print(f"[LLM] Extracted content: '{content[:100]}...'" if len(content) > 100 else f"[LLM] Extracted content: '{content}'")
            else:
                print(f"[LLM] [ERROR] OUTPUT and END found but format incorrect for Player {player_id}")
                content = "[格式错误：无法提取OUTPUT和END之间的内容]"
        else:
            # 格式不正确，记录错误但不重试（为了保持游戏流畅）
            print(f"[LLM] [WARN] Invalid format for Player {player_id}:")
            print(f"[LLM]   Has OUTPUT: {bool(has_output)}")
            print(f"[LLM]   Has END: {bool(has_end)}")

            # Fallback：如果有OUTPUT但没有END，提取OUTPUT后的所有内容
            if has_output:
                content = has_output.group(1).strip()
                # 如果内容太长，只取前200字符
                if len(content) > 200:
                    content = content[:200] + "..."
                print(f"[LLM] Using OUTPUT content (no END found): '{content[:100]}...'" if len(content) > 100 else f"[LLM] Using OUTPUT content: '{content}'")
            else:
                # 完全没有格式，提取最后200字符
                if len(full_response) > 200:
                    content = "..." + full_response[-200:]
                else:
                    content = full_response
                print(f"[LLM] No OUTPUT found, using fallback extraction")

        # 获取token使用量
        usage = result.get("usage", {})
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        # 更新统计
        total_tokens_used += total_tokens
        if player_id >= 0:
            if player_id not in player_tokens_used:
                player_tokens_used[player_id] = 0
            player_tokens_used[player_id] += total_tokens

        print(f"[LLM] Player {player_id}: {content[:50]}... (tokens: {total_tokens}, total: {total_tokens_used})")

        # 发送token统计到前端
        dialogue_queue.put({
            "type": "token_update",
            "total_tokens": total_tokens_used,
            "player_tokens": dict(player_tokens_used)
        })

        return content

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[LLM] Error for Player {player_id}:")
        print(f"  Error Type: {type(e).__name__}")
        print(f"  Error Message: {e}")
        print(f"  API URL: {api_base}/v1/chat/completions")
        print(f"  Model: {model}")
        print(f"  Full Traceback:\n{error_details}")
        return f"[Player {player_id} 暂时无法发言]"

def first_night_werewolf_discussion():
    """第一夜 - 狼人讨论：刀谁、策略、谁上警"""
    global sheriff_candidates
    print("\n[FIRST NIGHT] Werewolf discussion...")

    dialogue_queue.put({
        "type": "phase",
        "phase": "night"
    })

    dialogue_queue.put({
        "type": "status",
        "message": "🌙 第1夜 - 狼人讨论"
    })

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "第1夜-狼人",
        "content": "🌙 天黑请闭眼... 狼人请睁眼，认识彼此。",
        "panel": "werewolf"
    })

    werewolves = [p for p in PLAYERS if p['role'] in ['狼人', '狼王']]
    alive_non_wolves = [p for p in PLAYERS if p['role'] not in ['狼人', '狼王']]

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "第1夜-狼人",
        "content": f"🐺 狼人阵营：{', '.join([f'Player {w['id']}' for w in werewolves])}",
        "panel": "werewolf"
    })

    time.sleep(1)

    # 狼人讨论：刀谁、谁上警
    for wolf in werewolves:
        if not is_running:
            break

        if uls_mode:
            # ULS++ L0模式：狼人夜间行动
            seat = wolf['id'] + 1
            teammate_seats = ', '.join([f"seat {w['id']+1}" for w in werewolves if w['id'] != wolf['id']])
            target_seats = ', '.join([f"seat {p['id']+1}" for p in alive_non_wolves])

            prompt = f"""Werewolf ULS++ L0 NIGHT Phase - Night 1 Wolf Discussion
You are seat {seat}, role: {wolf['role']} (wolf team).
Teammates: {teammate_seats}

**CRITICAL: L0 Mode - ONE line header ONLY, NO free text:**

Format: N:<seat>[|ELC:JOIN|ELC:PASS]

**L0 Constraints:**
- N:<seat> = Kill target (seats 1-12)
- ELC:JOIN or ELC:PASS (election)
- Omit K (fixed at {LLM_CONFIG['max_tokens']})
- Available targets: {target_seats}

Example: N:8|ELC:JOIN

NO text. NO explanation. ONLY the header line."""
        else:
            # 正常模式
            prompt = f"""狼人杀游戏 - 第1夜，狼人内部讨论。
你是Player {wolf['id']}，角色{wolf['role']}（狼人阵营）。

队友：{', '.join([f"Player {w['id']}" for w in werewolves if w['id'] != wolf['id']])}

第一夜讨论重点：
1. 建议刀掉哪个玩家？（可选目标：{', '.join([f"Player {p['id']}" for p in alive_non_wolves])}）
2. 建议哪个狼人上警竞选？

请简短发言（2-3句）。用中文。"""

        response = call_llm(prompt, wolf['id'])

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": wolf['id'],
            "phase": "第1夜-狼人讨论",
            "content": response,
            "panel": "werewolf"
        })

        time.sleep(1.5)

    # 狼人决定刀人和谁上警
    kill_target = random.choice(alive_non_wolves)
    game_state['night_actions']['werewolf_kill'] = kill_target['id']

    # 随机选择1-2个狼人上警 + 其他随机玩家
    num_wolf_candidates = random.randint(1, 2)
    wolf_candidates = random.sample([w['id'] for w in werewolves], num_wolf_candidates)

    # 加上1-2个好人也上警
    good_guys = [p['id'] for p in PLAYERS if p['role'] not in ['狼人', '狼王']]
    num_good_candidates = random.randint(1, 2)
    good_candidates = random.sample(good_guys, num_good_candidates)

    sheriff_candidates = wolf_candidates + good_candidates
    random.shuffle(sheriff_candidates)

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "第1夜-狼人",
        "content": f"🐺 狼人决定：刀 Player {kill_target['id']}",
        "panel": "werewolf"
    })

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "第1夜-狼人",
        "content": f"📋 狼人决定上警名单：{', '.join([f'Player {c}' for c in wolf_candidates])}",
        "panel": "werewolf"
    })

    dialogue_queue.put({
        "type": "status",
        "message": "狼人请闭眼"
    })

    time.sleep(2)
    return kill_target['id']

def night_phase(day_num):
    """
    完整夜晚阶段
    顺序：狼人行动 → 守卫 → 预言家 → 女巫 → 结算死亡
    """
    global guard_last_target, witch_save_available, witch_poison_available, daily_statistics
    print(f"\n[NIGHT {day_num}] Starting...")

    # 初始化本夜统计
    night_stats = {
        "day": day_num,
        "night_actions": {},
        "night_deaths": [],
        "day_execution": None,
        "alive_werewolves": 0,
        "alive_villagers": 0,
        "game_ended": False,
        "winner": None
    }

    dialogue_queue.put({
        "type": "phase",
        "phase": "night"
    })

    dialogue_queue.put({
        "type": "status",
        "message": f"🌙 第{day_num}夜"
    })

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"第{day_num}夜",
        "content": "🌙 天黑请闭眼...",
        "panel": "werewolf"
    })

    time.sleep(1)

    # 1. 狼人行动
    wolves_target = None
    werewolves = [p for p in PLAYERS if p['role'] in ['狼人', '狼王'] and p['alive']]

    if not werewolves:
        return None  # 狼人全灭

    dialogue_queue.put({
        "type": "status",
        "message": "🐺 狼人请睁眼"
    })

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"第{day_num}夜-狼人",
        "content": "🐺 狼人请睁眼，认识队友。",
        "panel": "werewolf"
    })

    alive_non_wolves = [p for p in PLAYERS if p['alive'] and p['role'] not in ['狼人', '狼王']]

    if werewolves and alive_non_wolves:
        # 狼人讨论
        for wolf in werewolves:
            if not is_running:
                break

            # 获取所有存活的非狼人玩家编号（狼人只知道编号，不知道身份）
            alive_target_ids = [p['id'] for p in alive_non_wolves]
            wolf_team_ids = [w['id'] for w in werewolves if w['id'] != wolf['id']]

            prompt = f"""狼人杀游戏 - 第{day_num}夜，狼人内部讨论。
你是Player {wolf['id']}，{wolf['role']}（狼人阵营）。

队友：{', '.join([f"Player {wid}" for wid in wolf_team_ids])}

场上存活的其他玩家编号：{', '.join([f"Player {pid}" for pid in alive_target_ids])}

注意：你只知道玩家编号，不知道他们是什么身份（神职还是村民）。

请简短建议（1句）击杀哪个玩家编号。用中文。"""

            response = call_llm(prompt, wolf['id'])

            dialogue_queue.put({
                "type": "dialogue",
                "player_id": wolf['id'],
                "phase": f"第{day_num}夜-狼人",
                "content": response,
                "panel": "werewolf"
            })

            time.sleep(1)

        # 狼人决定击杀目标
        wolves_target = random.choice(alive_non_wolves)['id']
        night_stats["night_actions"]["wolf_target"] = wolves_target

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"第{day_num}夜-狼人",
            "content": f"🐺 狼人决定刀 Player {wolves_target}",
            "panel": "werewolf"
        })

    dialogue_queue.put({
        "type": "status",
        "message": "狼人请闭眼"
    })

    time.sleep(1.5)

    # 2. 守卫行动
    guard_target = None
    if HAS_GUARD:
        guard = next((p for p in PLAYERS if p['role'] == '守卫' and p['alive']), None)

        if guard:
            dialogue_queue.put({
                "type": "status",
                "message": "🛡️ 守卫请睁眼"
            })

            # 第一夜守卫空守（不守护任何人）
            if day_num == 1:
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": f"第{day_num}夜-守卫",
                    "content": "🛡️ 守卫请睁眼。第一夜空守，不守护任何人。",
                    "panel": "god"
                })

                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": guard['id'],
                    "phase": f"第{day_num}夜-守卫",
                    "content": "[空守] 守卫第一夜空守",
                    "panel": "god"
                })
            else:
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": f"第{day_num}夜-守卫",
                    "content": "🛡️ 守卫请睁眼，选择一个玩家守护（不能连续守护同一人）。",
                    "panel": "god"
                })

                # 守卫不能连续守同一人
                alive_others = [p for p in PLAYERS if p['alive'] and p['id'] != guard['id']]
                if guard_last_target is not None:
                    alive_others = [p for p in alive_others if p['id'] != guard_last_target]

                if alive_others:
                    target = random.choice(alive_others)
                    guard_target = target['id']
                    guard_last_target = guard_target
                    night_stats["night_actions"]["guard_target"] = guard_target

                    dialogue_queue.put({
                        "type": "dialogue",
                        "player_id": guard['id'],
                        "phase": f"第{day_num}夜-守卫",
                        "content": f"[守护] 守护 Player {guard_target}",
                        "panel": "god"
                    })

            dialogue_queue.put({
                "type": "status",
                "message": "守卫请闭眼"
            })

            time.sleep(1.5)

    # 3. 预言家行动
    seer = next((p for p in PLAYERS if p['role'] == '预言家' and p['alive']), None)

    if seer:
        dialogue_queue.put({
            "type": "status",
            "message": "👁️ 预言家请睁眼"
        })

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"第{day_num}夜-预言家",
            "content": "👁️ 预言家请睁眼，选择一个玩家查验。",
            "panel": "god"
        })

        alive_others = [p for p in PLAYERS if p['alive'] and p['id'] != seer['id']]
        if alive_others:
            target = random.choice(alive_others)
            is_wolf = target['role'] in ['狼人', '狼王']
            night_stats["night_actions"]["seer_check"] = {"target": target['id'], "result": "狼人" if is_wolf else "好人"}

            response = call_llm(f"你是预言家，验了Player {target['id']}，他是{'狼人' if is_wolf else '好人'}。简短思考（1句）。用中文。", seer['id'])

            dialogue_queue.put({
                "type": "dialogue",
                "player_id": seer['id'],
                "phase": f"第{day_num}夜-预言家",
                "content": f"[验人] Player {target['id']} 是{'狼人' if is_wolf else '好人'}。{response}",
                "panel": "god"
            })

        dialogue_queue.put({
            "type": "status",
            "message": "预言家请闭眼"
        })

        time.sleep(1.5)

    # 4. 女巫行动
    witch_save = False
    witch_poison_target = None
    witch = next((p for p in PLAYERS if p['role'] == '女巫' and p['alive']), None)

    if witch:
        dialogue_queue.put({
            "type": "status",
            "message": "🧪 女巫请睁眼"
        })

        # 告知女巫本夜将死者
        if wolves_target is not None:
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": f"第{day_num}夜-女巫",
                "content": f"🧪 女巫请睁眼。今晚 Player {wolves_target} 被狼人击杀。",
                "panel": "god"
            })
        else:
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": f"第{day_num}夜-女巫",
                "content": "🧪 女巫请睁眼。今晚平安夜，无人被击杀。",
                "panel": "god"
            })

        time.sleep(1)

        # 女巫决策
        used_medicine_this_night = False

        # 先问解药
        if witch_save_available and wolves_target is not None:
            save_prompt = f"你是女巫，Player {wolves_target}被狼人击杀。你有解药，是否使用解药救他？（是/否）。用中文回答。"
            response = call_llm(save_prompt, witch['id'])

            if "是" in response or "解药" in response or "救" in response:
                witch_save = True
                witch_save_available = False
                used_medicine_this_night = True
                night_stats["night_actions"]["witch_save"] = wolves_target

                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": witch['id'],
                    "phase": f"第{day_num}夜-女巫",
                    "content": f"[使用解药] 救了 Player {wolves_target}",
                    "panel": "god"
                })

        # 再问毒药（如果WITCH_DOUBLE_USE=False且已用解药，则不能用毒）
        can_use_poison = WITCH_DOUBLE_USE or not used_medicine_this_night

        if witch_poison_available and can_use_poison:
            alive_others = [p for p in PLAYERS if p['alive'] and p['id'] != witch['id']]
            if wolves_target is not None:
                alive_others = [p for p in alive_others if p['id'] != wolves_target]

            if alive_others:
                # 要求女巫给出毒药理由，必须明确认为对方极大概率是狼
                other_players_info = ', '.join([f"Player {p['id']}" for p in alive_others])
                poison_prompt = f"""你是女巫，是否使用毒药？
场上其他存活玩家：{other_players_info}

重要规则：毒药非常珍贵，只有当你极度确信某人是狼人时才能使用！

请回答：
1. 是否使用毒药？（是/否）
2. 如果使用，毒杀哪个玩家编号？
3. 理由是什么？为什么认为他极大概率是狼人？

用中文简短回答（1-2句）。"""

                response = call_llm(poison_prompt, witch['id'])

                # 检查回复中是否包含"是"、"毒"，以及"狼"或"极"等关键词
                # 要求女巫必须明确表达认为目标是狼人
                has_poison_intent = ("是" in response or "毒" in response)
                has_werewolf_reason = ("狼" in response or "极" in response or "一定" in response or "肯定" in response)

                if has_poison_intent and has_werewolf_reason:
                    # 尝试从回复中提取玩家编号
                    import re
                    player_match = re.search(r'Player\s*(\d+)', response)
                    if not player_match:
                        player_match = re.search(r'[号]?\s*(\d+)', response)

                    if player_match:
                        target_id = int(player_match.group(1))
                        # 验证目标是否在有效列表中
                        if any(p['id'] == target_id for p in alive_others):
                            witch_poison_target = target_id
                            witch_poison_available = False
                            night_stats["night_actions"]["witch_poison"] = witch_poison_target

                            dialogue_queue.put({
                                "type": "dialogue",
                                "player_id": witch['id'],
                                "phase": f"第{day_num}夜-女巫",
                                "content": f"[使用毒药] 毒杀 Player {witch_poison_target}。理由：{response[:50]}...",
                                "panel": "god"
                            })

        if not witch_save and witch_poison_target is None:
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": witch['id'],
                "phase": f"第{day_num}夜-女巫",
                "content": "[不使用药] 女巫选择本回合不使用药",
                "panel": "god"
            })

        dialogue_queue.put({
            "type": "status",
            "message": "女巫请闭眼"
        })

        time.sleep(1.5)

    # 5. 夜间结算死亡
    night_deaths = []

    # 先结算狼刀（考虑守卫和解药）
    if wolves_target is not None:
        if HAS_GUARD and guard_target == wolves_target:
            # 被守住
            pass
        elif witch_save and wolves_target:
            # 被解药救活
            pass
        else:
            night_deaths.append(wolves_target)

    # 再结算毒药
    if witch_poison_target is not None:
        night_deaths.append(witch_poison_target)

    # 记录夜死名单
    night_stats["night_deaths"] = night_deaths

    # 将本夜统计保存到全局(后续会在dawn_phase和day_discussion_and_voting中更新)
    daily_statistics.append(night_stats)

    # 夜晚阶段结束，更新一次实时统计
    update_realtime_statistics()

    # 返回夜死名单，由Dawn阶段处理
    return night_deaths

def dawn_phase(night_deaths, day_num):
    """
    黎明阶段：公布夜死并处理警徽、猎人开枪
    夜死无遗言
    注意：不公布死者身份（只公布号码）
    """
    global sheriff_player_id
    print(f"\n[DAWN {day_num}] Processing night deaths...")

    dialogue_queue.put({
        "type": "phase",
        "phase": "day"
    })

    dialogue_queue.put({
        "type": "status",
        "message": f"☀️ 第{day_num}天黎明"
    })

    # 先处理警长夜死（如果有）
    sheriff_died = False
    if night_deaths:
        for player_id in night_deaths:
            player = PLAYERS[player_id]
            if player.get('is_sheriff'):
                sheriff_died = True
                if NIGHT_BADGE_BREAKS:
                    # 警徽破碎
                    sheriff_player_id = None
                    player['is_sheriff'] = False

                    dialogue_queue.put({
                        "type": "dialogue",
                        "player_id": -1,
                        "phase": f"第{day_num}天黎明",
                        "content": "🎖️ 警长夜死，警徽破碎。",
                        "panel": "day"
                    })
                else:
                    # 少数房规：可以移交警徽
                    alive_players = [p for p in PLAYERS if p['alive'] and p['id'] != player_id]
                    if alive_players:
                        new_sheriff = random.choice(alive_players)
                        sheriff_player_id = new_sheriff['id']
                        player['is_sheriff'] = False
                        new_sheriff['is_sheriff'] = True

                        dialogue_queue.put({
                            "type": "dialogue",
                            "player_id": -1,
                            "phase": f"第{day_num}天黎明",
                            "content": f"🎖️ 警长移交警徽给 Player {new_sheriff['id']}",
                            "panel": "day"
                        })

    # 公布死讯（只公布号码，不公布身份）
    if not night_deaths:
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"第{day_num}天黎明",
            "content": "🎉 昨晚是平安夜，无人死亡。",
            "panel": "day"
        })
        time.sleep(2)

        # 第1天且未提前上警，则现在上警
        if day_num == 1 and not ELECTION_BEFORE_N1:
            sheriff_election()

        return

    # 公布死讯（只公布号码，不公布身份）
    death_list = ', '.join([f"Player {p}" for p in night_deaths])
    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"第{day_num}天黎明",
        "content": f"💀 昨晚死亡：{death_list}（夜死无遗言）",
        "panel": "day"
    })

    # 标记玩家死亡
    for player_id in night_deaths:
        PLAYERS[player_id]['alive'] = False

        dialogue_queue.put({
            "type": "death",
            "player_id": player_id
        })

    time.sleep(2)

    # 处理猎人夜死开枪（取决于HUNTER_NIGHT_SHOOT配置）
    hunter_shot_targets = []

    for player_id in night_deaths:
        player = PLAYERS[player_id]

        if player['role'] == '猎人':
            if HUNTER_NIGHT_SHOOT:
                # TODO: 需要判断是否被毒（被毒通常不能开枪）
                # 简化版：夜死可以开枪
                alive_players = [p for p in PLAYERS if p['alive']]
                if alive_players:
                    target = random.choice(alive_players)
                    hunter_shot_targets.append(target['id'])

                    dialogue_queue.put({
                        "type": "dialogue",
                        "player_id": player_id,
                        "phase": f"第{day_num}天黎明-猎人",
                        "content": f"🏹 猎人（Player {player_id}）夜死开枪带走 Player {target['id']}",
                        "panel": "day"
                    })

    # 处理猎人开枪连锁死亡
    if hunter_shot_targets:
        for target_id in hunter_shot_targets:
            PLAYERS[target_id]['alive'] = False

            dialogue_queue.put({
                "type": "death",
                "player_id": target_id
            })

        time.sleep(1.5)

    # 第1天且未提前上警，则现在上警
    if day_num == 1 and not ELECTION_BEFORE_N1:
        sheriff_election()

def sheriff_election_before_n1():
    """开局白天警长竞选（ELECTION_BEFORE_N1=True时使用）"""
    global sheriff_player_id, seer_claims, sheriff_candidates
    print("\n[SHERIFF ELECTION BEFORE N1] Starting...")

    dialogue_queue.put({
        "type": "phase",
        "phase": "day"
    })

    dialogue_queue.put({
        "type": "status",
        "message": "🎖️ 开局警长竞选"
    })

    # 随机选择3-5个玩家上警
    num_candidates = random.randint(3, 5)
    sheriff_candidates = random.sample(range(len(PLAYERS)), num_candidates)

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "警长竞选",
        "content": f"🎖️ 竞选警长的玩家: {', '.join(['Player ' + str(c) for c in sheriff_candidates])}",
        "panel": "day"
    })

    time.sleep(2)

    # 候选人依次发言
    for candidate_id in sheriff_candidates:
        if not is_running:
            break

        player = PLAYERS[candidate_id]

        prompt = f"""狼人杀 - 开局警长竞选。
你是Player {player['id']}，角色：{player['role']}。

请发表竞选演说，说明你为什么适合当警长。
重要：不要暴露你的真实身份！

请用2-3句话竞选。用中文。"""

        response = call_llm(prompt, player['id'])

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": player['id'],
            "phase": "警长竞选",
            "content": response,
            "panel": "day"
        })

        time.sleep(1.5)

    # 选举警长
    sheriff_id = random.choice(sheriff_candidates)
    sheriff_player_id = sheriff_id
    PLAYERS[sheriff_id]['is_sheriff'] = True

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "警长竞选",
        "content": f"🎖️ Player {sheriff_id} 当选警长！",
        "panel": "day"
    })

    time.sleep(2)
    print(f"[SHERIFF] Player {sheriff_id} elected.")

def sheriff_election():
    """警长竞选（第一夜后进行，候选人随机产生）"""
    global sheriff_player_id, seer_claims, sheriff_candidates
    print("\n[SHERIFF ELECTION] Starting...")

    dialogue_queue.put({
        "type": "phase",
        "phase": "day"
    })

    dialogue_queue.put({
        "type": "status",
        "message": "🎖️ 警长竞选"
    })

    # 生成候选人列表（3-5个玩家，包括狼人和好人）
    alive_players = [p for p in PLAYERS if p['alive']]
    num_candidates = min(random.randint(3, 5), len(alive_players))
    sheriff_candidates = random.sample([p['id'] for p in alive_players], num_candidates)

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "警长竞选",
        "content": f"🎖️ 竞选警长的玩家: {', '.join(['Player ' + str(c) for c in sheriff_candidates])}",
        "panel": "day"
    })

    time.sleep(2)

    # 候选人依次发言 - 必须跳预言家
    for candidate_id in sheriff_candidates:
        if not is_running:
            break

        player = PLAYERS[candidate_id]

        # 随机验人目标
        other_players = [p for p in range(len(PLAYERS)) if p != player['id']]
        checked_player = random.choice(other_players)
        checked_role = PLAYERS[checked_player]['role']
        is_werewolf = checked_role in ['狼人', '狼王']

        if player['role'] == '预言家':
            instruction = f"你是真预言家。昨晚验了Player {checked_player}，他是{'狼人' if is_werewolf else '好人'}。必须说'我是预言家'并报告验人。"
        elif player['role'] in ['狼人', '狼王']:
            fake_result = "狼人" if random.random() > 0.6 else "好人"
            instruction = f"你是狼人阵营，必须跳预言家（说'我是预言家'）并编造验人，例如'昨晚验了Player {checked_player}，他是{fake_result}'。绝对不能说你是狼人。"
        else:
            fake_result = "狼人" if random.random() > 0.6 else "好人"
            instruction = f"你必须跳预言家（说'我是预言家'）并编造验人，例如'昨晚验了Player {checked_player}，他是{fake_result}'。"

        prompt = f"""狼人杀 - 警长竞选。
你是Player {player['id']}，角色：{player['role']}。

{instruction}

重要：如果你是狼人阵营，绝对不能在发言中说"狼人"、"狼王"等暴露身份的词！

请用2-3句话竞选。用中文。"""

        response = call_llm(prompt, player['id'])

        if "我是预言家" in response or "预言家" in response:
            seer_claims.append(player['id'])

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": player['id'],
            "phase": "警长竞选",
            "content": response,
            "panel": "day"
        })

        time.sleep(1.5)

    # 选举警长
    sheriff_id = random.choice(sheriff_candidates)
    sheriff_player_id = sheriff_id
    PLAYERS[sheriff_id]['is_sheriff'] = True

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "警长竞选",
        "content": f"🎖️ Player {sheriff_id} 当选警长！",
        "panel": "day"
    })

    time.sleep(2)
    print(f"[SHERIFF] Player {sheriff_id} elected. Seer claims: {seer_claims}")

def day_discussion_and_voting(round_num):
    """白天讨论和投票（夜死已经在dawn_phase处理过，这里只做白天发言和投票）"""
    print(f"\n[DAY] Round {round_num} discussion and voting...")

    dialogue_queue.put({
        "type": "status",
        "message": f"☀️ 第{round_num}天讨论"
    })

    # 警长决定发言顺序（简化：随机顺序）
    alive_players = [p for p in PLAYERS if p['alive']]

    if not alive_players:
        return

    random.shuffle(alive_players)

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"第{round_num}天",
        "content": f"🎖️ 警长决定发言顺序：{', '.join([f'Player {p['id']}' for p in alive_players])}",
        "panel": "day"
    })

    time.sleep(1)

    # 依次发言
    for player in alive_players:
        if not is_running:
            break

        is_seer_claimer = player['id'] in seer_claims
        sheriff_info = "你是警长。" if player.get('is_sheriff') else ""

        if is_seer_claimer:
            other_alive = [p for p in PLAYERS if p['alive'] and p['id'] != player['id']]
            if other_alive:
                checked = random.choice(other_alive)
                is_wolf = checked['role'] in ['狼人', '狼王']
                instruction = f"你昨晚验了Player {checked['id']}，他是{'狼人' if is_wolf else '好人'}。报告验人。"
            else:
                instruction = "报告你的验人。"
        elif player['role'] in ['女巫', '猎人', '守卫']:
            instruction = "你是神职，不要暴露身份，以村民身份分析局势。"
        elif player['role'] in ['狼人', '狼王']:
            instruction = "你是狼人阵营，装成村民或继续跳预言家，误导好人。绝对不能说'狼人'、'狼王'等词暴露身份！"
        else:
            instruction = "你是村民，诚实分析局势，帮助好人阵营找出狼人。"

        # 构建历史发言上下文（仅当前轮次的发言）
        current_round_speeches = [s for s in public_memory_pool if s['round'] == round_num]
        history_context = ""
        if current_round_speeches:
            history_context = "\n\n【本轮发言记录】\n"
            for speech in current_round_speeches:
                history_context += f"Player {speech['player_id']}: {speech['content']}\n"
            history_context += "\n分析以上发言，找出逻辑漏洞和可疑之处，基于推理进行发言。"

        if uls_mode:
            # ULS++ L0模式：仅标题，严格限制
            seat = player['id'] + 1  # 转换为1-12的seat编号
            prompt = f"""Werewolf ULS++ L0 (Header-Only Mode) - Day {round_num} SPEECH
You are seat {seat}, role: {player['role']}. {sheriff_info}

{instruction}

**CRITICAL: L0 Mode - ONE line header ONLY, NO free text:**

Format:
PV:<seat>[|ALT:<seat>][|TIE:<seat>,<seat>]
[|SUS:<seat@score>,<seat@score>,<seat@score>]
[|EV:<±id>,<±id>]
[|CL:<role><±><str>@N{round_num}]
[|CF:<0..5>][|RK:<0..5>]

**L0 Constraints:**
- SUS: max 3 entries (top-k=3)
- EV: max 2 event references per turn
- Omit ST (defaults to A=aggressive)
- Omit K (fixed at {LLM_CONFIG['max_tokens']})
- Omit CF/RK if using defaults (CF=4.0, RK=3.0)
- Scores: 0.0-5.0
- Seats: 1-12 only
- Roles: S|W|Gd|H|WK

Example: PV:3|SUS:3@4.6,5@3.7,7@2.1|EV:+205,-118|CL:S+4@N2

NO text. NO explanation. ONLY the header line."""
        else:
            # 正常模式：自然语言 + 历史发言上下文
            prompt = f"""狼人杀 - 第{round_num}天讨论。
你是Player {player['id']}，角色：{player['role']}。{sheriff_info}

{instruction}{history_context}

要求：
1. 仔细分析之前玩家的发言，找出逻辑漏洞
2. 根据你的角色和策略进行推理
3. 给出你的判断和投票倾向
4. 简短发言（2-3句）。用中文。"""

        response = call_llm(prompt, player['id'])

        # 将发言存入公共记忆池
        public_memory_pool.append({
            "round": round_num,
            "player_id": player['id'],
            "content": response
        })

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": player['id'],
            "phase": f"第{round_num}天讨论",
            "content": response,
            "panel": "day"
        })

        time.sleep(1)

    # 投票处决
    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"第{round_num}天投票",
        "content": "🗳️ 投票阶段，请所有玩家投票。",
        "panel": "day"
    })

    time.sleep(1.5)

    alive_players = [p for p in PLAYERS if p['alive']]
    if len(alive_players) >= 2:
        # 统计投票
        vote_counts = {}

        # 每个玩家投票
        for voter in alive_players:
            if not is_running:
                break

            # 可以投票的目标（除了自己）
            vote_candidates = [p for p in alive_players if p['id'] != voter['id']]
            if not vote_candidates:
                continue

            # 构建投票决策的上下文
            current_round_speeches = [s for s in public_memory_pool if s['round'] == round_num]
            vote_context = "\n【所有玩家的发言】\n"
            for speech in current_round_speeches:
                vote_context += f"Player {speech['player_id']}: {speech['content']}\n"

            candidates_list = ", ".join([f"Player {p['id']}" for p in vote_candidates])

            # 根据角色给出投票策略指导
            if voter['role'] in ['狼人', '狼王']:
                vote_instruction = "你是狼人阵营，投票给对狼人威胁最大的好人（如预言家、强势村民）。"
            elif voter['role'] == '预言家':
                vote_instruction = "你是预言家，投票给你验出的狼人，或发言最可疑的玩家。"
            elif voter['role'] in ['女巫', '猎人', '守卫']:
                vote_instruction = "你是神职，投票给发言最可疑、逻辑有漏洞的玩家。"
            else:
                vote_instruction = "你是村民，投票给发言最可疑、逻辑有漏洞的玩家。"

            vote_prompt = f"""狼人杀 - 第{round_num}天投票决策
你是Player {voter['id']}，角色：{voter['role']}。

{vote_instruction}

{vote_context}

候选人：{candidates_list}

分析以上发言，选择一个最应该出局的玩家。只需要输出玩家编号，格式：Player X"""

            vote_response = call_llm(vote_prompt, voter['id'])

            # 从回复中提取玩家编号
            import re
            match = re.search(r'Player\s*(\d+)', vote_response, re.IGNORECASE)
            if match:
                voted_id = int(match.group(1))
                # 验证投票目标是否有效
                voted_for = next((p for p in vote_candidates if p['id'] == voted_id), None)
                if not voted_for:
                    # 如果提取的ID无效，随机选择
                    voted_for = random.choice(vote_candidates)
            else:
                # 如果无法解析，随机选择
                voted_for = random.choice(vote_candidates)

            # 记录投票
            if voted_for['id'] not in vote_counts:
                vote_counts[voted_for['id']] = []
            vote_counts[voted_for['id']].append(voter['id'])

            # 显示投票
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": voter['id'],
                "phase": f"第{round_num}天投票",
                "content": f"🗳️ 投票给 Player {voted_for['id']}",
                "panel": "day"
            })

            time.sleep(0.5)

        # 统计最高票数
        if vote_counts:
            max_votes = max(len(voters) for voters in vote_counts.values())
            candidates_with_max_votes = [player_id for player_id, voters in vote_counts.items() if len(voters) == max_votes]

            # 如果有平票，随机选一个
            vote_target_id = random.choice(candidates_with_max_votes)
            vote_target = next(p for p in PLAYERS if p['id'] == vote_target_id)

            # 显示投票结果
            vote_result_lines = ["📊 投票结果："]
            for player_id in sorted(vote_counts.keys()):
                voters = vote_counts[player_id]
                vote_result_lines.append(f"  Player {player_id}: {len(voters)}票 ({', '.join([f'P{v}' for v in voters])})")

            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": f"第{round_num}天投票",
                "content": "\n".join(vote_result_lines),
                "panel": "day"
            })

            time.sleep(1)
        else:
            vote_target = random.choice(alive_players)

        # 更新今日统计 - 记录白天处决的玩家
        if daily_statistics and len(daily_statistics) > 0:
            daily_statistics[-1]["day_execution"] = {
                "player_id": vote_target['id'],
                "role": vote_target['role']
            }

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"第{round_num}天投票",
            "content": f"🗳️ Player {vote_target['id']} 得票最多，被处决。",
            "panel": "day"
        })

        # 被处决玩家发表遗言
        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"第{round_num}天投票",
            "content": f"💬 Player {vote_target['id']} 请发表遗言。",
            "panel": "day"
        })

        time.sleep(1)

        # 生成遗言
        last_words_prompt = f"""狼人杀游戏 - 你被投票处决了。
你是Player {vote_target['id']}，角色：{vote_target['role']}。

现在是你的遗言时刻，请发表临终遗言：
- 如果你是好人阵营，可以留下关键信息帮助队友
- 如果你是狼人阵营，可以尝试误导对手
- 表达你的想法和建议

请用2-3句话发表遗言。用中文。"""

        last_words = call_llm(last_words_prompt, vote_target['id'])

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": vote_target['id'],
            "phase": f"第{round_num}天-遗言",
            "content": f"[遗言] {last_words}",
            "panel": "day"
        })

        time.sleep(2)

        vote_target['alive'] = False

        dialogue_queue.put({
            "type": "dialogue",
            "player_id": -1,
            "phase": f"第{round_num}天投票",
            "content": f"⚰️ Player {vote_target['id']} ({vote_target['role']}) 被投票处决。",
            "panel": "day"
        })

        dialogue_queue.put({
            "type": "death",
            "player_id": vote_target['id']
        })

        time.sleep(1)

        # 猎人/狼王技能
        if vote_target['role'] == '猎人':
            other_alive = [p for p in PLAYERS if p['alive']]
            if other_alive:
                hunter_target = random.choice(other_alive)
                hunter_target['alive'] = False

                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": vote_target['id'],
                    "phase": f"第{round_num}天-猎人",
                    "content": f"🏹 猎人开枪带走 Player {hunter_target['id']}",
                    "panel": "day"
                })

                dialogue_queue.put({
                    "type": "death",
                    "player_id": hunter_target['id']
                })

                time.sleep(1.5)

        elif vote_target['role'] == '狼王':
            other_alive = [p for p in PLAYERS if p['alive']]
            if other_alive:
                wolf_king_target = random.choice(other_alive)
                wolf_king_target['alive'] = False

                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": vote_target['id'],
                    "phase": f"第{round_num}天-狼王",
                    "content": f"👑 狼王带走 Player {wolf_king_target['id']}",
                    "panel": "day"
                })

                dialogue_queue.put({
                    "type": "death",
                    "player_id": wolf_king_target['id']
                })

                time.sleep(1.5)

    # 清空夜晚行动
    game_state['night_actions'] = {}

    # 显示今日统计
    display_daily_statistics(round_num)

    # 等待用户点击"下一天"按钮
    global waiting_for_next_day
    waiting_for_next_day = True

    dialogue_queue.put({
        "type": "waiting_for_next",
        "message": "等待用户点击下一天"
    })

    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "等待",
        "content": "⏸️ 点击下一天按钮继续游戏",
        "panel": "day"
    })

    # 等待waiting_for_next_day变为False
    while waiting_for_next_day and is_running:
        time.sleep(0.5)

def update_realtime_statistics():
    """实时更新统计面板"""
    if not daily_statistics or len(daily_statistics) == 0:
        return

    stats = daily_statistics[-1]
    day_num = stats["day"]

    # 构建实时统计信息
    stats_lines = []
    stats_lines.append(f"📊 第{day_num}天 实时统计")
    stats_lines.append("=" * 35)

    # 夜晚行动
    if stats["night_actions"]:
        stats_lines.append("\n🌙 夜晚行动:")
        actions = stats["night_actions"]
        if "wolf_target" in actions:
            stats_lines.append(f"  🐺 狼刀: Player {actions['wolf_target']}")
        if "guard_target" in actions:
            stats_lines.append(f"  🛡️ 守卫: Player {actions['guard_target']}")
        if "seer_check" in actions:
            check = actions['seer_check']
            stats_lines.append(f"  👁️ 验人: P{check['target']} → {check['result']}")
        if "witch_save" in actions:
            stats_lines.append(f"  🧪 解药: Player {actions['witch_save']}")
        if "witch_poison" in actions:
            stats_lines.append(f"  🧪 毒药: Player {actions['witch_poison']}")

    # 夜晚死亡
    if stats["night_deaths"]:
        death_list = ', '.join([f"P{p}" for p in stats["night_deaths"]])
        stats_lines.append(f"\n💀 夜晚死亡: {death_list}")
    else:
        stats_lines.append("\n🎉 平安夜")

    # 白天处决
    if stats["day_execution"]:
        exec_info = stats["day_execution"]
        stats_lines.append(f"\n🗳️ 白天处决: Player {exec_info['player_id']}")
        stats_lines.append(f"   身份: {exec_info['role']}")

    # 当前存活统计
    alive_players = [p for p in PLAYERS if p['alive']]
    alive_werewolves = [p for p in alive_players if p['role'] in ['狼人', '狼王']]
    alive_villagers = [p for p in alive_players if p['role'] not in ['狼人', '狼王']]

    stats_lines.append("\n" + "=" * 35)
    stats_lines.append(f"📈 存活: 🐺{len(alive_werewolves)} vs 👨‍🌾{len(alive_villagers)}")

    stats_content = "\n".join(stats_lines)

    # 发送到统计面板
    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"第{day_num}天",
        "content": stats_content,
        "panel": "statistics"
    })

def display_daily_statistics(day_num):
    """显示每天统计信息"""
    alive_players = [p for p in PLAYERS if p['alive']]
    alive_werewolves = [p for p in alive_players if p['role'] in ['狼人', '狼王']]
    alive_villagers = [p for p in alive_players if p['role'] not in ['狼人', '狼王']]

    # 更新今日统计中的存活人数
    if daily_statistics and len(daily_statistics) > 0:
        daily_statistics[-1]["alive_werewolves"] = len(alive_werewolves)
        daily_statistics[-1]["alive_villagers"] = len(alive_villagers)

    # 构建统计信息
    stats_lines = []
    stats_lines.append(f"📊 第{day_num}天统计信息 📊")
    stats_lines.append("-" * 40)

    if daily_statistics and len(daily_statistics) > 0:
        stats = daily_statistics[-1]

        # 夜晚行动统计
        if stats["night_actions"]:
            stats_lines.append("🌙 夜晚行动:")
            actions = stats["night_actions"]
            if "wolf_target" in actions:
                stats_lines.append(f"  🐺 狼人刀: Player {actions['wolf_target']}")
            if "guard_target" in actions:
                stats_lines.append(f"  🛡️ 守卫守护: Player {actions['guard_target']}")
            if "seer_check" in actions:
                check = actions['seer_check']
                stats_lines.append(f"  👁️ 预言家验: Player {check['target']} ({check['result']})")
            if "witch_save" in actions:
                stats_lines.append(f"  🧪 女巫救: Player {actions['witch_save']}")
            if "witch_poison" in actions:
                stats_lines.append(f"  🧪 女巫毒: Player {actions['witch_poison']}")

        # 夜晚死亡统计
        if stats["night_deaths"]:
            death_list = ', '.join([f"Player {p}" for p in stats["night_deaths"]])
            stats_lines.append(f"💀 夜晚死亡: {death_list}")
        else:
            stats_lines.append("🎉 夜晚平安夜")

        # 白天处决统计
        if stats["day_execution"]:
            exec_info = stats["day_execution"]
            stats_lines.append(f"🗳️ 白天处决: Player {exec_info['player_id']} ({exec_info['role']})")

    # 当前存活统计
    stats_lines.append("-" * 40)
    stats_lines.append(f"📈 当前存活: 狼人 {len(alive_werewolves)} 人 | 好人 {len(alive_villagers)} 人")

    # 检查是否触发游戏结束条件
    if len(alive_werewolves) >= len(alive_villagers):
        stats_lines.append("⚠️ 触发游戏结束条件: 狼人数 ≥ 好人数")
        if daily_statistics and len(daily_statistics) > 0:
            daily_statistics[-1]["game_ended"] = True
            daily_statistics[-1]["winner"] = "werewolves"
    elif len(alive_werewolves) == 0:
        stats_lines.append("⚠️ 触发游戏结束条件: 狼人全灭")
        if daily_statistics and len(daily_statistics) > 0:
            daily_statistics[-1]["game_ended"] = True
            daily_statistics[-1]["winner"] = "villagers"
    else:
        stats_lines.append("✅ 游戏继续")

    stats_content = "\n".join(stats_lines)

    # 发送统计信息到统计面板（statistics panel）
    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": f"第{day_num}天统计",
        "content": stats_content,
        "panel": "statistics"
    })

    time.sleep(2)

def display_game_summary():
    """游戏结束时显示完整统计摘要"""
    summary_lines = []
    summary_lines.append("=" * 50)
    summary_lines.append("🎮 游戏统计摘要 🎮")
    summary_lines.append("=" * 50)

    for i, stats in enumerate(daily_statistics, 1):
        summary_lines.append(f"\n📅 第{stats['day']}天:")
        summary_lines.append("-" * 40)

        # 夜晚行动
        if stats["night_actions"]:
            summary_lines.append("  🌙 夜晚行动:")
            actions = stats["night_actions"]
            if "wolf_target" in actions:
                summary_lines.append(f"    🐺 狼人刀: Player {actions['wolf_target']}")
            if "guard_target" in actions:
                summary_lines.append(f"    🛡️ 守卫守: Player {actions['guard_target']}")
            if "seer_check" in actions:
                check = actions['seer_check']
                summary_lines.append(f"    👁️ 预言家验: Player {check['target']} → {check['result']}")
            if "witch_save" in actions:
                summary_lines.append(f"    🧪 女巫救: Player {actions['witch_save']}")
            if "witch_poison" in actions:
                summary_lines.append(f"    🧪 女巫毒: Player {actions['witch_poison']}")

        # 夜晚死亡
        if stats["night_deaths"]:
            death_list = ', '.join([f"Player {p}" for p in stats["night_deaths"]])
            summary_lines.append(f"  💀 夜晚死亡: {death_list}")
        else:
            summary_lines.append("  🎉 平安夜")

        # 白天处决
        if stats["day_execution"]:
            exec_info = stats["day_execution"]
            summary_lines.append(f"  🗳️ 白天处决: Player {exec_info['player_id']} ({exec_info['role']})")

        # 当天结束后存活情况
        summary_lines.append(f"  📈 存活: 狼人 {stats['alive_werewolves']} | 好人 {stats['alive_villagers']}")

        if stats["game_ended"]:
            winner_name = "狼人阵营" if stats["winner"] == "werewolves" else "村民阵营"
            summary_lines.append(f"  🏆 游戏结束 - {winner_name}胜利！")

    summary_lines.append("=" * 50)
    summary_content = "\n".join(summary_lines)

    # 发送到白天面板
    dialogue_queue.put({
        "type": "dialogue",
        "player_id": -1,
        "phase": "游戏摘要",
        "content": summary_content,
        "panel": "day"
    })

    # 同时打印到控制台
    print("\n" + summary_content)
    time.sleep(3)

def check_win_condition():
    """检查胜利条件，返回 (winner, reason, details) 或 (None, None, None)"""
    alive_players = [p for p in PLAYERS if p['alive']]
    alive_werewolves = [p for p in alive_players if p['role'] in ['狼人', '狼王']]
    alive_villagers = [p for p in alive_players if p['role'] not in ['狼人', '狼王']]

    # 获取存活玩家的详细信息
    werewolf_list = [f"Player {p['id']} ({p['role']})" for p in alive_werewolves]
    villager_list = [f"Player {p['id']} ({p['role']})" for p in alive_villagers]

    if len(alive_werewolves) >= len(alive_villagers):
        reason = f"狼人数量({len(alive_werewolves)})已经大于等于好人数量({len(alive_villagers)})"
        details = f"\n\n存活狼人: {', '.join(werewolf_list) if werewolf_list else '无'}\n存活好人: {', '.join(villager_list) if villager_list else '无'}"
        return ('werewolves', reason, details)

    if len(alive_werewolves) == 0:
        reason = "所有狼人已被消灭"
        details = f"\n\n存活好人: {', '.join(villager_list)}"
        return ('villagers', reason, details)

    return (None, None, None)

def game_loop():
    """
    完整游戏循环
    if ELECTION_BEFORE_N1:
        警长竞选 → Night(1) → Dawn → Day(1) → Night(2) → Dawn → Day(2) → ...
    else:
        Night(1) → Dawn → Day(1) → Night(2) → Dawn → Day(2) → ...
    """
    global is_running, guard_last_target, witch_save_available, witch_poison_available, uls_mode

    print(f"\n[GAME_LOOP] Starting game with ULS_MODE = {uls_mode}")

    day_num = 1

    # 根据配置决定是否先上警
    if ELECTION_BEFORE_N1 and is_running:
        # 先警长竞选（开局白天上警）
        sheriff_election_before_n1()

    # 第一夜
    if is_running:
        # 执行第一夜（包含完整的夜晚阶段）
        night_deaths = night_phase(1)

        if night_deaths is None:  # 狼人全灭
            dialogue_queue.put({
                "type": "status",
                "message": "🎉 游戏结束 - 村民阵营胜利！"
            })
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": "游戏结束",
                "content": "👨‍🌾 村民阵营获胜！所有狼人已被击杀。",
                "panel": "day"
            })
            display_game_summary()
            is_running = False
            return

        # 黎明阶段
        dawn_phase(night_deaths, 1)

        # 警长竞选（如果没有提前上警）
        if is_running and not ELECTION_BEFORE_N1:
            sheriff_election()

    # 主游戏循环
    while is_running:
        # 检查胜利条件
        winner, reason, details = check_win_condition()
        if winner:
            dialogue_queue.put({
                "type": "status",
                "message": f"🎉 游戏结束 - {'狼人' if winner == 'werewolves' else '村民'}阵营胜利！"
            })

            panel = "day"
            if winner == 'werewolves':
                content = f"🐺 狼人阵营获胜！\n\n胜利原因: {reason}{details}"
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "游戏结束",
                    "content": content,
                    "panel": panel
                })
            else:
                content = f"👨‍🌾 村民阵营获胜！\n\n胜利原因: {reason}{details}"
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "游戏结束",
                    "content": content,
                    "panel": panel
                })

            display_game_summary()
            is_running = False
            break

        # 白天讨论投票
        day_discussion_and_voting(day_num)

        # 再次检查胜利
        winner, reason, details = check_win_condition()
        if winner:
            dialogue_queue.put({
                "type": "status",
                "message": f"🎉 游戏结束 - {'狼人' if winner == 'werewolves' else '村民'}阵营胜利！"
            })

            panel = "day"
            if winner == 'werewolves':
                content = f"🐺 狼人阵营获胜！\n\n胜利原因: {reason}{details}"
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "游戏结束",
                    "content": content,
                    "panel": panel
                })
            else:
                content = f"👨‍🌾 村民阵营获胜！\n\n胜利原因: {reason}{details}"
                dialogue_queue.put({
                    "type": "dialogue",
                    "player_id": -1,
                    "phase": "游戏结束",
                    "content": content,
                    "panel": panel
                })

            display_game_summary()
            is_running = False
            break

        # 夜晚阶段
        day_num += 1

        # 执行完整的夜晚阶段
        night_deaths = night_phase(day_num)

        if night_deaths is None:  # 狼人全灭
            dialogue_queue.put({
                "type": "status",
                "message": "🎉 游戏结束 - 村民阵营胜利！"
            })
            dialogue_queue.put({
                "type": "dialogue",
                "player_id": -1,
                "phase": "游戏结束",
                "content": "👨‍🌾 村民阵营获胜！所有狼人已被击杀。",
                "panel": "day"
            })
            display_game_summary()
            is_running = False
            break

        # 黎明阶段
        dawn_phase(night_deaths, day_num)

        time.sleep(2)

@app.route('/')
def index():
    import time
    # 添加时间戳强制刷新
    return render_template_string(HTML_TEMPLATE, players=PLAYERS), 200, {
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache',
        'Expires': '0'
    }

@app.route('/api/start', methods=['POST'])
def start():
    global is_running, seer_claims, sheriff_player_id, sheriff_candidates, game_state
    global guard_last_target, witch_save_available, witch_poison_available, daily_statistics
    global waiting_for_next_day, auto_mode, total_tokens_used, player_tokens_used

    if not is_running:
        is_running = True
        waiting_for_next_day = False
        # auto_mode 保持用户设置，不重置
        seer_claims = []
        sheriff_player_id = None
        sheriff_candidates = []
        guard_last_target = None
        witch_save_available = True
        witch_poison_available = True
        daily_statistics = []  # 重置统计
        total_tokens_used = 0  # 重置token统计
        player_tokens_used = {}  # 重置每个玩家的token统计
        game_state = {
            "phase": "night",
            "round": 0,
            "dead_players": [],
            "night_actions": {}
        }

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

    # 如果切换到自动模式且正在等待，立即继续
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

@app.route('/api/get_llm_config', methods=['GET'])
def get_llm_config():
    """获取当前LLM配置"""
    return {"status": "ok", "config": LLM_CONFIG}

@app.route('/api/set_llm_config', methods=['POST'])
def set_llm_config():
    global LLM_CONFIG

    try:
        from flask import request
        data = request.get_json()

        # 更新测试模型配置
        if 'test_api_base' in data:
            LLM_CONFIG['test_api_base'] = data['test_api_base']
        if 'test_model' in data:
            LLM_CONFIG['test_model'] = data['test_model']

        # 更新NPC模型配置
        if 'npc_api_base' in data:
            LLM_CONFIG['npc_api_base'] = data['npc_api_base']
        if 'npc_model' in data:
            LLM_CONFIG['npc_model'] = data['npc_model']

        print(f"[LLM_CONFIG] Updated:")
        print(f"  Test API: {LLM_CONFIG['test_api_base']} / {LLM_CONFIG['test_model']}")
        print(f"  NPC API:  {LLM_CONFIG['npc_api_base']} / {LLM_CONFIG['npc_model']}")

        # 保存配置到文件
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

        # 验证范围
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
            return {"status": "error", "message": "无效的版本号"}, 400

        base_dir = os.path.dirname(os.path.abspath(__file__))
        current_file = os.path.join(base_dir, 'werewolf_3panels.py')
        source_file = os.path.join(base_dir, f'werewolf_3panels_{version}.py')

        if not os.path.exists(source_file):
            return {"status": "error", "message": f"{version}版本文件不存在"}, 404

        # 备份当前文件
        temp_file = os.path.join(base_dir, 'werewolf_3panels_temp.py')
        shutil.copy(current_file, temp_file)

        # 复制目标版本
        shutil.copy(source_file, current_file)

        print(f"[VERSION] Switched to {version}")
        return {"status": "ok", "message": f"已切换到{version}版本"}

    except Exception as e:
        print(f"[VERSION] Error switching version: {e}")
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
    print("="*70)
    print("狼人杀 - 4对话框版本")
    print("="*70)
    print("\n[INFO] Starting server on http://localhost:5004")
    print("[INFO] 游戏流程：")
    print("  1. 第1夜：狼人讨论（刀谁、谁上警）")
    print("  2. 第1夜：神职行动")
    print("  3. 天亮：警长竞选")
    print("  4. 白天：讨论投票")
    print("  5. 夜晚循环...")
    print("[INFO] UI：4个对话框（狼人/神职/白天/统计）")
    print("="*70)

    app.run(host='127.0.0.1', port=5004, debug=False)
