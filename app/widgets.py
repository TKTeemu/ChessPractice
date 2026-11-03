"""Widgets in the style of the right-hand panel, for MainWindow and the modes' panels.

A mode's panel uses these instead of repeating colours and fonts (see Mode.build_panel).
"""

import tkinter as tk

from .theme import (BUTTON_ACTIVE, BUTTON_BG, ENTRY_BG, FONT, FONT_BOLD, FONT_LARGE_BOLD, FONT_SMALL,
                    MUTED_FG, PANEL_FG)


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


def checkbox(parent, text, variable, command, **kw):
    bg = parent["bg"]
    return tk.Checkbutton(parent, text=text, variable=variable, command=command, bg=bg, fg=PANEL_FG,
                          selectcolor=ENTRY_BG, activebackground=bg, activeforeground=PANEL_FG,
                          disabledforeground=MUTED_FG, font=FONT, bd=0, highlightthickness=0,
                          takefocus=0, **kw)
