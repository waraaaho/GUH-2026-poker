import random

from card_utils import Card, evaluate, full_deck
from game_state import GameStateView
from player_action import PlayerAction


class Model:
    """
    Monte Carlo Poker Bot for No-Limit Texas Hold'em.

    Estimates hand equity against active opponents via random rollouts,
    then makes mathematically sound betting decisions based on:
    - Hand equity vs fair share of the pot (1 / num_players)
    - Pot odds (call_amount / (pot + call_amount))
    - Bet sizing relative to pot and current street
    """

    def __init__(self, seed: int | None = None):
        self.hand: list[Card] = []
        self.player_id: int | None = None
        self.rng = random.Random(seed)

    def seed(self, hand: list[Card], player_id: int):
        """
        Called once before each hand: stores your 2 hole cards and your seat index.
        """
        self.hand = hand
        self.player_id = player_id

    def run(
        self, actions: list[PlayerAction], game_state: GameStateView
    ) -> PlayerAction:
        """
        Called on your turn. Evaluates game state and returns a legal PlayerAction.
        """
        me = self.player_id
        opponents = max(1, len(game_state.players_in_hand) - 1)
        board = list(game_state.board)

        # Calculate Monte Carlo equity
        equity = self._estimate_equity(board, opponents, game_state.street)
        fair_share = 1.0 / (opponents + 1)
        call_amount = game_state.call_amount
        pot_odds = game_state.pot_odds
        pot = game_state.pot

        # 1. Free to check (call_amount == 0)
        if call_amount == 0:
            # Value bet/raise if equity is significantly above fair share
            if equity > 1.35 * fair_share and equity >= 0.52 and game_state.can_raise:
                pct = 0.85 if equity > 0.80 else 0.60
                bet_amount = max(int(pct * pot), game_state.big_blind)
                target = game_state.current_bet + bet_amount
                return self._safe_raise(game_state, target)

            # Otherwise take the free check
            return PlayerAction.call(me)

        # 2. Facing a bet / raise (call_amount > 0)
        # Value re-raise with strong hands
        if equity > 1.60 * fair_share and equity >= 0.68 and game_state.can_raise:
            if equity > 0.82:
                target = game_state.current_bet + max(game_state.last_raise, int(0.80 * pot))
            else:
                target = game_state.current_bet + max(game_state.last_raise, int(0.50 * pot))
            return self._safe_raise(game_state, target)

        # Calling vs Folding: call if our equity covers the required pot odds
        if equity >= pot_odds:
            return PlayerAction.call(me)

        # Otherwise fold
        return PlayerAction.fold(me)

    def _estimate_equity(
        self, board: list[Card], opponents: int, street: str
    ) -> float:
        """
        Monte Carlo rollout: simulate future board runouts and random opponent hands
        to estimate win + tie probability.
        """
        # Dynamic sample count per street to balance precision and speed
        if street == "preflop":
            samples = 60
        elif street == "flop":
            samples = 80
        elif street == "turn":
            samples = 100
        else:  # river
            samples = 120

        known = set(self.hand + board)
        unseen = [c for c in full_deck() if c not in known]
        missing_board = 5 - len(board)
        needed = missing_board + 2 * opponents

        if len(unseen) < needed:
            return 0.5

        won = 0.0
        for _ in range(samples):
            dealt = self.rng.sample(unseen, needed)
            full_board = board + dealt[:missing_board]
            my_eval = evaluate(self.hand + full_board)

            opp_cards = dealt[missing_board:]
            opp_evals = [
                evaluate(opp_cards[2 * i : 2 * i + 2] + full_board)
                for i in range(opponents)
            ]
            best_opp = max(opp_evals)

            if my_eval > best_opp:
                won += 1.0
            elif my_eval == best_opp:
                won += 1.0 / (1 + opp_evals.count(best_opp))

        return won / samples

    def _safe_raise(self, game_state: GameStateView, target: int) -> PlayerAction:
        """
        Clamps the raise target within legal min_raise_to and max_raise_to.
        Falls back to call if raising is not permitted.
        """
        if not game_state.can_raise:
            return PlayerAction.call(self.player_id)
        low, high = game_state.raise_range
        total = min(high, max(low, target))
        return PlayerAction.raise_to(self.player_id, total)

    def end_game(
        self, actions: list[PlayerAction], game_state: GameStateView
    ):
        """
        Called after every hand.
        """
        pass
