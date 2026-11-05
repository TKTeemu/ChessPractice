import chess
import pytest

from app import model as M
from app.model import GameModel

SQ = chess.parse_square


def play(m, *ucis):
    events = []
    for uci in ucis:
        move = chess.Move.from_uci(uci)
        events.append(m.play(chess.Move(move.from_square, move.to_square, move.promotion)))
    return events


def perft(board, depth):
    if depth == 0:
        return 1
    total = 0
    for move in board.legal_moves:
        board.push(move)
        total += perft(board, depth - 1)
        board.pop()
    return total


@pytest.mark.parametrize("fen,depth,expected", [
    (chess.STARTING_FEN, 3, 8902),
    ("r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 2, 2039),  # "Kiwipete"
    ("8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 3, 2812),
])
def test_perft(fen, depth, expected):
    assert perft(chess.Board(fen), depth) == expected


def test_illegal_move_rejected():
    m = GameModel()
    assert m.play(chess.Move(SQ("e2"), SQ("e5"))) is None
    assert m.node is m.game


def test_events():
    m = GameModel()
    assert play(m, "e2e4", "d7d5") == [M.MOVE, M.MOVE]
    assert play(m, "e4d5") == [M.CAPTURE]
    assert play(m, "e7e6", "f1b5") == [M.MOVE, M.CHECK]


def test_castling_and_en_passant():
    m = GameModel()
    play(m, "e2e4", "a7a6", "e4e5", "d7d5")
    assert SQ("d6") in m.legal_targets(SQ("e5"))
    assert play(m, "e5d6") == [M.CAPTURE]
    assert m.board.piece_at(SQ("d5")) is None
    play(m, "a6a5", "g1f3", "a5a4", "f1e2", "a4a3")
    assert SQ("g1") in m.legal_targets(SQ("e1"))
    assert play(m, "e1g1") == [M.CASTLE]


def test_promotion():
    m = GameModel()
    m.new_game(chess.Board("8/P6k/7p/8/8/8/8/K7 w - - 0 1"))
    assert m.needs_promotion(SQ("a7"), SQ("a8"))
    assert m.play(chess.Move(SQ("a7"), SQ("a8"))) is None  # promotion piece required
    assert play(m, "a7a8n") == [M.PROMOTE]
    assert m.board.piece_at(SQ("a8")) == chess.Piece(chess.KNIGHT, chess.WHITE)


def test_checkmate_and_stalemate_status():
    m = GameModel()
    assert play(m, "f2f3", "e7e5", "g2g4", "d8h4") == [M.MOVE, M.MOVE, M.MOVE, M.END]
    assert m.status() == "Checkmate – Black wins"
    m.new_game(chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1"))
    assert m.status() == "Stalemate – Draw"


def test_threefold_repetition():
    m = GameModel()
    play(m, "g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8")
    assert m.status() == "Draw – threefold repetition"


def test_variations_created_and_reused():
    m = GameModel()
    play(m, "e2e4", "e7e5")
    m.back()
    play(m, "c7c5")
    assert len(m.node.parent.variations) == 2
    m.back()
    play(m, "e7e5")  # existing move: no new variation
    assert len(m.node.parent.variations) == 2
    assert m.node.parent.variations[0] is m.node


def test_navigation_and_switch_variation():
    m = GameModel()
    play(m, "e2e4", "e7e5", "g1f3")
    m.go_start()
    assert m.node is m.game
    m.go_end()
    assert m.board.fullmove_number == 2 and m.board.turn == chess.BLACK
    m.back()
    m.back()
    play(m, "c7c5")
    assert m.switch_variation(-1)
    assert m.node.move == chess.Move.from_uci("e7e5")
    assert not m.switch_variation(-1)


def test_delete_last_only_removes_leaf():
    m = GameModel()
    play(m, "e2e4", "e7e5")
    m.back()
    assert not m.delete_last()
    m.forward()
    assert m.delete_last()
    assert m.node.move == chess.Move.from_uci("e2e4") and not m.node.variations


def test_promote_and_delete_variation():
    m = GameModel()
    play(m, "e2e4", "e7e5", "g1f3")
    m.go_start()
    play(m, "d2d4", "d7d5")
    side = m.node
    assert m.promote_to_main(side)
    assert m.game.variations[0].move == chess.Move.from_uci("d2d4")
    old_main = m.game.variations[1]
    assert m.delete_variation(old_main.variations[0])  # any node inside the variation
    assert len(m.game.variations) == 1
    assert m.node is side


def test_delete_from_here_moves_current_out():
    m = GameModel()
    play(m, "e2e4", "e7e5", "g1f3")
    first = m.game.variations[0]
    assert m.delete_from_here(first.variations[0])
    assert m.node is first and not first.variations


def test_comment_marks_modified():
    m = GameModel()
    play(m, "e2e4")
    m.modified = False
    assert m.set_comment(m.node, " best by test ")
    assert m.node.comment == "best by test" and m.modified
    assert not m.set_comment(m.node, "best by test")


def test_play_takes_a_move_object():
    # The entry point for moves that do not come from the mouse (e.g. an engine)
    m = GameModel()
    assert m.play(chess.Move.from_uci("e2e4")) == M.MOVE
    assert m.play(chess.Move.from_uci("e2e4")) is None
    assert m.board.turn == chess.BLACK


def test_material_balance():
    assert M.material_balance(chess.Board(), chess.WHITE) == 0
    board = chess.Board("4k3/8/8/8/8/8/PPP5/R3K3 w - - 0 1")   # rook and three pawns vs nothing
    assert M.material_balance(board, chess.WHITE) == 8
    assert M.material_balance(board, chess.BLACK) == -8


def test_take_back_removes_moves_to_the_previous_turn():
    m = GameModel()
    for san in ("e4", "e5", "Nf3"):
        m.play(m.board.parse_san(san))
    assert m.take_back(chess.BLACK)                  # Nf3 and e5 go; Black to move again
    assert m.board.fen() == chess.Board("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1").fen()
    assert m.modified and not m.node.variations
    assert m.take_back(chess.WHITE) and m.node is m.game   # only e4 left
    assert not m.take_back(chess.WHITE)             # nothing of White's to take back


def test_take_back_works_from_an_earlier_position():
    m = GameModel()
    for san in ("d4", "d5", "c4", "e6"):
        m.play(m.board.parse_san(san))
    m.go_start()
    assert m.take_back(chess.WHITE)
    assert len(list(m.game.mainline_moves())) == 2 and m.node.turn() == chess.WHITE


# --- Restoring deleted moves, headers ----------------------------------------

def play_all(m, *sans):
    for san in sans:
        m.play(m.board.parse_san(san))


def test_restore_puts_a_variation_back_in_its_place():
    m = GameModel()
    play_all(m, "e4", "e5")
    m.back()
    play_all(m, "c5")
    m.back()
    play_all(m, "e6")
    parent = m.node.parent
    second = parent.variations[1]
    m.goto(second)
    assert m.delete_from_here(second) and len(parent.variations) == 2
    assert m.restore_deleted()
    assert parent.variations[1] is second and m.node is second and not m.restore_deleted()


def test_restore_undoes_deletions_in_reverse_order():
    m = GameModel()
    play_all(m, "e4", "e5", "Nf3")
    assert m.delete_last() and m.delete_last() and len(list(m.game.mainline_moves())) == 1
    assert m.restore_deleted() and m.restore_deleted()
    assert len(list(m.game.mainline_moves())) == 3 and m.at_end()


def test_a_new_move_or_game_ends_what_can_be_restored():
    m = GameModel()
    play_all(m, "e4")
    m.delete_last()
    assert m.can_restore()
    play_all(m, "e4")      # the same move again: restoring would give two of them
    assert not m.can_restore() and len(m.game.variations) == 1
    m.delete_last()
    m.new_game()
    assert not m.can_restore()


def test_set_headers_marks_the_game_modified_only_on_a_change():
    m = GameModel()
    m.set_headers({"Result": "*"})
    assert not m.modified
    m.set_headers({"Result": "1-0", "Termination": "normal"})
    assert m.modified and m.headers["Result"] == "1-0"
    m.mark_saved()
    m.clear_result()
    assert m.modified and m.headers["Result"] == "*" and "Termination" not in m.headers
    m.mark_saved()
    m.clear_result()
    assert not m.modified


def test_new_game_with_headers_and_intro_is_not_modified():
    m = GameModel()
    m.new_game(None, {"Event": "Test"}, "Hello")
    assert m.headers["Event"] == "Test" and m.game.comment == "Hello" and not m.modified
