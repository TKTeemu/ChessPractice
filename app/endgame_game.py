"""EndgameGame: the rules of one Endgame Practice game. Knows nothing about the user interface.

On top of ComputerGame (clock, result by time or resignation): the position's solution tree,
the computer's stored defence, and the success light. Each user move is judged once: by the
solution tree if the move is in it, otherwise by the engine's score of the position after the
move compared with the score before it. EndgameMode drives it.
"""

import random
import time

import chess

from . import strings as S
from .commands import EDIT_COMMENT, NAVIGATE, TAKE_BACK
from .computer_game import ComputerGame
from .endgames import SolutionTree
from .engines.base import Level

# The computer always plays at full strength; the same search judges the user's moves.
LEVEL = Level("endgame", "", None, 1.0, {"UCI_LimitStrength": False})

MATE = 100_000        # a mate in n is scored MATE - n (for the user) or -(MATE - n) (against)
MATE_BAND = 1_000     # scores beyond MATE - MATE_BAND are mates
WIN_LOST_CP = 150     # goal "win": a move leaving less than this for the user …
LOSS_CP = -300        # goal "draw": a move leaving less than this …
DROP_CP = 100         # … is a mistake only if the score also fell by at least this much


def user_score(analysis, user_to_move):
    """An engine Analysis -> score from the user's point of view (mates as ±(MATE - n)), or None."""
    if analysis.mate is not None:
        score = MATE - analysis.mate if analysis.mate > 0 else -MATE - analysis.mate
    elif analysis.cp is not None:
        score = analysis.cp
    else:
        return None
    return score if user_to_move else -score


def is_mistake(goal, before, after):
    """True if a user move that changed the score `before` -> `after` (user's view) gave
    away the goal. A single uncertain score does not: the score must also drop clearly."""
    if after is None:
        return False
    if after >= MATE - MATE_BAND:
        return False                                # the user mates
    if after <= -MATE + MATE_BAND:
        return before is None or before > -MATE + MATE_BAND   # walked into a mate
    dropped = before is None or before - after >= DROP_CP
    limit = WIN_LOST_CP if goal == "win" else LOSS_CP
    return after < limit and dropped


