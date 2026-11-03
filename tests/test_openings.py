import random
from pathlib import Path

import chess
import pytest

from app.openings import OpeningBook, OpeningLine, split_comment

FOLDER = Path(__file__).resolve().parent.parent / "assets" / "openings"

# Key -> (group, start moves, side that makes the opening), as in Avausteoria_suunnitelma.md
EXPECTED = {
    "anderssen": ("Irregular openings", "1. a3", chess.WHITE),
    "ware": ("Irregular openings", "1. a4", chess.WHITE),
    "durkin": ("Irregular openings", "1. Na3", chess.WHITE),
    "dunst": ("Irregular openings", "1. Nc3", chess.WHITE),
    "sokolsky": ("Irregular openings", "1. b4", chess.WHITE),
    "saragossa": ("Irregular openings", "1. c3", chess.WHITE),
    "mieses": ("Irregular openings", "1. d3", chess.WHITE),
    "vant_kruijs": ("Irregular openings", "1. e3", chess.WHITE),
    "barnes": ("Irregular openings", "1. f3", chess.WHITE),
    "grob": ("Irregular openings", "1. g4", chess.WHITE),
    "clemenz": ("Irregular openings", "1. h3", chess.WHITE),
    "desprez": ("Irregular openings", "1. h4", chess.WHITE),
    "amar": ("Irregular openings", "1. Nh3", chess.WHITE),
    "benko": ("Irregular openings", "1. g3", chess.WHITE),
    "larsen": ("Flank openings", "1. b3", chess.WHITE),
    "bird": ("Flank openings", "1. f4", chess.WHITE),
    "reti": ("Flank openings", "1. Nf3", chess.WHITE),
    "english": ("Flank openings", "1. c4", chess.WHITE),
    "english_defence": ("Flank openings", "1. c4 e6 2. d4 b6", chess.BLACK),
    "queens_gambit": ("Gambits", "1. d4 d5 2. c4", chess.WHITE),
    "kings_gambit": ("Gambits", "1. e4 e5 2. f4", chess.WHITE),
}


@pytest.fixture(scope="module")
def book():
    return OpeningBook.load(FOLDER)


def line_of(book, key):
    return OpeningLine(book.opening(key))


def test_all_book_files_load(book):
    assert book.errors == []
    assert {o.key for o in book.openings} == set(EXPECTED)
    assert len({o.key for o in book.openings}) == len(book.openings)


def test_openings_match_the_plan(book):
    for key, (group, start, side) in EXPECTED.items():
        opening = book.opening(key)
        moves = list(opening.game.mainline_moves())
        plies = len(start.replace(".", " ").split()) - start.count(".")
        assert chess.Board().variation_san(moves[:plies]) == start, key
        assert opening.group == group and opening.side == side, key
        assert 8 <= len(moves) <= 18, key


def test_groups_in_order(book):
    groups = [name for name, _ in book.groups()]
    assert groups == ["Irregular openings", "Flank openings", "Gambits"]
    irregular = dict(book.groups())["Irregular openings"]
    assert irregular[0].key == "anderssen" and irregular[-1].key == "benko"


def test_main_line_first_and_pick_without_variety(book):
    line = line_of(book, "reti")
    board = chess.Board()
    board.push_san("Nf3")
    moves = line.moves(board)
    assert board.san(moves[0].move) == "d5" and len(moves) == 3
    assert moves[0].weight > moves[1].weight
    for _ in range(5):
        assert line.pick(board, random.Random(), vary=False) == chess.Move.from_uci("d7d5")


def test_varied_pick_uses_book_moves(book):
    line = line_of(book, "queens_gambit")
    board = chess.Board()
    for san in ("d4", "d5", "c4"):
        board.push_san(san)
    rng = random.Random(1)
    picked = {board.san(line.pick(board, rng, vary=True)) for _ in range(200)}
    assert picked <= {"e6", "dxc4", "c6", "e5", "Nc6"} and "e6" in picked and len(picked) >= 3


def test_transposition_is_found(book):
    line = line_of(book, "english_defence")
    board = chess.Board()
    for san in ("c4", "b6", "d4", "e6"):    # the other move order
        board.push_san(san)
    assert [board.san(bm.move) for bm in line.moves(board)][0] == "e4"


def test_outside_the_book(book):
    line = line_of(book, "reti")
    board = chess.Board()
    board.push_san("e4")
    assert line.moves(board) == [] and line.pick(board, random.Random(), True) is None


def test_line_names_and_comments(book):
    line = line_of(book, "english")
    board = chess.Board()
    board.push_san("c4")
    by_san = {board.san(bm.move): bm for bm in line.moves(board)}
    assert by_san["e5"].line == "Reversed Sicilian" and by_san["c5"].line == "Symmetrical Variation"
    assert line.moves(chess.Board())[0].comment.startswith("White controls d5")
    # the name is inherited by later moves of the variation
    board.push_san("c5")
    assert line.moves(board)[0].line == "Symmetrical Variation"


def test_split_comment():
    assert split_comment("Line: From's Gambit; Black gives a pawn.") == ("From's Gambit", "Black gives a pawn.")
    assert split_comment("Line: Slav Defence") == ("Slav Defence", "")
    assert split_comment("Just an idea.") == (None, "Just an idea.")


def test_invalid_games_are_skipped(tmp_path):
    (tmp_path / "bad.pgn").write_text(
        '[Event "No key"]\n[Side "white"]\n\n1. e4 *\n\n'
        '[Event "Bad side"]\n[Key "x"]\n[Side "red"]\n\n1. e4 *\n\n'
        '[Event "Illegal"]\n[Key "y"]\n[Side "white"]\n\n1. e5 *\n\n'
        '[Event "Good"]\n[Key "z"]\n[Side "black"]\n\n1. e4 c5 *\n', encoding="utf-8")
    book = OpeningBook.load(tmp_path)
    assert [o.key for o in book.openings] == ["z"]
    assert len(book.errors) == 3
