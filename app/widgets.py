"""Widgets in the style of the right-hand panel, for MainWindow and the modes' panels.

A mode's panel uses these instead of repeating colours and fonts (see Mode.build_panel).
"""

import tkinter as tk
from tkinter import ttk

from .theme import (BUTTON_ACTIVE, BUTTON_BG, ENTRY_BG, FONT, FONT_BOLD, FONT_LARGE_BOLD, FONT_SMALL,
                    LIGHT_COLORS, MUTED_FG, PANEL_BG, PANEL_FG)

SCROLLBAR_STYLE = "Dark.Vertical.TScrollbar"


def button(parent, text, command, **kw):
    return tk.Button(parent, text=text, command=command, bg=BUTTON_BG, fg=PANEL_FG,
                     activebackground=BUTTON_ACTIVE, activeforeground=PANEL_FG, relief="flat",
                     bd=0, padx=10, pady=6, font=FONT_LARGE_BOLD, takefocus=0, **kw)


def label(parent, text="", bold=False, muted=None, wrap=False, **kw):
    """A label on the parent's background. Bold text is bright, other text muted unless
    muted=False. wrap=True wraps the text to the label's width."""
    if muted is None:
        muted = not bold
    widget = tk.Label(parent, text=text, bg=parent["bg"], fg=MUTED_FG if muted else PANEL_FG,
                      font=FONT_BOLD if bold else FONT_SMALL, anchor="w", justify="left", **kw)
    if wrap:
        widget.bind("<Configure>", lambda e: widget.configure(wraplength=e.width))
    return widget


def scrollbar(parent, command):
    """A dark vertical scrollbar. tk.Scrollbar ignores colours on Windows, and the "clam" theme
    is borrowed only for this style's parts, so the dialogs keep the system look."""
    style = ttk.Style(parent)
    if "Dark.Scrollbar.trough" not in style.element_names():
        style.element_create("Dark.Scrollbar.trough", "from", "clam")
        style.element_create("Dark.Scrollbar.thumb", "from", "clam")
        style.layout(SCROLLBAR_STYLE, [("Dark.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Dark.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
        style.configure(SCROLLBAR_STYLE, background=BUTTON_BG, troughcolor=PANEL_BG, bordercolor=PANEL_BG,
                        lightcolor=BUTTON_BG, darkcolor=BUTTON_BG, gripcount=0)
        style.map(SCROLLBAR_STYLE, background=[("active", BUTTON_ACTIVE)])
    return ttk.Scrollbar(parent, orient="vertical", command=command, style=SCROLLBAR_STYLE)


def checkbox(parent, text, variable, command, **kw):
    bg = parent["bg"]
    return tk.Checkbutton(parent, text=text, variable=variable, command=command, bg=bg, fg=PANEL_FG,
                          selectcolor=ENTRY_BG, activebackground=bg, activeforeground=PANEL_FG,
                          disabledforeground=MUTED_FG, font=FONT, bd=0, highlightthickness=0,
                          takefocus=0, **kw)


class Light(tk.Frame):
    """A round lamp and a short text: grey (pending), green (success) or red (fail)."""

    def __init__(self, parent, size=14, **kw):
        super().__init__(parent, bg=parent["bg"], **kw)
        self.canvas = tk.Canvas(self, width=size, height=size, bg=parent["bg"], highlightthickness=0, bd=0)
        self.canvas.pack(side="left", padx=(0, 6))
        self.lamp = self.canvas.create_oval(1, 1, size - 1, size - 1, outline="")
        self.text = tk.Label(self, bg=parent["bg"], fg=PANEL_FG, font=FONT_BOLD)
        self.text.pack(side="left")

    def set_state(self, state, text):
        """state: "pending", "success" or "fail"; text: the words next to the lamp."""
        self.canvas.itemconfigure(self.lamp, fill=LIGHT_COLORS[state])
        self.text.configure(text=text)


def light(parent, size=14):
    """A success light; size: the lamp's diameter in pixels."""
    return Light(parent, size)
