from pathlib import Path
text = Path('werewolf_3panels.py').read_text(encoding='utf-8')
needle = "def check_win_condition():"
idx = text.find(needle)
assert idx != -1
end_idx = text.find('\n\n', idx + len(needle))
insert_pos = text.find('\n', end_idx) + 1
snippet = "def finalize_game(winner, reason=\"\", details=\"\"):\n    \"\"\"结束对局时统一处理收尾逻辑\"\"\"\n    global is_running\n\n    victory_faction = '狼人' if winner == 'werewolves' else '村民'\n    status_message = f'🎉 游戏结束 - {victory_faction}阵营胜利'\n    if victory_faction == '狼人':\n        content = f'🐺 狼人阵营获胜！\n\n胜利原因: {reason or ""}{details or ""}'\n    else:\n        content = f'👨‍🌾 村民阵营获胜！\n\n胜利原因: {reason or ""}{details or ""}'\n\n    dialogue_queue.put({\n        "type": "status",\n        "message": status_message\n    })\n    dialogue_queue.put({\n        "type": "dialogue",\n        "player_id": -1,\n        "phase": "游戏结束",\n        "content": content,\n        "panel": "day"\n    })\n\n    save_game_session(winner, reason or "", details or "")\n    display_game_summary()\n    is_running = False\n\n\n"\nnew_text = text[:insert_pos] + snippet + text[insert_pos:]
Path('werewolf_3panels.py').write_text(new_text, encoding='utf-8')
