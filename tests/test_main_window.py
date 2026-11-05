"""Integration tests: the real MainWindow and modes on a real Tk root, with the windows hidden
and dialogs replaced. They cover what the mode tests cannot, because those fake play_move and the
view updates. Skipped where Tk cannot open a window.
"""

import json
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import chess
import pytest

from app.commands import NAVIGATE
from app.engines import Analysis, Engine
from app.main_window import MainWindow, restored_geometry
from app.modes import mode_settings
from app.modes.board import BoardMode
from app.settings import Settings

ROOT = Path(__file__).resolve().parent.parent
VS = {"engine": "random", "level": "random", "color": "white", "start": "initial", "minutes": 30, "increment": 0}
LEARN = {"opening": "reti", "role": "opening", "engine": "random", "level": "random", "vary": False,
         "suggest_moves": 12}
ENDGAME = {"difficulty": 1, "minutes": 15}


class Answers:
    """What the replaced dialogs answer, and what they were asked."""
    def __init__(self):
        self.save = False          # the save prompt: True, False or None (Cancel)
        self.resign = True
        self.save_path = ""        # the file dialog; "" = Cancel
        self.open_path = ""
        self.errors = []
        self.warnings = []
        self.save_prompts = 0
        self.resign_prompts = 0


@pytest.fixture
def answers(monkeypatch):
    a = Answers()

    def save_prompt(*args, **kw):
        a.save_prompts += 1
        return a.save

    def resign_prompt(*args, **kw):
        a.resign_prompts += 1
        return a.resign

    monkeypatch.setattr(messagebox, "askyesnocancel", save_prompt)
    monkeypatch.setattr(messagebox, "askyesno", resign_prompt)
    monkeypatch.setattr(messagebox, "showerror", lambda title, text, **kw: a.errors.append(text))
    monkeypatch.setattr(messagebox, "showwarning", lambda title, text, **kw: a.warnings.append(text))
    monkeypatch.setattr(filedialog, "asksaveasfilename", lambda **kw: a.save_path)
    monkeypatch.setattr(filedialog, "askopenfilename", lambda **kw: a.open_path)
    return a


def make_window(tmp_path, **saved):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk cannot open a window here")
    root.withdraw()
    settings_path = tmp_path / "settings.json"
    if not settings_path.exists():   # a second window in a test is the program started again
        settings_path.write_text(json.dumps({"sound": False, **saved}), encoding="utf-8")
    return MainWindow(root, ROOT, Settings(settings_path, mode_settings()))


@pytest.fixture
def win(tmp_path, answers):
    window = make_window(tmp_path)
    yield window
    close(window)


def close(window):
    window.mode.deactivate()
    try:
        window.root.destroy()
    except tk.TclError:
        pass   # the test closed it


def pump(window, until, seconds=5):
    """Run the event loop until `until()` is true."""
    deadline = time.monotonic() + seconds
    while not until():
        assert time.monotonic() < deadline, "timed out"
        window.root.update()
        time.sleep(0.01)


def play(window, *sans):
    for san in sans:
        window.play_move(window.model.board.parse_san(san))


def comment_text(window):
    return window.comment.get("1.0", "end").strip()


def plies(window):
    return len(list(window.model.game.mainline_moves()))


# --- Bug: saving could leave a stale result on disk -----------------------------

def test_resigning_after_a_save_counts_as_an_unsaved_change(win, answers, tmp_path):
    answers.save_path = str(tmp_path / "game.pgn")
    win.set_mode("vs_computer", VS)
    play(win, "e4")
    assert win.files.save()
    assert not win.model.modified and not win.root.title().startswith("*")
    win.mode.resign()
    assert win.model.modified and win.root.title().startswith("*")


