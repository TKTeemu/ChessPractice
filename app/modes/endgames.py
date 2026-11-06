"""EndgameMode: the user plays a stored endgame position against the computer.

The rules live in EndgameGame and the positions in endgames.py; this class connects them to
the window: the level dialog, drawing a position, Retry, the progress kept in settings, the
computer's stored defence after a short pause, engine analyses (they judge the user's moves
and give the computer's reply), the success light, suggestion arrows and the panel. The clock
comes from TimedGameMode. This is practice, not a game to give up, so there is no Resign
command and no question about it; a running attempt is simply resigned when it is left.
"""

import tkinter as tk
from tkinter import messagebox

import chess

from .. import strings as S
from .. import widgets
from ..dialogs import choose_endgame
from ..endgame_game import LEVEL, EndgameGame
from ..engines import Analysis
from ..model import visible_comment
from .base import MenuItem
from .timed_mode import TimedGameMode

TREE_DELAY_MS = 400   # a stored reply waits a moment, so that it is seen as a separate move

# Kinds of engine request: the score of the position before the user's move (when not yet
# known), the score after it together with the computer's reply, and the user's best move
# for the suggestion arrow.
BASELINE, REPLY, HINT = "baseline", "reply", "hint"
PLAYED, SOLVED = "played", "solved"   # settings["end_progress"]: position key -> one of these


class EndgameMode(TimedGameMode):
    key = "end_practice"
    label = S.MODE_ENDGAMES
    takes_back = True
    back_takes_back = True
    SETTINGS = {
        "end_difficulty": 1,
        "end_minutes": 15,
        "end_suggest": False,
        "end_progress": {},
    }

    def __init__(self, ctx):
        super().__init__(ctx)
        self._labels = {}
        self._suggest_var = None
        self._pending = None   # (request id, kind, ply) of the engine request on its way

    # --- Life cycle -------------------------------------------------------

    def _engine(self):
        """The first installed engine that can judge moves, else the first one that can play."""
        available, _ = self.engine_choices()
        cls = next((cls for cls in available if cls.can_analyse), available[0])
        return cls(self.ctx.settings, self.ctx.app_dir)

    def choose(self):
        ctx = self.ctx
        collection = ctx.assets.endgames()
        if not collection.all:
            messagebox.showerror(S.END_TITLE, S.END_NO_POSITIONS.format(folder=ctx.assets.endgame_folder),
                                 parent=ctx.root)
            return None
        available, _ = self.engine_choices()
        notes = [] if any(cls.can_analyse for cls in available) else [S.END_NO_ENGINE]
        if collection.errors:
            notes.append(S.END_FILE_ERRORS.format(
                errors="\n".join(f"{name}: {error}" for name, error in collection.errors[:5])))
        levels = collection.levels()
        deck = ctx.assets.endgame_deck()
        played = {d: deck.played(d) for d, _, _ in levels}
        solved = {d: self._solved(d) for d, _, _ in levels}
        return choose_endgame(ctx.root, levels, played, solved, notes, ctx.settings)

    def start(self, config):
        ctx = self.ctx
        ctx.settings["end_difficulty"] = config["difficulty"]
        ctx.settings["end_minutes"] = config["minutes"]
        key = config.get("sample")   # Retry: the same position again; otherwise draw one
        sample = (ctx.assets.endgames().sample(key) if key
                  else ctx.assets.endgame_deck().draw(config["difficulty"]))
        engine = self._engine()
        self.game = EndgameGame(sample, engine.name, engine.can_analyse, config["minutes"])
        self._record_progress(PLAYED)

        self.start_game(chess.Board(sample.fen), intro=sample.game.comment.strip())
        ctx.set_flipped(self.game.user_color == chess.BLACK)
        self.start_engine(engine, LEVEL)
        self.start_clock()
        self._next_turn()

    def confirm_leave(self):
        return True

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

    def turn_text(self):
        if self.game is None:
            return None
        model = self.ctx.model
        return self.game.turn_text(model.board, model.at_end())

    def light(self):
        return self.game.light if self.game else None

    def light_text(self):
        return self.game.light_text if self.game else ""

    def hint_arrows(self):
        if self.game is None or not self._suggest() or not self.ctx.model.at_end():
            return []
        return self.game.hints(self._tip())

    def hints_shown(self, hints):
        if self.game is not None:
            self.game.note_hints(self._tip(), hints)
            self._update_panel()

    # --- Progress ---------------------------------------------------------

    def _record_progress(self, state):
        """Remember in settings how far the position has got; solved stays solved."""
        settings, key = self.ctx.settings, self.game.sample.key
        progress = settings["end_progress"]
        if progress.get(key) != SOLVED and progress.get(key) != state:
            settings["end_progress"] = {**progress, key: state}

    def _solved(self, difficulty):
        progress = self.ctx.settings["end_progress"]
        return sum(progress.get(s.key) == SOLVED for s in self.ctx.assets.endgames().samples(difficulty))

    def _note_solved(self):
        if self.game.light == "success":
            self._record_progress(SOLVED)

    # --- Retry --------------------------------------------------------------

    def retry(self):
        """The same position again. The attempt is replaced without any question, because Retry
        is pressed again and again."""
        config = {"difficulty": self.game.sample.difficulty, "minutes": self.ctx.settings["end_minutes"],
                  "sample": self.game.sample.key}
        self.ctx.set_mode(self.key, config=config, discard=True)

    # --- Moves ------------------------------------------------------------

    def after_move(self):
        super().after_move()
        model = self.ctx.model
        if self.game.last_comment and not visible_comment(model.node.comment):
            model.set_comment(model.node, self.game.last_comment)
        self._note_solved()
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
            self.ctx.update_status()   # the suggestion arrow

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
        widgets.button(frame, S.END_RETRY, self.retry).grid(row=4, column=0, sticky="ew", padx=2)
        self._buttons = {"open": widgets.button(frame, S.MODE_OPEN_IN_BOARD, self.open_in_board_mode)}
        self._buttons["open"].grid(row=4, column=1, sticky="ew", padx=2)
        self._update_panel()
        return frame

    def _suggest_changed(self):
        self.ctx.settings["end_suggest"] = self._suggest_var.get()
        if self._running() and not self.game.is_computer_turn(self._tip()):
            self._user_turn()
        self.ctx.update_status()

    def _game_over(self):
        super()._game_over()
        self._note_solved()
        self._update_panel()

    def _update_panel(self):
        if not self._labels or self.game is None:
            return
        game = self.game
        difficulty = game.sample.difficulty
        self._labels["goal"].configure(text=game.goal_text())
        assets = self.ctx.assets
        self._labels["level"].configure(text=S.END_PLAYED.format(
            level=difficulty, played=assets.endgame_deck().played(difficulty),
            total=len(assets.endgames().samples(difficulty)), solved=self._solved(difficulty)))
        self._labels["counters"].configure(text=S.END_COUNTERS.format(
            hints=game.hints_used, take_backs=game.take_backs))
        self._update_buttons()

    def menu_items(self):
        return [
            MenuItem(S.MODE_TAKE_BACK, self.take_back, self.can_take_back),
            MenuItem(S.END_RETRY, self.retry, lambda: self.game is not None),
            MenuItem(S.MODE_OPEN_IN_BOARD, self.open_in_board_mode,
                     lambda: self.game is not None and self.game.over),
        ]
