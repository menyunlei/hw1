"""
简化的测试服务器 - 仅用于测试评估功能
"""
from flask import Flask, jsonify
from enhanced_reasoning_evaluator import EnhancedReasoningEvaluator
import queue

app = Flask(__name__)

# 添加CORS头
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

# 全局变量
dialogue_queue = queue.Queue()
game_evaluator = None

@app.route('/api/test_evaluation', methods=['POST'])
def test_evaluation():
    """测试评估功能 - 注入模拟数据"""
    global game_evaluator, dialogue_queue

    # 初始化评估器
    game_evaluator = EnhancedReasoningEvaluator(test_subject_id=7)
    print("[TEST] Evaluator initialized")

    # 注入测试数据
    test_dialogues = [
        {"type": "dialogue", "player_id": 7, "content": "我认为Player 2是真预言家,因为他的发言逻辑清晰", "round": 1, "phase": "day"},
        {"type": "dialogue", "player_id": 7, "content": "Player 3的投票模式很可疑,他总是跟随Player 5投票", "round": 1, "phase": "day"},
        {"type": "dialogue", "player_id": 7, "content": "🗳️ 投票给 Player 3", "round": 1, "phase": "voting"},
        {"type": "dialogue", "player_id": 7, "content": "根据概率论,如果Player 2是真预言家,那么Player 5是狼的概率是80%", "round": 2, "phase": "day"},
        {"type": "dialogue", "player_id": 7, "content": "我需要重新考虑,Player 5昨天的发言其实有道理", "round": 2, "phase": "day"},
        {"type": "dialogue", "player_id": 7, "content": "🗳️ 投票给 Player 6", "round": 2, "phase": "voting"},
    ]

    # 清空并添加测试数据
    while not dialogue_queue.empty():
        dialogue_queue.get()

    for dialogue in test_dialogues:
        dialogue_queue.put(dialogue)

    print(f"[TEST] Injected {len(test_dialogues)} test dialogues")
    return jsonify({"status": "ok", "message": f"已注入{len(test_dialogues)}条测试数据", "test_data_count": len(test_dialogues)})

@app.route('/api/get_evaluation', methods=['GET'])
def get_evaluation():
    """获取评估结果"""
    global game_evaluator, dialogue_queue

    if game_evaluator is None:
        return jsonify({"status": "error", "message": "评估器未初始化，请先调用 /api/test_evaluation"}), 400

    try:
        # 转换对话历史
        dialogue_history = list(dialogue_queue.queue)
        print(f"[EVAL] dialogue_history length: {len(dialogue_history)}")

        # 清空评估器数据
        game_evaluator.speeches = []
        game_evaluator.votes = []
        game_evaluator.events = []

        # 添加事件
        for dialogue in dialogue_history:
            player_id = dialogue.get('player_id')
            if player_id == 7:
                content = dialogue.get('content', '')
                phase = dialogue.get('phase', '')
                round_num = dialogue.get('round', 1)

                is_vote = '投票' in phase or content.startswith('🗳️')

                if is_vote:
                    import re
                    match = re.search(r'Player (\d+)', content)
                    target = int(match.group(1)) if match else None
                    game_evaluator.add_event('vote', player_id, content, round_num, {'target': target})
                    print(f"[EVAL] Added vote, target={target}")
                else:
                    game_evaluator.add_event('speech', player_id, content, round_num)
                    print(f"[EVAL] Added speech")

        print(f"[EVAL] Total speeches: {len(game_evaluator.speeches)}, votes: {len(game_evaluator.votes)}")

        # 计算评分
        result = game_evaluator.calculate_final_score()

        # 添加统计
        result['stats'] = {
            'speeches': len(game_evaluator.speeches),
            'votes': len(game_evaluator.votes),
            'dialogue_queue_size': len(dialogue_history)
        }

        print(f"[EVAL] Score: {result['weighted_score']}/100")
        return jsonify({"status": "ok", "evaluation": result})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("测试评估服务器")
    print("=" * 60)
    print("端口: 5006")
    print("测试步骤:")
    print("1. POST http://localhost:5006/api/test_evaluation")
    print("2. GET  http://localhost:5006/api/get_evaluation")
    print("=" * 60)
    app.run(host='127.0.0.1', port=5006, debug=False)