def test_a_new_game_after_a_save_offers_to_save_the_resignation(win, tmp_path, answers):
    path = tmp_path / "game.pgn"
    answers.save_path = str(path)
    win.set_mode("vs_computer", VS)
    play(win, "e4")
    win.files.save()
    assert '[Result "*"]' in path.read_text(encoding="utf-8")
    answers.save = True
    win.set_mode("vs_computer", VS)
    assert answers.save_prompts == 1
    assert '[Result "0-1"]' in path.read_text(encoding="utf-8")


def test_a_game_without_moves_is_left_without_a_save_prompt(win, answers):
    win.set_mode("vs_computer", VS)
    win.set_mode("vs_computer", VS)
    assert answers.save_prompts == 0


# --- Closing the program asks nothing --------------------------------------------

def test_exit_with_unsaved_moves_closes_without_questions(tmp_path, answers):
    win = make_window(tmp_path)
    play(win, "e4")
    assert win.model.modified
    win.exit()
    assert answers.save_prompts == 0 and answers.resign_prompts == 0
    with pytest.raises(tk.TclError):
        win.root.winfo_exists()   # the window is gone


def test_exit_during_a_game_does_not_resign_it_or_touch_its_file(tmp_path, answers):
    win = make_window(tmp_path)
    path = tmp_path / "game.pgn"
    answers.save_path = str(path)
    win.set_mode("vs_computer", VS)
    play(win, "e4")
    win.files.save()
    saved = path.read_text(encoding="utf-8")
    pump(win, lambda: plies(win) == 2)
    mode = win.mode
    win.exit()
    assert answers.save_prompts == 0 and answers.resign_prompts == 0
    assert not mode.game.over and path.read_text(encoding="utf-8") == saved


# --- Bug: a typed comment could vanish -------------------------------------------

def test_toggling_suggestions_keeps_the_comment_being_typed(win):
    win.set_mode("learn_openings", LEARN)
    play(win, "Nf3")
    win.back()
    win.forward()
    win.comment.delete("1.0", "end")
    win.comment.insert("1.0", "being typed")
    win.mode._suggest_var.set(False)
    win.mode._suggest_changed()
    assert comment_text(win) == "being typed"


# --- Bug: cancelling the save prompt still resigned the game ----------------------

def test_cancelling_save_as_on_a_new_game_does_not_resign(win, answers):
    win.set_mode("vs_computer", VS)
    mode = win.mode
    play(win, "e4")
    answers.save = True
    answers.save_path = ""   # Cancel in the file dialog
    win.set_mode("vs_computer", VS)
    assert win.mode is mode
    assert not win.mode.game.over and win.model.headers["Result"] == "*"


def test_save_as_on_a_new_game_saves_the_resigned_game(win, tmp_path, answers):
    path = tmp_path / "game.pgn"
    win.set_mode("vs_computer", VS)
    play(win, "e4")
    answers.save = True
    answers.save_path = str(path)
    win.set_mode("vs_computer", VS)
    assert '[Result "0-1"]' in path.read_text(encoding="utf-8")


def test_answering_no_to_resign_keeps_playing(win, answers):
    win.set_mode("vs_computer", VS)
    mode = win.mode
    play(win, "e4")
    answers.resign = False
    win.set_mode("vs_computer", VS)
    assert win.mode is mode and not win.mode.game.over and answers.save_prompts == 0


# --- Bug: the left arrow deleted moves in Learn Openings ---------------------------

def test_left_arrow_browses_in_learn_openings(win):
    win.set_mode("learn_openings", LEARN)
    play(win, "Nf3")
    pump(win, lambda: plies(win) == 2)   # the book reply
    play(win, "g3")
    pump(win, lambda: plies(win) == 4)
    win.go_start()
    win.forward()
    win.forward()
    win.back()
    assert plies(win) == 4 and win.model.node.ply() == 1
    assert win.take_back_button.winfo_manager() and win.take_back_button["state"] == "normal"


