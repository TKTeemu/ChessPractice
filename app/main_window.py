"""Main window: layout, menus, keyboard shortcuts, the status line and the active mode."""

import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import chess

from . import strings as S
from .assets import Assets
from .board_view import BoardView
from .commands import DELETE_LAST, EDIT_COMMENT, EDIT_TREE, NAVIGATE, OPEN, PASTE, TAKE_BACK
from .dialogs import choose_engine_path
from .engines import StockfishEngine
from .file_commands import FileCommands
from .model import GameModel, event_for, visible_comment
from .modes import MODES, ModeContext, mode_class, mode_settings
from .movelist_view import MoveListView
from .pieces import PieceImages
from .settings import Settings
from .sounds import ILLEGAL, Sounds
from .theme import (BACKGROUND, BOARD_THEMES, CLOCK_ACTIVE_BG, CLOCK_ACTIVE_FG, CLOCK_BG, CLOCK_FG, CLOCK_LOW_FG,
                    DEFAULT_BOARD_THEME, ENTRY_BG, FONT, FONT_BOLD, FONT_CLOCK, FONT_LARGE_BOLD, FONT_MONO_SMALL,
                    FONT_SMALL, FONT_SMALL_BOLD, FONT_STATUS, MUTED_FG, PANEL_BG, PANEL_FG)
from .widgets import button, light

AUTOSAVE_MS = 2000   # how often changed settings are written to settings.json
NOTICE_MS = 4000     # how long an explanation of a blocked action stays on the status line
NAV_FIRST, NAV_PREV, NAV_NEXT, NAV_LAST = "first", "prev", "next", "last"   # the |◀ ◀ ▶ ▶| buttons
GEOMETRY_RE = re.compile(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)")
MIN_VISIBLE = 100    # pixels of a restored window's title bar that must be on a screen


def restored_geometry(saved, screen):
    """The window geometry to use for a saved one, or None for the default size. If the saved
    position would leave the title bar out of reach (a monitor has been disconnected), only the
    size is kept and Windows chooses the position. screen: (x, y, width, height) of the desktop."""
    match = GEOMETRY_RE.fullmatch(saved)
    if match is None:
        return None
    width, height, x, y = map(int, match.groups())
    left, top, screen_width, screen_height = screen
    reachable = (x + width >= left + MIN_VISIBLE and x <= left + screen_width - MIN_VISIBLE
                 and top <= y <= top + screen_height - MIN_VISIBLE)
    return saved if reachable else f"{width}x{height}"


