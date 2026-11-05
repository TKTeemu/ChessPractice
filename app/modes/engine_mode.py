"""EngineGameMode: the shared base of modes in which the computer plays one side.

It owns the engine worker, the timer that polls it, delayed computer moves and the
request ids that make stale replies harmless, and answers the questions MainWindow asks
from `self.game`, an EngineGame (app/engine_game.py). A subclass implements choose() and
start(config), which creates `self.game`, calls start_game() and start_engine(), and decides
in computer_turn() how the computer chooses its move.
"""

from tkinter import messagebox

from .. import strings as S
from ..commands import TAKE_BACK
from ..engines import ENGINES, EngineError, engine_class
from ..engines.worker import EngineWorker
from .base import Mode

POLL_MS = 50      # how often engine results are checked


class EngineGameMode(Mode):
    show_details = False
    replaces_game = True

    def __init__(self, ctx):
        super().__init__(ctx)
        self.game = None
        self.level = None
        self.worker = None

    # --- Choosing the engine ----------------------------------------------

    def engine_choices(self):
        """(available engine classes, notes explaining the missing ones) for the dialog."""
        settings, app_dir = self.ctx.settings, self.ctx.app_dir
        available = [cls for cls in ENGINES if cls.available(settings, app_dir)]
        notes = [cls.unavailable_reason(settings, app_dir) for cls in ENGINES
                 if not cls.available(settings, app_dir)]
        return available, notes

    def make_engine(self, key):
        return engine_class(key)(self.ctx.settings, self.ctx.app_dir)

    # --- Life cycle -------------------------------------------------------

    def start_game(self, board=None, intro=""):
        """Replace the game on the board with self.game, which has just been created."""
        headers = {}
        self.game.write_headers(headers)
        self.ctx.new_game(board, headers=headers, intro=intro)

    def start_engine(self, engine, level):
        """The engine process starts only with the first request (EngineWorker)."""
        self.level = level
        self.worker = EngineWorker(engine)
        self._schedule("poll", POLL_MS, self._poll)

    def deactivate(self):
        super().deactivate()
        if self.worker is not None:
            self.worker.close()
            self.worker = None

    def new_game(self):
        self.ctx.set_mode(self.key)   # the dialog again, with the previous choices
        return True

    # --- Questions --------------------------------------------------------

    def _running(self):
        return self.game is not None and not self.game.over

    def _tip(self):
        """The board after the last move played (the user may be browsing earlier moves)."""
        return self.ctx.model.game.end().board()

    def can_move(self, color):
        model = self.ctx.model
        return self.game is not None and self.game.can_move(model.board, color, model.at_end())

    def allows(self, command):
        return self.game is None or self.game.allows(command)

    def status_text(self):
        return self.game.status_text(self._tip()) if self.game else None

    def can_take_back(self):
        return self.takes_back and self.game is not None and self.game.allows(TAKE_BACK) and any(
            node.parent.turn() == self.game.user_color for node in self.ctx.model.game.mainline())

    # --- Moves ------------------------------------------------------------

    def _next_turn(self):
        """It is the next player's turn in self._tip()."""
        if self.game.is_computer_turn(self._tip()):
            self.computer_turn()

    def take_back(self):
        """Remove the user's last move and the reply. Asked first, because cancelling the
        computer's move with nothing to take back would leave it never moving again."""
        if not self.can_take_back():
            return
        self.cancel_computer_move()
        if self.ctx.take_back(self.game.user_color):
            self.game.took_back(self._tip())
            self.ctx.model.clear_result()
            self._next_turn()
            self.ctx.update_status()

    # --- Computer moves ---------------------------------------------------

    def computer_turn(self):
        """The computer is to move in self._tip(). Subclasses may choose a move themselves."""
        self.request_engine_move()

    def request_engine_move(self):
        self.worker.request(self._tip(), self.level, self.game.new_request())

    def play_computer_move(self, move, delay_ms=0):
        """Play a move chosen without the engine (e.g. from a book) after a short pause."""
        request_id = self.game.new_request()
        self._schedule("move", delay_ms, lambda: self._deliver(request_id, move))

    def cancel_computer_move(self):
        """Forget any computer move still on its way (take-back, game over)."""
        if self.game is not None:
            self.game.new_request()
        if self.worker is not None:
            self.worker.cancel()

    def _deliver(self, request_id, move):
        self._after_ids.pop("move", None)
        if self.game.is_current(request_id):
            self.ctx.play_move(move, from_end=True)

    def _poll(self):
        self._schedule("poll", POLL_MS, self._poll)
        for request_id, result in self.worker.poll():
            if not self.game.is_current(request_id):
                continue   # resigned, taken back or a new game started meanwhile
            if isinstance(result, EngineError):
                self.engine_failed(result)
            else:
                self.engine_result(result)

    def engine_result(self, result):
        """A current result of the worker: a chess.Move, or an Analysis if one was asked for."""
        self.ctx.play_move(result, from_end=True)

    def engine_failed(self, error):
        self.game.engine_failed(error)
        self._game_over()
        self.ctx.update_status()
        messagebox.showerror(S.VS_ENGINE_ERROR_TITLE, str(error), parent=self.ctx.root)

    # --- Ending -----------------------------------------------------------

    def _game_over(self):
        """The game has just ended: write the result. Subclasses also update their panel."""
        self.ctx.model.set_headers(self.game.result_headers())
        if self.worker is not None:
            self.worker.cancel()

    def open_in_board_mode(self):
        self.ctx.set_mode("board")
