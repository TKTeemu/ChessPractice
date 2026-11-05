"""Check the endgame positions in assets/endgames/ with Stockfish.

    python -m tools.check_endgames                 every position, 3 s per position looked at
    python -m tools.check_endgames --level 5 --time 10
    python -m tools.check_endgames --key saavedra

Run it whenever positions are added or changed. It is slow, so it is not part of the tests.
For each position it checks that

1. the FEN is legal and the Goal is right: the side to move wins (Goal "win") or holds the
   draw without being clearly better (Goal "draw");
2. no user move of the solution (main line or variation without a NAG) gives the goal away,
   and every move marked ? or ?? really does, judged by the same rule as the game
   (app/endgame_game.is_mistake);

and prints a summary: positions per level, missing source details and every problem found.
With Syzygy tablebases in engines/syzygy/ the scores of small positions are exact.
Exit status 1 if there were problems.
"""

import argparse
import sys
import threading
from pathlib import Path

import chess

from app.endgame_game import LOSS_CP, MATE, MATE_BAND, WIN_LOST_CP, is_mistake, user_score
from app.endgames import WRONG_NAGS, EndgameCollection
from app.engines.base import Level
from app.engines.stockfish import StockfishEngine
from app.model import game_outcome
from app.settings import Settings

ROOT = Path(__file__).resolve().parent.parent
WIN_SUSPICIOUS = 300    # Goal "draw" but the user's side is better than this: is it really a draw?


class Checker:
    def __init__(self, engine, seconds):
        self.engine = engine
        self.level = Level("check", "", None, seconds, {"UCI_LimitStrength": False})
        self.cache = {}

    def score(self, board, user):
        """The engine's score of `board` from `user`'s point of view."""
        key = board.fen()
        if key not in self.cache:
            if board.is_checkmate():
                self.cache[key] = (-MATE, board.turn)
            elif game_outcome(board) is not None:
                self.cache[key] = (0, board.turn)
            else:
                analysis = self.engine.analyse(board, self.level, threading.Event())
                self.cache[key] = (user_score(analysis, True), board.turn)
        value, turn = self.cache[key]
        return value if turn == user else -value

    def check(self, sample):
        """A list of problems with this position (empty = fine)."""
        problems = []
        board = sample.game.board()
        user = board.turn
        start = self.score(board, user)
        if sample.goal == "win" and start < WIN_LOST_CP:
            problems.append(f"Goal win, but the start is only {fmt(start)}")
        if sample.goal == "draw":
            if start < LOSS_CP:
                problems.append(f"Goal draw, but the start is lost ({fmt(start)})")
            elif start > WIN_SUSPICIOUS:
                problems.append(f"Goal draw, but the user's side is better ({fmt(start)})")
        self._walk(sample, sample.game, board, user, problems)
        return problems

    def _walk(self, sample, node, board, user, problems):
        for child in node.variations:
            before = self.score(board, user) if board.turn == user else None
            san = board.san(child.move)
            number = f"{board.fullmove_number}{'.' if board.turn == chess.WHITE else '...'}"
            board.push(child.move)
            if before is not None:
                after = self.score(board, user)
                mistake = is_mistake(sample.goal, before, after)
                wrong = bool(WRONG_NAGS & child.nags)
                if wrong and not mistake:
                    problems.append(f"{number} {san}? is marked wrong, but scores {fmt(after)} (before {fmt(before)})")
                elif not wrong and mistake:
                    problems.append(f"{number} {san} gives the goal away: {fmt(before)} -> {fmt(after)}")
            self._walk(sample, child, board, user, problems)
            board.pop()


def fmt(score):
    if score >= MATE - MATE_BAND:
        return f"mate in {MATE - score}"
    if score <= -MATE + MATE_BAND:
        return f"mated in {MATE + score}"
    return f"{score:+d} cp"


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--time", type=float, default=3.0, help="seconds per position looked at")
    parser.add_argument("--level", type=int, help="only this difficulty")
    parser.add_argument("--key", help="only this position")
    parser.add_argument("--folder", default=str(ROOT / "assets" / "endgames"))
    args = parser.parse_args()

    collection = EndgameCollection.load(args.folder)
    failed = bool(collection.errors)
    for name, error in collection.errors:
        print(f"ERROR {name}: {error}")
    settings = Settings(ROOT / "settings.json")
    if not StockfishEngine.available(settings, ROOT):
        raise SystemExit(StockfishEngine.unavailable_reason(settings, ROOT))
    engine = StockfishEngine(settings, ROOT)
    engine.start()
    engine.new_game()
    checker = Checker(engine, args.time)
    try:
        for difficulty, name, count in collection.levels():
            if args.level not in (None, difficulty):
                continue
            print(f"\nLevel {difficulty} – {name}: {count} positions")
            for sample in collection.samples(difficulty):
                if args.key not in (None, sample.key):
                    continue
                problems = checker.check(sample)
                credit = sample.credit_text() or "(no source)"
                print(f"  {'FAIL' if problems else 'ok  '} {sample.key:24s} {sample.goal:4s} {sample.name} · {credit}")
                for problem in problems:
                    print(f"         {problem}")
                failed = failed or bool(problems)
                sys.stdout.flush()
    finally:
        engine.close()
    print("\nProblems found." if failed else "\nAll positions are fine.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
