
import sys
sys.path.insert(0, r"C:\Users\yunlei\Downloads\hw1")
from werewolf_game import WerewolfGame
import json

llm_config = {
    'api_base': 'http://localhost:8080',
    'model': '/home/apulis-dev/userdata/Llama-3.3-70B-Instruct',
    'temperature': 0.7,
    'max_tokens': 500
}

print("[SYSTEM] Starting Werewolf Game")
print("[CONFIG] API: 0".format(llm_config['api_base']))
print("[CONFIG] Model: 0".format(llm_config['model']))
print("="*70)

try:
    # 直接使用用户指定的模型
    print("[CONFIG] 使用模型: 0".format(llm_config['model']))
    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    results = game.play_game()
    
    print("\n[SYSTEM] Game completed successfully")
    print("[RESULT] Winner: " + results['game_summary']['winner'])
    print("[RESULT] Rounds: " + str(results['game_summary']['total_rounds']))

    # Save results
    with open('last_game_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

except Exception as e:
    print("[ERROR] Game failed: " + str(e))
    import traceback
    traceback.print_exc()
