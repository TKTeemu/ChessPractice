"""LearnOpeningsMode: the computer plays its side from the opening book, then the engine takes over.

The rules live in LearningGame and the book in openings.py; this class connects them to the
window: the opening dialog, book moves after a short pause, the engine worker (via
EngineGameMode), suggestion arrows and the panel with Open in Board Mode.
"""

import random
import tkinter as tk
from tkinter import messagebox

import chess

from .. import strings as S
from .. import widgets
from ..dialogs import choose_opening
from ..learning_game import LearningGame
from ..openings import OpeningLine
from .base import MenuItem
from .engine_mode import EngineGameMode

BOOK_DELAY_MS = 400   # a book reply waits a moment, so that it is seen as a separate move
CHOICES = ("opening", "role", "engine", "level", "vary", "suggest_moves")   # stored as settings learn_<choice>


class LearnOpeningsMode(EngineGameMode):
    key = "learn_openings"
    label = S.MODE_LEARN_OPENINGS
    takes_back = True
    SETTINGS = {
        "learn_opening": "reti",
        "learn_role": "opening",
        "learn_engine": "stockfish",
        "learn_level": "1320",
        "learn_vary": True,
        "learn_suggest": True,
        "learn_suggest_moves": 12,
    }

    def __init__(self, ctx):
        super().__init__(ctx)
        self._labels = {}
        self._buttons = {}
        self._suggest_var = None
        self._suggest_check = None

    # --- Life cycle -------------------------------------------------------

    def choose(self):
        ctx = self.ctx
        book = ctx.assets.opening_book()
        if not book.openings:
            messagebox.showerror(S.LEARN_TITLE, S.LEARN_NO_BOOK.format(folder=ctx.assets.opening_folder),
                                 parent=ctx.root)
            return None
        available, notes = self.engine_choices()
        if book.errors:
            notes.append(S.LEARN_BOOK_ERRORS.format(
                errors="\n".join(f"{name}: {error}" for name, error in book.errors[:5])))
        return choose_opening(ctx.root, book, available, notes, ctx.settings)

    def start(self, config):
        ctx = self.ctx
        settings = ctx.settings
        for key in CHOICES:
            settings[f"learn_{key}"] = config[key]

        opening = ctx.assets.opening_book().opening(config["opening"])
        engine = self.make_engine(config["engine"])
        level = engine.level(config["level"])
        user_color = opening.side if config["role"] == "opening" else not opening.side
        self.game = LearningGame(OpeningLine(opening), user_color, f"{engine.name} {level.label}".strip(),
                                 vary=config["vary"], rng=random.Random(),
                                 suggest_moves=config["suggest_moves"])

        self.start_game()
        ctx.set_flipped(user_color == chess.BLACK)
        self.start_engine(engine, level)
        self._next_turn()

    # --- Questions --------------------------------------------------------

    def _suggest(self):
        return self.ctx.settings["learn_suggest"]

    def title(self):
        title = super().title()
        return f"{title} · {self.game.opening.name}" if self.game else title

    def hint_arrows(self):
        if self.game is None or not self._suggest() or not self.ctx.model.at_end():
            return []
        return self.game.hints(self._tip())

    # --- Moves ------------------------------------------------------------

    def after_move(self):
        model = self.ctx.model
        node = model.node
        self.game.move_played(model.board, suggest=self._suggest())
        if self.game.last_comment and not node.comment:
            model.set_comment(node, self.game.last_comment)
        if self.game.over:
            self._game_over()
        else:
            self._next_turn()
        self._update_panel()

    def _next_turn(self):
        super()._next_turn()
        self._update_panel()

    def computer_turn(self):
        move = self.game.computer_reply(self._tip())
        if move is None:
            self.request_engine_move()
        else:
            self.play_computer_move(move, BOOK_DELAY_MS)

    # --- UI ---------------------------------------------------------------

    def build_panel(self, parent):
        frame = tk.Frame(parent, bg=parent["bg"])
        frame.columnconfigure((0, 1), weight=1)
        self._labels = {"name": widgets.label(frame, bold=True, wrap=True),
                        "line": widgets.label(frame, wrap=True),
                        "theory": widgets.label(frame, wrap=True)}
        for row, name in enumerate(("name", "line", "theory")):
            self._labels[name].grid(row=row, column=0, columnspan=2, sticky="ew", padx=4)
        check_row = tk.Frame(frame, bg=frame["bg"])
        check_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 4))
        self._suggest_var = tk.BooleanVar(value=self._suggest())
        self._suggest_check = widgets.checkbox(check_row, S.LEARN_SUGGEST, self._suggest_var,
                                               self._suggest_changed)
        self._suggest_check.pack(side="left")
        self._labels["phase"] = widgets.label(check_row)
        self._labels["phase"].pack(side="left", padx=(4, 0))
        self._buttons = {
            "open": widgets.button(frame, S.MODE_OPEN_IN_BOARD, self.open_in_board_mode),
        }
        self._buttons["open"].grid(row=4, column=0, columnspan=2, sticky="ew", padx=2)
        self._update_panel()
        return frame

    def _suggest_changed(self):
        self.ctx.settings["learn_suggest"] = self._suggest_var.get()
        self.ctx.update_status()

    def _update_panel(self):
        if not self._labels or self.game is None:
            return
        opening = self.game.opening
        eco = opening.eco.replace("-", "–")
        self._labels["name"].configure(text=f"{opening.name} · {eco}" if eco else opening.name)
        line = self.game.current_line_name
        self._labels["line"].configure(text=S.LEARN_LINE.format(name=line) if line else "")
        if line:
            self._labels["line"].grid()
        else:
            self._labels["line"].grid_remove()
        self._labels["theory"].configure(text=self.game.theory_text())
        phase = self.game.opening_phase
        self._suggest_check.configure(state="normal" if phase else "disabled")
        self._labels["phase"].configure(text="" if phase else S.LEARN_PHASE_OVER)

    def menu_items(self):
        return [
            MenuItem(S.MODE_TAKE_BACK, self.take_back, self.can_take_back),
            MenuItem(S.MODE_OPEN_IN_BOARD, self.open_in_board_mode, lambda: self.game is not None),
        ]
