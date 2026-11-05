"""The opening book: PGN files in assets/openings/, one game per opening. Logic layer: no tkinter.

Each game's move tree is the theory of one opening. The first variation at a node is the
main line; later ones are alternatives with less weight. A comment of the form
"Line: <name>" (optionally followed by "; <text>") names the variation from that move on;
any other comment text explains the move.
"""

import re
from dataclasses import dataclass

import chess
import chess.pgn

from . import fileio
from .model import position_key

LINE_RE = re.compile(r"^\s*Line:\s*([^;\n]+?)\s*(?:;\s*|$)")
SIDES = {"white": chess.WHITE, "black": chess.BLACK}
DEFAULT_GROUP = "Other openings"


@dataclass(frozen=True)
class Opening:
    key: str
    name: str
    group: str
    eco: str
    side: chess.Color          # the side that makes the opening
    game: chess.pgn.Game       # the move tree


@dataclass(frozen=True)
class BookMove:
    move: chess.Move
    weight: int                # the main line has the largest weight
    line: str | None           # name of the variation this move leads into, if known
    comment: str               # explanation of the move, without the "Line:" part


def split_comment(text):
    """A book comment -> (line name or None, explanation)."""
    match = LINE_RE.match(text)
    if match is None:
        return None, text.strip()
    return match.group(1), text[match.end():].strip()


class OpeningBook:
    def __init__(self, openings, group_order, errors=()):
        self.openings = openings            # in file order
        self.errors = list(errors)          # (file name, message) of skipped games
        self._group_order = group_order     # group -> sort number

    @classmethod
    def load(cls, folder):
        """All *.pgn files in `folder`. Games with errors are skipped and listed in `errors`."""
        group_order, keys = {}, set()

        def build(game):
            opening = cls._opening(game, keys)
            keys.add(opening.key)
            order = game.headers.get("GroupOrder", "")
            group_order.setdefault(opening.group, int(order) if order.isdigit() else 999)
            return opening

        openings, errors = fileio.load_pgn_folder(folder, build)
        return cls(openings, group_order, errors)

    @staticmethod
    def _opening(game, keys):
        h = game.headers
        name = h.get("Event", "?")
        if game.errors:
            raise ValueError(f"{name}: {game.errors[0]}")
        key = h.get("Key", "")
        if not key or key in keys:
            raise ValueError(f"{name}: missing or duplicate Key \"{key}\"")
        side = h.get("Side", "").lower()
        if side not in SIDES:
            raise ValueError(f"{name}: Side must be white or black")
        if not game.variations:
            raise ValueError(f"{name}: no moves")
        return Opening(key, name, h.get("Group", DEFAULT_GROUP), h.get("ECO", ""), SIDES[side], game)

    def groups(self):
        """[(group, [Opening, …])]: groups by GroupOrder, openings in file order."""
        result = {}
        for opening in self.openings:
            result.setdefault(opening.group, []).append(opening)
        return sorted(result.items(), key=lambda item: self._group_order[item[0]])

    def opening(self, key):
        return next((o for o in self.openings if o.key == key), None)


class OpeningLine:
    """The theory of one opening, looked up by position."""

    def __init__(self, opening):
        self.opening = opening
        self._index = {}    # position key -> [BookMove], main line first
        self._build(opening.game, opening.game.board(), None)

    def _build(self, node, board, line):
        count = len(node.variations)
        moves = self._index.setdefault(position_key(board), [])
        for i, child in enumerate(node.variations):
            name, comment = split_comment(child.comment)
            child_line = name or line
            if all(bm.move != child.move for bm in moves):
                moves.append(BookMove(child.move, 2 ** (count - 1 - i), child_line, comment))
            board.push(child.move)
            self._build(child, board, child_line)
            board.pop()
        if not moves:
            del self._index[position_key(board)]

    def moves(self, board):
        """The book moves in this position, main line first. Empty = not in the book."""
        moves = self._index.get(position_key(board), [])
        return sorted(moves, key=lambda bm: -bm.weight)

    def pick(self, board, rng, vary):
        """A book move for the computer: the main line, or weighted at random if `vary`."""
        moves = self.moves(board)
        if not moves:
            return None
        if not vary:
            return moves[0].move
        return rng.choices([bm.move for bm in moves], weights=[bm.weight for bm in moves])[0]
