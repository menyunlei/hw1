"""
Integrated Web UI with Game Control and Real-time Visualization
集成的Web界面，包含游戏控制和实时可视化
"""

from flask import Flask, render_template_string, jsonify, request
import threading
import subprocess
import sys
import json
import time
import os
import queue
from datetime import datetime

app = Flask(__name__)

# Global variables
game_process = None
game_thread = None
game_status = "idle"  # idle, running, completed, error
game_output = []
game_events = []
output_queue = queue.Queue()

# HTML Template with integrated controls
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Werewolf Game - Integrated Control Center</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px 30px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }

        .header h1 {
            color: #333;
            font-size: 28px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .status-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
            margin-left: 20px;
        }

        .status-idle { background: #e0e0e0; color: #666; }
        .status-running { background: #4CAF50; color: white; animation: pulse 2s infinite; }
        .status-completed { background: #2196F3; color: white; }
        .status-error { background: #f44336; color: white; }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.7; }
            100% { opacity: 1; }
        }

        .control-panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.15);
        }

        .control-buttons {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }

        .btn {
            padding: 12px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }

        .btn-start {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-stop {
            background: #f44336;
            color: white;
        }

        .btn-clear {
            background: #FF9800;
            color: white;
        }

        .btn-export {
            background: #607D8B;
            color: white;
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .main-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }

        .panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.15);
            max-height: 600px;
            display: flex;
            flex-direction: column;
        }

        .panel-header {
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }

        .console-output {
            background: #1e1e1e;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            font-size: 14px;
            padding: 15px;
            border-radius: 8px;
            overflow-y: auto;
            flex: 1;
            white-space: pre-wrap;
            word-wrap: break-word;
        }

        .events-container {
            overflow-y: auto;
            flex: 1;
        }

        .event-item {
            background: #f5f5f5;
            border-left: 4px solid #667eea;
            padding: 10px 15px;
            margin-bottom: 10px;
            border-radius: 5px;
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

        .event-time {
            color: #666;
            font-size: 12px;
        }

        .event-type {
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }

        .event-data {
            color: #555;
            margin-top: 5px;
            font-size: 14px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .stat-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }

        .stat-value {
            font-size: 24px;
            font-weight: bold;
        }

        .stat-label {
            font-size: 14px;
            opacity: 0.9;
            margin-top: 5px;
        }
        
        /* Enhanced visualization styles */
        .visualization-container {
            margin-top: 20px;
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }
        
        .player-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
            gap: 10px;
        }
        
        .player-card {
            background: #f5f5f5;
            border-radius: 8px;
            padding: 12px;
            position: relative;
            transition: all 0.3s ease;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .player-card.dead {
            opacity: 0.6;
            background: #e0e0e0;
        }
        
        .player-card.werewolf {
            border-left: 4px solid #f44336;
        }
        
        .player-card.villager {
            border-left: 4px solid #4CAF50;
        }
        
        .player-card.special {
            border-left: 4px solid #2196F3;
        }
        
        .player-card.sheriff {
            box-shadow: 0 0 0 2px gold;
        }
        
        .player-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .player-role {
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
        }
        
        .player-status {
            font-size: 12px;
            padding: 2px 6px;
            border-radius: 10px;
            display: inline-block;
        }
        
        .player-metrics {
            margin-top: 8px;
            font-size: 12px;
        }
        
        .timeline-container {
            overflow-x: auto;
            padding: 10px 0;
        }
        
        .timeline {
            display: flex;
            min-width: 100%;
            padding: 20px 0;
            position: relative;
        }
        
        .timeline::before {
            content: '';
            position: absolute;
            top: 20px;
            left: 0;
            right: 0;
            height: 2px;
            background: #ddd;
        }
        
        .timeline-event {
            position: relative;
            min-width: 100px;
            margin-right: 20px;
            padding-top: 15px;
        }
        
        .timeline-dot {
            position: absolute;
            width: 16px;
            height: 16px;
            background: #667eea;
            border-radius: 50%;
            top: 13px;
            left: 42px;
            z-index: 2;
        }
        
        .night-event .timeline-dot {
            background: #333;
        }
        
        .day-event .timeline-dot {
            background: #FF9800;
        }
        
        .vote-event .timeline-dot {
            background: #f44336;
        }
        
        .timeline-content {
            background: #fff;
            border-radius: 8px;
            padding: 10px;
            margin-top: 10px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            max-width: 200px;
        }
        
        .timeline-title {
            font-weight: bold;
            font-size: 14px;
            margin-bottom: 5px;
        }
        
        .timeline-desc {
            font-size: 12px;
            color: #666;
        }
        
        /* LLM Agent Dialog Visualization Styles - Circular Layout */
        .agent-dialog-container {
            margin-top: 20px;
            border-radius: 8px;
            background: #f9f9f9;
            padding: 15px;
        }

        .dialog-filters {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
            justify-content: center;
        }

        .dialog-filter {
            padding: 5px 12px;
            border: none;
            border-radius: 15px;
            background: #e0e0e0;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }

        .dialog-filter.active {
            background: #667eea;
            color: white;
        }

        /* Circular table layout */
        .circular-table-container {
            position: relative;
            width: 100%;
            min-height: 700px;
            padding: 20px;
        }

        /* Center table */
        .center-table {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 200px;
            height: 200px;
            background: linear-gradient(135deg, #8B4513 0%, #A0522D 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            border: 8px solid #654321;
        }

        .center-table-text {
            color: white;
            font-size: 18px;
            font-weight: bold;
            text-align: center;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        }

        /* Player bubble positioning around the circle */
        .player-bubble {
            position: absolute;
            width: 140px;
            background: white;
            border-radius: 12px;
            padding: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            transition: all 0.3s ease;
            cursor: pointer;
            border: 3px solid #ddd;
        }

        .player-bubble:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 12px rgba(0,0,0,0.25);
            z-index: 100;
        }

        .player-bubble.werewolf {
            border-color: #f44336;
            background: linear-gradient(135deg, #fff 0%, #ffebee 100%);
        }

        .player-bubble.villager {
            border-color: #4CAF50;
            background: linear-gradient(135deg, #fff 0%, #e8f5e9 100%);
        }

        .player-bubble.special {
            border-color: #FF9800;
            background: linear-gradient(135deg, #fff 0%, #fff3e0 100%);
        }

        .player-bubble.dead {
            opacity: 0.5;
            filter: grayscale(100%);
        }

        .player-bubble.speaking {
            animation: speaking-pulse 1.5s infinite;
            border-width: 4px;
        }

        @keyframes speaking-pulse {
            0%, 100% {
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }
            50% {
                box-shadow: 0 8px 20px rgba(102, 126, 234, 0.6);
                transform: scale(1.08);
            }
        }

        /* Player bubble header */
        .player-bubble-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 2px solid #eee;
        }

        .player-bubble-name {
            font-weight: bold;
            font-size: 13px;
            color: #333;
        }

        .player-bubble-emoji {
            font-size: 18px;
        }

        /* Latest dialog content */
        .player-bubble-dialog {
            font-size: 12px;
            color: #555;
            line-height: 1.4;
            max-height: 80px;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 4;
            -webkit-box-orient: vertical;
        }

        .player-bubble-meta {
            margin-top: 6px;
            font-size: 10px;
            color: #999;
            display: flex;
            justify-content: space-between;
        }

        /* Speech indicator */
        .speech-indicator {
            position: absolute;
            top: -10px;
            right: -10px;
            width: 30px;
            height: 30px;
            background: #667eea;
            border-radius: 50%;
            display: none;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 16px;
            animation: bounce 0.6s infinite;
        }

        .player-bubble.speaking .speech-indicator {
            display: flex;
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }

        /* Modal for full dialog history */
        .dialog-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .dialog-modal.active {
            display: flex;
        }

        .dialog-modal-content {
            background: white;
            border-radius: 15px;
            padding: 25px;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }

        .dialog-modal-header {
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 20px;
            color: #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .dialog-modal-close {
            cursor: pointer;
            font-size: 24px;
            color: #999;
            transition: color 0.2s;
        }

        .dialog-modal-close:hover {
            color: #333;
        }

        .dialog-history-item {
            background: #f9f9f9;
            border-left: 4px solid #667eea;
            padding: 12px;
            margin-bottom: 12px;
            border-radius: 6px;
        }

        .dialog-history-item.werewolf {
            border-left-color: #f44336;
        }

        .dialog-history-item.villager {
            border-left-color: #4CAF50;
        }

        .dialog-history-item.special {
            border-left-color: #FF9800;
        }

        .dialog-history-meta {
            font-size: 12px;
            color: #999;
            margin-bottom: 8px;
        }

        .dialog-history-content {
            color: #444;
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
        }
        
        /* Role-specific Actions Styles */
        .role-actions-container {
            margin-top: 15px;
        }
        
        .role-action-groups {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .role-action-group {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            overflow: hidden;
        }
        
        .role-action-header {
            background: #667eea;
            color: white;
            padding: 8px 12px;
            font-weight: bold;
            font-size: 14px;
        }
        
        #werewolf-actions .role-action-header {
            background: #f44336;
        }
        
        #seer-actions .role-action-header {
            background: #2196F3;
        }
        
        #witch-actions .role-action-header {
            background: #9C27B0;
        }
        
        #hunter-actions .role-action-header {
            background: #FF9800;
        }
        
        .role-action-list {
            padding: 8px 12px;
            max-height: 150px;
            overflow-y: auto;
        }
        
        .role-action-item {
            padding: 6px 0;
            border-bottom: 1px solid #eee;
            font-size: 13px;
            color: #555;
        }
        
        .role-action-item:last-child {
            border-bottom: none;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .config-section {
            margin-top: 15px;
            padding: 15px;
            background: #f5f5f5;
            border-radius: 8px;
        }

        .config-item {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }

        .config-label {
            width: 150px;
            font-weight: bold;
            color: #555;
        }

        .config-input {
            flex: 1;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
        }

        .loading-spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>
                🐺 Werewolf Game Control Center
                <span id="status-badge" class="status-badge status-idle">IDLE</span>
            </h1>
        </div>

        <div class="control-panel">
            <div class="control-buttons">
                <button id="btn-start" class="btn btn-start" onclick="startGame()">
                    ▶️ Start Game
                </button>
                <button id="btn-stop" class="btn btn-stop" onclick="stopGame()" disabled>
                    ⏹️ Stop Game
                </button>
                <button id="btn-clear" class="btn btn-clear" onclick="clearOutput()">
                    🗑️ Clear Output
                </button>
                <button id="btn-export" class="btn btn-export" onclick="exportResults()">
                    📥 Export Results
                </button>
            </div>

            <div class="config-section">
                <div class="config-item">
                    <span class="config-label">API Endpoint:</span>
                    <input type="text" id="api-endpoint" class="config-input"
                           value="http://localhost:8080" placeholder="http://localhost:8080">
                </div>
                <div class="config-item">
                    <span class="config-label">Model:</span>
                    <input type="text" id="model-name" class="config-input"
                           value="/home/apulis-dev/userdata/Llama-3.3-70B-Instruct"
                           placeholder="Model name">
                </div>
            </div>
        </div>

        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <div class="stat-value" id="stat-round">0</div>
                <div class="stat-label">Current Round</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-alive">13</div>
                <div class="stat-label">Players Alive</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-events">0</div>
                <div class="stat-label">Total Events</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="stat-duration">00:00</div>
                <div class="stat-label">Duration</div>
            </div>
        </div>

        <div class="main-content">
            <div class="panel">
                <div class="panel-header">📟 Game Console Output</div>
                <div class="console-output" id="console-output">
                    Waiting for game to start...
                    Click "Start Game" to begin.
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">📊 Game Events</div>
                <div class="events-container" id="events-container">
                    <div class="event-item">
                        <div class="event-time">System Ready</div>
                        <div class="event-type">Waiting for game start</div>
                        <div class="event-data">Configure settings and click Start Game</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Player Status Section -->
        <div class="visualization-container">
            <div class="panel" style="max-height: none;">
                <div class="panel-header">🧩 Players Status</div>
                <div class="player-grid" id="player-grid">
                    <!-- Player cards will be generated here -->
                    <div class="player-card villager">
                        <div class="player-name">Player 1 (初始状态)</div>
                        <div class="player-role">角色未知</div>
                        <div class="player-status">存活</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Simple Dialogue Output -->
        <div class="visualization-container">
            <div class="panel" style="max-height: none;">
                <div class="panel-header">💬 Player Dialogues</div>
                <div id="dialogue-output" style="background: white; padding: 20px; border-radius: 8px; font-family: monospace; font-size: 14px; line-height: 1.8; max-height: 600px; overflow-y: auto;">
                    <div style="color: #999;">Waiting for player dialogues...</div>
                </div>
            </div>
        </div>

        <!-- Dialog History Modal -->
        <div class="dialog-modal" id="dialog-modal">
            <div class="dialog-modal-content">
                <div class="dialog-modal-header">
                    <span id="modal-player-title">Player Dialog History</span>
                    <span class="dialog-modal-close" onclick="closeDialogModal()">&times;</span>
                </div>
                <div id="dialog-history-list">
                    <!-- Dialog history items will be added here -->
                </div>
            </div>
        </div>

        <!-- Game Timeline Section -->
        <div class="visualization-container">
            <div class="panel" style="max-height: none;">
                <div class="panel-header">⏱️ Game Timeline</div>
                <div class="timeline-container">
                    <div class="timeline" id="timeline">
                        <!-- Timeline events will be generated here -->
                        <div class="timeline-event">
                            <div class="timeline-dot"></div>
                            <div class="timeline-content">
                                <div class="timeline-title">游戏开始</div>
                                <div class="timeline-desc">等待游戏开始...</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Role-specific Actions Section -->
        <div class="visualization-container">
            <div class="panel" style="max-height: none;">
                <div class="panel-header">🎭 Role-specific Actions</div>
                <div class="role-actions-container">
                    <div class="role-action-groups">
                        <div class="role-action-group" id="werewolf-actions">
                            <div class="role-action-header">🐺 Werewolves</div>
                            <div class="role-action-list" id="werewolf-action-list">
                                <div class="role-action-item">等待狼人行动...</div>
                            </div>
                        </div>
                        <div class="role-action-group" id="seer-actions">
                            <div class="role-action-header">👁️ Seer</div>
                            <div class="role-action-list" id="seer-action-list">
                                <div class="role-action-item">等待预言家行动...</div>
                            </div>
                        </div>
                        <div class="role-action-group" id="witch-actions">
                            <div class="role-action-header">🧪 Witch</div>
                            <div class="role-action-list" id="witch-action-list">
                                <div class="role-action-item">等待女巫行动...</div>
                            </div>
                        </div>
                        <div class="role-action-group" id="hunter-actions">
                            <div class="role-action-header">🏹 Hunter</div>
                            <div class="role-action-list" id="hunter-action-list">
                                <div class="role-action-item">等待猎人行动...</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let gameStatus = 'idle';
        let eventSource = null;
        let startTime = null;
        let durationTimer = null;

        function updateStatus(status) {
            gameStatus = status;
            const badge = document.getElementById('status-badge');
            badge.className = `status-badge status-${status}`;
            badge.textContent = status.toUpperCase();

            // Update button states
            document.getElementById('btn-start').disabled = (status === 'running');
            document.getElementById('btn-stop').disabled = (status !== 'running');
        }

        function startGame() {
            if (gameStatus === 'running') return;

            const apiEndpoint = document.getElementById('api-endpoint').value;
            const modelName = document.getElementById('model-name').value;

            updateStatus('running');
            clearOutput();
            startTime = Date.now();
            startDurationTimer();

            // Start game via API
            fetch('/api/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    api_endpoint: apiEndpoint,
                    model: modelName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'started') {
                    appendToConsole('[SYSTEM] Game started successfully\\n');
                    startEventStream();
                } else {
                    updateStatus('error');
                    appendToConsole('[ERROR] Failed to start game: ' + data.message);
                }
            })
            .catch(error => {
                updateStatus('error');
                appendToConsole('[ERROR] ' + error.message);
            });
        }

        function stopGame() {
            fetch('/api/stop', {method: 'POST'})
            .then(response => response.json())
            .then(data => {
                updateStatus('idle');
                appendToConsole('\\n[SYSTEM] Game stopped by user\\n');
                stopEventStream();
                stopDurationTimer();
            });
        }

        function clearOutput() {
            document.getElementById('console-output').textContent = '';
            document.getElementById('events-container').innerHTML = '';
            document.getElementById('stat-events').textContent = '0';
        }

        function appendToConsole(text) {
            const console = document.getElementById('console-output');
            console.textContent += text;
            console.scrollTop = console.scrollHeight;
        }

        function addEvent(event) {
            const container = document.getElementById('events-container');
            const eventDiv = document.createElement('div');
            eventDiv.className = 'event-item';

            const time = new Date().toLocaleTimeString();
            eventDiv.innerHTML = `
                <div class="event-time">${time}</div>
                <div class="event-type">${event.type || 'Unknown'}</div>
                <div class="event-data">${JSON.stringify(event.data || {}, null, 2)}</div>
            `;

            container.insertBefore(eventDiv, container.firstChild);

            // Update event count
            const eventCount = container.children.length;
            document.getElementById('stat-events').textContent = eventCount;

            // Keep only last 50 events
            while (container.children.length > 50) {
                container.removeChild(container.lastChild);
            }
            
            // Update game visualizations
            updateGameVisualizations(event);
        }
        
        // Game state tracking
        let gameStateData = {
            players: {},
            currentRound: 0,
            phase: 'waiting',
            timelineEvents: [],
            playerDialogs: [],
            roleActions: {
                werewolf: [],
                seer: [],
                witch: [],
                hunter: []
            }
        };
        
        function updateGameVisualizations(event) {
            try {
                // Process event data for visualization updates
                const eventData = event.data || '';
                const eventType = event.type || 'unknown';

                console.log('[VIZ] updateGameVisualizations called:', { eventType, dataPreview: typeof eventData === 'string' ? eventData.substring(0, 50) : eventData });

                // Extract player information from events
                if (eventType === 'player_action' || eventType === 'game_event') {
                    updatePlayersFromEvent(eventData, eventType);
                }

                // Add to timeline
                addEventToTimeline(eventData, eventType);

                // Process player dialogs - improved detection
                // Support both emoji and [SPEECH] marker for Windows compatibility
                const isPlayerStatement = eventType === 'player_statement' ||
                    eventType === 'player_action' ||  // FIXED: Also check for player_action type from console
                    (typeof eventData === 'string' && (eventData.includes('🗣️') || eventData.includes('[SPEECH]'))) ||
                    (typeof eventData === 'object' && eventData.statement);

                console.log('[VIZ] Is player statement?', isPlayerStatement);

                if (isPlayerStatement) {
                    console.log('[VIZ] Calling addPlayerDialog...');
                    addPlayerDialog(eventData, eventType);
                }

                // Process role-specific actions
                processRoleActions(eventData, eventType);

            } catch (e) {
                console.error('Visualization update error:', e);
            }
        }
        
        function addPlayerDialog(eventData, eventType) {
            try {
                console.log('='.repeat(50));
                console.log('[DEBUG] addPlayerDialog called!');
                console.log('[DEBUG] eventType:', eventType);
                console.log('[DEBUG] eventData:', eventData);
                console.log('='.repeat(50));

                // Extract player ID and statement from event data
                let playerId = null;
                let statement = '';
                let round = gameStateData.currentRound;

                // Handle different event data structures
                if (typeof eventData === 'object' && eventData !== null) {
                    // Structured event object
                    if (eventData.player_id !== undefined) {
                        playerId = String(eventData.player_id);
                    }
                    if (eventData.statement !== undefined) {
                        statement = eventData.statement;
                    } else if (eventData.data !== undefined) {
                        statement = eventData.data;
                    }
                    if (eventData.round !== undefined) {
                        round = eventData.round;
                    }
                } else if (typeof eventData === 'string') {
                    // String event - try to extract from pattern
                    const playerMatch = eventData.match(/Player ([0-9]+):\s*(.*)/);
                    if (playerMatch) {
                        playerId = playerMatch[1];
                        statement = playerMatch[2];
                    } else {
                        const idMatch = eventData.match(/Player ([0-9]+)/);
                        if (idMatch) {
                            playerId = idMatch[1];
                            statement = eventData;
                        }
                    }
                }

                // Clean up statement
                if (statement) {
                    // Remove emoji or [SPEECH] prefix if present
                    statement = statement.replace(/^🗣️\s*/, '').replace(/^\[SPEECH\]\s*/, '').trim();
                }

                // If we couldn't extract needed information, return
                if (!playerId || !statement || statement.length < 5) {
                    console.log('[DEBUG] Dialog rejected:', { playerId, statement, statementLength: statement.length });
                    return;
                }

                console.log('[DEBUG] Dialog accepted:', { playerId, statement: statement.substring(0, 50), round });

                // Create a dialog object
                const dialog = {
                    playerId: playerId,
                    playerRole: gameStateData.players[playerId]?.role || 'unknown',
                    round: round,
                    timestamp: new Date().toLocaleTimeString(),
                    content: statement,
                    type: gameStateData.players[playerId]?.role === 'werewolf' ? 'werewolf' :
                          gameStateData.players[playerId]?.role === 'villager' ? 'villager' : 'special'
                };

                // Add to dialog collection
                gameStateData.playerDialogs.push(dialog);

                // Update the dialog visualization
                refreshAgentDialogs();

            } catch (e) {
                console.error('Dialog processing error:', e);
            }
        }
        
        function processRoleActions(eventData, eventType) {
            try {
                // Process werewolf actions
                if (eventData.includes('狼人') || eventData.includes('Werewolf') || 
                    eventType === 'werewolf_action' || eventData.includes('werewolf')) {
                    const action = {
                        round: gameStateData.currentRound,
                        phase: gameStateData.phase,
                        description: typeof eventData === 'string' ? eventData : JSON.stringify(eventData),
                        timestamp: new Date().toLocaleTimeString()
                    };
                    gameStateData.roleActions.werewolf.push(action);
                    updateRoleActionList('werewolf');
                }
                
                // Process seer actions
                if (eventData.includes('预言家') || eventData.includes('Seer') || 
                    eventType === 'seer_action' || eventData.includes('seer')) {
                    const action = {
                        round: gameStateData.currentRound,
                        phase: gameStateData.phase,
                        description: typeof eventData === 'string' ? eventData : JSON.stringify(eventData),
                        timestamp: new Date().toLocaleTimeString()
                    };
                    gameStateData.roleActions.seer.push(action);
                    updateRoleActionList('seer');
                }
                
                // Process witch actions
                if (eventData.includes('女巫') || eventData.includes('Witch') || 
                    eventType === 'witch_action' || eventData.includes('witch')) {
                    const action = {
                        round: gameStateData.currentRound,
                        phase: gameStateData.phase,
                        description: typeof eventData === 'string' ? eventData : JSON.stringify(eventData),
                        timestamp: new Date().toLocaleTimeString()
                    };
                    gameStateData.roleActions.witch.push(action);
                    updateRoleActionList('witch');
                }
                
                // Process hunter actions
                if (eventData.includes('猎人') || eventData.includes('Hunter') || 
                    eventType === 'hunter_action' || eventData.includes('hunter')) {
                    const action = {
                        round: gameStateData.currentRound,
                        phase: gameStateData.phase,
                        description: typeof eventData === 'string' ? eventData : JSON.stringify(eventData),
                        timestamp: new Date().toLocaleTimeString()
                    };
                    gameStateData.roleActions.hunter.push(action);
                    updateRoleActionList('hunter');
                }
            } catch (e) {
                console.error('Role action processing error:', e);
            }
        }
        
        function updatePlayersFromEvent(eventData, eventType) {
            try {
                console.log('[PLAYER] updatePlayersFromEvent called:', { eventType, eventData: typeof eventData === 'string' ? eventData.substring(0, 100) : eventData });

                // Extract player ID and information from events
                const playerMatch = eventData.match(/Player ([0-9]+)/i);

                console.log('[PLAYER] Regex match result:', playerMatch);

                if (playerMatch) {
                    const playerId = playerMatch[1];
                    console.log('[PLAYER] Extracted player ID:', playerId);

                    // Initialize player if not exists
                    if (!gameStateData.players[playerId]) {
                        console.log('[PLAYER] Creating new player:', playerId);
                        gameStateData.players[playerId] = {
                            id: playerId,
                            name: `Player ${playerId}`,
                            status: 'alive',
                            role: 'unknown',
                            isSheriff: false,
                            statements: 0
                        };
                        console.log('[PLAYER] Player created successfully:', gameStateData.players[playerId]);
                    } else {
                        console.log('[PLAYER] Player already exists:', playerId);
                    }
                    
                    // Update player based on event content
                    if (eventData.includes('死亡') || eventData.includes('淘汰') || 
                        eventData.includes('eliminated') || eventData.includes('killed')) {
                        gameStateData.players[playerId].status = 'dead';
                    }
                    
                    // Track statements
                    if (eventData.includes('🗣️')) {
                        gameStateData.players[playerId].statements++;
                    }
                    
                    // Sheriff detection
                    if (eventData.includes('警长') || eventData.includes('Sheriff')) {
                        gameStateData.players[playerId].isSheriff = true;
                    }
                    
                    // Role detection (simplified)
                    if (eventData.includes('狼人') || eventData.includes('Werewolf')) {
                        gameStateData.players[playerId].role = 'werewolf';
                    } else if (eventData.includes('预言家') || eventData.includes('Seer')) {
                        gameStateData.players[playerId].role = 'seer';
                    } else if (eventData.includes('女巫') || eventData.includes('Witch')) {
                        gameStateData.players[playerId].role = 'witch';
                    } else if (eventData.includes('猎人') || eventData.includes('Hunter')) {
                        gameStateData.players[playerId].role = 'hunter';
                    } else if (eventData.includes('村民') || eventData.includes('Villager')) {
                        gameStateData.players[playerId].role = 'villager';
                    }
                }
                
                // Update round information
                const roundMatch = eventData.match(/Round ([0-9]+)/i);
                if (roundMatch) {
                    gameStateData.currentRound = parseInt(roundMatch[1]);
                }
                
                // Phase detection
                if (eventData.includes('[NIGHT]')) {
                    gameStateData.phase = 'night';
                } else if (eventData.includes('[DAY]')) {
                    gameStateData.phase = 'day';
                } else if (eventData.includes('[VOTE]')) {
                    gameStateData.phase = 'vote';
                }
                
                // Update the player grid visualization
                refreshPlayerGrid();

                console.log('[PLAYER] Total players after update:', Object.keys(gameStateData.players).length);
                console.log('[PLAYER] All player IDs:', Object.keys(gameStateData.players));

            } catch (e) {
                console.error('Player update error:', e);
            }
        }
        
        function refreshPlayerGrid() {
            const playerGrid = document.getElementById('player-grid');
            playerGrid.innerHTML = '';
            
            // Sort players by ID
            const playerIds = Object.keys(gameStateData.players).sort((a, b) => parseInt(a) - parseInt(b));
            
            for (const playerId of playerIds) {
                const player = gameStateData.players[playerId];
                
                const playerCard = document.createElement('div');
                playerCard.className = `player-card ${player.status === 'dead' ? 'dead' : ''}`;
                
                // Add role-based styling
                if (player.role === 'werewolf') {
                    playerCard.classList.add('werewolf');
                } else if (player.role === 'villager') {
                    playerCard.classList.add('villager');
                } else if (player.role !== 'unknown') {
                    playerCard.classList.add('special');
                }
                
                // Add sheriff badge
                if (player.isSheriff) {
                    playerCard.classList.add('sheriff');
                }
                
                // Role emoji
                let roleEmoji = '❓';
                if (player.role === 'werewolf') roleEmoji = '🐺';
                else if (player.role === 'villager') roleEmoji = '👨‍🌾';
                else if (player.role === 'seer') roleEmoji = '👁️';
                else if (player.role === 'witch') roleEmoji = '🧪';
                else if (player.role === 'hunter') roleEmoji = '🏹';
                
                // Status emoji
                const statusEmoji = player.status === 'dead' ? '☠️' : '✅';
                
                // Sheriff badge
                const sheriffBadge = player.isSheriff ? ' 👮' : '';
                
                playerCard.innerHTML = `
                    <div class="player-name">Player ${player.id}${sheriffBadge}</div>
                    <div class="player-role">${roleEmoji} ${player.role !== 'unknown' ? player.role.charAt(0).toUpperCase() + player.role.slice(1) : 'Unknown'}</div>
                    <div class="player-status">${statusEmoji} ${player.status.charAt(0).toUpperCase() + player.status.slice(1)}</div>
                    <div class="player-metrics">
                        发言: ${player.statements}
                    </div>
                `;
                
                playerGrid.appendChild(playerCard);
            }
        }
        
        function addEventToTimeline(eventData, eventType) {
            // Limit timeline events to prevent performance issues
            if (gameStateData.timelineEvents.length >= 20) {
                return;
            }
            
            // Don't add every event to timeline, only significant ones
            let shouldAddToTimeline = false;
            let timelineTitle = '';
            let timelineDesc = '';
            let eventClass = '';
            
            if (eventData.includes('[NIGHT]')) {
                shouldAddToTimeline = true;
                timelineTitle = `夜晚 ${gameStateData.currentRound}`;
                timelineDesc = eventData;
                eventClass = 'night-event';
            } else if (eventData.includes('[DAY]')) {
                shouldAddToTimeline = true;
                timelineTitle = `白天 ${gameStateData.currentRound}`;
                timelineDesc = eventData;
                eventClass = 'day-event';
            } else if (eventData.includes('[VOTE]')) {
                shouldAddToTimeline = true;
                timelineTitle = `投票 ${gameStateData.currentRound}`;
                timelineDesc = eventData;
                eventClass = 'vote-event';
            } else if (eventData.includes('killed') || eventData.includes('淘汰') || 
                     eventData.includes('死亡') || eventData.includes('eliminated')) {
                shouldAddToTimeline = true;
                timelineTitle = '玩家淘汰';
                timelineDesc = eventData;
                eventClass = 'death-event';
            }
            
            if (shouldAddToTimeline) {
                // Add to data store
                gameStateData.timelineEvents.push({
                    title: timelineTitle,
                    desc: timelineDesc,
                    class: eventClass,
                    time: new Date().toLocaleTimeString()
                });
                
                // Refresh timeline
                refreshTimeline();
            }
        }
        
        function refreshTimeline() {
            const timeline = document.getElementById('timeline');
            timeline.innerHTML = '';
            
            // Add events in reverse chronological order
            for (let i = gameStateData.timelineEvents.length - 1; i >= 0; i--) {
                const event = gameStateData.timelineEvents[i];
                
                const eventElement = document.createElement('div');
                eventElement.className = `timeline-event ${event.class}`;
                
                eventElement.innerHTML = `
                    <div class="timeline-dot"></div>
                    <div class="timeline-content">
                        <div class="timeline-title">${event.title}</div>
                        <div class="timeline-desc">${event.desc}</div>
                    </div>
                `;
                
                timeline.appendChild(eventElement);
            }
            
            // If empty, add placeholder
            if (gameStateData.timelineEvents.length === 0) {
                timeline.innerHTML = `
                    <div class="timeline-event">
                        <div class="timeline-dot"></div>
                        <div class="timeline-content">
                            <div class="timeline-title">游戏开始</div>
                            <div class="timeline-desc">等待游戏事件...</div>
                        </div>
                    </div>
                `;
            }
        }
        
        // Keep track of how many dialogues we've displayed
        let displayedDialogCount = 0;
        let typewriterSpeed = 30; // milliseconds per character

        function refreshAgentDialogs() {
            const container = document.getElementById('dialogue-output');

            console.log('*'.repeat(50));
            console.log('[TYPEWRITER] refreshAgentDialogs called!');
            console.log('[TYPEWRITER] Total dialogues:', gameStateData.playerDialogs.length);
            console.log('[TYPEWRITER] Displayed count:', displayedDialogCount);
            console.log('*'.repeat(50));

            // If no dialogues yet
            if (gameStateData.playerDialogs.length === 0) {
                container.innerHTML = '<div style="color: #999;">等待玩家发言...</div>';
                return;
            }

            // Only add NEW dialogues (don't redraw everything)
            if (gameStateData.playerDialogs.length > displayedDialogCount) {
                // Clear "waiting" message on first dialogue
                if (displayedDialogCount === 0 && container.innerHTML.includes('等待玩家发言')) {
                    container.innerHTML = '';
                }

                // Get the new dialogues
                const newDialogs = gameStateData.playerDialogs.slice(displayedDialogCount);

                console.log('[TYPEWRITER] Processing', newDialogs.length, 'new dialogues');

                // Add each new dialogue with character-by-character typewriter effect
                newDialogs.forEach((dialog, index) => {
                    console.log(`[TYPEWRITER] Adding dialogue ${index + 1}:`, dialog.playerId, dialog.content.substring(0, 30));

                    // Get emoji for role
                    let roleEmoji = '❓';
                    if (dialog.playerRole === 'werewolf') roleEmoji = '🐺';
                    else if (dialog.playerRole === 'villager') roleEmoji = '👨‍🌾';
                    else if (dialog.playerRole === 'seer') roleEmoji = '👁️';
                    else if (dialog.playerRole === 'witch') roleEmoji = '🧪';
                    else if (dialog.playerRole === 'hunter') roleEmoji = '🏹';

                    // Get color for role
                    let color = '#667eea';
                    if (dialog.playerRole === 'werewolf') color = '#f44336';
                    else if (dialog.playerRole === 'villager') color = '#4CAF50';
                    else color = '#FF9800';

                    const dialogDiv = document.createElement('div');
                    dialogDiv.style.marginBottom = '15px';
                    dialogDiv.style.paddingBottom = '15px';
                    dialogDiv.style.borderBottom = '1px solid #eee';

                    const contentDiv = document.createElement('div');
                    contentDiv.style.color = '#333';
                    contentDiv.style.lineHeight = '1.6';

                    dialogDiv.innerHTML = `
                        <div style="margin-bottom: 5px;">
                            <span style="font-weight: bold; color: ${color};">${roleEmoji} Player ${dialog.playerId}</span>
                            <span style="color: #999; font-size: 12px; margin-left: 10px;">[Round ${dialog.round}] ${dialog.timestamp}</span>
                        </div>
                    `;

                    dialogDiv.appendChild(contentDiv);

                    // Insert at the top (newest first)
                    container.insertBefore(dialogDiv, container.firstChild);

                    // Typewriter effect - CHARACTER BY CHARACTER (supports Chinese and English)
                    const fullText = dialog.content;
                    let charIndex = 0;

                    console.log(`[TYPEWRITER] Starting typewriter for Player ${dialog.playerId}, length: ${fullText.length} chars`);

                    function showNextChar() {
                        if (charIndex < fullText.length) {
                            contentDiv.textContent += fullText[charIndex];
                            charIndex++;
                            setTimeout(showNextChar, typewriterSpeed);
                        } else {
                            console.log(`[TYPEWRITER] Finished Player ${dialog.playerId}`);
                        }
                    }

                    // Start typing after a brief delay for this dialogue
                    setTimeout(() => {
                        showNextChar();
                    }, index * 200); // Stagger multiple dialogues
                });

                displayedDialogCount = gameStateData.playerDialogs.length;
            }

            console.log('[TYPEWRITER] Display count updated to:', displayedDialogCount);
        }

        // Show player's full dialog history in modal
        function showPlayerHistory(playerId) {
            const player = gameStateData.players[playerId];
            const playerDialogs = gameStateData.playerDialogs.filter(d => d.playerId === playerId);

            // Update modal title
            document.getElementById('modal-player-title').textContent =
                `Player ${playerId} ${player ? '(' + player.role + ')' : ''} - Dialog History`;

            // Populate dialog history
            const historyList = document.getElementById('dialog-history-list');
            historyList.innerHTML = '';

            if (playerDialogs.length === 0) {
                historyList.innerHTML = '<p style="text-align: center; color: #999;">该玩家尚未发言</p>';
            } else {
                // Show in chronological order (oldest first)
                playerDialogs.forEach(dialog => {
                    const item = document.createElement('div');
                    item.className = `dialog-history-item ${dialog.type}`;
                    item.innerHTML = `
                        <div class="dialog-history-meta">
                            Round ${dialog.round} - ${dialog.timestamp}
                        </div>
                        <div class="dialog-history-content">${dialog.content}</div>
                    `;
                    historyList.appendChild(item);
                });
            }

            // Show modal
            document.getElementById('dialog-modal').classList.add('active');
        }

        // Close dialog modal
        function closeDialogModal() {
            document.getElementById('dialog-modal').classList.remove('active');
        }

        // Close modal when clicking outside
        document.addEventListener('click', function(e) {
            const modal = document.getElementById('dialog-modal');
            if (e.target === modal) {
                closeDialogModal();
            }
        });
        
        function updateRoleActionList(role) {
            const actionList = document.getElementById(`${role}-action-list`);
            if (!actionList) return;
            
            // Clear current list
            actionList.innerHTML = '';
            
            // Get actions for this role
            const actions = gameStateData.roleActions[role];
            
            // Display actions in reverse chronological order
            for (let i = actions.length - 1; i >= 0; i--) {
                const action = actions[i];
                
                const actionElement = document.createElement('div');
                actionElement.className = 'role-action-item';
                actionElement.textContent = `[R${action.round}] ${action.description}`;
                
                actionList.appendChild(actionElement);
            }
            
            // If empty, add placeholder
            if (actions.length === 0) {
                actionList.innerHTML = `<div class="role-action-item">等待${getRoleNameChinese(role)}行动...</div>`;
            }
        }
        
        function getRoleNameChinese(role) {
            switch(role) {
                case 'werewolf': return '狼人';
                case 'seer': return '预言家';
                case 'witch': return '女巫';
                case 'hunter': return '猎人';
                default: return role;
            }
        }

        function startEventStream() {
            if (eventSource) eventSource.close();

            eventSource = new EventSource('/api/stream');

            eventSource.onmessage = function(event) {
                const data = JSON.parse(event.data);

                if (data.type === 'output') {
                    appendToConsole(data.content);
                    
                    // Try to extract game information from console output
                    const content = data.content;
                    
                    // Process important console output for enhanced visualizations
                    if (content.includes('Player') || content.includes('玩家') ||
                        content.includes('Round') || content.includes('回合') ||
                        content.includes('Night') || content.includes('Day') ||
                        content.includes('Vote') || content.includes('投票')) {

                        console.log('[CONSOLE] Processing line:', content.substring(0, 100));

                        // Create a pseudo-event for visualization
                        const pseudoEvent = {
                            type: content.includes('死亡') || content.includes('淘汰') ? 'vote_result' :
                                  content.includes('发言') || content.includes('陈述') || content.includes('🗣️') || content.includes('[SPEECH]') ? 'player_action' : 'game_event',
                            data: content
                        };

                        console.log('[CONSOLE] Created pseudo-event:', pseudoEvent.type);

                        // Update visualizations with this console output
                        updateGameVisualizations(pseudoEvent);
                    }
                } else if (data.type === 'event') {
                    addEvent(data);

                    // Update stats based on event
                    if (data.round) {
                        document.getElementById('stat-round').textContent = data.round;
                        gameStateData.currentRound = data.round;
                    }
                    if (data.alive_players !== undefined) {
                        document.getElementById('stat-alive').textContent = data.alive_players;
                    }

                    // IMPORTANT: Also update visualizations for structured events
                    updateGameVisualizations(data);
                } else if (data.type === 'status') {
                    updateStatus(data.status);
                    if (data.status === 'completed' || data.status === 'error') {
                        stopDurationTimer();
                    }
                }
            };

            eventSource.onerror = function(error) {
                console.error('EventStream error:', error);
                eventSource.close();
            };
        }

        function stopEventStream() {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
        }

        function startDurationTimer() {
            stopDurationTimer();
            durationTimer = setInterval(() => {
                if (startTime) {
                    const elapsed = Math.floor((Date.now() - startTime) / 1000);
                    const minutes = Math.floor(elapsed / 60);
                    const seconds = elapsed % 60;
                    document.getElementById('stat-duration').textContent =
                        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
                }
            }, 1000);
        }

        function stopDurationTimer() {
            if (durationTimer) {
                clearInterval(durationTimer);
                durationTimer = null;
            }
        }

        function exportResults() {
            window.open('/api/export', '_blank');
        }

        // Poll for status updates
        setInterval(() => {
            if (gameStatus === 'running') {
                fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    if (data.status !== gameStatus) {
                        updateStatus(data.status);
                    }
                });
            }
        }, 2000);
        
        // Initialize event handlers when page loads
        window.addEventListener('load', function() {
            console.log('[INIT] Page loaded! 2-player dialogue view ready.');
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/start', methods=['POST'])
def start_game():
    """Start the werewolf game"""
    global game_process, game_thread, game_status, game_output, game_events

    if game_status == "running":
        return jsonify({"status": "error", "message": "Game already running"})

    try:
        config = request.json or {}
        api_endpoint = config.get('api_endpoint', 'http://localhost:8080')
        model = config.get('model', '/home/apulis-dev/userdata/Llama-3.3-70B-Instruct')

        # Reset state
        game_output = []
        game_events = []
        game_status = "running"

        # Create a Python script to run the game
        game_script = f'''
import sys
sys.path.insert(0, r"{os.path.dirname(os.path.abspath(__file__))}")
from werewolf_game import WerewolfGame
import json

llm_config = {{
    'api_base': '{api_endpoint}',
    'model': '{model}',
    'temperature': 0.7,
    'max_tokens': 500
}}

print("[SYSTEM] Starting Werewolf Game")
print("[CONFIG] API: {0}".format(llm_config['api_base']))
print("[CONFIG] Model: {0}".format(llm_config['model']))
print("="*70)

try:
    # 直接使用用户指定的模型
    print("[CONFIG] 使用模型: {0}".format(llm_config['model']))
    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    results = game.play_game()
    
    print("\\n[SYSTEM] Game completed successfully")
    print("[RESULT] Winner: " + results['game_summary']['winner'])
    print("[RESULT] Rounds: " + str(results['game_summary']['total_rounds']))

    # Save results
    with open('last_game_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

except Exception as e:
    print("[ERROR] Game failed: " + str(e))
    import traceback
    traceback.print_exc()
'''

        # Write the script to a temporary file
        with open('temp_game_runner.py', 'w', encoding='utf-8') as f:
            f.write(game_script)

        # Start the game in a subprocess
        def run_game():
            global game_process, game_status, game_output

            try:
                game_process = subprocess.Popen(
                    [sys.executable, 'temp_game_runner.py'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                # Track game state for visualization
                current_round = 0
                alive_players = 13
                player_roles = {}
                
                # Import for regex
                import re
                
                # Read output line by line
                if game_process and game_process.stdout:
                    for line in game_process.stdout:
                        game_output.append(line)
                        output_queue.put(('output', line))
                        
                        # Enhanced event parsing for better visualizations
                        
                        # Round detection
                        round_match = None
                        if "Round" in line:
                            import re
                            round_match = re.search(r"Round (\d+)", line)
                            if round_match:
                                current_round = int(round_match.group(1))
                                output_queue.put(('event', {
                                    'type': 'round_update',
                                    'data': line.strip(),
                                    'round': current_round
                                }))
                        
                        # Player elimination detection
                        if "killed" in line or "eliminated" in line or "died" in line or "死亡" in line or "淘汰" in line:
                            if alive_players > 0:
                                alive_players -= 1
                            output_queue.put(('event', {
                                'type': 'player_eliminated',
                                'data': line.strip(),
                                'alive_players': alive_players,
                                'round': current_round
                            }))
                        
                        # Game phase detection
                        if '[SHERIFF]' in line:
                            output_queue.put(('event', {
                                'type': 'sheriff_election', 
                                'data': line.strip(),
                                'round': current_round
                            }))
                        elif '[VOTE]' in line:
                            output_queue.put(('event', {
                                'type': 'voting_phase', 
                                'data': line.strip(),
                                'round': current_round
                            }))
                        elif '[NIGHT]' in line:
                            output_queue.put(('event', {
                                'type': 'night_phase', 
                                'data': line.strip(),
                                'round': current_round
                            }))
                        elif '[DAY]' in line:
                            output_queue.put(('event', {
                                'type': 'day_phase', 
                                'data': line.strip(),
                                'round': current_round
                            }))
                        
                        # Player actions detection - Enhanced dialog capture
                        # Support both emoji and [SPEECH] marker for Windows compatibility
                        if '🗣️' in line or '[SPEECH]' in line:
                            # Extract player ID and statement
                            player_id = None
                            statement = line.strip()
                            player_match = re.search(r"Player ([0-9]+):\s*(.*)", line)
                            if player_match:
                                player_id = player_match.group(1)
                                statement = player_match.group(2)

                            output_queue.put(('event', {
                                'type': 'player_statement',
                                'data': statement,
                                'player_id': player_id,
                                'statement': statement,
                                'round': current_round
                            }))
                        elif 'statement' in line.lower() or ('Player' in line and ':' in line and not any(x in line for x in ['[NIGHT]', '[DAY]', '[VOTE]', '[WOLF]', '[SEER]', '🗳️', '❌', '☠️'])):
                            # Backup pattern for statements without marker
                            player_id = None
                            statement = line.strip()
                            player_match = re.search(r"Player ([0-9]+):\s*(.*)", line)
                            if player_match:
                                player_id = player_match.group(1)
                                statement = player_match.group(2)

                            output_queue.put(('event', {
                                'type': 'player_statement',
                                'data': statement,
                                'player_id': player_id,
                                'statement': statement,
                                'round': current_round
                            }))
                        elif '👤' in line:
                            # 尝试提取玩家ID
                            player_id = None
                            player_match = re.search(r"Player ([0-9]+)", line)
                            if player_match:
                                player_id = player_match.group(1)

                            output_queue.put(('event', {
                                'type': 'player_action',
                                'data': line.strip(),
                                'player_id': player_id,
                                'round': current_round
                            }))
                            
                        # Vote and results detection
                        if '🗳️' in line:
                            output_queue.put(('event', {
                                'type': 'vote_cast', 
                                'data': line.strip(),
                                'round': current_round
                            }))
                        elif '❌' in line or '☠️' in line:
                            output_queue.put(('event', {
                                'type': 'vote_result', 
                                'data': line.strip(),
                                'round': current_round,
                                'alive_players': alive_players
                            }))
                        
                        # 捕获特定角色动作
                        if '狼人' in line or 'Werewolf' in line or 'werewolf' in line:
                            output_queue.put(('event', {
                                'type': 'werewolf_action', 
                                'data': line.strip(),
                                'round': current_round
                            }))
                            
                        if '预言家' in line or 'Seer' in line or 'seer' in line:
                            output_queue.put(('event', {
                                'type': 'seer_action', 
                                'data': line.strip(),
                                'round': current_round
                            }))
                            
                        if '女巫' in line or 'Witch' in line or 'witch' in line:
                            output_queue.put(('event', {
                                'type': 'witch_action', 
                                'data': line.strip(),
                                'round': current_round
                            }))
                            
                        if '猎人' in line or 'Hunter' in line or 'hunter' in line:
                            output_queue.put(('event', {
                                'type': 'hunter_action', 
                                'data': line.strip(),
                                'round': current_round
                            }))
                            
                        # Role revelation detection
                        role_patterns = [
                            (r"Player ([0-9]+).*?狼人", "werewolf"), 
                            (r"Player ([0-9]+).*?Werewolf", "werewolf"),
                            (r"Player ([0-9]+).*?村民", "villager"), 
                            (r"Player ([0-9]+).*?Villager", "villager"),
                            (r"Player ([0-9]+).*?预言家", "seer"), 
                            (r"Player ([0-9]+).*?Seer", "seer"),
                            (r"Player ([0-9]+).*?女巫", "witch"), 
                            (r"Player ([0-9]+).*?Witch", "witch"),
                            (r"Player ([0-9]+).*?猎人", "hunter"), 
                            (r"Player ([0-9]+).*?Hunter", "hunter"),
                        ]
                        
                        import re
                        for pattern, role in role_patterns:
                            role_match = re.search(pattern, line)
                            if role_match:
                                player_id = role_match.group(1)
                                player_roles[player_id] = role
                                output_queue.put(('event', {
                                    'type': 'role_reveal', 
                                    'data': line.strip(),
                                    'player_id': player_id,
                                    'role': role
                                }))
                
                # Wait for process to complete
                game_process.wait()

                if game_process.returncode == 0:
                    game_status = "completed"
                    output_queue.put(('status', 'completed'))
                else:
                    game_status = "error"
                    output_queue.put(('status', 'error'))

            except Exception as e:
                game_status = "error"
                output_queue.put(('output', f"[ERROR] {str(e)}\n"))
                output_queue.put(('status', 'error'))

        game_thread = threading.Thread(target=run_game, daemon=True)
        game_thread.start()

        return jsonify({"status": "started", "message": "Game started successfully"})

    except Exception as e:
        game_status = "error"
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/stop', methods=['POST'])
def stop_game():
    """Stop the running game"""
    global game_process, game_status

    if game_process and game_process.poll() is None:
        game_process.terminate()
        game_status = "idle"
        return jsonify({"status": "stopped"})

    return jsonify({"status": "not_running"})

@app.route('/api/status')
def get_status():
    """Get current game status"""
    global game_status
    return jsonify({"status": game_status})

@app.route('/api/stream')
def stream_events():
    """Server-sent events stream for real-time updates"""
    def generate():
        while True:
            try:
                # Get item from queue with timeout
                item_type, data = output_queue.get(timeout=1)

                if item_type == 'output':
                    yield f'data: {json.dumps({"type": "output", "content": data})}\n\n'
                elif item_type == 'event':
                    yield f'data: {json.dumps({"type": "event", **data})}\n\n'
                elif item_type == 'status':
                    yield f'data: {json.dumps({"type": "status", "status": data})}\n\n'

            except queue.Empty:
                # Send heartbeat
                yield f'data: {json.dumps({"type": "heartbeat"})}\n\n'

            except Exception as e:
                print(f"Stream error: {e}")
                break

    return app.response_class(generate(), mimetype='text/event-stream')

@app.route('/api/export')
def export_results():
    """Export game results"""
    try:
        if os.path.exists('last_game_results.json'):
            with open('last_game_results.json', 'r', encoding='utf-8') as f:
                results = json.load(f)

            response = app.response_class(
                json.dumps(results, indent=2, ensure_ascii=False),
                mimetype='application/json',
                headers={'Content-Disposition': 'attachment; filename=game_results.json'}
            )
            return response
        else:
            return jsonify({"error": "No results available"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def main():
    """Run the integrated web UI"""
    print("="*70)
    print("WEREWOLF GAME - INTEGRATED WEB UI")
    print("="*70)
    print("\n[INFO] Starting web server...")
    print("[INFO] Open your browser and go to: http://localhost:5000")
    print("[INFO] Use the web interface to start and control the game")
    print("\n[FEATURES]")
    print("  - Click 'Start Game' to begin")
    print("  - View real-time console output")
    print("  - Monitor game events as they happen")
    print("  - Export results when game completes")
    print("\n[NOTE] Ensure your LLM API server is running before starting the game")
    print("="*70)

    # Try to find available port
    import socket
    port = 5000
    for attempt_port in range(5000, 5010):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', attempt_port))
                s.close()
                port = attempt_port
                break
        except:
            continue

    print(f"\n[INFO] Starting on port: {port}")
    print(f"[INFO] Open: http://localhost:{port}")

    # Run Flask app
    app.run(debug=False, host='127.0.0.1', port=port)

if __name__ == '__main__':
    main()