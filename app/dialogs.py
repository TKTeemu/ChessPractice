"""Small modal dialogs of the main window: choosing a game, starting a game against
the computer, choosing an opening to learn, choosing a practice level and locating Stockfish."""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import chess

from . import strings as S
from .theme import DIALOG_MUTED_FG, DIALOG_WARNING_FG, FONT, FONT_LARGE_BOLD


def _dialog(root, title):
    top = tk.Toplevel(root)
    top.title(title)
    top.transient(root)
    top.resizable(False, False)
    return top


def _show_modal(root, top):
    top.update_idletasks()
    x = root.winfo_rootx() + (root.winfo_width() - top.winfo_width()) // 2
    y = root.winfo_rooty() + (root.winfo_height() - top.winfo_height()) // 3
    top.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    top.grab_set()
    root.wait_window(top)


def _number_box(parent, value, low, high):
    """A spin box for a whole number. Returns (widget, read), where read() gives the number,
    kept between low and high; anything that is not a number reads as `value`."""
    var = tk.IntVar(value=value)
    widget = tk.Spinbox(parent, from_=low, to=high, width=4, textvariable=var)

    def read():
        try:
            return max(low, min(high, var.get()))
        except tk.TclError:
            return max(low, min(high, value))

    return widget, read


def choose_game(root, games):
    """Let the user pick one game from a multi-game PGN. Returns an index or None."""
    top = _dialog(root, S.CHOOSE_GAME_TITLE)
    result = {"index": None}
    tk.Label(top, text=S.CHOOSE_GAME_PROMPT.format(count=len(games)), anchor="w").pack(
        fill="x", padx=10, pady=(10, 4))
    frame = tk.Frame(top)
    frame.pack(fill="both", expand=True, padx=10)
    listbox = tk.Listbox(frame, width=80, height=min(20, len(games)), font=FONT,
                         activestyle="none", exportselection=False)
    scroll = tk.Scrollbar(frame, command=listbox.yview)
    listbox.configure(yscrollcommand=scroll.set)
    listbox.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    for i, game in enumerate(games, 1):
        h = game.headers
        listbox.insert("end", f"{i}. {h.get('White', '?')} – {h.get('Black', '?')}   "
                              f"{h.get('Result', '*')}   {h.get('Event', '')}  {h.get('Date', '')}")
    listbox.selection_set(0)

    def ok(event=None):
        sel = listbox.curselection()
        if sel:
            result["index"] = sel[0]
        top.destroy()

    buttons = tk.Frame(top)
    buttons.pack(fill="x", padx=10, pady=10)
    tk.Button(buttons, text=S.BTN_CANCEL, width=10, command=top.destroy).pack(side="right")
    tk.Button(buttons, text=S.BTN_OK, width=10, command=ok).pack(side="right", padx=6)
    listbox.bind("<Double-Button-1>", ok)
    top.bind("<Return>", ok)
    top.bind("<Escape>", lambda e: top.destroy())
    listbox.focus_set()
    _show_modal(root, top)
    return result["index"]


def _engine_level_pickers(parent, engines, settings, prefix):
    """Engine and level comboboxes, preset from settings[prefix + "_engine" / "_level"].

    Returns (engine_box, level_box, chosen); the caller places the boxes, and chosen()
    gives the (engine key, level key) selected. The choices are found by their position
    in the list, never by the text shown, so two entries with the same label cannot mix.
    """
    levels = [cls(settings).levels() for cls in engines]
    saved = settings[f"{prefix}_engine"]
    engine_box = ttk.Combobox(parent, values=[cls.name for cls in engines], state="readonly", width=24)
    engine_box.current(next((i for i, cls in enumerate(engines) if cls.key == saved), 0))
    level_box = ttk.Combobox(parent, state="readonly", width=24)

    def engine_changed(event=None, wanted=None):
        engine_levels = levels[engine_box.current()]
        level_box.configure(values=[lv.label or S.LEVEL_NONE for lv in engine_levels])
        level_box.current(next((i for i, lv in enumerate(engine_levels) if lv.key == wanted), 0))

    engine_box.bind("<<ComboboxSelected>>", engine_changed)
    engine_changed(wanted=settings[f"{prefix}_level"])

    def chosen():
        index = engine_box.current()
        return engines[index].key, levels[index][max(level_box.current(), 0)].key

    return engine_box, level_box, chosen


