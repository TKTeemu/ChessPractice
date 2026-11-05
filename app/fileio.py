"""Reading and writing PGN and FEN."""

import io
import os
from pathlib import Path

import chess
import chess.pgn

from . import strings as S


class GameList(list):
    """The games read from a PGN text. `skipped` lists the games that could not be read."""
    skipped = ()


def read_text(path):
    """A text file as UTF-8 or, if it is not valid UTF-8, as Windows-1252 (common in old PGN
    files). Guessing wrong must not lose letters: saving would make the damage permanent."""
    data = Path(path).read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def write_text_atomic(path, text):
    """Write through a temporary file, so that a crash cannot leave half a file."""
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise


def board_from_fen(fen):
    """A chess.Board from a FEN; ValueError unless it is a position the rules and engines can
    handle (a FEN without kings parses fine, but Stockfish crashes on it)."""
    board = chess.Board(fen)
    if not board.is_valid():
        raise ValueError(S.ERROR_INVALID_POSITION)
    return board


def _game_error(game):
    """Why this parsed game cannot be used, or None."""
    if game.errors:
        return str(game.errors[0])
    try:
        return None if game.board().is_valid() else S.ERROR_INVALID_POSITION
    except ValueError as e:
        return str(e)


def parse_pgn_games(text):
    """The games in a PGN text as a GameList. A bad game is skipped and listed in `skipped`;
    ValueError only if there were games and none of them could be read."""
    games = GameList()
    games.skipped = []
    stream = io.StringIO(text)
    number = 0
    while (game := chess.pgn.read_game(stream)) is not None:
        number += 1
        error = _game_error(game)
        if error is None:
            games.append(game)
        else:
            games.skipped.append(S.GAME_SKIPPED.format(number=number, error=error))
    if games.skipped and not games:
        raise ValueError(games.skipped[0])
    return games


def read_pgn_games(path):
    return parse_pgn_games(read_text(path))


def load_pgn_folder(folder, build):
    """Every game of every *.pgn file in `folder`, for data files such as the opening book.
    build(game) makes an item of a game, or raises ValueError to skip it.
    Returns (items, [(file name, message)])."""
    items, errors = [], []
    for path in sorted(Path(folder).glob("*.pgn")):
        try:
            text = read_text(path)
        except OSError as e:
            errors.append((path.name, str(e)))
            continue
        stream = io.StringIO(text)
        while (game := chess.pgn.read_game(stream)) is not None:
            try:
                items.append(build(game))
            except ValueError as e:
                errors.append((path.name, str(e)))
    return items, errors


def game_to_pgn(game):
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
    return game.accept(exporter) + "\n"


def write_pgn(game, path):
    write_text_atomic(path, game_to_pgn(game))


def read_fen(path):
    for line in read_text(path).splitlines():
        if line.strip():
            return board_from_fen(line.strip())
    raise ValueError("empty file")


def write_fen(board, path):
    write_text_atomic(path, board.fen() + "\n")


def parse_text(text):
    """Interpret pasted text: returns ("fen", Board) or ("pgn", GameList), or raises ValueError."""
    text = text.strip()
    if not text:
        raise ValueError("empty")
    if "\n" not in text:
        try:
            return "fen", board_from_fen(text)
        except ValueError:
            pass
    parsed = parse_pgn_games(text)
    games = GameList(g for g in parsed
                     if g.variations or "FEN" in g.headers or text.lstrip().startswith("["))
    games.skipped = parsed.skipped
    if not games:
        raise ValueError("no games")
    return "pgn", games
