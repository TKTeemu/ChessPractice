"""BoardMode: the free board. Both sides can be moved; variations and comments work.

Optionally Stockfish analyses the position shown: the score, the expected line and an arrow for
the best move. It runs only while the Engine analysis box is ticked and the program is in this
mode. Each position gets a quick search, for an answer while stepping through a game, and then
a longer one.
"""

import tkinter as tk

from .. import strings as S
from .. import widgets
from ..engines import ENGINES, EngineError, Level, format_score
from ..engines.worker import EngineWorker
from .base import Mode

POLL_MS = 50          # how often engine results are checked
SETTLE_MS = 150       # wait this long after a position change, in case the user steps on at once
LINE_MOVES = 6        # half-moves of the expected line shown
QUICK = Level("analysis-quick", "", None, 0.3, {"UCI_LimitStrength": False})
DEEP = Level("analysis-deep", "", None, 3.0, {"UCI_LimitStrength": False})


class BoardMode(Mode):
    key = "board"
    label = S.MODE_BOARD
    SETTINGS = {"board_analysis": False}

    def __init__(self, ctx):
        super().__init__(ctx)
        self.worker = None
        self._request_id = 0
        self._level = None        # the level of the search on its way
        self._result = None       # the latest Analysis of the current position
        self._node = None         # the node analysed
        self._var = None
        self._label = None

    # --- Life cycle -------------------------------------------------------

    def deactivate(self):
        super().deactivate()
        self._close_worker()

    def _close_worker(self):
        if self.worker is not None:
            self.worker.close()
            self.worker = None

    # --- Engine -----------------------------------------------------------

    def _engine_class(self):
        """The first installed engine that gives scores, or None."""
        settings, app_dir = self.ctx.settings, self.ctx.app_dir
        return next((cls for cls in ENGINES if cls.can_analyse and cls.available(settings, app_dir)), None)

    def _analysing(self):
        return self.ctx.settings["board_analysis"] and self._engine_class() is not None

    def _analyse(self):
        """Start on the position shown; called SETTLE_MS after it changed."""
        board = self.ctx.model.board
        if board.is_game_over():
            self._show("")
            return
        if self.worker is None:
            self.worker = EngineWorker(self._engine_class()(self.ctx.settings, self.ctx.app_dir))
            self._schedule("poll", POLL_MS, self._poll)
        self._show(S.BOARD_ANALYSING)
        self._request(QUICK)

    def _request(self, level):
        self._request_id += 1
        self._level = level
        self.worker.request(self.ctx.model.board, level, self._request_id, analyse=True)

    def _poll(self):
        self._schedule("poll", POLL_MS, self._poll)
        for request_id, result in self.worker.poll():
            if request_id != self._request_id:
                continue   # the position has changed since
            if isinstance(result, EngineError):
                self._failed(result)
                return
            self._result = result
            self._show(self._result_text(result))
            if self._level is QUICK:
                self._request(DEEP)
            self.ctx.update_status()   # the arrow

    def _failed(self, error):
        self.ctx.settings["board_analysis"] = False
        if self._var is not None:
            self._var.set(False)
        self._stop()
        self._show(S.BOARD_ANALYSIS_ERROR.format(error=error))
        self.ctx.update_status()

    def _stop(self):
        self._cancel_timers()
        self._close_worker()
        self._result = None
        self._node = None

    def _result_text(self, analysis):
        board = self.ctx.model.board
        try:
            line = board.variation_san(analysis.pv[:LINE_MOVES])
        except ValueError:   # an engine's line with an illegal move: the best move is checked
            line = board.san(analysis.move)
        score = format_score(analysis, board.turn)
        return S.BOARD_ANALYSIS_LINE.format(score=score, line=line) if score else line

    # --- Notifications and questions --------------------------------------

    def position_changed(self):
        node = self.ctx.model.node
        if node is self._node or not self._analysing():
            return
        self._node = node
        self._result = None
        self._schedule("analyse", SETTLE_MS, self._analyse)

    def hint_arrows(self):
        if self._result is None:
            return []
        move = self._result.move
        return [(move.from_square, move.to_square, "main")]

    # --- UI ---------------------------------------------------------------

    def build_panel(self, parent):
        frame = tk.Frame(parent, bg=parent["bg"])
        frame.columnconfigure(0, weight=1)
        available = self._engine_class() is not None
        self._var = tk.BooleanVar(value=self._analysing())
        check = widgets.checkbox(frame, S.BOARD_ANALYSIS if available else f"{S.BOARD_ANALYSIS} {S.BOARD_NO_ENGINE}",
                                 self._var, self._toggled, state="normal" if available else "disabled")
        check.grid(row=0, column=0, sticky="w")
        self._label = widgets.label(frame, muted=False, wrap=True)
        self._label.grid(row=1, column=0, sticky="ew", padx=4)
        self._show("")
        return frame

    def _toggled(self):
        on = self._var.get()
        self.ctx.settings["board_analysis"] = on
        if on:
            self.position_changed()
        else:
            self._stop()
            self._show("")
            self.ctx.update_status()

    def _show(self, text):
        if self._label is not None:
            self._label.configure(text=text)
            if text:
                self._label.grid()
            else:
                self._label.grid_remove()