def new_computer_game(root, engines, notes, settings, current_finished):
    """Play vs Computer: engine, level, colour and start position.

    `engines` are the available engine classes, `notes` explain the missing ones.
    Returns {"engine", "level", "color", "start", "minutes", "increment"} (keys as stored in
    settings) or None.
    """
    top = _dialog(root, S.VS_TITLE)
    result = {}

    def labelled(row, text):
        tk.Label(top, text=text, anchor="w").grid(row=row, column=0, sticky="w", padx=(12, 6), pady=4)

    labelled(0, S.VS_ENGINE)
    labelled(1, S.VS_LEVEL)
    engine_box, level_box, chosen = _engine_level_pickers(top, engines, settings, "vs")
    engine_box.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=4)
    level_box.grid(row=1, column=1, sticky="w", padx=(0, 12), pady=4)

    def radios(row, text, choices, value):
        labelled(row, text)
        var = tk.StringVar(value=value if value in choices else next(iter(choices)))
        frame = tk.Frame(top)
        frame.grid(row=row, column=1, sticky="w", padx=(0, 12), pady=4)
        for key, label in choices.items():
            tk.Radiobutton(frame, text=label, value=key, variable=var).pack(side="left", padx=(0, 8))
        return var

    color_var = radios(2, S.VS_COLOR, S.VS_COLORS, settings["vs_color"])
    start_var = radios(3, S.VS_START, S.VS_STARTS, settings["vs_start"])
    if current_finished:
        start_var.set("initial")

    labelled(4, S.VS_TIME)
    time_row = tk.Frame(top)
    time_row.grid(row=4, column=1, sticky="w", padx=(0, 12), pady=4)
    minutes_box, read_minutes = _number_box(time_row, settings["vs_minutes"], 1, 180)
    increment_box, read_increment = _number_box(time_row, settings["vs_increment"], 0, 60)
    minutes_box.pack(side="left")
    tk.Label(time_row, text=S.VS_MINUTES).pack(side="left", padx=6)
    increment_box.pack(side="left")
    tk.Label(time_row, text=S.VS_INCREMENT).pack(side="left", padx=6)

    row = 5
    tk.Label(top, text=S.VS_NOTE, anchor="w", fg=DIALOG_MUTED_FG).grid(
        row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 0))
    for note in notes:
        row += 1
        tk.Label(top, text=note, anchor="w", justify="left", fg=DIALOG_WARNING_FG).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 0))

    def ok(event=None):
        if start_var.get() == "current" and current_finished:
            messagebox.showinfo(S.VS_TITLE, S.VS_START_FINISHED, parent=top)
            start_var.set("initial")
            return
        engine, level = chosen()
        result.update(engine=engine, level=level, color=color_var.get(), start=start_var.get(),
                      minutes=read_minutes(), increment=read_increment())
        top.destroy()

    buttons = tk.Frame(top)
    buttons.grid(row=row + 1, column=0, columnspan=2, sticky="e", padx=12, pady=12)
    tk.Button(buttons, text=S.VS_PLAY, width=10, command=ok).pack(side="left", padx=6)
    tk.Button(buttons, text=S.BTN_CANCEL, width=10, command=top.destroy).pack(side="left")
    top.bind("<Return>", ok)
    top.bind("<Escape>", lambda e: top.destroy())
    _show_modal(root, top)
    return result or None


def _start_san(opening):
    """The moves that define the opening, e.g. "1. d4 d5 2. c4" (PGN header Plies, default 1)."""
    plies = opening.game.headers.get("Plies", "1")
    moves = list(opening.game.mainline_moves())[:int(plies) if plies.isdigit() else 1]
    return chess.Board().variation_san(moves)


def _opening_matches(opening, query):
    return any(query in text.lower() for text in (opening.name, opening.eco, opening.group, _start_san(opening)))


