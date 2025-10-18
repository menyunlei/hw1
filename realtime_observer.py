"""
Real-time Observer System for Werewolf Game
实时观战和幻觉标记系统
"""

import json
import asyncio
import websockets
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import queue
import sys


class HallucinationType(Enum):
    """Types of hallucinations"""
    FACTUAL_ERROR = "factual_error"  # 事实错误
    TIMELINE_CONFUSION = "timeline_confusion"  # 时间线混乱
    ROLE_CONFUSION = "role_confusion"  # 角色混淆
    FALSE_MEMORY = "false_memory"  # 虚假记忆
    LOGIC_CONTRADICTION = "logic_contradiction"  # 逻辑矛盾
    INFORMATION_FABRICATION = "info_fabrication"  # 信息编造


@dataclass
class HallucinationMark:
    """Hallucination mark by judge"""
    player_id: int
    round_number: int
    phase: str
    hallucination_type: HallucinationType
    description: str
    statement: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    severity: int = 1  # 1-5, 5 being most severe


@dataclass
class GameEvent:
    """Real-time game event"""
    event_type: str
    round: int
    phase: str
    data: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RealtimeObserver:
    """Real-time game observer with hallucination marking"""

    def __init__(self):
        self.events: List[GameEvent] = []
        self.hallucination_marks: List[HallucinationMark] = []
        self.game_state = {}
        self.websocket_clients = set()
        self.event_queue = queue.Queue()
        self.running = False

    def log_event(self, event_type: str, round_num: int, phase: str, data: Dict[str, Any]):
        """Log a game event"""
        event = GameEvent(event_type, round_num, phase, data)
        self.events.append(event)

        # Print to console for observation
        self._print_event(event)

        # Queue for WebSocket broadcast (will be handled by async loop if running)
        self._broadcast_event_sync(event)

    def mark_hallucination(self, player_id: int, round_num: int, phase: str,
                          hallucination_type: HallucinationType,
                          description: str, statement: str, severity: int = 1):
        """Mark a hallucination"""
        mark = HallucinationMark(
            player_id, round_num, phase, hallucination_type,
            description, statement, severity=severity
        )
        self.hallucination_marks.append(mark)

        print(f"\n HALLUCINATION MARKED:")
        print(f"   Player {player_id} - {hallucination_type.value}")
        print(f"   Description: {description}")
        print(f"   Severity: {'' * severity}")

        # Queue for WebSocket broadcast
        self._broadcast_hallucination_sync(mark)

    def _print_event(self, event: GameEvent):
        """Print event to console for observation"""
        symbols = {
            'game_start': '',
            'sheriff_elected': '[SHERIFF]',
            'night_deaths': '[NIGHT]',
            'day_elimination': '[DAY]',
            'player_statement': '[TALK]',
            'vote': '[VOTE]',
            'werewolf_action': '[WOLF]',
            'seer_check': '[SEER]',
            'witch_action': '[WITCH]',
            'hunter_revenge': '[TARGET]',
            'guard_protect': '[GUARD]'
        }

        symbol = symbols.get(event.event_type, '')
        print(f"\n{symbol} [{event.timestamp[-8:]}] Round {event.round} - {event.phase}")
        print(f"   {event.event_type}: {json.dumps(event.data, ensure_ascii=False)[:200]}")

    def _broadcast_event_sync(self, event: GameEvent):
        """Synchronously queue event for broadcast"""
        if self.websocket_clients:
            message = json.dumps({
                'type': 'game_event',
                'data': asdict(event)
            })
            # Queue for later async broadcast
            self.event_queue.put(('event', message))

    def _broadcast_hallucination_sync(self, mark: HallucinationMark):
        """Synchronously queue hallucination for broadcast"""
        if self.websocket_clients:
            message = json.dumps({
                'type': 'hallucination_mark',
                'data': {
                    'player_id': mark.player_id,
                    'round': mark.round_number,
                    'phase': mark.phase,
                    'type': mark.hallucination_type.value,
                    'description': mark.description,
                    'statement': mark.statement,
                    'severity': mark.severity,
                    'timestamp': mark.timestamp
                }
            })
            # Queue for later async broadcast
            self.event_queue.put(('hallucination', message))

    async def websocket_handler(self, websocket, path):
        """Handle WebSocket connections"""
        self.websocket_clients.add(websocket)
        try:
            # Send current state to new client
            await websocket.send(json.dumps({
                'type': 'initial_state',
                'events': [asdict(e) for e in self.events[-50:]],  # Last 50 events
                'hallucinations': [
                    {
                        'player_id': m.player_id,
                        'round': m.round_number,
                        'phase': m.phase,
                        'type': m.hallucination_type.value,
                        'description': m.description,
                        'severity': m.severity,
                        'timestamp': m.timestamp
                    } for m in self.hallucination_marks
                ]
            }))

            # Keep connection alive
            async for message in websocket:
                data = json.loads(message)

                # Handle client marking hallucination
                if data['type'] == 'mark_hallucination':
                    self.mark_hallucination(
                        data['player_id'],
                        data['round'],
                        data['phase'],
                        HallucinationType(data['hallucination_type']),
                        data['description'],
                        data.get('statement', ''),
                        data.get('severity', 1)
                    )

        finally:
            self.websocket_clients.remove(websocket)

    def start_websocket_server(self, host='localhost', port=8765):
        """Start WebSocket server for real-time observation"""
        import socket

        # Try to find an available port
        for attempt_port in range(port, port + 10):
            try:
                # Test if port is available
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((host, attempt_port))
                    s.close()

                print(f"\n Starting WebSocket server on ws://{host}:{attempt_port}")

                async def server():
                    async with websockets.serve(self.websocket_handler, host, attempt_port):
                        await asyncio.Future()  # run forever

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(server())
                break

            except OSError as e:
                if attempt_port == port + 9:
                    print(f"[ERROR] Could not find available port in range {port}-{port+9}")
                    raise
                else:
                    print(f"Port {attempt_port} is busy, trying next...")
                    continue

    def generate_hallucination_report(self) -> Dict[str, Any]:
        """Generate hallucination analysis report"""
        report = {
            'total_hallucinations': len(self.hallucination_marks),
            'by_player': {},
            'by_type': {},
            'by_round': {},
            'severity_distribution': {i: 0 for i in range(1, 6)},
            'detailed_marks': []
        }

        for mark in self.hallucination_marks:
            # By player
            if mark.player_id not in report['by_player']:
                report['by_player'][mark.player_id] = []
            report['by_player'][mark.player_id].append({
                'round': mark.round_number,
                'type': mark.hallucination_type.value,
                'severity': mark.severity
            })

            # By type
            h_type = mark.hallucination_type.value
            report['by_type'][h_type] = report['by_type'].get(h_type, 0) + 1

            # By round
            round_key = f"round_{mark.round_number}"
            report['by_round'][round_key] = report['by_round'].get(round_key, 0) + 1

            # Severity distribution
            report['severity_distribution'][mark.severity] += 1

            # Detailed marks
            report['detailed_marks'].append({
                'player_id': mark.player_id,
                'round': mark.round_number,
                'phase': mark.phase,
                'type': mark.hallucination_type.value,
                'description': mark.description,
                'statement': mark.statement,
                'severity': mark.severity,
                'timestamp': mark.timestamp
            })

        return report


