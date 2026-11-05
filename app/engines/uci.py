"""A small UCI client on top of subprocess.

Written instead of chess.engine because python-chess 1.11.2 uses an asyncio API
that is removed in Python 3.16. Any UCI engine can reuse it.
"""

import queue
import subprocess
import sys
import threading
import time

import chess

from .base import Analysis, EngineError

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
START_TIMEOUT = 10.0     # seconds to wait for uciok / readyok
EXTRA_TIMEOUT = 10.0     # seconds to wait for bestmove beyond the requested think time
STOP_TIMEOUT = 2.0       # seconds to wait for bestmove after "stop"


def parse_option(line):
    """'option name UCI_Elo type spin default 1320 min 1320 max 3190' -> ("UCI_Elo", {...})."""
    words = line.split()[2:]
    keywords = ("type", "default", "min", "max", "var")
    name = []
    while words and words[0] not in keywords:
        name.append(words.pop(0))
    info = {}
    key = None
    for word in words:
        if word in keywords:
            key = word
            info.setdefault(key, "")
        elif key:
            info[key] = f"{info[key]} {word}".strip()
    for key in ("min", "max"):
        if key in info:
            try:
                info[key] = int(info[key])
            except ValueError:
                del info[key]
    return " ".join(name), info


def parse_score(line):
    """'info depth 20 score cp 35 … pv …' -> (35, None); '… score mate -3 …' -> (None, -3).
    None if the line has no exact score (none at all, or only a lowerbound/upperbound)."""
    words = line.split()
    try:
        i = words.index("score")
        kind, value = words[i + 1], int(words[i + 2])
    except (ValueError, IndexError):
        return None
    if words[i + 3:i + 4] in (["lowerbound"], ["upperbound"]):
        return None
    if kind == "cp":
        return value, None
    if kind == "mate":
        return None, value
    return None


def parse_pv(line):
    """'info depth 20 … pv e2e4 e7e5' -> (Move(e2e4), Move(e7e5)); () if the line has no pv."""
    words = line.split()
    if "pv" not in words:
        return ()
    try:
        return tuple(chess.Move.from_uci(word) for word in words[words.index("pv") + 1:])
    except ValueError:
        return ()


class UciClient:
    """One engine process. Not thread-safe: use it from one thread (close() excepted)."""

    def __init__(self, command, cwd=None):
        self.command = [str(c) for c in command]
        self.cwd = cwd
        self.process = None
        self.lines = queue.Queue()
        self.options = {}   # name -> {"type": …, "default": …, "min": …, "max": …}
        self.name = ""
        self._lock = threading.Lock()

    # --- Process ----------------------------------------------------------

    def start(self):
        try:
            self.process = subprocess.Popen(
                self.command, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                bufsize=1, creationflags=NO_WINDOW)
        except OSError as e:
            raise EngineError(str(e)) from e
        threading.Thread(target=self._read, args=(self.process.stdout,), daemon=True).start()
        self.send("uci")
        for line in self._until("uciok", START_TIMEOUT):
            if line.startswith("option name "):
                name, info = parse_option(line)
                self.options[name] = info
            elif line.startswith("id name "):
                self.name = line[8:].strip()

    def _read(self, stream):
        try:
            for line in stream:
                self.lines.put(line.strip())
        except (OSError, ValueError):
            pass
        self.lines.put(None)   # end of output: the process has exited

    def send(self, text):
        try:
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()
        except (OSError, ValueError, AttributeError) as e:
            raise EngineError(f"engine not running ({e})") from e

    def _until(self, token, timeout):
        """Yield output lines up to and including the first line starting with `token`."""
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise EngineError(f"no '{token}' from engine")
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty:
                continue
            if line is None:
                raise EngineError("engine exited")
            yield line
            if line == token or line.startswith(token + " "):
                return

    # --- Commands ---------------------------------------------------------

    def setoption(self, name, value):
        if isinstance(value, bool):
            value = "true" if value else "false"
        self.send(f"setoption name {name} value {value}")

    def isready(self):
        self.send("isready")
        for _ in self._until("readyok", START_TIMEOUT):
            pass

    def new_game(self):
        self.send("ucinewgame")
        self.isready()

    def search(self, board, movetime, stop):
        """Search `board` for `movetime` seconds; returns an Analysis (best move, the last
        exact score reported, the latest line, and the ponder move if any)."""
        root = board.root()
        moves = " ".join(m.uci() for m in board.move_stack)
        self.send(f"position fen {root.fen()}" + (f" moves {moves}" if moves else ""))
        self.send(f"go movetime {max(1, round(movetime * 1000))}")
        deadline = time.monotonic() + movetime + EXTRA_TIMEOUT
        stopped = False
        score = (None, None)
        pv = ()
        while True:
            if stop.is_set() and not stopped:
                self.send("stop")
                stopped = True
                deadline = min(deadline, time.monotonic() + STOP_TIMEOUT)
            if time.monotonic() > deadline:
                raise EngineError("no 'bestmove' from engine")
            try:
                line = self.lines.get(timeout=0.05)
            except queue.Empty:
                continue
            if line is None:
                raise EngineError("engine exited")
            if line.startswith("info "):
                score = parse_score(line) or score
                pv = parse_pv(line) or pv
            elif line.startswith("bestmove"):
                parts = line.split()
                try:
                    move = chess.Move.from_uci(parts[1])
                except (IndexError, ValueError):
                    raise EngineError(f"engine has no move: {line}") from None
                if move not in board.legal_moves:
                    raise EngineError(f"illegal move from engine: {parts[1]}")
                ponder = None
                if len(parts) >= 4 and parts[2] == "ponder":
                    try:
                        ponder = chess.Move.from_uci(parts[3])
                    except ValueError:
                        pass
                return Analysis(move, *score, ponder=ponder, pv=pv if pv[:1] == (move,) else (move,))

    def close(self):
        with self._lock:
            process, self.process = self.process, None
        if process is None:
            return
        try:
            process.stdin.write("quit\n")
            process.stdin.flush()
        except (OSError, ValueError):
            pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)
        for stream in (process.stdin, process.stdout):
            try:
                stream.close()
            except (OSError, ValueError):
                pass
