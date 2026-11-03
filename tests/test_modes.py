import time
from pathlib import Path

import chess

from app.commands import ALL_COMMANDS
from app.model import GameModel
from app.modes import MODES, ModeContext, mode_class, mode_settings
from app.modes.board import BoardMode
from app.settings import DEFAULTS, Settings

ROOT = Path(__file__).resolve().parent.parent


class FakeRoot:
    """Stands in for tk.Tk: after() only stores the callback; run_timers() runs those due."""

    def __init__(self):
        self.timers = {}
        self._next = 0

    def after(self, ms, callback):
        self._next += 1
        self.timers[self._next] = callback
        return self._next

    def after_cancel(self, after_id):
        self.timers.pop(after_id, None)

    def run_timers(self):
        due, self.timers = self.timers, {}
        for callback in due.values():
            callback()


def fake_context(tmp_path):
    calls = []

    def record(name):
        return lambda *args, **kw: calls.append((name, args))

    model = GameModel()

    def new_game(board=None):
        model.new_game(board)
        calls.append(("new_game", (board,)))

    ctx = ModeContext(root=FakeRoot(), model=model, settings=Settings(tmp_path / "settings.json", mode_settings()),
                      app_dir=ROOT, play_move=record("play_move"), new_game=new_game,
                      refresh=record("refresh"), set_flipped=record("set_flipped"), set_mode=record("set_mode"),
                      set_clocks=record("set_clocks"), play_sound=record("play_sound"),
                      take_back=record("take_back"))
    return ctx, calls


def played_moves(calls):
    return [args[0] for name, args in calls if name == "play_move"]


def test_every_mode_has_unique_key_and_label():
    keys = [cls.key for cls in MODES]
    assert len(keys) == len(set(keys))
    assert all(cls.key and cls.label for cls in MODES)
    assert MODES[0] is BoardMode and mode_class("board") is BoardMode


def test_mode_settings_are_prefixed_and_do_not_clash():
    seen = set(DEFAULTS)
    for cls in MODES:
        for key in cls.SETTINGS:
            assert key not in seen, key
            assert key.startswith(cls.key.split("_")[0] + "_"), key
            seen.add(key)


def test_allowed_command_sets_use_known_names():
    from app.computer_game import ComputerGame
    from app.learning_game import LearningGame
    for cls in (ComputerGame, LearningGame):
        assert cls.ALLOWED_DURING_GAME <= ALL_COMMANDS and cls.ALLOWED_AFTER_GAME <= ALL_COMMANDS


def test_no_command_names_as_string_literals():
    # allows("...") with a literal would hide a typo; use the constants in app/commands.py
    for path in (ROOT / "app").rglob("*.py"):
        assert 'allows("' not in path.read_text(encoding="utf-8"), path


def test_board_mode_allows_everything(tmp_path):
    ctx, _ = fake_context(tmp_path)
    mode = BoardMode(ctx)
    assert mode.choose() == {} and mode.confirm_leave() and not mode.replaces_game
    mode.start({})
    for command in ALL_COMMANDS:
        assert mode.allows(command)
    assert mode.can_move(chess.WHITE) and mode.can_move(chess.BLACK)
    assert mode.status_text() is None and not mode.new_game()
    mode.leave()
    mode.deactivate()


def test_vs_computer_mode_before_a_game_is_harmless(tmp_path):
    ctx, calls = fake_context(tmp_path)
    mode = mode_class("vs_computer")(ctx)
    assert mode.confirm_leave() and mode.replaces_game
    assert not mode.can_move(chess.WHITE)
    mode.leave()
    mode.deactivate()
    assert ("set_clocks", (None,)) in calls


def test_learn_openings_mode_is_registered_and_harmless_before_a_game(tmp_path):
    ctx, calls = fake_context(tmp_path)
    cls = mode_class("learn_openings")
    assert cls is not None and cls in MODES
    mode = cls(ctx)
    assert mode.confirm_leave() and not mode.can_move(chess.WHITE)
    assert mode.hint_arrows() == [] and mode.status_text() is None
    mode.take_back()
    mode.deactivate()
    assert not any(name == "take_back" for name, _ in calls)


def test_default_mode_hooks(tmp_path):
    ctx, _ = fake_context(tmp_path)
    mode = BoardMode(ctx)
    assert mode.hint_arrows() == [] and mode.show_details and mode.allows("take_back")
    assert not mode_class("vs_computer").show_details and not mode_class("learn_openings").show_details


# --- Games started with start(config), without windows ----------------------

def test_vs_computer_start_as_white_waits_for_the_user(tmp_path):
    ctx, calls = fake_context(tmp_path)
    mode = mode_class("vs_computer")(ctx)
    mode.start({"engine": "random", "level": "random", "color": "white", "start": "initial"})
    try:
        assert ctx.settings["vs_engine"] == "random" and ctx.settings["vs_color"] == "white"
        assert ctx.model.headers["White"] == "You" and ctx.model.headers["Event"] == "vs Computer"
        assert ("set_flipped", (False,)) in calls
        assert mode.can_move(chess.WHITE) and not mode.can_move(chess.BLACK)
        assert not mode.allows("navigate") and mode.status_text() == "Your move"
    finally:
        mode.deactivate()


def test_vs_computer_start_as_black_gets_an_engine_move(tmp_path):
    ctx, calls = fake_context(tmp_path)
    mode = mode_class("vs_computer")(ctx)
    mode.start({"engine": "random", "level": "random", "color": "black", "start": "initial"})
    try:
        assert ("set_flipped", (True,)) in calls and not mode.can_move(chess.BLACK)
        deadline = time.monotonic() + 5
        while not played_moves(calls) and time.monotonic() < deadline:
            ctx.root.run_timers()   # the poll timer reads the worker's result
            time.sleep(0.02)
        moves = played_moves(calls)
        assert len(moves) == 1 and moves[0] in chess.Board().legal_moves
    finally:
        mode.deactivate()


def test_vs_computer_leave_resigns_a_running_game(tmp_path):
    ctx, calls = fake_context(tmp_path)
    mode = mode_class("vs_computer")(ctx)
    mode.start({"engine": "random", "level": "random", "color": "white", "start": "initial"})
    try:
        mode.leave()
        assert mode.game.over and ctx.model.headers["Result"] == "0-1"
        assert mode.confirm_leave()   # nothing left to ask once the game is over
    finally:
        mode.deactivate()


def test_learn_openings_start_plays_the_book_move_for_the_computer(tmp_path):
    ctx, calls = fake_context(tmp_path)
    mode = mode_class("learn_openings")(ctx)
    mode.start({"opening": "reti", "role": "reply", "engine": "random", "level": "random", "vary": False})
    try:
        assert ctx.model.headers["Opening"] and ctx.settings["learn_role"] == "reply"
        assert ("set_flipped", (True,)) in calls
        assert not played_moves(calls)   # the book reply waits BOOK_DELAY_MS
        ctx.root.run_timers()
        assert played_moves(calls) == [chess.Move.from_uci("g1f3")]
    finally:
        mode.deactivate()


def test_deactivate_cancels_pending_computer_moves(tmp_path):
    ctx, calls = fake_context(tmp_path)
    mode = mode_class("learn_openings")(ctx)
    mode.start({"opening": "reti", "role": "reply", "engine": "random", "level": "random", "vary": False})
    mode.deactivate()
    ctx.root.run_timers()
    assert not played_moves(calls) and not ctx.root.timers
