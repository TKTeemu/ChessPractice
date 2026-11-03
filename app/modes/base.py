"""The Mode interface. A mode decides what the user may do and what happens after a move.

MainWindow asks the active mode questions instead of checking which mode is active.
The defaults behave like the free board: everything allowed, nothing extra.

Switching modes (MainWindow.set_mode) runs in this order:
    new.choose() -> old.confirm_leave() -> (save prompt) -> old.leave() -> old.deactivate()
    -> new.start(config)
so nothing of the new mode happens before the old one has been closed.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class ModeContext:
    """What a mode may use. Passed in by MainWindow; modes do not import MainWindow."""
    root: object                  # tk.Tk
    model: object                 # GameModel: read freely; change through the callables below
    settings: object              # Settings
    app_dir: Path                 # the program folder (assets/, engines/)
    play_move: Callable           # play_move(move, from_end=False)
    new_game: Callable            # new_game(board=None): replace the game, then refresh
    refresh: Callable             # refresh(rebuild=False)
    set_flipped: Callable         # set_flipped(bool)
    set_mode: Callable            # set_mode(key) -> bool
    set_clocks: Callable          # set_clocks({color: (text, active, low)} or None)
    play_sound: Callable          # play_sound(kind)
    take_back: Callable           # take_back(color) -> bool: remove moves back to color's last turn, then refresh


@dataclass
class MenuItem:
    label: str
    command: Callable
    enabled: Callable = lambda: True


class Mode:
    key = ""        # unique, stored in settings.json
    label = ""      # menu text, from strings.py
    show_details = True    # the Comment & FEN section is open until the user closes it
    replaces_game = False  # start() replaces the game: MainWindow asks to save the old one first
    SETTINGS = {}   # the mode's own settings and their defaults, keys prefixed with the mode key

    def __init__(self, ctx):
        self.ctx = ctx

    # Life cycle
    def choose(self):
        """Show the mode's dialog, if any, and return what the user chose (a dict), or None
        to stay in the previous mode. No side effects: the previous mode is still active."""
        return {}

    def start(self, config):
        """Begin, with what choose() returned. The previous mode has been closed."""

    def confirm_leave(self):
        """Before the mode is left, a new game starts or the program exits. Only asks; False = cancel."""
        return True

    def leave(self):
        """The user confirmed leaving (and the save prompt was answered), e.g. resign the game."""

    def deactivate(self):
        """Release engines, timers and threads."""

    # Questions MainWindow asks
    def can_move(self, color):
        return True

    def allows(self, command):
        """command: one of the names in app/commands.py."""
        return True

    def title(self):
        """The mode name shown above the board."""
        return self.label.rstrip("…")

    def subtitle(self):
        """A second, smaller line under the title, e.g. where a position comes from. None = hidden."""
        return None

    def status_text(self):
        """None = the model's normal status."""
        return None

    def score_text(self):
        """Shown above the board on the right, e.g. the material balance. None = nothing."""
        return None

    def light(self):
        """A success light above the board on the right: "pending", "success" or "fail". None = hidden."""
        return None

    def new_game(self):
        """File > New Game and the New Game button. Return True if the mode handled it."""
        return False

    def hint_arrows(self):
        """Suggestion arrows for the board: [(from_sq, to_sq, style)], style "main" or "alt"."""
        return []

    # Notifications
    def after_move(self):
        """After every successful play_move, before the views are refreshed."""

    # Optional UI
    def build_panel(self, parent):
        """Widgets for the right-hand panel (use app/widgets.py), or None."""
        return None

    def menu_items(self):
        return []
