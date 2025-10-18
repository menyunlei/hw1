"""
Human Player Demo - Interactive GUI for 1 Human + 11 NPC Werewolf Game
人类玩家演示 - 1个人类玩家 + 11个NPC的狼人杀游戏

The human player can be assigned as Player 7 (test subject) to participate in the guided demo.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import requests
import json
from queue import Queue
import time

# Import the guided demo configuration
from guided_demo import (
    DEMO_ROLES,
    get_player_script,
    get_uls_instruction,
    get_night_script,
    get_voting_script,
    get_demo_summary
)

# Import the reasoning evaluator
from reasoning_evaluator import ReasoningEvaluator

class HumanPlayerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("狼人杀 - 人类玩家模式 (Human Player Demo)")
        self.root.geometry("1400x900")

        # Game state
        self.human_player_id = 7  # Default: Player 7 (test subject)
        self.game_running = False
        self.current_phase = "waiting"
        self.message_queue = Queue()

        # API Configuration
        self.api_url = "http://localhost:5000"

        # Reasoning evaluator
        self.evaluator = ReasoningEvaluator(test_subject_id=self.human_player_id)

        self.setup_ui()
        self.start_message_listener()

    def setup_ui(self):
        """Setup the GUI layout"""

        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        # ===== Left Panel: Player Info & Controls =====
        left_frame = ttk.Frame(main_frame, padding="5")
        left_frame.grid(row=0, column=0, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Player Info
        info_label = ttk.Label(left_frame, text="你的角色信息", font=("Arial", 14, "bold"))
        info_label.pack(pady=5)

        self.player_info_text = scrolledtext.ScrolledText(left_frame, width=30, height=10, wrap=tk.WORD)
        self.player_info_text.pack(pady=5, fill=tk.BOTH, expand=True)

        # Quick Actions
        action_label = ttk.Label(left_frame, text="快捷操作", font=("Arial", 12, "bold"))
        action_label.pack(pady=5)

        self.sheriff_btn = ttk.Button(left_frame, text="🎖️ 上警竞选", command=self.sheriff_campaign)
        self.sheriff_btn.pack(pady=2, fill=tk.X)

        self.speak_btn = ttk.Button(left_frame, text="💬 发言", command=self.open_speech_dialog)
        self.speak_btn.pack(pady=2, fill=tk.X)

        self.vote_btn = ttk.Button(left_frame, text="🗳️ 投票", command=self.open_vote_dialog)
        self.vote_btn.pack(pady=2, fill=tk.X)

        # Night Actions (hidden initially)
        self.night_action_frame = ttk.LabelFrame(left_frame, text="夜晚行动", padding="5")
        self.night_action_frame.pack(pady=5, fill=tk.X)
        self.night_action_frame.pack_forget()  # Hide by default

        # Player List
        player_list_label = ttk.Label(left_frame, text="玩家列表", font=("Arial", 12, "bold"))
        player_list_label.pack(pady=5)

        self.player_list = scrolledtext.ScrolledText(left_frame, width=30, height=15, wrap=tk.WORD)
        self.player_list.pack(pady=5, fill=tk.BOTH, expand=True)

        # ===== Center Panel: Game Log =====
        center_frame = ttk.Frame(main_frame, padding="5")
        center_frame.grid(row=0, column=1, rowspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Phase indicator
        self.phase_label = ttk.Label(center_frame, text="游戏阶段: 等待开始",
                                     font=("Arial", 16, "bold"), foreground="blue")
        self.phase_label.pack(pady=5)

        # Game log
        log_label = ttk.Label(center_frame, text="游戏日志", font=("Arial", 12, "bold"))
        log_label.pack(pady=5)

        self.game_log = scrolledtext.ScrolledText(center_frame, width=80, height=35, wrap=tk.WORD)
        self.game_log.pack(pady=5, fill=tk.BOTH, expand=True)

        # ===== Right Panel: NPC Guidance & Statistics =====
        right_frame = ttk.Frame(main_frame, padding="5")
        right_frame.grid(row=0, column=2, rowspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))

        # NPC Guidance
        guidance_label = ttk.Label(right_frame, text="NPC行为指引", font=("Arial", 12, "bold"))
        guidance_label.pack(pady=5)

        self.npc_guidance = scrolledtext.ScrolledText(right_frame, width=35, height=20, wrap=tk.WORD)
        self.npc_guidance.pack(pady=5, fill=tk.BOTH, expand=True)

        # Statistics
        stats_label = ttk.Label(right_frame, text="游戏统计", font=("Arial", 12, "bold"))
        stats_label.pack(pady=5)

        self.stats_text = scrolledtext.ScrolledText(right_frame, width=35, height=15, wrap=tk.WORD)
        self.stats_text.pack(pady=5, fill=tk.BOTH, expand=True)

        # ===== Bottom Panel: Controls =====
        control_frame = ttk.Frame(main_frame, padding="5")
        control_frame.grid(row=2, column=1, sticky=(tk.W, tk.E))

        self.start_btn = ttk.Button(control_frame, text="▶️ 开始游戏", command=self.start_game)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(control_frame, text="⏹️ 停止游戏", command=self.stop_game, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.next_btn = ttk.Button(control_frame, text="⏭️ 继续下一阶段", command=self.next_phase, state=tk.DISABLED)
        self.next_btn.pack(side=tk.LEFT, padx=5)

        self.eval_btn = ttk.Button(control_frame, text="📊 显示评估结果", command=self.show_evaluation, state=tk.DISABLED)
        self.eval_btn.pack(side=tk.LEFT, padx=5)

        # Player selection
        ttk.Label(control_frame, text="你的座位号:").pack(side=tk.LEFT, padx=5)
        self.player_var = tk.StringVar(value="7")
        player_combo = ttk.Combobox(control_frame, textvariable=self.player_var,
                                    values=[str(i) for i in range(1, 13)], width=5)
        player_combo.pack(side=tk.LEFT, padx=5)
        player_combo.bind("<<ComboboxSelected>>", self.on_player_change)

    def log_message(self, message, tag="info"):
        """Add message to game log"""
        self.game_log.insert(tk.END, f"{message}\n", tag)
        self.game_log.see(tk.END)

        # Color coding
        self.game_log.tag_config("info", foreground="black")
        self.game_log.tag_config("system", foreground="blue", font=("Arial", 10, "bold"))
        self.game_log.tag_config("important", foreground="red", font=("Arial", 10, "bold"))
        self.game_log.tag_config("npc", foreground="gray")

    def update_player_info(self):
        """Update player information display"""
        player_id = self.human_player_id
        if player_id in DEMO_ROLES:
            role_info = DEMO_ROLES[player_id]
            info = f"座位号: {player_id}\n"
            info += f"角色: {role_info['role']}\n"
            info += f"任务: {role_info['duty']}\n\n"

            # Add behavior hints
            behavior = role_info['behavior']
            info += "行为提示:\n"
            if behavior.get('sheriff_campaign'):
                info += "  ✓ 需要上警竞选\n"
            info += f"  站边: {behavior.get('side_with', '未知')}\n"
            info += f"  发言风格: {behavior.get('speech_style', '自由')}\n"

            self.player_info_text.delete(1.0, tk.END)
            self.player_info_text.insert(1.0, info)

    def update_player_list(self):
        """Update player list display"""
        text = "玩家列表 (1-12):\n" + "="*30 + "\n"
        for pid in range(1, 13):
            if pid == self.human_player_id:
                text += f"👤 Player {pid} (你)\n"
            else:
                text += f"🤖 Player {pid} (NPC)\n"
                if pid in DEMO_ROLES:
                    text += f"     角色: {DEMO_ROLES[pid]['role']}\n"

        self.player_list.delete(1.0, tk.END)
        self.player_list.insert(1.0, text)

    def update_npc_guidance(self, phase):
        """Show NPC behavior guidance for current phase"""
        text = f"当前阶段: {phase}\n" + "="*40 + "\n\n"

        if phase == "sheriff_campaign":
            text += "上警环节 - NPC行为:\n\n"
            for pid in [2, 10]:
                uls = get_uls_instruction(pid, "sheriff_campaign")
                if uls:
                    text += f"Player {pid}:\n"
                    text += f"  {uls['natural_language']}\n\n"

        elif phase == "wolf_discussion":
            text += "狼人讨论 - NPC行为:\n\n"
            for pid in [1, 10, 11, 12]:
                if pid != self.human_player_id:
                    uls = get_uls_instruction(pid, "wolf_discussion", {"night": 1})
                    if uls:
                        text += f"Player {pid}:\n"
                        text += f"  {uls['natural_language']}\n\n"

        elif phase == "voting":
            text += "投票环节 - NPC行为:\n\n"
            vote_script = get_voting_script("sheriff_election")
            if vote_script:
                for pid, target in vote_script["votes"].items():
                    if pid != self.human_player_id:
                        text += f"Player {pid} → Player {target}\n"

        self.npc_guidance.delete(1.0, tk.END)
        self.npc_guidance.insert(1.0, text)

    def on_player_change(self, event=None):
        """Handle player selection change"""
        try:
            self.human_player_id = int(self.player_var.get())
            # Reinitialize evaluator with new player ID
            self.evaluator = ReasoningEvaluator(test_subject_id=self.human_player_id)
            self.update_player_info()
            self.update_player_list()
            self.log_message(f"你现在是 Player {self.human_player_id}", "system")
        except ValueError:
            pass

    def start_game(self):
        """Start the game"""
        self.game_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.next_btn.config(state=tk.NORMAL)

        self.log_message("="*60, "system")
        self.log_message("游戏开始！", "system")
        self.log_message("="*60, "system")

        # Show demo summary
        summary = get_demo_summary()
        self.log_message(f"\n{summary['title']}", "important")
        self.log_message(f"玩家数: {summary['players']}")
        self.log_message(f"你的座位: Player {self.human_player_id}")
        self.log_message(f"测试主体: Player {summary['test_subject']}\n")

        self.update_player_info()
        self.update_player_list()

        # Start with Night 1
        self.current_phase = "night1"
        self.phase_label.config(text="🌙 第1夜 - 夜晚行动")
        self.show_night_phase()

    def stop_game(self):
        """Stop the game"""
        self.game_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.next_btn.config(state=tk.DISABLED)

        self.log_message("\n游戏已停止", "system")

    def show_night_phase(self):
        """Show night phase actions"""
        self.log_message("\n" + "="*60, "system")
        self.log_message("🌙 第1夜开始", "important")
        self.log_message("="*60, "system")

        night_script = get_night_script(1)

        # Check if human player is a wolf
        human_role = DEMO_ROLES.get(self.human_player_id, {}).get('role')

        if human_role in ['狼人', '狼王']:
            self.log_message("\n你是狼人！现在是狼人讨论时间...", "important")
            self.update_npc_guidance("wolf_discussion")

            # Show wolf team discussion
            self.log_message("\n狼队讨论:", "npc")
            for pid in [1, 10, 11, 12]:
                if pid != self.human_player_id:
                    uls = get_uls_instruction(pid, "wolf_discussion", {"night": 1})
                    if uls:
                        self.log_message(f"Player {pid}: {uls['natural_language']}", "npc")

            self.log_message(f"\n建议目标: Player {night_script['wolves_kill']}", "important")

        else:
            self.log_message("\n你闭眼睡觉...", "info")
            self.log_message("狼人正在讨论刀人目标...", "npc")

        # Show night actions (for demo purposes, reveal to human)
        self.log_message("\n[剧本提示 - 第1夜行动]:", "system")
        self.log_message(f"  狼人刀: Player {night_script['wolves_kill']}")
        self.log_message(f"  预言家验: Player {night_script['seer_check']}")
        self.log_message(f"  守卫守: Player {night_script['guard_protect']}")
        self.log_message(f"  女巫救: {night_script['witch_save']}")
        self.log_message(f"  女巫毒: Player {night_script['witch_poison']}")

    def sheriff_campaign(self):
        """Open sheriff campaign dialog"""
        self.current_phase = "sheriff_campaign"
        self.phase_label.config(text="🎖️ 警长竞选")

        self.log_message("\n" + "="*60, "system")
        self.log_message("🎖️ 警长竞选开始", "important")
        self.log_message("="*60, "system")

        self.update_npc_guidance("sheriff_campaign")

        # Show NPC candidates
        self.log_message("\n上警候选人: Player 2, Player 10", "info")

        # Player 2 speech
        uls_2 = get_uls_instruction(2, "sheriff_campaign")
        if uls_2:
            self.log_message(f"\nPlayer 2 发言:", "npc")
            self.log_message(f"  {uls_2['natural_language']}", "npc")
            self.log_message(f"  [ULS++: {uls_2['uls_format']}]", "npc")

        # Player 10 speech
        uls_10 = get_uls_instruction(10, "sheriff_campaign")
        if uls_10:
            self.log_message(f"\nPlayer 10 发言:", "npc")
            self.log_message(f"  {uls_10['natural_language']}", "npc")
            self.log_message(f"  [ULS++: {uls_10['uls_format']}]", "npc")

        # Check if human should speak
        human_behavior = DEMO_ROLES.get(self.human_player_id, {}).get('behavior', {})
        if human_behavior.get('sheriff_campaign'):
            self.log_message(f"\n你需要上警竞选！请发言...", "important")
            self.open_speech_dialog()
        else:
            self.log_message(f"\n你没有上警", "info")

    def open_speech_dialog(self):
        """Open speech input dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("发言")
        dialog.geometry("500x300")

        ttk.Label(dialog, text="输入你的发言:", font=("Arial", 12)).pack(pady=10)

        speech_text = scrolledtext.ScrolledText(dialog, width=60, height=10)
        speech_text.pack(pady=10)

        def submit_speech():
            speech = speech_text.get(1.0, tk.END).strip()
            if speech:
                self.log_message(f"\n[你的发言]:", "important")
                self.log_message(f"Player {self.human_player_id}: {speech}", "important")

                # Record speech for evaluation
                round_num = 1 if "night1" in self.current_phase or "sheriff" in self.current_phase else 2
                self.evaluator.add_event("speech", self.human_player_id, speech, round_num)

                # Enable evaluation button after first speech
                self.eval_btn.config(state=tk.NORMAL)

                dialog.destroy()
            else:
                messagebox.showwarning("警告", "请输入发言内容")

        ttk.Button(dialog, text="提交发言", command=submit_speech).pack(pady=10)

    def open_vote_dialog(self):
        """Open voting dialog"""
        self.current_phase = "voting"
        self.phase_label.config(text="🗳️ 投票阶段")

        self.update_npc_guidance("voting")

        dialog = tk.Toplevel(self.root)
        dialog.title("投票")
        dialog.geometry("400x300")

        ttk.Label(dialog, text="请选择你要投票的玩家:", font=("Arial", 12)).pack(pady=10)

        vote_var = tk.StringVar()

        # Create vote buttons
        for i in range(1, 13):
            if i != self.human_player_id:
                ttk.Radiobutton(dialog, text=f"Player {i}", variable=vote_var,
                              value=str(i)).pack(anchor=tk.W, padx=20)

        def submit_vote():
            target = vote_var.get()
            if target:
                self.log_message(f"\n[你的投票]:", "important")
                self.log_message(f"Player {self.human_player_id} 投票给 Player {target}", "important")

                # Record vote for evaluation
                round_num = 1 if "sheriff" in self.current_phase else 2
                vote_type = "sheriff" if "sheriff" in self.current_phase else "day_exile"
                self.evaluator.add_event("vote", self.human_player_id, f"投票给{target}",
                                        round_num, {"target": int(target), "vote_type": vote_type})

                # Show NPC votes
                self.log_message("\nNPC投票结果:", "npc")
                vote_script = get_voting_script("sheriff_election")
                if vote_script:
                    vote_count = {}
                    for pid, vtarget in vote_script["votes"].items():
                        if pid != self.human_player_id:
                            self.log_message(f"  Player {pid} → Player {vtarget}", "npc")
                            vote_count[vtarget] = vote_count.get(vtarget, 0) + 1

                    # Add human vote
                    vote_count[int(target)] = vote_count.get(int(target), 0) + 1

                    self.log_message("\n投票统计:", "system")
                    for candidate, count in sorted(vote_count.items()):
                        self.log_message(f"  Player {candidate}: {count}票", "system")

                dialog.destroy()
            else:
                messagebox.showwarning("警告", "请选择投票目标")

        ttk.Button(dialog, text="确认投票", command=submit_vote).pack(pady=20)

    def next_phase(self):
        """Move to next game phase"""
        phase_sequence = [
            "night1",
            "sheriff_campaign",
            "day1_discussion",
            "day1_voting",
            "night2",
            "day2_discussion"
        ]

        try:
            current_idx = phase_sequence.index(self.current_phase)
            if current_idx < len(phase_sequence) - 1:
                self.current_phase = phase_sequence[current_idx + 1]
                self.log_message(f"\n进入下一阶段: {self.current_phase}", "system")

                if self.current_phase == "sheriff_campaign":
                    self.sheriff_campaign()
                elif self.current_phase == "day1_voting":
                    self.open_vote_dialog()
        except ValueError:
            pass

    def show_evaluation(self):
        """Show evaluation results in a new window"""
        # Calculate evaluation
        eval_result = self.evaluator.calculate_final_score()
        report = self.evaluator.generate_report()

        # Create evaluation window
        eval_window = tk.Toplevel(self.root)
        eval_window.title("📊 深度推理能力评估报告")
        eval_window.geometry("900x700")

        # Main container
        main_frame = ttk.Frame(eval_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame,
                               text=f"深度推理能力评估报告 - Player {self.human_player_id}",
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Score summary frame
        summary_frame = ttk.Frame(main_frame, padding="10", relief=tk.RIDGE, borderwidth=2)
        summary_frame.pack(fill=tk.X, pady=10)

        # Final score
        score_label = ttk.Label(summary_frame,
                               text=f"总分: {eval_result['weighted_score']}/100",
                               font=("Arial", 20, "bold"),
                               foreground="blue")
        score_label.pack()

        grade_label = ttk.Label(summary_frame,
                               text=f"等级: {eval_result['final_grade']}",
                               font=("Arial", 16, "bold"),
                               foreground="red" if eval_result['weighted_score'] < 60 else "green")
        grade_label.pack()

        # Dimension scores
        dimensions_frame = ttk.LabelFrame(main_frame, text="各维度得分", padding="10")
        dimensions_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # Create scrolled text for dimensions
        dimensions_text = scrolledtext.ScrolledText(dimensions_frame, width=100, height=15,
                                                    wrap=tk.WORD, font=("Courier", 10))
        dimensions_text.pack(fill=tk.BOTH, expand=True)

        # Format dimension scores
        for dim_key, dim_info in self.evaluator.dimensions.items():
            result = eval_result["scores"].get(dim_key, {})
            score = result.get("score", 0)
            weight = dim_info["weight"]

            dimensions_text.insert(tk.END, f"\n{'='*80}\n", "header")
            dimensions_text.insert(tk.END, f"【{dim_info['name']}】 ", "header")
            dimensions_text.insert(tk.END, f"权重: {weight*100}%  得分: {score}/100\n", "score")
            dimensions_text.insert(tk.END, f"{'='*80}\n", "header")

            for detail in result.get("details", []):
                if "✓" in detail:
                    dimensions_text.insert(tk.END, f"{detail}\n", "pass")
                elif "✗" in detail:
                    dimensions_text.insert(tk.END, f"{detail}\n", "fail")
                else:
                    dimensions_text.insert(tk.END, f"{detail}\n", "neutral")

        # Color tags
        dimensions_text.tag_config("header", foreground="blue", font=("Courier", 10, "bold"))
        dimensions_text.tag_config("score", foreground="purple", font=("Courier", 10, "bold"))
        dimensions_text.tag_config("pass", foreground="green")
        dimensions_text.tag_config("fail", foreground="red")
        dimensions_text.tag_config("neutral", foreground="orange")

        dimensions_text.config(state=tk.DISABLED)

        # Statistics
        stats_frame = ttk.Frame(main_frame, padding="10")
        stats_frame.pack(fill=tk.X)

        stats_text = f"统计: 发言 {len(self.evaluator.speeches)}次 | 投票 {len(self.evaluator.votes)}次 | 站边变化 {len(self.evaluator.side_changes)}次"
        ttk.Label(stats_frame, text=stats_text, font=("Arial", 10)).pack()

        # Buttons
        button_frame = ttk.Frame(main_frame, padding="10")
        button_frame.pack(fill=tk.X)

        def export_report():
            filename = self.evaluator.export_json(f"evaluation_player{self.human_player_id}.json")
            messagebox.showinfo("导出成功", f"评估结果已导出到:\n{filename}")

        ttk.Button(button_frame, text="📄 导出JSON", command=export_report).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📋 复制报告", command=lambda: self.copy_to_clipboard(report)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="关闭", command=eval_window.destroy).pack(side=tk.RIGHT, padx=5)

        # Also update the stats panel in main window
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, f"评估结果摘要\n{'='*40}\n\n")
        self.stats_text.insert(1.0, f"总分: {eval_result['weighted_score']}/100\n")
        self.stats_text.insert(1.0, f"等级: {eval_result['final_grade']}\n\n")

        for dim_key, dim_info in self.evaluator.dimensions.items():
            result = eval_result["scores"].get(dim_key, {})
            score = result.get("score", 0)
            self.stats_text.insert(tk.END, f"{dim_info['name']}: {score}/100\n")

    def copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("已复制", "报告已复制到剪贴板")

    def start_message_listener(self):
        """Start background thread to listen for messages"""
        def listener():
            while True:
                try:
                    if not self.message_queue.empty():
                        msg = self.message_queue.get()
                        self.log_message(msg)
                    time.sleep(0.1)
                except:
                    break

        thread = threading.Thread(target=listener, daemon=True)
        thread.start()


def main():
    root = tk.Tk()
    app = HumanPlayerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
