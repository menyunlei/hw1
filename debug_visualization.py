"""
Debug script to trace dialog visualization issues
"""

import sys
import io

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import re

print("="*70)
print("DIALOG VISUALIZATION DEBUG SCRIPT")
print("="*70)
print()

# Simulate game output
simulated_outputs = [
    "[DAY] Day 1 - Discussion",
    "  [SPEECH] Player 0: I think Player 3 is acting suspicious",
    "  [SPEECH] Player 1: We should trust the seer",
    "  [SPEECH] Player 3: I am the real seer, I checked Player 5",
    "[VOTE] Day 1 - Voting",
    "  Player 0 votes for Player 3",
]

print("Step 1: Simulated Game Output")
print("-"*70)
for line in simulated_outputs:
    print(line)
print()

# Test event detection
print("Step 2: Event Detection Test")
print("-"*70)

def detect_player_statement(line):
    """Detect if line contains a player statement"""
    # Check for markers
    if '[SPEECH]' in line or ('Player' in line and ':' in line):
        # Try to extract
        player_match = re.search(r"Player ([0-9]+):\s*(.*)", line)
        if player_match:
            player_id = player_match.group(1)
            statement = player_match.group(2)
            return {
                'detected': True,
                'player_id': player_id,
                'statement': statement,
                'marker': '[SPEECH]' if '[SPEECH]' in line else 'None'
            }
    return {'detected': False}

for line in simulated_outputs:
    result = detect_player_statement(line)
    if result['detected']:
        print(f"DETECTED: Player {result['player_id']}")
        print(f"  Statement: {result['statement']}")
        print(f"  Marker: {result['marker']}")
    else:
        print(f"SKIPPED: {line}")
    print()

# Test the actual integrated_web_ui.py logic
print("Step 3: Web UI Event Queue Simulation")
print("-"*70)

events = []
current_round = 1

for line in simulated_outputs:
    # Simulate the actual logic from integrated_web_ui.py
    if '[SPEECH]' in line:
        player_match = re.search(r"Player ([0-9]+):\s*(.*)", line)
        if player_match:
            player_id = player_match.group(1)
            statement = player_match.group(2)

            event = {
                'type': 'player_statement',
                'data': statement,
                'player_id': player_id,
                'statement': statement,
                'round': current_round
            }
            events.append(event)
            print(f"Event created: player_statement")
            print(f"  Player ID: {player_id}")
            print(f"  Statement: {statement}")
            print(f"  Round: {current_round}")
            print()

print(f"Total events created: {len(events)}")
print()

# Test JavaScript-side processing
print("Step 4: Frontend Processing Simulation")
print("-"*70)

dialogs = []

for event in events:
    event_type = event.get('type')
    event_data = event.get('data')

    # Simulate addPlayerDialog logic
    player_id = None
    statement = ''
    round_num = event.get('round', 0)

    if isinstance(event_data, dict):
        player_id = str(event_data.get('player_id', ''))
        statement = event_data.get('statement', '')
    elif isinstance(event_data, str):
        statement = event_data
        player_id = event.get('player_id', '')

    # Clean up statement
    statement = statement.replace('[SPEECH]', '').strip()

    if player_id and statement and len(statement) >= 5:
        dialog = {
            'playerId': player_id,
            'round': round_num,
            'content': statement,
            'valid': True
        }
        dialogs.append(dialog)
        print(f"Dialog created:")
        print(f"  Player ID: {dialog['playerId']}")
        print(f"  Round: {dialog['round']}")
        print(f"  Content: {dialog['content'][:50]}...")
        print()
    else:
        print(f"Dialog rejected:")
        print(f"  Player ID: {player_id}")
        print(f"  Statement length: {len(statement)}")
        print()

print(f"Total dialogs created: {len(dialogs)}")
print()

# Summary
print("="*70)
print("SUMMARY")
print("="*70)
print(f"Game output lines: {len(simulated_outputs)}")
print(f"Player statements detected: {len(events)}")
print(f"Frontend dialogs created: {len(dialogs)}")
print()

if len(dialogs) > 0:
    print("[SUCCESS] Dialog visualization pipeline is working!")
    print()
    print("If you still don't see dialogs in the Web UI:")
    print("1. Check browser console (F12) for JavaScript errors")
    print("2. Verify the 'Player Interactions' panel exists")
    print("3. Check if Server-Sent Events are working")
    print("4. Look for 'player_statement' events in Network tab")
else:
    print("[ERROR] No dialogs were created!")
    print("The visualization pipeline has issues.")

print()
print("="*70)
print("NEXT STEPS")
print("="*70)
print()
print("1. Run the actual game and check console output for [SPEECH] markers")
print("2. Open browser DevTools (F12) -> Console tab")
print("3. Check for JavaScript errors")
print("4. Go to Network tab -> Filter by 'stream'")
print("5. Click on the stream connection")
print("6. Check if 'player_statement' events are being sent")
print()
print("If events are being sent but not displayed:")
print("- Check the refreshAgentDialogs() function is being called")
print("- Verify gameStateData.playerDialogs array is being updated")
print("- Check if dialog filter is hiding the dialogs")
print()
