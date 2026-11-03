"""TimedGameMode: the shared base of modes in which the computer plays and a chess clock runs.

On top of EngineGameMode: the clock tick and flag fall, the clocks next to the player names,
the [%clk] comments, Resign (also when the mode is left during a game) and the buttons that
depend on whether the game runs. `self.game` is a ComputerGame (app/computer_game.py).
A subclass implements choose() and start(config), which creates the game, calls
start_engine() and start_clock(), and then _next_turn().
"""

from tkinter import messagebox

import chess

from .. import strings as S
from ..clock import format_time
from ..model import END
from .engine_mode import EngineGameMode

TICK_MS = 100     # how often the clocks are redrawn and checked for a flag fall
LOW_TIME = 60     # seconds; below this the clock is shown in red with tenths


class TimedGameMode(EngineGameMode):

    def __init__(self, ctx):
        super().__init__(ctx)
        self._buttons = {}

    # --- Life cycle -------------------------------------------------------

    def start_clock(self):
        self._schedule("tick", TICK_MS, self._tick)

    def deactivate(self):
        super().deactivate()
        self.ctx.set_clocks(None)

    def confirm_leave(self):
        if not self._running():
            return True
        return messagebox.askyesno(S.VS_RESIGN_TITLE, S.VS_RESIGN_PROMPT, parent=self.ctx.root)

    def leave(self):
        self.resign()

    # --- Moves ------------------------------------------------------------

    def after_move(self):
        model = self.ctx.model
        left = self.game.move_played(model.board)
        model.set_clock(model.node, left)
        if self.game.over:
            self._game_over()
        else:
            self._next_turn()
        self._update_clocks()

    def _next_turn(self):
        if self.game.is_computer_turn(self._tip()):
            self.computer_turn()
        self._update_buttons()

    # --- Clock ------------------------------------------------------------

    def _tick(self):
        self._schedule("tick", TICK_MS, self._tick)
        if self._running() and self.game.clock.flagged() is not None and self.game.check_time(self._tip()):
            self._game_over()
            self.ctx.refresh()
            self.ctx.play_sound(END)
        self._update_clocks()

    def _update_clocks(self):
        clock = self.game.clock
        values = {}
        for color in chess.COLORS:
            left = clock.remaining(color)
            values[color] = (format_time(left), clock.running == color, left < LOW_TIME)
        self.ctx.set_clocks(values)

    # --- Ending -----------------------------------------------------------

    def resign(self):
        if not self._running():
            return
        self.game.resign()
        self._game_over()
        self.ctx.refresh()
        self.ctx.play_sound(END)

    def _game_over(self):
        super()._game_over()
        self._update_buttons()
        self._update_clocks()

    # --- UI ---------------------------------------------------------------

    def _button_states(self):
        """{button name: enabled} for the buttons in self._buttons."""
        running = self._running()
        return {"resign": running, "open": self.game is not None and not running}

    def _update_buttons(self):
        states = self._button_states()
        for name, button in self._buttons.items():
            if button.winfo_exists():
                button.configure(state="normal" if states.get(name, True) else "disabled")
