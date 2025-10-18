"""
Enhanced Web UI for Werewolf Game Analysis
交互式Web界面展示对抗细节和游戏数据
"""

import json
import socket
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, jsonify, send_from_directory
import webbrowser
from threading import Timer
import os

app = Flask(__name__)

# Global storage for game data
game_data = {}

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('dashboard.html')

@app.route('/api/game_summary')
def game_summary():
    """API endpoint for game summary"""
    if not game_data:
        return jsonify({"error": "No game data loaded"})
    
    # Extract summary data from game_data
    summary = game_data.get("game_summary", {})
    
    return jsonify({
        "game_id": game_data.get("game_id", "Unknown"),
        "timestamp": game_data.get("timestamp", "Unknown"),
        "total_rounds": summary.get("total_rounds", 0),
        "winner": summary.get("winner", "Unknown"),
        "final_nash_score": summary.get("final_nash_score", 0),
        "final_werewolf_advantage": summary.get("final_werewolf_advantage", 0),
        "start_time": summary.get("start_time", "Unknown"),
        "end_time": summary.get("end_time", "Unknown")
    })

@app.route('/api/players')
def players():
    """API endpoint for player data"""
    if not game_data:
        return jsonify({"error": "No game data loaded"})
    
    player_metrics = game_data.get("player_metrics", {})
    players_data = {}
    
    for player_id, data in player_metrics.items():
        players_data[player_id] = {
            "role": data.get("role", "Unknown"),
            "final_status": data.get("final_status", "Unknown"),
            "metrics": data.get("metrics", {})
        }
    
    return jsonify(players_data)

@app.route('/api/rounds')
def rounds():
    """API endpoint for round data"""
    if not game_data:
        return jsonify({"error": "No game data loaded"})
    
    return jsonify(game_data.get("rounds", {}))

def load_game_data(game_report_path):
    """Load game data from JSON file"""
    global game_data
    
    try:
        with open(game_report_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        print(f"✓ Loaded game data from {game_report_path}")
    except Exception as e:
        print(f"✗ Error loading game data: {e}")
        raise

def open_browser(host='localhost', port=5000):
    """Open browser to dashboard"""
    webbrowser.open(f'http://{host}:{port}/')

def find_available_port(start_port=8000, max_attempts=20):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("localhost", port))
                print(f"Found available port: {port}")
                return port
            except socket.error:
                print(f"Port {port} is in use, trying next port...")
    
    # If we reach here, no ports were available
    raise RuntimeError(f"Could not find an available port after {max_attempts} attempts")