class EndgameGame(ComputerGame):
    EVENT = S.END_EVENT
    ALLOWED_DURING_GAME = frozenset({TAKE_BACK, NAVIGATE})
    ALLOWED_AFTER_GAME = frozenset({TAKE_BACK, EDIT_COMMENT, NAVIGATE})   # no TAKE_BACK after time or resign

    def __init__(self, sample, engine_name, can_judge, minutes=15, rng=None, now=time.monotonic):
        super().__init__(sample.side(), engine_name, LEVEL, minutes, now)
        self.sample = sample
        self.goal = sample.goal
        self.tree = SolutionTree(sample)
        self.can_judge = can_judge   # an engine that gives scores is available
        self.rng = rng or random.Random()
        self.judgements = {}         # ply of each user move -> "ok" | "fail" | "pending"
        self.evals = {}              # ply -> engine score of the position after that many plies, user's view
        self.best = {}               # ply -> the engine's best move in that position
        self.solved_ply = None       # a correct line of the solution was played out here
        self.take_backs = 0
        self.hints_used = 0
        self._hinted = set()         # plies at which suggestion arrows were shown
        self.last_comment = ""       # explanation of the solution move just played
        self._board_end = False      # the game ended on the board (mate, stalemate, draw)

    # --- Queries ----------------------------------------------------------

    @property
    def light(self):
        """ "pending", "success" or "fail"."""
        if "fail" in self.judgements.values():
            return "fail"
        if self.over and self.result != "*":
            return "success" if self._goal_reached() else "fail"
        return "success" if self.solved_ply is not None else "pending"

    @property
    def light_text(self):
        """The words next to the light. Once the game has ended they say how, because nothing
        else on the board changes. An engine error is left to the status line: it can be long."""
        if not self.over:
            return S.LIGHT_TEXTS[self.light]
        text = S.LIGHT_ENDED_TEXTS[self.light]
        return text if self.result == "*" else S.LIGHT_RESULT.format(light=text, result=self.end_text)

    def _goal_reached(self):
        if self.result == "1/2-1/2":
            return self.goal == "draw"
        return self.result == ("1-0" if self.user_color == chess.WHITE else "0-1")

    def goal_text(self):
        return S.END_GOALS[self.goal].format(color=S.COLOR_NAMES[self.user_color])

    def turn_text(self, board, at_end):
        """The line above the board for the position shown; no one is to move in the final one."""
        you = S.COLOR_NAMES[self.user_color]
        if self.over and at_end:
            return S.END_YOU_PLAY.format(color=you)
        return S.END_TURN.format(color=you, turn=S.COLOR_NAMES[board.turn])

    def allows(self, command):
        if command == TAKE_BACK and self.over and not self._board_end:
            return False
        return super().allows(command)

    def hints(self, board):
        """Arrows for the user's turn: [(from_sq, to_sq, "main" | "alt")]. The solution's moves
        if the position is in it, else the engine's best move if it is known."""
        if self.over or board.turn != self.user_color:
            return []
        moves = [sm.move for sm in self.tree.moves(board) if not sm.wrong]
        if not moves:
            best = self.best.get(len(board.move_stack))
            moves = [best] if best is not None else []
        return [(m.from_square, m.to_square, "main" if i == 0 else "alt") for i, m in enumerate(moves)]

    def note_hints(self, board, hints):
        """The arrows `hints` are being shown: count the position once."""
        ply = len(board.move_stack)
        if hints and ply not in self._hinted:
            self._hinted.add(ply)
            self.hints_used += 1

    def tree_reply(self, board):
        """The computer's stored defence in this position, or None: ask the engine."""
        return None if self.over else self.tree.pick(board, self.rng)

    def needs_eval(self, ply):
        """An engine score of the position after `ply` plies is still wanted (to judge a move)."""
        return self.can_judge and ply >= 0 and ply not in self.evals

    def needs_judging(self, board):
        """The user's move that led to `board` waits for the engine's verdict."""
        return self.can_judge and self.judgements.get(len(board.move_stack)) == "pending"

    # --- Events -----------------------------------------------------------

    def move_played(self, board):
        """After each move, with the board after it. Returns the mover's remaining seconds."""
        before = board.copy()
        move = before.pop()
        ply = len(board.move_stack)
        if self.best.get(ply - 1) == move and ply - 1 in self.evals:
            self.evals[ply] = self.evals[ply - 1]     # the engine's own move keeps its score
        solution = self.tree.move(before, move)
        self.last_comment = solution.comment if solution else ""
        if before.turn == self.user_color:
            self.notice = None
            if solution is not None:
                self.judgements[ply] = "fail" if solution.wrong else "ok"
                if solution.wrong:
                    self.notice = f"{S.END_WRONG_TRY}: {solution.comment}" if solution.comment else S.END_WRONG_TRY
            elif self.tree.contains(board):          # a move order that transposes into the solution
                self.judgements[ply] = "ok"
            else:
                self.judgements[ply] = "pending"
                if not self.can_judge:
                    self.notice = S.END_NO_JUDGE
        if self.solved_ply is None and self.tree.at_end(board):
            self.solved_ply = ply
        left = super().move_played(board)
        self._board_end = self.over
        return left

    def analysed(self, ply, analysis):
        """The engine's Analysis of the position after `ply` plies. Judges the user's move
        that led there, if it is still waiting."""
        self.evals[ply] = user_score(analysis, ply % 2 == 0)   # the user moves first
        self.best[ply] = analysis.move
        if analysis.ponder is not None:
            self.best.setdefault(ply + 1, analysis.ponder)   # the expected reply: a free suggestion
        if self.judgements.get(ply) == "pending":
            mistake = is_mistake(self.goal, self.evals.get(ply - 1), self.evals[ply])
            self.judgements[ply] = "fail" if mistake else "ok"
            if mistake:
                self.notice = S.END_MISTAKE

    def took_back(self, board):
        """After moves were taken back: forget what was learnt about the removed moves. The
        clock is not wound back; it runs for the user."""
        ply = len(board.move_stack)
        for table in (self.judgements, self.evals, self.best):
            for key in [k for k in table if k > ply]:
                del table[key]
        if self.solved_ply is not None and self.solved_ply > ply:
            self.solved_ply = None
        super().took_back(board)
        self._board_end = False
        self.last_comment = ""
        self.take_backs += 1
        if self.started:
            self.clock.start(self.user_color)

    # --- Headers ----------------------------------------------------------

    def write_headers(self, headers):
        super().write_headers(headers)
        sample = self.sample
        headers["SetUp"] = "1"
        headers["FEN"] = sample.fen
        headers["EndgameKey"] = sample.key
        headers["Difficulty"] = str(sample.difficulty)
        for name, value in (("Composer", sample.composer), ("Source", sample.source), ("Year", sample.year)):
            if value:
                headers[name] = value

    def result_headers(self):
        return {**super().result_headers(), "HintsUsed": str(self.hints_used),
                "TakeBacks": str(self.take_backs)}
