"""MiddlegameMode: the user plays a known middlegame puzzle against the computer, to the end.

Everything works as in EndgameMode; only the puzzles, the settings and the rule that a solved
puzzle stays solved (MiddlegameGame) differ.
"""

from .. import strings as S
from ..dialogs import choose_endgame
from ..middlegame_game import MiddlegameGame
from .endgames import EndgameMode


class MiddlegameMode(EndgameMode):
    key = "mid_practice"
    label = S.MODE_MIDDLEGAMES
    PREFIX = "mid"
    GAME = MiddlegameGame
    TITLE = S.MID_TITLE
    NO_POSITIONS = S.MID_NO_POSITIONS
    CLASSIC = S.MID_CLASSIC
    SETTINGS = {
        "mid_difficulty": 1,
        "mid_minutes": 30,
        "mid_suggest": False,
        "mid_progress": {},
    }

    def _collection(self):
        return self.ctx.assets.middlegames()

    def _deck(self):
        return self.ctx.assets.middlegame_deck(self.ctx.settings["mid_progress"])

    def _folder(self):
        return self.ctx.assets.middlegame_folder

    def _dialog(self, levels, played, solved, notes):
        return choose_endgame(self.ctx.root, levels, played, solved, notes, self.ctx.settings,
                              title=self.TITLE, prefix=self.PREFIX)
