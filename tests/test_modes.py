import time
from pathlib import Path

import chess

from app.assets import Assets
from app.commands import ALL_COMMANDS
from app.model import GameModel
from app.modes import MODES, START_MODE, ModeContext, mode_class, mode_settings
from app.modes.board import BoardMode
from app.settings import DEFAULTS, Settings

ROOT = Path(__file__).resolve().parent.parent
VS_WHITE = {"engine": "random", "level": "random", "color": "white", "start": "initial",
            "minutes": 30, "increment": 0}
LEARN_REPLY = {"opening": "reti", "role": "reply", "engine": "random", "level": "random", "vary": False,
               "suggest_moves": 12}


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

    def new_game(board=None, headers=None, intro=""):
        model.new_game(board, headers, intro)
        calls.append(("new_game", (board,)))

    ctx = ModeContext(root=FakeRoot(), model=model, settings=Settings(tmp_path / "settings.json", mode_settings()),
                      app_dir=ROOT, assets=Assets(ROOT), play_move=record("play_move"), new_game=new_game,
                      update_status=record("update_status"), set_flipped=record("set_flipped"),
                      set_mode=record("set_mode"),
                      set_clocks=record("set_clocks"), play_sound=record("play_sound"),
                      take_back=record("take_back"))
    return ctx, calls


def played_moves(calls):
    return [args[0] for name, args in calls if name == "play_move"]


def test_every_mode_has_unique_key_and_label():
    keys = [cls.key for cls in MODES]
    assert len(keys) == len(set(keys))
    assert all(cls.key and cls.label for cls in MODES)
    assert mode_class("board") is BoardMode


def test_board_is_last_in_the_menu_but_the_program_starts_in_it():
    assert MODES[-1] is BoardMode and START_MODE is BoardMode
    assert BoardMode.label == "Board (free analysis)"


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
    assert mode.takes_back and not mode.can_take_back()
    mode.take_back()
    mode.deactivate()
    assert not any(name == "take_back" for name, _ in calls)


def test_default_mode_hooks(tmp_path):
    ctx, _ = fake_context(tmp_path)
    mode = BoardMode(ctx)
    assert mode.hint_arrows() == [] and mode.show_details and mode.allows("take_back")
    assert not mode.takes_back and not mode.can_take_back()   # no Take Back button in Board mode
    assert not mode_class("vs_computer").takes_back
    assert not mode_class("vs_computer").show_details and not mode_class("learn_openings").show_details


# --- Games started with start(config), without windows ----------------------

def test_vs_computer_start_as_white_waits_for_the_user(tmp_path):
    ctx, calls = fake_context(tmp_path)
    mode = mode_class("vs_computer")(ctx)
    mode.start(VS_WHITE)
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
    mode.start({**VS_WHITE, "color": "black"})
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
    mode.start(VS_WHITE)
    try:
        mode.leave()
        assert mode.game.over and ctx.model.headers["Result"] == "0-1"
        assert mode.confirm_leave()   # nothing left to ask once the game is over
    finally:
        mode.deactivate()


def test_learn_openings_start_plays_the_book_move_for_the_computer(tmp_path):
    ctx, calls = fake_context(tmp_path)
    mode = mode_class("learn_openings")(ctx)
    mode.start(LEARN_REPLY)
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
    mode.start(LEARN_REPLY)
    mode.deactivate()
    ctx.root.run_timers()
    assert not played_moves(calls) and not ctx.root.timers


# --- Endgame Practice -------------------------------------------------------

def endgame_mode(tmp_path, monkeypatch, key="saavedra"):
    from app.engines import RandomEngine
    from app.modes.endgames import EndgameMode
    ctx, calls = fake_context(tmp_path)
    mode = EndgameMode(ctx)
    monkeypatch.setattr(EndgameMode, "_engine", lambda self: RandomEngine(seed=1))
    monkeypatch.setattr(ctx.assets.endgame_deck(), "draw", lambda difficulty: ctx.assets.endgames().sample(key))
    return mode, ctx, calls


