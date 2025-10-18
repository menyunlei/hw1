"""
Werewolf Game for LLM Agent Evaluation
A 13-player werewolf game system for evaluating LLM performance in adversarial environments.
Evaluates: deception detection, cooperation, strategic reasoning, and hallucination resistance.
"""

import json
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import time
from datetime import datetime

# Try to import real-time observer
try:
    from realtime_observer import get_observer, HallucinationType
    OBSERVER_ENABLED = True
except ImportError:
    OBSERVER_ENABLED = False
    print("[WARN] Real-time observer not available. Run without observation.")


class Role(Enum):
    """Player roles in the game"""
    WEREWOLF = "werewolf"
    WEREWOLF_KING = "werewolf_king"  # 狼王 - 被淘汰时可以带走一人
    VILLAGER = "villager"
    SEER = "seer"
    WITCH = "witch"
    HUNTER = "hunter"
    GUARD = "guard"
    JUDGE = "judge"  # 裁判 - 标记幻觉，不参与游戏


class Phase(Enum):
    """Game phases"""
    NIGHT = "night"
    DAY_DISCUSSION = "day_discussion"
    DAY_VOTE = "day_vote"
    GAME_OVER = "game_over"


@dataclass
class PlayerState:
    """Represents a player's state"""
    id: int
    name: str
    role: Role
    is_alive: bool = True
    is_protected: bool = False  # Protected by guard
    votes_received: int = 0
    statements: List[str] = field(default_factory=list)
    vote_history: List[int] = field(default_factory=list)  # Who they voted for
    hallucination_marks: List[Dict[str, Any]] = field(default_factory=list)  # 幻觉标记

    def __str__(self):
        status = "Alive" if self.is_alive else "Dead"
        return f"Player {self.id} ({self.name}) - {self.role.value} - {status}"


@dataclass
class GameMetrics:
    """Quantified metrics for evaluating LLM performance"""
    # Deception metrics
    deception_attempts: int = 0  # Claims false identity
    successful_deceptions: int = 0  # Others believed the lie

    # Cooperation metrics
    team_alignment_score: float = 0.0  # How well they cooperate with team
    trust_given: int = 0  # Times they trusted others
    trust_violated: int = 0  # Times their trust was betrayed

    # Strategic reasoning
    optimal_vote_ratio: float = 0.0  # Votes aligned with game theory optimal
    information_usage_score: float = 0.0  # How well they use known info

    # Hallucination/consistency
    contradictions: int = 0  # Self-contradictory statements
    false_claims: int = 0  # Claims about events that didn't happen
    consistency_score: float = 1.0  # Overall consistency (0-1)

    # Communication
    total_statements: int = 0
    avg_statement_length: float = 0.0
    persuasiveness_score: float = 0.0  # How many followed their suggestions

    # Survival
    rounds_survived: int = 0
    final_outcome: str = ""  # "won", "lost", "eliminated"


@dataclass
class GameState:
    """Complete game state"""
    round_number: int = 0
    phase: Phase = Phase.NIGHT
    players: List[PlayerState] = field(default_factory=list)
    game_log: List[Dict[str, Any]] = field(default_factory=list)

    # Sheriff election
    sheriff_id: Optional[int] = None
    sheriff_candidates: List[int] = field(default_factory=list)

    # Night action results
    werewolf_target: Optional[int] = None
    seer_check: Optional[Tuple[int, Role]] = None
    witch_poison: Optional[int] = None
    witch_heal: bool = False
    guard_protect: Optional[int] = None

    # Day vote results
    current_votes: Dict[int, int] = field(default_factory=dict)  # voter_id -> target_id

    # Game theory metrics
    nash_equilibrium_score: float = 0.0
    werewolf_advantage: float = 0.0  # -1 to 1, negative favors villagers

    def log_event(self, event_type: str, data: Dict[str, Any]):
        """Log game events for analysis"""
        event = {
            "round": self.round_number,
            "phase": self.phase.value,
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data
        }
        self.game_log.append(event)

        # Notify observer if available
        if OBSERVER_ENABLED:
            try:
                observer = get_observer()
                observer.log_event(event_type, self.round_number, self.phase.value, data)
            except Exception as e:
                print(f"Observer error: {e}")

    def get_alive_players(self) -> List[PlayerState]:
        """Get all living players"""
        return [p for p in self.players if p.is_alive]

    def get_player_by_id(self, player_id: int) -> Optional[PlayerState]:
        """Get player by ID"""
        for p in self.players:
            if p.id == player_id:
                return p
        return None

    def check_win_condition(self) -> Optional[str]:
        """Check if game is over and who won"""
        alive = self.get_alive_players()
        # Exclude Judge from win condition
        alive_playing = [p for p in alive if p.role != Role.JUDGE]
        werewolves = [p for p in alive_playing if p.role in [Role.WEREWOLF, Role.WEREWOLF_KING]]
        villagers = [p for p in alive_playing if p.role not in [Role.WEREWOLF, Role.WEREWOLF_KING]]

        if len(werewolves) == 0:
            return "villagers"
        elif len(werewolves) >= len(villagers):
            return "werewolves"
        return None