def test_take_back_button_removes_the_users_move_and_the_reply(win):
    win.set_mode("learn_openings", LEARN)
    play(win, "Nf3")
    pump(win, lambda: plies(win) == 2)
    win.take_back_button.invoke()
    assert plies(win) == 0 and win.take_back_button["state"] == "disabled"


def test_take_back_button_is_only_in_modes_that_have_it(win):
    assert not win.take_back_button.winfo_manager()
    win.set_mode("vs_computer", VS)
    assert not win.take_back_button.winfo_manager()


# --- Bug: Learn Openings could hang ----------------------------------------------

def test_take_back_before_the_first_user_move_does_not_stop_the_computer(win):
    win.set_mode("learn_openings", {**LEARN, "role": "reply"})
    win.mode.take_back()      # during the pause before the book reply
    win.delete_last()         # Ctrl+Z means the same here
    pump(win, lambda: plies(win) == 1)
    assert win.mode.status_text() == "Your move"


# --- Bug: any update cleared the selection, a drag and the arrows -----------------

def test_a_status_update_keeps_the_selection_and_the_arrows(win):
    win.board.update()
    win.board.selected = chess.E2
    win.board.targets = {chess.E3, chess.E4}
    win.board.arrows.add((chess.E2, chess.E4))
    win.update_status()
    win.position_changed()        # the same position
    assert win.board.selected == chess.E2 and win.board.arrows
    play(win, "e4")               # another position
    assert win.board.selected is None and not win.board.arrows


def test_a_game_ending_during_a_drag_stops_the_move(win):
    win.set_mode("vs_computer", VS)
    win.board.selected = chess.E2
    win.board.targets = {chess.E4}
    win.mode.resign()
    assert win.board.selected is None
    win.user_move(chess.E2, chess.E4, None)
    assert plies(win) == 0


# --- Bugs: invalid positions, bad settings ---------------------------------------

def test_a_fen_without_kings_is_rejected(win, answers):
    win.fen_var.set("8/8/8/8/8/8/8/8 w - - 0 1")
    win._fen_entered(None)
    assert answers.errors and win.model.fen() == chess.STARTING_FEN


def test_a_bad_board_theme_does_not_stop_the_program(tmp_path, answers):
    win = make_window(tmp_path, board_theme="no such theme", piece_set="neither")
    try:
        win.board.redraw()
        assert win.settings["board_theme"] == "green" and win.settings["piece_set"] == "cburnett"
    finally:
        close(win)


def test_a_bad_window_geometry_does_not_stop_the_program(tmp_path, answers):
    close(make_window(tmp_path, window_geometry="big, please"))


def test_restored_geometry():
    desktop = (0, 0, 1920, 1080)
    assert restored_geometry("900x700+100+50", desktop) == "900x700+100+50"
    assert restored_geometry("900x700+3000+50", desktop) == "900x700"     # on a monitor now gone
    assert restored_geometry("900x700+-1500+50", desktop) == "900x700"
    assert restored_geometry("900x700+100+-500", desktop) == "900x700"    # the title bar is above the desktop
    assert restored_geometry("900x700+-1500+50", (-1920, 0, 3840, 1080)) == "900x700+-1500+50"
    assert restored_geometry("", desktop) is None and restored_geometry("nonsense", desktop) is None


# --- Opening files ---------------------------------------------------------------

def test_a_file_with_a_skipped_game_is_not_overwritten_by_save(win, answers, tmp_path):
    path = tmp_path / "games.pgn"
    path.write_text("1. e4 e5 *\n\n1. e4 e5 2. Ke3 *\n", encoding="utf-8")
    answers.open_path = str(path)
    win.files.open_file()
    assert answers.warnings and "Game 2" in answers.warnings[0]
    assert plies(win) == 2 and win.files.path is None


def test_opening_a_good_single_game_keeps_the_path(win, answers, tmp_path):
    path = tmp_path / "game.pgn"
    path.write_text("1. e4 e5 *\n", encoding="utf-8")
    answers.open_path = str(path)
    win.files.open_file()
    assert not answers.warnings and win.files.path == path


