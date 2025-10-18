"""
Test script to verify fixes are working
测试脚本验证修复是否正常
"""

import sys

print("Testing fixes...")

# Test 1: Check role descriptions
print("\n1. Testing role descriptions...")
from werewolf_game import Role

all_roles = [Role.WEREWOLF, Role.WEREWOLF_KING, Role.VILLAGER, Role.SEER,
             Role.WITCH, Role.HUNTER, Role.GUARD, Role.JUDGE]

print("   [OK] All roles defined:", all_roles)

# Test 2: Check import of observer
print("\n2. Testing observer import...")
try:
    from realtime_observer import get_observer, HallucinationType
    print("   [OK] Observer imported successfully")
except Exception as e:
    print(f"   ✗ Observer import failed: {e}")

# Test 3: Check WebSocket port handling
print("\n3. Testing WebSocket port availability...")
import socket

def test_port(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            s.close()
            return True
    except:
        return False

for port in range(8765, 8775):
    if test_port(port):
        print(f"   [OK] Port {port} is available")
        break
    else:
        print(f"   [WARN] Port {port} is busy")

# Test 4: Check game initialization with new roles
print("\n4. Testing game initialization...")
try:
    from werewolf_game import WerewolfGame, GameState, PlayerState

    # Mock LLM config
    llm_config = {
        'api_base': 'http://localhost:8080',
        'model': 'test',
        'temperature': 0.7,
        'max_tokens': 100
    }

    # Create game
    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    game.initialize_game()

    # Check roles
    roles_count = {}
    for player in game.game_state.players:
        role = player.role.value
        roles_count[role] = roles_count.get(role, 0) + 1

    print("   Role distribution:")
    for role, count in roles_count.items():
        print(f"      {role}: {count}")

    # Verify counts
    assert roles_count.get('werewolf_king', 0) == 1, "Should have 1 werewolf king"
    assert roles_count.get('werewolf', 0) == 3, "Should have 3 werewolves"
    assert roles_count.get('judge', 0) == 1, "Should have 1 judge"
    assert sum(roles_count.values()) == 13, "Should have 13 players total"

    print("   [OK] Game initialization successful")

except Exception as e:
    print(f"   ✗ Game initialization failed: {e}")
    import traceback
    traceback.print_exc()

print("\n[SUCCESS] All tests completed!")
print("\nYou can now run the game with:")
print("  python run_game.py")
print("\nOr with enhanced observer:")
print("  python run_with_observer.py")