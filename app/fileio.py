"""Reading and writing PGN and FEN."""

import io
from pathlib import Path

import chess
import chess.pgn


def parse_pgn_games(text):
    games = []
    stream = io.StringIO(text)
    while True:
        game = chess.pgn.read_game(stream)
        if game is None:
            break
        if game.errors:
            raise ValueError(str(game.errors[0]))
        games.append(game)
    return games


def read_pgn_games(path):
    return parse_pgn_games(Path(path).read_text(encoding="utf-8-sig", errors="replace"))


def game_to_pgn(game):
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    return game.accept(exporter) + "\n"


def write_pgn(game, path):
    Path(path).write_text(game_to_pgn(game), encoding="utf-8")


def read_fen(path):
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            return chess.Board(line.strip())
    raise ValueError("empty file")


def write_fen(board, path):
    Path(path).write_text(board.fen() + "\n", encoding="utf-8")


def parse_text(text):
    """Interpret pasted text: returns ("fen", Board) or ("pgn", [games]), or raises ValueError."""
    text = text.strip()
    if not text:
        raise ValueError("empty")
    if "\n" not in text:
        try:
            return "fen", chess.Board(text)
        except ValueError:
            pass
    games = parse_pgn_games(text)
    games = [g for g in games if g.variations or "FEN" in g.headers or text.lstrip().startswith("[")]
    if not games:
        raise ValueError("no games")
    return "pgn", games
