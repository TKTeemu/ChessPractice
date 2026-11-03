"""ComputerGame: the rules of one game against an engine. Knows nothing about the user interface.

On top of EngineGame: the chess clock, the score text, the time control headers and the
result by time or resignation. VsComputerMode drives it.
"""

import time

import chess

from . import strings as S
from .clock import ChessClock
from .commands import EDIT_COMMENT
from .engine_game import EngineGame
from .model import material_balance, outcome_text


class ComputerGame(EngineGame):
    EVENT = S.VS_EVENT
    # Never NAVIGATE: browsing earlier moves would look like taking moves back. Only Board mode
    # allows it; a finished game is reviewed there (Open in Board Mode).
    ALLOWED_DURING_GAME = frozenset()
    ALLOWED_AFTER_GAME = frozenset({EDIT_COMMENT})

    def __init__(self, user_color, engine_name, level, minutes=30, now=time.monotonic):
        super().__init__(user_color, f"{engine_name} {level.label}".strip())
        self.level = level
        self.seconds = round(minutes * 60)
        self.clock = ChessClock(self.seconds, self.seconds, now)
        self.started = False     # the clock starts with the first move

    # --- Queries ----------------------------------------------------------

    def score_text(self, board):
        """Material from the user's point of view: "Material: you +3", "… −2" or "… even"."""
        balance = material_balance(board, self.user_color)
        if balance > 0:
            return S.VS_SCORE_AHEAD.format(points=balance)
        if balance < 0:
            return S.VS_SCORE_BEHIND.format(points=-balance)
        return S.VS_SCORE_EVEN

    # --- Headers ----------------------------------------------------------

    def write_headers(self, headers):
        super().write_headers(headers)
        headers["TimeControl"] = str(self.seconds)
        if self.level.elo is not None:
            headers["WhiteElo" if self.computer_color == chess.WHITE else "BlackElo"] = str(self.level.elo)

    # --- Events -----------------------------------------------------------

    def move_played(self, board):
        """Call after each move with the board after it. Returns the mover's remaining
        seconds (for the [%clk] comment); ends the game if the position is final."""
        mover = not board.turn
        left = self.clock.remaining(mover)
        if self.started:
            self.clock.switch()
        else:
            self.started = True
            self.clock.start(board.turn)
        outcome = board.outcome(claim_draw=True)
        if outcome is not None:
            self._finish(outcome.result(), outcome_text(outcome), "normal")
        return left

    def check_time(self, board):
        """Call regularly. Returns True if a flag fell just now (the game is then over)."""
        if self.over:
            return False
        loser = self.clock.flagged()
        if loser is None:
            return False
        winner = not loser
        if board.has_insufficient_material(winner):
            self._finish("1/2-1/2", S.VS_TIMEOUT_DRAW, "time forfeit")
        else:
            text = S.VS_TIMEOUT_YOU_WIN if winner == self.user_color else S.VS_TIMEOUT_YOU_LOSE
            self._finish(_win(winner), text.format(engine=self.engine_label), "time forfeit")
        return True

    def resign(self):
        if not self.over:
            self._finish(_win(self.computer_color), S.VS_RESIGNED.format(engine=self.engine_label), "normal")

    def _finish(self, result, text, termination=None):
        self.clock.stop()
        super()._finish(result, text, termination)


def _win(color):
    return "1-0" if color == chess.WHITE else "0-1"