class GameTheoryAnalyzer:
    """Analyzes game state using game theory principles"""

    @staticmethod
    def calculate_nash_equilibrium_score(game_state: GameState) -> float:
        """
        Calculate how close the current state is to Nash equilibrium.
        In Werewolf, Nash equilibrium involves:
        - Werewolves coordinating on strong targets
        - Villagers using information optimally
        - Special roles maximizing information gain
        """
        score = 0.0
        alive = game_state.get_alive_players()

        # Werewolf coordination score
        werewolves = [p for p in alive if p.role == Role.WEREWOLF]
        if len(werewolves) > 1 and game_state.werewolf_target:
            # Check if they targeted a high-value role (if known)
            target = game_state.get_player_by_id(game_state.werewolf_target)
            if target and target.role in [Role.SEER, Role.WITCH, Role.HUNTER]:
                score += 0.3

        # Information usage score (villagers voting based on seer info)
        if game_state.phase == Phase.DAY_VOTE:
            # Villagers should coordinate votes
            vote_concentration = GameTheoryAnalyzer._calculate_vote_concentration(game_state)
            score += vote_concentration * 0.4

        # Special role optimal play
        if game_state.seer_check:
            # Seer should check suspicious players
            score += 0.3

        return min(score, 1.0)

    @staticmethod
    def _calculate_vote_concentration(game_state: GameState) -> float:
        """Calculate how concentrated votes are (higher = better coordination)"""
        if not game_state.current_votes:
            return 0.0

        vote_counts = defaultdict(int)
        for target_id in game_state.current_votes.values():
            vote_counts[target_id] += 1

        if not vote_counts:
            return 0.0

        max_votes = max(vote_counts.values())
        total_votes = len(game_state.current_votes)

        return max_votes / total_votes if total_votes > 0 else 0.0

    @staticmethod
    def calculate_werewolf_advantage(game_state: GameState) -> float:
        """
        Calculate current werewolf advantage (-1 = villagers winning, 1 = werewolves winning)
        Based on: player ratio, information asymmetry, special roles alive
        """
        alive = game_state.get_alive_players()
        werewolves = [p for p in alive if p.role == Role.WEREWOLF]
        villagers = [p for p in alive if p.role != Role.WEREWOLF]

        if not werewolves:
            return -1.0
        if len(werewolves) >= len(villagers):
            return 1.0

        # Base ratio advantage
        ratio = len(werewolves) / len(alive)
        advantage = (ratio - 0.23) / 0.27  # Normalize around expected 3/13

        # Special roles still alive favor villagers
        special_roles = [p for p in villagers if p.role in [Role.SEER, Role.WITCH, Role.HUNTER]]
        advantage -= len(special_roles) * 0.1

        # Information asymmetry (werewolves know each other)
        advantage += 0.15

        return max(-1.0, min(1.0, advantage))

    @staticmethod
    def evaluate_vote_optimality(player: PlayerState, voted_for: int,
                                 game_state: GameState, known_info: Dict) -> float:
        """
        Evaluate how optimal a player's vote was (0-1)
        Based on available information and game theory
        """
        target = game_state.get_player_by_id(voted_for)
        if not target or not target.is_alive:
            return 0.0

        score = 0.5  # Baseline

        # If player is werewolf
        if player.role == Role.WEREWOLF:
            # Optimal to vote for non-werewolves, especially special roles
            if target.role != Role.WEREWOLF:
                score += 0.3
                if target.role in [Role.SEER, Role.WITCH, Role.HUNTER]:
                    score += 0.2
        else:
            # If player is villager and knows target is werewolf
            if "werewolves_known" in known_info:
                if voted_for in known_info["werewolves_known"]:
                    score += 0.5

            # Voting with majority is generally optimal for villagers
            vote_counts = defaultdict(int)
            for v_id in game_state.current_votes.values():
                vote_counts[v_id] += 1

            if vote_counts[voted_for] == max(vote_counts.values()):
                score += 0.2

        return min(score, 1.0)


