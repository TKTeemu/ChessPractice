"""LearningGame: the rules of one opening-training game. Knows nothing about the user interface.

The computer answers from the opening book while the position is in it and leaves the
rest to the engine. On top of EngineGame, the game keeps count of the user's book moves,
notices when the user leaves the theory, and decides how long next-move suggestions are
shown (the opening phase). LearnOpeningsMode drives it.
"""

import random

from . import strings as S
from .commands import EDIT_COMMENT, NAVIGATE, TAKE_BACK
from .engine_game import EngineGame
from .model import game_outcome, outcome_text

ALLOWED = frozenset({NAVIGATE, EDIT_COMMENT, TAKE_BACK})
OUT_OF_BOOK_USER_MOVES = 2   # the opening phase ends after this many user moves outside the book
MAX_ALT_HINTS = 3


class LearningGame(EngineGame):
    EVENT = S.LEARN_EVENT
    ALLOWED_DURING_GAME = ALLOWED
    ALLOWED_AFTER_GAME = ALLOWED

    def __init__(self, line, user_color, engine_label, vary=True, rng=None, suggest_moves=12):
        super().__init__(user_color, engine_label)
        self.line = line
        self.vary = vary
        self.rng = rng or random.Random()
        self.suggest_moves = suggest_moves
        self._reset()

    def _reset(self):
        self.in_book = True
        self.book_moves_played = 0      # half-moves of either side that were book moves
        self.user_book_hits = 0         # user moves that were book moves …
        self.user_book_chances = 0      # … out of the user moves played in a book position
        self.deviation = None           # [BookMove] of the position the user just left the book in
        self.current_line_name = None
        self.opening_phase = True
        self.notice = None
        self.last_comment = ""          # explanation of the book move just played
        self.result = None
        self.end_text = None
        self.termination = None
        self._out_moves = None          # user moves since the game left the book, None while in it
        self._announced = False         # "End of theory" / "Out of theory" has been shown

    # --- Queries ----------------------------------------------------------

    @property
    def opening(self):
        return self.line.opening

    def theory_text(self):
        return S.LEARN_THEORY.format(hits=self.user_book_hits, total=self.user_book_chances)

    def suggestions(self, board):
        """Book moves for the user in this position; empty once the opening phase is over."""
        if not self.opening_phase or self.over or board.turn != self.user_color:
            return []
        return self.line.moves(board)

    def hints(self, board):
        """Arrows for the board: [(from_sq, to_sq, "main" | "alt")]. The book moves of this
        position, or, right after the user left the book, those of the position left."""
        moves = self.suggestions(board)
        if not moves and self.opening_phase and board.turn == self.user_color:
            moves = self.deviation or []
        return [(bm.move.from_square, bm.move.to_square, "main" if i == 0 else "alt")
                for i, bm in enumerate(moves[:1 + MAX_ALT_HINTS])]

    def computer_reply(self, board):
        """A book move for the computer, or None: ask the engine."""
        return self.line.pick(board, self.rng, self.vary)

    # --- Events -----------------------------------------------------------

    def move_played(self, board_after, suggest=True):
        """Call after each move. `suggest`: the user wants book moves named when leaving the book."""
        board_before = board_after.copy()
        move = board_before.pop()
        user_move = board_before.turn == self.user_color
        book = self.line.moves(board_before)
        book_move = next((bm for bm in book if bm.move == move), None)
        was_in_book, self.in_book = self.in_book, bool(self.line.moves(board_after))
        if user_move:
            self.notice = None
            self.deviation = None
            if book:
                self.user_book_chances += 1
                if book_move or self.in_book:   # a move order that transposes is theory too
                    self.user_book_hits += 1
                else:
                    self.deviation = book
        self.last_comment = book_move.comment if book_move else ""
        if book_move:
            self.book_moves_played += 1
            if book_move.line:
                self.current_line_name = book_move.line

        if self.in_book:
            self._out_moves = None
        elif self._out_moves is None:
            self._out_moves = 0                  # left the book just now
        elif user_move:
            self._out_moves += 1
            if self._out_moves >= OUT_OF_BOOK_USER_MOVES:
                self.opening_phase = False
        if board_after.fullmove_number > self.suggest_moves:
            self.opening_phase = False

        if was_in_book and not self.in_book:
            if self.deviation:
                names = ", ".join(board_before.san(bm.move) for bm in self.deviation)
                self.notice = (S.LEARN_OUT_OF_THEORY_BOOK.format(moves=names)
                               if suggest and self.opening_phase else S.LEARN_OUT_OF_THEORY)
            elif not self._announced:
                self.notice = S.LEARN_END_OF_THEORY
            self._announced = True

        outcome = game_outcome(board_after)
        if outcome is not None:
            self._finish(outcome.result(), outcome_text(outcome))

    def took_back(self, board):
        """After moves were taken back: recount everything for the game up to `board`."""
        self._reset()
        replay = board.root()
        for move in board.move_stack:
            replay.push(move)
            self.move_played(replay)
        super().took_back(board)
        self.deviation = None

    # --- Headers ----------------------------------------------------------

    def write_headers(self, headers):
        super().write_headers(headers)
        headers["Opening"] = self.opening.name
        if self.opening.eco:
            headers["ECO"] = self.opening.eco
