"""A tiny UCI engine for testing the UCI client: plays the first legal move.

Run as: python fake_uci.py   (reads UCI commands from stdin)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "vendor"))

import chess  # noqa: E402


def main():
    board = chess.Board()
    out = sys.stdout
    for line in sys.stdin:
        words = line.split()
        if not words:
            continue
        cmd = words[0]
        if cmd == "uci":
            out.write("id name FakeEngine\n")
            out.write("option name Threads type spin default 1 min 1 max 8\n")
            out.write("option name Hash type spin default 16 min 1 max 1024\n")
            out.write("option name UCI_LimitStrength type check default false\n")
            out.write("option name UCI_Elo type spin default 1320 min 1320 max 3190\n")
            out.write("uciok\n")
        elif cmd == "isready":
            out.write("readyok\n")
        elif cmd == "setoption":
            out.write(f"info string {line.strip()}\n")
        elif cmd == "position":
            fen = " ".join(words[2:8]) if words[1] == "fen" else chess.STARTING_FEN
            board = chess.Board(fen)
            if "moves" in words:
                for uci in words[words.index("moves") + 1:]:
                    board.push_uci(uci)
        elif cmd == "go":
            moves = sorted(board.legal_moves, key=lambda m: m.uci())
            out.write(f"bestmove {moves[0].uci() if moves else '(none)'}\n")
        elif cmd == "quit":
            return
        out.flush()


if __name__ == "__main__":
    main()
