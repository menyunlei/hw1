"""
Web UI for Werewolf Game Analysis - Modified Version
交互式Web界面展示对抗细节和性能分析
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
performance_data = {}


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
    return jsonify({
        "total_rounds": game_data.get("total_rounds", 0),
        "winner": game_data.get("winner", "Unknown"),
        "players": game_data.get("players", []),
        "game_date": game_data.get("date", "Unknown")
    })


def load_game_data(game_report_path, performance_report_path=None):
    """Load game data from JSON file"""
    global game_data, performance_data
    
    try:
        with open(game_report_path, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
        print(f"✓ Loaded game data from {game_report_path}")
        
        if performance_report_path:
            try:
                with open(performance_report_path, 'r', encoding='utf-8') as f:
                    performance_data = json.load(f)
                print(f"✓ Loaded performance data from {performance_report_path}")
            except Exception as e:
                print(f"✗ Error loading performance data: {e}")
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


def run_dashboard(game_report, performance_report=None, start_port=8000):
    """Run the dashboard"""
    port = find_available_port(start_port)
    
    # Add template folder if not exists (for standalone script)
    template_dir = Path(__file__).parent / 'templates'
    if not template_dir.exists():
        template_dir.mkdir(exist_ok=True)
        
        # Create a basic dashboard.html template if it doesn't exist
        dashboard_html = template_dir / 'dashboard.html'
        if not dashboard_html.exists():
            with open(dashboard_html, 'w', encoding='utf-8') as f:
                f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Werewolf Game Analysis</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #333; }
        .card { background: #f9f9f9; border-radius: 5px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        <h1>Werewolf Game Analysis</h1>
        
        <div class="card">
            <h2>Game Summary</h2>
            <div id="gameSummary">Loading...</div>
        </div>

        <!-- More sections would be added here -->
    </div>

    <script>
        // Fetch game summary data
        fetch('/api/game_summary')
            .then(response => response.json())
            .then(data => {
                const summaryEl = document.getElementById('gameSummary');
                if (data.error) {
                    summaryEl.innerHTML = `<p>Error: ${data.error}</p>`;
                } else {
                    summaryEl.innerHTML = `
                        <p><strong>Date:</strong> ${data.game_date}</p>
                        <p><strong>Total Rounds:</strong> ${data.total_rounds}</p>
                        <p><strong>Winner:</strong> ${data.winner}</p>
                    `;
                }
            })
            .catch(error => {
                document.getElementById('gameSummary').innerHTML = `<p>Error loading data: ${error}</p>`;
            });
    </script>
</body>
</html>
                """)
    
    # Add static folder if not exists
    static_dir = Path(__file__).parent / 'static'
    if not static_dir.exists():
        static_dir.mkdir(exist_ok=True)
    
    # Load game data
    load_game_data(game_report, performance_report)

    print("\n======================================================================")
    print("Starting Werewolf Game Analysis Dashboard")
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
        print("Usage: python web_ui.py <game_report.json> [performance_report.json] [start_port]")
        sys.exit(1)

    game_report = sys.argv[1]
    perf_report = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2].endswith('.json') else None
    start_port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000

    run_dashboard(game_report, perf_report, start_port)