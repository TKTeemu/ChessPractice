import chess
import chess.pgn

from app.computer_game import ComputerGame
from app.engines.base import Level
from app.model import GameModel

LEVEL = Level("1500", "1500", 1500, 1.0, {})


class FakeTime:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def new_game(color=chess.WHITE, minutes=30):
    now = FakeTime()
    return ComputerGame(color, "Stockfish", LEVEL, minutes, now), now


def test_turns_and_moving_rights():
    game, _ = new_game(chess.BLACK)
    board = chess.Board()
    assert game.is_engine_turn(board)
    assert not game.can_move(board, chess.WHITE, at_end=True)
    board.push_san("e4")
    assert not game.is_engine_turn(board)
    assert game.can_move(board, chess.BLACK, at_end=True)
    assert not game.can_move(board, chess.BLACK, at_end=False)   # browsing earlier moves
    assert not game.can_move(board, chess.WHITE, at_end=True)


def test_commands_blocked_during_game():
    game, _ = new_game()
    for command in ("delete_last", "edit_tree", "paste", "open", "edit_comment", "navigate"):
        assert not game.allows(command)
    game.resign()
    assert game.allows("edit_comment") and not game.allows("navigate") and not game.allows("delete_last")


def test_headers():
    game, _ = new_game(chess.BLACK)
    headers = chess.pgn.Game().headers
    game.write_headers(headers)
    assert headers["White"] == "Stockfish 1500" and headers["Black"] == "You"
    assert headers["WhiteElo"] == "1500" and "BlackElo" not in headers
    assert headers["TimeControl"] == "1800" and headers["Event"] == "vs Computer"


def test_clock_starts_with_first_move_and_returns_mover_time():
    game, now = new_game()
    board = chess.Board()
    now.t = 50                       # thinking before the first move is free
    board.push_san("e4")
    assert game.move_played(board) == 1800
    now.t += 10                      # engine thinks 10 s
    board.push_san("e5")
    assert game.move_played(board) == 1790
    now.t += 30
    board.push_san("Nf3")
    assert game.move_played(board) == 1770


def test_checkmate_ends_game():
    game, _ = new_game()
    board = chess.Board()
    for san in ("f3", "e5", "g4", "Qh4#"):
        board.push_san(san)
        game.move_played(board)
    assert game.over and game.result == "0-1" and game.termination == "normal"


def test_time_forfeit():
    game, now = new_game(minutes=1)
    board = chess.Board()
    board.push_san("e4")
    game.move_played(board)
    board.push_san("e5")
    game.move_played(board)          # user's (white's) clock runs
    now.t += 59
    assert not game.check_time(board)
    now.t += 2
    assert game.check_time(board)
    assert game.result == "0-1" and game.termination == "time forfeit"
    assert not game.check_time(board)   # only once


def test_time_forfeit_is_draw_without_mating_material():
    game, now = new_game(minutes=1)
    board = chess.Board("4k3/8/8/8/8/8/4P3/4K2R b - - 0 1")   # black (engine) has a bare king
    board.push_san("Kd8")
    game.move_played(board)
    now.t += 61
    assert game.check_time(board)
    assert game.result == "1/2-1/2"


def test_resign_and_stale_engine_replies():
    game, _ = new_game(chess.BLACK)
    request_id = game.new_request()
    assert game.is_current(request_id)
    assert not game.is_current(request_id - 1)
    game.resign()
    assert game.result == "1-0" and not game.is_current(request_id)


def test_engine_failure_stops_game():
    game, _ = new_game()
    game.engine_failed("crashed")
    assert game.over and game.result == "*" and "crashed" in game.end_text


def test_clock_comment_is_hidden_and_kept():
    m = GameModel()
    m.make_move(chess.E2, chess.E4)
    m.set_clock(m.node, 1781.4)
    assert "[%clk 0:29:41]" in m.node.comment
    assert m.set_comment(m.node, "good move")
    assert "[%clk 0:29:41]" in m.node.comment and "good move" in m.node.comment
    assert not m.set_comment(m.node, "good move")
    assert m.set_comment(m.node, "")
    assert m.node.comment == "[%clk 0:29:41]"


def test_score_text_from_users_point_of_view():
    board = chess.Board()
    white, _ = new_game(chess.WHITE)
    black, _ = new_game(chess.BLACK)
    assert white.score_text(board) == black.score_text(board) == "Material: even"
    board = chess.Board("rnb1kbnr/pppp1ppp/8/4p3/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")   # black has no queen
    assert white.score_text(board) == "Material: you +9"
    assert black.score_text(board) == "Material: you −9"