def choose_opening(root, book, engines, notes, settings):
    """Learn Openings: the opening (grouped list with search), your side, engine and level.

    Returns {"opening", "role", "engine", "level", "vary", "suggest_moves"} (as stored in
    settings) or None.
    """
    top = _dialog(root, S.LEARN_TITLE)
    result = {}
    openings = {f"o:{o.key}": o for o in book.openings}

    search_row = tk.Frame(top)
    search_row.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 4))
    tk.Label(search_row, text=S.LEARN_SEARCH).pack(side="left")
    search_var = tk.StringVar()
    search = tk.Entry(search_row, textvariable=search_var, width=30)
    search.pack(side="left", padx=(6, 0))

    lists = tk.Frame(top)
    lists.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=4)
    tree = ttk.Treeview(lists, columns=("start",), show="tree", selectmode="browse", height=16)
    tree.column("#0", width=230)
    tree.column("start", width=150)
    scroll = tk.Scrollbar(lists, command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="left", fill="y")
    preview = tk.Text(lists, width=30, height=16, wrap="word", relief="flat", bg=top["bg"],
                      font=FONT, padx=8, takefocus=0)
    preview.tag_configure("title", font=FONT_LARGE_BOLD)
    preview.tag_configure("muted", foreground=DIALOG_MUTED_FG)
    preview.pack(side="left", fill="both", padx=(8, 0))

    def fill_tree(*_):
        query = search_var.get().strip().lower()
        selected = tree.selection()
        tree.delete(*tree.get_children())
        for group, members in book.groups():
            shown = [o for o in members if not query or _opening_matches(o, query)]
            if not shown:
                continue
            gid = f"g:{group}"
            tree.insert("", "end", iid=gid, text=group, open=True)
            for o in shown:
                tree.insert(gid, "end", iid=f"o:{o.key}", text=o.name, values=(_start_san(o),))
        keep = [iid for iid in selected if tree.exists(iid)]
        first_opening = next((iid for g in tree.get_children() for iid in tree.get_children(g)), None)
        target = keep[0] if keep else first_opening
        if target:
            tree.selection_set(target)
            tree.see(target)
        else:
            show_preview(None)

    role_var = tk.StringVar(value=settings["learn_role"] if settings["learn_role"] in S.LEARN_ROLES
                            else "opening")
    role_row = tk.Frame(top)
    role_row.grid(row=2, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 4))
    tk.Label(role_row, text=S.LEARN_YOU_PLAY, width=10, anchor="w").pack(side="left")
    role_buttons = {key: tk.Radiobutton(role_row, value=key, variable=role_var) for key in S.LEARN_ROLES}
    for button in role_buttons.values():
        button.pack(side="left", padx=(0, 8))

    def current():
        sel = [iid for iid in tree.selection() if iid in openings]
        return openings[sel[0]] if sel else None

    def show_preview(opening):
        preview.configure(state="normal")
        preview.delete("1.0", "end")
        if opening is not None:
            moves = list(opening.game.mainline_moves())
            eco = opening.eco.replace("-", "–")
            preview.insert("end", opening.name + "\n", "title")
            if eco:
                preview.insert("end", eco + "\n", "muted")
            preview.insert("end", "\n" + S.LEARN_MAIN_LINE.format(count=(len(moves) + 1) // 2) + "\n", "muted")
            preview.insert("end", chess.Board().variation_san(moves))
        preview.configure(state="disabled")
        side = opening.side if opening is not None else chess.WHITE
        for key, button in role_buttons.items():
            color = side if key == "opening" else not side
            button.configure(text=S.LEARN_ROLES[key].format(color=S.COLOR_NAMES[color]))

    tree.bind("<<TreeviewSelect>>", lambda e: show_preview(current()))

    pickers = tk.Frame(top)
    pickers.grid(row=3, column=0, columnspan=2, sticky="w", padx=12, pady=4)
    engine_box, level_box, chosen = _engine_level_pickers(pickers, engines, settings, "learn")
    tk.Label(pickers, text=S.VS_ENGINE, width=10, anchor="w").pack(side="left")
    engine_box.pack(side="left")
    tk.Label(pickers, text=S.VS_LEVEL).pack(side="left", padx=(12, 6))
    level_box.configure(width=12)
    level_box.pack(side="left")

    vary_var = tk.BooleanVar(value=settings["learn_vary"])
    tk.Checkbutton(top, text=S.LEARN_VARY, variable=vary_var).grid(
        row=4, column=0, columnspan=2, sticky="w", padx=12, pady=4)
    suggest_row = tk.Frame(top)
    suggest_row.grid(row=5, column=0, columnspan=2, sticky="w", padx=12, pady=4)
    tk.Label(suggest_row, text=S.LEARN_SUGGEST_UNTIL).pack(side="left")
    suggest_box, read_suggest = _number_box(suggest_row, settings["learn_suggest_moves"], 10, 15)
    suggest_box.pack(side="left", padx=6)

    row = 5
    for note in notes:
        row += 1
        tk.Label(top, text=note, anchor="w", justify="left", fg=DIALOG_WARNING_FG).grid(
            row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 0))

    def ok(event=None):
        opening = current()
        if opening is None:
            return
        engine, level = chosen()
        result.update(opening=opening.key, role=role_var.get(), engine=engine, level=level,
                      vary=vary_var.get(), suggest_moves=read_suggest())
        top.destroy()

    buttons = tk.Frame(top)
    buttons.grid(row=row + 1, column=0, columnspan=2, sticky="e", padx=12, pady=12)
    tk.Button(buttons, text=S.LEARN_START, width=10, command=ok).pack(side="left", padx=6)
    tk.Button(buttons, text=S.BTN_CANCEL, width=10, command=top.destroy).pack(side="left")

    saved = f"o:{settings['learn_opening']}"
    fill_tree()
    if tree.exists(saved):
        tree.selection_set(saved)
        tree.see(saved)
    search_var.trace_add("write", fill_tree)
    tree.bind("<Double-Button-1>", lambda e: ok() if tree.identify_row(e.y) in openings else None)
    top.bind("<Return>", ok)
    top.bind("<Escape>", lambda e: top.destroy())
    search.focus_set()
    _show_modal(root, top)
    return result or None


def choose_endgame(root, levels, played, solved, notes, settings, title=S.END_TITLE, prefix="end"):
    """Endgame and Middlegame Practice: the difficulty level and the clock.

    `levels` are (difficulty, name, number of positions), `played` and `solved` map a difficulty
    to how many of its positions have been played and solved, `notes` explain a missing engine.
    `title` names the dialog and `prefix` starts the names of the mode's settings.
    Returns {"difficulty", "minutes"} or None.
    """
    top = _dialog(root, title)
    result = {}
    saved = settings[f"{prefix}_difficulty"]
    level_var = tk.IntVar(value=saved if any(d == saved for d, _, _ in levels) else levels[0][0])

    tk.Label(top, text=S.END_DIFFICULTY, anchor="w").grid(row=0, column=0, columnspan=3, sticky="w",
                                                          padx=12, pady=(12, 4))
    for row, (difficulty, name, count) in enumerate(levels, 1):
        tk.Radiobutton(top, text=f"{difficulty}  {name}", value=difficulty, variable=level_var,
                       anchor="w").grid(row=row, column=0, columnspan=2, sticky="w", padx=(24, 12))
        tk.Label(top, text=S.END_LEVEL_COUNT.format(count=count, played=played.get(difficulty, 0),
                                                    solved=solved.get(difficulty, 0)),
                 fg=DIALOG_MUTED_FG, anchor="e").grid(row=row, column=2, sticky="e", padx=(0, 12))

    row = len(levels) + 1
    time_row = tk.Frame(top)
    time_row.grid(row=row, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 0))
    tk.Label(time_row, text=S.END_TIME).pack(side="left")
    minutes_box, read_minutes = _number_box(time_row, settings[f"{prefix}_minutes"], 1, 180)
    minutes_box.pack(side="left", padx=6)
    tk.Label(time_row, text=S.END_MINUTES).pack(side="left")

    for note in notes:
        row += 1
        tk.Label(top, text=note, anchor="w", justify="left", fg=DIALOG_WARNING_FG).grid(
            row=row, column=0, columnspan=3, sticky="w", padx=12, pady=(8, 0))

    def ok(event=None):
        result.update(difficulty=level_var.get(), minutes=read_minutes())
        top.destroy()

    buttons = tk.Frame(top)
    buttons.grid(row=row + 1, column=0, columnspan=3, sticky="e", padx=12, pady=12)
    tk.Button(buttons, text=S.END_START, width=10, command=ok).pack(side="left", padx=6)
    tk.Button(buttons, text=S.BTN_CANCEL, width=10, command=top.destroy).pack(side="left")
    top.bind("<Return>", ok)
    top.bind("<Escape>", lambda e: top.destroy())
    _show_modal(root, top)
    return result or None


