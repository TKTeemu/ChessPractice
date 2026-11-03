"""EngineGame: the shared rules of a game in which the user plays one side and the computer
the other. Knows nothing about the user interface.

Whose turn it is, what the user may do, the result, the common PGN headers and which
computer replies are still wanted (request ids). ComputerGame and LearningGame add what
is different about them; EngineGameMode drives them.
"""

import datetime

import chess

from . import strings as S


class EngineGame:
    EVENT = ""                      # PGN Event header
    ALLOWED_DURING_GAME = frozenset()   # commands (app/commands.py) while the game runs …
    ALLOWED_AFTER_GAME = frozenset()    # … and after it has ended

    def __init__(self, user_color, engine_label):
        self.user_color = user_color
        self.computer_color = not user_color
        self.engine_label = engine_label
        self.result = None       # "1-0", "0-1", "1/2-1/2" or "*" once the game is over
        self.end_text = None     # status line text once the game is over
        self.termination = None  # PGN Termination header, if any
        self.request_id = 0

    # --- Queries ----------------------------------------------------------

    @property
    def over(self):
        return self.result is not None

    def player_name(self, color):
        return S.VS_YOU if color == self.user_color else self.engine_label

    def is_computer_turn(self, board):
        return not self.over and board.turn == self.computer_color

    def can_move(self, board, color, at_end):
        """The user may move only their own pieces, on their turn, from the last position."""
        return not self.over and at_end and color == self.user_color == board.turn

    def allows(self, command):
        return command in (self.ALLOWED_AFTER_GAME if self.over else self.ALLOWED_DURING_GAME)

    def status_text(self, board):
        if self.over:
            return self.end_text
        if board.turn == self.user_color:
            text = S.VS_YOUR_MOVE
            if board.is_check():
                text += " · " + S.STATUS_CHECK
            return text
        return S.VS_THINKING

    # --- Headers ----------------------------------------------------------

    def write_headers(self, headers):
        headers["Event"] = self.EVENT
        headers["Site"] = S.UNKNOWN
        headers["Date"] = datetime.date.today().strftime("%Y.%m.%d")
        headers["Round"] = S.UNKNOWN
        headers["White"] = self.player_name(chess.WHITE)
        headers["Black"] = self.player_name(chess.BLACK)
        headers["Result"] = "*"

    def write_result(self, headers):
        headers["Result"] = self.result or "*"
        if self.termination:
            headers["Termination"] = self.termination

    # --- Ending -----------------------------------------------------------

    def engine_failed(self, error):
        if not self.over:
            self._finish("*", S.VS_ENGINE_ERROR.format(error=error), "abandoned")

    def _finish(self, result, text, termination=None):
        self.result, self.end_text, self.termination = result, text, termination
        self.request_id += 1   # any computer reply still on its way is no longer wanted

    # --- Computer requests ------------------------------------------------

    def new_request(self):
        self.request_id += 1
        return self.request_id

    def is_current(self, request_id):
        return not self.over and request_id == self.request_id