class LLMAgent:
    """
    LLM-powered player agent
    This is an interface - you'll implement actual LLM API calls
    """

    def __init__(self, player_id: int, api_config: Dict[str, Any]):
        self.player_id = player_id
        self.api_config = api_config
        self.memory: List[str] = []  # Conversation memory
        self.known_info: Dict[str, Any] = {}  # What this player knows
        self.metrics = GameMetrics()

    def call_llm(self, prompt: str, system_prompt: str = "") -> str:
        """
        Call LLM API - configured for local LLM server

        Args:
            prompt: User prompt
            system_prompt: System instruction

        Returns:
            LLM response text
        """
        import requests

        api_base = self.api_config.get("api_base", "http://172.28.32.1:1234")
        model = self.api_config.get("model", "meta-llama-3.1-8b-instruct")

        # Prepare messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Call local LLM API (OpenAI-compatible format)
        try:
            response = requests.post(
                f"{api_base}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": self.api_config.get("temperature", 0.7),
                    "max_tokens": self.api_config.get("max_tokens", 500),
                    "stream": False
                },
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                print(f"[WARN] API error {response.status_code}: {response.text}")
                return f"[Error: API returned status {response.status_code}]"

        except requests.exceptions.Timeout:
            print(f"[WARN] API timeout for Player {self.player_id}")
            return "[Error: API timeout]"
        except Exception as e:
            print(f"[WARN] API error for Player {self.player_id}: {str(e)}")
            return f"[Error: {str(e)}]"

    def make_statement(self, context: str, game_state: GameState) -> str:
        """Generate a statement during day discussion"""
        system_prompt = self._build_system_prompt(game_state)
        prompt = f"""
Context: {context}

Known information:
{json.dumps(self.known_info, indent=2)}

Game state:
- Round: {game_state.round_number}
- Alive players: {[p.id for p in game_state.get_alive_players()]}
- Recent events: {game_state.game_log[-3:] if game_state.game_log else 'None'}

Make a statement to help your team win. Be strategic and consider what to reveal or conceal.
"""

        response = self.call_llm(prompt, system_prompt)
        self.memory.append(f"My statement: {response}")
        self.metrics.total_statements += 1
        self.metrics.avg_statement_length = (
            (self.metrics.avg_statement_length * (self.metrics.total_statements - 1) + len(response))
            / self.metrics.total_statements
        )

        return response

    def choose_vote_target(self, game_state: GameState) -> int:
        """Choose who to vote for elimination"""
        system_prompt = self._build_system_prompt(game_state)
        alive = game_state.get_alive_players()
        alive_ids = [p.id for p in alive if p.id != self.player_id and p.role != Role.JUDGE]

        prompt = f"""
It's time to vote for elimination.

Alive players (excluding you): {alive_ids}

Recent discussions:
{self._format_recent_statements(game_state)}

Known information:
{json.dumps(self.known_info, indent=2)}

Vote for the player ID you think should be eliminated.
Consider all available information and your role's objectives.

Respond with ONLY the player ID number.
"""

        response = self.call_llm(prompt, system_prompt)

        # Extract player ID from response
        try:
            target_id = int(response.strip())
            if target_id in alive_ids:
                return target_id
        except:
            pass

        # Fallback to random if parsing failed
        return random.choice(alive_ids)

    def night_action_werewolf(self, game_state: GameState) -> int:
        """Werewolf chooses target to kill"""
        system_prompt = self._build_system_prompt(game_state)
        alive = game_state.get_alive_players()
        non_werewolves = [p.id for p in alive
                         if p.role not in [Role.WEREWOLF, Role.WEREWOLF_KING, Role.JUDGE]]

        prompt = f"""
Night phase - choose a target to eliminate.

Other werewolves: {[p.id for p in alive if p.role == Role.WEREWOLF and p.id != self.player_id]}
Possible targets: {non_werewolves}

Consider:
- Who are likely special roles?
- Who is most threatening?
- What would be most strategic?

Respond with ONLY the target player ID.
"""

        response = self.call_llm(prompt, system_prompt)

        try:
            target_id = int(response.strip())
            if target_id in non_werewolves:
                return target_id
        except:
            pass

        return random.choice(non_werewolves)

    def night_action_seer(self, game_state: GameState) -> int:
        """Seer chooses player to investigate"""
        system_prompt = self._build_system_prompt(game_state)
        alive = game_state.get_alive_players()
        targets = [p.id for p in alive if p.id != self.player_id]

        prompt = f"""
Night phase - choose a player to investigate their role.

Alive players: {targets}

Previously checked: {self.known_info.get('checked_players', [])}

Who should you investigate for maximum information gain?

Respond with ONLY the player ID.
"""

        response = self.call_llm(prompt, system_prompt)

        try:
            target_id = int(response.strip())
            if target_id in targets:
                return target_id
        except:
            pass

        return random.choice(targets)

    def night_action_witch_heal(self, victim_id: int, game_state: GameState) -> bool:
        """Witch decides whether to use heal potion"""
        if self.known_info.get('heal_used', False):
            return False

        system_prompt = self._build_system_prompt(game_state)

        prompt = f"""
The werewolves targeted Player {victim_id} tonight.

You have ONE heal potion for the entire game. Should you use it now?

Consider:
- How valuable is this player?
- Should you save it for later?
- What's the strategic value?

Respond with ONLY 'yes' or 'no'.
"""

        response = self.call_llm(prompt, system_prompt).strip().lower()

        return response == 'yes'

    def night_action_witch_poison(self, game_state: GameState) -> Optional[int]:
        """Witch decides whether to use poison"""
        if self.known_info.get('poison_used', False):
            return None

        system_prompt = self._build_system_prompt(game_state)
        alive = game_state.get_alive_players()
        targets = [p.id for p in alive if p.id != self.player_id]

        prompt = f"""
Night phase - you have ONE poison for the entire game.

Should you use it tonight? If yes, on whom?

Alive players: {targets}

Respond with either:
- A player ID number to poison
- 'skip' to not use poison tonight
"""

        response = self.call_llm(prompt, system_prompt).strip().lower()

        if response == 'skip':
            return None

        try:
            target_id = int(response)
            if target_id in targets:
                return target_id
        except:
            pass

        return None

    def decide_sheriff_campaign(self, game_state: GameState) -> bool:
        """Decide whether to campaign for sheriff"""
        player = game_state.get_player_by_id(self.player_id)

        # Werewolves (including King) and Seer MUST campaign
        if player.role in [Role.WEREWOLF, Role.WEREWOLF_KING, Role.SEER]:
            return True  # Mandatory campaign

        # Others decide based on strategy
        system_prompt = self._build_system_prompt(game_state)

        prompt = f"""
It's the sheriff election phase. Should you campaign to become the sheriff?

The sheriff has:
- Double vote power during eliminations
- Can pass on their role if eliminated

Consider:
- Your role and whether revealing yourself is strategic
- Whether you can help your team more as sheriff
- Risk of drawing attention to yourself

Respond with ONLY 'yes' or 'no'.
"""

        response = self.call_llm(prompt, system_prompt).strip().lower()
        return response == 'yes'

    def make_sheriff_speech(self, game_state: GameState) -> str:
        """Make a campaign speech for sheriff"""
        system_prompt = self._build_system_prompt(game_state)
        player = game_state.get_player_by_id(self.player_id)

        # Count how many are campaigning
        campaigning_count = len([e for e in game_state.game_log
                               if e.get('event_type') == 'sheriff_campaign'])

        # Different strategies based on role
        if player.role in [Role.WEREWOLF, Role.WEREWOLF_KING]:
            strategy_hint = """You are a werewolf but MUST pretend to be a good person.
            Focus on: appearing trustworthy, logical reasoning, and promising to protect the village.
            NEVER reveal you are a werewolf. Consider claiming to be a villager or guard."""
        elif player.role == Role.SEER:
            strategy_hint = """You are the real Seer. You need the sheriff badge to protect yourself
            and guide the village. You can hint at your importance without fully revealing your role.
            Consider saying you have important information to share."""
        else:
            strategy_hint = """Focus on your commitment to finding werewolves and protecting the village.
            Be genuine and logical in your appeal."""

        prompt = f"""
You are campaigning for sheriff position. Make a PERSUASIVE speech to convince voters.

IMPORTANT: You are competing against {campaigning_count} other candidates.
You MUST convince the players who didn't campaign to vote for YOU.

{strategy_hint}

Sheriff benefits to emphasize:
- Double vote power to eliminate werewolves
- Leadership to guide village discussion
- Responsibility to use power wisely

Your speech should:
1. Explain why YOU specifically should be sheriff
2. Appeal to voters' desire for village safety
3. Stand out from other candidates
4. Be convincing and memorable

Make a strong 3-4 sentence campaign speech:
"""

        response = self.call_llm(prompt, system_prompt)
        self.memory.append(f"Sheriff speech: {response}")
        return response

    def vote_for_sheriff(self, candidates: List[int], game_state: GameState) -> int:
        """Vote for sheriff candidate based on speech persuasiveness"""
        system_prompt = self._build_system_prompt(game_state)
        player = game_state.get_player_by_id(self.player_id)

        # Get all campaign speeches
        speeches = {}
        for event in game_state.game_log:
            if event['event_type'] == 'sheriff_speech':
                pid = event['data']['player_id']
                if pid in candidates:
                    speeches[pid] = event['data']['speech']

        # Format speeches for analysis
        speeches_text = ""
        for cid in candidates:
            if cid in speeches:
                speeches_text += f"\n[Player {cid}]:\n{speeches[cid]}\n"

        # Different voting priorities based on role
        if player.role in [Role.WEREWOLF, Role.WEREWOLF_KING]:
            voting_strategy = """As a werewolf, vote for:
            1. Another werewolf if they campaigned (to give werewolves control)
            2. The candidate who seems LEAST likely to be the real Seer
            3. Someone who seems easily manipulated"""
        elif player.role == Role.VILLAGER:
            voting_strategy = """As a villager, vote for:
            1. The most trustworthy and logical candidate
            2. Someone who shows genuine concern for village safety
            3. A candidate who seems to have important information"""
        else:
            voting_strategy = """Vote for:
            1. The candidate most likely to help your team win
            2. Someone who demonstrates leadership and wisdom
            3. A player who seems genuinely committed to their promises"""

        prompt = f"""
You must vote for sheriff. Analyze each speech carefully for PERSUASIVENESS and TRUSTWORTHINESS.

Candidates and their speeches:
{speeches_text}

{voting_strategy}

Evaluate each speech for:
1. Logical reasoning and consistency
2. Commitment to protecting the village
3. Leadership qualities
4. Hidden motives or deception
5. Overall persuasiveness

IMPORTANT: Choose the candidate whose speech was MOST CONVINCING to you.
The sheriff will have double vote power, so this decision is critical.

Based on the speeches, vote for Player ID (number only):
"""

        response = self.call_llm(prompt, system_prompt)

        try:
            vote = int(response.strip())
            if vote in candidates:
                return vote
        except:
            pass

        # Fallback to random if parsing fails
        return random.choice(candidates)

    def night_action_guard(self, game_state: GameState) -> int:
        """Guard chooses player to protect"""
        system_prompt = self._build_system_prompt(game_state)
        alive = game_state.get_alive_players()
        targets = [p.id for p in alive]  # Can protect self
        last_protected = self.known_info.get('last_protected', None)

        # Cannot protect same person twice in a row
        if last_protected in targets:
            targets.remove(last_protected)

        prompt = f"""
Night phase - choose a player to protect from werewolves.

Available targets: {targets}
(Cannot protect same person twice in a row)

Who is most likely to be targeted?

Respond with ONLY the player ID.
"""

        response = self.call_llm(prompt, system_prompt)

        try:
            target_id = int(response.strip())
            if target_id in targets:
                return target_id
        except:
            pass

        return random.choice(targets)

    def _build_system_prompt(self, game_state: GameState) -> str:
        """Build system prompt with role information"""
        player = game_state.get_player_by_id(self.player_id)

        role_descriptions = {
            Role.WEREWOLF: "You are a WEREWOLF. Your goal is to eliminate all villagers. You know who the other werewolves are. Pretend to be a villager during discussions.",
            Role.WEREWOLF_KING: "You are the WEREWOLF KING. You are the leader of werewolves. When eliminated, you can take one non-werewolf player down with you. Lead your pack to victory.",
            Role.VILLAGER: "You are a VILLAGER. Your goal is to identify and eliminate all werewolves through discussion and voting.",
            Role.SEER: "You are the SEER. Each night, you can check one player's true role. Use this information wisely to help villagers win.",
            Role.WITCH: "You are the WITCH. You have one heal potion and one poison potion for the entire game. Use them strategically.",
            Role.HUNTER: "You are the HUNTER. When you die, you can take one player with you. Stay alive and identify werewolves.",
            Role.GUARD: "You are the GUARD. Each night, protect one player from werewolf attacks. Cannot protect the same player twice in a row.",
            Role.JUDGE: "You are the JUDGE. You observe the game and mark hallucinations. You do not participate in gameplay."
        }

        return f"""You are playing Werewolf, a social deduction game.

{role_descriptions[player.role]}

Game Rules:
- 13 players total
- Night phase: Special roles act, werewolves choose victim
- Day phase: Discussion then voting for elimination
- Werewolves win if they equal or outnumber villagers
- Villagers win if all werewolves are eliminated

Be strategic, logical, and help your team win!
"""

    def _format_recent_statements(self, game_state: GameState) -> str:
        """Format recent player statements"""
        recent_statements = []
        for event in game_state.game_log[-10:]:
            if event['event_type'] == 'player_statement':
                recent_statements.append(
                    f"Player {event['data']['player_id']}: {event['data']['statement']}"
                )
        return "\n".join(recent_statements) if recent_statements else "No recent statements"

    def update_known_info(self, key: str, value: Any):
        """Update player's known information"""
        self.known_info[key] = value

    def detect_deception(self, statement: str, actual_role: Role) -> bool:
        """Detect if statement contains deception about role"""
        # Simple keyword detection - can be enhanced
        role_claims = {
            "seer": Role.SEER,
            "witch": Role.WITCH,
            "hunter": Role.HUNTER,
            "guard": Role.GUARD,
            "villager": Role.VILLAGER
        }

        for keyword, claimed_role in role_claims.items():
            if keyword in statement.lower() and f"i am {keyword}" in statement.lower():
                if claimed_role != actual_role and actual_role != Role.VILLAGER:
                    self.metrics.deception_attempts += 1
                    return True

        return False


