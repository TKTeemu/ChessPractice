"""StockfishEngine: Stockfish over UCI, with a table of strength levels."""

from pathlib import Path

from .. import strings as S
from .base import Engine, EngineError, Level
from .uci import UciClient


def _elo(elo):
    return Level(str(elo), str(elo), elo, 1.0, {"UCI_LimitStrength": True, "UCI_Elo": elo})


# The levels shown in the dialog. Keep existing keys unchanged: settings.json stores them.
LEVELS = [_elo(elo) for elo in (1320, 1500, 1650, 1800, 2000, 2200, 2400, 2600, 2800)] + [
    Level("max", S.LEVEL_MAXIMUM, None, 2.0, {"UCI_LimitStrength": False}),
]

BASE_OPTIONS = {"Threads": 1, "Hash": 64}


class StockfishEngine(Engine):
    key = "stockfish"
    name = S.ENGINE_STOCKFISH

    def __init__(self, settings):
        super().__init__(settings)
        self.client = None
        self._options = {}   # options last sent, so they are only sent when they change

    # --- Finding the exe --------------------------------------------------

    @classmethod
    def default_dir(cls, settings):
        return cls.app_dir(settings) / "engines" / "stockfish"

    @classmethod
    def find_exe(cls, settings):
        """settings["engine_path"] if set, else stockfish.exe (or stockfish*.exe) in engines/stockfish/."""
        configured = settings["engine_path"]
        if configured:
            path = Path(configured)
            return path if path.is_file() else None
        folder = cls.default_dir(settings)
        exact = folder / "stockfish.exe"
        if exact.is_file():
            return exact
        found = sorted(folder.glob("stockfish*.exe")) if folder.is_dir() else []
        return found[0] if found else None

    @classmethod
    def available(cls, settings):
        return cls.find_exe(settings) is not None

    @classmethod
    def unavailable_reason(cls, settings):
        return S.STOCKFISH_MISSING.format(folder=cls.default_dir(settings))

    # --- Engine -----------------------------------------------------------

    def levels(self):
        return LEVELS

    def start(self):
        exe = self.find_exe(self.settings)
        if exe is None:
            raise EngineError(self.unavailable_reason(self.settings))
        self.client = UciClient([exe], cwd=exe.parent)
        self.client.start()
        for name, value in BASE_OPTIONS.items():
            self._set(name, value)
        self.client.isready()

    def new_game(self):
        self.client.new_game()

    def _set(self, name, value):
        info = self.client.options.get(name)
        if info is None or self._options.get(name) == value:
            return
        if isinstance(value, int) and not isinstance(value, bool):
            # The engine reports its own limits (e.g. UCI_Elo min/max); stay inside them
            value = max(info.get("min", value), min(info.get("max", value), value))
        self.client.setoption(name, value)
        self._options[name] = value

    def best_move(self, board, level, stop):
        if self.client is None:
            raise EngineError("engine not started")
        for name, value in level.options.items():
            self._set(name, value)
        return self.client.go(board, level.think_time, stop)

    def close(self):
        if self.client is not None:
            self.client.close()
