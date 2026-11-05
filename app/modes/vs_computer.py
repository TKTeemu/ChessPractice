"""VsComputerMode: the user plays one colour, an engine the other, with a chess clock.

The rules live in ComputerGame; this class connects them to the window: the dialog and the
Resign / Open in Board Mode buttons. The engine worker comes from EngineGameMode, the
clock and Resign from TimedGameMode.
"""

import random
import tkinter as tk

import chess

from .. import strings as S
from ..computer_game import ComputerGame
from ..dialogs import new_computer_game
from ..model import game_outcome
from .base import MenuItem
from .timed_mode import TimedGameMode

CHOICES = ("engine", "level", "color", "start", "minutes", "increment")   # stored as settings vs_<choice>


class VsComputerMode(TimedGameMode):
    key = "vs_computer"
    label = S.MODE_VS_COMPUTER
    SETTINGS = {
        "vs_minutes": 30,
        "vs_increment": 0,
        "vs_engine": "stockfish",
        "vs_level": "1320",
        "vs_color": "white",
        "vs_start": "initial",
    }

    # --- Life cycle -------------------------------------------------------

    def _current_board(self):
        """The position shown, without its move history (the start of a game from it)."""
        return chess.Board(self.ctx.model.board.fen())

    def choose(self):
        available, notes = self.engine_choices()
        return new_computer_game(self.ctx.root, available, notes, self.ctx.settings,
                                 game_outcome(self._current_board()) is not None)

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
        self.game = ComputerGame(user_color, engine.name, level, config["minutes"], increment=config["increment"])

        self.start_game(self._current_board() if config["start"] == "current" else None)
        ctx.set_flipped(user_color == chess.BLACK)
        self.start_engine(engine, level)
        self.start_clock()
        self._next_turn()

    # --- Questions --------------------------------------------------------

    def title(self):
        title = super().title()
        return f"{title} · {self.game.engine_label}" if self.game else title

    def score_text(self):
        return self.game.score_text(self._tip()) if self.game else None

    # --- UI ---------------------------------------------------------------

    def build_panel(self, parent):
        frame = tk.Frame(parent, bg=parent["bg"])
        frame.columnconfigure((0, 1), weight=1)
        self._grid_game_buttons(frame, 0)
        return frame

    def menu_items(self):
        return [
            MenuItem(S.MODE_RESIGN, self.resign, self._running),
            MenuItem(S.MODE_OPEN_IN_BOARD, self.open_in_board_mode,
                     lambda: self.game is not None and self.game.over),
        ]
