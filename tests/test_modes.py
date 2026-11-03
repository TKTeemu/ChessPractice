import chess

from app.model import GameModel
from app.modes import MODES, ModeContext, mode_class
from app.modes.board import BoardMode


def fake_context(tmp_path):
    from app.settings import Settings

    calls = []

    def record(name):
        return lambda *args, **kw: calls.append((name, args))

    ctx = ModeContext(root=None, model=GameModel(), settings=Settings(tmp_path / "settings.json"),
                      play_move=record("play_move"), new_game=record("new_game"), refresh=record("refresh"),
                      set_flipped=record("set_flipped"), set_mode=record("set_mode"),
                      confirm_discard=lambda: True, set_clocks=record("set_clocks"),
                      play_sound=record("play_sound"), button=record("button"),
                      take_back=record("take_back"))
    return ctx, calls


def test_every_mode_has_unique_key_and_label():
    keys = [cls.key for cls in MODES]
    assert len(keys) == len(set(keys))
    assert all(cls.key and cls.label for cls in MODES)
    assert MODES[0] is BoardMode and mode_class("board") is BoardMode


def test_board_mode_allows_everything(tmp_path):
    ctx, _ = fake_context(tmp_path)
    mode = BoardMode(ctx)
    assert mode.activate() and mode.confirm_leave()
    for command in ("delete_last", "edit_tree", "paste", "open", "navigate", "edit_comment"):
        assert mode.allows(command)
    assert mode.can_move(chess.WHITE) and mode.can_move(chess.BLACK)
    assert mode.status_text() is None and not mode.new_game()
    mode.deactivate()


def test_vs_computer_mode_before_a_game_is_harmless(tmp_path):
    ctx, calls = fake_context(tmp_path)
    mode = mode_class("vs_computer")(ctx)
    assert mode.confirm_leave()
    assert not mode.can_move(chess.WHITE)
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
