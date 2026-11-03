"""VsComputerMode: the user plays one colour, an engine the other, with a chess clock.

The rules live in ComputerGame; this class connects them to the window: the dialog, the
engine worker (via EngineGameMode), the clock display and the Resign / Open in Board Mode
buttons.
"""

import random
import tkinter as tk
from tkinter import messagebox

import chess

from .. import strings as S
from .. import widgets
from ..clock import format_time
from ..computer_game import ComputerGame
from ..dialogs import new_computer_game
from ..model import END
from .base import MenuItem
from .engine_mode import EngineGameMode

TICK_MS = 100     # how often the clocks are redrawn and checked for a flag fall
LOW_TIME = 60     # seconds; below this the clock is shown in red with tenths
CHOICES = ("engine", "level", "color", "start")   # dialog choices, stored as settings vs_<choice>


class VsComputerMode(EngineGameMode):
    key = "vs_computer"
    label = S.MODE_VS_COMPUTER
    SETTINGS = {
        "vs_minutes": 30,
        "vs_engine": "stockfish",
        "vs_level": "1320",
        "vs_color": "white",
        "vs_start": "initial",
    }

    def __init__(self, ctx):
        super().__init__(ctx)
        self._buttons = {}

    # --- Life cycle -------------------------------------------------------

    def _current_board(self):
        """The position shown, without its move history (the start of a game from it)."""
        return chess.Board(self.ctx.model.board.fen())

    def choose(self):
        available, notes = self.engine_choices()
        return new_computer_game(self.ctx.root, available, notes, self.ctx.settings,
                                 self._current_board().is_game_over(claim_draw=True))

    def start(self, config):
        ctx = self.ctx
        settings = ctx.settings
        for key in CHOICES:
            settings[f"vs_{key}"] = config[key]

        engine = self.make_engine(config["engine"])
        level = engine.level(config["level"])
        color_key = config["color"]
        if color_key == "random":
            color_key = random.choice(("white", "black"))
        user_color = chess.WHITE if color_key == "white" else chess.BLACK
        self.game = ComputerGame(user_color, engine.name, level, settings["vs_minutes"])

        ctx.new_game(self._current_board() if config["start"] == "current" else None)
        self.game.write_headers(ctx.model.headers)
        ctx.set_flipped(user_color == chess.BLACK)
        self.start_engine(engine, level)
        self._schedule("tick", TICK_MS, self._tick)
        self._next_turn()

    def deactivate(self):
        super().deactivate()
        self.ctx.set_clocks(None)

    def confirm_leave(self):
        if not self._running():
            return True
        return messagebox.askyesno(S.VS_RESIGN_TITLE, S.VS_RESIGN_PROMPT, parent=self.ctx.root)

    def leave(self):
        self.resign()

    # --- Questions --------------------------------------------------------

    def title(self):
        title = super().title()
        return f"{title} · {self.game.engine_label}" if self.game else title

    def score_text(self):
        return self.game.score_text(self._tip()) if self.game else None

    # --- Moves ------------------------------------------------------------

    def after_move(self):
        model = self.ctx.model
        left = self.game.move_played(model.board)
        model.set_clock(model.node, left)
        if self.game.over:
            self._game_over()
        else:
            self._next_turn()
        self._update_clocks()

    def _next_turn(self):
        if self.game.is_computer_turn(self._tip()):
            self.computer_turn()
        self._update_buttons()

    # --- Clock ------------------------------------------------------------

    def _tick(self):
        self._schedule("tick", TICK_MS, self._tick)
        if self._running() and self.game.clock.flagged() is not None and self.game.check_time(self._tip()):
            self._game_over()
            self.ctx.refresh()
            self.ctx.play_sound(END)
        self._update_clocks()

    def _update_clocks(self):
        clock = self.game.clock
        values = {}
        for color in chess.COLORS:
            left = clock.remaining(color)
            values[color] = (format_time(left), clock.running == color, left < LOW_TIME)
        self.ctx.set_clocks(values)

    # --- Ending -----------------------------------------------------------

    def resign(self):
        if not self._running():
            return
        self.game.resign()
        self._game_over()
        self.ctx.refresh()
        self.ctx.play_sound(END)

    def _game_over(self):
        super()._game_over()
        self._update_buttons()
        self._update_clocks()

    # --- UI ---------------------------------------------------------------

    def build_panel(self, parent):
        frame = tk.Frame(parent, bg=parent["bg"])
        frame.columnconfigure((0, 1), weight=1)
        self._buttons = {
            "resign": widgets.button(frame, S.MODE_RESIGN, self.resign),
            "open": widgets.button(frame, S.MODE_OPEN_IN_BOARD, self.open_in_board_mode),
        }
        self._buttons["resign"].grid(row=0, column=0, sticky="ew", padx=2)
        self._buttons["open"].grid(row=0, column=1, sticky="ew", padx=2)
        self._update_buttons()
        return frame

    def _update_buttons(self):
        running = self._running()
        states = {"resign": running, "open": self.game is not None and not running}
        for name, button in self._buttons.items():
            if button.winfo_exists():
                button.configure(state="normal" if states[name] else "disabled")

    def menu_items(self):
        return [
            MenuItem(S.MODE_RESIGN, self.resign, self._running),
            MenuItem(S.MODE_OPEN_IN_BOARD, self.open_in_board_mode,
                     lambda: self.game is not None and self.game.over),
        ]