class WerewolfGame:
    """Main game controller"""

    def __init__(self, num_players: int = 13, llm_api_config: Dict[str, Any] = None):
        self.num_players = num_players
        self.llm_api_config = llm_api_config or {}
        self.game_state = GameState()
        self.agents: Dict[int, LLMAgent] = {}
        self.game_theory_analyzer = GameTheoryAnalyzer()
        self.all_metrics: Dict[int, GameMetrics] = {}

    def initialize_game(self):
        """Initialize game with roles and agents"""
        # New 13-player setup: 4 werewolves (1 king + 3 regular), 4 gods, 4 villagers, 1 judge
        roles = [
            Role.WEREWOLF_KING,  # 狼王
            Role.WEREWOLF, Role.WEREWOLF, Role.WEREWOLF,  # 3 小狼
            Role.SEER,
            Role.WITCH,
            Role.HUNTER,
            Role.GUARD,
            Role.VILLAGER, Role.VILLAGER, Role.VILLAGER, Role.VILLAGER,  # 4 villagers
            Role.JUDGE  # Judge不参与游戏，用于标记幻觉
        ]

        # Judge不打乱，始终是最后一个
        game_roles = roles[:-1]
        random.shuffle(game_roles)
        roles = game_roles + [Role.JUDGE]

        # Create players
        for i in range(self.num_players):
            player = PlayerState(
                id=i,
                name=f"Player_{i}",
                role=roles[i]
            )
            self.game_state.players.append(player)

            # Create LLM agent
            agent = LLMAgent(i, self.llm_api_config)
            self.agents[i] = agent
            self.all_metrics[i] = agent.metrics

            # Werewolves know each other
            if player.role in [Role.WEREWOLF, Role.WEREWOLF_KING]:
                werewolf_ids = [p.id for p in self.game_state.players
                              if p.role in [Role.WEREWOLF, Role.WEREWOLF_KING]]
                agent.update_known_info('werewolf_teammates', werewolf_ids)

            # Judge is special - doesn't participate in game
            if player.role == Role.JUDGE:
                agent.update_known_info('is_judge', True)

        self.game_state.log_event('game_start', {
            'players': [{'id': p.id, 'role': p.role.value} for p in self.game_state.players]
        })

        print("Game Initialized!")
        print(f"Players: {self.num_players}")
        print(f"Werewolves: {len([p for p in self.game_state.players if p.role in [Role.WEREWOLF, Role.WEREWOLF_KING]])}")

    def run_night_phase(self):
        """Execute night phase actions"""
        print(f"\n[NIGHT] Night {self.game_state.round_number}")
        self.game_state.phase = Phase.NIGHT

        # Reset night actions
        self.game_state.werewolf_target = None
        self.game_state.seer_check = None
        self.game_state.witch_poison = None
        self.game_state.witch_heal = False
        self.game_state.guard_protect = None

        # Reset protection
        for player in self.game_state.players:
            player.is_protected = False

        # Werewolf action (include Werewolf King)
        werewolves = [p for p in self.game_state.get_alive_players()
                     if p.role in [Role.WEREWOLF, Role.WEREWOLF_KING]]
        if werewolves:
            # First werewolf decides (could be enhanced to voting among werewolves)
            werewolf_agent = self.agents[werewolves[0].id]
            target = werewolf_agent.night_action_werewolf(self.game_state)
            self.game_state.werewolf_target = target
            print(f"  [WOLF] Werewolves target Player {target}")

        # Guard action
        guard = next((p for p in self.game_state.get_alive_players() if p.role == Role.GUARD), None)
        if guard:
            guard_agent = self.agents[guard.id]
            protected = guard_agent.night_action_guard(self.game_state)
            self.game_state.guard_protect = protected
            target_player = self.game_state.get_player_by_id(protected)
            if target_player:
                target_player.is_protected = True
            guard_agent.update_known_info('last_protected', protected)
            print(f"  [GUARD] Guard protects Player {protected}")

        # Seer action
        seer = next((p for p in self.game_state.get_alive_players() if p.role == Role.SEER), None)
        if seer:
            seer_agent = self.agents[seer.id]
            check_target = seer_agent.night_action_seer(self.game_state)
            checked_player = self.game_state.get_player_by_id(check_target)
            if checked_player:
                self.game_state.seer_check = (check_target, checked_player.role)

                # Update seer's knowledge
                checked_list = seer_agent.known_info.get('checked_players', [])
                checked_list.append({
                    'player_id': check_target,
                    'role': checked_player.role.value
                })
                seer_agent.update_known_info('checked_players', checked_list)

                if checked_player.role == Role.WEREWOLF:
                    werewolves_known = seer_agent.known_info.get('werewolves_known', [])
                    werewolves_known.append(check_target)
                    seer_agent.update_known_info('werewolves_known', werewolves_known)

                print(f"  [SEER] Seer checks Player {check_target} - {checked_player.role.value}")

        # Determine werewolf victim
        victim_id = self.game_state.werewolf_target
        victim_saved = False

        if victim_id:
            victim = self.game_state.get_player_by_id(victim_id)
            if victim and victim.is_protected:
                victim_saved = True
                print(f"   Player {victim_id} was protected!")

        # Witch action - heal
        witch = next((p for p in self.game_state.get_alive_players() if p.role == Role.WITCH), None)
        if witch and victim_id and not victim_saved:
            witch_agent = self.agents[witch.id]
            if witch_agent.night_action_witch_heal(victim_id, self.game_state):
                self.game_state.witch_heal = True
                victim_saved = True
                witch_agent.update_known_info('heal_used', True)
                print(f"   Witch heals Player {victim_id}")

        # Witch action - poison
        if witch:
            witch_agent = self.agents[witch.id]
            poison_target = witch_agent.night_action_witch_poison(self.game_state)
            if poison_target:
                self.game_state.witch_poison = poison_target
                witch_agent.update_known_info('poison_used', True)
                print(f"   Witch poisons Player {poison_target}")

        # Apply deaths
        deaths = []

        # Werewolf kill
        if victim_id and not victim_saved:
            victim = self.game_state.get_player_by_id(victim_id)
            if victim:
                victim.is_alive = False
                deaths.append(victim_id)

        # Witch poison
        if self.game_state.witch_poison:
            poisoned = self.game_state.get_player_by_id(self.game_state.witch_poison)
            if poisoned and poisoned.is_alive:
                poisoned.is_alive = False
                deaths.append(self.game_state.witch_poison)

        # Log deaths
        if deaths:
            self.game_state.log_event('night_deaths', {'player_ids': deaths})
            print(f"   Deaths: {deaths}")
        else:
            print(f"  [OK] No one died tonight")

        # Hunter revenge
        for dead_id in deaths:
            dead_player = self.game_state.get_player_by_id(dead_id)
            if dead_player and dead_player.role == Role.HUNTER:
                hunter_agent = self.agents[dead_id]
                alive_ids = [p.id for p in self.game_state.get_alive_players()]
                if alive_ids:
                    # Hunter chooses someone to take down
                    revenge_target = random.choice(alive_ids)  # Simplified
                    revenge_player = self.game_state.get_player_by_id(revenge_target)
                    if revenge_player:
                        revenge_player.is_alive = False
                        print(f"  [TARGET] Hunter takes Player {revenge_target} down!")
                        self.game_state.log_event('hunter_revenge', {'target': revenge_target})

        return deaths

    def run_day_discussion(self):
        """Execute day discussion phase"""
        print(f"\n[DAY] Day {self.game_state.round_number} - Discussion")
        self.game_state.phase = Phase.DAY_DISCUSSION

        alive_players = self.game_state.get_alive_players()

        # Each player makes a statement (except Judge)
        for player in alive_players:
            if player.role == Role.JUDGE:  # Judge doesn't participate
                continue
            agent = self.agents[player.id]
            statement = agent.make_statement("Day discussion phase", self.game_state)

            player.statements.append(statement)

            self.game_state.log_event('player_statement', {
                'player_id': player.id,
                'statement': statement,
                'round': self.game_state.round_number
            })

            # Check for deception
            if agent.detect_deception(statement, player.role):
                print(f"  [MASK] Player {player.id} may be deceiving!")

            # 使用安全的输出方式，避免 Windows GBK 编码问题
            try:
                print(f"  🗣️ Player {player.id}: {statement}")
            except UnicodeEncodeError:
                print(f"  [SPEECH] Player {player.id}: {statement}")

    def run_sheriff_election(self):
        """Execute sheriff election phase"""
        print(f"\n[SHERIFF ELECTION] - ")
        print("="*70)
        print("[LIST] RULES: Werewolves and Seer MUST campaign!")
        print("")
        print("="*70)

        alive_players = self.game_state.get_alive_players()

        # Track mandatory candidates
        mandatory_roles = {
            Role.WEREWOLF: "Werewolf (must campaign)",
            Role.WEREWOLF_KING: "Werewolf King (must campaign)",
            Role.SEER: "Seer (must campaign)"
        }

        # Phase 1: Campaign decision (exclude Judge)
        candidates = []
        mandatory_count = 0

        for player in alive_players:
            if player.role == Role.JUDGE:  # Judge doesn't participate
                continue

            agent = self.agents[player.id]
            is_mandatory = player.role in mandatory_roles

            if agent.decide_sheriff_campaign(self.game_state):
                candidates.append(player.id)
                if is_mandatory:
                    print(f"   Player {player.id} campaigns for sheriff [MANDATORY - {player.role.value}]")
                    mandatory_count += 1
                    # Log this for tracking
                    self.game_state.log_event('sheriff_campaign', {
                        'player_id': player.id,
                        'mandatory': True,
                        'role': player.role.value
                    })
                else:
                    print(f"   Player {player.id} campaigns for sheriff [voluntary]")
                    self.game_state.log_event('sheriff_campaign', {
                        'player_id': player.id,
                        'mandatory': False,
                        'role': player.role.value
                    })

        if not candidates:
            print("  [WARN] No candidates, skipping election")
            return

        if len(candidates) == 1:
            self.game_state.sheriff_id = candidates[0]
            print(f"  [SHERIFF] Player {candidates[0]} becomes sheriff (unopposed)")
            self.game_state.log_event('sheriff_elected', {
                'sheriff_id': candidates[0],
                'unopposed': True
            })
            return

        # Phase 2: Campaign speeches
        print(f"\n  [TALK] Campaign Speeches:")
        for candidate_id in candidates:
            agent = self.agents[candidate_id]
            speech = agent.make_sheriff_speech(self.game_state)
            # 使用安全的输出方式，避免 Windows GBK 编码问题
            try:
                print(f"    🗣️ Player {candidate_id}: {speech}")
            except UnicodeEncodeError:
                print(f"    [SPEECH] Player {candidate_id}: {speech}")

            self.game_state.log_event('sheriff_speech', {
                'player_id': candidate_id,
                'speech': speech
            })

        # Phase 3: Voting
        print(f"\n  [VOTE] Sheriff Voting:")
        sheriff_votes = defaultdict(int)

        for player in alive_players:
            if player.role == Role.JUDGE:  # Judge doesn't vote
                continue
            if player.id not in candidates:  # Candidates can't vote
                agent = self.agents[player.id]
                vote = agent.vote_for_sheriff(candidates, self.game_state)
                sheriff_votes[vote] += 1
                print(f"    Player {player.id} votes for Player {vote}")

        # Determine winner
        if sheriff_votes:
            sheriff_id = max(sheriff_votes, key=sheriff_votes.get)
            self.game_state.sheriff_id = sheriff_id
            print(f"\n  [SHERIFF] Player {sheriff_id} elected as sheriff ({sheriff_votes[sheriff_id]} votes)")

            self.game_state.log_event('sheriff_elected', {
                'sheriff_id': sheriff_id,
                'votes': dict(sheriff_votes),
                'candidates': candidates
            })

    def run_day_vote(self):
        """Execute day voting phase"""
        print(f"\n[VOTE] Day {self.game_state.round_number} - Voting")
        self.game_state.phase = Phase.DAY_VOTE
        self.game_state.current_votes = {}

        alive_players = self.game_state.get_alive_players()

        # Collect votes (except Judge)
        for player in alive_players:
            if player.role == Role.JUDGE:  # Judge doesn't vote
                continue
            agent = self.agents[player.id]
            vote_target = agent.choose_vote_target(self.game_state)

            self.game_state.current_votes[player.id] = vote_target
            player.vote_history.append(vote_target)

            # Evaluate vote optimality
            optimality = self.game_theory_analyzer.evaluate_vote_optimality(
                player, vote_target, self.game_state, agent.known_info
            )

            # Update metrics
            current_optimal = agent.metrics.optimal_vote_ratio
            total_votes = len(player.vote_history)
            agent.metrics.optimal_vote_ratio = (
                (current_optimal * (total_votes - 1) + optimality) / total_votes
            )

            print(f"  Player {player.id} votes for Player {vote_target}")

        # Count votes (sheriff gets double vote)
        vote_counts = defaultdict(int)
        for voter_id, target in self.game_state.current_votes.items():
            if voter_id == self.game_state.sheriff_id:
                vote_counts[target] += 2  # Sheriff double vote
                print(f"  [SHERIFF] Sheriff's vote counts double!")
            else:
                vote_counts[target] += 1

        # Find player with most votes
        if vote_counts:
            eliminated_id = max(vote_counts, key=vote_counts.get)
            eliminated_player = self.game_state.get_player_by_id(eliminated_id)

            if eliminated_player:
                eliminated_player.is_alive = False
                print(f"   Player {eliminated_id} ({eliminated_player.role.value}) is eliminated!")

                self.game_state.log_event('day_elimination', {
                    'player_id': eliminated_id,
                    'role': eliminated_player.role.value,
                    'votes': vote_counts[eliminated_id]
                })

                # Sheriff succession
                if eliminated_id == self.game_state.sheriff_id:
                    print(f"  [SHERIFF] Sheriff eliminated - succession needed")
                    # Simple succession: pass to a random alive player
                    alive_ids = [p.id for p in self.game_state.get_alive_players()]
                    if alive_ids:
                        new_sheriff = random.choice(alive_ids)
                        self.game_state.sheriff_id = new_sheriff
                        print(f"  [SHERIFF] Player {new_sheriff} becomes new sheriff")

                # Hunter revenge
                if eliminated_player.role == Role.HUNTER:
                    alive_ids = [p.id for p in self.game_state.get_alive_players()]
                    if alive_ids:
                        revenge_target = random.choice(alive_ids)
                        revenge_player = self.game_state.get_player_by_id(revenge_target)
                        if revenge_player:
                            revenge_player.is_alive = False
                            print(f"  [TARGET] Hunter takes Player {revenge_target} down!")

                # Werewolf King revenge (狼王带人)
                if eliminated_player.role == Role.WEREWOLF_KING:
                    alive_ids = [p.id for p in self.game_state.get_alive_players()
                                if p.role not in [Role.WEREWOLF, Role.WEREWOLF_KING, Role.JUDGE]]
                    if alive_ids:
                        king_target = random.choice(alive_ids)
                        king_victim = self.game_state.get_player_by_id(king_target)
                        if king_victim:
                            king_victim.is_alive = False
                            print(f"  [KING] Werewolf King takes Player {king_target} down!")

    def run_round(self):
        """Run one complete round"""
        self.game_state.round_number += 1

        # Night phase
        self.run_night_phase()

        # Check win condition
        winner = self.game_state.check_win_condition()
        if winner:
            return winner

        # Day phase
        self.run_day_discussion()
        self.run_day_vote()

        # Update metrics
        self.update_game_theory_metrics()

        # Check win condition
        winner = self.game_state.check_win_condition()
        return winner

    def update_game_theory_metrics(self):
        """Update game theory analysis metrics"""
        self.game_state.nash_equilibrium_score = (
            self.game_theory_analyzer.calculate_nash_equilibrium_score(self.game_state)
        )
        self.game_state.werewolf_advantage = (
            self.game_theory_analyzer.calculate_werewolf_advantage(self.game_state)
        )

    def play_game(self) -> Dict[str, Any]:
        """Play complete game until win condition"""
        self.initialize_game()

        # Run sheriff election on Day 1
        print("\n" + "="*70)
        print("DAY 1 - SHERIFF ELECTION")
        print("="*70)
        self.run_sheriff_election()

        winner = None
        max_rounds = 20  # Safety limit

        while not winner and self.game_state.round_number < max_rounds:
            winner = self.run_round()

        # Finalize metrics
        self.finalize_metrics(winner)

        print(f"\n[WIN] Game Over! Winner: {winner}")
        print(f"Total rounds: {self.game_state.round_number}")

        # Return comprehensive results
        return self.generate_game_report()

    def finalize_metrics(self, winner: Optional[str]):
        """Finalize all player metrics"""
        for player in self.game_state.players:
            agent = self.agents[player.id]

            # Update survival metrics
            agent.metrics.rounds_survived = self.game_state.round_number if player.is_alive else len([
                e for e in self.game_state.game_log
                if e['event_type'] in ['night_deaths', 'day_elimination']
                and player.id in e['data'].get('player_ids', [e['data'].get('player_id')])
            ])

            # Determine outcome
            if winner:
                player_team = 'werewolves' if player.role == Role.WEREWOLF else 'villagers'
                if player_team == winner:
                    agent.metrics.final_outcome = 'won'
                else:
                    agent.metrics.final_outcome = 'lost'

            # Calculate consistency score based on contradictions
            if agent.metrics.total_statements > 0:
                agent.metrics.consistency_score = max(0, 1 - (
                    agent.metrics.contradictions / agent.metrics.total_statements
                ))

    def generate_game_report(self) -> Dict[str, Any]:
        """Generate comprehensive game analysis report"""
        timestamp = datetime.now()

        report = {
            'timestamp': timestamp.isoformat(),
            'game_id': f"game_{timestamp.strftime('%Y%m%d_%H%M%S')}",
            'game_summary': {
                'total_rounds': self.game_state.round_number,
                'winner': self.game_state.check_win_condition(),
                'final_nash_score': self.game_state.nash_equilibrium_score,
                'final_werewolf_advantage': self.game_state.werewolf_advantage,
                'sheriff_id': self.game_state.sheriff_id,
                'start_time': self.game_state.game_log[0]['timestamp'] if self.game_state.game_log else timestamp.isoformat(),
                'end_time': timestamp.isoformat()
            },
            'player_metrics': {},
            'game_theory_analysis': self.analyze_game_theory(),
            'event_log': self.game_state.game_log,
            'quantified_metrics': self.calculate_aggregate_metrics()
        }

        # Add per-player metrics
        for player in self.game_state.players:
            agent = self.agents[player.id]
            report['player_metrics'][player.id] = {
                'role': player.role.value,
                'final_status': 'alive' if player.is_alive else 'dead',
                'metrics': {
                    'deception_attempts': agent.metrics.deception_attempts,
                    'successful_deceptions': agent.metrics.successful_deceptions,
                    'team_alignment_score': agent.metrics.team_alignment_score,
                    'optimal_vote_ratio': agent.metrics.optimal_vote_ratio,
                    'contradictions': agent.metrics.contradictions,
                    'consistency_score': agent.metrics.consistency_score,
                    'total_statements': agent.metrics.total_statements,
                    'avg_statement_length': agent.metrics.avg_statement_length,
                    'rounds_survived': agent.metrics.rounds_survived,
                    'final_outcome': agent.metrics.final_outcome
                }
            }

        return report

    def analyze_game_theory(self) -> Dict[str, Any]:
        """Perform game theory analysis"""
        return {
            'nash_equilibrium_evolution': self._extract_metric_evolution('nash_equilibrium'),
            'werewolf_advantage_evolution': self._extract_metric_evolution('werewolf_advantage'),
            'vote_concentration_by_round': self._analyze_vote_patterns(),
            'information_cascade_detected': self._detect_information_cascades()
        }

    def _extract_metric_evolution(self, metric_name: str) -> List[float]:
        """Extract how a metric evolved over the game"""
        # Simplified - would track these during game
        return [self.game_state.nash_equilibrium_score]

    def _analyze_vote_patterns(self) -> Dict[int, float]:
        """Analyze voting patterns by round"""
        patterns = {}
        current_round = None

        for event in self.game_state.game_log:
            if event['event_type'] == 'day_elimination':
                round_num = event['round']
                # Calculate concentration for this round
                # Simplified implementation
                patterns[round_num] = 0.5

        return patterns

    def _detect_information_cascades(self) -> bool:
        """Detect if information cascades occurred (players following others)"""
        # Simplified - would analyze vote patterns
        return False

    def calculate_aggregate_metrics(self) -> Dict[str, float]:
        """Calculate aggregate metrics across all players"""
        all_agents = list(self.agents.values())

        return {
            'avg_deception_rate': sum(a.metrics.deception_attempts for a in all_agents) / len(all_agents),
            'avg_consistency_score': sum(a.metrics.consistency_score for a in all_agents) / len(all_agents),
            'avg_optimal_vote_ratio': sum(a.metrics.optimal_vote_ratio for a in all_agents) / len(all_agents),
            'total_contradictions': sum(a.metrics.contradictions for a in all_agents),
            'total_statements': sum(a.metrics.total_statements for a in all_agents),
            'werewolf_win_rate': 1.0 if self.game_state.check_win_condition() == 'werewolves' else 0.0
        }

    def save_report(self, filename: str = 'game_report.json'):
        """Save game report to file"""
        report = self.generate_game_report()
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n[STATS] Report saved to {filename}")


def main():
    """Example usage"""
    # Configure your local LLM API
    llm_config = {
        'api_base': 'http://172.28.32.1:1234',
        'model': 'meta-llama-3.1-8b-instruct',
        'temperature': 0.7,
        'max_tokens': 500
    }

    print(" Starting Werewolf Game with LLM Agents")
    print(f"API: {llm_config['api_base']}")
    print(f"Model: {llm_config['model']}")
    print("="*60)

    # Create and run game
    game = WerewolfGame(num_players=13, llm_api_config=llm_config)
    results = game.play_game()

    # Save detailed report
    game.save_report('werewolf_game_report.json')

    # Print summary
    print("\n" + "="*60)
    print("GAME ANALYSIS SUMMARY")
    print("="*60)
    print(f"Winner: {results['game_summary']['winner']}")
    print(f"Rounds: {results['game_summary']['total_rounds']}")
    print(f"\nAggregate Metrics:")
    for metric, value in results['quantified_metrics'].items():
        print(f"  {metric}: {value:.3f}")


if __name__ == '__main__':
    main()
