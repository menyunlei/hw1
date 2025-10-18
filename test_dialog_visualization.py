"""
Test script to verify dialog visualization improvements
"""

import json
import re
import sys
import io

# Fix Windows encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Test event patterns
test_events = [
    {
        'type': 'player_statement',
        'data': {
            'player_id': 1,
            'statement': 'I believe Player 3 is a werewolf based on their behavior.',
            'round': 1
        }
    },
    {
        'type': 'console_output',
        'data': '  🗣️ Player 2: I am the seer and I checked Player 5 last night. They are innocent!'
    },
    {
        'type': 'console_output',
        'data': '  🗣️ Player 4: As a villager, I think we should trust Player 2.'
    },
    {
        'type': 'player_statement',
        'data': 'Player 6: This is highly suspicious. I vote to eliminate Player 3.',
        'player_id': 6,
        'round': 1
    }
]

def extract_dialog_info(event):
    """Extract dialog information from event"""
    event_type = event.get('type', 'unknown')
    event_data = event.get('data', '')

    player_id = None
    statement = ''
    round_num = 0

    # Handle different event data structures
    if isinstance(event_data, dict):
        # Structured event object
        if 'player_id' in event_data:
            player_id = str(event_data['player_id'])
        if 'statement' in event_data:
            statement = event_data['statement']
        elif 'data' in event_data:
            statement = event_data['data']
        if 'round' in event_data:
            round_num = event_data['round']
    elif isinstance(event_data, str):
        # String event - try to extract from pattern
        player_match = re.search(r"Player ([0-9]+):\s*(.*)", event_data)
        if player_match:
            player_id = player_match[1]
            statement = player_match[2]
        else:
            id_match = re.search(r"Player ([0-9]+)", event_data)
            if id_match:
                player_id = id_match[1]
                statement = event_data

    # Clean up statement
    if statement:
        # Remove emoji prefix if present
        statement = re.sub(r'^🗣️\s*', '', statement).strip()

    return {
        'player_id': player_id,
        'statement': statement,
        'round': round_num,
        'valid': bool(player_id and statement and len(statement) >= 5)
    }

# Test the extraction logic
print("="*70)
print("TESTING DIALOG EXTRACTION LOGIC")
print("="*70)
print()

for i, event in enumerate(test_events, 1):
    print(f"Test Event {i}:")
    print(f"  Type: {event['type']}")
    print(f"  Data: {json.dumps(event['data'], indent=4)}")
    print()

    result = extract_dialog_info(event)
    print(f"Extracted Information:")
    print(f"  Player ID: {result['player_id']}")
    print(f"  Statement: {result['statement']}")
    print(f"  Round: {result['round']}")
    print(f"  Valid: {'YES' if result['valid'] else 'NO'}")
    print()
    print("-"*70)
    print()

print("\n" + "="*70)
print("SUMMARY")
print("="*70)

valid_count = sum(1 for event in test_events if extract_dialog_info(event)['valid'])
print(f"Valid dialogs extracted: {valid_count}/{len(test_events)}")
print()

if valid_count == len(test_events):
    print("[SUCCESS] All test events successfully extracted!")
else:
    print("[WARNING] Some events failed extraction. Review the logic.")

print()
print("="*70)
print("WEB UI INTEGRATION NOTES")
print("="*70)
print()
print("The integrated_web_ui.py has been updated with:")
print("1. Enhanced dialog detection using speech emoji markers")
print("2. Improved pattern matching for player statements")
print("3. Better handling of structured vs string events")
print("4. Automatic cleanup of emoji prefixes in statements")
print()
print("To test the full system:")
print("1. Run: python integrated_web_ui.py")
print("2. Open browser to http://localhost:5000")
print("3. Start a game and watch the 'Player Interactions' section")
print("4. Player dialogs should now appear in real-time")
print()
print("="*70)
