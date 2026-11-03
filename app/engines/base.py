"""The Engine interface and the Level record. Logic layer: no tkinter."""

from dataclasses import dataclass, field


class EngineError(Exception):
    """The engine could not start or could not produce a legal move."""


@dataclass(frozen=True)
class Level:
    key: str                 # stored in settings.json, e.g. "1500"
    label: str               # shown in the dialog, e.g. "1500"
    elo: int | None          # for the PGN WhiteElo/BlackElo header; None if unknown
    think_time: float        # seconds per move
    options: dict = field(default_factory=dict)   # engine-specific, e.g. {"UCI_Elo": 1500}


class Engine:
    """Something that chooses moves. Instances are used from the worker thread only,
    except for levels() and close()."""

    key = ""
    name = ""

    def __init__(self, settings, app_dir=None):
        self.settings = settings
        self.app_dir = app_dir   # the program folder (engines/ is under it)

    @classmethod
    def available(cls, settings, app_dir):
        """True if the engine can be started. Must be fast and start nothing."""
        return True

    @classmethod
    def unavailable_reason(cls, settings, app_dir):
        """Text for the dialog when available() is False, or None."""
        return None

    def levels(self):
        raise NotImplementedError

    def level(self, key):
        """The level with this key, or the first level if the key is unknown."""
        levels = self.levels()
        return next((lv for lv in levels if lv.key == key), levels[0])

    def start(self):
        pass

    def new_game(self):
        pass

    def best_move(self, board, level, stop):
        """Return a legal chess.Move for `board`. Return soon after `stop` (threading.Event) is set."""
        raise NotImplementedError

    def close(self):
        """End any process. Safe to call twice and from any thread."""
