from pathlib import Path

import chess

from app.endgames import GOALS, EndgameCollection, SolutionTree
from app.model import game_outcome

FOLDER = Path(__file__).resolve().parent.parent / "assets" / "middlegames"
COLLECTION = EndgameCollection.load(FOLDER)
LEVELS = [1, 2, 3]
PER_LEVEL = 10


def test_every_file_loads_without_errors():
    assert COLLECTION.errors == []


def test_every_level_has_a_name_and_enough_puzzles():
    levels = COLLECTION.levels()
    assert [d for d, _, _ in levels] == LEVELS
    for difficulty, name, count in levels:
        assert name != str(difficulty), f"level {difficulty} has no DifficultyName"
        assert count >= PER_LEVEL, (difficulty, count)


def test_puzzles_are_playable_and_solutions_legal():
    for sample in COLLECTION.all:
        assert sample.goal in GOALS, sample.key
        board = chess.Board(sample.fen)
        assert board.is_valid() and game_outcome(board) is None, sample.key
        assert sample.game.errors == [], sample.key   # illegal moves would be listed here
        assert sample.name and sample.name != "?", sample.key
        assert sample.game.comment.strip(), sample.key   # the introduction


def test_every_puzzle_has_a_solution_that_can_be_played_out():
    for sample in COLLECTION.all:
        tree = SolutionTree(sample)
        board = chess.Board(sample.fen)
        assert tree.moves(board), sample.key
        node = sample.game
        while node.variations:
            node = node.variations[0]
            board.push(node.move)
        assert tree.at_end(board), sample.key


def test_keys_are_unique():
    keys = [s.key for s in COLLECTION.all]
    assert len(keys) == len(set(keys))


def test_games_are_credited_above_level_one():
    for sample in COLLECTION.all:
        if sample.difficulty > 1:
            assert sample.source and sample.year, sample.key
