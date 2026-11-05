import io
import random
from pathlib import Path

import chess
import chess.pgn

from app.endgames import DIFFICULTIES, GOALS, EndgameCollection, EndgameDeck, SolutionTree
from app.model import game_outcome

FOLDER = Path(__file__).resolve().parent.parent / "assets" / "endgames"
COLLECTION = EndgameCollection.load(FOLDER)
MIN_PER_LEVEL = 15


def collection_from(text):
    folder_text = io.StringIO(text)
    samples, keys = [], set()
    while (game := chess.pgn.read_game(folder_text)) is not None:
        sample = EndgameCollection._sample(game, keys)
        keys.add(sample.key)
        samples.append(sample)
    return EndgameCollection(samples, {})


def position(key, difficulty=1):
    return f"""[Event "{key}"]
[Key "{key}"]
[Difficulty "{difficulty}"]
[Goal "win"]
[SetUp "1"]
[FEN "8/8/8/4k3/8/8/8/R3K3 w - - 0 1"]

*

"""


# --- The files in assets/endgames/ ------------------------------------------

def test_every_file_loads_without_errors():
    assert COLLECTION.errors == []
    assert len(COLLECTION.all) >= 5 * MIN_PER_LEVEL


def test_every_level_has_a_name_and_enough_positions():
    levels = COLLECTION.levels()
    assert [d for d, _, _ in levels] == list(DIFFICULTIES)
    for difficulty, name, count in levels:
        assert name != str(difficulty), f"level {difficulty} has no DifficultyName"
        assert count >= MIN_PER_LEVEL, (difficulty, count)


def test_positions_are_playable_and_solutions_legal():
    for sample in COLLECTION.all:
        assert sample.goal in GOALS and sample.difficulty in DIFFICULTIES
        board = chess.Board(sample.fen)
        assert board.is_valid() and game_outcome(board) is None, sample.key
        assert sample.game.errors == [], sample.key   # illegal moves would be listed here
        assert sample.name and sample.name != "?", sample.key


def test_keys_are_unique():
    keys = [s.key for s in COLLECTION.all]
    assert len(keys) == len(set(keys))


# --- Loading rules -------------------------------------------------------------

def test_bad_games_are_skipped_with_a_reason(tmp_path):
    good = position("good")
    (tmp_path / "level1.pgn").write_text(
        good + good  # duplicate key
        + position("bad_level", difficulty=7)
        + '[Event "No FEN"]\n[Key "nofen"]\n[Difficulty "1"]\n[Goal "win"]\n\n*\n\n'
        + good.replace('"win"', '"lose"').replace('"good"', '"badgoal"'),
        encoding="utf-8")
    collection = EndgameCollection.load(tmp_path)
    assert [s.key for s in collection.all] == ["good"]
    reasons = " ".join(error for _, error in collection.errors)
    assert "duplicate" in reasons and "Difficulty" in reasons and "FEN" in reasons and "Goal" in reasons


def test_credit_text_leaves_out_what_is_unknown():
    sample = COLLECTION.sample("saavedra")
    assert sample.credit_text().startswith("Fernando Saavedra") and "1895" in sample.credit_text()
    plain = collection_from(position("plain")).all[0]
    assert plain.credit_text() == "" and plain.side() == chess.WHITE


# --- SolutionTree ---------------------------------------------------------------

def test_solution_tree_marks_wrong_tries_and_ends():
    tree = SolutionTree(COLLECTION.sample("saavedra"))
    board = chess.Board(tree.sample.fen)
    for san in ("c7", "Rd6+", "Kb5", "Rd5+", "Kb4", "Rd4+", "Kb3", "Rd3+", "Kc2", "Rd4"):
        assert not tree.at_end(board)
        board.push_san(san)
    moves = {board.san(sm.move): sm for sm in tree.moves(board)}
    assert not moves["c8=R"].wrong and moves["c8=Q"].wrong and moves["c8=Q"].comment
    assert tree.moves(board)[0].move == board.parse_san("c8=R")   # the main line first
    board.push_san("c8=Q")
    assert tree.pick(board, random.Random(0)) == board.parse_san("Rc4+")   # the refutation
    board.push_san("Rc4+")
    board.push_san("Qxc4")
    assert not tree.at_end(board)   # a line after a wrong try is no success


def test_solution_tree_finds_transpositions():
    tree = SolutionTree(COLLECTION.sample("reti"))
    board = chess.Board(tree.sample.fen)
    for san in ("Kg7", "Kb6", "Kf6", "h4"):   # 1... Kb6 first, then h4
        board.push_san(san)
    assert tree.contains(board) and tree.moves(board)


# --- EndgameDeck -----------------------------------------------------------------

def deck_collection(count):
    return collection_from("".join(position(f"p{i}") for i in range(count)))


def test_deck_does_not_repeat_until_the_level_is_played():
    deck = EndgameDeck(deck_collection(6), random.Random(1))
    first = [deck.draw(1).key for _ in range(6)]
    assert len(set(first)) == 6 and deck.played(1) == 6 and deck.played(2) == 0
    for _ in range(30):   # the next round never starts with the position just played
        last = deck._last[1]
        round_ = [deck.draw(1).key for _ in range(6)]
        assert len(set(round_)) == 6 and round_[0] != last


def test_deck_with_a_single_position():
    deck = EndgameDeck(deck_collection(1), random.Random(2))
    assert deck.draw(1).key == deck.draw(1).key == "p0" and deck.played(1) == 1


def test_deck_prefers_positions_not_played_in_an_earlier_run():
    collection = deck_collection(4)
    deck = EndgameDeck(collection, random.Random(3), played=["p0", "p1", "removed since"])
    assert deck.played(1) == 2
    assert {deck.draw(1).key for _ in range(2)} == {"p2", "p3"}
    assert deck.played(1) == 4
    assert {deck.draw(1).key for _ in range(4)} == {"p0", "p1", "p2", "p3"}   # then all of them again


def test_deck_with_everything_played_starts_over():
    deck = EndgameDeck(deck_collection(2), random.Random(4), played=["p0", "p1"])
    assert {deck.draw(1).key for _ in range(2)} == {"p0", "p1"}
