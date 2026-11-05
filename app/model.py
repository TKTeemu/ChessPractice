"""Game state and rules. Knows nothing about the user interface."""

import datetime
import re

import chess
import chess.pgn

from . import strings as S

# Sound/event kinds, in priority order (first match wins)
END, CHECK, PROMOTE, CASTLE, CAPTURE, MOVE = "end", "check", "promote", "castle", "capture", "move"


def default_headers(game):
    game.headers["Event"] = S.DEFAULT_EVENT
    game.headers["Site"] = S.UNKNOWN
    game.headers["Date"] = datetime.date.today().strftime("%Y.%m.%d")
    game.headers["Round"] = S.UNKNOWN
    game.headers["White"] = S.DEFAULT_WHITE
    game.headers["Black"] = S.DEFAULT_BLACK
    game.headers["Result"] = "*"


def game_outcome(board):
    """How the game ends at `board`, or None if it goes on.

    Threefold repetition and the fifty-move rule end the game only once they have happened.
    board.outcome(claim_draw=True) would also end it when the next move could bring them
    about, which takes the choice away from the player to move.
    """
    outcome = board.outcome()
    if outcome is not None:
        return outcome
    if board.is_fifty_moves():
        return chess.Outcome(chess.Termination.FIFTY_MOVES, None)
    if board.is_repetition(3):
        return chess.Outcome(chess.Termination.THREEFOLD_REPETITION, None)
    return None


def event_for(node):
    """Classify the move that led to `node` (for sounds)."""
    before = node.parent.board()
    move = node.move
    after = before.copy(stack=True)
    after.push(move)
    if game_outcome(after) is not None:
        return END
    if after.is_check():
        return CHECK
    if move.promotion:
        return PROMOTE
    if before.is_castling(move):
        return CASTLE
    if before.is_capture(move):
        return CAPTURE
    return MOVE


# PGN comment commands such as [%clk 0:29:41]: kept in the file, hidden from the user
COMMAND_RE = re.compile(r"\[%[^\]]*\]")
COMMAND_WITH_SPACE_RE = re.compile(r"[ \t]*\[%[^\]]*\][ \t]*")


def visible_comment(text):
    """The comment without [%…] commands."""
    return COMMAND_WITH_SPACE_RE.sub(" ", text).strip()


PIECE_VALUES = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}


def material_balance(board, color):
    """Material points of `color` minus the opponent's (pawn 1, knight and bishop 3, rook 5, queen 9)."""
    total = 0
    for piece in board.piece_map().values():
        value = PIECE_VALUES.get(piece.piece_type, 0)
        total += value if piece.color == color else -value
    return total


def outcome_text(outcome):
    """Status line text for a finished position (a chess.Outcome)."""
    t = chess.Termination
    return {
        t.CHECKMATE: S.STATUS_CHECKMATE_WHITE if outcome.winner == chess.WHITE else S.STATUS_CHECKMATE_BLACK,
        t.STALEMATE: S.STATUS_STALEMATE,
        t.INSUFFICIENT_MATERIAL: S.STATUS_DRAW_INSUFFICIENT,
        t.THREEFOLD_REPETITION: S.STATUS_DRAW_REPETITION,
        t.FIFTY_MOVES: S.STATUS_DRAW_FIFTY,
        t.FIVEFOLD_REPETITION: S.STATUS_DRAW_FIVEFOLD,
        t.SEVENTYFIVE_MOVES: S.STATUS_DRAW_SEVENTYFIVE,
    }.get(outcome.termination, outcome.result())


def line_start(node):
    """First node of the variation that contains `node` (root if in the main line)."""
    while node.parent is not None and node.parent.variations[0] is node:
        node = node.parent
    return node


def position_key(board):
    """Positions are compared without move counters, so transpositions are found."""
    return board.epd()


def is_descendant(node, ancestor):
    while node is not None:
        if node is ancestor:
            return True
        node = node.parent
    return False