def user_plays(mode, ctx, san):
    """What MainWindow.play_move does: the model plays the move, then the mode is told."""
    ctx.model.play(ctx.model.board.parse_san(san))
    mode.after_move()


def test_endgame_mode_is_registered_and_harmless_before_a_game(tmp_path):
    ctx, calls = fake_context(tmp_path)
    cls = mode_class("end_practice")
    assert cls in MODES and cls.label == "Endgame Practice…"
    mode = cls(ctx)
    assert mode.confirm_leave() and not mode.can_move(chess.WHITE) and mode.replaces_game
    assert mode.light() is None and mode.subtitle() is None and mode.hint_arrows() == []
    assert mode.takes_back and not mode.can_take_back()
    mode.take_back()
    mode.deactivate()
    assert not any(name == "take_back" for name, _ in calls)


def test_endgame_start_sets_up_the_position(tmp_path, monkeypatch):
    mode, ctx, calls = endgame_mode(tmp_path, monkeypatch)
    mode.start({"difficulty": 5, "minutes": 10})
    try:
        assert ctx.settings["end_difficulty"] == 5 and ctx.settings["end_minutes"] == 10
        headers = ctx.model.headers
        assert headers["Event"] == "Endgame practice" and headers["EndgameKey"] == "saavedra"
        assert ctx.model.board.fen() == mode.game.sample.fen and ("set_flipped", (False,)) in calls
        assert mode.can_move(chess.WHITE) and not mode.can_move(chess.BLACK)
        assert mode.light() == "pending" and "Saavedra" in mode.title() and "1895" in mode.subtitle()
        assert mode.allows("take_back") and mode.allows("navigate")
        assert mode.score_text() is None
    finally:
        mode.deactivate()


def test_endgame_computer_plays_the_stored_defence(tmp_path, monkeypatch):
    mode, ctx, calls = endgame_mode(tmp_path, monkeypatch)
    mode.start({"difficulty": 5, "minutes": 10})
    try:
        user_plays(mode, ctx, "c7")
        assert not played_moves(calls)   # the stored reply waits TREE_DELAY_MS
        ctx.root.run_timers()
        assert played_moves(calls) == [chess.Move.from_uci("d5d6")]
        assert mode.game.judgements == {1: "ok"}
    finally:
        mode.deactivate()


def test_endgame_suggestions_and_take_back(tmp_path, monkeypatch):
    mode, ctx, calls = endgame_mode(tmp_path, monkeypatch)
    ctx.settings["end_suggest"] = True
    mode.start({"difficulty": 5, "minutes": 10})
    try:
        hints = mode.hint_arrows()
        assert hints == [(chess.C6, chess.C7, "main")] and mode.game.hints_used == 0   # only a question
        mode.hints_shown(hints)
        assert mode.game.hints_used == 1
        user_plays(mode, ctx, "Kb7")   # off the solution; no engine to judge it
        assert mode.game.light == "pending" and "No engine" in mode.status_text()
        assert mode.can_take_back()
        mode.take_back()
        assert ("take_back", (chess.WHITE,)) in calls   # MainWindow removes the moves
    finally:
        mode.deactivate()


def test_endgame_leave_resigns_and_the_light_turns_red(tmp_path, monkeypatch):
    mode, ctx, calls = endgame_mode(tmp_path, monkeypatch)
    mode.start({"difficulty": 5, "minutes": 10})
    try:
        mode.leave()
        assert mode.game.over and mode.light() == "fail" and ctx.model.headers["Result"] == "0-1"
        assert not mode.allows("take_back") and not mode.can_take_back()
    finally:
        mode.deactivate()


# --- Registry of engines, shared logic ---------------------------------------

def test_endgame_engine_comes_from_the_registry(tmp_path):
    from app.engines import ENGINES
    from app.modes.endgames import EndgameMode
    ctx, _ = fake_context(tmp_path)
    available = [cls for cls in ENGINES if cls.available(ctx.settings, ctx.app_dir)]
    expected = next((cls for cls in available if cls.can_analyse), available[0])
    assert type(EndgameMode(ctx)._engine()) is expected
