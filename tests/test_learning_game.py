import random
from pathlib import Path

import chess
import chess.pgn

from app.learning_game import LearningGame
from app.openings import OpeningBook, OpeningLine

FOLDER = Path(__file__).resolve().parent.parent / "assets" / "openings"
BOOK = OpeningBook.load(FOLDER)


def new_game(key="reti", user_color=chess.WHITE, vary=False, suggest_moves=12):
    line = OpeningLine(BOOK.opening(key))
    return LearningGame(line, user_color, "Stockfish 1500", vary, random.Random(0), suggest_moves)


def play(game, board, *sans):
    for san in sans:
        board.push_san(san)
        game.move_played(board)


def test_computer_follows_the_book_then_asks_the_engine():
    game = new_game()
    board = chess.Board()
    assert not game.is_computer_turn(board)
    play(game, board, "Nf3")
    assert game.is_computer_turn(board)
    assert board.san(game.computer_reply(board)) == "d5"      # the main line
    play(game, board, "d5", "g3", "Nf6", "Bg2", "c6", "O-O", "Bg4", "d3", "Nbd7", "Nbd2", "e5", "e4")
    assert game.computer_reply(board) is None                  # end of the book: the engine plays
    assert game.notice == "End of theory – the engine takes over."
    assert game.user_book_hits == game.user_book_chances == 7
    assert game.current_line_name == "King's Indian Attack"


def test_deviation_is_recognised():
    game = new_game()
    board = chess.Board()
    play(game, board, "Nf3", "d5", "b3")                       # not in the book
    assert not game.in_book and game.deviation
    before = chess.Board()
    before.push_san("Nf3")
    before.push_san("d5")
    assert {before.san(bm.move) for bm in game.deviation} == {"g3", "c4"}
    assert game.notice == "Out of theory. Book moves: g3, c4"
    assert game.user_book_hits == 1 and game.user_book_chances == 2
    assert game.computer_reply(board) is None
    # the arrows show the book moves of the position left until the user moves again
    board.push_san("Nf6")
    assert len(game.hints(board)) == 2 and game.hints(board)[0][2] == "main"


def test_deviation_without_suggestions_is_only_mentioned():
    game = new_game()
    board = chess.Board()
    play(game, board, "Nf3", "d5")
    board.push_san("b3")
    game.move_played(board, suggest=False)
    assert game.notice == "Out of theory"


def test_suggestions_while_in_book():
    game = new_game()
    board = chess.Board()
    hints = game.hints(board)
    assert hints == [(chess.G1, chess.F3, "main")]
    play(game, board, "Nf3")
    assert game.hints(board) == []                              # the computer's turn


def test_take_back_restores_the_state():
    game = new_game()
    board = chess.Board()
    play(game, board, "Nf3", "d5", "b3", "Nf6")
    assert game.deviation and not game.in_book
    for _ in range(2):
        board.pop()
    game.took_back(board)
    assert game.in_book and game.deviation is None and game.notice is None
    assert game.user_book_hits == game.user_book_chances == 1
    assert game.opening_phase and not game.over
    assert {chess.Board(board.fen()).san(chess.Move(f, t)) for f, t, _ in game.hints(board)} == {"g3", "c4"}


def test_black_as_the_opening_side():
    game = new_game("english_defence", user_color=chess.BLACK)
    board = chess.Board()
    assert game.is_computer_turn(board)
    assert board.san(game.computer_reply(board)) == "c4"
    play(game, board, "c4")
    assert [board.san(chess.Move(f, t)) for f, t, _ in game.hints(board)][0] == "e6"
    play(game, board, "e6", "d4", "b6")
    assert game.user_book_hits == 2 and game.in_book


def test_user_plays_the_reply():
    game = new_game("reti", user_color=chess.BLACK)
    board = chess.Board()
    assert game.is_computer_turn(board) and board.san(game.computer_reply(board)) == "Nf3"
    headers = chess.pgn.Game().headers
    game.write_headers(headers)
    assert headers["White"] == "Stockfish 1500" and headers["Black"] == "You"
    assert headers["Event"] == "Opening training" and headers["Opening"] == "Réti Opening"
    assert headers["ECO"] == "A04-A09"


def test_opening_phase_ends_at_the_move_limit():
    game = new_game("queens_gambit", suggest_moves=10)
    board = chess.Board()
    play(game, board, "d4", "d5", "c4", "e6", "Nc3", "Nf6", "Bg5", "Be7", "e3", "O-O", "Nf3", "Nbd7",
         "Rc1", "c6", "Bd3", "dxc4", "Bxc4", "Nd5")
    assert board.fullmove_number == 10 and game.opening_phase
    play(game, board, "Bxe7", "Qxe7")
    assert board.fullmove_number == 11 and not game.opening_phase
    assert game.hints(board) == [] and game.suggestions(board) == []


def test_opening_phase_ends_two_user_moves_outside_the_book():
    game = new_game()
    board = chess.Board()
    play(game, board, "Nf3", "d5", "b3", "Nf6")                # left the book with b3
    assert game.opening_phase
    play(game, board, "Bb2", "e6")
    assert game.opening_phase                                   # one user move outside the book
    play(game, board, "e3")
    assert not game.opening_phase and game.hints(board) == []


def test_returning_to_the_book_by_transposition_keeps_the_opening_phase():
    game = new_game("english")
    board = chess.Board()
    # 1.c4 e5 2.Nf3 (not in the book) Nc6 3.Nc3 Nf6 reaches the book position after 3.Nf3 Nc6
    play(game, board, "c4", "e5", "Nf3")
    assert not game.in_book
    play(game, board, "Nc6", "Nc3")
    assert not game.in_book and game.opening_phase
    play(game, board, "Nf6")
    assert game.in_book and game.opening_phase
    assert [board.san(chess.Move(f, t)) for f, t, _ in game.hints(board)][0] == "g3"


def test_commands_and_game_end():
    game = new_game()
    assert game.allows("take_back") and game.allows("navigate") and not game.allows("paste")
    board = chess.Board()
    play(game, board, "f3", "e5", "g4", "Qh4#")
    assert game.over and game.end_text == "Checkmate – Black wins" and game.result == "0-1"
    assert not game.can_move(board, chess.WHITE, at_end=True)
    request = game.new_request()
    assert not game.is_current(request)
