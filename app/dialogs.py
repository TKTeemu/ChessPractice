"""Small modal dialogs of the main window: choosing a game, starting a game against
the computer and choosing an opening to learn."""

import tkinter as tk
from tkinter import messagebox, ttk

import chess

from . import strings as S


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


def choose_game(root, games):
    """Let the user pick one game from a multi-game PGN. Returns an index or None."""
    top = _dialog(root, S.CHOOSE_GAME_TITLE)
    result = {"index": None}
    tk.Label(top, text=S.CHOOSE_GAME_PROMPT.format(count=len(games)), anchor="w").pack(
        fill="x", padx=10, pady=(10, 4))
    frame = tk.Frame(top)
    frame.pack(fill="both", expand=True, padx=10)
    listbox = tk.Listbox(frame, width=80, height=min(20, len(games)), font=("Segoe UI", 10),
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
    gives the (engine key, level key) selected.
    """
    levels = {cls.key: cls(settings).levels() for cls in engines}
    names = {cls.name: cls.key for cls in engines}
    saved = settings[f"{prefix}_engine"]
    engine_key = saved if saved in levels else engines[0].key
    engine_var = tk.StringVar(value=next(cls.name for cls in engines if cls.key == engine_key))
    engine_box = ttk.Combobox(parent, textvariable=engine_var, values=list(names), state="readonly", width=24)
    level_var = tk.StringVar()
    level_box = ttk.Combobox(parent, textvariable=level_var, state="readonly", width=24)

    def engine_changed(event=None, wanted=None):
        engine_levels = levels[names[engine_var.get()]]
        level_box.configure(values=[lv.label or S.LEVEL_NONE for lv in engine_levels])
        level = next((lv for lv in engine_levels if lv.key == wanted), engine_levels[0])
        level_var.set(level.label or S.LEVEL_NONE)

    engine_box.bind("<<ComboboxSelected>>", engine_changed)
    engine_changed(wanted=settings[f"{prefix}_level"])

    def chosen():
        key = names[engine_var.get()]
        level = next(lv for lv in levels[key] if (lv.label or S.LEVEL_NONE) == level_var.get())
        return key, level.key

    return engine_box, level_box, chosen


def new_computer_game(root, engines, notes, settings, current_finished):
    """Play vs Computer: engine, level, colour and start position.

    `engines` are the available engine classes, `notes` explain the missing ones.
    Returns {"engine", "level", "color", "start"} (keys as stored in settings) or None.
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

    row = 4
    tk.Label(top, text=S.VS_CLOCK_NOTE.format(minutes=settings["vs_minutes"]), anchor="w",
             fg="#555555").grid(row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 0))
    for note in notes:
        row += 1
        tk.Label(top, text=note, anchor="w", justify="left", fg="#A03020").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 0))

    def ok(event=None):
        if start_var.get() == "current" and current_finished:
            messagebox.showinfo(S.VS_TITLE, S.VS_START_FINISHED, parent=top)
            start_var.set("initial")
            return
        engine, level = chosen()
        result.update(engine=engine, level=level, color=color_var.get(), start=start_var.get())
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

    Returns {"opening", "role", "engine", "level", "vary"} (as stored in settings) or None.
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
                      font=("Segoe UI", 10), padx=8, takefocus=0)
    preview.tag_configure("title", font=("Segoe UI", 11, "bold"))
    preview.tag_configure("muted", foreground="#555555")
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

    row = 4
    for note in notes:
        row += 1
        tk.Label(top, text=note, anchor="w", justify="left", fg="#A03020").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=12, pady=(8, 0))

    def ok(event=None):
        opening = current()
        if opening is None:
            return
        engine, level = chosen()
        result.update(opening=opening.key, role=role_var.get(), engine=engine, level=level,
                      vary=vary_var.get())
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