def test_a_latin1_name_survives_opening_and_saving(win, answers, tmp_path):
    path = tmp_path / "old.pgn"
    path.write_bytes('[White "Mäkinen"]\n\n1. e4 *\n'.encode("cp1252"))
    answers.open_path = str(path)
    win.files.open_file()
    win.files.save()
    assert '[White "Mäkinen"]' in path.read_text(encoding="utf-8")


# --- Browsing ----------------------------------------------------------------------

def test_play_vs_computer_can_be_browsed_only_after_the_game(win):
    win.set_mode("vs_computer", VS)
    play(win, "e4")
    pump(win, lambda: plies(win) == 2)
    win.back()
    assert win.model.at_end() and win.nav_buttons["prev"]["state"] == "disabled"
    assert win.status["text"] == "Moves can be browsed when the game has finished."
    win.mode.resign()
    assert win.nav_buttons["prev"]["state"] == "normal"
    win.back()
    assert win.model.node.ply() == 1 and plies(win) == 2
    assert not win.mode.can_move(chess.WHITE)


def test_endgame_practice_can_be_browsed_during_the_game(win):
    win.set_mode("end_practice", ENDGAME)
    assert win.nav_buttons["prev"]["state"] == "normal" and win.mode.allows(NAVIGATE)


def test_blocked_commands_say_why_and_the_status_comes_back(win, monkeypatch):
    monkeypatch.setattr("app.main_window.NOTICE_MS", 1)
    win.set_mode("vs_computer", VS)
    normal = win.status["text"]
    win.files.open_file()
    win.files.paste()
    assert win.status["text"] != normal
    pump(win, lambda: win.status["text"] == normal)


def test_fen_field_is_readable_when_read_only(win):
    win.set_mode("vs_computer", VS)
    assert win.fen_entry["state"] == "readonly"
    assert win.fen_entry["readonlybackground"] == win.fen_entry["background"]


def test_clicking_elsewhere_takes_focus_from_the_comment(tmp_path, answers):
    win = make_window(tmp_path)
    try:
        win.root.deiconify()
        win.root.update()
        win.root.focus_force()
        win.comment.focus_force()
        win.root.update()
        assert win.root.focus_get() is win.comment
        win.nav_buttons["next"].event_generate("<ButtonPress-1>")
        win.root.update()
        assert win.root.focus_get() is win.board
        win.comment.focus_force()
        win.root.update()
        win.movelist.text.event_generate("<Button-1>", x=5, y=5)
        win.root.update()
        assert win.root.focus_get() is win.movelist.text
    finally:
        close(win)


# --- Undo ------------------------------------------------------------------------

def test_deleted_moves_can_be_restored(win):
    play(win, "e4", "e5", "Nf3")
    win.back()
    win.back()     # at 1. e4
    win.edit_tree("delete_from_here", win.model.node)
    assert plies(win) == 0
    win.restore_deleted()
    assert plies(win) == 3 and win.model.node.ply() == 1
    win.go_end()
    win.delete_last()
    assert plies(win) == 2
    win.restore_deleted()
    assert plies(win) == 3 and win.model.node.ply() == 3


def test_delete_from_here_is_disabled_during_a_game(win):
    win.movelist.rebuild()
    win.movelist.menu.entryconfigure(2, state="normal")
    win.set_mode("vs_computer", VS)
    play(win, "e4")
    pump(win, lambda: plies(win) == 2)
    node = win.model.game.variations[0]
    win.movelist._node_at = lambda event: node
    win.movelist.menu.tk_popup = lambda x, y: None
    event = tk.Event()
    event.x_root = event.y_root = 0
    win.movelist._right_click(event)
    assert win.movelist.menu.entrycget(2, "state") == "disabled"


# --- Endgame Practice: buttons, retry, progress ------------------------------------

