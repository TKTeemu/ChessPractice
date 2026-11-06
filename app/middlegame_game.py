"""MiddlegameGame: the rules of one Middlegame Practice game. Knows nothing about the user interface.

The same as EndgameGame, except that a puzzle stays solved: the rest of the game can be long
and is played against full strength, so once a correct line has been played out the light stays
green whatever happens later, and later moves are no longer judged.
"""

from . import strings as S
from .endgame_game import EndgameGame


class MiddlegameGame(EndgameGame):
    EVENT = S.MID_EVENT
    KEY_HEADER = "MiddlegameKey"

    @property
    def _solved_cleanly(self):
        """A correct line was played out, and no move on the way to it was a miss."""
        return self.solved_ply is not None and not any(
            verdict == "fail" for ply, verdict in self.judgements.items() if ply <= self.solved_ply)

    @property
    def light(self):
        return "success" if self._solved_cleanly else super().light

    def needs_judging(self, board):
        return not self._solved_cleanly and super().needs_judging(board)

    def move_played(self, board):
        left = super().move_played(board)
        if self._solved_cleanly:
            self.notice = None
        return left

    def analysed(self, ply, analysis):
        super().analysed(ply, analysis)
        if self._solved_cleanly:
            self.notice = None
