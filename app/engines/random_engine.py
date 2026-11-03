"""RandomEngine: plays a random legal move. Needs no files; used in tests and as a fallback."""

import random

from .. import strings as S
from .base import Engine, EngineError, Level

LEVELS = [Level("random", S.LEVEL_RANDOM, None, 0.5)]


class RandomEngine(Engine):
    key = "random"
    name = S.ENGINE_RANDOM

    def __init__(self, settings=None, seed=None):
        super().__init__(settings)
        self.random = random.Random(seed)

    def levels(self):
        return LEVELS

    def best_move(self, board, level, stop):
        moves = list(board.legal_moves)
        if not moves:
            raise EngineError("no legal moves")
        stop.wait(level.think_time)   # a short pause so the reply does not appear instantly
        return self.random.choice(moves)
