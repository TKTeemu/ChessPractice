import chess
import pytest

from app import fileio
from app.model import GameModel

PGN = """[Event "Analysis"]
[Site "?"]
[Date "2026.11.02"]
[Round "?"]
[White "White"]
[Black "Black"]
[Result "*"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 (3. Bc4 Bc5) 3... a6 {Morphy Defence} *
"""

# Morphy vs Duke of Brunswick and Count Isouard, Paris 1858
OPERA_GAME = ("1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6 7. Qb3 Qe7 "
              "8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7 12. O-O-O Rd8 13. Rxd7 Rxd7 "
              "14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8 17. Rd8# 1-0")


def test_pgn_round_trip(tmp_path):
    game = fileio.parse_pgn_games(PGN)[0]
    path = tmp_path / "game.pgn"
    fileio.write_pgn(game, path)
    again = fileio.read_pgn_games(path)[0]
    assert fileio.game_to_pgn(again) == fileio.game_to_pgn(game)
    third = again.variations[0].variations[0].variations[0].variations[0]
    assert len(third.variations) == 2
    assert third.variations[0].variations[0].comment == "Morphy Defence"


def normalize(pgn):
    return " ".join(pgn.replace("( ", "(").replace(" )", ")").replace("{ ", "{").replace(" }", "}").split())


def test_saved_text_matches_standard():
    assert normalize(fileio.game_to_pgn(fileio.parse_pgn_games(PGN)[0])) == normalize(PGN)


def test_opera_game_entered_on_board():
    m = GameModel()
    reference = fileio.parse_pgn_games(OPERA_GAME)[0]
    for move in reference.mainline_moves():
        assert m.make_move(move.from_square, move.to_square, move.promotion) is not None
    assert m.status() == "Checkmate – White wins"
    moves = normalize(fileio.game_to_pgn(m.game).split("\n\n")[1])
    assert moves == OPERA_GAME[:-4] + " *"


def test_multiple_games():
    games = fileio.parse_pgn_games(PGN + "\n" + OPERA_GAME + "\n")
    assert len(games) == 2


def test_setup_position_pgn(tmp_path):
    fen = "8/P6k/8/8/8/8/8/K7 w - - 0 1"
    m = GameModel()
    m.new_game(chess.Board(fen))
    m.make_move(chess.A7, chess.A8, chess.QUEEN)
    path = tmp_path / "setup.pgn"
    fileio.write_pgn(m.game, path)
    text = path.read_text(encoding="utf-8")
    assert '[SetUp "1"]' in text and f'[FEN "{fen}"]' in text
    assert fileio.read_pgn_games(path)[0].board().fen() == fen


def test_fen_round_trip(tmp_path):
    board = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq - 2 3")
    path = tmp_path / "pos.fen"
    fileio.write_fen(board, path)
    assert fileio.read_fen(path) == board


def test_parse_text():
    kind, board = fileio.parse_text(chess.STARTING_FEN)
    assert kind == "fen" and board == chess.Board()
    kind, games = fileio.parse_text(PGN)
    assert kind == "pgn" and len(games) == 1
    kind, games = fileio.parse_text("1. d4 d5 2. c4")
    assert kind == "pgn" and len(list(games[0].mainline_moves())) == 3
    for bad in ("", "hello world", "1. e4 e5 2. Ke3"):
        with pytest.raises(ValueError):
            fileio.parse_text(bad)
