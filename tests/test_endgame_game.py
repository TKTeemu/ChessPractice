import io

import chess
import chess.pgn

from app.commands import TAKE_BACK
from app.endgame_game import MATE, EndgameGame, is_mistake, user_score
from app.endgames import EndgameCollection
from app.engines.base import Analysis

SAAVEDRA = """[Event "Saavedra Position"]
[Key "saavedra"]
[Difficulty "5"]
[Goal "win"]
[Composer "Fernando Saavedra"]
[Year "1895"]
[SetUp "1"]
[FEN "8/8/1KP5/3r4/8/8/8/k7 w - - 0 1"]

1. c7 Rd6+ 2. Kb5 Rd5+ 3. Kb4 Rd4+ 4. Kb3 Rd3+ 5. Kc2 Rd4
6. c8=R (6. c8=Q? {Rc4+ 7. Qxc4 is stalemate.} Rc4+ 7. Qxc4) 6... Ra4 7. Kb3 *
"""
SAAVEDRA_MAIN = ["c7", "Rd6+", "Kb5", "Rd5+", "Kb4", "Rd4+", "Kb3", "Rd3+", "Kc2", "Rd4", "c8=R", "Ra4", "Kb3"]

STALEMATE_TRAP = """[Event "Queen Mate"]
[Key "kq"]
[Difficulty "1"]
[Goal "win"]
[SetUp "1"]
[FEN "k7/8/2K5/8/8/8/8/1Q6 w - - 0 1"]

{Mate, but mind the stalemate.} 1. Qb7# (1. Qb6? {Stalemate.}) *
"""
NO_TREE = """[Event "Rook Mate"]
[Key "kr"]
[Difficulty "1"]
[Goal "{goal}"]
[SetUp "1"]
[FEN "{fen}"]

*
"""
KR_FEN = "8/8/8/4k3/8/8/8/R3K3 w - - 0 1"


class FakeTime:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def sample(text):
    return EndgameCollection._sample(chess.pgn.read_game(io.StringIO(text)), set())


def new_game(text=SAAVEDRA, can_judge=False, minutes=15):
    now = FakeTime()
    return EndgameGame(sample(text), "Stockfish", can_judge, minutes, now=now), now


def play(game, board, *sans):
    for san in sans:
        board.push_san(san)
        game.move_played(board)


def start_board(game):
    return chess.Board(game.sample.fen)


# --- Judging rule ------------------------------------------------------------

def test_user_score_and_mates():
    move = chess.Move.from_uci("e2e4")
    assert user_score(Analysis(move, cp=120), True) == 120
    assert user_score(Analysis(move, cp=120), False) == -120
    assert user_score(Analysis(move, mate=3), True) == MATE - 3
    assert user_score(Analysis(move, mate=-2), False) == MATE - 2   # the opponent is mated
    assert user_score(Analysis(move), True) is None


def test_is_mistake_needs_a_clear_drop():
    assert is_mistake("win", 500, 40)            # a win thrown away
    assert not is_mistake("win", 179, 140)       # an uncertain score that hardly moved
    assert not is_mistake("win", 500, 300)       # still winning
    assert not is_mistake("win", 40, MATE - 5)   # the user mates
    assert is_mistake("win", 400, -MATE + 3)     # walked into a mate
    assert is_mistake("draw", 0, -400)
    assert not is_mistake("draw", -250, -320)    # it was already almost lost
    assert not is_mistake("draw", 0, -100)
    assert not is_mistake("win", 500, None)


# --- The solution tree ------------------------------------------------------

def test_solution_move_is_ok_and_tree_gives_the_defence():
    game, _ = new_game()
    board = start_board(game)
    assert game.user_color == chess.WHITE and game.goal_text() == "Goal: White to play and win"
    play(game, board, "c7")
    assert game.judgements == {1: "ok"} and game.light == "pending"
    assert board.san(game.tree_reply(board)) == "Rd6+"


def test_known_wrong_try_turns_the_light_red_and_explains():
    game, _ = new_game()
    board = start_board(game)
    play(game, board, *SAAVEDRA_MAIN[:10], "c8=Q")
    assert game.light == "fail" and "stalemate" in game.notice
    assert board.san(game.tree_reply(board)) == "Rc4+"   # the computer plays the refutation


def test_playing_the_solution_out_is_a_success():
    game, _ = new_game()
    board = start_board(game)
    play(game, board, *SAAVEDRA_MAIN)
    assert game.light == "success" and game.solved_ply == len(SAAVEDRA_MAIN)
    assert game.tree_reply(board) is None   # outside the tree the engine plays


def test_mate_reaches_the_win_goal():
    game, _ = new_game(STALEMATE_TRAP)
    board = start_board(game)
    play(game, board, "Qb7#")
    assert game.over and game.light == "success" and game.result == "1-0"


def test_stalemate_misses_the_win_goal():
    game, _ = new_game(NO_TREE.format(goal="win", fen="k7/8/2K5/8/8/8/8/1Q6 w - - 0 1"))
    board = start_board(game)
    play(game, board, "Qb6")
    assert game.over and game.result == "1/2-1/2" and game.light == "fail"