def widget_texts(widget):
    """The text of this widget and of all the widgets inside it."""
    texts = {str(widget.cget("text"))} if "text" in widget.keys() else set()
    for child in widget.winfo_children():
        texts |= widget_texts(child)
    return texts


def test_endgame_practice_has_retry_but_no_resign_or_next_position(win):
    win.set_mode("end_practice", ENDGAME)
    labels = {item.label for item in win.mode.menu_items()} | widget_texts(win.root)
    assert "Retry" in labels and "Open in Board Mode" in labels
    assert "Resign" not in labels and "Next Position" not in labels


def test_play_vs_computer_keeps_its_resign_button(win):
    win.set_mode("vs_computer", VS)
    assert "Resign" in widget_texts(win.root)


def test_open_in_board_mode_is_enabled_when_the_attempt_is_over(win):
    win.set_mode("end_practice", ENDGAME)
    button = win.mode._buttons["open"]
    assert button["state"] == "disabled"
    win.mode.leave()
    assert button["state"] == "normal"


def test_new_game_draws_another_position_of_the_chosen_level(win, answers, monkeypatch):
    win.set_mode("end_practice", ENDGAME)
    first = win.mode.game.sample
    monkeypatch.setattr("app.modes.endgames.choose_endgame", lambda *args: ENDGAME)
    win.new_game()
    assert win.mode.game.sample is not first
    assert win.mode.game.sample.difficulty == first.difficulty


def test_retry_plays_the_same_position_again(win, answers):
    win.set_mode("end_practice", ENDGAME)
    first = win.mode.game.sample
    win.mode.retry()
    assert win.mode.game.sample is first and not win.mode.game.over
    assert answers.save_prompts == 0 and answers.resign_prompts == 0


def test_leaving_endgame_practice_never_asks_to_resign(win, answers, monkeypatch):
    monkeypatch.setattr("app.modes.endgames.choose_endgame", lambda *args: ENDGAME)
    win.set_mode("end_practice", ENDGAME)
    win.mode.retry()
    win.new_game()
    old = win.mode
    win.set_mode("board")
    assert win.mode is not old and old.game.over
    assert answers.resign_prompts == 0


def test_the_save_prompt_stays_when_a_new_game_replaces_an_attempt(win, answers, monkeypatch):
    monkeypatch.setattr("app.modes.endgames.choose_endgame", lambda *args: ENDGAME)
    win.set_mode("end_practice", ENDGAME)
    win.play_move(next(iter(win.model.board.legal_moves)))
    win.new_game()
    assert answers.save_prompts == 1 and answers.resign_prompts == 0


def test_endgame_progress_survives_a_restart(tmp_path, answers):
    win = make_window(tmp_path)
    win.set_mode("end_practice", ENDGAME)
    key = win.mode.game.sample.key
    win.settings["end_progress"] = {**win.settings["end_progress"], "kept": "solved"}
    win.exit()

    again = make_window(tmp_path)
    try:
        deck = again.ctx.assets.endgame_deck()
        assert again.settings["end_progress"][key] == "played" and deck.played(1) == 1
        assert all(deck.draw(1).key != key for _ in range(len(again.ctx.assets.endgames().samples(1)) - 1))
    finally:
        close(again)


def test_a_solved_position_is_recorded_and_stays_solved(win):
    win.set_mode("end_practice", ENDGAME)
    win.mode.game.solved_ply = 1
    win.mode._note_solved()
    key = win.mode.game.sample.key
    assert win.settings["end_progress"][key] == "solved"
    win.mode._record_progress("played")
    assert win.settings["end_progress"][key] == "solved"
    assert win.mode._solved(1) == 1


def test_hints_are_counted_once_per_position(win):
    win.settings["end_suggest"] = True
    win.set_mode("end_practice", ENDGAME)
    win.update_status()
    win.update_status()
    win.mode.hint_arrows()   # a question: no side effects
    assert win.mode.game.hints_used == 1