def choose_engine_path(root, current, default_folder):
    """Where Stockfish is: `current` is settings["engine_path"] ("" = the default place).
    Returns the new value, or None if nothing changed."""
    top = _dialog(root, S.ENGINE_PATH_TITLE)
    result = {}
    shown = current or S.ENGINE_PATH_DEFAULT.format(folder=default_folder)
    tk.Label(top, text=S.ENGINE_PATH_CURRENT.format(path=shown), anchor="w", justify="left").pack(
        fill="x", padx=12, pady=12)

    def choose_file():
        name = filedialog.askopenfilename(parent=top, filetypes=[(S.FILETYPE_EXE, "*.exe"), (S.FILETYPE_ALL, "*.*")])
        if name:
            result["path"] = name
            top.destroy()

    def use_default():
        result["path"] = ""
        top.destroy()

    buttons = tk.Frame(top)
    buttons.pack(side="bottom", anchor="e", padx=12, pady=(0, 12))
    tk.Button(buttons, text=S.ENGINE_PATH_CHOOSE, command=choose_file).pack(side="left", padx=(0, 6))
    tk.Button(buttons, text=S.ENGINE_PATH_RESET, command=use_default).pack(side="left", padx=(0, 6))
    tk.Button(buttons, text=S.BTN_CANCEL, width=10, command=top.destroy).pack(side="left")
    top.bind("<Escape>", lambda e: top.destroy())
    _show_modal(root, top)
    return result.get("path")
