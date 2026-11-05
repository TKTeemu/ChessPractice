"""The Mode interface. A mode decides what the user may do and what happens after a move.

MainWindow asks the active mode questions instead of checking which mode is active.
The defaults behave like the free board: everything allowed, nothing extra.

Switching modes (MainWindow.set_mode) runs in this order:
    new.choose() -> old.confirm_leave() -> (save prompt) -> old.leave() -> (save) -> old.deactivate()
    -> new.build_panel() -> new.start(config)
so nothing of the new mode happens before the old one has been closed.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class ModeContext:
    """What a mode may use. Passed in by MainWindow; modes do not import MainWindow."""
    root: object                  # tk.Tk
    model: object                 # GameModel: read freely; change only through its methods
    settings: object              # Settings
    app_dir: Path                 # the program folder (engines/)
    assets: object                # Assets: the opening book and the endgame positions
    play_move: Callable           # play_move(move, from_end=False)
    new_game: Callable            # new_game(board=None, headers=None, intro=""): replace the game
    update_status: Callable       # update_status(): labels, buttons and arrows, after a mode's state changed
    set_flipped: Callable         # set_flipped(bool)
    set_mode: Callable            # set_mode(key, config=None, discard=False) -> bool
    set_clocks: Callable          # set_clocks({color: (text, active, low)} or None)
    play_sound: Callable          # play_sound(kind)
    take_back: Callable           # take_back(color) -> bool: remove moves back to color's last turn, then update the views


@dataclass
class MenuItem:
    label: str
    command: Callable
    enabled: Callable = lambda: True


class Mode:
    key = ""        # unique
    label = ""      # menu text, from strings.py
    show_details = True    # the Comment & FEN section is open until the user closes it
    replaces_game = False  # start() replaces the game: MainWindow asks to save the old one first
    takes_back = False     # the Take Back button is shown; it calls take_back()
    SETTINGS = {}   # the mode's own settings and their defaults, keys prefixed with the mode key

    def __init__(self, ctx):
        self.ctx = ctx
        self._after_ids = {}

    # Life cycle
    def choose(self):
        """Show the mode's dialog, if any, and return what the user chose (a dict), or None
        to stay in the previous mode. No side effects: the previous mode is still active."""
        return {}

    def start(self, config):
        """Begin, with what choose() returned. The previous mode has been closed and this
        mode's panel exists."""

    def confirm_leave(self):
        """Before the mode is left, a new game starts or the program exits. Only asks; False = cancel."""
        return True

    def leaving_changes_game(self):
        """leave() will change the game (e.g. a resignation writes the result), so it must be
        offered for saving even if it has no unsaved changes now."""
        return False

    def leave(self):
        """The user confirmed leaving (and the save prompt was answered), e.g. resign the game."""

    def deactivate(self):
        """Release engines, timers and threads."""
        self._cancel_timers()

    # Questions MainWindow asks. They have no side effects: they may be asked at any time.
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

    def can_take_back(self):
        """A mode with takes_back: there is a move of the user's to take back now."""
        return False

    def take_back(self):
        """A mode with takes_back: the Take Back button, e.g. remove the user's last move and the reply."""

    # Notifications
    def after_move(self):
        """After every successful play_move, before the views are updated."""

    def position_changed(self):
        """The current position or the game tree changed, however that happened."""

    def hints_shown(self, hints):
        """The arrows hint_arrows() returned are now on the board."""

    # Optional UI
    def build_panel(self, parent):
        """Widgets for the right-hand panel (use app/widgets.py), or None."""
        return None

    def menu_items(self):
        return []

    # Timers
    def _schedule(self, name, ms, callback):
        """Run callback after ms milliseconds, replacing the timer of this name if one is waiting."""
        old = self._after_ids.get(name)
        if old is not None:
            self.ctx.root.after_cancel(old)
        self._after_ids[name] = self.ctx.root.after(ms, callback)

    def _cancel_timers(self):
        for after_id in self._after_ids.values():
            self.ctx.root.after_cancel(after_id)
        self._after_ids.clear()
