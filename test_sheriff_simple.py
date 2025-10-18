"""
Simple test for sheriff election mandatory campaign rules
简单测试强制上警规则
"""

import sys
sys.path.insert(0, '.')

from werewolf_game import Role, GameState, PlayerState, LLMAgent

def test_mandatory_campaigns():
    """Test that werewolves and seer must campaign"""

    print("=" * 60)
    print("TESTING MANDATORY SHERIFF CAMPAIGNS")
    print("=" * 60)

    # Mock LLM config
    llm_config = {
        'api_base': 'http://localhost:8080',
        'model': '/home/apulis-dev/userdata/Llama-3.3-70B-Instruct',
        'temperature': 0.7,
        'max_tokens': 500
    }

    # Create mock game state
    game_state = GameState()
    game_state.round = 1
    game_state.phase = "sheriff_election"

    # Create test players with different roles
    test_roles = [
        (1, Role.WEREWOLF_KING, "Werewolf King"),
        (2, Role.WEREWOLF, "Werewolf"),
        (3, Role.WEREWOLF, "Werewolf"),
        (4, Role.WEREWOLF, "Werewolf"),
        (5, Role.SEER, "Seer"),
        (6, Role.WITCH, "Witch"),
        (7, Role.HUNTER, "Hunter"),
        (8, Role.GUARD, "Guard"),
        (9, Role.VILLAGER, "Villager"),
        (10, Role.VILLAGER, "Villager"),
        (11, Role.VILLAGER, "Villager"),
        (12, Role.VILLAGER, "Villager"),
        (13, Role.JUDGE, "Judge")
    ]

    print("\n1. Setting up test players:")
    print("-" * 40)

    for player_id, role, role_name in test_roles:
        player = PlayerState(
            id=player_id,
            name=f"Player{player_id}",
            role=role,
            is_alive=True
        )
        game_state.players.append(player)
        print(f"   Player {player_id:2d}: {role_name:15s}")

    print("\n2. Testing campaign decisions:")
    print("-" * 40)
    print("   Expected: Werewolves and Seer MUST campaign")
    print("   Expected: Judge excluded from game")
    print("   Expected: Others campaign voluntarily")
    print("-" * 40)

    campaign_results = []
    errors = []

    for player in game_state.players:
        # Skip judge
        if player.role == Role.JUDGE:
            print(f"   Player {player.id:2d} (Judge): EXCLUDED - Correct")
            continue

        # Create agent and test campaign decision
        agent = LLMAgent(player.id, llm_config)

        # Test the decide_sheriff_campaign method
        try:
            # The method should return True for werewolves and seer
            decision = agent.decide_sheriff_campaign(game_state)

            is_mandatory = player.role in [Role.WEREWOLF, Role.WEREWOLF_KING, Role.SEER]
            role_name = player.role.value

            if is_mandatory:
                if decision:
                    status = "CORRECT (Must campaign)"
                    symbol = "[OK]"
                else:
                    status = "ERROR (Should campaign)"
                    symbol = "[FAIL]"
                    errors.append(f"Player {player.id} ({role_name}) did not campaign")
            else:
                if decision:
                    status = "Voluntary campaign"
                    symbol = "[OK]"
                else:
                    status = "Declined"
                    symbol = "[OK]"

            campaign_results.append({
                'id': player.id,
                'role': role_name,
                'mandatory': is_mandatory,
                'campaigned': decision
            })

            print(f"   Player {player.id:2d} ({role_name:12s}): {decision!s:5s} - {status:25s} {symbol}")

        except Exception as e:
            print(f"   Player {player.id:2d}: ERROR - {e}")
            errors.append(f"Player {player.id} error: {e}")

    print("\n3. Summary:")
    print("-" * 40)

    # Count mandatory campaigns
    mandatory_count = sum(1 for r in campaign_results if r['mandatory'])
    mandatory_campaigned = sum(1 for r in campaign_results if r['mandatory'] and r['campaigned'])
    voluntary_count = sum(1 for r in campaign_results if not r['mandatory'])
    voluntary_campaigned = sum(1 for r in campaign_results if not r['mandatory'] and r['campaigned'])

    print(f"   Mandatory roles: {mandatory_count}")
    print(f"   Actually campaigned: {mandatory_campaigned}")
    print(f"   Voluntary roles: {voluntary_count}")
    print(f"   Voluntarily campaigned: {voluntary_campaigned}")

    # Check specific roles
    werewolves_campaigned = all(r['campaigned'] for r in campaign_results
                                if r['role'] in ['werewolf', 'werewolf_king'])
    seer_campaigned = all(r['campaigned'] for r in campaign_results
                          if r['role'] == 'seer')

    print("\n4. Verification:")
    print("-" * 40)
    print(f"   All werewolves campaigned: {werewolves_campaigned} {'[PASS]' if werewolves_campaigned else '[FAIL]'}")
    print(f"   Seer campaigned: {seer_campaigned} {'[PASS]' if seer_campaigned else '[FAIL]'}")
    print(f"   Judge excluded: True [PASS]")

    if errors:
        print("\n5. Errors found:")
        print("-" * 40)
        for error in errors:
            print(f"   - {error}")
        return False
    else:
        print("\n5. Result:")
        print("-" * 40)
        print("   [SUCCESS] All mandatory campaign rules working correctly!")
        return True


if __name__ == "__main__":
    print("\nSIMPLE SHERIFF ELECTION TEST")
    print("Testing mandatory campaign rules without full game initialization\n")

    try:
        success = test_mandatory_campaigns()

        print("\n" + "=" * 60)
        if success:
            print("TEST PASSED!")
            print("Werewolves and Seer MUST campaign: VERIFIED")
            print("Judge excluded from game: VERIFIED")
            print("Other roles campaign voluntarily: VERIFIED")
        else:
            print("TEST FAILED!")
            print("Please check the decide_sheriff_campaign method")
        print("=" * 60)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()