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


@dataclass(frozen=True)
class Analysis:
    """The result of Engine.analyse: the best move and the score, from the point of view of
    the side to move in the analysed position. At most one of cp and mate is set."""
    move: object             # chess.Move
    cp: int | None = None    # centipawns
    mate: int | None = None  # mate in n moves; negative: the side to move is mated
    ponder: object = None    # the expected reply (chess.Move), if the engine gave one
    pv: tuple = ()           # the expected line (chess.Moves), starting with `move`


def format_score(analysis, white_to_move):
    """The score from White's point of view: "+0.35", "-1.20", "#3" (White mates), "#-3"; "" if unknown."""
    sign = 1 if white_to_move else -1
    if analysis.mate is not None:
        return f"#{sign * analysis.mate}"
    if analysis.cp is not None:
        return f"{sign * analysis.cp / 100:+.2f}"
    return ""


class Engine:
    """Something that chooses moves. Instances are used from the worker thread only,
    except for levels() and close()."""

    key = ""
    name = ""
    can_analyse = False   # analyse() gives a score with the move

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

    def analyse(self, board, level, stop):
        """Like best_move, but returns an Analysis with the score. Only if can_analyse."""
        raise NotImplementedError

    def close(self):
        """End any process. Safe to call twice and from any thread."""
