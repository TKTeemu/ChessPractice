"""ChessClock: remaining time per side. No tkinter and no timer of its own.

The time source `now` is a parameter so that tests can pass a fake clock. The remaining
time is always computed from `now()`, never by counting ticks.
"""

import time

import chess


class ChessClock:
    def __init__(self, seconds_white, seconds_black, now=time.monotonic, increment=0):
        self.now = now
        self.increment = increment   # seconds added to the mover's time after each move
        self._left = {chess.WHITE: float(seconds_white), chess.BLACK: float(seconds_black)}
        self.running = None      # colour whose clock runs, or None
        self._since = 0.0        # now() when the running clock was last started

    def start(self, color):
        """Start `color`'s clock (stops the other one)."""
        self._settle()
        self.running = color
        self._since = self.now()

    def switch(self):
        """After a move: the mover gets the increment, unless the flag has already fallen,
        and the other side's clock runs."""
        if self.running is not None:
            self._settle()
            if self._left[self.running] > 0:
                self._left[self.running] += self.increment
            self.start(not self.running)

    def stop(self):
        self._settle()
        self.running = None

    def _settle(self):
        if self.running is not None:
            t = self.now()
            self._left[self.running] -= t - self._since
            self._since = t

    def remaining(self, color):
        left = self._left[color]
        if color == self.running:
            left -= self.now() - self._since
        return max(0.0, left)

    def flagged(self):
        """The colour whose time has run out, or None."""
        if self.running is not None and self.remaining(self.running) <= 0:
            return self.running
        return None


def format_time(seconds):
    """Clock display: 29:41, 1:05:00, and tenths under a minute (0:42.3)."""
    if seconds < 60:
        tenths = int(seconds * 10)
        return f"0:{tenths // 10:02d}.{tenths % 10}"
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"
