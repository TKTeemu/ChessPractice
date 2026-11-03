"""Main window: layout, menus, keyboard shortcuts, file commands and the status line."""

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import chess

from . import fileio
from . import strings as S
from .board_view import BoardView
from .dialogs import choose_game
from .model import GameModel, event_for, visible_comment
from .modes import MODES, ModeContext, mode_class
from .movelist_view import MoveListView
from .pieces import PieceImages
from .settings import Settings
from .sounds import ILLEGAL, Sounds
from .theme import (BACKGROUND, BUTTON_ACTIVE, BUTTON_BG, CLOCK_ACTIVE_BG, CLOCK_ACTIVE_FG, CLOCK_BG,
                    CLOCK_FG, CLOCK_LOW_FG, ENTRY_BG, MUTED_FG, PANEL_BG, PANEL_FG)


class MainWindow:
    """Owns the model and all views and acts as the controller between them.

    Every change to the model goes through a method here, which then calls refresh()
    so that board, move list, status line, FEN field and title stay in step.
    The active mode (self.mode) is asked what the user may do; see app/modes/base.py.
    """

    def __init__(self, root, app_dir):
        self.root = root
        self.app_dir = Path(app_dir)
        self.settings = Settings(self.app_dir / "settings.json")
        self.model = GameModel()
        self.pieces = PieceImages(self.app_dir / "assets" / "pieces", self.settings["piece_set"])
        self.sounds = Sounds(self.app_dir / "assets" / "sounds", self.settings["sound"])
        self.path = None
        self._comment_node = None
        self._clocks = None   # {color: (text, active, low)} while a mode shows clocks
        self.ctx = ModeContext(
            root=root, model=self.model, settings=self.settings, play_move=self.play_move,
            new_game=self._set_position, refresh=self.refresh, set_flipped=self.set_flipped,
            set_mode=self.set_mode, confirm_discard=self._confirm_discard, set_clocks=self.set_clocks,
            play_sound=self.sounds.play, button=self._button, take_back=self.take_back)
        self.mode = MODES[0](self.ctx)   # the program always starts in the first mode (Board)

        self.scale = root.winfo_fpixels("1i") / 96   # 1.25 on a 125 % display
        root.title(S.APP_TITLE)
        root.geometry(self.settings["window_geometry"] or f"{self._px(1100)}x{self._px(760)}")
        root.minsize(self._px(780), self._px(520))
        root.configure(bg=BACKGROUND)

        self._build_ui()
        self._build_menu()
        self._bind_keys()
        root.protocol("WM_DELETE_WINDOW", self.exit)

        self.board.flipped = self.settings["flipped"]
        self.board.show_coords = self.settings["show_coordinates"]
        self.board.theme = self.settings["board_theme"]
        self._show_details()
        self.refresh(rebuild=True)

    # --- Layout -----------------------------------------------------------

    def _px(self, pixels):
        """Scale a size designed for a 100 % display."""
        return round(pixels * self.scale)

    def _button(self, parent, text, command, **kw):
        return tk.Button(parent, text=text, command=command, bg=BUTTON_BG, fg=PANEL_FG,
                         activebackground=BUTTON_ACTIVE, activeforeground=PANEL_FG, relief="flat",
                         bd=0, padx=10, pady=6, font=("Segoe UI", 11, "bold"), takefocus=0, **kw)

    def _build_ui(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        left = tk.Frame(root, bg=BACKGROUND)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=8)
        name_font = ("Segoe UI", 11, "bold")
        title_row = tk.Frame(left, bg=BACKGROUND)
        title_row.pack(side="top", fill="x")
        self.mode_title = tk.Label(title_row, bg=BACKGROUND, fg=MUTED_FG, font=("Segoe UI", 10, "bold"), anchor="w")
        self.mode_title.pack(side="left", fill="x", expand=True)
        self.score = tk.Label(title_row, bg=BACKGROUND, fg=PANEL_FG, font=("Segoe UI", 10, "bold"), anchor="e")
        self.score.pack(side="right")
        rows = {}
        for side in ("top", "bottom"):
            row = tk.Frame(left, bg=BACKGROUND)
            row.pack(side=side, fill="x")
            rows[side] = (tk.Label(row, bg=BACKGROUND, fg=PANEL_FG, font=name_font, anchor="w"),
                          tk.Label(row, bg=CLOCK_BG, fg=CLOCK_FG, font=("Consolas", 15, "bold"), padx=10))
            rows[side][0].pack(side="left", fill="x", expand=True)
        (self.top_name, self.top_clock), (self.bottom_name, self.bottom_clock) = rows["top"], rows["bottom"]
        self.board = BoardView(left, self.model, self.pieces, self.user_move, self.illegal_move,
                               can_move=lambda color: self.mode.can_move(color))
        self.board.pack(side="top", fill="both", expand=True, pady=4)

        right = tk.Frame(root, bg=PANEL_BG, width=self._px(290))
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=8)
        right.grid_propagate(False)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        # Shared toolbar: the same in every mode; the mode decides what a new game means
        toolbar = tk.Frame(right, bg=PANEL_BG)
        toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        self._button(toolbar, S.BTN_NEW_GAME, self.new_game).pack(side="left", padx=2)

        self.status = tk.Label(right, bg=PANEL_BG, fg=PANEL_FG, font=("Segoe UI", 12, "bold"),
                               anchor="w", justify="left", padx=10, pady=6)
        self.status.grid(row=1, column=0, sticky="ew")
        self.status.bind("<Configure>", lambda e: self.status.configure(wraplength=e.width - self._px(20)))

        # The active mode's own controls (e.g. Resign); hidden when the mode has none
        self.mode_panel = tk.Frame(right, bg=PANEL_BG)
        self.mode_panel.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.mode_panel.grid_remove()

        self.movelist = MoveListView(right, self.model, self.select_node, self.edit_tree)
        self.movelist.grid(row=3, column=0, sticky="nsew")

        nav = tk.Frame(right, bg=PANEL_BG)
        nav.grid(row=4, column=0, sticky="ew", padx=6, pady=6)
        for i, (text, command) in enumerate(((S.BTN_FIRST, self.go_start), (S.BTN_PREV, self.back),
                                             (S.BTN_NEXT, self.forward), (S.BTN_LAST, self.go_end))):
            nav.columnconfigure(i, weight=1, uniform="nav")
            self._button(nav, text, command).grid(row=0, column=i, sticky="ew", padx=2)
        nav.columnconfigure(4, weight=2)
        self._button(nav, S.BTN_FLIP, self.flip).grid(row=0, column=4, sticky="ew", padx=2)

        # Comment & FEN: collapsible; open or closed is remembered per mode
        self.details_toggle = tk.Button(right, command=self._toggle_details, bg=PANEL_BG, fg=MUTED_FG,
                                        activebackground=PANEL_BG, activeforeground=PANEL_FG, relief="flat",
                                        bd=0, anchor="w", padx=10, font=("Segoe UI", 9, "bold"), takefocus=0)
        self.details_toggle.grid(row=5, column=0, sticky="ew", pady=(0, 4))
        self.details = tk.Frame(right, bg=PANEL_BG)
        self.details.grid(row=6, column=0, sticky="ew")
        self.details.columnconfigure(0, weight=1)

        tk.Label(self.details, text=S.LABEL_COMMENT, bg=PANEL_BG, fg=MUTED_FG, anchor="w",
                 font=("Segoe UI", 9)).grid(row=0, column=0, sticky="ew", padx=10)
        self.comment = tk.Text(self.details, height=3, bg=ENTRY_BG, fg=PANEL_FG, insertbackground=PANEL_FG,
                               relief="flat", font=("Segoe UI", 10), wrap="word", padx=6, pady=4)
        self.comment.grid(row=1, column=0, sticky="ew", padx=8)
        self.comment.bind("<FocusOut>", lambda e: self._save_comment(rebuild=True))

        fen_row = tk.Frame(self.details, bg=PANEL_BG)
        fen_row.grid(row=2, column=0, sticky="ew", padx=8, pady=8)
        fen_row.columnconfigure(1, weight=1)
        tk.Label(fen_row, text=S.LABEL_FEN, bg=PANEL_BG, fg=MUTED_FG,
                 font=("Segoe UI", 9)).grid(row=0, column=0, padx=(2, 6))
        self.fen_var = tk.StringVar()
        self.fen_entry = tk.Entry(fen_row, textvariable=self.fen_var, bg=ENTRY_BG, fg=PANEL_FG,
                                  insertbackground=PANEL_FG, relief="flat", font=("Consolas", 9))
        self.fen_entry.grid(row=0, column=1, sticky="ew", ipady=4)
        self.fen_entry.bind("<Return>", self._fen_entered)
        self._button(fen_row, S.BTN_COPY, self.copy_fen, ).grid(row=0, column=2, padx=(6, 0))

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self._guarded = []   # (menu, index, command name for mode.allows)

        def guarded(menu, name, **kw):
            menu.add_command(**kw)
            self._guarded.append((menu, menu.index("end"), name))

        m = tk.Menu(menubar, tearoff=0, postcommand=self._update_menu_states)
        m.add_command(label=S.FILE_NEW, accelerator="Ctrl+N", command=self.new_game)
        guarded(m, "open", label=S.FILE_OPEN, accelerator="Ctrl+O", command=self.open_file)
        m.add_command(label=S.FILE_SAVE, accelerator="Ctrl+S", command=self.save)
        m.add_command(label=S.FILE_SAVE_AS, command=self.save_as)
        m.add_command(label=S.FILE_SAVE_FEN, command=self.save_fen)
        m.add_separator()
        m.add_command(label=S.FILE_COPY_PGN, accelerator="Ctrl+C", command=self.copy_pgn)
        m.add_command(label=S.FILE_COPY_FEN, command=self.copy_fen)
        guarded(m, "paste", label=S.FILE_PASTE, accelerator="Ctrl+V", command=self.paste)
        m.add_separator()
        m.add_command(label=S.FILE_EXIT, command=self.exit)
        menubar.add_cascade(label=S.MENU_FILE, menu=m)

        m = tk.Menu(menubar, tearoff=0)
        m.add_command(label=S.VIEW_FLIP, accelerator="F", command=self.flip)
        self.coords_var = tk.BooleanVar(value=self.settings["show_coordinates"])
        m.add_checkbutton(label=S.VIEW_COORDS, variable=self.coords_var, command=self._toggle_coords)
        self.sound_var = tk.BooleanVar(value=self.settings["sound"])
        m.add_checkbutton(label=S.VIEW_SOUND, variable=self.sound_var, command=self._toggle_sound)
        self.piece_set_var = tk.StringVar(value=self.settings["piece_set"])
        sub = tk.Menu(m, tearoff=0)
        for key, label in S.PIECE_SETS.items():
            sub.add_radiobutton(label=label, value=key, variable=self.piece_set_var,
                                command=self._change_piece_set)
        m.add_cascade(label=S.VIEW_PIECE_SET, menu=sub)
        self.theme_var = tk.StringVar(value=self.settings["board_theme"])
        sub = tk.Menu(m, tearoff=0)
        for key, label in S.BOARD_THEMES.items():
            sub.add_radiobutton(label=label, value=key, variable=self.theme_var,
                                command=self._change_theme)
        m.add_cascade(label=S.VIEW_BOARD_THEME, menu=sub)
        menubar.add_cascade(label=S.MENU_VIEW, menu=m)

        self.mode_var = tk.StringVar(value=self.mode.key)
        self.mode_menu = tk.Menu(menubar, tearoff=0, postcommand=self._build_mode_menu)
        menubar.add_cascade(label=S.MENU_GAME, menu=self.mode_menu)

        m = tk.Menu(menubar, tearoff=0)
        m.add_command(label=S.HELP_SHORTCUTS,
                      command=lambda: messagebox.showinfo(S.SHORTCUTS_TITLE, S.SHORTCUTS_TEXT, parent=self.root))
        m.add_command(label=S.HELP_ABOUT,
                      command=lambda: messagebox.showinfo(S.ABOUT_TITLE, S.ABOUT_TEXT, parent=self.root))
        menubar.add_cascade(label=S.MENU_HELP, menu=m)

        self.root.configure(menu=menubar)

    def _update_menu_states(self):
        for menu, index, name in self._guarded:
            menu.entryconfigure(index, state="normal" if self.mode.allows(name) else "disabled")

    def _build_mode_menu(self):
        """Rebuilt each time the menu opens: the modes, then the active mode's own items."""
        m = self.mode_menu
        m.delete(0, "end")
        self.mode_var.set(self.mode.key)
        for cls in MODES:
            m.add_radiobutton(label=cls.label, value=cls.key, variable=self.mode_var,
                              command=lambda key=cls.key: self._mode_chosen(key))
        items = self.mode.menu_items()
        if items:
            m.add_separator()
        for item in items:
            m.add_command(label=item.label, command=item.command,
                          state="normal" if item.enabled() else "disabled")

    def _build_mode_panel(self):
        for child in self.mode_panel.winfo_children():
            child.destroy()
        panel = self.mode.build_panel(self.mode_panel)
        if panel is None:
            self.mode_panel.grid_remove()
        else:
            panel.pack(fill="x")
            self.mode_panel.grid()
        self._show_details()

    def _details_states(self):
        """settings["details_open"], e.g. "board,!vs_computer": open in Board, closed in
        Play vs Computer. A mode that is not listed uses its show_details."""
        return [item for item in self.settings["details_open"].split(",") if item]

    def _details_open(self):
        states = self._details_states()
        if self.mode.key in states:
            return True
        if "!" + self.mode.key in states:
            return False
        return self.mode.show_details

    def _show_details(self):
        is_open = self._details_open()
        self.details_toggle.configure(text=S.DETAILS_OPEN if is_open else S.DETAILS_CLOSED)
        if is_open:
            self.details.grid()
        else:
            self.details.grid_remove()

    def _toggle_details(self):
        self._save_comment(rebuild=True)
        key = self.mode.key
        states = [item for item in self._details_states() if item not in (key, "!" + key)]
        states.append("!" + key if self._details_open() else key)
        self.settings["details_open"] = ",".join(states)
        self._show_details()

    def _bind_keys(self):
        def board_key(handler):
            # Keys that mean something else while typing in the comment or FEN field
            def wrapped(event):
                if not in_main_window(event):
                    return None
                if isinstance(event.widget, (tk.Entry, tk.Text)) and event.widget is not self.movelist.text:
                    return None
                handler()
                return "break"
            return wrapped

        def always(handler):
            def wrapped(event):
                if not in_main_window(event):
                    return None
                handler()
                return "break"
            return wrapped

        def in_main_window(event):
            # bind_all also sees key presses inside dialogs
            widget = event.widget
            return isinstance(widget, tk.Misc) and widget.winfo_toplevel() is self.root

        keys = {
            "<Left>": self.back, "<Right>": self.forward, "<Home>": self.go_start, "<End>": self.go_end,
            "<Up>": lambda: self.switch_variation(-1), "<Down>": lambda: self.switch_variation(1),
            "<f>": self.flip, "<F>": self.flip,
            "<Control-z>": self.delete_last, "<Control-Z>": self.delete_last,
            "<Control-c>": self.copy_pgn, "<Control-C>": self.copy_pgn,
            "<Control-v>": self.paste, "<Control-V>": self.paste,
        }
        for sequence, handler in keys.items():
            self.root.bind_all(sequence, board_key(handler))
        for sequence, handler in {"<Control-n>": self.new_game, "<Control-N>": self.new_game,
                                  "<Control-o>": self.open_file, "<Control-O>": self.open_file,
                                  "<Control-s>": self.save, "<Control-S>": self.save}.items():
            self.root.bind_all(sequence, always(handler))
        # Clicking the board or the move list takes focus away from the text fields
        self.board.bind("<ButtonPress-1>", lambda e: self.board.focus_set(), add="+")

    # --- Refreshing -------------------------------------------------------

    def refresh(self, rebuild=False):
        """Bring every view up to date with the model."""
        self.board.set_hints(self.mode.hint_arrows())
        self.board.position_changed()
        if rebuild:
            self.movelist.rebuild()
        else:
            self.movelist.show_current()
        self.status.configure(text=self.mode.status_text() or self.model.status())
        self.mode_title.configure(text=self.mode.title())
        self.score.configure(text=self.mode.score_text() or "")
        self.fen_var.set(self.model.fen())
        self.fen_entry.configure(state="normal" if self.mode.allows("paste") else "readonly")
        self._load_comment()
        self._update_names()
        self._update_title()

    def _update_names(self):
        h = self.model.headers
        white, black = h.get("White", S.DEFAULT_WHITE), h.get("Black", S.DEFAULT_BLACK)
        top, bottom = (white, black) if self.board.flipped else (black, white)
        self.top_name.configure(text=top)
        self.bottom_name.configure(text=bottom)
        self._show_clocks()

    def set_clocks(self, values):
        """values: {chess.WHITE: (text, active, low), chess.BLACK: …}, or None to hide the clocks."""
        if values != self._clocks:
            self._clocks = values
            self._show_clocks()

    def _show_clocks(self):
        top_color = chess.WHITE if self.board.flipped else chess.BLACK
        for label, color in ((self.top_clock, top_color), (self.bottom_clock, not top_color)):
            if self._clocks is None:
                label.pack_forget()
                continue
            text, active, low = self._clocks[color]
            fg = CLOCK_LOW_FG if low else (CLOCK_ACTIVE_FG if active else CLOCK_FG)
            label.configure(text=text, fg=fg, bg=CLOCK_ACTIVE_BG if active else CLOCK_BG)
            if not label.winfo_ismapped():
                label.pack(side="right")

    def _update_title(self):
        name = self.path.name if self.path else S.UNTITLED
        mark = "*" if self.model.modified else ""
        self.root.title(f"{mark}{name} – {S.APP_TITLE}")

    def _load_comment(self):
        self._comment_node = self.model.node
        self.comment.configure(state="normal")
        self.comment.delete("1.0", "end")
        self.comment.insert("1.0", visible_comment(self.model.node.comment))
        if not self.mode.allows("edit_comment"):
            self.comment.configure(state="disabled")

    def _save_comment(self, rebuild=False):
        node = self._comment_node
        if node is None or not self.mode.allows("edit_comment"):
            return False
        changed = self.model.set_comment(node, self.comment.get("1.0", "end"))
        if changed and rebuild:
            self.movelist.rebuild()
            self._update_title()
        return changed

    # --- Moves and navigation ---------------------------------------------

    def user_move(self, frm, to, promotion):
        self.play_move(chess.Move(frm, to, promotion))

    def play_move(self, move, from_end=False):
        """Play a chess.Move from any source (the board or an engine) and update the views.

        from_end: play it after the last move of the line (an engine reply arriving while
        the user is looking at earlier moves).
        """
        self._save_comment()
        if from_end:
            self.model.go_end()
        event = self.model.play(move)
        if event is None:
            self.illegal_move()
            return
        self.mode.after_move()
        self.refresh(rebuild=True)
        self.sounds.play(event)

    def illegal_move(self):
        self.board.redraw()
        self.sounds.play(ILLEGAL)

    def _navigate(self, action):
        if not self.mode.allows("navigate"):
            return
        changed = self._save_comment()
        moved = action()
        if moved or changed:
            self.refresh(rebuild=changed)
        if moved and self.model.node.move is not None:
            self.sounds.play(event_for(self.model.node))

    def back(self):
        self._navigate(self.model.back)

    def forward(self):
        self._navigate(self.model.forward)

    def go_start(self):
        self._navigate(self.model.go_start)

    def go_end(self):
        self._navigate(self.model.go_end)

    def switch_variation(self, delta):
        self._navigate(lambda: self.model.switch_variation(delta))

    def select_node(self, node):
        self._navigate(lambda: self.model.goto(node))

    def delete_last(self):
        if not self.mode.allows("delete_last"):
            return
        self._save_comment()
        if self.model.delete_last():
            self.refresh(rebuild=True)

    def take_back(self, color):
        """Remove the moves back to `color`'s previous turn (Take Back in a game mode)."""
        if not self.mode.allows("take_back"):
            return False
        self._save_comment()
        if not self.model.take_back(color):
            return False
        self.refresh(rebuild=True)
        return True

    def edit_tree(self, action, node):
        if not self.mode.allows("edit_tree"):
            return
        self._save_comment()
        handler = {"promote": self.model.promote_to_main,
                   "delete_variation": self.model.delete_variation,
                   "delete_from_here": self.model.delete_from_here}[action]
        if handler(node):
            self.refresh(rebuild=True)

    def flip(self):
        self.set_flipped(not self.board.flipped)

    def set_flipped(self, flipped):
        self.settings["flipped"] = flipped
        self.board.set_flipped(flipped)
        self._update_names()

    # --- Modes ------------------------------------------------------------

    def _mode_chosen(self, key):
        self.mode_var.set(self.mode.key)   # the radio button shows the mode actually active
        if key == self.mode.key:
            self.mode.new_game()           # e.g. Play vs Computer again: a new game
        else:
            self.set_mode(key)

    def set_mode(self, key):
        """Switch to the mode with this key (or restart the current one). Returns True on success."""
        cls = mode_class(key)
        if cls is None or not self.mode.confirm_leave():
            return False
        self._save_comment()
        new = cls(self.ctx)
        if not new.activate():
            return False
        old, self.mode = self.mode, new
        old.deactivate()
        self.settings["mode"] = key
        self.mode_var.set(key)
        self._build_mode_panel()
        self.refresh(rebuild=True)
        return True

    # --- View settings ----------------------------------------------------

    def _toggle_coords(self):
        self.settings["show_coordinates"] = self.coords_var.get()
        self.board.set_show_coords(self.coords_var.get())

    def _toggle_sound(self):
        self.settings["sound"] = self.sounds.enabled = self.sound_var.get()

    def _change_piece_set(self):
        self.settings["piece_set"] = self.piece_set_var.get()
        self.pieces.set_piece_set(self.piece_set_var.get())
        self.board.redraw()

    def _change_theme(self):
        self.settings["board_theme"] = self.theme_var.get()
        self.board.set_theme(self.theme_var.get())

    # --- Files ------------------------------------------------------------

    def _initial_dir(self):
        last = self.settings["last_directory"]
        if last and Path(last).is_dir():
            return last
        games = self.app_dir / "Games"
        games.mkdir(exist_ok=True)
        return str(games)

    def _confirm_discard(self):
        """True if it is fine to replace the current game."""
        self._save_comment()
        if not self.model.modified:
            return True
        answer = messagebox.askyesnocancel(S.UNSAVED_TITLE, S.UNSAVED_PROMPT, parent=self.root)
        if answer is None:
            return False
        return self.save() if answer else True

    def _set_game(self, game, path=None):
        self.model.load_game(game)
        self.path = Path(path) if path else None
        self.refresh(rebuild=True)

    def _set_position(self, board):
        self.model.new_game(board)
        self.path = None
        self.refresh(rebuild=True)

    def new_game(self):
        if self.mode.new_game():
            return
        if self._confirm_discard():
            self._set_position(None)

    def open_file(self):
        if not self.mode.allows("open") or not self._confirm_discard():
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
                self._set_position(fileio.read_fen(path))
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
        if len(games) == 1:
            self._set_game(games[0], path)
            return
        index = choose_game(self.root, games)
        if index is not None:
            # Saving must not overwrite a multi-game file with a single game
            self._set_game(games[index], None)

    def save(self):
        self._save_comment()
        if self.path is None:
            return self.save_as()
        return self._write_pgn(self.path)

    def save_as(self):
        self._save_comment()
        h = self.model.headers
        suggestion = f"{h.get('White', '')} - {h.get('Black', '')}".strip(" -?") or "game"
        name = filedialog.asksaveasfilename(
            parent=self.root, initialdir=self._initial_dir(), initialfile=suggestion + ".pgn",
            defaultextension=".pgn", filetypes=[(S.FILETYPE_PGN, "*.pgn"), (S.FILETYPE_ALL, "*.*")])
        if not name:
            return False
        self.settings["last_directory"] = str(Path(name).parent)
        if self._write_pgn(Path(name)):
            self.path = Path(name)
            self._update_title()
            return True
        return False

    def _write_pgn(self, path):
        try:
            fileio.write_pgn(self.model.game, path)
        except OSError as e:
            messagebox.showerror(S.ERROR_TITLE, S.ERROR_SAVE.format(error=e), parent=self.root)
            return False
        self.model.modified = False
        self._update_title()
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
        self._save_comment()
        self._copy(fileio.game_to_pgn(self.model.game))

    def copy_fen(self):
        self._copy(self.model.fen())

    def paste(self):
        if not self.mode.allows("paste"):
            return
        try:
            text = self.root.clipboard_get()
            kind, data = fileio.parse_text(text)
        except (tk.TclError, ValueError):
            messagebox.showerror(S.ERROR_TITLE, S.ERROR_PASTE, parent=self.root)
            return
        if not self._confirm_discard():
            return
        if kind == "fen":
            self._set_position(data)
        else:
            self._load_games(data)

    def _fen_entered(self, event):
        if not self.mode.allows("paste"):
            return "break"
        try:
            board = chess.Board(self.fen_var.get().strip())
        except ValueError as e:
            messagebox.showerror(S.ERROR_TITLE, S.ERROR_FEN.format(error=e), parent=self.root)
            return "break"
        if board.fen() != self.model.fen() and self._confirm_discard():
            self._set_position(board)
        self.board.focus_set()
        return "break"

    # --- Exit -------------------------------------------------------------

    def exit(self):
        if not self.mode.confirm_leave() or not self._confirm_discard():
            return
        self.mode.deactivate()   # stops engine processes and timers
        if self.root.state() == "normal":
            self.settings["window_geometry"] = self.root.geometry()
        self.settings.save()
        self.root.destroy()