class GameModel:
    """The game tree (a python-chess Game) and the node currently shown.

    `node` is the current position in the tree and `board` is its cached chess.Board;
    both change only through the methods below. `modified` tells whether the game
    has unsaved changes: every method that changes what would be saved sets it, so the game,
    its nodes and its headers are not written to from outside this class.
    """

    def __init__(self):
        self.new_game()

    # --- Game setup -------------------------------------------------------

    def new_game(self, board=None, headers=None, intro=""):
        """A new game, not yet modified. headers: PGN headers on top of the defaults.
        intro: the comment before the first move."""
        game = chess.pgn.Game()
        default_headers(game)
        if board is not None:
            game.setup(board)
        if headers:
            game.headers.update(headers)
        game.comment = intro
        self.load_game(game)

    def load_game(self, game):
        self.game = game
        self.modified = False
        self._deleted = []   # (parent, node, index among its siblings, current node), last one last
        self._set_node(game)

    def mark_saved(self):
        self.modified = False

    def _set_node(self, node):
        self.node = node
        self.board = node.board()

    # --- Queries ----------------------------------------------------------

    @property
    def headers(self):
        return self.game.headers

    def fen(self):
        return self.board.fen()

    def legal_targets(self, square):
        return {m.to_square for m in self.board.legal_moves if m.from_square == square}

    def needs_promotion(self, from_sq, to_sq):
        return any(m.promotion for m in self.board.legal_moves
                   if m.from_square == from_sq and m.to_square == to_sq)

    def status(self):
        board = self.board
        outcome = game_outcome(board)
        if outcome is None:
            text = S.STATUS_WHITE_TO_MOVE if board.turn == chess.WHITE else S.STATUS_BLACK_TO_MOVE
            if board.is_check():
                text += " · " + S.STATUS_CHECK
            return text
        return outcome_text(outcome)

    def at_end(self):
        """True if the current node is the last one of its line."""
        return not self.node.variations

    # --- Making moves -----------------------------------------------------

    def play(self, move):
        """Play a chess.Move from the current node. Returns the event kind, or None if illegal.

        If the move already exists from this node, we just step into it;
        otherwise a new variation is created (the main line if there is none yet).
        """
        if move not in self.board.legal_moves:
            return None
        if self.node.has_variation(move):
            child = self.node.variation(move)
        else:
            child = self.node.add_variation(move)
            self.modified = True
            self._deleted.clear()   # a restored line could now clash with the new move
        self._set_node(child)
        return event_for(child)

    # --- Navigation -------------------------------------------------------

    def goto(self, node):
        if node is not self.node:
            self._set_node(node)
            return True
        return False

    def back(self):
        return self.node.parent is not None and self.goto(self.node.parent)

    def forward(self):
        return bool(self.node.variations) and self.goto(self.node.variations[0])

    def go_start(self):
        return self.goto(self.game)

    def go_end(self):
        return self.goto(self.node.end())

    def switch_variation(self, delta):
        """Move to the previous/next sibling variation of the current move."""
        parent = self.node.parent
        if parent is None or len(parent.variations) < 2:
            return False
        siblings = parent.variations
        index = siblings.index(self.node) + delta
        if 0 <= index < len(siblings):
            return self.goto(siblings[index])
        return False

    # --- Editing the tree -------------------------------------------------

    def _remove(self, node):
        """Delete `node` and everything after it, in a way restore_deleted() can undo."""
        parent = node.parent
        self._deleted.append((parent, node, parent.variations.index(node), self.node))
        parent.remove_variation(node)
        self.modified = True

    def can_restore(self):
        return bool(self._deleted)

    def restore_deleted(self):
        """Undo the latest deletion: the moves come back where they were, and so does the current
        position. Possible until a new move is played or another game is loaded."""
        if not self._deleted:
            return False
        parent, node, index, current = self._deleted.pop()
        parent.variations.insert(min(index, len(parent.variations)), node)
        self.modified = True
        self._set_node(current)
        return True

    def delete_last(self):
        """Ctrl+Z: remove the current move if it is the last one in its line."""
        node = self.node
        if node.parent is None or node.variations:
            return False
        self._remove(node)
        self._set_node(node.parent)
        return True

    def take_back(self, color):
        """Remove moves from the end of the current line back to the position before `color`'s
        last move (usually the computer's reply and the user's move). False if `color` has no move there."""
        child = self.node.end()
        node = child.parent
        while node is not None and node.turn() != color:
            child, node = node, node.parent
        if node is None:
            return False
        node.remove_variation(child)
        self.modified = True
        self._deleted.clear()
        self._set_node(node)
        return True

    def promote_to_main(self, node):
        changed = False
        while node.parent is not None:
            if node.parent.variations[0] is not node:
                node.parent.promote_to_main(node)
                changed = True
            node = node.parent
        if changed:
            self.modified = True
            self._set_node(self.node)  # refresh cached board (unchanged position)
        return changed

    def delete_variation(self, node):
        start = line_start(node)
        if start.parent is None:
            return False  # main line: nothing to delete as a variation
        return self.delete_from_here(start)

    def delete_from_here(self, node):
        parent = node.parent
        if parent is None:
            return False
        moved_out = is_descendant(self.node, node)
        self._remove(node)
        if moved_out:
            self._set_node(parent)
        return True

    # --- Comments ---------------------------------------------------------

    def set_comment(self, node, text):
        """Set the visible part of the comment; [%…] commands are kept. Returns True if it changed."""
        text = text.strip()
        if text == visible_comment(node.comment):
            return False
        node.comment = " ".join(COMMAND_RE.findall(node.comment) + ([text] if text else []))
        self.modified = True
        return True

    def set_clock(self, node, seconds):
        """Store the remaining clock time after this move as [%clk h:mm:ss]."""
        node.set_clock(round(seconds))
        self.modified = True

    # --- Headers ----------------------------------------------------------

    def set_headers(self, values):
        """Change PGN headers (e.g. the result). The game counts as modified if any value changed."""
        for name, value in values.items():
            if self.game.headers.get(name) != value:
                self.game.headers[name] = value
                self.modified = True

    def clear_result(self):
        """The game goes on after all (moves were taken back): no result any more."""
        self.set_headers({"Result": "*"})
        if self.game.headers.pop("Termination", None) is not None:
            self.modified = True