def create_template():
    """Create the dashboard HTML template"""
    template_dir = Path(__file__).parent / 'templates'
    template_dir.mkdir(exist_ok=True)
    
    dashboard_html = template_dir / 'dashboard.html'
    with open(dashboard_html, 'w', encoding='utf-8') as f:
        f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Werewolf Game Analysis</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background-color: #f5f5f5;
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
        }
        h1, h2, h3 { 
            color: #333; 
        }
        .card { 
            background: #ffffff; 
            border-radius: 8px; 
            padding: 20px; 
            margin-bottom: 20px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }
        .player-card {
            border-left: 5px solid #ccc;
            margin-bottom: 15px;
            padding: 15px;
            background: #f9f9f9;
        }
        .werewolf { border-left-color: #ff5252; }
        .villager { border-left-color: #4caf50; }
        .witch { border-left-color: #9c27b0; }
        .seer { border-left-color: #2196f3; }
        .hunter { border-left-color: #ff9800; }
        
        .status-alive { color: #4caf50; font-weight: bold; }
        .status-dead { color: #f44336; font-weight: bold; }
        
        .metrics-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        .metrics-table th {
            background: #f2f2f2;
            text-align: left;
            padding: 8px;
        }
        .metrics-table td {
            border-top: 1px solid #eee;
            padding: 8px;
        }
        
        .winner-villagers { color: #4caf50; font-weight: bold; }
        .winner-werewolves { color: #f44336; font-weight: bold; }
        
        .header-section {
            background-color: #3f51b5;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .header-section h1 {
            color: white;
            margin: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-section">
            <h1>Werewolf Game Analysis</h1>
            <p>Interactive dashboard for analyzing game outcomes and player metrics</p>
        </div>
        
        <div class="card">
            <h2>Game Summary</h2>
            <div id="gameSummary">Loading...</div>
        </div>
        
        <div class="card">
            <h2>Player Analysis</h2>
            <div id="playerAnalysis">Loading...</div>
        </div>
        
        <div class="card">
            <h2>Game Timeline</h2>
            <div id="gameTimeline">
                <p>Round data not available in this version. Check the full game report for details.</p>
            </div>
        </div>
    </div>

    <script>
        // Format date-time strings
        function formatDateTime(dateTimeStr) {
            if (!dateTimeStr || dateTimeStr === 'Unknown') return 'Unknown';
            const date = new Date(dateTimeStr);
            return date.toLocaleString();
        }
        
        // Load game summary
        fetch('/api/game_summary')
            .then(response => response.json())
            .then(data => {
                const summaryEl = document.getElementById('gameSummary');
                if (data.error) {
                    summaryEl.innerHTML = `<p>Error: ${data.error}</p>`;
                } else {
                    const winnerClass = data.winner === 'villagers' ? 'winner-villagers' : 'winner-werewolves';
                    summaryEl.innerHTML = `
                        <p><strong>Game ID:</strong> ${data.game_id}</p>
                        <p><strong>Start Time:</strong> ${formatDateTime(data.start_time)}</p>
                        <p><strong>End Time:</strong> ${formatDateTime(data.end_time)}</p>
                        <p><strong>Total Rounds:</strong> ${data.total_rounds}</p>
                        <p><strong>Winner:</strong> <span class="${winnerClass}">${data.winner.toUpperCase()}</span></p>
                        <p><strong>Nash Equilibrium Score:</strong> ${parseFloat(data.final_nash_score).toFixed(2)}</p>
                        <p><strong>Werewolf Advantage:</strong> ${parseFloat(data.final_werewolf_advantage).toFixed(2)}</p>
                    `;
                }
            })
            .catch(error => {
                document.getElementById('gameSummary').innerHTML = `<p>Error loading game summary: ${error}</p>`;
            });
        
        // Load player data
        fetch('/api/players')
            .then(response => response.json())
            .then(data => {
                const playerEl = document.getElementById('playerAnalysis');
                if (data.error) {
                    playerEl.innerHTML = `<p>Error: ${data.error}</p>`;
                } else {
                    let playersHtml = '';
                    
                    Object.entries(data).forEach(([playerId, playerData]) => {
                        const roleClass = playerData.role.toLowerCase();
                        const statusClass = playerData.final_status === 'alive' ? 'status-alive' : 'status-dead';
                        const metrics = playerData.metrics;
                        
                        playersHtml += `
                            <div class="player-card ${roleClass}">
                                <h3>Player ${playerId} - ${playerData.role.toUpperCase()}</h3>
                                <p>Status: <span class="${statusClass}">${playerData.final_status.toUpperCase()}</span></p>
                                <p>Outcome: ${metrics.final_outcome === 'won' ? '🏆 Won' : '❌ Lost'}</p>
                                
                                <h4>Performance Metrics</h4>
                                <table class="metrics-table">
                                    <tr>
                                        <th>Metric</th>
                                        <th>Value</th>
                                    </tr>
                                    <tr>
                                        <td>Rounds Survived</td>
                                        <td>${metrics.rounds_survived}</td>
                                    </tr>
                                    <tr>
                                        <td>Total Statements</td>
                                        <td>${metrics.total_statements}</td>
                                    </tr>
                                    <tr>
                                        <td>Avg Statement Length</td>
                                        <td>${parseFloat(metrics.avg_statement_length).toFixed(1)}</td>
                                    </tr>
                                    <tr>
                                        <td>Deception Attempts</td>
                                        <td>${metrics.deception_attempts}</td>
                                    </tr>
                                    <tr>
                                        <td>Successful Deceptions</td>
                                        <td>${metrics.successful_deceptions}</td>
                                    </tr>
                                    <tr>
                                        <td>Consistency Score</td>
                                        <td>${parseFloat(metrics.consistency_score).toFixed(2)}</td>
                                    </tr>
                                    <tr>
                                        <td>Team Alignment Score</td>
                                        <td>${parseFloat(metrics.team_alignment_score).toFixed(2)}</td>
                                    </tr>
                                    <tr>
                                        <td>Optimal Vote Ratio</td>
                                        <td>${parseFloat(metrics.optimal_vote_ratio).toFixed(2)}</td>
                                    </tr>
                                </table>
                            </div>
                        `;
                    });
                    
                    playerEl.innerHTML = playersHtml;
                }
            })
            .catch(error => {
                document.getElementById('playerAnalysis').innerHTML = `<p>Error loading player data: ${error}</p>`;
            });
    </script>
</body>
</html>
        """)
    
    print(f"✓ Created dashboard template at {dashboard_html}")

def run_dashboard(game_report, start_port=8000):
    """Run the dashboard"""
    port = find_available_port(start_port)
    
    # Create the template
    create_template()
    
    # Load game data
    load_game_data(game_report)

    print("\n======================================================================")
    print("Starting Enhanced Werewolf Game Analysis Dashboard")
    print("======================================================================")
    print(f"\nDashboard will be available at: http://localhost:{port}/")
    print("Press Ctrl+C to stop the server\n")

    # Open browser after 1 second
    Timer(1, lambda: open_browser(host='localhost', port=port)).start()

    # Run Flask app
    app.run(host='localhost', debug=False, port=port)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python enhanced_web_ui.py <game_report.json> [performance_report.json] [start_port]")
        sys.exit(1)

    game_report = sys.argv[1]
    
    # Check if second argument is a JSON file or a port number
    if len(sys.argv) > 2:
        if sys.argv[2].endswith('.json'):
            # It's a JSON file, so this is performance report
            perf_report = sys.argv[2]
            start_port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
        else:
            # It's likely a port number
            perf_report = None
            try:
                start_port = int(sys.argv[2])
            except ValueError:
                print("Error: Second argument must be either a JSON file or a port number")
                sys.exit(1)
    else:
        perf_report = None
        start_port = 8000

    run_dashboard(game_report, start_port)