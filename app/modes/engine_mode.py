"""EngineGameMode: the shared base of modes in which the computer plays one side.

It owns the engine worker, the timer that polls it, delayed computer moves and the
request ids that make stale replies harmless. A subclass creates `self.game`, an object
with `over`, `new_request()`, `is_current(request_id)` and `engine_failed(error)`, and
decides in computer_turn() how the computer chooses its move.
"""

from tkinter import messagebox

from .. import strings as S
from ..engines import EngineError
from ..engines.worker import EngineWorker
from .base import Mode

POLL_MS = 50      # how often engine results are checked


class EngineGameMode(Mode):
    def __init__(self, ctx):
        super().__init__(ctx)
        self.game = None
        self.level = None
        self.worker = None
        self._after_ids = {}

    # --- Life cycle -------------------------------------------------------

    def start_engine(self, engine, level):
        """The engine process starts only with the first request (EngineWorker)."""
        self.level = level
        self.worker = EngineWorker(engine)
        self._schedule("poll", POLL_MS, self._poll)

    def deactivate(self):
        for after_id in self._after_ids.values():
            self.ctx.root.after_cancel(after_id)
        self._after_ids.clear()
        if self.worker is not None:
            self.worker.close()
            self.worker = None

    # --- Questions --------------------------------------------------------

    def _running(self):
        return self.game is not None and not self.game.over

    def _tip(self):
        """The board after the last move played (the user may be browsing earlier moves)."""
        return self.ctx.model.game.end().board()

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
                self.ctx.play_move(result, from_end=True)

    def engine_failed(self, error):
        self.game.engine_failed(error)
        self._game_over()
        self.ctx.refresh()
        messagebox.showerror(S.VS_ENGINE_ERROR_TITLE, str(error), parent=self.ctx.root)

    def _game_over(self):
        """The game has just ended. Subclasses also write the result and update their buttons."""
        if self.worker is not None:
            self.worker.cancel()

    # --- Timers -----------------------------------------------------------

    def _schedule(self, name, ms, callback):
        old = self._after_ids.get(name)
        if old is not None:
            self.ctx.root.after_cancel(old)
        self._after_ids[name] = self.ctx.root.after(ms, callback)
