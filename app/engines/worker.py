"""EngineWorker: runs an engine's searches in a background thread.

Results go into a queue that the main thread polls; the worker never touches tkinter.
"""

import queue
import threading

from .base import EngineError

JOIN_TIMEOUT = 3.0


class EngineWorker:
    """Owns one engine and one thread. The engine is started lazily on the first request."""

    def __init__(self, engine):
        self.engine = engine
        self.results = queue.Queue()   # (request_id, chess.Move or EngineError)
        self._jobs = queue.Queue()
        self._stop = threading.Event()
        self._closed = False
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def request(self, board, level, request_id):
        """Start a search on a copy of `board`."""
        self.cancel()
        self._stop = threading.Event()
        self._jobs.put((board.copy(), level, request_id, self._stop))

    def cancel(self):
        """Ask the running search to stop. Its result still arrives; ignore it by request id."""
        self._stop.set()

    def poll(self):
        """Results ready so far (call from the main thread)."""
        items = []
        while True:
            try:
                items.append(self.results.get_nowait())
            except queue.Empty:
                return items

    def close(self):
        if self._closed:
            return
        self._closed = True
        self.cancel()
        self._jobs.put(None)
        self._thread.join(JOIN_TIMEOUT)
        self.engine.close()   # again, in case the thread is stuck: kills the process

    def _run(self):
        started = False
        try:
            while True:
                job = self._jobs.get()
                if job is None:
                    return
                board, level, request_id, stop = job
                if stop.is_set():
                    continue
                try:
                    if not started:
                        self.engine.start()
                        self.engine.new_game()
                        started = True
                    result = self.engine.best_move(board, level, stop)
                except EngineError as e:
                    result = e
                except Exception as e:   # a bug in an engine must not kill the thread silently
                    result = EngineError(repr(e))
                self.results.put((request_id, result))
        finally:
            self.engine.close()