def test_a_draw_reaches_the_draw_goal():
    game, _ = new_game(NO_TREE.format(goal="draw", fen="4k3/8/8/8/8/8/4p3/4K3 w - - 0 1"))
    board = start_board(game)
    play(game, board, "Kxe2")   # insufficient material
    assert game.over and game.result == "1/2-1/2" and game.light == "success"


def test_time_out_misses_the_goal_and_blocks_take_back():
    game, now = new_game()
    board = start_board(game)
    play(game, board, "c7", "Rd6+")
    now.t += 15 * 60 + 1
    assert game.check_time(board)
    assert game.light == "fail" and not game.allows(TAKE_BACK)


def test_take_back_allowed_after_mate_or_stalemate():
    game, _ = new_game(NO_TREE.format(goal="win", fen="k7/8/2K5/8/8/8/8/1Q6 w - - 0 1"))
    board = start_board(game)
    play(game, board, "Qb6")
    assert game.over and game.allows(TAKE_BACK)
    board.pop()
    game.took_back(board)
    assert not game.over and game.light == "pending" and game.take_backs == 1


# --- The engine as judge ----------------------------------------------------

def test_engine_verdict_turns_the_light():
    game, _ = new_game(NO_TREE.format(goal="win", fen=KR_FEN), can_judge=True)
    board = start_board(game)
    play(game, board, "Ra5+")
    assert game.needs_judging(board) and game.needs_eval(0)
    move = chess.Move.from_uci("e5d4")
    game.analysed(0, Analysis(move, cp=900))          # before the move, the user to move
    game.analysed(1, Analysis(move, cp=-880))         # after it, the computer to move
    assert game.judgements[1] == "ok" and game.light == "pending"
    board.push_san("Kd4")
    game.move_played(board)
    play(game, board, "Rb5")
    game.analysed(3, Analysis(move, cp=0))            # e.g. the rook hangs
    assert game.light == "fail" and game.notice


def test_red_stays_red_until_take_back():
    game, _ = new_game(NO_TREE.format(goal="win", fen=KR_FEN), can_judge=True)
    board = start_board(game)
    game.analysed(0, Analysis(chess.Move.from_uci("a1a5"), cp=900))
    play(game, board, "Ra5+")
    game.analysed(1, Analysis(chess.Move.from_uci("e5d4"), cp=0))
    play(game, board, "Kd4", "Ke2")
    game.analysed(3, Analysis(chess.Move.from_uci("d4c4"), cp=-900))   # a good move later
    assert game.light == "fail"
    board.pop()
    board.pop()
    board.pop()
    game.took_back(board)
    assert game.light == "pending" and game.judgements == {} and 1 not in game.evals and 0 in game.evals


def test_the_engines_own_move_keeps_its_score():
    game, _ = new_game(NO_TREE.format(goal="win", fen=KR_FEN), can_judge=True)
    board = start_board(game)
    play(game, board, "Ra5+")
    reply = chess.Move.from_uci("e5d4")
    game.analysed(1, Analysis(reply, cp=-880, ponder=chess.Move.from_uci("e1d2")))
    board.push(reply)
    game.move_played(board)
    assert game.evals[2] == 880 and not game.needs_eval(2)
    assert game.hints(board) == [(chess.E1, chess.D2, "main")]   # the expected reply as a suggestion


def test_without_an_engine_moves_off_the_solution_stay_grey():
    game, _ = new_game()
    board = start_board(game)
    play(game, board, "Kb7")
    assert game.judgements == {1: "pending"} and game.light == "pending"
    assert not game.needs_judging(board) and game.notice == "No engine to judge moves off the solution"
    assert game.tree_reply(board) is None


def test_stale_replies_after_take_back_are_ignored():
    game, _ = new_game(can_judge=True)
    board = start_board(game)
    play(game, board, "Kb7")
    request_id = game.new_request()
    board.pop()
    game.took_back(board)
    assert not game.is_current(request_id)


# --- Suggestions, headers ---------------------------------------------------

def test_hints_from_the_tree_and_counted_once():
    game, _ = new_game()
    board = start_board(game)
    hints = game.hints(board)
    assert hints == [(chess.C6, chess.C7, "main")]
    game.note_hints(board, hints)
    game.note_hints(board, hints)
    assert game.hints_used == 1
    play(game, board, "c7")
    assert game.hints(board) == []   # the computer's turn


def test_headers():
    game, _ = new_game()
    headers = chess.pgn.Game().headers
    game.write_headers(headers)
    assert headers["Event"] == "Endgame practice" and headers["White"] == "You"
    assert headers["Black"] == "Stockfish" and headers["FEN"] == game.sample.fen
    assert headers["EndgameKey"] == "saavedra" and headers["Difficulty"] == "5"
    assert headers["Composer"] == "Fernando Saavedra" and "Source" not in headers
    game.resign()
    game.write_result(headers)
    assert headers["Result"] == "0-1" and headers["HintsUsed"] == "0" and headers["TakeBacks"] == "0"
    assert game.light == "fail"
