"""Chess engines. The order of ENGINES is the order in the Play vs Computer dialog."""

from .base import Analysis, Engine, EngineError, Level, format_score
from .random_engine import RandomEngine
from .stockfish import StockfishEngine

ENGINES = [StockfishEngine, RandomEngine]


def engine_class(key):
    return next((cls for cls in ENGINES if cls.key == key), None)