class InteractiveJudge:
    """Interactive judge interface for marking hallucinations"""

    def __init__(self, observer: RealtimeObserver):
        self.observer = observer
        self.current_round = 0
        self.current_phase = "night"

    def start_interactive_mode(self):
        """Start interactive judging mode"""
        print("\n" + "="*70)
        print("[JUDGE] JUDGE MODE ACTIVATED")
        print("="*70)
        print("\nCommands:")
        print("  mark <player_id> <type> <severity> <description> - Mark hallucination")
        print("  types - Show hallucination types")
        print("  stats - Show current statistics")
        print("  help - Show this help")
        print("  quit - Exit judge mode")
        print("\nHallucination Types:")
        for h_type in HallucinationType:
            print(f"  {h_type.value}")
        print("="*70 + "\n")

        while True:
            try:
                command = input("\n[JUDGE] Judge> ").strip()

                if command == 'quit':
                    break
                elif command == 'help':
                    self._show_help()
                elif command == 'types':
                    self._show_types()
                elif command == 'stats':
                    self._show_stats()
                elif command.startswith('mark '):
                    self._mark_hallucination(command)
                else:
                    print("Unknown command. Type 'help' for help.")

            except KeyboardInterrupt:
                print("\n\nExiting judge mode...")
                break
            except Exception as e:
                print(f"Error: {e}")

    def _show_help(self):
        """Show help information"""
        print("\n[BOOK] HELP:")
        print("  mark <player_id> <type> <severity> <description>")
        print("    Example: mark 3 factual_error 3 Claims to be seer but contradicts earlier statement")
        print("\n  Severity levels: 1 (minor) to 5 (severe)")

    def _show_types(self):
        """Show hallucination types"""
        print("\n[TAG] HALLUCINATION TYPES:")
        types_desc = {
            HallucinationType.FACTUAL_ERROR: "Statement contradicts known facts",
            HallucinationType.TIMELINE_CONFUSION: "Confuses event order or timing",
            HallucinationType.ROLE_CONFUSION: "Mistakes or forgets roles",
            HallucinationType.FALSE_MEMORY: "References events that didn't happen",
            HallucinationType.LOGIC_CONTRADICTION: "Self-contradictory logic",
            HallucinationType.INFORMATION_FABRICATION: "Makes up information"
        }
        for h_type, desc in types_desc.items():
            print(f"  {h_type.value}: {desc}")

    def _show_stats(self):
        """Show current statistics"""
        report = self.observer.generate_hallucination_report()
        print("\n[STATS] HALLUCINATION STATISTICS:")
        print(f"  Total marks: {report['total_hallucinations']}")
        print(f"\n  By type:")
        for h_type, count in report['by_type'].items():
            print(f"    {h_type}: {count}")
        print(f"\n  Severity distribution:")
        for severity, count in report['severity_distribution'].items():
            if count > 0:
                print(f"    Level {severity}: {count} marks")

    def _mark_hallucination(self, command: str):
        """Mark a hallucination from command"""
        parts = command.split(' ', 4)
        if len(parts) < 5:
            print("Usage: mark <player_id> <type> <severity> <description>")
            return

        try:
            player_id = int(parts[1])
            h_type = HallucinationType(parts[2])
            severity = int(parts[3])
            description = parts[4]

            if severity < 1 or severity > 5:
                print("Severity must be between 1 and 5")
                return

            self.observer.mark_hallucination(
                player_id, self.current_round, self.current_phase,
                h_type, description, "", severity
            )
            print(f"[OK] Hallucination marked for Player {player_id}")

        except ValueError as e:
            print(f"Invalid input: {e}")
        except Exception as e:
            print(f"Error marking hallucination: {e}")


# Global observer instance
global_observer = RealtimeObserver()


def get_observer():
    """Get the global observer instance"""
    return global_observer


def start_observer_server():
    """Start the observer WebSocket server in a separate thread"""
    def run_server():
        global_observer.start_websocket_server()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("[OK] Observer WebSocket server started")


def start_interactive_judge():
    """Start interactive judge mode"""
    judge = InteractiveJudge(global_observer)
    judge_thread = threading.Thread(target=judge.start_interactive_mode, daemon=True)
    judge_thread.start()
    print("[OK] Interactive judge mode started")


if __name__ == '__main__':
    print("Starting Real-time Observer System...")
    start_observer_server()
    start_interactive_judge()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down observer system...")