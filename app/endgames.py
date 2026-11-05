"""Endgame positions for Endgame Practice: PGN files in assets/endgames/, one game per position.
Logic layer: no tkinter.

Each game starts from its FEN (SetUp "1"). The side to move is the user's side, and the Goal
header says what the user must achieve ("win" or "draw"). The move tree is the solution: the
main line is the solution, a user-side variation without a NAG is an equally good
alternative, and a variation whose first move has a ? or ?? NAG is a known wrong try.
Variations on the computer's side are alternative defences.
"""

import random
from dataclasses import dataclass

import chess
import chess.pgn

from . import fileio
from .model import game_outcome, position_key

GOALS = ("win", "draw")
DIFFICULTIES = range(1, 6)
WRONG_NAGS = frozenset({chess.pgn.NAG_MISTAKE, chess.pgn.NAG_BLUNDER})


@dataclass(frozen=True)
class EndgameSample:
    key: str
    name: str
    difficulty: int
    goal: str                  # "win" | "draw", for the side to move
    fen: str
    composer: str
    source: str
    year: str
    game: chess.pgn.Game       # the solution tree

    def side(self):
        """The side to move, which the user plays."""
        return chess.Board(self.fen).turn

    def credit_text(self):
        """ "Composer · Source · Year", leaving out what is not known; "" if nothing is."""
        return " · ".join(part for part in (self.composer, self.source, self.year) if part)


@dataclass(frozen=True)
class SolutionMove:
    move: chess.Move
    wrong: bool                # a known wrong try (NAG ? or ??)
    comment: str               # explanation, shown when the move is played
    weight: int                # the main line has the largest weight


class EndgameCollection:
    def __init__(self, samples, level_names, errors=()):
        self.all = samples                   # in file order
        self.errors = list(errors)           # (file name, message) of skipped games
        self._level_names = level_names      # difficulty -> name

    @classmethod
    def load(cls, folder):
        """All *.pgn files in `folder`. Games with errors are skipped and listed in `errors`."""
        names, keys = {}, set()

        def build(game):
            sample = cls._sample(game, keys)
            keys.add(sample.key)
            name = game.headers.get("DifficultyName", "")
            if name:
                names.setdefault(sample.difficulty, name)
            return sample

        samples, errors = fileio.load_pgn_folder(folder, build)
        return cls(samples, names, errors)

    @staticmethod
    def _sample(game, keys):
        h = game.headers
        name = h.get("Event", "?")
        if game.errors:
            raise ValueError(f"{name}: {game.errors[0]}")
        key = h.get("Key", "")
        if not key or key in keys:
            raise ValueError(f"{name}: missing or duplicate Key \"{key}\"")
        difficulty = h.get("Difficulty", "")
        if not difficulty.isdigit() or int(difficulty) not in DIFFICULTIES:
            raise ValueError(f"{name}: Difficulty must be 1–5")
        goal = h.get("Goal", "").lower()
        if goal not in GOALS:
            raise ValueError(f"{name}: Goal must be win or draw")
        fen = h.get("FEN", "")
        if not fen or h.get("SetUp") != "1":
            raise ValueError(f"{name}: SetUp \"1\" and FEN are required")
        try:
            board = chess.Board(fen)
        except ValueError as e:
            raise ValueError(f"{name}: {e}") from None
        if not board.is_valid() or game_outcome(board) is not None:
            raise ValueError(f"{name}: the FEN is not a playable position")
        return EndgameSample(key, name, int(difficulty), goal, board.fen(), h.get("Composer", ""),
                             h.get("Source", ""), h.get("Year", ""), game)

    def levels(self):
        """[(difficulty, name, number of positions)] of the levels that have positions."""
        counts = {}
        for sample in self.all:
            counts[sample.difficulty] = counts.get(sample.difficulty, 0) + 1
        return [(d, self._level_names.get(d, str(d)), counts[d]) for d in sorted(counts)]

    def samples(self, difficulty):
        return [s for s in self.all if s.difficulty == difficulty]

    def sample(self, key):
        return next((s for s in self.all if s.key == key), None)


class SolutionTree:
    """The solution of one position, looked up by position (so transpositions are found)."""

    def __init__(self, sample):
        self.sample = sample
        self._index = {}     # position key -> [SolutionMove], main line first
        self._ends = set()   # position keys where a correct line ends
        self._build(sample.game, sample.game.board(), wrong_line=False)

    def _build(self, node, board, wrong_line):
        count = len(node.variations)
        if count == 0:
            if node.parent is not None and not wrong_line:
                self._ends.add(position_key(board))
            return
        moves = self._index.setdefault(position_key(board), [])
        for i, child in enumerate(node.variations):
            wrong = bool(WRONG_NAGS & child.nags)
            if all(sm.move != child.move for sm in moves):
                moves.append(SolutionMove(child.move, wrong, child.comment.strip(), 2 ** (count - 1 - i)))
            board.push(child.move)
            self._build(child, board, wrong_line or wrong)
            board.pop()

    def moves(self, board):
        """The solution's moves in this position, main line first. Empty = not in the solution."""
        return sorted(self._index.get(position_key(board), []), key=lambda sm: -sm.weight)

    def move(self, board, move):
        return next((sm for sm in self.moves(board) if sm.move == move), None)

    def contains(self, board):
        key = position_key(board)
        return key in self._index or key in self._ends

    def at_end(self, board):
        """True if a correct line of the solution ends in this position (it has been played out)."""
        key = position_key(board)
        return key in self._ends and key not in self._index

    def pick(self, board, rng):
        """A move for the side to move that is not a wrong try: the main line most often."""
        moves = [sm for sm in self.moves(board) if not sm.wrong]
        if not moves:
            return None
        return rng.choices([sm.move for sm in moves], weights=[sm.weight for sm in moves])[0]


class EndgameDeck:
    """Draws positions of a level without repeating one before the whole level has been played
    ("shuffle bag"). `played`: keys of the positions played earlier (they come last)."""

    def __init__(self, collection, rng=None, played=()):
        self.collection = collection
        self.rng = rng or random.Random()
        self._bags = {}       # difficulty -> keys still to draw, next one last
        self._played = {}     # difficulty -> keys drawn so far
        self._last = {}       # difficulty -> the key drawn last
        for key in played:
            sample = collection.sample(key)
            if sample is not None:   # a position may have been removed since
                self._played.setdefault(sample.difficulty, set()).add(key)

    def draw(self, difficulty):
        bag = self._bags.get(difficulty)
        if not bag:
            first_bag = difficulty not in self._bags
            bag = [s.key for s in self.collection.samples(difficulty)]
            if not bag:
                raise ValueError(f"no positions on level {difficulty}")
            if first_bag:   # go on where the previous run stopped
                played = self._played.get(difficulty, ())
                bag = [key for key in bag if key not in played] or bag
            self.rng.shuffle(bag)
            last = self._last.get(difficulty)
            if len(bag) > 1 and bag[-1] == last:   # the one just played does not come first again
                bag[0], bag[-1] = bag[-1], bag[0]
            self._bags[difficulty] = bag
        key = bag.pop()
        self._last[difficulty] = key
        self._played.setdefault(difficulty, set()).add(key)
        return self.collection.sample(key)

    def played(self, difficulty):
        """How many different positions of the level have been drawn."""
        return len(self._played.get(difficulty, ()))
