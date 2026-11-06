import io

import chess
import chess.pgn

from app.endgames import EndgameCollection
from app.engines.base import Analysis
from app.middlegame_game import MiddlegameGame

PUZZLE = """[Event "Back-Rank Mate"]
[Key "back_rank"]
[Difficulty "1"]
[Goal "win"]
[SetUp "1"]
[FEN "3r2k1/5ppp/p7/1p6/8/P6P/1P2QPP1/4R1K1 w - - 0 1"]

1. Qe7 Rf8 *
"""


def analysis(move, cp):
    return Analysis(move=chess.Move.from_uci(move), ponder=None, cp=cp, mate=None)


def new_game(can_judge=True):
    sample = EndgameCollection._sample(chess.pgn.read_game(io.StringIO(PUZZLE)), set())
    return MiddlegameGame(sample, "Stockfish", can_judge, 30), chess.Board(sample.fen)


def play(game, board, *sans):
    for san in sans:
        board.push_san(san)
        game.move_played(board)


def test_the_light_turns_green_at_the_end_of_the_line():
    game, board = new_game()
    assert game.light == "pending"
    play(game, board, "Qe7")
    assert game.light == "pending"
    play(game, board, "Rf8")
    assert game.solved_ply == 2 and game.light == "success" and game.light_text == "Solved"


def test_the_light_stays_green_when_the_game_is_lost_afterwards():
    game, board = new_game()
    play(game, board, "Qe7", "Rf8")
    game.resign()
    assert game.over and game.result == "0-1"
    assert game.light == "success" and game.light_text.startswith("Solved · ")


def test_the_light_stays_green_when_a_later_move_is_a_blunder():
    game, board = new_game()
    play(game, board, "Qe7", "Rf8", "Kh1")
    assert game.light == "success" and not game.needs_judging(board)   # no time spent on judging
    game.judgements[3] = "pending"
    game.analysed(2, analysis("e7e8", 500))
    game.analysed(3, analysis("f8e8", 500))   # the side to move's view: Black is winning
    assert game.judgements[3] == "fail" and game.light == "success" and game.notice is None


def test_a_miss_before_the_solution_is_finished_stays_red():
    game, board = new_game()
    play(game, board, "Kh1")
    game.analysed(0, analysis("e2e7", 500))
    game.analysed(1, analysis("d8d1", 500))   # the side to move's view: Black is winning
    assert game.light == "fail" and game.notice


def test_taking_back_the_solving_move_ends_solved():
    game, board = new_game()
    play(game, board, "Qe7", "Rf8")
    board.pop()
    board.pop()
    game.took_back(board)
    assert game.solved_ply is None and game.light == "pending"


def test_winning_off_the_line_also_counts_and_losing_off_it_does_not():
    game, board = new_game()
    game._finish("1-0", "Black resigned", "normal")
    assert game.light == "success"
    game, board = new_game()
    game.resign()
    assert game.light == "fail"


def test_suggestions_come_from_the_line_and_then_from_the_engine():
    game, board = new_game()
    assert game.hints(board) == [(chess.E2, chess.E7, "main")]
    play(game, board, "Qe7", "Rf8")
    assert game.hints(board) == []   # the end of the line: nothing known yet
    game.analysed(2, analysis("e7c7", 500))
    assert game.hints(board) == [(chess.E7, chess.C7, "main")]


def test_saved_game_headers_name_the_puzzle():
    game, _ = new_game()
    headers = {}
    game.write_headers(headers)
    assert headers["Event"] == "Middlegame practice" and headers["MiddlegameKey"] == "back_rank"
    assert "EndgameKey" not in headers and headers["FEN"] == game.sample.fen
