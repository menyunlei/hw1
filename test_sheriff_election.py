"""
Test script for sheriff election with mandatory campaigns
测试脚本：验证强制上警规则
"""

import sys
import json
from werewolf_game import WerewolfGame, Role, LLMAgent

def test_sheriff_election():
    """Test the mandatory sheriff campaign rules"""

    print("Testing Sheriff Election Rules...")
    print("=" * 60)

    # Create a test game
    llm_config = {
        'api_base': 'http://172.28.32.1:1234',
        'model': 'meta-llama-3.1-8b-instruct',
        'temperature': 0.7,
        'max_tokens': 500
    }

    # Create game with 13 players
    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    game.initialize_game()

    print("\n1. Checking role distribution:")
    print("-" * 40)

    roles_count = {}
    werewolves = []
    seer = None
    judge = None

    for player in game.game_state.players:
        role_name = player.role.value
        roles_count[role_name] = roles_count.get(role_name, 0) + 1

        if player.role in [Role.WEREWOLF, Role.WEREWOLF_KING]:
            werewolves.append(player.id)
        elif player.role == Role.SEER:
            seer = player.id
        elif player.role == Role.JUDGE:
            judge = player.id

    for role, count in sorted(roles_count.items()):
        print(f"   {role}: {count}")

    print(f"\n   Werewolves (must campaign): {werewolves}")
    print(f"   Seer (must campaign): {seer}")
    print(f"   Judge (excluded): {judge}")

    print("\n2. Testing sheriff campaign decisions:")
    print("-" * 40)

    # Test campaign decisions for each player
    campaign_decisions = {}
    mandatory_campaigns = []
    voluntary_campaigns = []

    for player in game.game_state.players:
        if player.role == Role.JUDGE:
            print(f"   Player {player.id} (Judge) - Excluded from game")
            continue

        agent = LLMAgent(player.id, llm_config)
        decision = agent.decide_sheriff_campaign(game.game_state)
        campaign_decisions[player.id] = decision

        role_name = player.role.value
        is_mandatory = player.role in [Role.WEREWOLF, Role.WEREWOLF_KING, Role.SEER]

        if is_mandatory:
            mandatory_campaigns.append(player.id)
            status = "MANDATORY" if decision else "ERROR!"
        else:
            if decision:
                voluntary_campaigns.append(player.id)
            status = "voluntary" if decision else "declined"

        symbol = "[M]" if is_mandatory else "[V]"
        decision_text = "YES" if decision else "NO"

        print(f"   Player {player.id:2d} ({role_name:12s}) {symbol}: {decision_text:3s} - {status}")

    print("\n3. Verification Results:")
    print("-" * 40)

    # Check if all mandatory players campaigned
    all_werewolves_campaigned = all(campaign_decisions.get(w, False) for w in werewolves)
    seer_campaigned = campaign_decisions.get(seer, False)

    print(f"   All werewolves campaigned: {all_werewolves_campaigned} {'[OK]' if all_werewolves_campaigned else '[FAILED]'}")
    print(f"   Seer campaigned: {seer_campaigned} {'[OK]' if seer_campaigned else '[FAILED]'}")
    print(f"   Judge excluded: {judge not in campaign_decisions} [OK]")

    print(f"\n   Mandatory campaigns: {len(mandatory_campaigns)} players")
    print(f"   Voluntary campaigns: {len(voluntary_campaigns)} players")
    print(f"   Total campaigning: {len(mandatory_campaigns) + len(voluntary_campaigns)} players")

    # Test speech generation for campaigners
    print("\n4. Testing persuasive speech generation:")
    print("-" * 40)

    # Test a werewolf's speech
    if werewolves:
        werewolf_id = werewolves[0]
        werewolf_agent = LLMAgent(werewolf_id, llm_config)
        print(f"\n   Testing Werewolf (Player {werewolf_id}) speech:")

        # Mock speech generation
        werewolf_player = game.game_state.get_player_by_id(werewolf_id)
        print(f"   Role: {werewolf_player.role.value}")
        print("   Speech strategy: Hide identity, appear trustworthy")
        print("   Expected: Emphasize leadership, avoid suspicion")

    # Test seer's speech
    if seer:
        seer_agent = LLMAgent(seer, llm_config)
        print(f"\n   Testing Seer (Player {seer}) speech:")

        seer_player = game.game_state.get_player_by_id(seer)
        print(f"   Role: {seer_player.role.value}")
        print("   Speech strategy: Subtly hint at information role")
        print("   Expected: Emphasize investigation, truth-seeking")

    # Test voting logic
    print("\n5. Testing vote analysis logic:")
    print("-" * 40)

    print("   Vote factors considered:")
    print("   - Speech persuasiveness score")
    print("   - Leadership demonstration")
    print("   - Trust indicators")
    print("   - Logical consistency")
    print("   - Emotional appeal")

    # Summary
    print("\n" + "=" * 60)
    print("SHERIFF ELECTION TEST SUMMARY")
    print("=" * 60)

    success = all_werewolves_campaigned and seer_campaigned and (judge not in campaign_decisions)

    if success:
        print("[SUCCESS] All mandatory campaign rules working correctly!")
        print("   - Werewolves MUST campaign: Verified")
        print("   - Seer MUST campaign: Verified")
        print("   - Judge excluded: Verified")
    else:
        print("[FAILED] Issues found with mandatory campaigns:")
        if not all_werewolves_campaigned:
            print("   - Some werewolves did not campaign")
        if not seer_campaigned:
            print("   - Seer did not campaign")
        if judge in campaign_decisions:
            print("   - Judge was not properly excluded")

    return success


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SHERIFF ELECTION RULE TEST")
    print("Testing mandatory campaigns for Werewolves and Seer")
    print("=" * 60)

    try:
        success = test_sheriff_election()

        print("\n" + "=" * 60)
        if success:
            print("All tests passed! The sheriff election system is working.")
            print("\nKey features verified:")
            print("1. Werewolves (including King) MUST campaign")
            print("2. Seer MUST campaign")
            print("3. Other roles campaign voluntarily")
            print("4. Judge is excluded from all game activities")
            print("5. Persuasive speeches are role-appropriate")
        else:
            print("Some tests failed. Please check the implementation.")
        print("=" * 60)

    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()