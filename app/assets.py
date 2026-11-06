"""The program's data files, loaded when first needed and then kept while the program runs.
Logic layer: no tkinter.

MainWindow makes one Assets and gives it to the modes through ModeContext. A mode object lives
only until the next mode switch; what is here outlives it, so that the book is not loaded again
and the positions drawn do not repeat.
"""

from pathlib import Path

from .endgames import EndgameCollection, EndgameDeck
from .openings import OpeningBook


class Assets:
    def __init__(self, app_dir, played_endgames=lambda: ()):
        self.app_dir = Path(app_dir)
        self.played_endgames = played_endgames   # keys of the endgames played in earlier runs
        self._book = None
        self._endgames = None
        self._deck = None
        self._middlegames = None
        self._middlegame_deck = None

    @property
    def opening_folder(self):
        return self.app_dir / "assets" / "openings"

    @property
    def endgame_folder(self):
        return self.app_dir / "assets" / "endgames"

    @property
    def middlegame_folder(self):
        return self.app_dir / "assets" / "middlegames"

    def opening_book(self):
        if self._book is None:
            self._book = OpeningBook.load(self.opening_folder)
        return self._book

    def endgames(self):
        if self._endgames is None:
            self._endgames = EndgameCollection.load(self.endgame_folder)
        return self._endgames

    def endgame_deck(self):
        if self._deck is None:
            self._deck = EndgameDeck(self.endgames(), played=self.played_endgames())
        return self._deck

    def middlegames(self):
        if self._middlegames is None:
            self._middlegames = EndgameCollection.load(self.middlegame_folder)
        return self._middlegames

    def middlegame_deck(self, played=()):
        """`played`: keys of the puzzles played in earlier runs; used when the deck is first made."""
        if self._middlegame_deck is None:
            self._middlegame_deck = EndgameDeck(self.middlegames(), played=played)
        return self._middlegame_deck
