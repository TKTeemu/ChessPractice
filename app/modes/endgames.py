"""EndgameMode: the user plays a stored endgame position against the computer.

The rules live in EndgameGame and the positions in endgames.py; this class connects them to
the window: the level dialog, drawing a position, the computer's stored defence after a short
pause, engine analyses (they judge the user's moves and give the computer's reply), the
success light, suggestion arrows and the panel. The clock and Resign come from TimedGameMode.
"""

import tkinter as tk
from tkinter import messagebox

import chess

from .. import strings as S
from .. import widgets
from ..commands import TAKE_BACK
from ..dialogs import choose_endgame
from ..endgame_game import LEVEL, EndgameGame
from ..endgames import EndgameCollection, EndgameDeck
from ..engines import Analysis, RandomEngine, StockfishEngine
from ..model import visible_comment
from .base import MenuItem
from .timed_mode import TimedGameMode

TREE_DELAY_MS = 400   # a stored reply waits a moment, so that it is seen as a separate move

# Kinds of engine request: the score of the position before the user's move (when not yet
# known), the score after it together with the computer's reply, and the user's best move
# for the suggestion arrow.
BASELINE, REPLY, HINT = "baseline", "reply", "hint"


class EndgameMode(TimedGameMode):
    key = "end_practice"
    label = S.MODE_ENDGAMES
    SETTINGS = {
        "end_difficulty": 1,
        "end_minutes": 15,
        "end_suggest": False,
    }
    # Kept on the class, not the instance: set_mode creates a new mode object each time, and
    # the positions drawn must not repeat until the program is restarted.
    _collection = None
    _deck = None

    def __init__(self, ctx):
        super().__init__(ctx)
        self._labels = {}
        self._suggest_var = None
        self._pending = None   # (request id, kind, ply) of the engine request on its way

    # --- Life cycle -------------------------------------------------------

    def folder(self):
        return self.ctx.app_dir / "assets" / "endgames"

    def _load(self):
        cls = type(self)
        if cls._collection is None:
            cls._collection = EndgameCollection.load(self.folder())
            cls._deck = EndgameDeck(cls._collection)
        return cls._collection

    def _engine(self):
        """Stockfish if it is installed, else random moves."""
        settings, app_dir = self.ctx.settings, self.ctx.app_dir
        if StockfishEngine.available(settings, app_dir):
            return StockfishEngine(settings, app_dir)
        return RandomEngine(settings, app_dir)

    def choose(self):
        ctx = self.ctx
        collection = self._load()
        if not collection.all:
            messagebox.showerror(S.END_TITLE, S.END_NO_POSITIONS.format(folder=self.folder()), parent=ctx.root)
            return None
        notes = [] if StockfishEngine.available(ctx.settings, ctx.app_dir) else [S.END_NO_ENGINE]
        if collection.errors:
            notes.append(S.END_FILE_ERRORS.format(
                errors="\n".join(f"{name}: {error}" for name, error in collection.errors[:5])))
        levels = collection.levels()
        played = {d: self._deck.played(d) for d, _, _ in levels}
        return choose_endgame(ctx.root, levels, played, notes, ctx.settings)

    def start(self, config):
        ctx = self.ctx
        ctx.settings["end_difficulty"] = config["difficulty"]
        ctx.settings["end_minutes"] = config["minutes"]
        self._load()
        sample = self._deck.draw(config["difficulty"])
        engine = self._engine()
        self.game = EndgameGame(sample, engine.name, engine.can_analyse, config["minutes"])

        ctx.new_game(chess.Board(sample.fen))
        ctx.model.game.comment = sample.game.comment.strip()   # the position's introduction
        self.game.write_headers(ctx.model.headers)
        ctx.set_flipped(self.game.user_color == chess.BLACK)
        self.start_engine(engine, LEVEL)
        self.start_clock()
        self._next_turn()

    # --- Questions --------------------------------------------------------

    def _suggest(self):
        return self.ctx.settings["end_suggest"]

    def title(self):
        title = super().title()
        if self.game is None:
            return title
        sample = self.game.sample
        return f"{title} · {S.END_LEVEL.format(level=sample.difficulty)} · {sample.name}"

    def subtitle(self):
        if self.game is None:
            return None
        return self.game.sample.credit_text() or S.END_CLASSIC

    def light(self):
        return self.game.light if self.game else None

    def hint_arrows(self):
        if self.game is None or not self._suggest() or not self.ctx.model.at_end():
            return []
        board = self._tip()
        hints = self.game.hints(board)
        self.game.note_hints(board, hints)
        self._update_panel()
        return hints

    # --- Moves ------------------------------------------------------------

    def after_move(self):
        super().after_move()
        model = self.ctx.model
        if self.game.last_comment and not visible_comment(model.node.comment):
            model.set_comment(model.node, self.game.last_comment)
        self._update_panel()

    def _next_turn(self):
        super()._next_turn()
        if not self.game.over and not self.game.is_computer_turn(self._tip()):
            self._user_turn()
        self._update_panel()

    def _user_turn(self):
        """The user is to move: off the solution, ask for the best move if suggestions are on."""
        board = self._tip()
        ply = len(board.move_stack)
        if (self._suggest() and self.game.can_judge and not self.game.tree.moves(board)
                and ply not in self.game.best):
            self._request(board, HINT, ply)

    def computer_turn(self):
        board = self._tip()
        move = self.game.tree_reply(board)
        if move is not None:
            self.play_computer_move(move, TREE_DELAY_MS)
            return
        ply = len(board.move_stack)
        if self.game.needs_judging(board) and self.game.needs_eval(ply - 1):
            before = board.copy()
            before.pop()
            self._request(before, BASELINE, ply - 1)
        else:
            self._request(board, REPLY, ply)

    def _request(self, board, kind, ply):
        request_id = self.game.new_request()
        self._pending = (request_id, kind, ply)
        self.worker.request(board, self.level, request_id, analyse=True)

    def engine_result(self, result):
        if not isinstance(result, Analysis):   # an engine without scores: just its move
            super().engine_result(result)
            return
        _, kind, ply = self._pending
        self.game.analysed(ply, result)
        if kind == BASELINE:
            self._request(self._tip(), REPLY, ply + 1)
        elif kind == REPLY:
            self.ctx.play_move(result.move, from_end=True)
        else:
            self.ctx.refresh()   # the suggestion arrow

    def take_back(self):
        if self.game is None or not self._can_take_back():
            return
        self.cancel_computer_move()
        if self.ctx.take_back(self.game.user_color):
            self.game.took_back(self._tip())
            headers = self.ctx.model.headers
            headers["Result"] = "*"
            headers.pop("Termination", None)
            self._next_turn()
            self._update_clocks()
            self.ctx.refresh()

    def _can_take_back(self):
        return self.game is not None and self.game.allows(TAKE_BACK) and any(
            node.parent.turn() == self.game.user_color for node in self.ctx.model.game.mainline())

    # --- UI ---------------------------------------------------------------

    def build_panel(self, parent):
        frame = tk.Frame(parent, bg=parent["bg"])
        frame.columnconfigure((0, 1), weight=1)
        self._labels = {"goal": widgets.label(frame, bold=True, wrap=True),
                        "level": widgets.label(frame, wrap=True),
                        "counters": widgets.label(frame, wrap=True)}
        for row, name in enumerate(("goal", "level", "counters")):
            self._labels[name].grid(row=row, column=0, columnspan=2, sticky="ew", padx=4)
        self._suggest_var = tk.BooleanVar(value=self._suggest())
        widgets.checkbox(frame, S.LEARN_SUGGEST, self._suggest_var, self._suggest_changed).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(2, 4))
        self._buttons = {
            "take_back": widgets.button(frame, S.MODE_TAKE_BACK, self.take_back),
            "resign": widgets.button(frame, S.MODE_RESIGN, self.resign),
            "open": widgets.button(frame, S.MODE_OPEN_IN_BOARD, self.open_in_board_mode),
        }
        self._buttons["take_back"].grid(row=4, column=0, sticky="ew", padx=2)
        self._buttons["resign"].grid(row=4, column=1, sticky="ew", padx=2)
        self._buttons["open"].grid(row=5, column=0, columnspan=2, sticky="ew", padx=2, pady=(4, 0))
        self._update_buttons()
        self._update_panel()
        return frame

    def _suggest_changed(self):
        self.ctx.settings["end_suggest"] = self._suggest_var.get()
        if self._running() and not self.game.is_computer_turn(self._tip()):
            self._user_turn()
        self.ctx.refresh()

    def _button_states(self):
        return {**super()._button_states(), "take_back": self._can_take_back()}

    def _game_over(self):
        super()._game_over()
        self._update_panel()

    def _update_panel(self):
        if not self._labels or not self._labels["goal"].winfo_exists() or self.game is None:
            return
        game = self.game
        difficulty = game.sample.difficulty
        self._labels["goal"].configure(text=game.goal_text())
        total = next((count for d, _, count in self._collection.levels() if d == difficulty), 0)
        self._labels["level"].configure(text=S.END_PLAYED.format(
            level=difficulty, played=self._deck.played(difficulty), total=total))
        self._labels["counters"].configure(text=S.END_COUNTERS.format(
            hints=game.hints_used, take_backs=game.take_backs))
        self._update_buttons()

    def menu_items(self):
        return [
            MenuItem(S.MODE_TAKE_BACK, self.take_back, self._can_take_back),
            MenuItem(S.MODE_RESIGN, self.resign, self._running),
            MenuItem(S.MODE_OPEN_IN_BOARD, self.open_in_board_mode,
                     lambda: self.game is not None and self.game.over),
        ]