class MainWindow:
    """Owns the model and all views and acts as the controller between them.

    After a change, one of two methods brings the views up to date: position_changed() when the
    current position or the game tree changed (board, move list, FEN, comment and everything
    below), and update_status() when only what the mode says changed (status line, title, panel
    buttons, arrows). update_status() leaves alone what the user is doing: the text being typed
    in the comment field, and a piece being moved or the arrows on the board.
    The active mode (self.mode) is asked what the user may do; see app/modes/base.py.
    File and clipboard commands are in self.files (app/file_commands.py).
    """

    def __init__(self, root, app_dir, settings=None):
        self.root = root
        self.app_dir = Path(app_dir)
        self.settings = settings if settings is not None else Settings(self.app_dir / "settings.json", mode_settings())
        self._repair_settings()
        self.model = GameModel()
        self.pieces = PieceImages(self.app_dir / "assets" / "pieces", self.settings["piece_set"])
        self.sounds = Sounds(self.app_dir / "assets" / "sounds", self.settings["sound"])
        self.files = FileCommands(self)
        self._comment_node = None
        self._clocks = None         # {color: (text, active, low)} while a mode shows clocks
        self._notice_after = None   # the timer that ends an explanation on the status line
        self._autosave_failed = False
        self.ctx = ModeContext(
            root=root, model=self.model, settings=self.settings, app_dir=self.app_dir,
            assets=Assets(self.app_dir, lambda: self.settings["end_progress"]),
            play_move=self.play_move, new_game=self.files.set_position, update_status=self.update_status,
            set_flipped=self.set_flipped, set_mode=self.set_mode, set_clocks=self.set_clocks,
            play_sound=self.sounds.play, take_back=self.take_back)
        self.mode = MODES[0](self.ctx)   # the program always starts in the first mode (Board)

        self.scale = root.winfo_fpixels("1i") / 96   # 1.25 on a 125 % display
        root.title(S.APP_TITLE)
        screen = (root.winfo_vrootx(), root.winfo_vrooty(), root.winfo_vrootwidth(), root.winfo_vrootheight())
        root.geometry(restored_geometry(self.settings["window_geometry"], screen)
                      or f"{self._px(1100)}x{self._px(760)}")
        root.minsize(self._px(780), self._px(520))
        root.configure(bg=BACKGROUND)

        self._build_ui()
        self._build_menu()
        self._bind_keys()
        root.protocol("WM_DELETE_WINDOW", self.exit)

        self.board.flipped = self.settings["flipped"]
        self.board.show_coords = self.settings["show_coordinates"]
        self.board.theme = self.settings["board_theme"]
        self._build_mode_panel()
        self.position_changed(rebuild=True)
        self.root.after(AUTOSAVE_MS, self._autosave)

    def _repair_settings(self):
        """A hand-edited settings.json can name something that does not exist."""
        if self.settings["board_theme"] not in BOARD_THEMES:
            self.settings["board_theme"] = DEFAULT_BOARD_THEME
        if self.settings["piece_set"] not in S.PIECE_SETS:
            self.settings["piece_set"] = next(iter(S.PIECE_SETS))

    # --- Layout -----------------------------------------------------------

    def _px(self, pixels):
        """Scale a size designed for a 100 % display."""
        return round(pixels * self.scale)

    def _build_ui(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        left = tk.Frame(root, bg=BACKGROUND)
        left.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=8)
        title_row = tk.Frame(left, bg=BACKGROUND)
        title_row.pack(side="top", fill="x")
        self.mode_title = tk.Label(title_row, bg=BACKGROUND, fg=MUTED_FG, font=FONT_BOLD, anchor="w")
        self.mode_title.pack(side="left", fill="x", expand=True)
        self.score = tk.Label(title_row, bg=BACKGROUND, fg=PANEL_FG, font=FONT_BOLD, anchor="e")
        self.score.pack(side="right")
        self.light = light(title_row, self._px(14))   # packed when the mode has a success light
        # Where the position comes from (Mode.subtitle); packed only when the mode has one
        self.subtitle = tk.Label(left, bg=BACKGROUND, fg=MUTED_FG, font=FONT_SMALL, anchor="w")
        self._subtitle_after = title_row
        rows = {}
        for side in ("top", "bottom"):
            row = tk.Frame(left, bg=BACKGROUND)
            row.pack(side=side, fill="x")
            rows[side] = (tk.Label(row, bg=BACKGROUND, fg=PANEL_FG, font=FONT_LARGE_BOLD, anchor="w"),
                          tk.Label(row, bg=CLOCK_BG, fg=CLOCK_FG, font=FONT_CLOCK, padx=10))
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

        # Shared toolbar: the same in every mode; the mode decides what a new game means.
        # Take Back is packed only in a mode that has it (_build_mode_panel).
        toolbar = tk.Frame(right, bg=PANEL_BG)
        toolbar.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 0))
        button(toolbar, S.BTN_NEW_GAME, self.new_game).pack(side="left", padx=2)
        self.take_back_button = button(toolbar, S.MODE_TAKE_BACK, lambda: self.mode.take_back())

        self.status = tk.Label(right, bg=PANEL_BG, fg=PANEL_FG, font=FONT_STATUS,
                               anchor="w", justify="left", padx=10, pady=6)
        self.status.grid(row=1, column=0, sticky="ew")
        self.status.bind("<Configure>", lambda e: self.status.configure(wraplength=e.width - self._px(20)))

        # The active mode's own controls (e.g. Resign); hidden when the mode has none
        self.mode_panel = tk.Frame(right, bg=PANEL_BG)
        self.mode_panel.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))
        self.mode_panel.grid_remove()

        self.movelist = MoveListView(right, self.model, self.select_node, self.edit_tree,
                                     can_edit=lambda: self.mode.allows(EDIT_TREE))
        self.movelist.grid(row=3, column=0, sticky="nsew")

        nav = tk.Frame(right, bg=PANEL_BG)
        nav.grid(row=4, column=0, sticky="ew", padx=6, pady=6)
        self.nav_buttons = {}   # disabled when the mode does not allow them (_update_nav)
        for i, (name, text, command) in enumerate(((NAV_FIRST, S.BTN_FIRST, self.go_start),
                                                   (NAV_PREV, S.BTN_PREV, self.back),
                                                   (NAV_NEXT, S.BTN_NEXT, self.forward),
                                                   (NAV_LAST, S.BTN_LAST, self.go_end))):
            nav.columnconfigure(i, weight=1, uniform="nav")
            self.nav_buttons[name] = button(nav, text, command)
            self.nav_buttons[name].grid(row=0, column=i, sticky="ew", padx=2)
        nav.columnconfigure(4, weight=2)
        button(nav, S.BTN_FLIP, self.flip).grid(row=0, column=4, sticky="ew", padx=2)

        # Comment & FEN: collapsible; open or closed is remembered per mode
        self.details_toggle = tk.Button(right, command=self._toggle_details, bg=PANEL_BG, fg=MUTED_FG,
                                        activebackground=PANEL_BG, activeforeground=PANEL_FG, relief="flat",
                                        bd=0, anchor="w", padx=10, font=FONT_SMALL_BOLD, takefocus=0)
        self.details_toggle.grid(row=5, column=0, sticky="ew", pady=(0, 4))
        self.details = tk.Frame(right, bg=PANEL_BG)
        self.details.grid(row=6, column=0, sticky="ew")
        self.details.columnconfigure(0, weight=1)

        tk.Label(self.details, text=S.LABEL_COMMENT, bg=PANEL_BG, fg=MUTED_FG, anchor="w",
                 font=FONT_SMALL).grid(row=0, column=0, sticky="ew", padx=10)
        self.comment = tk.Text(self.details, height=3, bg=ENTRY_BG, fg=PANEL_FG, insertbackground=PANEL_FG,
                               relief="flat", font=FONT, wrap="word", padx=6, pady=4)
        self.comment.grid(row=1, column=0, sticky="ew", padx=8)
        self.comment.bind("<FocusOut>", lambda e: self.save_comment(rebuild=True))

        fen_row = tk.Frame(self.details, bg=PANEL_BG)
        fen_row.grid(row=2, column=0, sticky="ew", padx=8, pady=8)
        fen_row.columnconfigure(1, weight=1)
        tk.Label(fen_row, text=S.LABEL_FEN, bg=PANEL_BG, fg=MUTED_FG,
                 font=FONT_SMALL).grid(row=0, column=0, padx=(2, 6))
        self.fen_var = tk.StringVar()
        self.fen_entry = tk.Entry(fen_row, textvariable=self.fen_var, bg=ENTRY_BG, fg=PANEL_FG,
                                  readonlybackground=ENTRY_BG, insertbackground=PANEL_FG, relief="flat",
                                  font=FONT_MONO_SMALL)
        self.fen_entry.grid(row=0, column=1, sticky="ew", ipady=4)
        self.fen_entry.bind("<Return>", self._fen_entered)
        button(fen_row, S.BTN_COPY, self.files.copy_fen).grid(row=0, column=2, padx=(6, 0))

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self._guarded = []   # (menu, index, command name for mode.allows)

        def guarded(menu, name, **kw):
            menu.add_command(**kw)
            self._guarded.append((menu, menu.index("end"), name))

        files = self.files
        m = tk.Menu(menubar, tearoff=0, postcommand=self._update_menu_states)
        m.add_command(label=S.FILE_NEW, accelerator="Ctrl+N", command=self.new_game)
        guarded(m, OPEN, label=S.FILE_OPEN, accelerator="Ctrl+O", command=files.open_file)
        m.add_command(label=S.FILE_SAVE, accelerator="Ctrl+S", command=files.save)
        m.add_command(label=S.FILE_SAVE_AS, command=files.save_as)
        m.add_command(label=S.FILE_SAVE_FEN, command=files.save_fen)
        m.add_separator()
        m.add_command(label=S.FILE_COPY_PGN, accelerator="Ctrl+C", command=files.copy_pgn)
        m.add_command(label=S.FILE_COPY_FEN, command=files.copy_fen)
        guarded(m, PASTE, label=S.FILE_PASTE, accelerator="Ctrl+V", command=files.paste)
        m.add_separator()
        m.add_command(label=S.FILE_EXIT, command=self.exit)
        menubar.add_cascade(label=S.MENU_FILE, menu=m)

        self.edit_menu = tk.Menu(menubar, tearoff=0, postcommand=self._update_edit_menu)
        self.edit_menu.add_command(label=S.EDIT_DELETE_LAST, accelerator="Ctrl+Z", command=self.delete_last)
        self.edit_menu.add_command(label=S.EDIT_RESTORE, accelerator="Ctrl+Y", command=self.restore_deleted)
        menubar.add_cascade(label=S.MENU_EDIT, menu=self.edit_menu)

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
        m.add_separator()
        m.add_command(label=S.VIEW_ENGINE_PATH, command=self._choose_engine_path)
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

    def _update_edit_menu(self):
        can_delete = self.mode.can_take_back() if self.mode.takes_back else self.mode.allows(DELETE_LAST)
        can_restore = self.mode.allows(EDIT_TREE) and self.model.can_restore()
        self.edit_menu.entryconfigure(0, state="normal" if can_delete else "disabled")
        self.edit_menu.entryconfigure(1, state="normal" if can_restore else "disabled")

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
        if self.mode.takes_back:
            self.take_back_button.pack(side="left", padx=2)
        else:
            self.take_back_button.pack_forget()
        self._show_details()

    def _details_open(self):
        """settings["details_open"], e.g. {"board": True, "vs_computer": False}. A mode that
        is not listed uses its show_details."""
        is_open = self.settings["details_open"].get(self.mode.key)
        return is_open if isinstance(is_open, bool) else self.mode.show_details

    def _show_details(self):
        is_open = self._details_open()
        self.details_toggle.configure(text=S.DETAILS_OPEN if is_open else S.DETAILS_CLOSED)
        if is_open:
            self.details.grid()
        else:
            self.details.grid_remove()

    def _toggle_details(self):
        self.save_comment(rebuild=True)
        self.settings["details_open"] = {**self.settings["details_open"], self.mode.key: not self._details_open()}
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

        def leave_text_field(event):
            # A click anywhere else takes focus away from the text fields, so that the arrow keys
            # and F work again. (The move list has its own handler, which stops this event.)
            if in_main_window(event) and event.widget not in (self.comment, self.fen_entry):
                self.board.focus_set()

        files = self.files
        keys = {
            "<Left>": self.back, "<Right>": self.forward, "<Home>": self.go_start, "<End>": self.go_end,
            "<Up>": lambda: self.switch_variation(-1), "<Down>": lambda: self.switch_variation(1),
            "<f>": self.flip, "<F>": self.flip,
            "<Control-z>": self.delete_last, "<Control-Z>": self.delete_last,
            "<Control-y>": self.restore_deleted, "<Control-Y>": self.restore_deleted,
            "<Control-c>": files.copy_pgn, "<Control-C>": files.copy_pgn,
            "<Control-v>": files.paste, "<Control-V>": files.paste,
        }
        for sequence, handler in keys.items():
            self.root.bind_all(sequence, board_key(handler))
        for sequence, handler in {"<Control-n>": self.new_game, "<Control-N>": self.new_game,
                                  "<Control-o>": files.open_file, "<Control-O>": files.open_file,
                                  "<Control-s>": files.save, "<Control-S>": files.save}.items():
            self.root.bind_all(sequence, always(handler))
        self.root.bind_all("<ButtonPress-1>", leave_text_field, add="+")

    # --- Keeping the views up to date ---------------------------------------

    def position_changed(self, rebuild=False):
        """The current position or the game tree changed. rebuild: the tree did, so the move
        list is drawn again (new move, deletion, comment)."""
        self.mode.position_changed()
        self.board.position_changed()
        if rebuild:
            self.movelist.rebuild()
        else:
            self.movelist.show_current()
        self.fen_var.set(self.model.fen())
        self._load_comment()
        self.update_status()

    def update_status(self):
        """What the mode says changed: labels, buttons and arrows. The position is the same, so
        the comment field and a piece being moved are left alone."""
        hints = self.mode.hint_arrows()
        self.board.set_hints(hints)
        self.mode.hints_shown(hints)
        self.board.rules_changed()
        self._show_status()
        self.mode_title.configure(text=self.mode.title())
        self.score.configure(text=self.mode.score_text() or "")
        self._update_subtitle()
        self._update_light()
        self.fen_entry.configure(state="normal" if self.mode.allows(PASTE) else "readonly")
        self.comment.configure(state="normal" if self.mode.allows(EDIT_COMMENT) else "disabled")
        self._update_nav()
        self._update_names()
        self.update_title()

    def _show_status(self):
        if self._notice_after is not None:
            self.root.after_cancel(self._notice_after)
            self._notice_after = None
        self.status.configure(text=self.mode.status_text() or self.model.status())

    def _show_notice(self, text):
        """Explain something on the status line for a moment."""
        self._show_status()
        self.status.configure(text=text)
        self._notice_after = self.root.after(NOTICE_MS, self._show_status)

    def allowed(self, command):
        """The mode allows this command now; if not, tell the user why nothing happens."""
        if self.mode.allows(command):
            return True
        self._show_notice(S.BLOCKED_BROWSE if command == NAVIGATE else S.BLOCKED_IN_GAME)
        return False

    def _update_subtitle(self):
        text = self.mode.subtitle()
        if text is None:
            self.subtitle.pack_forget()
            return
        self.subtitle.configure(text=text)
        if not self.subtitle.winfo_manager():
            self.subtitle.pack(side="top", fill="x", after=self._subtitle_after)

    def _update_nav(self):
        """The |◀ ◀ ▶ ▶| buttons browse the game, when the mode allows it. Take Back is separate."""
        state = "normal" if self.mode.allows(NAVIGATE) else "disabled"
        for nav_button in self.nav_buttons.values():
            nav_button.configure(state=state)
        self.take_back_button.configure(state="normal" if self.mode.can_take_back() else "disabled")

    def _update_light(self):
        state = self.mode.light()
        if state is None:
            self.light.pack_forget()
            return
        self.light.set_state(state, self.mode.light_text())
        if not self.light.winfo_manager():
            # Before the title: in a narrow window the title is cut, not the result of the game
            self.light.pack(side="right", padx=(12, 0), before=self.mode_title)

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

    def update_title(self):
        path = self.files.path
        name = path.name if path else S.UNTITLED
        mark = "*" if self.model.modified else ""
        self.root.title(f"{mark}{name} – {S.APP_TITLE}")

    def _load_comment(self):
        self._comment_node = self.model.node
        self.comment.configure(state="normal")
        self.comment.delete("1.0", "end")
        self.comment.insert("1.0", visible_comment(self.model.node.comment))
        # update_status(), which always follows, disables the field if the mode does not allow editing

    def save_comment(self, rebuild=False):
        node = self._comment_node
        if node is None or not self.mode.allows(EDIT_COMMENT):
            return False
        changed = self.model.set_comment(node, self.comment.get("1.0", "end"))
        if changed and rebuild:
            self.movelist.rebuild()
            self.update_title()
        return changed

    # --- Moves and navigation ---------------------------------------------

    def user_move(self, frm, to, promotion):
        if self.mode.can_move(self.model.board.turn):   # the game may have ended during the drag
            self.play_move(chess.Move(frm, to, promotion))
        else:
            self.illegal_move()

    def play_move(self, move, from_end=False):
        """Play a chess.Move from any source (the board or an engine) and update the views.

        from_end: play it after the last move of the line (an engine reply arriving while
        the user is looking at earlier moves).
        """
        self.save_comment()
        if from_end:
            self.model.go_end()
        event = self.model.play(move)
        if event is None:
            self.illegal_move()
            return
        self.mode.after_move()
        self.position_changed(rebuild=True)
        self.sounds.play(event)

    def illegal_move(self):
        self.board.redraw()
        self.sounds.play(ILLEGAL)

    def _navigate(self, action):
        if not self.allowed(NAVIGATE):
            return
        changed = self.save_comment()
        moved = action()
        if moved:
            self.position_changed(rebuild=changed)
            if self.model.node.move is not None:
                self.sounds.play(event_for(self.model.node))
        elif changed:
            self.movelist.rebuild()
            self.update_title()

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
        """Ctrl+Z. In a mode with Take Back that is what it means there."""
        if self.mode.takes_back:
            self.mode.take_back()
            return
        if not self.allowed(DELETE_LAST):
            return
        self.save_comment()
        if self.model.delete_last():
            self.position_changed(rebuild=True)

    def restore_deleted(self):
        """Ctrl+Y: undo the latest deletion of moves."""
        if not self.allowed(EDIT_TREE):
            return
        self.save_comment()
        if self.model.restore_deleted():
            self.position_changed(rebuild=True)

    def take_back(self, color):
        """Remove the moves back to `color`'s previous turn (Take Back in a game mode)."""
        if not self.mode.allows(TAKE_BACK):
            return False
        self.save_comment()
        if not self.model.take_back(color):
            return False
        self.position_changed(rebuild=True)
        return True

    def edit_tree(self, action, node):
        if not self.allowed(EDIT_TREE):
            return
        self.save_comment()
        handler = {"promote": self.model.promote_to_main,
                   "delete_variation": self.model.delete_variation,
                   "delete_from_here": self.model.delete_from_here}[action]
        if handler(node):
            self.position_changed(rebuild=True)

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

    def set_mode(self, key, config=None, discard=False):
        """Switch to the mode with this key (or restart the current one). Returns True on success.

        config: what the new mode's dialog would return, so that it is not shown. discard: the
        new mode replaces the game without offering to save it.

        The order matters (see app/modes/base.py): the new mode's dialog first, then leaving
        the old mode, and only after the old mode is closed does the new one start."""
        cls = mode_class(key)
        if cls is None:
            return False
        new = cls(self.ctx)
        if config is None:
            config = new.choose()
        if config is None or not self._leave_mode(keep_game=discard or not new.replaces_game):
            return False
        old, self.mode = self.mode, new
        old.deactivate()
        self.mode_var.set(key)
        self._build_mode_panel()
        new.start(config)
        self.position_changed(rebuild=True)
        return True

    def _leave_mode(self, keep_game):
        """Ask before leaving the active mode, then leave it (e.g. resign). keep_game=False:
        the game will be replaced, so offer to save it first.
        False = the user cancelled, and nothing has changed (unless the disk failed while
        saving; the user was told, and the game is still there to save again)."""
        if not self.mode.confirm_leave():
            return False
        if keep_game:
            self.save_comment()
            self.mode.leave()
            return True
        return self.files.confirm_discard(before_write=self.mode.leave,
                                          will_change=self.mode.leaving_changes_game())

    def new_game(self):
        if self.mode.new_game():
            return
        if self.files.confirm_discard():
            self.files.set_position()

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

    def _choose_engine_path(self):
        path = choose_engine_path(self.root, self.settings["engine_path"], StockfishEngine.default_dir(self.app_dir))
        if path is not None:
            self.settings["engine_path"] = path
            self._build_mode_panel()   # a panel may depend on whether the engine is there

    # --- Files ------------------------------------------------------------

    def _fen_entered(self, event):
        self.files.fen_entered(self.fen_var.get())
        return "break"

    # --- Exit -------------------------------------------------------------

    def _autosave(self):
        """Settings are written soon after they change, so that a crash does not lose them.
        After a failure (a read-only folder) only exit() tries again, and tells the user."""
        if self.settings.dirty and not self._autosave_failed:
            self._autosave_failed = not self.settings.save()
        self.root.after(AUTOSAVE_MS, self._autosave)

    def exit(self):
        """Close at once, without questions: an unsaved game is not kept, and a running one is
        not resigned."""
        self.mode.deactivate()   # stops engine processes and timers
        if self.root.state() == "normal":
            self.settings["window_geometry"] = self.root.geometry()
        if not self.settings.save():
            messagebox.showwarning(S.ERROR_TITLE, S.ERROR_SETTINGS.format(path=self.settings.path),
                                   parent=self.root)
        self.root.destroy()
