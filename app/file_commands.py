"""FileCommands: the File menu's commands, the clipboard, and offering to save a game."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from . import fileio
from . import strings as S
from .commands import OPEN, PASTE
from .dialogs import choose_game

MAX_SKIPPED_SHOWN = 5   # games named in the "some games were skipped" message


class FileCommands:
    """Replaces, saves and copies the game. `window` is the MainWindow it belongs to."""

    def __init__(self, window):
        self.window = window
        self.path = None   # the open file; None for a new game or one picked from a multi-game file

    @property
    def root(self):
        return self.window.root

    @property
    def model(self):
        return self.window.model

    @property
    def settings(self):
        return self.window.settings

    def _initial_dir(self):
        last = self.settings["last_directory"]
        if last and Path(last).is_dir():
            return last
        games = self.window.app_dir / "Games"
        try:
            games.mkdir(exist_ok=True)
        except OSError:   # e.g. a read-only program folder
            return str(Path.home())
        return str(games)

    # --- Offering to save -------------------------------------------------

    def confirm_discard(self, before_write=None, will_change=False):
        """True if the current game may now be replaced, after offering to save it.

        before_write runs when all questions have been answered and nothing can be cancelled
        any more, just before the file is written, so that what it does (a resignation) goes in
        the file but Cancel leaves everything as it was. will_change: before_write will change
        the game, so offer to save it even if it has no unsaved changes now."""
        self.window.save_comment()
        path = None
        if self.model.modified or will_change:
            answer = messagebox.askyesnocancel(S.UNSAVED_TITLE, S.UNSAVED_PROMPT, parent=self.root)
            if answer is None:
                return False
            if answer:
                path = self.path or self._ask_save_path()
                if path is None:
                    return False
        if before_write is not None:
            before_write()
        return self._write_game(path) if path else True

    # --- Replacing the game -----------------------------------------------

    def set_game(self, game, path=None):
        self.model.load_game(game)
        self.path = Path(path) if path else None
        self.window.position_changed(rebuild=True)

    def set_position(self, board=None, headers=None, intro=""):
        self.model.new_game(board, headers, intro)
        self.path = None
        self.window.position_changed(rebuild=True)

    def open_file(self):
        if not self.window.allowed(OPEN) or not self.confirm_discard():
            return
        name = filedialog.askopenfilename(
            parent=self.root, initialdir=self._initial_dir(),
            filetypes=[(S.FILETYPE_PGN, "*.pgn"), (S.FILETYPE_FEN, "*.fen"), (S.FILETYPE_ALL, "*.*")])
        if not name:
            return
        path = Path(name)
        self.settings["last_directory"] = str(path.parent)
        try:
            if path.suffix.lower() == ".fen":
                self.set_position(fileio.read_fen(path))
                return
            games = fileio.read_pgn_games(path)
        except (OSError, ValueError) as e:
            messagebox.showerror(S.ERROR_TITLE, S.ERROR_OPEN.format(error=e), parent=self.root)
            return
        self._load_games(games, path)

    def _load_games(self, games, path=None):
        if not games:
            messagebox.showerror(S.ERROR_TITLE, S.ERROR_NO_GAMES, parent=self.root)
            return
        if games.skipped:
            self._report_skipped(games.skipped)
            path = None   # saving must not overwrite the file without the games left out
        if len(games) == 1:
            self.set_game(games[0], path)
            return
        index = choose_game(self.root, games)
        if index is not None:
            # Saving must not overwrite a multi-game file with a single game
            self.set_game(games[index], None)

    def _report_skipped(self, skipped):
        lines = skipped[:MAX_SKIPPED_SHOWN]
        if len(skipped) > MAX_SKIPPED_SHOWN:
            lines.append(S.WARNING_MORE.format(count=len(skipped) - MAX_SKIPPED_SHOWN))
        messagebox.showwarning(S.WARNING_TITLE, S.WARNING_GAMES_SKIPPED.format(
            count=len(skipped), details="\n".join(lines)), parent=self.root)

    # --- Saving -----------------------------------------------------------

    def save(self):
        self.window.save_comment()
        if self.path is None:
            return self.save_as()
        return self._write_game(self.path)

    def save_as(self):
        self.window.save_comment()
        path = self._ask_save_path()
        return self._write_game(path) if path else False

    def _ask_save_path(self):
        """The file to save the game in, or None if the user cancelled. Nothing is written yet."""
        h = self.model.headers
        suggestion = f"{h.get('White', '')} - {h.get('Black', '')}".strip(" -?") or "game"
        name = filedialog.asksaveasfilename(
            parent=self.root, initialdir=self._initial_dir(), initialfile=suggestion + ".pgn",
            defaultextension=".pgn", filetypes=[(S.FILETYPE_PGN, "*.pgn"), (S.FILETYPE_ALL, "*.*")])
        if not name:
            return None
        self.settings["last_directory"] = str(Path(name).parent)
        return Path(name)

    def _write_game(self, path):
        try:
            fileio.write_pgn(self.model.game, path)
        except OSError as e:
            messagebox.showerror(S.ERROR_TITLE, S.ERROR_SAVE.format(error=e), parent=self.root)
            return False
        self.path = path
        self.model.mark_saved()
        self.window.update_title()
        return True

    def save_fen(self):
        name = filedialog.asksaveasfilename(
            parent=self.root, initialdir=self._initial_dir(), initialfile="position.fen",
            defaultextension=".fen", filetypes=[(S.FILETYPE_FEN, "*.fen"), (S.FILETYPE_ALL, "*.*")])
        if not name:
            return
        self.settings["last_directory"] = str(Path(name).parent)
        try:
            fileio.write_fen(self.model.board, name)
        except OSError as e:
            messagebox.showerror(S.ERROR_TITLE, S.ERROR_SAVE.format(error=e), parent=self.root)

    # --- Clipboard --------------------------------------------------------

    def _copy(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)

    def copy_pgn(self):
        self.window.save_comment()
        self._copy(fileio.game_to_pgn(self.model.game))

    def copy_fen(self):
        self._copy(self.model.fen())

    def paste(self):
        if not self.window.allowed(PASTE):
            return
        try:
            text = self.root.clipboard_get()
            kind, data = fileio.parse_text(text)
        except (tk.TclError, ValueError):
            messagebox.showerror(S.ERROR_TITLE, S.ERROR_PASTE, parent=self.root)
            return
        if not self.confirm_discard():
            return
        if kind == "fen":
            self.set_position(data)
        else:
            self._load_games(data)

    def fen_entered(self, fen):
        """The user typed a FEN into the FEN field and pressed Enter."""
        if not self.window.allowed(PASTE):
            return
        try:
            board = fileio.board_from_fen(fen.strip())
        except ValueError as e:
            messagebox.showerror(S.ERROR_TITLE, S.ERROR_FEN.format(error=e), parent=self.root)
            return
        if board.fen() != self.model.fen() and self.confirm_discard():
            self.set_position(board)
