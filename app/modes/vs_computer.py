"""VsComputerMode: the user plays one colour, an engine the other, with a chess clock.

The rules live in ComputerGame; this class connects them to the window: the dialog, the
engine worker, the clock display and the Resign / Open in Board Mode buttons.
"""

import random
import tkinter as tk
from tkinter import messagebox

import chess

from .. import strings as S
from ..clock import format_time
from ..computer_game import ComputerGame
from ..dialogs import new_computer_game
from ..engines import ENGINES
from ..model import END
from .base import MenuItem
from .engine_mode import EngineGameMode

TICK_MS = 100     # how often the clocks are redrawn and checked for a flag fall
LOW_TIME = 60     # seconds; below this the clock is shown in red with tenths


class VsComputerMode(EngineGameMode):
    key = "vs_computer"
    label = S.MODE_VS_COMPUTER
    show_details = False

    def __init__(self, ctx):
        super().__init__(ctx)
        self._buttons = {}

    # --- Life cycle -------------------------------------------------------

    def activate(self):
        ctx = self.ctx
        settings = ctx.settings
        available = [cls for cls in ENGINES if cls.available(settings)]
        notes = [cls.unavailable_reason(settings) for cls in ENGINES if not cls.available(settings)]
        current = chess.Board(ctx.model.board.fen())
        choice = new_computer_game(ctx.root, available, notes, settings,
                                   current.is_game_over(claim_draw=True))
        if choice is None or not ctx.confirm_discard():
            return False
        for key in ("engine", "level", "color", "start"):
            settings[f"vs_{key}"] = choice[key]

        engine = next(cls for cls in available if cls.key == choice["engine"])(settings)
        level = engine.level(choice["level"])
        color_key = choice["color"]
        if color_key == "random":
            color_key = random.choice(("white", "black"))
        user_color = chess.WHITE if color_key == "white" else chess.BLACK
        self.game = ComputerGame(user_color, engine.name, level, settings["vs_minutes"])

        ctx.new_game(current if choice["start"] == "current" else None)
        self.game.write_headers(ctx.model.headers)
        ctx.set_flipped(user_color == chess.BLACK)
        self.start_engine(engine, level)
        self._schedule("tick", TICK_MS, self._tick)
        self._next_turn()
        return True

    def deactivate(self):
        super().deactivate()
        self.ctx.set_clocks(None)

    def confirm_leave(self):
        if not self._running():
            return True
        if not messagebox.askyesno(S.VS_RESIGN_TITLE, S.VS_RESIGN_PROMPT, parent=self.ctx.root):
            return False
        self.resign()
        return True

    # --- Questions --------------------------------------------------------

    def can_move(self, color):
        model = self.ctx.model
        return self.game is not None and self.game.can_move(model.board, color, model.at_end())

    def allows(self, command):
        return self.game is None or self.game.allows(command)

    def title(self):
        title = super().title()
        return f"{title} · {self.game.engine_label}" if self.game else title

    def status_text(self):
        return self.game.status_text(self._tip()) if self.game else None

    def score_text(self):
        return self.game.score_text(self._tip()) if self.game else None

    def new_game(self):
        if self.confirm_leave():
            self.ctx.set_mode(self.key)   # a fresh game: shows the dialog again
        return True

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
        board = self._tip()
        if self.game.is_engine_turn(board):
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
        self.game.write_result(self.ctx.model.headers)
        super()._game_over()
        self._update_buttons()
        self._update_clocks()

    def open_in_board_mode(self):
        self.ctx.set_mode("board")

    # --- UI ---------------------------------------------------------------

    def build_panel(self, parent):
        frame = tk.Frame(parent, bg=parent["bg"])
        frame.columnconfigure((0, 1), weight=1)
        self._buttons = {
            "resign": self.ctx.button(frame, S.MODE_RESIGN, self.resign),
            "open": self.ctx.button(frame, S.MODE_OPEN_IN_BOARD, self.open_in_board_mode),
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
