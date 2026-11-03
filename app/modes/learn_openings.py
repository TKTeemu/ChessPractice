"""LearnOpeningsMode: the computer plays its side from the opening book, then the engine takes over.

The rules live in LearningGame and the book in openings.py; this class connects them to the
window: the opening dialog, book moves after a short pause, the engine worker (via
EngineGameMode), suggestion arrows and the panel with Take Back and Open in Board Mode.
"""

import random
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import chess

from .. import strings as S
from ..dialogs import choose_opening
from ..engines import ENGINES
from ..learning_game import LearningGame
from ..openings import OpeningBook, OpeningLine
from ..theme import ENTRY_BG, MUTED_FG, PANEL_FG
from .base import MenuItem
from .engine_mode import EngineGameMode

BOOK_DELAY_MS = 400   # a book reply waits a moment, so that it is seen as a separate move
SUGGEST_MOVES_RANGE = (10, 15)


class LearnOpeningsMode(EngineGameMode):
    key = "learn_openings"
    label = S.MODE_LEARN_OPENINGS
    show_details = False

    def __init__(self, ctx):
        super().__init__(ctx)
        self._labels = {}
        self._buttons = {}
        self._suggest_var = None
        self._suggest_check = None

    # --- Life cycle -------------------------------------------------------

    def book_folder(self):
        return Path(self.ctx.settings.path).parent / "assets" / "openings"

    def activate(self):
        ctx = self.ctx
        settings = ctx.settings
        book = OpeningBook.load(self.book_folder())
        if not book.openings:
            messagebox.showerror(S.LEARN_TITLE, S.LEARN_NO_BOOK.format(folder=self.book_folder()),
                                 parent=ctx.root)
            return False
        available = [cls for cls in ENGINES if cls.available(settings)]
        notes = [cls.unavailable_reason(settings) for cls in ENGINES if not cls.available(settings)]
        if book.errors:
            notes.append(S.LEARN_BOOK_ERRORS.format(
                errors="\n".join(f"{name}: {error}" for name, error in book.errors[:5])))
        choice = choose_opening(ctx.root, book, available, notes, settings)
        if choice is None or not ctx.confirm_discard():
            return False
        for key in ("opening", "role", "engine", "level", "vary"):
            settings[f"learn_{key}"] = choice[key]

        opening = book.opening(choice["opening"])
        engine = next(cls for cls in available if cls.key == choice["engine"])(settings)
        level = engine.level(choice["level"])
        user_color = opening.side if choice["role"] == "opening" else not opening.side
        low, high = SUGGEST_MOVES_RANGE
        self.game = LearningGame(OpeningLine(opening), user_color, f"{engine.name} {level.label}".strip(),
                                 vary=choice["vary"], rng=random.Random(),
                                 suggest_moves=min(high, max(low, settings["learn_suggest_moves"])))

        ctx.new_game(None)
        self.game.write_headers(ctx.model.headers)
        ctx.set_flipped(user_color == chess.BLACK)
        self.start_engine(engine, level)
        self._next_turn()
        return True

    def new_game(self):
        self.ctx.set_mode(self.key)   # the dialog again, with the previous choices
        return True

    # --- Questions --------------------------------------------------------

    def _suggest(self):
        return self.ctx.settings["learn_suggest"]

    def can_move(self, color):
        model = self.ctx.model
        return self.game is not None and self.game.can_move(model.board, color, model.at_end())

    def allows(self, command):
        return self.game is None or self.game.allows(command)

    def title(self):
        title = super().title()
        return f"{title} · {self.game.opening.name}" if self.game else title

    def status_text(self):
        return self.game.status_text(self._tip()) if self.game else None

    def hint_arrows(self):
        if self.game is None or not self._suggest() or not self.ctx.model.at_end():
            return []
        return self.game.hints(self._tip())

    # --- Moves ------------------------------------------------------------

    def after_move(self):
        model = self.ctx.model
        node = model.node
        self.game.move_played(node.parent.board(), node.move, model.board, suggest=self._suggest())
        if self.game.last_comment and not node.comment:
            model.set_comment(node, self.game.last_comment)
        if self.game.over:
            self._game_over()
        else:
            self._next_turn()
        self._update_panel()

    def _next_turn(self):
        board = self._tip()
        if self.game.is_computer_turn(board):
            self.computer_turn()
        self._update_panel()

    def computer_turn(self):
        move = self.game.computer_reply(self._tip())
        if move is None:
            self.request_engine_move()
        else:
            self.play_computer_move(move, BOOK_DELAY_MS)

    def take_back(self):
        if self.game is None:
            return
        self.cancel_computer_move()
        if self.ctx.take_back(self.game.user_color):
            self.game.took_back(self._tip())
            self.ctx.model.headers["Result"] = "*"
            self._next_turn()
            self.ctx.refresh()

    def _game_over(self):
        self.game.write_result(self.ctx.model.headers)
        super()._game_over()

    def open_in_board_mode(self):
        self.ctx.set_mode("board")

    # --- UI ---------------------------------------------------------------

    def build_panel(self, parent):
        bg = parent["bg"]
        frame = tk.Frame(parent, bg=bg)
        frame.columnconfigure((0, 1), weight=1)

        def label(row, bold=False):
            widget = tk.Label(frame, bg=bg, fg=PANEL_FG if bold else MUTED_FG, anchor="w", justify="left",
                              font=("Segoe UI", 10, "bold") if bold else ("Segoe UI", 9))
            widget.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4)
            widget.bind("<Configure>", lambda e: widget.configure(wraplength=e.width))
            return widget

        self._labels = {"name": label(0, bold=True), "line": label(1), "theory": label(2)}
        check_row = tk.Frame(frame, bg=bg)
        check_row.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(2, 4))
        self._suggest_var = tk.BooleanVar(value=self._suggest())
        self._suggest_check = tk.Checkbutton(
            check_row, text=S.LEARN_SUGGEST, variable=self._suggest_var, command=self._suggest_changed,
            bg=bg, fg=PANEL_FG, selectcolor=ENTRY_BG, activebackground=bg, activeforeground=PANEL_FG,
            disabledforeground=MUTED_FG, font=("Segoe UI", 10), bd=0, highlightthickness=0, takefocus=0)
        self._suggest_check.pack(side="left")
        self._labels["phase"] = tk.Label(check_row, bg=bg, fg=MUTED_FG, font=("Segoe UI", 9))
        self._labels["phase"].pack(side="left", padx=(4, 0))
        self._buttons = {
            "take_back": self.ctx.button(frame, S.MODE_TAKE_BACK, self.take_back),
            "open": self.ctx.button(frame, S.MODE_OPEN_IN_BOARD, self.open_in_board_mode),
        }
        self._buttons["take_back"].grid(row=4, column=0, sticky="ew", padx=2)
        self._buttons["open"].grid(row=4, column=1, sticky="ew", padx=2)
        self._update_panel()
        return frame

    def _suggest_changed(self):
        self.ctx.settings["learn_suggest"] = self._suggest_var.get()
        self.ctx.refresh()

    def _can_take_back(self):
        return self.game is not None and any(
            node.parent.turn() == self.game.user_color for node in self.ctx.model.game.mainline())

    def _update_panel(self):
        if not self._labels or not self._labels["name"].winfo_exists() or self.game is None:
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
        self._buttons["take_back"].configure(state="normal" if self._can_take_back() else "disabled")

    def menu_items(self):
        return [
            MenuItem(S.MODE_TAKE_BACK, self.take_back, self._can_take_back),
            MenuItem(S.MODE_OPEN_IN_BOARD, self.open_in_board_mode, lambda: self.game is not None),
        ]