# --- Engine analysis in Board mode -------------------------------------------------

class FakeAnalyser(Engine):
    key = "fake"
    name = "Fake"
    can_analyse = True
    searches = 0

    def analyse(self, board, level, stop):
        type(self).searches += 1
        move = next(iter(board.legal_moves))
        return Analysis(move, cp=35, pv=(move,))

    def best_move(self, board, level, stop):
        return next(iter(board.legal_moves))


def test_analysis_shows_score_and_arrow_and_stops_when_unticked(win, monkeypatch):
    monkeypatch.setattr(BoardMode, "_engine_class", lambda self: FakeAnalyser)
    FakeAnalyser.searches = 0
    win._build_mode_panel()
    mode = win.mode
    mode._var.set(True)
    mode._toggled()
    pump(win, lambda: win.board.hints)
    assert "+0.35" in mode._label["text"]
    pump(win, lambda: FakeAnalyser.searches >= 2)   # the quick search, then the longer one

    play(win, "e4")
    assert not win.board.hints                       # the old arrow is gone at once
    pump(win, lambda: win.board.hints)
    assert "-0.35" in mode._label["text"]            # from White's point of view; Black to move

    mode._var.set(False)
    mode._toggled()
    assert not win.board.hints and mode.worker is None and not mode._label["text"]


def test_analysis_is_off_by_default_and_starts_no_engine(win):
    assert win.mode.worker is None and not win.settings["board_analysis"]
    play(win, "e4")
    win.root.update()
    assert win.mode.worker is None


def test_analysis_engine_failure_turns_it_off_with_a_message(win, monkeypatch):
    from app.engines import EngineError

    class Failing(FakeAnalyser):
        def analyse(self, board, level, stop):
            raise EngineError("boom")

    monkeypatch.setattr(BoardMode, "_engine_class", lambda self: Failing)
    win._build_mode_panel()
    win.mode._var.set(True)
    win.mode._toggled()
    pump(win, lambda: "boom" in win.mode._label["text"])
    assert not win.settings["board_analysis"] and win.mode.worker is None


def test_analysis_ends_when_the_mode_is_left(win, monkeypatch):
    monkeypatch.setattr(BoardMode, "_engine_class", lambda self: FakeAnalyser)
    win._build_mode_panel()
    board_mode = win.mode
    board_mode._var.set(True)
    board_mode._toggled()
    pump(win, lambda: win.board.hints)
    win.set_mode("vs_computer", VS)
    assert board_mode.worker is None and not win.board.hints


# --- Settings that used to be only in settings.json ---------------------------------

def test_clock_choices_from_the_dialog_reach_the_game(win):
    win.set_mode("vs_computer", {**VS, "minutes": 5, "increment": 3})
    assert win.settings["vs_minutes"] == 5 and win.settings["vs_increment"] == 3
    assert win.model.headers["TimeControl"] == "300+3" and not win.model.modified


def test_suggest_moves_choice_reaches_the_game(win):
    win.set_mode("learn_openings", {**LEARN, "suggest_moves": 15})
    assert win.settings["learn_suggest_moves"] == 15 and win.mode.game.suggest_moves == 15


def test_engine_path_dialog_result_is_stored(win, monkeypatch):
    monkeypatch.setattr("app.main_window.choose_engine_path", lambda root, current, folder: "C:/x/sf.exe")
    win._choose_engine_path()
    assert win.settings["engine_path"] == "C:/x/sf.exe"
    monkeypatch.setattr("app.main_window.choose_engine_path", lambda root, current, folder: None)
    win._choose_engine_path()
    assert win.settings["engine_path"] == "C:/x/sf.exe"


# --- The rule that the model is changed through its own methods -----------------------

def test_modes_do_not_write_to_the_game_directly():
    for path in (ROOT / "app" / "modes").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "headers[" not in text and ".comment =" not in text and ".modified =" not in text, path

