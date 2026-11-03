"""ComputerGame: the rules of one game against an engine. Knows nothing about the user interface.

Whose turn it is, what the user may do, the chess clock, the result and which engine
replies are still wanted (request ids). VsComputerMode drives it.
"""

import datetime
import time

import chess

from . import strings as S
from .clock import ChessClock
from .model import material_balance, outcome_text

# Commands (see Mode.allows) that stay available in a game against the computer.
# Never "navigate": browsing earlier moves would look like taking moves back. Only Board mode
# allows it; a finished game is reviewed there (Open in Board Mode).
ALLOWED_DURING_GAME = set()
ALLOWED_AFTER_GAME = {"edit_comment"}


class ComputerGame:
    def __init__(self, user_color, engine_name, level, minutes=30, now=time.monotonic):
        self.user_color = user_color
        self.engine_color = not user_color
        self.engine_label = f"{engine_name} {level.label}".strip()
        self.level = level
        self.seconds = round(minutes * 60)
        self.clock = ChessClock(self.seconds, self.seconds, now)
        self.started = False     # the clock starts with the first move
        self.result = None       # "1-0", "0-1", "1/2-1/2" or "*" once the game is over
        self.termination = None  # PGN Termination header
        self.end_text = None     # status line text once the game is over
        self.request_id = 0

    # --- Queries ----------------------------------------------------------

    @property
    def over(self):
        return self.result is not None

    def player_name(self, color):
        return S.VS_YOU if color == self.user_color else self.engine_label

    def is_engine_turn(self, board):
        return not self.over and board.turn == self.engine_color

    def can_move(self, board, color, at_end):
        """The user may move only their own pieces, on their turn, from the last position."""
        return not self.over and at_end and color == self.user_color == board.turn

    def allows(self, command):
        return command in (ALLOWED_AFTER_GAME if self.over else ALLOWED_DURING_GAME)

    def status_text(self, board):
        if self.over:
            return self.end_text
        if board.turn == self.user_color:
            text = S.VS_YOUR_MOVE
            if board.is_check():
                text += " · " + S.STATUS_CHECK
            return text
        return S.VS_THINKING

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
        headers["Event"] = S.VS_EVENT
        headers["Site"] = S.UNKNOWN
        headers["Date"] = datetime.date.today().strftime("%Y.%m.%d")
        headers["Round"] = S.UNKNOWN
        headers["White"] = self.player_name(chess.WHITE)
        headers["Black"] = self.player_name(chess.BLACK)
        headers["Result"] = "*"
        headers["TimeControl"] = str(self.seconds)
        if self.level.elo is not None:
            headers["WhiteElo" if self.engine_color == chess.WHITE else "BlackElo"] = str(self.level.elo)

    def write_result(self, headers):
        headers["Result"] = self.result
        headers["Termination"] = self.termination

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
            self._finish(outcome.result(), "normal", outcome_text(outcome))
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
            self._finish("1/2-1/2", "time forfeit", S.VS_TIMEOUT_DRAW)
        else:
            text = S.VS_TIMEOUT_YOU_WIN if winner == self.user_color else S.VS_TIMEOUT_YOU_LOSE
            self._finish(_win(winner), "time forfeit", text.format(engine=self.engine_label))
        return True

    def resign(self):
        if not self.over:
            self._finish(_win(self.engine_color), "normal", S.VS_RESIGNED.format(engine=self.engine_label))

    def engine_failed(self, error):
        if not self.over:
            self._finish("*", "abandoned", S.VS_ENGINE_ERROR.format(error=error))

    def _finish(self, result, termination, text):
        self.clock.stop()
        self.result, self.termination, self.end_text = result, termination, text
        self.request_id += 1   # any engine reply still on its way is no longer wanted

    # --- Engine requests --------------------------------------------------

    def new_request(self):
        self.request_id += 1
        return self.request_id

    def is_current(self, request_id):
        return not self.over and request_id == self.request_id


def _win(color):
    return "1-0" if color == chess.WHITE else "0-1"
